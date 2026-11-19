"""Shared configuration, state and app-discovery helpers.

* apps.json   - what YOU edit (apps, repos, settings). Safe to commit.
* state.json  - what the updater writes (active version, history). Not committed.
"""
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

DEFAULT_SETTINGS = {
    "server_name": "Craft Apps",
    "host": "0.0.0.0",
    "port": 8080,
    "auto_discover": True,
    "backup_count": 3,          # old versions kept besides the active one
    "cross_origin_isolation": False,  # COOP/COEP headers (needed by some WASM apps)
    "tls_cert": "",             # optional: path to certificate (enables HTTPS)
    "tls_key": "",
    "admin_enabled": True,
    "admin_allowed_networks": [  # admin dashboard is reachable only from these
        "127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12",
        "192.168.0.0/16", "169.254.0.0/16", "fc00::/7", "fe80::/10",
    ],
    "admin_session_minutes": 30,
    "max_upload_mb": 1024,
    "inbox_enabled": True,      # drop <prefix><version>.zip into inbox/ to install
    "inbox_poll_seconds": 5,
    # The dashboard runs on its own port so that a hosted app (same origin as the
    # public port) can never talk to it. 0 = share the public port (not recommended).
    "admin_port": 8081,
    "admin_host": "",           # empty = same as "host"; use 127.0.0.1 to keep it local
    "cache_enabled": True,      # keep every downloaded/uploaded zip: no re-downloads
    "cache_keep": 5,            # zips kept per app
    "auto_update_hours": 6,     # how often GitHub is checked (0 = never)
    "access_log": False,
}

DEFAULT_APPS = {
    "settings": {"server_name": "Craft Apps"},
    "apps": [
        {"id": "pdfcraft", "title": "PDF Craft", "folder_prefix": "pdfcraft-web-",
         "repo": "storytold/pdfcraft", "asset_pattern": "^pdfcraft-web-.*\\.zip$",
         "index_path": "index.html", "description": "PDF editor and tools",
         "icon": "\U0001F4C4", "enabled": True, "prerelease": False, "auto_update": False},
        {"id": "figcraft", "title": "Fig Craft", "folder_prefix": "figcraft-web-",
         "repo": "storytold/figcraft", "asset_pattern": ".*web.*\\.zip$",
         "index_path": "index.html", "description": "Graphics editor",
         "icon": "\U0001F3A8", "enabled": True, "prerelease": False, "auto_update": False},
    ],
}

RESERVED_IDS = {"admin", "health", "api"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
OP_LOCK = threading.Lock()  # one install/update/delete at a time

lock = threading.RLock()


# ---------------------------------------------------------------- paths
def base_dir():
    """Data folder: $CRAFTWEB_HOME, else next to the executable (frozen build),
    else the project folder."""
    env = os.environ.get("CRAFTWEB_HOME")
    if env:
        return Path(env).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def cache_dir():
    return base_dir() / "cache"


def ensure_default_config():
    """First run on a clean folder (or a container volume): create apps.json."""
    if not config_path().exists():
        base_dir().mkdir(parents=True, exist_ok=True)
        save_json(config_path(), DEFAULT_APPS)


def root_dir():
    return base_dir() / "root"


def config_path():
    return base_dir() / "apps.json"


def state_path():
    return base_dir() / "state.json"


# ---------------------------------------------------------------- json io
def _load_json(path, default):
    if not path.exists():
        return default
    try:
        # utf-8-sig tolerates the BOM that Windows editors like to add
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print("WARNING: cannot read %s: %s" % (path.name, exc), file=sys.stderr)
        return default


def save_json(path, data):
    with lock:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)


def load_config():
    data = _load_json(config_path(), {})
    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings") or {})
    apps = [a for a in (data.get("apps") or []) if isinstance(a, dict)]
    return {"settings": settings, "apps": apps}


def update_apps(mutator):
    """Edit only the 'apps' list of apps.json (settings are written back untouched)."""
    with lock:
        raw = _load_json(config_path(), {})
        if not isinstance(raw, dict):
            raw = {}
        apps = [a for a in (raw.get("apps") or []) if isinstance(a, dict)]
        mutator(apps)
        raw["apps"] = apps
        raw.setdefault("settings", {})
        save_json(config_path(), raw)
    invalidate_cache()


def load_state():
    data = _load_json(state_path(), {})
    return data if isinstance(data, dict) else {}


def save_state(state):
    save_json(state_path(), state)


# ---------------------------------------------------------------- versions
_PRE = re.compile(r"[-._]?(alpha|beta|rc|pre|dev|snapshot)", re.IGNORECASE)


def version_key(name, prefix=""):
    """Sortable key: 1.10.0 > 1.9.0, and 1.2.0 > 1.2.0-rc.1."""
    if prefix and name.lower().startswith(prefix.lower()):
        name = name[len(prefix):]
    match = _PRE.search(name)
    main = name[:match.start()] if match else name
    pre = name[match.end():] if match else ""
    nums = tuple(int(n) for n in re.findall(r"\d+", main))
    pre_nums = tuple(int(n) for n in re.findall(r"\d+", pre))
    return (nums, 0 if match else 1, pre_nums)


def tag_of(app, folder_name):
    prefix = app.get("folder_prefix", "")
    if prefix and folder_name.lower().startswith(prefix.lower()):
        return folder_name[len(prefix):]
    return folder_name


def installed_folders(app):
    """Installed version folders of an app, newest first."""
    prefix = app.get("folder_prefix", "")
    root = root_dir()
    if not prefix or not root.is_dir():
        return []
    found = [
        p for p in root.iterdir()
        if p.is_dir()
        and not p.name.endswith(".installing")
        and p.name.lower().startswith(prefix.lower())
    ]
    found.sort(key=lambda p: version_key(p.name, prefix), reverse=True)
    return found


def active_folder(app, state=None):
    """The folder being served: the one the updater activated, else the newest."""
    folders = installed_folders(app)
    if not folders:
        return None
    if state is None:
        state = load_state()
    wanted = (state.get(app.get("id", "").lower()) or {}).get("active_folder")
    for folder in folders:
        if folder.name == wanted:
            return folder
    return folders[0]


# ---------------------------------------------------------------- discovery
CACHE_TTL = 2.0
_cache = {"key": None, "at": 0.0, "apps": {}}


def invalidate_cache():
    _cache["at"] = 0.0


def discover_apps():
    """Map of app id -> app info. Cached for a couple of seconds so serving
    every asset request does not re-scan the disk."""
    with lock:
        key = str(base_dir())
        if _cache["key"] == key and time.monotonic() - _cache["at"] < CACHE_TTL:
            return _cache["apps"]
        apps = _scan()
        _cache.update(key=key, at=time.monotonic(), apps=apps)
        return apps


def _scan():
    config = load_config()
    settings = config["settings"]
    state = load_state()
    root = root_dir()
    root.mkdir(exist_ok=True)
    apps = {}

    for item in config["apps"]:
        if not item.get("enabled", True):
            continue
        app_id = str(item.get("id", "")).strip().lower()
        if not app_id or app_id in RESERVED_IDS or not item.get("folder_prefix"):
            continue
        selected = active_folder(item, state)
        if selected is None:
            continue
        index = (selected / item.get("index_path", "index.html")).resolve()
        try:
            if selected.resolve() not in index.parents or not index.is_file():
                continue
        except OSError:
            continue
        apps[app_id] = {
            "id": app_id,
            "title": item.get("title", app_id),
            "description": item.get("description", ""),
            "icon": item.get("icon", ""),
            "base": selected.resolve(),
            "index": index,
            "version": selected.name,
            "source": "configured",
            "cross_origin_isolation": bool(
                item.get("cross_origin_isolation", settings["cross_origin_isolation"])
            ),
        }

    if settings.get("auto_discover", True):
        prefixes = [
            str(a.get("folder_prefix", "")).lower()
            for a in config["apps"] if a.get("folder_prefix")
        ]
        folders = [
            p for p in root.iterdir()
            if p.is_dir() and not p.name.endswith(".installing")
            and not any(p.name.lower().startswith(x) for x in prefixes)
        ]
        folders.sort(key=lambda p: version_key(p.name), reverse=True)
        for folder in folders:
            indexes = list(folder.rglob("index.html"))
            if not indexes:
                continue
            index = min(indexes, key=lambda p: len(p.relative_to(folder).parts))
            slug = re.sub(r"-web-.*$", "", folder.name, flags=re.IGNORECASE).lower()
            slug = re.sub(r"[^a-z0-9_-]+", "-", slug).strip("-")
            if not slug or slug in apps or slug in RESERVED_IDS:
                continue
            apps[slug] = {
                "id": slug,
                "title": slug.replace("-", " ").title(),
                "description": "Automatically discovered",
                "icon": "",
                "base": index.parent.resolve(),
                "index": index.resolve(),
                "version": folder.name,
                "source": "automatic",
                "cross_origin_isolation": bool(settings["cross_origin_isolation"]),
            }
    return apps

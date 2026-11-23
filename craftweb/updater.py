"""Release manager: install, update, roll back and prune Craft apps.

Examples
  python updater.py                               interactive menu
  python updater.py --list                        installed versions
  python updater.py --check                       compare with GitHub (exit 10 if updates exist)
  python updater.py --app pdfcraft --latest       install newest release
  python updater.py --latest --all                update every enabled app
  python updater.py --app pdfcraft --tag v1.2.0   install a specific release
  python updater.py --app pdfcraft --from-zip x.zip --tag v1.2.0   offline install
  python updater.py --app pdfcraft --rollback     go back to the previous version
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

from . import config as cfg
from . import localize

API = "https://api.github.com"
USER_AGENT = "CraftWeb-Manager"
MAX_FILES = 10000
MAX_BYTES = 2 * 1024 * 1024 * 1024


class UpdateError(Exception):
    pass


_sink = threading.local()


def say(*args):
    """print(), unless a capture() is active on this thread (dashboard jobs)."""
    line = " ".join(str(a) for a in args)
    fn = getattr(_sink, "fn", None)
    if fn:
        fn(line)
    else:
        print(line)


@contextlib.contextmanager
def capture(fn):
    previous = getattr(_sink, "fn", None)
    _sink.fn = fn
    try:
        yield
    finally:
        _sink.fn = previous


def describe_error(exc):
    if isinstance(exc, UpdateError):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        hint = ""
        if exc.code in (403, 429):
            hint = " (GitHub rate limit? set the GITHUB_TOKEN environment variable)"
        elif exc.code == 404:
            hint = " (repo/tag not found, or private - set GITHUB_TOKEN)"
        return "GitHub returned HTTP %d%s" % (exc.code, hint)
    if isinstance(exc, urllib.error.URLError):
        return ("cannot reach GitHub (%s). On an offline network use "
                "a ZIP upload or the inbox folder." % exc.reason)
    return "%s: %s" % (type(exc).__name__, exc)


# ---------------------------------------------------------------- HTTP
class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the GitHub token to another host (e.g. the CDN)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urlsplit(newurl).netloc != urlsplit(req.full_url).netloc:
            new.headers.pop("Authorization", None)
            new.unredirected_hdrs.pop("Authorization", None)
        return new


def _token():
    import os
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _open(url, accept, timeout):
    headers = {"Accept": accept, "User-Agent": USER_AGENT,
               "X-GitHub-Api-Version": "2022-11-28"}
    if _token():
        headers["Authorization"] = "Bearer " + _token()
    opener = urllib.request.build_opener(_StripAuthOnRedirect)  # honours HTTP(S)_PROXY
    return opener.open(urllib.request.Request(url, headers=headers), timeout=timeout)


def api_get(url):
    with _open(url, "application/vnd.github+json", 45) as response:
        return json.loads(response.read().decode("utf-8"))


def get_releases(repo, prerelease=False):
    releases = api_get("%s/repos/%s/releases?per_page=30" % (API, repo))
    return [r for r in releases
            if not r.get("draft") and (prerelease or not r.get("prerelease"))]


def get_release_by_tag(repo, tag):
    return api_get("%s/repos/%s/releases/tags/%s" % (API, repo, quote(tag)))


def download(asset, destination):
    # With a token (private repos) the API asset URL must be used.
    url = asset["url"] if _token() else asset["browser_download_url"]
    digest = hashlib.sha256()
    done = 0
    total = asset.get("size") or 0
    step = 0
    with _open(url, "application/octet-stream", 120) as response, \
            open(destination, "wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total and done * 10 // total > step:
                step = done * 10 // total
                say("  %d%%" % (step * 10))
    expected = asset.get("digest") or ""
    if expected.startswith("sha256:") and digest.hexdigest().lower() != expected[7:].lower():
        raise UpdateError("SHA256 verification failed - download is corrupt.")
    return digest.hexdigest()


# ---------------------------------------------------------------- archives
def sanitize_tag(tag):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", tag).strip("-") or "unknown"


def safe_extract(zip_path, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES:
            raise UpdateError("Archive contains too many files.")
        total = 0
        for entry in entries:
            name = entry.filename.replace("\\", "/")
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or re.match(r"^[A-Za-z]:", name):
                raise UpdateError("Unsafe archive path: %s" % entry.filename)
            if entry.flag_bits & 1:
                raise UpdateError("Encrypted ZIP is not supported.")
            total += entry.file_size
            if total > MAX_BYTES:
                raise UpdateError("Archive exceeds the 2 GB limit.")
            target = (destination / Path(*member.parts)).resolve()
            if target != destination and destination not in target.parents:
                raise UpdateError("Archive path escapes destination.")
        archive.extractall(destination)


def find_app_root(extracted, index_path):
    matches = [p for p in extracted.rglob(index_path) if p.is_file()]
    if not matches:
        raise UpdateError("Could not find %s in the archive." % index_path)
    root = min(matches, key=lambda p: len(p.relative_to(extracted).parts))
    for _ in PurePosixPath(index_path).parts:
        root = root.parent
    return root


def _downloads():
    path = cfg.base_dir() / "downloads"
    path.mkdir(exist_ok=True)
    return path


# ---------------------------------------------------------------- install
def activate(app, folder_name, asset="", sha256=""):
    with cfg.lock:
        state = cfg.load_state()
        key = app["id"].lower()
        entry = state.get(key, {})
        current = cfg.active_folder(app, state)
        history = [h for h in entry.get("history", []) if h != folder_name]
        if current is not None and current.name != folder_name:
            history.append(current.name)
        entry.update(
            active_folder=folder_name,
            installed_version=cfg.tag_of(app, folder_name),
            installed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            last_asset=asset,
            last_sha256=sha256,
            history=history[-20:],
        )
        state[key] = entry
        cfg.save_state(state)
    cfg.invalidate_cache()


def prune(app):
    keep = int(cfg.load_config()["settings"].get("backup_count", 3))
    root = cfg.root_dir()
    for leftover in root.glob(app["folder_prefix"] + "*.installing"):
        shutil.rmtree(leftover, ignore_errors=True)
    if keep < 0:
        return
    active = cfg.active_folder(app)
    others = [f for f in cfg.installed_folders(app) if f != active]
    for old in others[keep:]:
        say("Removing old version:", old.name)
        shutil.rmtree(old, ignore_errors=True)


def _zip_total(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        return sum(e.file_size for e in archive.infolist())


def _ensure_space(path, needed):
    free = shutil.disk_usage(path).free
    if free < needed + 50 * 1024 * 1024:
        raise UpdateError("Not enough disk space: about %.0f MB needed, %.0f MB free."
                          % (needed / 1048576, free / 1048576))


def _place(app, name, source):
    """Copy an app tree into root/<name> atomically (staging folder + rename)."""
    index_path = app.get("index_path", "index.html")
    root = cfg.root_dir()
    staging = root / (name + ".installing")
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging)
    if not (staging / index_path).is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise UpdateError("Installation validation failed.")
    staging.rename(root / name)


def _activate_if(app, name, asset, sha256, mode, before):
    key = lambda n: cfg.version_key(n, app["folder_prefix"])  # noqa: E731
    if mode == "always" or before is None or key(name) > key(before.name):
        localize.auto(cfg.root_dir() / name, say)   # offline-ready before anyone opens it
        activate(app, name, asset, sha256)
        return True
    say("Installed %s but kept %s active (it is newer)." % (name, before.name))
    return False


def install_zip(app, zip_path, tag, asset="", sha256="", mode="always", cache=True):
    """Install a release zip. mode="newer" only switches to it if it is newer than
    the active version (used by imports). The zip is kept in the local cache."""
    zip_path = Path(zip_path)
    root = cfg.root_dir()
    root.mkdir(exist_ok=True)
    name = app["folder_prefix"] + sanitize_tag(tag)
    before = cfg.active_folder(app)

    if (root / name).exists():
        say("Version %s is already installed - activating it." % name)
    else:
        _ensure_space(root, _zip_total(zip_path) * 2.2)
        with tempfile.TemporaryDirectory(dir=_downloads()) as tmp:
            extracted = Path(tmp) / "extracted"
            extracted.mkdir()
            safe_extract(zip_path, extracted)
            _place(app, name, find_app_root(extracted, app.get("index_path", "index.html")))

    if cache:
        cache_store(app, zip_path, tag, asset or zip_path.name)
    activated = _activate_if(app, name, asset, sha256, mode, before)
    prune(app)
    if activated:
        say("\nSUCCESS: %s %s is now live at /%s/" % (app["title"], tag, app["id"]))
    return root / name


def install_dir(app, directory, tag, mode="always"):
    """Install an already extracted web build (a folder that contains index.html)."""
    root = cfg.root_dir()
    root.mkdir(exist_ok=True)
    name = app["folder_prefix"] + sanitize_tag(tag)
    before = cfg.active_folder(app)
    if (root / name).exists():
        say("Version %s is already installed." % name)
    else:
        source = find_app_root(Path(directory), app.get("index_path", "index.html"))
        _ensure_space(root, sum(f.stat().st_size for f in source.rglob("*") if f.is_file()) * 1.2)
        _place(app, name, source)
    activated = _activate_if(app, name, "", "", mode, before)
    prune(app)
    if activated:
        say("\nSUCCESS: %s %s is now live at /%s/" % (app["title"], tag, app["id"]))
    return root / name


# ---------------------------------------------------------------- local cache
# Every zip that is downloaded, uploaded or imported is kept in cache/<app-id>/, so a
# version can be reinstalled (or rolled back to after pruning) without downloading again.
def _safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120] or "app.zip"


def cache_file(app, tag, asset):
    return cfg.cache_dir() / app["id"].lower() / (sanitize_tag(tag) + "__" + _safe_name(asset))


def cache_list(app):
    folder = cfg.cache_dir() / app["id"].lower()
    if not folder.is_dir():
        return []
    items = []
    for f in folder.glob("*__*"):
        if f.is_file() and f.suffix.lower() == ".zip":
            tag = f.name.split("__", 1)[0]
            items.append({"name": f.name, "tag": tag, "size": f.stat().st_size,
                          "mtime": int(f.stat().st_mtime)})
    items.sort(key=lambda i: cfg.version_key(i["tag"]), reverse=True)
    return items


def cache_store(app, zip_path, tag, asset):
    settings = cfg.load_config()["settings"]
    if not settings.get("cache_enabled", True):
        return None
    dest = cache_file(app, tag, asset)
    try:
        if dest.exists() and dest.stat().st_size == Path(zip_path).stat().st_size:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        shutil.copyfile(zip_path, part)
        os.replace(part, dest)
    except OSError as exc:  # a full disk must never break an otherwise good install
        say("Warning: could not cache the download (%s)." % exc)
        return None
    keep = int(settings.get("cache_keep", 5))
    if keep > 0:
        for old in cache_list(app)[keep:]:
            (dest.parent / old["name"]).unlink(missing_ok=True)
    return dest


def cache_delete(app, name):
    for item in cache_list(app):
        if item["name"] == name:
            (cfg.cache_dir() / app["id"].lower() / name).unlink(missing_ok=True)
            return True
    raise UpdateError("Cached file not found.")


def install_from_cache(app, name):
    for item in cache_list(app):
        if item["name"] == name:
            path = cfg.cache_dir() / app["id"].lower() / name
            return install_zip(app, path, item["tag"], asset=name.split("__", 1)[1], cache=False)
    raise UpdateError("Cached file not found.")


def _cache_valid(path, asset):
    if asset.get("size") and path.stat().st_size != asset["size"]:
        return None
    digest = asset.get("digest") or ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    if digest.startswith("sha256:") and h.hexdigest().lower() != digest[7:].lower():
        return None
    return h.hexdigest()


# ---------------------------------------------------------------- import
_VERSION_IN_NAME = re.compile(r"v?\d+(?:\.\d+)+[\w.+-]*", re.IGNORECASE)


def _norm(name):
    """'FigCraft_Web_' / 'figcraft-web-' / 'figcraft' -> 'figcraft'"""
    n = re.sub(r"[^a-z0-9]+", "", str(name).lower())
    return n[:-3] if n.endswith("web") and len(n) > 3 else n


def match_app(filename, apps):
    """'pdfcraft-web-v1.2.0.zip' -> (app, 'v1.2.0'). Longest folder_prefix wins, then the
    same name with other punctuation/case. Release patterns are deliberately NOT used:
    a loose pattern like '.*web.*' would swallow unrelated files."""
    stem = filename[:-4] if filename.lower().endswith(".zip") else filename
    best = None
    for app in apps:
        prefix = str(app.get("folder_prefix", ""))
        if (prefix and stem.lower().startswith(prefix.lower()) and len(stem) > len(prefix)
                and (best is None or len(prefix) > len(best[0]["folder_prefix"]))):
            best = (app, stem[len(prefix):])
    if best and cfg.TAG_RE.match(best[1]):
        return best
    # Same name with different punctuation/case ("FigCraft_Web_2.0.zip" vs app "figcraft"):
    # it is the same app, so it must not become a duplicate.
    det = detect_app(filename)
    if det:
        wanted = _norm(det["folder_prefix"])
        for app in apps:
            if wanted in (_norm(app.get("id", "")), _norm(app.get("folder_prefix", ""))):
                return app, det["tag"]
    return None


# ---------------------------------------------------------------- automatic recognition
# "<name><sep><version>[.zip]" is enough to define an app: pdfcraft-web-v1.2.0.zip ->
# app "pdfcraft", folder prefix "pdfcraft-web-", version "v1.2.0".
_DETECT = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*?[A-Za-z0-9])?)(?P<sep>[-_.])"
    r"(?P<tag>(?:[vV]\d+(?:\.\d+)*|\d+(?:\.\d+)+)(?:[-+_.]?[A-Za-z0-9][A-Za-z0-9._+-]*)?)$")


def detect_app(filename):
    """Read an app definition out of a file/folder name, or return None."""
    stem = filename[:-4] if filename.lower().endswith(".zip") else filename
    m = _DETECT.match(stem)
    if not m or not re.search("[A-Za-z]", m.group("name")) or not cfg.TAG_RE.match(m.group("tag")):
        return None
    name, prefix = m.group("name"), m.group("name") + m.group("sep")
    base = re.sub(r"[-_.]web$", "", name, flags=re.IGNORECASE) or name
    app_id = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:40]
    if app_id in cfg.RESERVED_IDS:
        app_id += "-app"
    if not cfg.ID_RE.match(app_id) or len(prefix) > 60:
        return None
    return {"id": app_id, "title": " ".join(w.capitalize() for w in re.split(r"[-_.]+", app_id)),
            "folder_prefix": prefix, "tag": m.group("tag"),
            "asset_pattern": "^" + re.escape(prefix) + r".*\.zip$"}


def prefix_conflict(prefix, apps):
    """The app whose prefix is a different prefix of (or starts with) this one, if any."""
    mine = prefix.lower()
    for a in apps:
        theirs = str(a.get("folder_prefix", "")).lower()
        if theirs and theirs != mine and (mine.startswith(theirs) or theirs.startswith(mine)):
            return a
    return None


def unique_id(base, taken):
    app_id, n = base, 2
    while app_id in taken:
        app_id = "%s-%d" % (base[:36], n)
        n += 1
    return app_id


def register_detected(det):
    """Add a detected app to apps.json (or return the one that already has this prefix)."""
    out = {}

    def mutate(apps):
        for a in apps:
            if str(a.get("folder_prefix", "")).lower() == det["folder_prefix"].lower():
                out["app"] = a
                return
        clash = prefix_conflict(det["folder_prefix"], apps)
        if clash:
            raise UpdateError("folder prefix '%s' overlaps with app '%s'" % (det["folder_prefix"], clash.get("id")))
        taken = {str(a.get("id", "")).lower() for a in apps}
        new = {"id": unique_id(det["id"], taken), "title": det["title"],
               "folder_prefix": det["folder_prefix"], "repo": "",
               "asset_pattern": det["asset_pattern"], "index_path": "index.html",
               "description": "", "icon": "", "enabled": True, "prerelease": False,
               "auto_update": False}
        apps.append(new)
        out["app"] = new

    cfg.update_apps(mutate)
    return out["app"]


def resolve_app(filename, create=True):
    """Existing app by name, else (if allowed) a brand-new app read from the name.
    Returns (app, tag, created) or None."""
    apps = [a for a in cfg.load_config()["apps"] if a.get("enabled", True) and a.get("id")
            and a.get("folder_prefix")]
    hit = match_app(filename, apps)
    if hit:
        return hit[0], hit[1], False
    det = detect_app(filename) if create else None
    if det is None:
        return None
    app = register_detected(det)
    say("New app recognised from the file name: %s (%s)" % (app["id"], app["folder_prefix"]))
    return app, det["tag"], True


def _collect(paths):
    """Expand files/folders into zips and already-extracted app folders."""
    found = []
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_file() and p.suffix.lower() == ".zip":
            found.append(p)
        elif p.is_dir():
            found.extend(sorted(p.rglob("*.zip")))
            found.extend(sorted(c for c in p.iterdir() if c.is_dir()))
            if (p / "index.html").is_file():
                found.append(p)
        else:
            say("Skipped (not a zip or folder):", p)
    return found


def import_paths(paths, app_id=None, create=None):
    """Install files you already downloaded (zips or extracted folders) - no download.

    Newer-than-active versions are activated; older ones are installed only while they
    fit in `backup_count`, but every zip is cached so it can be reinstalled any time."""
    config = cfg.load_config()
    apps = [a for a in config["apps"] if a.get("enabled", True) and a.get("id")
            and a.get("folder_prefix")]
    keep_n = int(config["settings"].get("backup_count", 3)) + 1
    forced = find_app(apps, app_id) if app_id else None
    if create is None:
        create = bool(config["settings"].get("auto_create_apps", True))
    plan, skipped, seen, created = {}, [], set(), []

    for item in _collect(paths):
        if forced:
            stem = item.stem if item.is_file() else item.name
            pre = forced["folder_prefix"]
            tag = stem[len(pre):] if stem.lower().startswith(pre.lower()) else \
                (_VERSION_IN_NAME.search(stem) or [stem])[0]
            matched = (forced, tag) if cfg.TAG_RE.match(tag) else None
        else:
            matched = match_app(item.name, apps)
            if matched is None and create:
                det = detect_app(item.name)
                if det:
                    try:
                        app = register_detected(det)
                    except UpdateError as exc:
                        skipped.append((item, str(exc)))
                        continue
                    if app not in apps:
                        apps.append(app)
                        created.append(app["id"])
                        say("New app recognised: %s (%s)" % (app["id"], app["folder_prefix"]))
                    matched = (app, det["tag"])
        if matched is None:
            skipped.append((item, "could not read an app name and version from the name"))
            continue
        app, tag = matched
        key = (app["id"], sanitize_tag(tag))
        if key in seen:
            skipped.append((item, "duplicate of %s %s" % key))
            continue
        seen.add(key)
        plan.setdefault(app["id"], (app, []))[1].append((tag, item))

    result = {"installed": [], "cached": [], "skipped": skipped, "created": created}
    for app, entries in plan.values():
        installed_tags = [cfg.tag_of(app, f.name) for f in cfg.installed_folders(app)]
        ranked = sorted({t for t, _ in entries} | set(installed_tags),
                        key=cfg.version_key, reverse=True)
        keep = set(ranked[:keep_n])
        for tag, item in sorted(entries, key=lambda e: cfg.version_key(e[0])):  # oldest first
            try:
                if tag in keep or tag in installed_tags:
                    if item.is_dir():
                        install_dir(app, item, tag, mode="newer")
                    else:
                        install_zip(app, item, tag, asset=item.name, mode="newer")
                    result["installed"].append((app["id"], tag))
                elif item.is_file():
                    cache_store(app, item, tag, item.name)
                    say("Cached %s %s (older than the %d versions kept)." % (app["id"], tag, keep_n))
                    result["cached"].append((app["id"], tag))
                else:
                    skipped.append((item, "older than the versions kept"))
            except (UpdateError, zipfile.BadZipFile, OSError) as exc:
                skipped.append((item, describe_error(exc)))
                say("FAILED %s %s: %s" % (app["id"], tag, describe_error(exc)))
    return result


def rollback(app, tag=None):
    root = cfg.root_dir()
    if tag:
        name = app["folder_prefix"] + sanitize_tag(tag)
        if not (root / name).is_dir():
            raise UpdateError("Version %s is not installed." % tag)
    else:
        state = cfg.load_state().get(app["id"].lower(), {})
        current = cfg.active_folder(app)
        candidates = [h for h in reversed(state.get("history", []))
                      if (root / h).is_dir() and (current is None or h != current.name)]
        if not candidates:
            raise UpdateError("No previous version to roll back to.")
        name = candidates[0]
    activate(app, name)
    say("Active version is now:", cfg.tag_of(app, name))


# ---------------------------------------------------------------- GitHub flow
def choose(items, describe):
    if not items:
        raise UpdateError("No available options.")
    for i, item in enumerate(items, 1):
        say("%d. %s" % (i, describe(item)))
    while True:
        answer = input("Select number (0 to cancel): ").strip()
        if answer == "0":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(items):
            return items[int(answer) - 1]
        say("Invalid selection.")


def update_app(app, tag=None, latest=False, prerelease=None):
    if not app.get("repo"):
        raise UpdateError("%s has no 'repo' in apps.json." % app["id"])
    if prerelease is None:
        prerelease = bool(app.get("prerelease", False))
    pattern = re.compile(app.get("asset_pattern", r".*\.zip$"), re.IGNORECASE)

    say("\n" + "=" * 55)
    say("Updating: %s  (%s)" % (app["title"], app["repo"]))
    say("=" * 55)

    interactive = not (tag or latest)
    if tag:
        release = get_release_by_tag(app["repo"], tag)
    else:
        releases = get_releases(app["repo"], prerelease)
        if not releases:
            raise UpdateError("No releases found.")
        release = next(
            (r for r in releases
             if any(pattern.fullmatch(a["name"]) for a in r.get("assets", []))),
            releases[0],
        ) if latest else choose(
            releases,
            lambda r: "%s %s" % (r.get("tag_name"),
                                 "[Pre-release]" if r.get("prerelease") else ""))
        if release is None:
            return

    assets = [a for a in release.get("assets", []) if pattern.fullmatch(a["name"])]
    if not assets:
        names = ", ".join(a["name"] for a in release.get("assets", [])) or "(none)"
        raise UpdateError("No asset matches asset_pattern. Release assets: " + names)
    if interactive and len(assets) > 1:
        asset = choose(assets, lambda a: "%s (%.2f MB)" % (a["name"], a["size"] / 1048576))
        if asset is None:
            return
    else:
        asset = assets[0]
        if len(assets) > 1:
            say("Several assets match; using", asset["name"])

    tag_name = release["tag_name"]
    cached = cache_file(app, tag_name, asset["name"])
    if cached.is_file():
        sha = _cache_valid(cached, asset)
        if sha:
            say("Using the cached copy of %s - nothing to download." % asset["name"])
            install_zip(app, cached, tag_name, asset["name"], sha, cache=False)
            return
        cached.unlink(missing_ok=True)  # stale or corrupt: fetch it again

    say("Downloading %s (%.2f MB)" % (asset["name"], asset["size"] / 1048576))
    with tempfile.TemporaryDirectory(dir=_downloads()) as tmp:
        zip_file = Path(tmp) / "release.zip"
        sha = download(asset, zip_file)
        install_zip(app, zip_file, release["tag_name"], asset["name"], sha)


def release_list(app):
    """Releases of an app's repo with the assets matching its asset_pattern."""
    pattern = re.compile(app.get("asset_pattern", r".*\.zip$"), re.IGNORECASE)
    out = []
    for r in get_releases(app["repo"], bool(app.get("prerelease", False))):
        assets = [{"name": a["name"], "size": a.get("size", 0)}
                  for a in r.get("assets", []) if pattern.fullmatch(a["name"])]
        out.append({"tag": r.get("tag_name", ""), "prerelease": bool(r.get("prerelease")),
                    "published": r.get("published_at"), "assets": assets})
    return out


def check_updates(apps, prerelease=None):
    state = cfg.load_state()
    outdated = 0
    for app in apps:
        if not app.get("repo"):
            continue
        entry = state.get(app["id"].lower(), {})
        current = entry.get("installed_version")
        if not current:
            folder = cfg.active_folder(app, state)
            current = cfg.tag_of(app, folder.name) if folder else "(not installed)"
        try:
            releases = get_releases(
                app["repo"],
                bool(app.get("prerelease")) if prerelease is None else prerelease)
        except urllib.error.URLError as exc:
            say("%-12s ERROR: %s" % (app["id"], exc))
            continue
        newest = releases[0]["tag_name"] if releases else "(none)"
        if newest != current and releases:
            outdated += 1
            say("%-12s %s -> %s   UPDATE AVAILABLE" % (app["id"], current, newest))
        else:
            say("%-12s %s   up to date" % (app["id"], current))
    return outdated


def list_installed(apps):
    state = cfg.load_state()
    for app in apps:
        folders = cfg.installed_folders(app)
        active = cfg.active_folder(app, state)
        say("%s (%s)" % (app["title"], app["id"]))
        if not folders:
            say("   (not installed)")
        for f in folders:
            say("   %s %s" % ("*" if f == active else " ", cfg.tag_of(app, f.name)))


# ---------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(prog="updater",
                                description="Install and update Craft apps.")
    p.add_argument("--list", action="store_true", help="show installed versions")
    p.add_argument("--check", action="store_true",
                   help="compare with GitHub; exit code 10 if updates exist")
    p.add_argument("--app", help="app id from apps.json")
    p.add_argument("--all", action="store_true", help="apply to every enabled app")
    p.add_argument("--latest", action="store_true", help="install the newest release")
    p.add_argument("--tag", help="release tag (or version label with --from-zip/--rollback)")
    p.add_argument("--from-zip", metavar="FILE", help="install from a local zip (offline)")
    p.add_argument("--rollback", action="store_true", help="re-activate the previous version")
    p.add_argument("--import", dest="import_paths", nargs="+", metavar="PATH",
                   help="install files you already downloaded (zips / folders), no download")
    p.add_argument("--localize", action="store_true",
                   help="download the internet resources (CDN files, web fonts) the active version "
                        "of --app (default: every app) loads, and use local copies")
    p.add_argument("--no-create", action="store_true",
                   help="with --import: do not create apps from unknown file names")
    p.add_argument("--prerelease", action="store_true", help="include pre-releases")
    return p


def find_app(apps, app_id):
    for app in apps:
        if app["id"].lower() == app_id.lower():
            return app
    raise UpdateError("Unknown app '%s'. Known: %s" % (
        app_id, ", ".join(a["id"] for a in apps)))


def main(argv=None):
    args = build_parser().parse_args(argv)
    apps = [a for a in cfg.load_config()["apps"]
            if a.get("enabled", True) and a.get("id") and a.get("folder_prefix")]
    prerelease = True if args.prerelease else None

    try:
        if args.list:
            list_installed(apps)
            return 0
        if args.check:
            return 10 if check_updates(apps, prerelease) else 0

        if args.localize:
            for target in ([find_app(apps, args.app)] if args.app else apps):
                active = cfg.active_folder(target)
                if active is None:
                    continue
                say("Localizing %s %s ..." % (target["id"], cfg.tag_of(target, active.name)))
                result = localize.localize_folder(active, say)
                if not result["files_changed"] and not result["failed"]:
                    say("  nothing to localize.")
            return 0

        if args.import_paths:
            result = import_paths(args.import_paths, args.app, create=False if args.no_create else None)
            say("\nImported: %d installed, %d cached only, %d skipped; %d new app(s): %s" % (
                len(result["installed"]), len(result["cached"]), len(result["skipped"]),
                len(result["created"]), ", ".join(result["created"]) or "-"))
            for path, why in result["skipped"]:
                say("  skipped %s: %s" % (path, why))
            return 0 if result["installed"] or result["cached"] else 1

        if args.latest and args.all:
            for app in apps:
                if app.get("repo"):
                    try:
                        update_app(app, latest=True, prerelease=prerelease)
                    except UpdateError as exc:
                        say("%s: %s" % (app["id"], exc))
            return 0

        if args.app:
            app = find_app(apps, args.app)
        elif args.from_zip or args.rollback or args.latest or args.tag:
            raise UpdateError("--app is required with this option.")
        else:  # interactive
            app = choose([a for a in apps if a.get("repo")],
                         lambda a: "%s (%s)" % (a["title"], a["repo"]))
            if app is None:
                return 0

        if args.rollback:
            rollback(app, args.tag)
        elif args.from_zip:
            zip_path = Path(args.from_zip)
            if not zip_path.is_file():
                raise UpdateError("File not found: %s" % zip_path)
            tag = args.tag or re.sub(r"\.zip$", "", zip_path.name, flags=re.I)
            prefix = app["folder_prefix"]
            if not args.tag and tag.lower().startswith(prefix.lower()):
                tag = tag[len(prefix):]
            install_zip(app, zip_path, tag)
        else:
            update_app(app, tag=args.tag, latest=args.latest, prerelease=prerelease)
        return 0

    except (UpdateError, urllib.error.URLError) as exc:
        say("\nFAILED:", describe_error(exc))
    except KeyboardInterrupt:
        say("\nCancelled.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

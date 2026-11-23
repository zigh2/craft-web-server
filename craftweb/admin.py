"""Admin dashboard: authenticated JSON API + static single-page UI under /admin/."""
import hmac
import http.cookies
import json
import logging
import os
import platform
import re
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import __version__
from . import config as cfg
from . import diagnose, inbox, localize, pki, portmux, scheduler, security, updater

STATIC_DIR = Path(__file__).parent / "dashboard"
STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "app.css": "text/css; charset=utf-8",
    "app.js": "text/javascript; charset=utf-8",
    "theme.js": "text/javascript; charset=utf-8",
    "favicon.svg": "image/svg+xml",
}
COOKIE = "craftweb_sid"
STARTED = time.time()
LOG = logging.getLogger("craftweb")

# Applied to every /admin response (the dashboard has no inline script or style).
ADMIN_HEADERS = [
    ("Content-Security-Policy",
     "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
     "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
]

SESSIONS = security.Sessions()
LIMITER = security.LoginLimiter()
JOBS = {}
_jobs_lock = threading.Lock()
_rel_cache = {}
_du = {"at": 0.0, "bytes": 0, "key": None}


def reset():
    """Forget sessions, throttling and cached data (used by the tests)."""
    global SESSIONS, LIMITER
    SESSIONS = security.Sessions()
    LIMITER = security.LoginLimiter()
    JOBS.clear()
    _rel_cache.clear()
    _du["at"] = 0.0


class ApiError(Exception):
    def __init__(self, status, message, code="error", headers=None):
        super().__init__(message)
        self.status, self.message, self.code, self.headers = status, message, code, headers


class Ctx:
    def __init__(self, h, ip, session, query, settings):
        self.h, self.ip, self.session = h, ip, session
        self.query, self.settings = query, settings

    def json(self, limit=65536):
        try:
            length = int(self.h.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > limit:
            raise ApiError(400, "Invalid request body", "bad_request")
        try:
            data = json.loads(self.h.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "Invalid JSON", "bad_request")
        if not isinstance(data, dict):
            raise ApiError(400, "JSON object expected", "bad_request")
        return data

    def arg(self, name):
        return (self.query.get(name) or [""])[0]


# ---------------------------------------------------------------- entry point
def handle(h, method, head=False):
    h._admin = True
    ip = h.client_address[0]
    try:
        _route(h, method, head, ip)
    except ApiError as exc:
        _out(h, exc.status, {"error": exc.message, "code": exc.code}, exc.headers)
    except Exception as exc:  # never leak internals to the client
        LOG.exception("admin error: %r", exc)
        _out(h, 500, {"error": "Internal error", "code": "internal"})


def _out(h, status, obj, headers=None):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h._send(body, "application/json; charset=utf-8", False, status, headers)


def _route(h, method, head, ip):
    settings = cfg.load_config()["settings"]
    if not settings.get("admin_enabled", True):
        raise ApiError(404, "Not found", "disabled")
    if not security.ip_allowed(ip, settings.get("admin_allowed_networks")):
        security.audit(ip, "denied-network", h.path[:100])
        raise ApiError(403, "Forbidden", "forbidden")

    split = urlsplit(h.path)
    path = split.path
    if not path.startswith("/admin/api/"):
        return _static(h, path, head, method)
    if head or method not in ("GET", "POST"):
        raise ApiError(405, "Method not allowed", "method")

    name = path[len("/admin/api/"):]
    route = ROUTES.get((method, name))
    if route is None:
        raise ApiError(404, "Not found", "not_found")

    session = _session(h, ip, settings)
    if name not in PUBLIC and session is None:
        raise ApiError(401, "Authentication required", "session")
    if method == "POST":
        _check_origin(h)
        if name not in PUBLIC and not hmac.compare_digest(
                h.headers.get("X-CSRF-Token", ""), session["csrf"]):
            raise ApiError(403, "Bad CSRF token", "csrf")

    result = route(Ctx(h, ip, session, parse_qs(split.query), settings))
    headers = None
    if isinstance(result, tuple):
        result, headers = result
    _out(h, 200, result, headers)


def _static(h, path, head, method):
    if method != "GET" and not head:
        raise ApiError(405, "Method not allowed", "method")
    if path in ("/admin", "/admin/"):
        name = "index.html"
    elif path.startswith("/admin/static/"):
        name = path[len("/admin/static/"):]
    else:
        raise ApiError(404, "Not found", "not_found")
    ctype = STATIC_FILES.get(name)  # whitelist: nothing else is ever read
    if ctype is None:
        raise ApiError(404, "Not found", "not_found")
    h._send((STATIC_DIR / name).read_bytes(), ctype, head)


def _session(h, ip, settings):
    jar = http.cookies.SimpleCookie()
    try:
        jar.load(h.headers.get("Cookie", ""))
    except http.cookies.CookieError:
        return None
    morsel = jar.get(COOKIE)
    if morsel is None:
        return None
    idle = max(1, int(settings.get("admin_session_minutes", 30))) * 60
    session = SESSIONS.get(morsel.value, ip, idle)
    if session:
        session["token"] = morsel.value
    return session


def _check_origin(h):
    origin = h.headers.get("Origin")
    if origin and urlsplit(origin).netloc != h.headers.get("Host", ""):
        raise ApiError(403, "Cross-origin request blocked", "csrf")


def _tls(c):
    return bool(getattr(c.h.server, "tls", False))


# ---------------------------------------------------------------- helpers
def _cfg_app(app_id):
    for app in cfg.load_config()["apps"]:
        if str(app.get("id", "")).lower() == str(app_id).lower() and app.get("folder_prefix"):
            return app
    raise ApiError(404, "Unknown application", "no_app")


def _folder_for(app, tag):
    for folder in cfg.installed_folders(app):
        if cfg.tag_of(app, folder.name) == tag:
            return folder
    raise ApiError(404, "Version is not installed", "no_version")


def _disk_usage():
    now = time.time()
    key = str(cfg.root_dir())
    if _du["key"] == key and now - _du["at"] < 30:
        return _du["bytes"]
    total = 0
    for base, _dirs, files in os.walk(cfg.root_dir()):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    _du.update(at=now, bytes=total, key=key)
    return total


def _app_view(app, state, live, latest, ports):
    folders = cfg.installed_folders(app)
    active = cfg.active_folder(app, state)
    entry = state.get(str(app["id"]).lower(), {})
    return {
        "id": app["id"], "title": app.get("title", app["id"]),
        "description": app.get("description", ""), "icon": app.get("icon", ""),
        "repo": app.get("repo", ""), "enabled": app.get("enabled", True),
        "folder_prefix": app["folder_prefix"],
        "asset_pattern": app.get("asset_pattern", r".*\.zip$"),
        "index_path": app.get("index_path", "index.html"),
        "prerelease": bool(app.get("prerelease", False)),
        "cross_origin_isolation": bool(app.get("cross_origin_isolation", False)),
        "auto_update": bool(app.get("auto_update", False)),
        "own_port": app.get("own_port"), "port_config": app.get("port") or None,
        "port": ports.get(str(app["id"]).lower()),
        "port_error": portmux.status(str(app["id"]).lower()).get("error"),
        "latest": latest.get(app["id"]),
        "cache": updater.cache_list(app),
        "active": cfg.tag_of(app, active.name) if active else None,
        "installed_at": entry.get("installed_at") if active else None,
        "live": str(app["id"]).lower() in live,
        "versions": [{"tag": cfg.tag_of(app, f.name), "active": f == active}
                     for f in folders],
    }


def _start_job(c, title, fn):
    if not cfg.OP_LOCK.acquire(blocking=False):
        raise ApiError(409, "Another operation is running. Try again shortly.", "busy")
    job = {"id": uuid.uuid4().hex[:12], "title": title, "status": "running",
           "log": [], "started": time.time(), "finished": None}
    with _jobs_lock:
        JOBS[job["id"]] = job
        for old in sorted(JOBS.values(), key=lambda j: j["started"])[:-30]:
            JOBS.pop(old["id"], None)

    def run():
        try:
            with updater.capture(lambda line: job["log"].append(line[:500])):
                fn()
            job["status"] = "done"
        except Exception as exc:
            job["log"].append("FAILED: " + updater.describe_error(exc))
            job["status"] = "failed"
        finally:
            job["finished"] = time.time()
            cfg.OP_LOCK.release()
            security.audit(c.ip, "job-" + job["status"], title)

    threading.Thread(target=run, name="job-" + job["id"], daemon=True).start()
    return job


def _exclusive():
    class _Guard:
        def __enter__(self):
            if not cfg.OP_LOCK.acquire(blocking=False):
                raise ApiError(409, "Another operation is running. Try again shortly.", "busy")

        def __exit__(self, *exc):
            cfg.OP_LOCK.release()
    return _Guard()


# ---------------------------------------------------------------- routes
def r_session(c):
    out = {"authenticated": c.session is not None, "version": __version__,
           "setup_required": not security.password_hash()}
    if c.session:
        out["csrf"] = c.session["csrf"]
    return out


def r_login(c):
    wait = LIMITER.retry_after(c.ip)
    if wait:
        raise ApiError(429, "Too many attempts. Try again in %d s." % wait, "locked")
    stored = security.password_hash()
    if not stored:
        raise ApiError(409, "Admin password is not set.", "setup")
    password = str(c.json().get("password", ""))[:256]
    if not security.verify_password(password, stored):
        LIMITER.failure(c.ip)
        security.audit(c.ip, "login-failed")
        time.sleep(0.8)  # slows online guessing
        raise ApiError(401, "Invalid password", "bad_password")
    LIMITER.success(c.ip)
    token, csrf = SESSIONS.create(c.ip)
    security.audit(c.ip, "login")
    cookie = "%s=%s; HttpOnly; SameSite=Strict; Path=/admin" % (COOKIE, token)
    if _tls(c):
        cookie += "; Secure"
    return {"ok": True, "csrf": csrf}, [("Set-Cookie", cookie)]


def r_logout(c):
    SESSIONS.destroy(c.session["token"])
    security.audit(c.ip, "logout")
    return {"ok": True}, [("Set-Cookie",
                           "%s=; HttpOnly; SameSite=Strict; Path=/admin; Max-Age=0" % COOKIE)]


def r_overview(c):
    config = cfg.load_config()
    settings, state = config["settings"], cfg.load_state()
    live = cfg.discover_apps()
    root = cfg.root_dir()
    root.mkdir(exist_ok=True)
    usage = shutil.disk_usage(root)
    configured = {str(a["id"]).lower() for a in config["apps"] if a.get("id")}
    latest = scheduler.snapshot()
    ports = portmux.active()
    return {
        "server": {
            "name": settings["server_name"], "version": __version__,
            "python": platform.python_version(), "uptime": int(time.time() - STARTED),
            "host": settings["host"], "port": settings["port"], "tls": _tls(c),
            "apps_bytes": _disk_usage(), "disk_free": usage.free, "disk_total": usage.total,
            "allowed_networks": settings["admin_allowed_networks"],
            "session_minutes": settings["admin_session_minutes"],
            "max_upload_mb": settings["max_upload_mb"],
            "inbox_enabled": settings["inbox_enabled"],
            "admin_port": settings["admin_port"], "public_port": cfg.RUNTIME.get("port", settings["port"]),
            "isolate_apps": settings["isolate_apps"], "app_port_base": settings["app_port_base"],
            "localize_external": settings["localize_external"],
            "cross_origin_isolation": settings["cross_origin_isolation"],
            "auto_update_hours": settings["auto_update_hours"],
            "cache_enabled": settings["cache_enabled"], "cache_keep": settings["cache_keep"],
        },
        "apps": [_app_view(a, state, live, latest, ports) for a in config["apps"]
                 if a.get("id") and a.get("folder_prefix")],
        "discovered": [{"id": a["id"], "version": a["version"]}
                       for a in live.values() if a["id"] not in configured],
        "inbox": inbox.listing(),
    }


def r_releases(c):
    app = _cfg_app(c.arg("app"))
    if not app.get("repo"):
        raise ApiError(400, "No GitHub repository configured.", "no_repo")
    hit = _rel_cache.get(app["id"])
    if hit and time.time() - hit[0] < 60:
        releases = hit[1]
    else:
        try:
            releases = updater.release_list(app)
        except Exception as exc:
            raise ApiError(502, updater.describe_error(exc), "github")
        _rel_cache[app["id"]] = (time.time(), releases)
    names = {f.name for f in cfg.installed_folders(app)}
    prefix = app["folder_prefix"]
    return {"releases": [dict(r, installed=(prefix + updater.sanitize_tag(r["tag"])) in names)
                         for r in releases]}


def r_install(c):
    body = c.json()
    app = _cfg_app(body.get("app", ""))
    tag = str(body.get("tag") or "")
    if tag and not re.match(r"^[\w.+-]{1,100}$", tag):
        raise ApiError(400, "Invalid tag", "bad_request")
    if not app.get("repo"):
        raise ApiError(400, "No GitHub repository configured.", "no_repo")
    security.audit(c.ip, "install", "%s %s" % (app["id"], tag or "latest"))
    job = _start_job(c, "Install %s %s" % (app["id"], tag or "(latest)"),
                     lambda: updater.update_app(app, tag=tag or None, latest=not tag,
                                                prerelease=bool(app.get("prerelease"))))
    return {"job": job["id"]}


def r_activate(c):
    body = c.json()
    app = _cfg_app(body.get("app", ""))
    folder = _folder_for(app, str(body.get("tag", "")))
    with _exclusive():
        updater.activate(app, folder.name)
    security.audit(c.ip, "activate", "%s %s" % (app["id"], cfg.tag_of(app, folder.name)))
    return {"ok": True}


def r_delete_version(c):
    body = c.json()
    app = _cfg_app(body.get("app", ""))
    folder = _folder_for(app, str(body.get("tag", "")))
    if folder == cfg.active_folder(app):
        raise ApiError(409, "Cannot delete the active version.", "active")
    with _exclusive():
        shutil.rmtree(folder)
    _du["at"] = 0.0
    security.audit(c.ip, "delete-version", "%s %s" % (app["id"], cfg.tag_of(app, folder.name)))
    return {"ok": True}


def r_upload(c):
    app = _cfg_app(c.h.headers.get("X-App", ""))
    tag = c.h.headers.get("X-Version", "")
    if not cfg.TAG_RE.match(tag):
        raise ApiError(400, "Invalid version label.", "bad_version")
    try:
        length = int(c.h.headers.get("Content-Length") or 0)
    except ValueError:
        length = 0
    limit = int(c.settings.get("max_upload_mb", 1024)) * 1048576
    if length <= 0:
        raise ApiError(400, "Empty upload.", "bad_request")
    if length > limit:
        raise ApiError(413, "File exceeds the upload limit (%d MB)." % (limit // 1048576), "too_big")

    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(c.h.headers.get("X-Filename", "")))[:120] or "upload.zip"
    log = []
    with _exclusive():
        tmp = tempfile.NamedTemporaryFile(dir=updater._downloads(), suffix=".zip", delete=False)
        try:
            with tmp:
                remaining = length
                while remaining > 0:
                    chunk = c.h.rfile.read(min(1048576, remaining))
                    if not chunk:
                        raise ApiError(400, "Upload interrupted.", "bad_request")
                    tmp.write(chunk)
                    remaining -= len(chunk)
            if not zipfile.is_zipfile(tmp.name):
                raise ApiError(400, "Not a valid ZIP file.", "bad_zip")
            try:
                mode = "newer" if c.h.headers.get("X-Mode") == "import" else "always"
                with updater.capture(log.append):
                    updater.install_zip(app, Path(tmp.name), tag, asset=filename, mode=mode)
            except (updater.UpdateError, zipfile.BadZipFile) as exc:
                raise ApiError(400, str(exc), "install_failed")
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
    _du["at"] = 0.0
    security.audit(c.ip, "upload-install", "%s %s" % (app["id"], tag))
    return {"ok": True, "log": log}


def validate_app(data):
    if not isinstance(data, dict):
        raise ApiError(400, "Invalid application data", "bad_request")

    def text(key, maximum, default=""):
        value = str(data.get(key, default) or default).strip()
        if len(value) > maximum:
            raise ApiError(400, "%s is too long" % key, "bad_request")
        return value

    app_id = text("id", 40).lower()
    if not cfg.ID_RE.match(app_id) or app_id in cfg.RESERVED_IDS:
        raise ApiError(400, "ID must be 1-40 chars: a-z, 0-9, _ or - (not a reserved name).", "bad_id")
    prefix = text("folder_prefix", 60, app_id + "-web-")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$", prefix):
        raise ApiError(400, "Invalid folder prefix.", "bad_prefix")
    repo = text("repo", 100)
    if repo and not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo):
        raise ApiError(400, "Repository must look like owner/name.", "bad_repo")
    pattern = text("asset_pattern", 200, r".*\.zip$")
    try:
        re.compile(pattern)
    except re.error:
        raise ApiError(400, "Asset pattern is not a valid regular expression.", "bad_pattern")
    index = text("index_path", 100, "index.html")
    if (not re.match(r"^[A-Za-z0-9_./-]{1,100}$", index) or index.startswith("/")
            or ".." in index.split("/")):
        raise ApiError(400, "Invalid index path.", "bad_index")
    try:
        port = int(data.get("port") or 0)
    except (TypeError, ValueError):
        port = -1
    if port and not 1024 <= port <= 65535:
        raise ApiError(400, "Port must be between 1024 and 65535.", "bad_port")
    icon = text("icon", 8)
    if icon.isascii() and icon:
        icon = ""  # only emoji / symbols are shown as icons
    return {
        "id": app_id, "title": text("title", 60, app_id), "folder_prefix": prefix,
        "repo": repo, "asset_pattern": pattern, "index_path": index,
        "description": text("description", 200), "icon": icon,
        "enabled": bool(data.get("enabled", True)),
        "prerelease": bool(data.get("prerelease", False)),
        "auto_update": bool(data.get("auto_update", False)),
        "cross_origin_isolation": bool(data.get("cross_origin_isolation", False)),
        "own_port": bool(data.get("own_port", False)),
        "port": port,
    }


def r_app_save(c):
    body = c.json()
    data = validate_app(body.get("app"))
    original = str(body.get("original_id") or "").lower()
    settings = cfg.load_config()["settings"]
    if original:
        data["id"] = original  # the ID (URL + state key) never changes
    with _exclusive():
        def mutate(apps):
            index = next((i for i, a in enumerate(apps)
                          if str(a.get("id", "")).lower() == (original or data["id"])), None)
            if original and index is None:
                raise ApiError(404, "Unknown application", "no_app")
            if not original and index is not None:
                raise ApiError(409, "An application with this ID already exists.", "exists")
            taken = {int(cfg.RUNTIME.get("port", settings["port"])),
                     int(cfg.RUNTIME.get("admin_port", settings.get("admin_port") or 0))}
            taken |= {int(o["port"]) for o in apps if o.get("port") and str(o.get("id", "")).lower() != data["id"]}
            if data["port"] and data["port"] in taken:
                raise ApiError(409, "This port is already used.", "port_in_use")
            mine = data["folder_prefix"].lower()
            for other in apps:
                if str(other.get("id", "")).lower() == data["id"]:
                    continue
                theirs = str(other.get("folder_prefix", "")).lower()
                if theirs and (mine.startswith(theirs) or theirs.startswith(mine)):
                    raise ApiError(409, "Folder prefix overlaps with '%s'." % other.get("id"),
                                   "prefix_overlap")
            if index is None:
                apps.append(data)
            else:
                if (apps[index].get("folder_prefix") != data["folder_prefix"]
                        and cfg.installed_folders(apps[index])):
                    raise ApiError(409, "Cannot change the prefix while versions are installed.",
                                   "prefix_locked")
                apps[index].update(data)
        cfg.update_apps(mutate)
    security.audit(c.ip, "app-save", data["id"])
    portmux.wake.set()
    return {"ok": True}


def r_app_delete(c):
    body = c.json()
    app = _cfg_app(body.get("id", ""))
    with _exclusive():
        if body.get("purge"):
            for folder in cfg.installed_folders(app):
                shutil.rmtree(folder, ignore_errors=True)
        cfg.update_apps(lambda apps: apps.__setitem__(
            slice(None), [a for a in apps
                          if str(a.get("id", "")).lower() != str(app["id"]).lower()]))
        state = cfg.load_state()
        if state.pop(str(app["id"]).lower(), None) is not None:
            cfg.save_state(state)
    _du["at"] = 0.0
    security.audit(c.ip, "app-delete", "%s purge=%s" % (app["id"], bool(body.get("purge"))))
    portmux.wake.set()
    return {"ok": True}


def r_diagnose(c):
    app = _cfg_app(c.arg("app"))
    active = cfg.active_folder(app)
    if active is None:
        raise ApiError(404, "Nothing is installed for this app.", "no_version")
    result = diagnose.scan(active, app.get("index_path", "index.html"))
    settings = c.settings
    result.update(version=cfg.tag_of(app, active.name), tls=_tls(c),
                  localized=localize.summary(active),
                  own_port=str(app["id"]).lower() in portmux.active(),
                  isolation=bool(app.get("cross_origin_isolation", settings["cross_origin_isolation"])))
    return result


SETTING_KEYS = {"isolate_apps": bool, "cross_origin_isolation": bool, "localize_external": bool}


def r_https_info(c):
    data = pki.info()
    configured = bool(c.settings.get("tls_cert") and c.settings.get("tls_key"))
    data.update(active=_tls(c), configured=configured, needs_restart=configured and not _tls(c),
                public_port=cfg.RUNTIME.get("port", c.settings["port"]))
    return data


def r_https_setup(c):
    body = c.json()
    names = body.get("names") or []
    if not isinstance(names, list) or len(names) > 20:
        raise ApiError(400, "Invalid host names.", "bad_request")
    try:
        pki._split_extra(names)           # validate now, so the error is shown immediately
    except ValueError as exc:
        raise ApiError(400, str(exc), "bad_host")
    security.audit(c.ip, "https-setup", ",".join(str(n) for n in names)[:200])
    job = _start_job(c, "Set up HTTPS", lambda: pki.setup(names, renew=bool(body.get("renew")), new_ca=bool(body.get("new_ca")),
                                                     log=updater.say))
    return {"job": job["id"]}


def r_localize(c):
    app = _cfg_app(c.json().get("app", ""))
    active = cfg.active_folder(app)
    if active is None:
        raise ApiError(404, "Nothing is installed for this app.", "no_version")
    security.audit(c.ip, "localize", app["id"])
    job = _start_job(c, "Make %s offline-ready" % app["id"],
                     lambda: localize.localize_folder(active, updater.say))
    return {"job": job["id"]}


def r_settings(c):
    body = c.json()
    changes = {}
    for key, kind in SETTING_KEYS.items():
        if key in body:
            changes[key] = kind(body[key])
    if not changes:
        raise ApiError(400, "Nothing to change.", "bad_request")
    with _exclusive():
        cfg.update_settings(changes)
    security.audit(c.ip, "settings", json.dumps(changes))
    portmux.wake.set()
    return {"ok": True}


def r_check(c):
    app = _cfg_app(c.json().get("app", ""))
    if not app.get("repo"):
        raise ApiError(400, "No GitHub repository configured.", "no_repo")
    return scheduler.check_app(app)


def r_match(c):
    """Suggest (app, version) for a list of file names (used by the import dialog)."""
    names = c.json().get("names")
    if not isinstance(names, list) or len(names) > 200:
        raise ApiError(400, "Invalid request", "bad_request")
    config = cfg.load_config()
    apps = [a for a in config["apps"] if a.get("enabled", True) and a.get("id") and a.get("folder_prefix")]
    taken = {str(a.get("id", "")).lower() for a in config["apps"]}
    planned, out = {}, []
    for name in names:
        name = str(name)[:200]
        hit = updater.match_app(name, apps)
        if hit:
            out.append({"name": name, "app": hit[0]["id"], "tag": hit[1], "suggest": None})
            continue
        det = updater.detect_app(name)
        suggest = None
        if det and config["settings"].get("auto_create_apps", True) \
                and not updater.prefix_conflict(det["folder_prefix"], config["apps"]):
            key = det["folder_prefix"].lower()
            if key not in planned:
                app_id = updater.unique_id(det["id"], taken)
                taken.add(app_id)
                planned[key] = {"id": app_id, "title": det["title"],
                                "folder_prefix": det["folder_prefix"],
                                "asset_pattern": det["asset_pattern"]}
            suggest = planned[key]
        out.append({"name": name, "app": "", "tag": det["tag"] if det else "", "suggest": suggest})
    return {"matches": out}


def r_cache_install(c):
    body = c.json()
    app = _cfg_app(body.get("app", ""))
    name = str(body.get("name", ""))
    security.audit(c.ip, "install-cached", "%s %s" % (app["id"], name))
    job = _start_job(c, "Install %s from cache" % app["id"],
                     lambda: updater.install_from_cache(app, name))
    return {"job": job["id"]}


def r_cache_delete(c):
    body = c.json()
    app = _cfg_app(body.get("app", ""))
    try:
        with _exclusive():
            updater.cache_delete(app, str(body.get("name", "")))
    except updater.UpdateError as exc:
        raise ApiError(404, str(exc), "no_cache")
    security.audit(c.ip, "cache-delete", "%s %s" % (app["id"], body.get("name")))
    return {"ok": True}


def _job_view(job, full):
    out = {k: job[k] for k in ("id", "title", "status", "started", "finished")}
    out["log"] = job["log"][-300:] if full else []
    return out


def r_job(c):
    job = JOBS.get(c.arg("id"))
    if job is None:
        raise ApiError(404, "Unknown job", "no_job")
    return {"job": _job_view(job, True)}


def r_jobs(c):
    jobs = sorted(JOBS.values(), key=lambda j: j["started"], reverse=True)
    return {"jobs": [_job_view(j, True) for j in jobs]}


def r_audit(c):
    return {"entries": security.read_audit(200)}


def r_password(c):
    body = c.json()
    stored = security.password_hash()
    if not stored or not security.verify_password(str(body.get("current", ""))[:256], stored):
        security.audit(c.ip, "password-change-failed")
        raise ApiError(401, "Current password is wrong.", "bad_password")
    try:
        security.set_password(str(body.get("new", ""))[:256])
    except ValueError as exc:
        raise ApiError(400, str(exc), "weak_password")
    SESSIONS.destroy_others(c.session["token"])
    security.audit(c.ip, "password-changed")
    return {"ok": True}


ROUTES = {
    ("GET", "session"): r_session, ("POST", "login"): r_login, ("POST", "logout"): r_logout,
    ("GET", "overview"): r_overview, ("GET", "releases"): r_releases,
    ("POST", "install"): r_install, ("POST", "activate"): r_activate,
    ("POST", "delete-version"): r_delete_version, ("POST", "upload"): r_upload,
    ("POST", "app"): r_app_save, ("POST", "app-delete"): r_app_delete,
    ("GET", "job"): r_job, ("GET", "jobs"): r_jobs, ("GET", "audit"): r_audit,
    ("POST", "password"): r_password,
    ("POST", "check"): r_check, ("POST", "match"): r_match,
    ("GET", "diagnose"): r_diagnose, ("POST", "settings"): r_settings,
    ("POST", "localize"): r_localize,
    ("GET", "https-info"): r_https_info, ("POST", "https-setup"): r_https_setup,
    ("POST", "cache-install"): r_cache_install, ("POST", "cache-delete"): r_cache_delete,
}
PUBLIC = {"session", "login"}

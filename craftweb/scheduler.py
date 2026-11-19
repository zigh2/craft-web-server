"""Background checks against GitHub, with optional automatic installation."""
import logging
import threading
import time

from . import config as cfg
from . import security, updater

LOG = logging.getLogger("craftweb")
LATEST = {}  # app id -> {"tag", "update", "checked", "error"}
_lock = threading.Lock()
wake = threading.Event()


def installed_tag(app):
    folder = cfg.active_folder(app)
    return cfg.tag_of(app, folder.name) if folder else None


def check_app(app, install=False):
    """Look up the newest release. Auto-install only when that release is not
    already on disk, so a deliberate rollback is never undone."""
    entry = {"tag": None, "update": False, "checked": int(time.time()), "error": None}
    try:
        newest = next((r for r in updater.release_list(app) if r["assets"]), None)
    except Exception as exc:  # offline networks are normal here
        entry["error"] = updater.describe_error(exc)
        with _lock:
            LATEST[app["id"]] = entry
        return entry
    if newest:
        entry["tag"] = newest["tag"]
        entry["update"] = newest["tag"] != installed_tag(app)
        on_disk = any(cfg.tag_of(app, f.name) == updater.sanitize_tag(newest["tag"])
                      for f in cfg.installed_folders(app))
        if install and entry["update"] and not on_disk:
            _auto_install(app, newest["tag"])
            entry["update"] = newest["tag"] != installed_tag(app)
    with _lock:
        LATEST[app["id"]] = entry
    return entry


def _auto_install(app, tag):
    if not cfg.OP_LOCK.acquire(blocking=False):
        return  # a manual operation is running; try again next cycle
    try:
        lines = []
        with updater.capture(lines.append):
            updater.update_app(app, tag=tag, prerelease=bool(app.get("prerelease")))
        security.audit("auto-update", "auto-update", "%s %s" % (app["id"], tag))
        LOG.info("auto-updated %s to %s", app["id"], tag)
    except Exception as exc:
        security.audit("auto-update", "auto-update-failed",
                       "%s %s: %s" % (app["id"], tag, updater.describe_error(exc)))
        LOG.warning("auto-update of %s failed: %s", app["id"], updater.describe_error(exc))
    finally:
        cfg.OP_LOCK.release()


def check_all():
    for app in cfg.load_config()["apps"]:
        if app.get("enabled", True) and app.get("id") and app.get("repo") and app.get("folder_prefix"):
            check_app(app, install=bool(app.get("auto_update")))


def snapshot():
    with _lock:
        return {k: dict(v) for k, v in LATEST.items()}


def start():
    def loop():
        time.sleep(20)  # let the server settle first
        while True:
            try:
                hours = float(cfg.load_config()["settings"].get("auto_update_hours", 6))
            except (TypeError, ValueError):
                hours = 6
            if hours > 0:
                try:
                    check_all()
                except Exception:
                    LOG.exception("update check failed")
            wake.wait(max(hours, 1) * 3600 if hours > 0 else 300)
            wake.clear()

    threading.Thread(target=loop, name="scheduler", daemon=True).start()

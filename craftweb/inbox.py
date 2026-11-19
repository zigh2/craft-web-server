"""Drop folder: put <folder_prefix><version>.zip into inbox/ and it is installed
automatically (handy on networks without internet access)."""
import shutil
import threading
import time

from . import config as cfg
from . import security, updater


def inbox_dir():
    return cfg.base_dir() / "inbox"


def match_app(filename):
    apps = [a for a in cfg.load_config()["apps"]
            if a.get("enabled", True) and a.get("id") and a.get("folder_prefix")]
    return updater.match_app(filename, apps)


def _fail(path, reason):
    failed = inbox_dir() / "failed"
    failed.mkdir(parents=True, exist_ok=True)
    target = failed / path.name
    shutil.move(str(path), str(target))
    target.with_name(path.name + ".txt").write_text(reason + "\n", encoding="utf-8")
    security.audit("inbox", "inbox-failed", "%s: %s" % (path.name, reason))


def process_once(sizes):
    folder = inbox_dir()
    folder.mkdir(exist_ok=True)
    files = sorted(folder.glob("*.zip"))
    for gone in set(sizes) - {f.name for f in files}:
        sizes.pop(gone, None)
    for path in files:
        size = path.stat().st_size
        if sizes.get(path.name) != size:  # still being copied - wait one more tick
            sizes[path.name] = size
            continue
        matched = match_app(path.name)
        if matched is None:
            _fail(path, "File name must be <folder_prefix><version>.zip of a configured app.")
            continue
        if not cfg.OP_LOCK.acquire(blocking=False):
            return  # another operation is running; retry next tick
        try:
            app, tag = matched
            lines = []
            with updater.capture(lines.append):
                updater.install_zip(app, path, tag)
            path.unlink()
            security.audit("inbox", "inbox-install", "%s %s" % (app["id"], tag))
        except Exception as exc:  # keep the watcher alive no matter what
            _fail(path, updater.describe_error(exc))
        finally:
            cfg.OP_LOCK.release()


def start():
    def loop():
        sizes = {}
        while True:
            try:
                process_once(sizes)
            except Exception:
                pass
            try:
                delay = max(2, int(cfg.load_config()["settings"]["inbox_poll_seconds"]))
            except (TypeError, ValueError):
                delay = 5
            time.sleep(delay)

    threading.Thread(target=loop, name="inbox", daemon=True).start()


def listing():
    folder = inbox_dir()
    pending = sorted(p.name for p in folder.glob("*.zip")) if folder.is_dir() else []
    failed = sorted(p.name for p in (folder / "failed").glob("*.zip")) \
        if (folder / "failed").is_dir() else []
    return {"path": str(folder), "pending": pending, "failed": failed}

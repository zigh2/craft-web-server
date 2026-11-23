"""Per-app listeners. An app that expects to live at the site root ("/assets/...") runs on
its own port, where every absolute path just works and its storage/service workers are
isolated from the other apps. Listeners follow apps.json live (no restart needed)."""
import logging
import threading

from . import config as cfg

LOG = logging.getLogger("craftweb")
_lock = threading.Lock()
_running = {}   # app id -> (port, server)
STATUS = {}     # app id -> {"port": int, "error": str | None}
wake = threading.Event()


def active():
    """{app id: port} of the listeners that are really bound."""
    with _lock:
        return {k: v[0] for k, v in _running.items()}


def status(app_id):
    with _lock:
        return dict(STATUS.get(app_id) or {})


def reconcile(factory):
    desired = cfg.desired_ports()
    with _lock:
        for app_id in list(_running):
            port, server = _running[app_id]
            if desired.get(app_id) != port:
                server.shutdown()
                server.server_close()
                del _running[app_id]
                LOG.info("app %s: port %d closed", app_id, port)
        for app_id, port in desired.items():
            if app_id in _running:
                continue
            try:
                server = factory(port, app_id)
            except OSError as exc:
                previous = STATUS.get(app_id) or {}
                if previous.get("port") != port or not previous.get("error"):
                    LOG.warning("app %s: cannot listen on port %d: %s", app_id, port, exc)
                STATUS[app_id] = {"port": port, "error": str(exc)}
                continue
            threading.Thread(target=server.serve_forever, name="app-" + app_id, daemon=True).start()
            _running[app_id] = (port, server)
            STATUS[app_id] = {"port": port, "error": None}
            LOG.info("app %s: listening on its own port %d", app_id, port)
        for app_id in list(STATUS):
            if app_id not in desired:
                del STATUS[app_id]


def start(factory):
    def loop():
        while True:
            try:
                reconcile(factory)
            except Exception:
                LOG.exception("port manager failed")
            wake.wait(3)
            wake.clear()

    threading.Thread(target=loop, name="portmux", daemon=True).start()


def stop_all():
    with _lock:
        for port, server in _running.values():
            server.shutdown()
            server.server_close()
        _running.clear()
        STATUS.clear()

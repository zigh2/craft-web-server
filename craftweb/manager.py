"""The Manager: a small control panel for the person who runs the server.

It works when the server is not installed or not running, so it is a separate program from the
dashboard: install the server (background service + start at boot + firewall), start/stop/restart
it, check that everything works, read the logs and update the server itself.

It listens on 127.0.0.1 only and may run elevated, so it is locked down: a secret in the link it
opens, Host and Origin checks, a CSRF token, a strict CSP, and it closes itself when idle."""
import hmac
import http.cookies
import json
import logging
import os
import secrets
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import __version__
from . import config as cfg
from . import security, selfupdate, service, syscheck

LOG = logging.getLogger("craftweb")
UI_DIR = Path(__file__).parent / "manager_ui"
STATIC = {"index.html": "text/html; charset=utf-8", "manager.css": "text/css; charset=utf-8",
          "manager.js": "text/javascript; charset=utf-8", "favicon.svg": "image/svg+xml"}
HEADERS = [
    ("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                               "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    ("X-Frame-Options", "DENY"), ("Referrer-Policy", "no-referrer"), ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
]
IDLE_SECONDS = 3600
COOKIE = "craftweb_manager"


class State:
    def __init__(self, port):
        self.port = port
        self.token = secrets.token_urlsafe(24)       # in the link the program opens
        self.session = secrets.token_urlsafe(32)     # cookie, set when the link is opened
        self.csrf = secrets.token_urlsafe(24)
        self.last = time.time()
        self.jobs = {}
        self.update = None
        self.lock = threading.Lock()


class ApiError(Exception):
    def __init__(self, status, message, code="error"):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code


# ---------------------------------------------------------------- jobs
def start_job(state, title, fn):
    if not state.lock.acquire(blocking=False):
        raise ApiError(409, "Another action is still running.", "busy")
    job = {"id": uuid.uuid4().hex[:10], "title": title, "status": "running", "log": [], "started": time.time()}
    state.jobs[job["id"]] = job
    for old in sorted(state.jobs.values(), key=lambda j: j["started"])[:-15]:
        state.jobs.pop(old["id"], None)

    def run():
        try:
            fn(lambda line: job["log"].append(str(line)[:500]))
            job["status"] = "done"
        except Exception as exc:  # noqa: BLE001 - shown to the person in the log
            job["log"].append("FAILED: %s" % exc)
            job["status"] = "failed"
            LOG.warning("manager action %r failed: %s", title, exc)
        finally:
            state.lock.release()

    threading.Thread(target=run, daemon=True).start()
    return job


# ---------------------------------------------------------------- actions
def do_install(log, password=None):
    if not security.password_hash():
        if not password:
            raise ValueError("Choose a dashboard password first (at least %d characters)." % security.MIN_PASSWORD)
        security.set_password(password)
        log("Dashboard password saved.")
    service.install(log)


def do_update(log):
    """Download + verify + test the new version; the watchdog (or we) switch to it."""
    info = selfupdate.check()
    version = selfupdate.stage(info, log)
    if service.supervisor_alive():
        log("Restarting the server to finish the update ...")
        service.set_flag("restart")
        service.wait_until(lambda: service.health() is None or not selfupdate.staged(), 30)
        service.wait_until(lambda: service.health() is not None, 60)
    else:
        selfupdate.apply_staged(log)
        log("Updated to %s. Start the server from the Manager." % version)


def relaunch_as_admin():
    """Windows: start this program again with the UAC prompt, then the caller quits."""
    if os.name != "nt":
        raise RuntimeError("Run this program with sudo.")
    import ctypes
    params = " ".join('"%s"' % a for a in (sys.argv[1:] if getattr(sys, "frozen", False) else ["-m", "craftweb", "manager"]))
    target = sys.executable
    if ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1) <= 32:
        raise RuntimeError("The administrator prompt was cancelled.")


def open_local(what):
    settings = cfg.load_config()["settings"]
    scheme = "https" if settings.get("tls_cert") else "http"
    if what == "dashboard":
        port = int(settings.get("admin_port") or settings["port"])
        webbrowser.open("%s://127.0.0.1:%d/admin/" % (scheme, port))
    elif what == "apps":
        webbrowser.open("%s://127.0.0.1:%d/" % (scheme, int(settings["port"])))
    elif what in ("data", "logs"):
        path = cfg.base_dir() / ("logs" if what == "logs" else "")
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))      # noqa: S606 - a folder we computed ourselves
        else:
            service.run(["xdg-open", str(path)], timeout=10)
    else:
        raise ApiError(400, "Unknown target.", "bad_request")


def status(state):
    st = service.status()
    ip = syscheck.lan_ip()
    scheme = "https" if st["tls"] else "http"
    st.update(version=__version__, update=state.update, lan_ip=ip, kind=selfupdate.install_kind(),
              apps_url="%s://%s:%d/" % (scheme, ip or "localhost", st["port"]),
              dashboard_url="%s://%s:%d/admin/" % (scheme, ip or "localhost", st["admin_port"] or st["port"]),
              staged=(selfupdate.staged() or {}).get("version"), command_hint=cfg.cli("manager"))
    return st


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "CraftManager/" + __version__
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        pass

    @property
    def state(self):
        return self.server.state

    def _send(self, status, body, ctype, extra=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in HEADERS + list(extra):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, obj, extra=()):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", extra)

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host in ("127.0.0.1:%d" % self.state.port, "localhost:%d" % self.state.port)

    def _authed(self):
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except http.cookies.CookieError:
            return False
        morsel = jar.get(COOKIE)
        return bool(morsel) and hmac.compare_digest(morsel.value, self.state.session)

    def _handle(self, method):
        self.state.last = time.time()
        try:
            if not self._host_ok():                       # DNS-rebinding protection
                raise ApiError(403, "Forbidden", "host")
            split = urlsplit(self.path)
            query = parse_qs(split.query)
            if method == "GET" and split.path == "/" and query.get("t"):
                if not hmac.compare_digest(query["t"][0], self.state.token):
                    raise ApiError(403, "Forbidden", "token")
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", "%s=%s; HttpOnly; SameSite=Strict; Path=/" % (COOKIE, self.state.session))
                self.send_header("Content-Length", "0")
                for k, v in HEADERS:
                    self.send_header(k, v)
                self.end_headers()
                return
            if not self._authed():
                raise ApiError(403, "Open the Manager from the program: the link it opens contains a secret.", "auth")
            if split.path.startswith("/api/"):
                self._api(method, split.path[5:], query)
            elif method == "GET":
                name = "index.html" if split.path == "/" else split.path.lstrip("/")
                ctype = STATIC.get(name)
                if ctype is None:
                    raise ApiError(404, "Not found", "not_found")
                self._send(200, (UI_DIR / name).read_bytes(), ctype)
            else:
                raise ApiError(405, "Method not allowed", "method")
        except ApiError as exc:
            self._json(exc.status, {"error": exc.message, "code": exc.code})
        except Exception as exc:  # noqa: BLE001 - never leak internals
            LOG.exception("manager error: %s", exc)
            self._json(500, {"error": "Internal error", "code": "internal"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > 65536:
            raise ApiError(413, "Too large", "bad_request")
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            raise ApiError(400, "Invalid JSON", "bad_request")
        return data if isinstance(data, dict) else {}

    def _api(self, method, name, query):
        state = self.state
        if method == "POST":
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != self.headers.get("Host", ""):
                raise ApiError(403, "Cross-origin request blocked", "csrf")
            if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), state.csrf):
                raise ApiError(403, "Bad CSRF token", "csrf")
        if method == "GET" and name == "session":
            return self._json(200, {"csrf": state.csrf})
        if method == "GET" and name == "status":
            return self._json(200, status(state))
        if method == "GET" and name == "doctor":
            return self._json(200, syscheck.run_checks())
        if method == "GET" and name == "job":
            job = state.jobs.get((query.get("id") or [""])[0])
            if job is None:
                raise ApiError(404, "Unknown job", "no_job")
            return self._json(200, {"job": dict(job, log=job["log"][-300:])})
        if method == "GET" and name == "log":
            try:
                return self._json(200, {"text": syscheck.read_log((query.get("name") or ["server"])[0], 300)})
            except KeyError:
                raise ApiError(400, "Unknown log", "bad_request")
        if method != "POST":
            raise ApiError(404, "Not found", "not_found")

        body = self._body()
        if name == "action":
            action = body.get("name")
            actions = {
                "install": lambda log: do_install(log, body.get("password")),
                "uninstall": lambda log: service.uninstall(log),
                "start": lambda log: service.start(log),
                "stop": lambda log: service.stop(log),
                "restart": lambda log: service.restart(log),
                "migrate": lambda log: cfg.migrate_legacy(log),
            }
            if action not in actions:
                raise ApiError(400, "Unknown action", "bad_request")
            if action in ("install", "uninstall", "migrate") and not cfg.is_admin():
                raise ApiError(403, "Administrator rights are needed.", "need_admin")
            return self._json(200, {"job": start_job(state, action, actions[action])["id"]})
        if name == "password":
            try:
                security.set_password(str(body.get("password", ""))[:256])
            except ValueError as exc:
                raise ApiError(400, str(exc), "weak_password")
            return self._json(200, {"ok": True})
        if name == "update-check":
            info = selfupdate.check()
            state.update = {k: v for k, v in info.items() if k != "release"}
            return self._json(200, state.update)
        if name == "update":
            return self._json(200, {"job": start_job(state, "update", do_update)["id"]})
        if name == "open":
            open_local(str(body.get("what", "")))
            return self._json(200, {"ok": True})
        if name == "elevate":
            try:
                relaunch_as_admin()
            except RuntimeError as exc:
                raise ApiError(400, str(exc), "elevate")
            threading.Timer(0.5, self.server.shutdown).start()
            return self._json(200, {"ok": True})
        if name == "quit":
            threading.Timer(0.3, self.server.shutdown).start()
            return self._json(200, {"ok": True})
        raise ApiError(404, "Not found", "not_found")


def make_server(port=0):
    for candidate in ([port] if port else list(range(8099, 8121)) + [0]):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError:
            continue
    else:
        raise OSError("No free port for the Manager.")
    server.state = State(server.server_address[1])
    return server


def serve(server, open_browser=True, idle=IDLE_SECONDS, check=15):
    state = server.state
    url = "http://127.0.0.1:%d/?t=%s" % (state.port, state.token)

    def watchdog():
        while True:
            time.sleep(check)
            if time.time() - state.last > idle:
                server.shutdown()
                return
    threading.Thread(target=watchdog, daemon=True).start()
    threading.Thread(target=lambda: _first_update_check(state), daemon=True).start()
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return url


def _first_update_check(state):
    try:
        info = selfupdate.check()
        state.update = {k: v for k, v in info.items() if k != "release"}
    except Exception:  # noqa: BLE001 - optional nicety
        pass


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="manager", description="Simple control panel for the Craft Web Server.")
    parser.add_argument("--no-browser", action="store_true", help="only print the link")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    for name in ("stdout", "stderr"):                  # windowed (no console) builds have no streams
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    try:
        cfg.ensure_data_dir()
        (cfg.base_dir() / "logs").mkdir(exist_ok=True)
        logging.basicConfig(filename=str(cfg.base_dir() / "logs" / "manager.log"), level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
    except OSError:
        pass
    server = make_server(args.port)
    print("Manager: http://127.0.0.1:%d/?t=%s" % (server.state.port, server.state.token))
    serve(server, open_browser=not args.no_browser)
    return 0


def service_cli(argv):
    """craft-web-server service install|uninstall|start|stop|restart|status"""
    if not argv or argv[0] not in ("install", "uninstall", "start", "stop", "restart", "status"):
        print("usage: service install|uninstall|start|stop|restart|status")
        return 2
    action = argv[0]
    try:
        if action == "status":
            print(json.dumps(service.status(), indent=2))
        elif action == "install":
            if not security.password_hash():
                import getpass
                password = getpass.getpass("Choose the dashboard password (min %d chars): " % security.MIN_PASSWORD)
                security.set_password(password)
            service.install(print)
        else:
            getattr(service, action)(print)
    except (PermissionError, RuntimeError, ValueError) as exc:
        print("FAILED:", exc)
        return 1
    return 0



"""Static web server that publishes every installed Craft app under /<app-id>/."""
import argparse
import html
import http.cookies
import json
import logging
import logging.handlers
import mimetypes
import os
import socket
import ssl
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from . import __version__
from . import admin, inbox, localize, pki, portmux, scheduler, security
from . import config as cfg

# Windows registries often map .js to text/plain, which breaks module scripts.
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/manifest+json", ".webmanifest")
for _ext, _type in ((".woff2", "font/woff2"), (".woff", "font/woff"), (".ttf", "font/ttf"), (".otf", "font/otf")):
    mimetypes.add_type(_type, _ext)

PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@NAME@@</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #f4f6fa; font-family: Arial, sans-serif; color: #202938; }
header { padding: 38px 20px; background: #17243a; color: #fff; text-align: center; }
header h1 { margin: 0 0 10px; }
header p { color: #cbd5e1; margin: 0; }
main { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
.search { width: 100%; padding: 14px; border: 1px solid #ddd; border-radius: 10px; font-size: 16px; margin-bottom: 22px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; }
.card { display: block; text-decoration: none; color: inherit; background: #fff; padding: 22px; border-radius: 14px; box-shadow: 0 3px 12px #0000000a; transition: .2s; }
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px #00000012; }
.icon { font-size: 30px; margin-bottom: 15px; }
.title { font-weight: bold; font-size: 19px; }
.description { margin-top: 8px; color: #777; font-size: 13px; }
.version { margin-top: 14px; color: #888; font-size: 11px; direction: ltr; text-align: right; }
.open { margin-top: 15px; color: #2563eb; font-size: 14px; }
footer { text-align: center; color: #888; padding: 30px; }
</style>
</head>
<body>
<header><h1>@@NAME@@</h1><p>منصة التطبيقات المحلية</p></header>
<main>
<input id="search" class="search" placeholder="ابحث عن تطبيق..." oninput="filterApps()">
<div class="grid">@@CARDS@@</div>
</main>
<footer>Craft Apps Local Server @@VERSION@@</footer>
<script>
function filterApps() {
  const v = document.getElementById("search").value.toLowerCase();
  document.querySelectorAll(".card").forEach(c => {
    c.style.display = c.dataset.search.includes(v) ? "block" : "none";
  });
}
</script>
</body>
</html>
"""


def render_home(hostname="localhost", scheme="http"):
    apps = cfg.discover_apps()
    ports = portmux.active()
    cards = []
    for app in sorted(apps.values(), key=lambda a: a["title"].lower()):
        icon = app["icon"] if app["icon"] and not app["icon"].isascii() else "🌐"
        href = ("%s://%s:%d/" % (scheme, hostname, ports[app["id"]]) if app["id"] in ports
                else "/%s/" % quote(app["id"]))
        cards.append(
            '<a class="card" href="%s" data-search="%s">'
            '<div class="icon">%s</div>'
            '<div class="title">%s</div>'
            '<div class="description">%s</div>'
            '<div class="version">%s</div>'
            '<div class="open">فتح التطبيق ←</div></a>'
            % (
                html.escape(href, quote=True),
                html.escape(app["title"].lower(), quote=True),
                html.escape(icon),
                html.escape(app["title"]),
                html.escape(app["description"]),
                html.escape(app["version"]),
            )
        )
    name = html.escape(cfg.load_config()["settings"]["server_name"])
    body = "".join(cards) or "<p>لا توجد تطبيقات مثبّتة بعد.</p>"
    return (
        PAGE.replace("@@NAME@@", name)
        .replace("@@CARDS@@", body)
        .replace("@@VERSION@@", __version__)
    )


LOG = logging.getLogger("craftweb")


def setup_logging():
    """logs/server.log (rotating) + console. Access lines only if access_log is on."""
    LOG.setLevel(logging.INFO)
    if LOG.handlers:
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(),):
        handler.setFormatter(fmt)
        LOG.addHandler(handler)
    try:
        (cfg.base_dir() / "logs").mkdir(exist_ok=True)
        fileh = logging.handlers.RotatingFileHandler(
            cfg.base_dir() / "logs" / "server.log", maxBytes=1_000_000, backupCount=3,
            encoding="utf-8")
        fileh.setFormatter(fmt)
        LOG.addHandler(fileh)
    except OSError:
        pass


class CraftHandler(SimpleHTTPRequestHandler):
    """Public handler: serves the apps. The dashboard is NOT reachable here unless
    the operator explicitly shares the port (admin_port = 0)."""
    server_version = "CraftWeb/" + __version__
    ADMIN_ONLY = False

    def log_message(self, fmt, *args):
        if getattr(self.server, "access_log", False):
            LOG.info("%s %s", self.address_string(), fmt % args)

    def log_error(self, fmt, *args):
        if getattr(self.server, "access_log", False):
            LOG.warning("%s %s", self.address_string(), fmt % args)

    def __init__(self, *args, **kwargs):
        self._app = None  # must exist before the base class handles the request
        self._admin = False
        self._compat = False
        super().__init__(*args, directory=str(cfg.root_dir()), **kwargs)

    # -- headers shared by every response
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        if self._admin:
            self.send_header("Cache-Control", "no-store")
            for key, value in admin.ADMIN_HEADERS:
                self.send_header(key, value)
        else:
            # Versions are swapped in place: always revalidate (cheap 304s on a LAN).
            self.send_header("Cache-Control", "no-cache")
        if self._app and self._app.get("cross_origin_isolation"):
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        if self._compat:
            self.send_header("X-Craft-Compat", "root-path")  # served through the root-path fallback
        elif self._app and not getattr(self.server, "app_id", None) and self._is_document():
            # Remember the app of the last page opened: its absolute-path requests
            # ("/assets/x.js") are then served from that app (see _compat_app).
            cookie = "craft_app=%s; Path=/; SameSite=Lax; HttpOnly" % self._app["id"]
            self.send_header("Set-Cookie", cookie + ("; Secure" if getattr(self.server, "tls", False) else ""))
        super().end_headers()

    # -- routing
    def do_GET(self):
        if not self._dispatch(head=False):
            super().do_GET()

    def do_HEAD(self):
        if not self._dispatch(head=True):
            super().do_HEAD()

    def _admin_allowed(self):
        return self.ADMIN_ONLY or getattr(self.server, "admin_shared", False)

    def do_POST(self):
        is_admin = urlsplit(self.path).path.startswith("/admin/")
        if is_admin and self._admin_allowed():
            admin.handle(self, "POST")
        else:  # the public port never reveals that a dashboard exists
            self.send_error(404 if (is_admin or self.ADMIN_ONLY) else 405)

    def _send(self, body, ctype, head=False, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in headers or []:
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _dispatch(self, head):
        split = urlsplit(self.path)
        path = unquote(split.path)

        is_admin_path = path == "/admin" or path.startswith("/admin/")
        if self.ADMIN_ONLY:  # dashboard port: nothing but /admin/
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/admin/")
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif is_admin_path:
                admin.handle(self, "GET", head)
            else:
                self.send_error(404)
            return True
        if is_admin_path:
            if self._admin_allowed():
                admin.handle(self, "GET", head)
            else:
                self.send_error(404)
            return True

        if path in ("/", "/index.html"):
            self._send(render_home(self._hostname(), "https" if getattr(self.server, "tls", False) else "http")
                       .encode("utf-8"), "text/html; charset=utf-8", head)
            return True

        if path in ("/ca.crt", "/ca.cer", "/ca.pem"):   # the public certificate authority (never the key)
            data = pki.ca_der() if path == "/ca.cer" else pki.ca_pem()
            if data is None:
                self.send_error(404)
            else:
                self._send(data, "application/x-x509-ca-cert", head, 200,
                           [("Content-Disposition", 'attachment; filename="craft-web-server-ca%s"' % (
                               ".cer" if path == "/ca.cer" else ".crt"))])
            return True

        if path in ("/health", "/api/apps"):
            apps = cfg.discover_apps()
            if path == "/health":
                data = {"status": "ok", "version": __version__, "apps": len(apps)}
            else:
                ports = portmux.active()
                data = [
                    {"id": a["id"], "title": a["title"], "version": a["version"],
                     "source": a["source"], "port": ports.get(a["id"])}
                    for a in apps.values()
                ]
            self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8", head)
            return True

        parts = [p for p in path.split("/") if p]
        # /pdfcraft -> /pdfcraft/ so that relative asset URLs resolve correctly
        if len(parts) == 1 and not path.endswith("/") and parts[0].lower() in cfg.discover_apps():
            location = "/" + quote(parts[0]) + "/"
            if split.query:
                location += "?" + split.query
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return True
        return False

    # -- request classification
    def _hostname(self):
        host = self.headers.get("Host", "")
        if host.startswith("["):
            return host.split("]")[0] + "]"
        return host.rsplit(":", 1)[0] if ":" in host else host

    def _wants_html(self):
        dest = self.headers.get("Sec-Fetch-Dest")
        if dest:
            return dest in ("document", "iframe", "frame")
        accept = self.headers.get("Accept", "")
        return not accept or "text/html" in accept

    def _is_document(self):
        dest = self.headers.get("Sec-Fetch-Dest")
        if dest:
            return dest in ("document", "iframe", "frame")
        path = urlsplit(self.path).path
        return path.endswith("/") or path.endswith(".html")

    def _compat_app(self):
        """Which app does a root-level request ("/assets/x.js") belong to? The page that
        asked (Referer), else the app of the last page opened in this browser (cookie)."""
        apps = cfg.discover_apps()
        referer = self.headers.get("Referer")
        if referer:
            ref = urlsplit(referer)
            if ref.netloc == self.headers.get("Host", ""):
                seg = [p for p in unquote(ref.path).split("/") if p]
                if seg and seg[0].lower() in apps:
                    return apps[seg[0].lower()]
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except http.cookies.CookieError:
            return None
        morsel = jar.get("craft_app")
        return apps.get(morsel.value.lower()) if morsel else None

    def _file_for(self, app, rest):
        """File inside an app for the path segments `rest` (empty = the app's index)."""
        missing = str(cfg.root_dir() / "__not_found__")
        base = app["base"]
        if not rest:
            return str(app["index"])
        target = base.joinpath(*rest).resolve()
        # Block path traversal (../ and symlinks pointing outside the app)
        if target != base and base not in target.parents:
            return missing
        if target.is_dir():
            target = target / "index.html"
        # Single-page-app fallback for extension-less client routes (page loads only)
        if not target.exists() and not Path(rest[-1]).suffix and self._wants_html():
            target = app["index"]
        return str(target)

    def translate_path(self, path):
        missing = str(cfg.root_dir() / "__not_found__")
        parts = [unquote(p) for p in urlsplit(path).path.split("/") if p]
        if not parts:
            return missing
        if parts[0] == "_vendor":                # downloaded CDN files, shared by all apps
            return str(localize.vendor_file(parts[1:]) or missing)
        app = cfg.discover_apps().get(parts[0].lower())
        if app is not None:                      # /<app-id>/...
            self._app = app
            return self._file_for(app, parts[1:])
        app = self._compat_app()                 # apps built for "/": /assets/x.js
        if app is None:
            return missing
        self._app, self._compat = app, True
        return self._file_for(app, parts)


class AppHandler(CraftHandler):
    """Serves ONE app from the root of its own port, so apps that expect to live at "/"
    work unchanged and are isolated (storage, service workers) from the other apps."""

    def _dispatch(self, head):
        return False

    def do_POST(self):
        self.send_error(405)

    def translate_path(self, path):
        missing = str(cfg.root_dir() / "__not_found__")
        parts = [unquote(p) for p in urlsplit(path).path.split("/") if p]
        if parts and parts[0] == "_vendor":
            return str(localize.vendor_file(parts[1:]) or missing)
        app = cfg.discover_apps().get(getattr(self.server, "app_id", ""))
        if app is None:
            return missing
        self._app = app
        return self._file_for(app, parts)


class AdminHandler(CraftHandler):
    """Handler of the dashboard port: serves /admin/ and nothing else."""
    ADMIN_ONLY = True


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no packet is actually sent
            return s.getsockname()[0]
    except OSError:
        return "SERVER-IP"


def _make_server(host, port, handler, settings):
    server = ThreadingHTTPServer((host, port), handler)
    server.tls = False
    server.access_log = bool(settings.get("access_log"))
    cert, key = settings.get("tls_cert"), settings.get("tls_key")
    if cert and key:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cfg.base_dir() / cert, cfg.base_dir() / key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server.tls = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Craft Apps web server")
    parser.add_argument("--host", help="override settings.host")
    parser.add_argument("--port", type=int, help="override settings.port")
    parser.add_argument("--set-admin-password", action="store_true",
                        help="set or change the dashboard password, then exit")
    parser.add_argument("--setup-https", action="store_true",
                        help="create a local certificate authority + server certificate and enable HTTPS, then exit")
    parser.add_argument("--names", help="with --setup-https: extra host names / IPs, comma separated")
    args = parser.parse_args(argv)

    cfg.migrate_legacy(print)
    cfg.ensure_data_dir()
    cfg.ensure_default_config()
    if args.setup_https:
        return pki.main((["--names", args.names] if args.names else []))
    if args.set_admin_password:
        import getpass
        first = getpass.getpass("New admin password (min %d chars): " % security.MIN_PASSWORD)
        if first != getpass.getpass("Repeat password: "):
            print("Passwords do not match.")
            return 1
        try:
            security.set_password(first)
        except ValueError as exc:
            print(exc)
            return 1
        print("Admin password saved.")
        return 0

    setup_logging()
    settings = cfg.load_config()["settings"]
    host = args.host or settings["host"]
    port = args.port or int(settings["port"])
    cfg.root_dir().mkdir(exist_ok=True)

    # Headless setups (containers): CRAFTWEB_ADMIN_PASSWORD is used once, only if no
    # password exists yet.
    env_password = os.environ.get("CRAFTWEB_ADMIN_PASSWORD")
    if env_password and not security.password_hash():
        try:
            security.set_password(env_password)
            LOG.info("admin password initialised from CRAFTWEB_ADMIN_PASSWORD")
        except ValueError as exc:
            LOG.warning("CRAFTWEB_ADMIN_PASSWORD ignored: %s", exc)

    cfg.RUNTIME["port"] = port
    public = _make_server(host, port, CraftHandler, settings)
    scheme = "https" if public.tls else "http"
    ip = local_ip()

    admin_server, admin_url = None, None
    if settings.get("admin_enabled", True):
        admin_port = int(settings.get("admin_port") or 0)
        cfg.RUNTIME["admin_port"] = admin_port if admin_port != port else 0
        if admin_port and admin_port != port:
            admin_server = _make_server(settings.get("admin_host") or host, admin_port,
                                        AdminHandler, settings)
            admin_url = "%s://%s:%d/admin/" % (scheme, ip, admin_port)
        else:
            public.admin_shared = True
            admin_url = "%s://%s:%d/admin/" % (scheme, ip, port)

    print("=" * 56)
    print("            CRAFT APPS SERVER", __version__)
    print("=" * 56)
    print("Local  : %s://localhost:%d/" % (scheme, port))
    print("Network: %s://%s:%d/" % (scheme, ip, port))
    print("Apps   :", ", ".join(sorted(cfg.discover_apps())) or "(none installed yet)")
    if admin_url:
        print("Admin  :", admin_url)
        if getattr(public, "admin_shared", False):
            print("         WARNING: dashboard shares the apps port; set admin_port to isolate it")
        if not security.password_hash():
            print("         (no password yet - run: %s)" % cfg.cli("passwd"))
    print("=" * 56)

    if settings.get("inbox_enabled", True):
        inbox.start()
    scheduler.start()

    def app_listener(app_port, app_id):
        listener = _make_server(host, app_port, AppHandler, cfg.load_config()["settings"])
        listener.app_id = app_id
        return listener

    portmux.start(app_listener)
    if admin_server:
        threading.Thread(target=admin_server.serve_forever, name="admin-http",
                         daemon=True).start()
    try:
        public.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        portmux.stop_all()
        public.server_close()
        if admin_server:
            admin_server.shutdown()
            admin_server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

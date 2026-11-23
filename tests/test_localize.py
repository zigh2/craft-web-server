import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import admin, localize, security, updater  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, CraftHandler  # noqa: E402

APP = {"id": "demo", "title": "Demo", "folder_prefix": "demo-web-"}


class FakeCDN(BaseHTTPRequestHandler):
    hits = []
    port = 0

    def log_message(self, *a):
        pass

    def do_GET(self):
        FakeCDN.hits.append(self.path)
        p = self.path
        routes = {
            "/lib.js": ("application/javascript", b"window.LIB=1"),
            "/css/app.css": ("text/css", b"@import 'other.css'; @font-face{src:url(../fonts/f.woff2)}"
                                         b" .i{background:url(data:image/png;base64,AAA)}"),
            "/css/other.css": ("text/css", b"body{color:red}"),
            "/fonts/f.woff2": ("font/woff2", b"wOF2-f"),
            "/fonts/g.woff2": ("font/woff2", b"wOF2-g"),
        }
        if p.startswith("/gfonts/css2"):
            body = ("@font-face{font-family:X;src:url(http://127.0.0.1:%d/fonts/g.woff2) format('woff2')}"
                    % FakeCDN.port).encode()
            routes[p] = ("text/css; charset=utf-8", body)
        if p in routes:
            ctype, body = routes[p]
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)


def page(port):
    return (
        '<link rel="stylesheet" href="http://127.0.0.1:%(p)d/gfonts/css2?family=X&amp;display=swap" '
        'integrity="sha384-x" crossorigin="anonymous">'
        '<link rel="stylesheet" href="http://127.0.0.1:%(p)d/css/app.css">'
        '<link rel="canonical" href="https://example.com/page"><link rel="preconnect" href="https://fonts.gstatic.com">'
        '<script src="http://127.0.0.1:%(p)d/lib.js" integrity="sha384-abc" crossorigin></script>'
        '<script src="http://127.0.0.1:%(p)d/missing.js"></script><a href="http://127.0.0.1:%(p)d/lib.js">dl</a>'
        '<style>.a{background:url(http://127.0.0.1:%(p)d/fonts/f.woff2)}</style>'
        '<script>const w="http://127.0.0.1:%(p)d/lib.js"</script><script src="https://esm.sh/react"></script>'
        % {"p": port})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {}, "apps": [APP]}))
        cfg.invalidate_cache()
        admin.reset()
        localize._bad_hosts.clear()
        localize.ALLOW_PRIVATE = True                      # the fake CDN lives on 127.0.0.1
        FakeCDN.hits = []
        self.cdn = ThreadingHTTPServer(("127.0.0.1", 0), FakeCDN)
        FakeCDN.port = self.port = self.cdn.server_address[1]
        threading.Thread(target=self.cdn.serve_forever, daemon=True).start()
        self.app_dir = self.make_app("app")

    def tearDown(self):
        localize.ALLOW_PRIVATE = False
        self.cdn.shutdown()
        self.cdn.server_close()
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_app(self, name):
        d = Path(self.tmp, name)
        (d / "assets").mkdir(parents=True)
        (d / "index.html").write_text(page(self.port))
        (d / "assets/main.js").write_text(
            'import("http://127.0.0.1:%(p)d/lib.js");fetch("http://127.0.0.1:%(p)d/api/items");'
            'const a="https://api.invalid/x.js"' % {"p": self.port})
        return d

    def host(self):
        return "127.0.0.1_%d" % self.port


class LocalizeTests(Base):
    def test_rewrites_html_css_and_js_and_keeps_the_rest(self):
        result = localize.localize_folder(self.app_dir, lambda m: None)
        html = (self.app_dir / "index.html").read_text()
        h = self.host()
        self.assertIn('/_vendor/%s/lib.js"' % h, html)
        self.assertIn("/_vendor/%s/gfonts/css2__" % h, html)
        self.assertEqual(html.count("integrity="), 0)                       # same-origin now: hashes dropped
        self.assertIn("missing.js", html)
        self.assertIn('<a href="http://127.0.0.1:%d/lib.js">' % self.port, html)   # plain links stay
        self.assertIn("https://example.com/page", html)                     # canonical stays
        self.assertIn("https://fonts.gstatic.com", html)                    # preconnect stays
        self.assertIn("https://esm.sh/react", html)                         # unsupported module CDN stays
        self.assertIn("url(/_vendor/%s/fonts/f.woff2)" % h, html)           # inline <style>
        self.assertIn('const w="/_vendor/%s/lib.js"' % h, html)             # inline <script>
        js = (self.app_dir / "assets/main.js").read_text()
        self.assertIn('import("/_vendor/%s/lib.js")' % h, js)
        self.assertIn("http://127.0.0.1:%d/api/items" % self.port, js)      # not a static file: left alone
        self.assertIn("https://api.invalid/x.js", js)                       # unreachable: left alone
        self.assertEqual(result["unsupported"], ["esm.sh"])
        self.assertIn("HTTP 404", " ".join(result["failed"].values()))

    def test_vendored_css_is_rewritten_recursively_with_relative_paths(self):
        localize.localize_folder(self.app_dir, lambda m: None)
        vendor = localize.vendor_dir() / self.host()
        css = (vendor / "css/app.css").read_text()
        self.assertIn("@import 'other.css'", css)
        self.assertIn("url(../fonts/f.woff2)", css)
        self.assertIn("url(data:image/png;base64,AAA)", css)                # data URIs untouched
        self.assertTrue((vendor / "css/other.css").is_file())
        self.assertEqual((vendor / "fonts/f.woff2").read_bytes(), b"wOF2-f")
        gcss = next((vendor / "gfonts").glob("css2__*.css")).read_text()
        self.assertIn("url(../fonts/g.woff2)", gcss)                        # absolute font URL became relative
        self.assertEqual((vendor / "fonts/g.woff2").read_bytes(), b"wOF2-g")

    def test_second_run_changes_nothing_and_downloads_nothing(self):
        localize.localize_folder(self.app_dir, lambda m: None)
        FakeCDN.hits.clear()
        again = localize.localize_folder(self.app_dir, lambda m: None)
        self.assertEqual((again["files_changed"], again["downloaded"]), (0, 0))

    def test_vendor_store_is_reused_when_the_internet_is_gone(self):
        localize.localize_folder(self.app_dir, lambda m: None)
        self.cdn.shutdown()
        self.cdn.server_close()
        second = self.make_app("another-version")
        result = localize.localize_folder(second, lambda m: None)
        self.assertEqual(result["downloaded"], 0)
        self.assertIn("/_vendor/%s/lib.js" % self.host(), (second / "index.html").read_text())

    def test_manifest_summary(self):
        localize.localize_folder(self.app_dir, lambda m: None)
        info = localize.summary(self.app_dir)
        self.assertGreaterEqual(info["resources"], 5)
        self.assertEqual(localize.summary(Path(self.tmp)), {})

    def test_auto_respects_the_setting(self):
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {"localize_external": False}, "apps": [APP]}))
        self.assertIsNone(localize.auto(self.app_dir, lambda m: None))
        self.assertIn("http://127.0.0.1", (self.app_dir / "index.html").read_text())

    def test_install_makes_the_app_offline_ready_but_the_cached_zip_stays_original(self):
        z = Path(self.tmp, "demo.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("index.html", page(self.port))
        updater.install_zip(APP, z, "v1")
        installed = cfg.active_folder(APP) / "index.html"
        self.assertIn("/_vendor/", installed.read_text())
        cached = updater.cache_list(APP)[0]["name"]
        with zipfile.ZipFile(cfg.cache_dir() / "demo" / cached) as f:
            self.assertIn("http://127.0.0.1", f.read("index.html").decode())

    def test_a_broken_cdn_never_fails_an_install(self):
        self.cdn.shutdown()
        self.cdn.server_close()
        z = Path(self.tmp, "demo.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("index.html", page(self.port))
        updater.install_zip(APP, z, "v1")
        self.assertIsNotNone(cfg.active_folder(APP))


class ServingTests(Base):
    def setUp(self):
        super().setUp()
        localize.localize_folder(self.app_dir, lambda m: None)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), CraftHandler)
        self.httpd.tls = False
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def get(self, path, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=5)
        c.request("GET", path, headers=headers or {})
        r = c.getresponse()
        body = r.read()
        c.close()
        return r, body

    def test_vendor_files_are_served_without_knowing_the_app(self):
        r, body = self.get("/_vendor/%s/lib.js" % self.host())
        self.assertEqual((r.status, body), (200, b"window.LIB=1"))
        self.assertIn("javascript", r.getheader("Content-Type"))
        r, _ = self.get("/_vendor/%s/fonts/f.woff2" % self.host())
        self.assertEqual(r.getheader("Content-Type"), "font/woff2")

    def test_vendor_route_is_not_a_file_browser(self):
        for p in ("/_vendor/", "/_vendor", "/_vendor/../apps.json", "/_vendor/..%2f..%2fapps.json",
                  "/_vendor/%2e%2e/%2e%2e/apps.json", "/_vendor/vendor-index.json", "/_vendor/%s/" % self.host()):
            r, body = self.get(p)
            self.assertEqual(r.status, 404, p)
            self.assertNotIn(b"folder_prefix", body)
        self.assertFalse((localize.vendor_dir() / "index.json").exists())   # index lives outside /_vendor/


class SafetyTests(Base):
    def test_requests_to_private_places_are_refused(self):
        localize.ALLOW_PRIVATE = False
        for url in ("http://127.0.0.1/x.js", "http://10.0.0.5/a.js", "http://192.168.1.1/a.js",
                    "http://169.254.169.254/latest/meta-data", "http://[::1]/a", "http://localhost/a.js",
                    "http://printer.local/a.js", "https://example.org:8443/a.js", "ftp://example.org/a.js"):
            self.assertIsNotNone(localize._blocked(url), url)
        self.assertIsNone(localize._blocked("https://93.184.216.34/a.js"))

    def test_a_page_cannot_make_the_server_probe_the_lan(self):
        localize.ALLOW_PRIVATE = False
        result = localize.localize_folder(self.app_dir, lambda m: None)
        self.assertEqual(result["files_changed"], 0)
        self.assertEqual(FakeCDN.hits, [])
        local = {u: why for u, why in result["failed"].items() if "127.0.0.1" in u}
        self.assertTrue(local and all(("private" in why or "not allowed" in why) for why in local.values()))

    def test_download_limits(self):
        old = localize.MAX_NEW_FILES
        localize.MAX_NEW_FILES = 1
        try:
            result = localize.localize_folder(self.app_dir, lambda m: None)
        finally:
            localize.MAX_NEW_FILES = old
        self.assertEqual(result["downloaded"], 1)
        self.assertTrue(any("limit" in why for why in result["failed"].values()))


class AdminLocalizeTests(Base):
    def setUp(self):
        super().setUp()
        security.set_password("correct horse battery")
        z = Path(self.tmp, "demo.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("index.html", '<script src="http://127.0.0.1:%d/lib.js"></script>' % self.port)
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {"localize_external": False}, "apps": [APP]}))
        updater.install_zip(APP, z, "v1")           # auto-localizing is off: still external
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AdminHandler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.cookie = self.csrf = None
        r, d = self.call("POST", "/admin/api/login", {"password": "correct horse battery"})
        self.cookie, self.csrf = r.getheader("Set-Cookie").split(";")[0], d["csrf"]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=10)
        hdr = {"Content-Type": "application/json"}
        if self.cookie:
            hdr["Cookie"], hdr["X-CSRF-Token"] = self.cookie, self.csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=hdr)
        r = c.getresponse()
        data = json.loads(r.read() or b"{}")
        c.close()
        return r, data

    def test_button_flow_job_then_diagnose(self):
        r, d = self.call("GET", "/admin/api/diagnose?app=demo")
        self.assertIn("external_resources", [i["id"] for i in d["issues"]])
        r, d = self.call("POST", "/admin/api/localize", {"app": "demo"})
        self.assertEqual(r.status, 200, d)
        for _ in range(100):
            r, j = self.call("GET", "/admin/api/job?id=" + d["job"])
            if j["job"]["status"] != "running":
                break
        self.assertEqual(j["job"]["status"], "done", j)
        self.assertIn("Offline-ready", "\n".join(j["job"]["log"]))
        r, d = self.call("GET", "/admin/api/diagnose?app=demo")
        ids = [i["id"] for i in d["issues"]]
        self.assertNotIn("external_resources", ids)
        self.assertNotIn("missing_files", ids)                  # /_vendor/... resolves to the vendor store
        self.assertNotIn("root_paths", ids)
        self.assertGreaterEqual(d["localized"]["resources"], 1)

    def test_setting_is_switchable(self):
        r, d = self.call("POST", "/admin/api/settings", {"localize_external": True})
        self.assertEqual(r.status, 200)
        self.assertTrue(cfg.load_config()["settings"]["localize_external"])


if __name__ == "__main__":
    unittest.main()

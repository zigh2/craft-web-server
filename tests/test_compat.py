import http.client
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import admin, diagnose, portmux, security, updater  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, AppHandler, CraftHandler  # noqa: E402

APP = {"id": "demo", "title": "Demo", "folder_prefix": "demo-web-"}
INDEX = '<script type="module" src="/assets/app.js"></script><link rel="stylesheet" href="/assets/app.css">'


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Base(unittest.TestCase):
    apps = [APP]
    settings = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        Path(self.tmp, "apps.json").write_text(json.dumps(
            {"settings": dict(self.settings), "apps": self.apps}), encoding="utf-8")
        cfg.invalidate_cache()
        admin.reset()
        z = Path(self.tmp, "demo.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("index.html", INDEX)
            f.writestr("assets/app.js", "console.log('app')")
            f.writestr("assets/app.css", "body{}")
            f.writestr("locales/en.json", '{"hello":"hi"}')
            f.writestr("secret-outside.txt", "inside the app")
        updater.install_zip(self.apps[0], z, "v1")
        (Path(self.tmp) / "outside.txt").write_text("OUTSIDE")

    def tearDown(self):
        portmux.stop_all()
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self, handler, app_id=None):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        httpd.tls = False
        if app_id:
            httpd.app_id = app_id
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        return httpd.server_address[1]

    def get(self, port, path, headers=None, method="GET"):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request(method, path, headers=headers or {})
        r = c.getresponse()
        body = r.read()
        c.close()
        return r, body


class RootPathFallbackTests(Base):
    def test_assets_requested_from_the_root_are_served_via_referer(self):
        port = self.serve(CraftHandler)
        ref = {"Referer": "http://127.0.0.1:%d/demo/" % port}
        r, body = self.get(port, "/assets/app.js", ref)
        self.assertEqual((r.status, body), (200, b"console.log('app')"))
        self.assertEqual(r.getheader("X-Craft-Compat"), "root-path")
        self.assertEqual(self.get(port, "/locales/en.json", ref)[0].status, 200)

    def test_without_any_hint_root_paths_stay_404(self):
        port = self.serve(CraftHandler)
        self.assertEqual(self.get(port, "/assets/app.js")[0].status, 404)
        foreign = {"Referer": "http://evil.example/demo/"}      # other host: ignored
        self.assertEqual(self.get(port, "/assets/app.js", foreign)[0].status, 404)

    def test_cookie_of_the_last_opened_app_is_the_fallback(self):
        port = self.serve(CraftHandler)
        r, _ = self.get(port, "/demo/", {"Sec-Fetch-Dest": "document"})
        cookie = r.getheader("Set-Cookie")
        self.assertIn("craft_app=demo", cookie)
        self.assertIn("HttpOnly", cookie)
        r, _ = self.get(port, "/assets/app.css", {"Cookie": cookie.split(";")[0]})
        self.assertEqual(r.status, 200)
        r, _ = self.get(port, "/assets/app.css", {"Cookie": "craft_app=nonexistent"})
        self.assertEqual(r.status, 404)

    def test_sub_resources_do_not_set_the_cookie(self):
        port = self.serve(CraftHandler)
        r, _ = self.get(port, "/demo/assets/app.js", {"Sec-Fetch-Dest": "script"})
        self.assertIsNone(r.getheader("Set-Cookie"))

    def test_client_routes_fall_back_to_index_only_for_page_loads(self):
        port = self.serve(CraftHandler)
        ref = {"Cookie": "craft_app=demo"}
        r, body = self.get(port, "/tools/merge", dict(ref, **{"Sec-Fetch-Dest": "document"}))
        self.assertEqual((r.status, INDEX.encode() in body), (200, True))
        r, _ = self.get(port, "/api/data", dict(ref, **{"Sec-Fetch-Dest": "empty"}))   # fetch(): no fake HTML
        self.assertEqual(r.status, 404)
        r, _ = self.get(port, "/demo/some/route", {"Accept": "application/json"})
        self.assertEqual(r.status, 404)
        r, _ = self.get(port, "/demo/some/route", {"Accept": "text/html"})
        self.assertEqual(r.status, 200)

    def test_fallback_cannot_escape_the_app_folder(self):
        port = self.serve(CraftHandler)
        ref = {"Referer": "http://127.0.0.1:%d/demo/" % port}
        for p in ("/../outside.txt", "/..%2foutside.txt", "/%2e%2e/%2e%2e/apps.json",
                  "/..%2f..%2fapps.json", "/assets/../../outside.txt"):
            r, body = self.get(port, p, ref)
            self.assertNotIn(b"OUTSIDE", body, p)
            self.assertNotIn(b"folder_prefix", body, p)

    def test_real_app_ids_and_special_routes_win(self):
        port = self.serve(CraftHandler)
        ref = {"Referer": "http://127.0.0.1:%d/demo/" % port}
        self.assertEqual(json.loads(self.get(port, "/health", ref)[1])["status"], "ok")
        self.assertEqual(self.get(port, "/admin/", ref)[0].status, 404)


class OwnPortTests(Base):
    def test_app_handler_serves_the_app_from_the_root(self):
        port = self.serve(AppHandler, "demo")
        self.assertIn(INDEX.encode(), self.get(port, "/")[1])
        self.assertEqual(self.get(port, "/assets/app.js")[1], b"console.log('app')")
        self.assertEqual(self.get(port, "/index.html")[0].status, 200)
        self.assertEqual(self.get(port, "/nothing.png")[0].status, 404)
        r, body = self.get(port, "/deep/client/route", {"Accept": "text/html"})
        self.assertIn(INDEX.encode(), body)
        self.assertNotIn(b"folder_prefix", self.get(port, "/..%2fapps.json")[1])
        self.assertEqual(self.get(port, "/", method="HEAD")[0].status, 200)
        c = http.client.HTTPConnection("127.0.0.1", port)
        c.request("POST", "/anything", body=b"x")
        self.assertEqual(c.getresponse().status, 405)

    def test_ports_are_assigned_remembered_and_never_collide(self):
        base = free_port()
        Path(self.tmp, "apps.json").write_text(json.dumps({
            "settings": {"isolate_apps": True, "app_port_base": base, "port": base},
            "apps": [APP, {"id": "b", "folder_prefix": "b-"}, {"id": "c", "folder_prefix": "c-", "own_port": False},
                     {"id": "d", "folder_prefix": "d-", "port": base + 5}]}))
        first = cfg.desired_ports()
        self.assertEqual(sorted(first), ["b", "d", "demo"])
        self.assertEqual(first["d"], base + 5)
        self.assertEqual(len(set(first.values())), 3)
        self.assertNotIn(base, first.values())                 # the public port is reserved
        self.assertEqual(cfg.desired_ports(), first)            # stable across calls / restarts

    def test_port_manager_follows_the_configuration_live(self):
        port = free_port()
        APPS = {"settings": {"app_port_base": port},
                "apps": [dict(APP, own_port=True)]}
        Path(self.tmp, "apps.json").write_text(json.dumps(APPS))

        def factory(p, app_id):
            httpd = ThreadingHTTPServer(("127.0.0.1", p), AppHandler)
            httpd.tls, httpd.app_id = False, app_id
            return httpd

        portmux.reconcile(factory)
        self.assertEqual(portmux.active(), {"demo": port})
        self.assertEqual(self.get(port, "/assets/app.js")[0].status, 200)
        APPS["apps"][0]["own_port"] = False
        Path(self.tmp, "apps.json").write_text(json.dumps(APPS))
        portmux.reconcile(factory)
        self.assertEqual(portmux.active(), {})
        with self.assertRaises(OSError):
            self.get(port, "/")

    def test_port_in_use_is_reported_not_fatal(self):
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        self.addCleanup(blocker.close)
        busy = blocker.getsockname()[1]
        Path(self.tmp, "apps.json").write_text(json.dumps(
            {"apps": [dict(APP, port=busy)]}))

        def factory(p, app_id):
            return ThreadingHTTPServer(("127.0.0.1", p), AppHandler)

        portmux.reconcile(factory)
        self.assertEqual(portmux.active(), {})
        self.assertTrue(portmux.status("demo")["error"])

    def test_home_page_links_to_the_own_port(self):
        public = self.serve(CraftHandler)
        self.assertIn(b'href="/demo/"', self.get(public, "/")[1])
        portmux._running["demo"] = (8123, None)
        try:
            body = self.get(public, "/", {"Host": "192.168.1.5:%d" % public})[1]
        finally:
            portmux._running.clear()
        self.assertIn(b'href="http://192.168.1.5:8123/"', body)


class DiagnoseTests(Base):
    def test_scan_finds_the_usual_suspects(self):
        d = Path(self.tmp, "app")
        (d / "assets").mkdir(parents=True)
        (d / "index.html").write_text(
            '<script src="/assets/app.js"></script><script src="https://cdn.example.com/x.js"></script>'
            '<img src="gone.png"><script src="/missing.js"></script>')
        (d / "assets/app.js").write_text("new SharedArrayBuffer(1);crypto.subtle;serviceWorker.register('/sw.js')")
        (d / "assets/app.css").write_text("@import url(https://fonts.example.org/a.css);")
        found = {i["id"]: i for i in diagnose.scan(d)["issues"]}
        self.assertEqual(set(found), {"missing_files", "root_paths", "external_resources",
                                      "secure_context", "wasm_threads", "service_worker"})
        self.assertEqual(found["missing_files"]["severity"], "error")
        self.assertEqual(found["external_resources"]["items"], ["cdn.example.com", "fonts.example.org"])
        self.assertEqual(found["missing_files"]["count"], 2)

    def test_a_clean_app_has_no_issues(self):
        d = Path(self.tmp, "clean")
        d.mkdir()
        (d / "index.html").write_text('<script src="app.js"></script>')
        (d / "app.js").write_text("console.log(1)")
        self.assertEqual(diagnose.scan(d)["issues"], [])

    def test_missing_index_is_an_error(self):
        self.assertEqual(diagnose.scan(Path(self.tmp, "nope"))["issues"][0]["id"], "no_index")


class AdminCompatApiTests(Base):
    def setUp(self):
        super().setUp()
        security.set_password("correct horse battery")
        self.port = self.serve(AdminHandler)
        self.cookie = self.csrf = None
        r, d = self.call("POST", "/admin/api/login", {"password": "correct horse battery"})
        self.cookie, self.csrf = r.getheader("Set-Cookie").split(";")[0], d["csrf"]

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdr = {"Content-Type": "application/json"}
        if self.cookie:
            hdr["Cookie"], hdr["X-CSRF-Token"] = self.cookie, self.csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=hdr)
        r = c.getresponse()
        data = json.loads(r.read() or b"{}")
        c.close()
        return r, data

    def test_diagnose_endpoint(self):
        r, d = self.call("GET", "/admin/api/diagnose?app=demo")
        self.assertEqual(r.status, 200, d)
        self.assertEqual(d["version"], "v1")
        self.assertIn("root_paths", [i["id"] for i in d["issues"]])
        self.assertFalse(d["own_port"])
        r, d = self.call("GET", "/admin/api/diagnose?app=ghost")
        self.assertEqual(r.status, 404)

    def test_settings_whitelist(self):
        r, d = self.call("POST", "/admin/api/settings", {"isolate_apps": True})
        self.assertEqual(r.status, 200)
        raw = json.loads(Path(self.tmp, "apps.json").read_text())
        self.assertTrue(raw["settings"]["isolate_apps"])
        self.assertEqual(raw["apps"][0]["id"], "demo")                       # apps untouched
        r, d = self.call("POST", "/admin/api/settings", {"admin_port": 1, "admin_allowed_networks": []})
        self.assertEqual((r.status, d["code"]), (400, "bad_request"))         # nothing else is settable
        raw = json.loads(Path(self.tmp, "apps.json").read_text())
        self.assertNotIn("admin_port", raw["settings"])

    def test_own_port_fields_and_validation(self):
        r, d = self.call("POST", "/admin/api/app", {"app": {"id": "demo", "title": "Demo", "own_port": True,
                                                              "port": 8333}, "original_id": "demo"})
        self.assertEqual(r.status, 200, d)
        r, d = self.call("GET", "/admin/api/overview")
        self.assertEqual((d["apps"][0]["own_port"], d["apps"][0]["port_config"]), (True, 8333))
        for bad in (80, 70000, "abc"):
            r, d = self.call("POST", "/admin/api/app", {"app": {"id": "demo", "port": bad}, "original_id": "demo"})
            self.assertEqual(r.status, 400, bad)
        r, d = self.call("POST", "/admin/api/app", {"app": {"id": "demo", "port": 8080}, "original_id": "demo"})
        self.assertEqual((r.status, d["code"]), (409, "port_in_use"))


if __name__ == "__main__":
    unittest.main()

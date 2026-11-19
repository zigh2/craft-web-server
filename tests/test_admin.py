import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import admin, inbox, security  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, CraftHandler  # noqa: E402,F401

PASSWORD = "correct horse battery"
APP = {"id": "demo", "title": "Demo", "folder_prefix": "demo-web-", "repo": "o/demo"}


def zip_bytes(path, marker):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("demo/index.html", "<h1>%s</h1>" % marker)


class AdminBase(unittest.TestCase):
    settings = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        settings = {"backup_count": 2}
        settings.update(self.settings)
        Path(self.tmp, "apps.json").write_text(
            json.dumps({"settings": settings, "apps": [APP]}), encoding="utf-8")
        security.set_password(PASSWORD)
        cfg.invalidate_cache()
        admin.reset()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AdminHandler)
        self.httpd.tls = False
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]
        self.cookie, self.csrf = None, None

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, method, path, body=None, headers=None, raw=None, csrf=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdr = dict(headers or {})
        if self.cookie:
            hdr["Cookie"] = self.cookie
        if csrf and self.csrf:
            hdr["X-CSRF-Token"] = self.csrf
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            hdr["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=hdr)
        r = c.getresponse()
        payload = r.read()
        c.close()
        try:
            parsed = json.loads(payload)
        except ValueError:
            parsed = payload
        return r, parsed

    def login(self):
        r, d = self.call("POST", "/admin/api/login", {"password": PASSWORD})
        self.assertEqual(r.status, 200, d)
        self.cookie = r.getheader("Set-Cookie").split(";")[0]
        self.csrf = d["csrf"]

    def upload(self, tag):
        z = Path(self.tmp, tag + ".zip")
        zip_bytes(z, tag)
        return self.call("POST", "/admin/api/upload", raw=z.read_bytes(),
                         headers={"X-App": "demo", "X-Version": tag,
                                  "Content-Type": "application/zip"})


class AuthTests(AdminBase):
    def test_static_and_security_headers(self):
        r, body = self.call("GET", "/admin/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"app.js", body)
        self.assertIn("default-src 'none'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(r.getheader("Cache-Control"), "no-store")
        r, _ = self.call("GET", "/admin/static/app.js")
        self.assertIn("javascript", r.getheader("Content-Type"))

    def test_static_whitelist_and_traversal(self):
        for p in ("/admin/static/../server.py", "/admin/static/..%2fadmin.py",
                  "/admin/static/__init__.py", "/admin/static/%2e%2e/admin.py"):
            r, body = self.call("GET", p)
            self.assertEqual(r.status, 404, p)

    def test_api_requires_login(self):
        r, d = self.call("GET", "/admin/api/overview")
        self.assertEqual((r.status, d["code"]), (401, "session"))

    def test_wrong_password_and_lockout(self):
        for _ in range(5):
            r, d = self.call("POST", "/admin/api/login", {"password": "nope-nope-nope"})
            self.assertEqual(r.status, 401)
        r, d = self.call("POST", "/admin/api/login", {"password": PASSWORD})
        self.assertEqual((r.status, d["code"]), (429, "locked"))

    def test_login_cookie_flags_and_session(self):
        self.login()
        r, _ = self.call("POST", "/admin/api/login", {"password": PASSWORD})
        flags = r.getheader("Set-Cookie")
        self.assertIn("HttpOnly", flags)
        self.assertIn("SameSite=Strict", flags)
        r, d = self.call("GET", "/admin/api/session")
        self.assertTrue(d["authenticated"])

    def test_csrf_and_origin_enforced(self):
        self.login()
        r, d = self.call("POST", "/admin/api/logout", {}, csrf=False)
        self.assertEqual((r.status, d["code"]), (403, "csrf"))
        r, d = self.call("POST", "/admin/api/logout", {},
                         headers={"Origin": "http://evil.example"})
        self.assertEqual((r.status, d["code"]), (403, "csrf"))

    def test_logout_invalidates_session(self):
        self.login()
        r, _ = self.call("POST", "/admin/api/logout", {})
        self.assertEqual(r.status, 200)
        r, _ = self.call("GET", "/admin/api/overview")
        self.assertEqual(r.status, 401)

    def test_password_change(self):
        self.login()
        r, d = self.call("POST", "/admin/api/password", {"current": "wrong", "new": "x" * 12})
        self.assertEqual(r.status, 401)
        r, d = self.call("POST", "/admin/api/password", {"current": PASSWORD, "new": "short"})
        self.assertEqual((r.status, d["code"]), (400, "weak_password"))
        r, d = self.call("POST", "/admin/api/password",
                         {"current": PASSWORD, "new": "a brand new password"})
        self.assertEqual(r.status, 200)
        self.assertTrue(security.verify_password("a brand new password",
                                                 security.password_hash()))


class NetworkTests(AdminBase):
    settings = {"admin_allowed_networks": ["10.9.9.0/24"]}

    def test_denied_outside_allowed_networks(self):
        r, d = self.call("GET", "/admin/")
        self.assertEqual(r.status, 403)
        r, d = self.call("POST", "/admin/api/login", {"password": PASSWORD})
        self.assertEqual(r.status, 403)


class DisabledTests(AdminBase):
    settings = {"admin_enabled": False}

    def test_disabled(self):
        r, _ = self.call("GET", "/admin/")
        self.assertEqual(r.status, 404)


class OperationTests(AdminBase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_upload_activate_delete(self):
        for tag in ("v1.0.0", "v1.1.0"):
            r, d = self.upload(tag)
            self.assertEqual(r.status, 200, d)
        r, d = self.call("GET", "/admin/api/overview")
        app = d["apps"][0]
        self.assertEqual(app["active"], "v1.1.0")
        self.assertTrue(app["live"])
        r, d = self.call("POST", "/admin/api/activate", {"app": "demo", "tag": "v1.0.0"})
        self.assertEqual(r.status, 200)
        r, d = self.call("POST", "/admin/api/delete-version", {"app": "demo", "tag": "v1.0.0"})
        self.assertEqual((r.status, d["code"]), (409, "active"))
        r, d = self.call("POST", "/admin/api/delete-version", {"app": "demo", "tag": "v1.1.0"})
        self.assertEqual(r.status, 200)
        r, d = self.call("POST", "/admin/api/delete-version", {"app": "demo", "tag": "../x"})
        self.assertEqual(r.status, 404)

    def test_upload_rejects_bad_input(self):
        r, d = self.call("POST", "/admin/api/upload", raw=b"not a zip",
                         headers={"X-App": "demo", "X-Version": "v1"})
        self.assertEqual((r.status, d["code"]), (400, "bad_zip"))
        r, d = self.call("POST", "/admin/api/upload", raw=b"x",
                         headers={"X-App": "demo", "X-Version": "../evil"})
        self.assertEqual((r.status, d["code"]), (400, "bad_version"))
        r, d = self.call("POST", "/admin/api/upload", raw=b"x",
                         headers={"X-App": "ghost", "X-Version": "v1"})
        self.assertEqual(r.status, 404)

    def test_app_crud_and_validation(self):
        good = {"id": "newapp", "title": "New", "repo": "own/new", "icon": "🚀"}
        r, d = self.call("POST", "/admin/api/app", {"app": good})
        self.assertEqual(r.status, 200, d)
        r, d = self.call("POST", "/admin/api/app", {"app": good})
        self.assertEqual((r.status, d["code"]), (409, "exists"))
        for bad in ({"id": "admin"}, {"id": "Bad Id"}, {"id": "x1", "repo": "no-slash"},
                    {"id": "x2", "asset_pattern": "("}, {"id": "x3", "index_path": "../x"},
                    {"id": "demo2", "folder_prefix": "demo-"}):
            r, d = self.call("POST", "/admin/api/app", {"app": bad})
            self.assertIn(r.status, (400, 409), bad)
        raw = json.loads(Path(self.tmp, "apps.json").read_text())
        self.assertEqual(raw["settings"], {"backup_count": 2})  # settings untouched
        r, d = self.call("POST", "/admin/api/app-delete", {"id": "newapp"})
        self.assertEqual(r.status, 200)

    def test_install_without_network_reports_failure_job(self):
        os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"  # unreachable on purpose
        try:
            r, d = self.call("POST", "/admin/api/install", {"app": "demo", "tag": "v1"})
            self.assertEqual(r.status, 200, d)
            for _ in range(100):
                r, j = self.call("GET", "/admin/api/job?id=" + d["job"])
                if j["job"]["status"] != "running":
                    break
                time.sleep(0.1)
            self.assertEqual(j["job"]["status"], "failed")
        finally:
            os.environ.pop("HTTPS_PROXY", None)

    def test_audit_records_actions(self):
        self.upload("v1.0.0")
        r, d = self.call("GET", "/admin/api/audit")
        actions = [e["action"] for e in d["entries"]]
        self.assertIn("login", actions)
        self.assertIn("upload-install", actions)


class InboxTests(AdminBase):
    def test_drop_folder_installs_and_rejects(self):
        box = inbox.inbox_dir()
        box.mkdir()
        zip_bytes(box / "demo-web-v2.0.0.zip", "v2")
        zip_bytes(box / "unknown-1.zip", "x")
        sizes = {}
        inbox.process_once(sizes)   # first tick: record sizes
        inbox.process_once(sizes)   # second tick: stable -> process
        self.assertEqual(cfg.active_folder(APP).name, "demo-web-v2.0.0")
        self.assertFalse((box / "demo-web-v2.0.0.zip").exists())
        self.assertTrue((box / "failed" / "unknown-1.zip").exists())


if __name__ == "__main__":
    unittest.main()

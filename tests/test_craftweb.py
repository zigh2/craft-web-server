import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import config as cfg  # noqa: E402
from craftweb import updater  # noqa: E402
from craftweb.server import CraftHandler  # noqa: E402

APP = {
    "id": "demo", "title": "Demo", "folder_prefix": "demo-web-",
    "repo": "o/demo", "index_path": "index.html", "icon": "🧪",
}


def make_zip(path, marker, top="demo-web"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(top + "/index.html", "<h1>%s</h1>" % marker)
        z.writestr(top + "/app.js", "console.log('%s')" % marker)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        Path(self.tmp, "apps.json").write_text(json.dumps(
            {"settings": {"backup_count": 1}, "apps": [APP]}), encoding="utf-8")
        cfg.invalidate_cache()

    def tearDown(self):
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, tag):
        z = Path(self.tmp, "%s.zip" % tag)
        make_zip(z, tag)
        updater.install_zip(APP, z, tag)


class VersionTests(unittest.TestCase):
    def test_ordering(self):
        k = cfg.version_key
        self.assertGreater(k("v1.10.0"), k("v1.9.0"))
        self.assertGreater(k("v1.2.0"), k("v1.2.0-rc.1"))
        self.assertGreater(k("v1.2.0-rc.2"), k("v1.2.0-rc.1"))
        self.assertGreater(k("demo-web-v2", "demo-web-"), k("demo-web-v1.9", "demo-web-"))


class UpdaterTests(Base):
    def test_install_switch_rollback_prune(self):
        self.install("v1.0.0")
        self.install("v1.1.0")
        self.assertEqual(cfg.active_folder(APP).name, "demo-web-v1.1.0")
        updater.rollback(APP)
        self.assertEqual(cfg.active_folder(APP).name, "demo-web-v1.0.0")
        self.install("v1.2.0")
        self.install("v1.3.0")
        names = sorted(f.name for f in cfg.installed_folders(APP))
        self.assertEqual(len(names), 2)  # active + backup_count (1)
        self.assertIn("demo-web-v1.3.0", names)

    def test_reinstall_same_version_is_ok(self):
        self.install("v1.0.0")
        self.install("v1.0.0")
        self.assertEqual(len(cfg.installed_folders(APP)), 1)

    def test_zip_slip_rejected(self):
        z = Path(self.tmp, "evil.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("../evil.txt", "x")
        with self.assertRaises(updater.UpdateError):
            updater.install_zip(APP, z, "v9")

    def test_cli_from_zip_and_list(self):
        z = Path(self.tmp, "demo-web-v3.0.0.zip")
        make_zip(z, "v3")
        self.assertEqual(updater.main(["--app", "demo", "--from-zip", str(z)]), 0)
        self.assertEqual(cfg.active_folder(APP).name, "demo-web-v3.0.0")


class ServerTests(Base):
    def setUp(self):
        super().setUp()
        self.install("v1.0.0")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), CraftHandler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def get(self, path, method="GET"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path)
        r = c.getresponse()
        body = r.read()
        c.close()
        return r, body

    def test_home_lists_app(self):
        r, body = self.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn("Demo", body.decode("utf-8"))

    def test_redirect_and_index(self):
        r, _ = self.get("/demo")
        self.assertEqual((r.status, r.getheader("Location")), (302, "/demo/"))
        r, body = self.get("/demo/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"v1.0.0", body)

    def test_js_mime_and_head(self):
        r, _ = self.get("/demo/app.js")
        self.assertIn("javascript", r.getheader("Content-Type"))
        r, body = self.get("/demo/", "HEAD")
        self.assertEqual((r.status, body), (200, b""))

    def test_spa_fallback_and_404(self):
        r, body = self.get("/demo/some/route")
        self.assertEqual(r.status, 200)
        self.assertIn(b"v1.0.0", body)
        r, _ = self.get("/demo/missing.png")
        self.assertEqual(r.status, 404)
        r, _ = self.get("/nope/")
        self.assertEqual(r.status, 404)

    def test_path_traversal_blocked(self):
        for p in ("/demo/../../apps.json", "/demo/%2e%2e/%2e%2e/apps.json",
                  "/demo/..%2f..%2fapps.json"):
            r, body = self.get(p)
            self.assertNotIn(b"folder_prefix", body, p)

    def test_live_switch_without_restart(self):
        self.install("v2.0.0")
        r, body = self.get("/demo/")
        self.assertIn(b"v2.0.0", body)

    def test_health(self):
        r, body = self.get("/health")
        self.assertEqual(json.loads(body)["status"], "ok")


if __name__ == "__main__":
    unittest.main()

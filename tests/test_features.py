import collections
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

from craftweb import admin, inbox, scheduler, security, updater  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, CraftHandler  # noqa: E402

APP = {"id": "demo", "title": "Demo", "folder_prefix": "demo-web-", "repo": "o/demo",
       "asset_pattern": r"^demo-web-.*\.zip$"}


def make_zip(path, marker):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("demo/index.html", "<h1>%s</h1>" % marker)
    return Path(path)


class Base(unittest.TestCase):
    settings = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        settings = {"backup_count": 1, "cache_keep": 3}
        settings.update(self.settings)
        Path(self.tmp, "apps.json").write_text(
            json.dumps({"settings": settings, "apps": [APP]}), encoding="utf-8")
        cfg.invalidate_cache()
        admin.reset()
        scheduler.LATEST.clear()

    def tearDown(self):
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def zip(self, name):
        return make_zip(Path(self.tmp, name), name)

    def active(self):
        f = cfg.active_folder(APP)
        return f.name if f else None


class PortIsolationTests(Base):
    def serve(self, handler, shared=False):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        httpd.tls = False
        httpd.admin_shared = shared
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        return httpd.server_address[1]

    def req(self, port, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request(method, path, body=body, headers={"Content-Type": "application/json"} if body else {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r, data

    def test_public_port_has_no_dashboard(self):
        port = self.serve(CraftHandler)
        for method, path in (("GET", "/admin/"), ("GET", "/admin/api/session"),
                             ("GET", "/admin/static/app.js")):
            self.assertEqual(self.req(port, method, path)[0].status, 404, path)
        r, _ = self.req(port, "POST", "/admin/api/login", b'{"password":"x"}')
        self.assertEqual(r.status, 404)

    def test_admin_port_serves_only_the_dashboard(self):
        updater.install_zip(APP, self.zip("demo-web-v1.zip"), "v1")
        port = self.serve(AdminHandler)
        r, _ = self.req(port, "GET", "/")
        self.assertEqual((r.status, r.getheader("Location")), (302, "/admin/"))
        self.assertEqual(self.req(port, "GET", "/admin/")[0].status, 200)
        self.assertEqual(self.req(port, "GET", "/demo/")[0].status, 404)
        self.assertEqual(self.req(port, "GET", "/health")[0].status, 404)

    def test_shared_mode_still_possible(self):
        port = self.serve(CraftHandler, shared=True)
        self.assertEqual(self.req(port, "GET", "/admin/")[0].status, 200)


class CacheTests(Base):
    def test_install_keeps_zip_in_cache_and_reinstalls_offline(self):
        for tag in ("v1.0.0", "v1.1.0", "v1.2.0"):
            updater.install_zip(APP, self.zip("demo-web-%s.zip" % tag), tag)
        self.assertEqual(self.active(), "demo-web-v1.2.0")
        self.assertEqual(len(cfg.installed_folders(APP)), 2)   # active + backup_count
        names = [c["tag"] for c in updater.cache_list(APP)]
        self.assertEqual(names, ["v1.2.0", "v1.1.0", "v1.0.0"])  # nothing was lost
        old = [c for c in updater.cache_list(APP) if c["tag"] == "v1.0.0"][0]
        updater.install_from_cache(APP, old["name"])            # no network involved
        self.assertEqual(self.active(), "demo-web-v1.0.0")

    def test_cache_keep_limit_and_delete(self):
        for i in range(5):
            tag = "v1.%d.0" % i
            updater.install_zip(APP, self.zip("demo-web-%s.zip" % tag), tag)
        tags = [c["tag"] for c in updater.cache_list(APP)]
        self.assertEqual(tags, ["v1.4.0", "v1.3.0", "v1.2.0"])
        updater.cache_delete(APP, updater.cache_list(APP)[0]["name"])
        self.assertEqual(len(updater.cache_list(APP)), 2)
        with self.assertRaises(updater.UpdateError):
            updater.cache_delete(APP, "../../apps.json")

    def test_cache_can_be_disabled(self):
        Path(self.tmp, "apps.json").write_text(json.dumps(
            {"settings": {"cache_enabled": False}, "apps": [APP]}))
        updater.install_zip(APP, self.zip("demo-web-v1.zip"), "v1")
        self.assertEqual(updater.cache_list(APP), [])

    def test_update_app_uses_cached_copy_instead_of_downloading(self):
        z = self.zip("demo-web-v2.0.0.zip")
        updater.cache_store(APP, z, "v2.0.0", z.name)
        release = {"tag_name": "v2.0.0", "assets": [{"name": z.name, "size": z.stat().st_size,
                                                     "url": "u", "browser_download_url": "u"}]}
        calls = []
        updater.get_releases = lambda *a, **k: [release]
        updater.download = lambda *a, **k: calls.append(a) or ""
        try:
            updater.update_app(APP, latest=True)
        finally:
            import importlib
            importlib.reload(updater)
        self.assertEqual(calls, [])
        self.assertEqual(self.active(), "demo-web-v2.0.0")


class ImportTests(Base):
    def test_import_existing_downloads(self):
        src = Path(self.tmp, "downloads_old")
        src.mkdir()
        for tag in ("v1.0.0", "v1.5.0", "v2.0.0", "v0.5.0", "v0.6.0"):
            make_zip(src / ("demo-web-%s.zip" % tag), tag)
        (src / "random-notes.zip").write_bytes(b"not related")
        folder = src / "demo-web-v1.9.0"
        folder.mkdir()
        (folder / "index.html").write_text("<h1>1.9</h1>")
        result = updater.import_paths([str(src)])
        self.assertEqual(self.active(), "demo-web-v2.0.0")           # newest is live
        self.assertEqual(len(cfg.installed_folders(APP)), 2)          # active + backup_count
        cached = {c["tag"] for c in updater.cache_list(APP)}
        self.assertTrue({"v2.0.0", "v1.5.0", "v1.0.0"} <= cached)     # nothing needs re-downloading
        self.assertEqual([p.name for p, _ in result["skipped"]], ["random-notes.zip"])

    def test_import_never_downgrades_active_version(self):
        updater.install_zip(APP, self.zip("demo-web-v3.0.0.zip"), "v3.0.0")
        make_zip(Path(self.tmp, "demo-web-v1.0.0.zip"), "old")
        updater.import_paths([str(Path(self.tmp, "demo-web-v1.0.0.zip"))])
        self.assertEqual(self.active(), "demo-web-v3.0.0")

    def test_import_cli_and_forced_app(self):
        odd = make_zip(Path(self.tmp, "build_final.zip"), "x")  # no version in the name
        self.assertEqual(updater.main(["--import", str(odd)]), 1)
        self.assertEqual(updater.main(["--import", str(odd), "--app", "demo"]), 0)
        self.assertEqual(self.active(), "demo-web-build_final")

    def test_match_app_rules(self):
        apps = [APP, {"id": "fig", "folder_prefix": "fig-web-", "asset_pattern": r".*web.*\.zip$"}]
        self.assertEqual(updater.match_app("demo-web-v1.2.0.zip", apps)[1], "v1.2.0")
        self.assertEqual(updater.match_app("Fig_Web_2.0.1.zip", apps)[0]["id"], "fig")
        self.assertIsNone(updater.match_app("whatever.zip", apps))
        # a loose release pattern must never capture unrelated files
        self.assertIsNone(updater.match_app("lesson-builder-web-v1.0.0.zip", apps))


class AutoRecognitionTests(Base):
    def test_detect_app_from_names(self):
        cases = {
            "pdfcraft-web-v1.2.0.zip": ("pdfcraft", "pdfcraft-web-", "v1.2.0"),
            "Quran_Tools_2.3.zip": ("quran-tools", "Quran_Tools_", "2.3"),
            "app-1.2.3-win.zip": ("app", "app-", "1.2.3-win"),
            "tool2-v3.zip": ("tool2", "tool2-", "v3"),
            "admin-v1.0.zip": ("admin-app", "admin-", "v1.0"),      # reserved id is avoided
            "docs-web-1.0.0-beta.2": ("docs", "docs-web-", "1.0.0-beta.2"),   # folder name, no .zip
        }
        for name, (app_id, prefix, tag) in cases.items():
            det = updater.detect_app(name)
            self.assertEqual((det["id"], det["folder_prefix"], det["tag"]), (app_id, prefix, tag), name)
        for name in ("notes.zip", "my app 1.0.zip", "x-1.zip", "report_2024.zip"):
            self.assertIsNone(updater.detect_app(name), name)

    def test_batch_of_zips_creates_apps_without_any_setup(self):
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {"backup_count": 1}, "apps": []}))
        src = Path(self.tmp, "batch")
        src.mkdir()
        for n in ("lesson-builder-web-v1.0.0", "lesson-builder-web-v1.1.0", "Quran_Tools_2.3",
                  "Quran_Tools_2.4", "readme"):
            make_zip(src / (n + ".zip"), n)
        result = updater.import_paths([str(src)])
        apps = {a["id"]: a for a in cfg.load_config()["apps"]}
        self.assertEqual(sorted(apps), ["lesson-builder", "quran-tools"])
        self.assertEqual(apps["quran-tools"]["folder_prefix"], "Quran_Tools_")
        self.assertEqual(sorted(result["created"]), ["lesson-builder", "quran-tools"])
        cfg.invalidate_cache()
        live = cfg.discover_apps()
        self.assertEqual(live["lesson-builder"]["version"], "lesson-builder-web-v1.1.0")
        self.assertEqual(live["quran-tools"]["version"], "Quran_Tools_2.4")
        self.assertEqual([p.name for p, _ in result["skipped"]], ["readme.zip"])
        self.assertEqual(cfg.load_config()["settings"]["backup_count"], 1)   # settings untouched

    def test_can_be_turned_off(self):
        Path(self.tmp, "apps.json").write_text(json.dumps(
            {"settings": {"auto_create_apps": False}, "apps": []}))
        z = make_zip(Path(self.tmp, "zed-v1.0.zip"), "z")
        result = updater.import_paths([str(z)])
        self.assertEqual((cfg.load_config()["apps"], len(result["skipped"])), ([], 1))

    def test_same_app_with_other_punctuation_is_not_duplicated(self):
        z = make_zip(Path(self.tmp, "Demo_Web_4.0.0.zip"), "d")     # existing app: demo-web-
        updater.import_paths([str(z)])
        self.assertEqual([a["id"] for a in cfg.load_config()["apps"]], ["demo"])
        self.assertEqual(self.active(), "demo-web-4.0.0")

    def test_overlapping_prefix_is_refused_not_merged(self):
        Path(self.tmp, "apps.json").write_text(json.dumps({"apps": [
            {"id": "alpha-beta", "folder_prefix": "alpha-beta-", "title": "Alpha Beta"}]}))
        z = make_zip(Path(self.tmp, "alpha-v1.0.zip"), "t")   # "alpha-" is a prefix of "alpha-beta-"
        result = updater.import_paths([str(z)])
        self.assertEqual(len(cfg.load_config()["apps"]), 1)
        self.assertIn("overlaps", result["skipped"][0][1])

    def test_inbox_creates_unknown_app(self):
        box = inbox.inbox_dir()
        box.mkdir()
        make_zip(box / "brand-new-web-v0.1.0.zip", "b")
        sizes = {}
        inbox.process_once(sizes)
        inbox.process_once(sizes)
        ids = [a["id"] for a in cfg.load_config()["apps"]]
        self.assertIn("brand-new", ids)
        cfg.invalidate_cache()
        self.assertIn("brand-new", cfg.discover_apps())

    def test_cli_reports_created_apps(self):
        z = make_zip(Path(self.tmp, "gamma-v2.0.0.zip"), "g")
        self.assertEqual(updater.main(["--import", str(z)]), 0)
        self.assertIn("gamma", [a["id"] for a in cfg.load_config()["apps"]])


class DiskSpaceTests(Base):
    def test_install_refuses_when_disk_is_full(self):
        usage = collections.namedtuple("usage", "total used free")
        real = updater.shutil.disk_usage
        updater.shutil.disk_usage = lambda p: usage(10, 10, 1024)
        try:
            with self.assertRaises(updater.UpdateError):
                updater.install_zip(APP, self.zip("demo-web-v1.zip"), "v1")
        finally:
            updater.shutil.disk_usage = real
        self.assertEqual(cfg.installed_folders(APP), [])


class SchedulerTests(Base):
    def setUp(self):
        super().setUp()
        self._rl, self._ua = updater.release_list, updater.update_app

    def tearDown(self):
        updater.release_list, updater.update_app = self._rl, self._ua
        super().tearDown()

    def releases(self, tag):
        updater.release_list = lambda app: [{"tag": tag, "prerelease": False, "published": None,
                                             "assets": [{"name": "demo-web-%s.zip" % tag, "size": 1}]}]

    def test_reports_update_without_installing(self):
        updater.install_zip(APP, self.zip("demo-web-v1.zip"), "v1")
        self.releases("v2")
        entry = scheduler.check_app(APP, install=False)
        self.assertEqual((entry["tag"], entry["update"]), ("v2", True))

    def test_auto_install_and_rollback_protection(self):
        installed = []
        updater.update_app = lambda app, tag=None, **k: (
            installed.append(tag), updater.install_zip(app, self.zip("demo-web-%s.zip" % tag), tag))
        updater.install_zip(APP, self.zip("demo-web-v1.zip"), "v1")
        self.releases("v2")
        scheduler.check_app(APP, install=True)
        self.assertEqual(installed, ["v2"])
        self.assertEqual(self.active(), "demo-web-v2")
        updater.rollback(APP)                       # operator deliberately goes back
        self.assertEqual(self.active(), "demo-web-v1")
        scheduler.check_app(APP, install=True)      # v2 is still on disk -> must not undo it
        self.assertEqual(installed, ["v2"])
        self.assertEqual(self.active(), "demo-web-v1")

    def test_offline_error_is_recorded_not_raised(self):
        def boom(app):
            raise OSError("no route")
        updater.release_list = boom
        entry = scheduler.check_app(APP)
        self.assertTrue(entry["error"])


class MiscTests(Base):
    def test_data_lives_outside_the_program_folder(self):
        prog = Path(self.tmp, "program")
        prog.mkdir()
        win = {"ProgramData": "C:\\ProgramData"}
        self.assertEqual(cfg.default_data_dir("nt", win, prog, True), Path("C:\\ProgramData") / "CraftWebServer")
        self.assertEqual(cfg.default_data_dir("nt", win, prog, False), Path("C:\\ProgramData") / "CraftWebServer")
        self.assertEqual(cfg.default_data_dir("nt", {}, prog, False), Path("C:\\ProgramData") / "CraftWebServer")
        self.assertEqual(cfg.default_data_dir("posix", {"XDG_DATA_HOME": "/xdg"}, prog, True),
                         Path("/xdg/craft-web-server"))
        self.assertEqual(cfg.default_data_dir("posix", {}, prog, False), prog)     # source tree on Linux
        (prog / "portable.flag").write_text("")                                      # portable mode
        self.assertEqual(cfg.default_data_dir("nt", win, prog, True), prog)

    def test_legacy_data_is_moved_once_and_never_overwritten(self):
        prog, data = Path(self.tmp, "program"), Path(self.tmp, "data")
        (prog / "root" / "pdfcraft-web-v1").mkdir(parents=True)
        (prog / "cache").mkdir()
        (prog / "admin.json").write_text('{"password": "hash"}')
        (prog / "apps.json").write_text('{"apps": []}')
        (prog / "server.py").write_text("# the program stays")
        self.assertEqual(cfg.legacy_data(prog, data), ["admin.json", "apps.json", "root", "cache"])
        moved = cfg.migrate_legacy(lambda m: None, prog, data)
        self.assertEqual(sorted(moved), ["admin.json", "apps.json", "cache", "root"])
        self.assertEqual((data / "admin.json").read_text(), '{"password": "hash"}')
        self.assertTrue((data / "root" / "pdfcraft-web-v1").is_dir())
        self.assertTrue((prog / "server.py").exists())
        self.assertEqual(cfg.migrate_legacy(lambda m: None, prog, data), [])         # nothing left to move
        (prog / "admin.json").write_text("new")                                       # a stray second copy
        cfg.migrate_legacy(lambda m: None, prog, data)
        self.assertEqual((data / "admin.json").read_text(), '{"password": "hash"}')  # never overwritten

    def test_a_fresh_program_folder_has_no_legacy_data(self):
        prog, data = Path(self.tmp, "program"), Path(self.tmp, "data")
        (prog / "root").mkdir(parents=True)
        (prog / "root" / ".gitkeep").write_text("")
        (prog / "apps.json").write_text("{}")                                         # just the shipped template
        self.assertEqual(cfg.legacy_data(prog, data), [])
        self.assertEqual(cfg.legacy_data(prog, prog), [])

    def test_command_hints_match_how_the_program_runs(self):
        self.assertEqual(cfg.cli("passwd"), "python server.py --set-admin-password")
        sys.frozen = True
        real = sys.executable
        sys.executable = str(Path(self.tmp, "craft-web-server.exe"))
        try:
            self.assertEqual(cfg.cli("passwd"), "craft-web-server.exe passwd")
        finally:
            del sys.frozen
            sys.executable = real

    def test_default_config_is_created_on_a_clean_folder(self):
        Path(self.tmp, "apps.json").unlink()
        cfg.ensure_default_config()
        ids = [a["id"] for a in cfg.load_config()["apps"]]
        self.assertEqual(ids, ["pdfcraft", "figcraft"])


class DashboardCacheApiTests(Base):
    def setUp(self):
        super().setUp()
        security.set_password("correct horse battery")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AdminHandler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]
        self.cookie = self.csrf = None
        r, d = self.call("POST", "/admin/api/login", {"password": "correct horse battery"})
        self.cookie, self.csrf = r.getheader("Set-Cookie").split(";")[0], d["csrf"]

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

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

    def test_overview_cache_match_install_delete(self):
        updater.install_zip(APP, self.zip("demo-web-v1.0.0.zip"), "v1.0.0")
        updater.install_zip(APP, self.zip("demo-web-v2.0.0.zip"), "v2.0.0")
        updater.install_zip(APP, self.zip("demo-web-v3.0.0.zip"), "v3.0.0")
        r, d = self.call("GET", "/admin/api/overview")
        app = d["apps"][0]
        self.assertEqual(len(app["cache"]), 3)
        self.assertEqual(d["server"]["admin_port"], 8081)
        r, d = self.call("POST", "/admin/api/match", {"names": ["demo-web-v9.zip", "nope.zip",
                         "Zeta_Kit_1.0.zip", "Zeta_Kit_1.1.zip", "other-app-v2.zip"]})
        m = d["matches"]
        self.assertEqual([x["app"] for x in m], ["demo", "", "", "", ""])
        self.assertIsNone(m[1]["suggest"])
        self.assertEqual(m[2]["suggest"]["id"], "zeta-kit")                 # recognised, not created yet
        self.assertEqual(m[2]["suggest"], m[3]["suggest"])                    # one new app for both files
        self.assertEqual((m[4]["suggest"]["id"], m[4]["tag"]), ("other-app", "v2"))
        self.assertEqual([a["id"] for a in cfg.load_config()["apps"]], ["demo"])   # preview changes nothing
        name = [c for c in app["cache"] if c["tag"] == "v1.0.0"][0]["name"]
        r, d = self.call("POST", "/admin/api/cache-install", {"app": "demo", "name": name})
        self.assertEqual(r.status, 200, d)
        for _ in range(100):
            r, j = self.call("GET", "/admin/api/job?id=" + d["job"])
            if j["job"]["status"] != "running":
                break
        self.assertEqual(j["job"]["status"], "done")
        self.assertEqual(self.active(), "demo-web-v1.0.0")
        r, d = self.call("POST", "/admin/api/cache-delete", {"app": "demo", "name": name})
        self.assertEqual(r.status, 200)
        r, d = self.call("POST", "/admin/api/cache-delete", {"app": "demo", "name": "../x"})
        self.assertEqual(r.status, 404)


if __name__ == "__main__":
    unittest.main()

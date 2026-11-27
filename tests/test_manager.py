import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import manager, security, selfupdate, service, syscheck  # noqa: E402
from craftweb import config as cfg  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {}, "apps": []}))
        cfg.invalidate_cache()
        self.saved = {k: getattr(service, k) for k in ("install", "uninstall", "start", "stop", "restart", "health",
                                                       "supervisor_alive", "wait_until")}
        self.saved_misc = (cfg.is_admin, selfupdate.check, selfupdate.stage, selfupdate.apply_staged,
                           syscheck.NETWORK_CHECKS, manager.open_local)
        cfg.is_admin = lambda: True
        service.health = lambda *a, **k: None
        self.server = manager.make_server(0)
        self.state = self.server.state
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.state.port
        self.cookie = self.csrf = None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        for k, v in self.saved.items():
            setattr(service, k, v)
        (cfg.is_admin, selfupdate.check, selfupdate.stage, selfupdate.apply_staged,
         syscheck.NETWORK_CHECKS, manager.open_local) = self.saved_misc
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def req(self, method, path, body=None, headers=None, host=None, cookie=True, csrf=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdr = {"Host": host or "127.0.0.1:%d" % self.port}
        hdr.update(headers or {})
        if cookie and self.cookie:
            hdr["Cookie"] = self.cookie
        if csrf and self.csrf and method == "POST":
            hdr["X-CSRF-Token"] = self.csrf
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdr["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=hdr)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r, json.loads(raw)
        except ValueError:
            return r, raw

    def login(self):
        r, _ = self.req("GET", "/?t=" + self.state.token, cookie=False)
        self.assertEqual(r.status, 302)
        self.cookie = r.getheader("Set-Cookie").split(";")[0]
        r, d = self.req("GET", "/api/session")
        self.csrf = d["csrf"]

    def job(self, job_id):
        for _ in range(200):
            r, d = self.req("GET", "/api/job?id=" + job_id)
            if d["job"]["status"] != "running":
                return d["job"]
            time.sleep(0.05)
        self.fail("job did not finish")


class AccessTests(Base):
    def test_nothing_is_reachable_without_the_secret(self):
        for path in ("/", "/api/status", "/manager.js", "/api/doctor"):
            r, _ = self.req("GET", path)
            self.assertEqual(r.status, 403, path)
        r, _ = self.req("GET", "/?t=wrong-token")
        self.assertEqual(r.status, 403)

    def test_the_link_sets_a_strict_cookie_and_then_the_page_loads(self):
        r, _ = self.req("GET", "/?t=" + self.state.token)
        cookie = r.getheader("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertEqual(r.getheader("Location"), "/")
        self.cookie = cookie.split(";")[0]
        r, body = self.req("GET", "/")
        self.assertEqual(r.status, 200)
        self.assertIn(b"manager.js", body)
        self.assertIn("default-src 'none'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("X-Frame-Options"), "DENY")

    def test_dns_rebinding_is_blocked_by_the_host_check(self):
        self.login()
        for host in ("evil.example", "evil.example:%d" % self.port, "127.0.0.1", "192.168.1.5:%d" % self.port):
            r, _ = self.req("GET", "/api/status", host=host)
            self.assertEqual(r.status, 403, host)
        self.assertEqual(self.req("GET", "/api/status", host="localhost:%d" % self.port)[0].status, 200)

    def test_posts_need_the_csrf_token_and_a_matching_origin(self):
        self.login()
        r, d = self.req("POST", "/api/password", {"password": "x" * 12}, csrf=False)
        self.assertEqual((r.status, d["code"]), (403, "csrf"))
        r, d = self.req("POST", "/api/password", {"password": "x" * 12}, headers={"Origin": "http://evil.example"})
        self.assertEqual((r.status, d["code"]), (403, "csrf"))
        r, d = self.req("POST", "/api/password", {"password": "x" * 12})
        self.assertEqual(r.status, 200)

    def test_only_whitelisted_files_are_served(self):
        self.login()
        for path in ("/../apps.json", "/manager.py", "/%2e%2e/apps.json", "/__init__.py", "/index.html/../../x"):
            self.assertEqual(self.req("GET", path)[0].status, 404, path)
        r, _ = self.req("GET", "/manager.css")
        self.assertEqual(r.status, 200)

    def test_unknown_logs_are_refused(self):
        self.login()
        for name in ("../apps.json", "admin", "..%2fapps.json"):
            self.assertEqual(self.req("GET", "/api/log?name=" + name)[0].status, 400, name)
        Path(self.tmp, "logs").mkdir()
        Path(self.tmp, "logs", "server.log").write_text("hello log")
        self.assertEqual(self.req("GET", "/api/log?name=server")[1]["text"], "hello log")


class ActionTests(Base):
    def setUp(self):
        super().setUp()
        self.calls = []
        service.install = lambda log=print, wait=25: (self.calls.append("install"), log("installing"))
        service.uninstall = lambda log=print: self.calls.append("uninstall")
        service.start = lambda log=print: self.calls.append("start")
        service.stop = lambda log=print, wait=20: self.calls.append("stop")
        service.restart = lambda log=print: self.calls.append("restart")
        self.login()

    def test_install_needs_a_password_first(self):
        r, d = self.req("POST", "/api/action", {"name": "install"})
        j = self.job(d["job"])
        self.assertEqual(j["status"], "failed")
        self.assertIn("Choose a dashboard password", "\n".join(j["log"]))
        self.assertEqual(self.calls, [])
        r, d = self.req("POST", "/api/action", {"name": "install", "password": "short"})
        self.assertEqual(self.job(d["job"])["status"], "failed")
        r, d = self.req("POST", "/api/action", {"name": "install", "password": "a long enough password"})
        self.assertEqual(self.job(d["job"])["status"], "done")
        self.assertEqual(self.calls, ["install"])
        self.assertTrue(security.verify_password("a long enough password", security.password_hash()))

    def test_an_existing_password_is_kept_and_not_asked_again(self):
        security.set_password("my first long password")
        r, d = self.req("POST", "/api/action", {"name": "install", "password": "ignored new one!!"})
        self.assertEqual(self.job(d["job"])["status"], "done")
        self.assertTrue(security.verify_password("my first long password", security.password_hash()))

    def test_privileged_actions_need_administrator_rights(self):
        cfg.is_admin = lambda: False
        for name in ("install", "uninstall", "migrate"):
            r, d = self.req("POST", "/api/action", {"name": name})
            self.assertEqual((r.status, d["code"]), (403, "need_admin"), name)
        r, d = self.req("POST", "/api/action", {"name": "restart"})          # restart/start/stop go through flags
        self.assertEqual(r.status, 200)
        self.job(d["job"])

    def test_simple_actions_and_unknown_ones(self):
        for name in ("start", "stop", "restart", "uninstall"):
            r, d = self.req("POST", "/api/action", {"name": name})
            self.assertEqual(self.job(d["job"])["status"], "done", name)
        self.assertEqual(self.calls, ["start", "stop", "restart", "uninstall"])
        r, d = self.req("POST", "/api/action", {"name": "format-disk"})
        self.assertEqual((r.status, d["code"]), (400, "bad_request"))

    def test_only_one_action_at_a_time(self):
        gate = threading.Event()
        service.start = lambda log=print: gate.wait(5)
        r, d = self.req("POST", "/api/action", {"name": "start"})
        r2, d2 = self.req("POST", "/api/action", {"name": "restart"})
        self.assertEqual((r2.status, d2["code"]), (409, "busy"))
        gate.set()
        self.job(d["job"])

    def test_status_doctor_and_password(self):
        r, d = self.req("GET", "/api/status")
        self.assertEqual((r.status, d["running"], d["installed"], d["is_admin"]), (200, False, False, True))
        self.assertIn("data_dir", d)
        syscheck.NETWORK_CHECKS = []
        r, d = self.req("GET", "/api/doctor")
        self.assertEqual(r.status, 200)
        self.assertIn("server", [c["id"] for c in d["checks"]])
        r, d = self.req("POST", "/api/password", {"password": "tiny"})
        self.assertEqual((r.status, d["code"]), (400, "weak_password"))

    def test_open_targets_are_whitelisted(self):
        opened = []
        manager.open_local = lambda what: opened.append(what)
        r, _ = self.req("POST", "/api/open", {"what": "dashboard"})
        self.assertEqual((r.status, opened), (200, ["dashboard"]))
        manager.open_local = self.saved_misc[5]
        r, d = self.req("POST", "/api/open", {"what": "/etc/passwd"})
        self.assertEqual((r.status, d["code"]), (400, "bad_request"))


class UpdateFlowTests(Base):
    def setUp(self):
        super().setUp()
        self.events = []
        selfupdate.check = lambda *a, **k: {"current": "1", "latest": "2", "update": True, "supported": True,
                                            "kind": "source", "error": None, "release": {"big": "dict"}}
        selfupdate.stage = lambda info=None, log=print: (self.events.append("stage"), log("staged"), "2")[2]
        selfupdate.apply_staged = lambda log=print: (self.events.append("apply"), True)[1]
        self.login()

    def test_update_check_hides_the_raw_release(self):
        r, d = self.req("POST", "/api/update-check", {})
        self.assertEqual((d["latest"], d["update"]), ("2", True))
        self.assertNotIn("release", d)

    def test_with_the_watchdog_a_restart_is_requested(self):
        service.supervisor_alive = lambda: True
        service.wait_until = lambda check, timeout, interval=0.5: True
        r, d = self.req("POST", "/api/update", {})
        self.assertEqual(self.job(d["job"])["status"], "done")
        self.assertEqual(self.events, ["stage"])                      # the watchdog applies it while restarting
        self.assertTrue(service.flag_path("restart").exists())

    def test_without_the_watchdog_it_is_applied_directly(self):
        service.supervisor_alive = lambda: False
        r, d = self.req("POST", "/api/update", {})
        j = self.job(d["job"])
        self.assertEqual(j["status"], "done")
        self.assertEqual(self.events, ["stage", "apply"])
        self.assertIn("Start the server", "\n".join(j["log"]))

    def test_a_refused_update_is_reported_in_the_log(self):
        def refuse(info=None, log=print):
            raise RuntimeError("Checksum mismatch")
        selfupdate.stage = refuse
        r, d = self.req("POST", "/api/update", {})
        j = self.job(d["job"])
        self.assertEqual(j["status"], "failed")
        self.assertIn("Checksum mismatch", "\n".join(j["log"]))


class LifecycleTests(Base):
    def test_quit_ends_the_program(self):
        done = threading.Event()
        server = manager.make_server(0)
        threading.Thread(target=lambda: (manager.serve(server, open_browser=False, check=60), done.set()),
                         daemon=True).start()
        port, token = server.state.port, server.state.token
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("GET", "/?t=" + token, headers={"Host": "127.0.0.1:%d" % port})
        r = c.getresponse()
        r.read()
        cookie = r.getheader("Set-Cookie").split(";")[0]
        c.close()
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("POST", "/api/quit", body=b"{}", headers={"Host": "127.0.0.1:%d" % port, "Cookie": cookie,
                                                              "X-CSRF-Token": server.state.csrf,
                                                              "Content-Type": "application/json"})
        self.assertEqual(c.getresponse().status, 200)
        c.close()
        self.assertTrue(done.wait(5))

    def test_it_closes_itself_when_nobody_uses_it(self):
        server = manager.make_server(0)
        done = threading.Event()
        threading.Thread(target=lambda: (manager.serve(server, open_browser=False, idle=0.2, check=0.05), done.set()),
                         daemon=True).start()
        self.assertTrue(done.wait(5))

    def test_service_cli(self):
        service.start = lambda log=print: self.__class__.started.append(1)
        self.__class__.started = []
        self.assertEqual(manager.service_cli(["start"]), 0)
        self.assertEqual(self.__class__.started, [1])
        self.assertEqual(manager.service_cli(["nonsense"]), 2)
        security.set_password("a long enough password")
        cfg.is_admin = lambda: False
        self.assertEqual(manager.service_cli(["install"]), 1)          # not elevated: clear failure, exit 1


if __name__ == "__main__":
    unittest.main()

import hashlib
import http.client
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import __version__, admin, scheduler, security, selfupdate, service, supervisor, syscheck, updater  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, CraftHandler  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        os.environ.pop("CRAFTWEB_SUPERVISED", None)
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {}, "apps": []}))
        cfg.invalidate_cache()
        admin.reset()
        scheduler.SELF.clear()
        self.saved = {k: getattr(service, k) for k in ("run", "platform_name", "UNIT_PATH", "health", "start", "is_installed",
                                                       "firewall_rule_exists", "supervisor_alive")}
        self.saved_cfg = (cfg.is_admin, cfg.program_dir)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(service, k, v)
        cfg.is_admin, cfg.program_dir = self.saved_cfg
        os.environ.pop("CRAFTWEB_HOME", None)
        os.environ.pop("CRAFTWEB_SUPERVISED", None)
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------- service layer
class ServiceTests(Base):
    def setUp(self):
        super().setUp()
        self.cmds = []
        service.run = lambda cmd, timeout=60: (self.cmds.append(cmd) or (0, ""))
        service.health = lambda *a, **k: {"status": "ok", "version": "x"}
        service.start = lambda log=print: self.cmds.append(["<start>"])
        cfg.is_admin = lambda: True

    def test_task_xml_is_valid_and_survives_odd_paths(self):
        xml = service.task_xml([r"C:\Program Files\Craft & Co\craft-web-server.exe", "supervise"],
                               r"C:\Program Files\Craft & Co")
        root = ET.fromstring(xml.replace('encoding="UTF-16"', 'encoding="UTF-8"'))
        self.assertEqual(root.find(".//t:Command", NS).text, r"C:\Program Files\Craft & Co\craft-web-server.exe")
        self.assertEqual(root.find(".//t:Arguments", NS).text, "supervise")
        self.assertEqual(root.find(".//t:UserId", NS).text, "S-1-5-18")                 # SYSTEM
        self.assertEqual(root.find(".//t:ExecutionTimeLimit", NS).text, "PT0S")        # never stopped after 72 h
        self.assertEqual(root.find(".//t:DisallowStartIfOnBatteries", NS).text, "false")
        self.assertIsNotNone(root.find(".//t:BootTrigger", NS))
        self.assertEqual(root.find(".//t:RestartOnFailure/t:Count", NS).text, "999")

    def test_arguments_with_spaces_are_quoted(self):
        xml = service.task_xml([r"C:\Python\python.exe", r"C:\My Apps\run.py", "supervise"], r"C:\My Apps")
        root = ET.fromstring(xml.replace('encoding="UTF-16"', 'encoding="UTF-8"'))
        self.assertEqual(root.find(".//t:Arguments", NS).text, r'"C:\My Apps\run.py" supervise')

    def test_windows_install_sequence(self):
        service.platform_name = lambda: "windows"
        logs = []
        service.install(logs.append, wait=2)
        flat = [" ".join(c) for c in self.cmds]
        self.assertTrue(any(c.startswith("netsh advfirewall firewall delete rule") for c in flat))
        add = next(c for c in flat if "firewall add rule" in c)
        self.assertIn("profile=private,domain", add)
        self.assertIn("program=" + str(cfg.server_program()), add)
        create = next(c for c in self.cmds if c[0] == "schtasks")
        self.assertEqual(create[1:4], ["/create", "/tn", service.TASK])
        self.assertEqual(create[4], "/xml")
        self.assertEqual(create[-1], "/f")
        xml = Path(create[5]).read_bytes()
        self.assertTrue(xml.startswith((b"\xff\xfe", b"\xfe\xff")))                    # UTF-16 with BOM
        ET.fromstring(xml.decode("utf-16").replace('encoding="UTF-16"', 'encoding="UTF-8"'))
        self.assertEqual(self.cmds[-1], ["<start>"])
        self.assertIn("will start by itself", logs[-1])
        self.assertTrue(Path(self.tmp, "apps.json").exists())

    def test_install_needs_administrator_and_reports_failures(self):
        service.platform_name = lambda: "windows"
        cfg.is_admin = lambda: False
        with self.assertRaises(PermissionError):
            service.install(lambda m: None)
        cfg.is_admin = lambda: True
        service.run = lambda cmd, timeout=60: (1, "Access is denied") if cmd[0] == "schtasks" else (0, "")
        with self.assertRaises(RuntimeError) as e:
            service.install(lambda m: None)
        self.assertIn("Access is denied", str(e.exception))

    def test_install_fails_clearly_when_the_server_never_answers(self):
        service.platform_name = lambda: "windows"
        service.health = lambda *a, **k: None
        with self.assertRaises(RuntimeError) as e:
            service.install(lambda m: None, wait=1)
        self.assertIn("did not answer", str(e.exception))

    def test_linux_install_writes_a_systemd_unit(self):
        service.platform_name = lambda: "linux"
        service.UNIT_PATH = Path(self.tmp, "craft-web-server.service")
        service.install(lambda m: None, wait=2)
        unit = service.UNIT_PATH.read_text()
        self.assertIn("CRAFTWEB_HOME=%s" % self.tmp, unit)                             # data location is pinned
        self.assertIn("supervise", unit)
        self.assertIn("Restart=always", unit)
        self.assertIn(["systemctl", "enable", service.UNIT_NAME], self.cmds)

    def test_uninstall_removes_autostart_but_not_data(self):
        service.platform_name = lambda: "windows"
        service.uninstall(lambda m: None)
        flat = [" ".join(c) for c in self.cmds]
        self.assertIn("schtasks /delete /tn %s /f" % service.TASK, flat)
        self.assertTrue(any("firewall delete rule" in c for c in flat))
        self.assertTrue(Path(self.tmp, "apps.json").exists())

    def test_flags_and_pid_files(self):
        service.set_flag("restart")
        self.assertTrue(service.flag_path("restart").exists())
        service.clear_flag("restart")
        service.clear_flag("restart")                                                   # harmless twice
        self.assertFalse(service.flag_path("restart").exists())
        service.write_pid("supervisor", os.getpid())
        self.assertEqual(service.read_pid("supervisor"), os.getpid())
        self.assertTrue(service.supervisor_alive())
        self.assertFalse(service.pid_alive(0))
        self.assertFalse(service.pid_alive(4194000))
        self.assertEqual(service.read_pid("nothing"), 0)

    def test_stop_sets_the_flag_and_waits_for_the_supervisor(self):
        service.write_pid("supervisor", os.getpid())
        alive = {"n": 0}

        def fake_alive():
            alive["n"] += 1
            return not service.flag_path("stop").exists()
        real = service.supervisor_alive
        service.supervisor_alive = fake_alive
        try:
            service.stop(lambda m: None, wait=3)
        finally:
            service.supervisor_alive = real
        self.assertTrue(service.flag_path("stop").exists())

    def test_health_talks_to_a_real_server(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), CraftHandler)
        httpd.tls = False
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (httpd.shutdown(), httpd.server_close()))
        service.health = self.saved["health"]
        self.assertEqual(service.health(httpd.server_address[1])["status"], "ok")
        self.assertIsNone(service.health(1, timeout=1))


# ---------------------------------------------------------------- supervisor (real child processes)
class SupervisorTests(Base):
    def setUp(self):
        super().setUp()
        cfg.program_dir = lambda: Path(self.tmp)
        self.counter = Path(self.tmp, "runs")

    def child(self, body):
        """A tiny python program; `n` is how many times it has been started."""
        script = Path(self.tmp, "child.py")
        script.write_text("import pathlib, sys, time\n"
                          "c = pathlib.Path(%r)\n"
                          "n = int(c.read_text()) + 1 if c.exists() else 1\n"
                          "c.write_text(str(n))\n%s\n" % (str(self.counter), body))
        return [sys.executable, str(script)]

    def runs(self):
        return int(self.counter.read_text()) if self.counter.exists() else 0

    def test_exit_code_75_restarts_and_a_normal_exit_ends_it(self):
        cmd = self.child("sys.exit(75 if n < 3 else 0)")
        self.assertEqual(supervisor.supervise(cmd, poll=0.05, log=lambda m: None), 0)
        self.assertEqual(self.runs(), 3)
        self.assertEqual(service.read_pid("supervisor"), 0)                           # pid file cleaned

    def test_a_crashing_server_is_restarted_with_a_delay(self):
        cmd = self.child("sys.exit(3)")
        started = time.time()
        supervisor.supervise(cmd, poll=0.05, backoff=(0.2, 0.4), max_runs=3, log=lambda m: None)
        self.assertEqual(self.runs(), 3)
        self.assertGreaterEqual(time.time() - started, 0.5)                           # waited between crashes

    def test_restart_flag_restarts_a_healthy_server(self):
        cmd = self.child("time.sleep(60) if n == 1 else sys.exit(0)")
        threading.Timer(0.6, lambda: service.set_flag("restart")).start()
        supervisor.supervise(cmd, poll=0.05, log=lambda m: None)
        self.assertEqual(self.runs(), 2)
        self.assertFalse(service.flag_path("restart").exists())

    def test_stop_flag_ends_the_server_and_the_supervisor(self):
        cmd = self.child("time.sleep(60)")
        threading.Timer(0.6, lambda: service.set_flag("stop")).start()
        started = time.time()
        supervisor.supervise(cmd, poll=0.05, log=lambda m: None)
        self.assertLess(time.time() - started, 20)
        self.assertEqual(self.runs(), 1)
        self.assertFalse(service.pid_alive(service.read_pid("server")))

    def test_only_one_supervisor_runs(self):
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        self.addCleanup(sleeper.wait)
        self.addCleanup(sleeper.kill)
        service.write_pid("supervisor", sleeper.pid)
        messages = []
        self.assertEqual(supervisor.supervise(self.child("sys.exit(0)"), poll=0.05, log=messages.append), 0)
        self.assertEqual(self.runs(), 0)
        self.assertIn("already running", messages[0])

    def test_the_server_console_output_is_captured(self):
        cmd = self.child("print('hello from the server'); sys.exit(0)")
        supervisor.supervise(cmd, poll=0.05, log=lambda m: None)
        self.assertIn("hello from the server", Path(self.tmp, "logs", "console.log").read_text())

    def test_on_windows_the_whole_process_tree_is_ended(self):
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(sleeper.wait)
        calls = []
        real_run = supervisor.subprocess.run

        def fake_run(cmd, **kw):
            calls.append(cmd)
            sleeper.kill()                      # what taskkill /T /F would do
            return subprocess.CompletedProcess(cmd, 0, "", "")
        supervisor.subprocess.run = fake_run
        try:
            supervisor._stop(sleeper, windows=True)
        finally:
            supervisor.subprocess.run = real_run
        self.assertEqual(calls, [["taskkill", "/PID", str(sleeper.pid), "/T", "/F"]])
        self.assertIsNotNone(sleeper.poll())

    def test_a_new_version_that_keeps_crashing_is_rolled_back(self):
        target, old = Path(self.tmp, "program.bin"), Path(self.tmp, "program.bin.old")
        target.write_text("NEW")
        old.write_text("OLD")
        cfg.save_json(selfupdate.stage_dir() / "pending.json", {
            "from": "1.0.0", "to": "2.0.0", "started": 0, "crashes": 0, "swapped": [[str(target), str(old)]]})
        cmd = self.child("sys.exit(1)")
        supervisor.supervise(cmd, poll=0.05, backoff=(0.05,), max_runs=2, log=lambda m: None)
        self.assertEqual(target.read_text(), "OLD")
        self.assertIsNone(selfupdate.pending())
        self.assertEqual(cfg._load_json(selfupdate.stage_dir() / "last-result.json", {})["rolled_back_from"], "2.0.0")


# ---------------------------------------------------------------- self update
def project_zip(path, version, root="craft-web-server"):
    """The real project, as a release package, claiming `version`."""
    with zipfile.ZipFile(path, "w") as z:
        for folder in ("craftweb",):
            for f in (PROJECT / folder).rglob("*"):
                if f.is_file() and "__pycache__" not in f.parts:
                    z.write(f, "%s/%s" % (root, f.relative_to(PROJECT).as_posix()))
        for name in ("server.py", "updater.py", "run.py"):
            z.write(PROJECT / name, "%s/%s" % (root, name))
        z.writestr("%s/VERSION" % root, version + "\n")
    return Path(path)


class SelfUpdateBase(Base):
    def setUp(self):
        super().setUp()
        self.real = (updater.get_releases, updater.download, selfupdate.install_kind)
        self.program = Path(self.tmp, "program")
        self.program.mkdir()
        cfg.program_dir = lambda: self.program

    def tearDown(self):
        updater.get_releases, updater.download, selfupdate.install_kind = self.real
        super().tearDown()

    def release(self, version, zip_path, name=None, digest=True, tag=None):
        sha = hashlib.sha256(Path(zip_path).read_bytes()).hexdigest()
        asset = {"name": name or selfupdate.asset_name(version, selfupdate.install_kind()), "size": 1,
                 "url": "u", "browser_download_url": "u"}
        if digest:
            asset["digest"] = "sha256:" + sha
        rel = {"tag_name": tag or "v" + version, "html_url": "https://example/r", "assets": [asset]}
        updater.get_releases = lambda *a, **k: [rel]

        def fake_download(a, dest):
            shutil.copyfile(zip_path, dest)
            return hashlib.sha256(Path(zip_path).read_bytes()).hexdigest() if digest != "corrupt" else "0" * 64
        updater.download = fake_download
        return rel


class SelfUpdateTests(SelfUpdateBase):
    def test_check_compares_versions_and_survives_being_offline(self):
        self.release("99.0.0", project_zip(Path(self.tmp, "a.zip"), "99.0.0"))
        info = selfupdate.check()
        self.assertEqual((info["current"], info["latest"], info["update"], info["supported"]),
                         (__version__, "99.0.0", True, True))
        self.release("0.0.1", project_zip(Path(self.tmp, "b.zip"), "0.0.1"))
        self.assertFalse(selfupdate.check()["update"])

        def offline(*a, **k):
            raise OSError("no route")
        updater.get_releases = offline
        info = selfupdate.check()
        self.assertTrue(info["error"])
        self.assertFalse(info["update"])

    def test_source_update_end_to_end_keeps_the_old_files_until_stable(self):
        for name in ("server.py", "updater.py", "run.py", "VERSION"):
            (self.program / name).write_text("old " + name)
        (self.program / "craftweb").mkdir()
        (self.program / "craftweb" / "old.py").write_text("old")
        (self.program / "root").mkdir()                                  # data-like folders are never touched
        (self.program / "root" / "keep.txt").write_text("keep")
        self.release("99.0.0", project_zip(Path(self.tmp, "p.zip"), "99.0.0"))
        logs = []
        self.assertEqual(selfupdate.stage(log=logs.append), "99.0.0")
        self.assertIn("The new version starts correctly.", logs)
        self.assertEqual(selfupdate.staged()["version"], "99.0.0")
        self.assertEqual((self.program / "VERSION").read_text(), "old VERSION")                # not applied yet
        self.assertTrue(selfupdate.apply_staged(lambda m: None))
        self.assertEqual((self.program / "VERSION").read_text().strip(), "99.0.0")
        self.assertTrue((self.program / "craftweb" / "__main__.py").exists())
        self.assertEqual((self.program / "VERSION.old").read_text(), "old VERSION")
        self.assertTrue((self.program / "craftweb.old" / "old.py").exists())
        self.assertEqual((self.program / "root" / "keep.txt").read_text(), "keep")
        self.assertIsNone(selfupdate.staged())
        self.assertTrue(selfupdate.pending())
        self.assertTrue(selfupdate.confirm_pending(lambda m: None))
        self.assertFalse((self.program / "VERSION.old").exists())
        self.assertFalse((self.program / "craftweb.old").exists())
        self.assertFalse(selfupdate.pending())

    def test_rollback_puts_the_old_version_back(self):
        for name in ("server.py", "run.py", "updater.py", "VERSION"):
            (self.program / name).write_text("old " + name)
        self.release("99.0.0", project_zip(Path(self.tmp, "p.zip"), "99.0.0"))
        selfupdate.stage(log=lambda m: None)
        selfupdate.apply_staged(lambda m: None)
        self.assertTrue(selfupdate.rollback(lambda m: None))
        self.assertEqual((self.program / "VERSION").read_text(), "old VERSION")
        self.assertFalse(selfupdate.rollback(lambda m: None))                                  # nothing pending

    def test_early_crashes_trigger_the_rollback_late_ones_do_not(self):
        target, old = self.program / "x.bin", self.program / "x.bin.old"
        target.write_text("NEW")
        old.write_text("OLD")
        cfg.save_json(selfupdate.stage_dir() / "pending.json", {
            "from": "1", "to": "2", "started": 0, "crashes": 0, "swapped": [[str(target), str(old)]]})
        self.assertFalse(selfupdate.note_crash(3600, lambda m: None))          # ran for an hour: not the update's fault
        self.assertFalse(selfupdate.note_crash(2, lambda m: None))             # first early crash: wait and see
        self.assertEqual(target.read_text(), "NEW")
        self.assertTrue(selfupdate.note_crash(2, lambda m: None))              # second: roll back
        self.assertEqual(target.read_text(), "OLD")

    def test_a_failed_swap_restores_everything(self):
        (self.program / "a.py").write_text("old a")
        (self.program / "b.py").write_text("old b")
        stage_root = selfupdate.stage_dir() / "9.9.9" / "x"
        stage_root.mkdir(parents=True)
        (stage_root / "a.py").write_text("new a")                                               # b.py is missing -> move fails
        cfg.save_json(selfupdate.stage_dir() / "staged.json", {"version": "9.9.9", "kind": "source",
                                                               "root": str(stage_root), "files": ["a.py", "b.py"]})
        self.assertFalse(selfupdate.apply_staged(lambda m: None))
        self.assertEqual((self.program / "a.py").read_text(), "old a")
        self.assertEqual((self.program / "b.py").read_text(), "old b")
        self.assertIsNone(selfupdate.staged())

    def test_exe_update_swaps_both_programs(self):
        selfupdate.install_kind = lambda: "exe"
        for name in ("craft-web-server.exe", "CraftManager.exe"):
            (self.program / name).write_text("old " + name)
        z = Path(self.tmp, "w.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("craft-web-server-v99.0.0-windows-x64/craft-web-server.exe", "#!/bin/sh\necho 99.0.0\n")
            f.writestr("craft-web-server-v99.0.0-windows-x64/CraftManager.exe", "manager")
            f.writestr("craft-web-server-v99.0.0-windows-x64/README.md", "docs")
        self.release("99.0.0", z)
        real_extract = updater.safe_extract

        def extract_and_chmod(zp, dest):
            real_extract(zp, dest)
            for exe in Path(dest).rglob("*.exe"):
                exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
        updater.safe_extract = extract_and_chmod
        try:
            selfupdate.stage(log=lambda m: None)
        finally:
            updater.safe_extract = real_extract
        self.assertEqual(sorted(selfupdate.staged()["files"]), ["CraftManager.exe", "craft-web-server.exe"])
        self.assertTrue(selfupdate.apply_staged(lambda m: None))
        self.assertIn("99.0.0", (self.program / "craft-web-server.exe").read_text())
        self.assertEqual((self.program / "CraftManager.exe.old").read_text(), "old CraftManager.exe")


class SelfUpdateRefusalTests(SelfUpdateBase):
    def stage_with(self, **kw):
        z = kw.pop("zip", None) or project_zip(Path(self.tmp, "p.zip"), "99.0.0")
        self.release("99.0.0", z, **kw)
        with self.assertRaises(updater.UpdateError) as e:
            selfupdate.stage(log=lambda m: None)
        self.assertIsNone(selfupdate.staged())
        return str(e.exception)

    def test_corrupt_download_is_refused(self):
        self.assertIn("Checksum mismatch", self.stage_with(digest="corrupt"))

    def test_a_release_without_a_checksum_is_refused(self):
        self.assertIn("no checksum", self.stage_with(digest=False))

    def test_a_version_that_cannot_start_is_refused_before_anything_changes(self):
        lying = project_zip(Path(self.tmp, "lying.zip"), "98.0.0")             # claims 99.0.0, really is 98.0.0
        (self.program / "VERSION").write_text("old")
        self.assertIn("did not report 99.0.0", self.stage_with(zip=lying))
        self.assertEqual((self.program / "VERSION").read_text(), "old")

    def test_missing_asset_and_unsupported_installs(self):
        self.assertIn("has no file named", self.stage_with(name="something-else.zip"))
        selfupdate.install_kind = lambda: None
        self.release("99.0.0", project_zip(Path(self.tmp, "q.zip"), "99.0.0"))
        with self.assertRaises(updater.UpdateError):
            selfupdate.stage(log=lambda m: None)

    def test_nothing_to_do_when_already_current(self):
        self.release(__version__, project_zip(Path(self.tmp, "c.zip"), __version__))
        with self.assertRaises(updater.UpdateError) as e:
            selfupdate.stage(log=lambda m: None)
        self.assertIn("up to date", str(e.exception))


# ---------------------------------------------------------------- health check
class SyscheckTests(Base):
    def setUp(self):
        super().setUp()
        service.health = lambda *a, **k: None

    def status(self, check):
        return check()["status"]

    def test_password_check(self):
        r = syscheck.check_password()
        self.assertEqual((r["status"], r["action"]), ("fail", "password"))
        security.set_password("correct horse battery")
        self.assertEqual(syscheck.check_password()["status"], "ok")

    def test_config_check(self):
        self.assertEqual(self.status(syscheck.check_config), "ok")
        Path(self.tmp, "apps.json").write_text("{ not json")
        r = syscheck.check_config()
        self.assertEqual(r["status"], "fail")
        self.assertIn("not valid JSON", r["detail"])
        Path(self.tmp, "apps.json").unlink()
        self.assertEqual(self.status(syscheck.check_config), "info")

    def test_server_check_follows_the_health_endpoint(self):
        self.assertEqual(syscheck.check_server()["action"], "start")
        service.health = lambda *a, **k: {"status": "ok", "version": "1.2.3"}
        r = syscheck.check_server()
        self.assertEqual(r["status"], "ok")
        self.assertIn("1.2.3", r["detail"])

    def test_port_check_detects_another_program(self):
        blocker = socket.socket()
        blocker.bind(("0.0.0.0", 0))
        blocker.listen(1)
        self.addCleanup(blocker.close)
        busy = blocker.getsockname()[1]
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {"port": busy, "admin_port": 0}, "apps": []}))
        r = syscheck.check_ports()
        self.assertEqual(r["status"], "fail")
        self.assertIn("used by another program", r["detail"])
        free = socket.socket()
        free.bind(("0.0.0.0", 0))
        port = free.getsockname()[1]
        free.close()
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {"port": port, "admin_port": 0}, "apps": []}))
        self.assertEqual(syscheck.check_ports()["status"], "ok")

    def test_autostart_and_firewall_checks(self):
        service.platform_name = lambda: "windows"
        service.is_installed = lambda: False
        service.firewall_rule_exists = lambda: False
        self.assertEqual(syscheck.check_autostart()["action"], "install")
        self.assertEqual(syscheck.check_firewall()["status"], "warn")
        service.is_installed = lambda: True
        service.firewall_rule_exists = lambda: True
        self.assertEqual(syscheck.check_autostart()["status"], "ok")
        self.assertEqual(syscheck.check_firewall()["status"], "ok")
        service.firewall_rule_exists = lambda: None
        self.assertEqual(syscheck.check_firewall()["status"], "info")

    def test_log_reading_is_whitelisted_and_tailed(self):
        logs = Path(self.tmp, "logs")
        logs.mkdir()
        (logs / "server.log").write_text("\n".join("line %d" % i for i in range(500)))
        self.assertEqual(syscheck.read_log("server", 3), "line 497\nline 498\nline 499")
        self.assertEqual(syscheck.read_log("console"), "")
        for bad in ("../apps.json", "admin", "/etc/passwd"):
            with self.assertRaises(KeyError):
                syscheck.read_log(bad)

    def test_recent_errors_in_the_log(self):
        logs = Path(self.tmp, "logs")
        logs.mkdir()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        old = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 3 * 86400))
        (logs / "server.log").write_text("%s,100 ERROR ancient\n%s,200 INFO fine\n" % (old, now))
        self.assertEqual(syscheck.check_logs()["status"], "ok")                     # the old error is ignored
        (logs / "server.log").write_text("%s,100 WARNING careful\n" % now)
        self.assertEqual(syscheck.check_logs()["status"], "info")
        (logs / "server.log").write_text("%s,100 ERROR something broke\n" % now)
        r = syscheck.check_logs()
        self.assertEqual(r["status"], "warn")
        self.assertIn("something broke", r["detail"])
        (logs / "server.log").write_text("")
        (logs / "console.log").write_text("Traceback (most recent call last):\n  boom\n")
        self.assertEqual(syscheck.check_logs()["status"], "warn")

    def test_run_checks_never_raises_and_summarises(self):
        original = syscheck.check_disk

        def boom():
            raise RuntimeError("disk exploded")
        syscheck.CHECKS[syscheck.CHECKS.index(original)] = boom
        try:
            report = syscheck.run_checks(network=False)
        finally:
            syscheck.CHECKS[syscheck.CHECKS.index(boom)] = original
        broken = [c for c in report["checks"] if "disk exploded" in c["detail"]]
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["status"], "fail")
        self.assertEqual(sum(report["summary"].values()), len(report["checks"]))
        self.assertGreaterEqual(len(report["checks"]), 12)


# ---------------------------------------------------------------- dashboard endpoints
class SystemApiTests(Base):
    def setUp(self):
        super().setUp()
        security.set_password("correct horse battery")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), AdminHandler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.cookie = self.csrf = None
        r, d = self.call("POST", "/admin/api/login", {"password": "correct horse battery"})
        self.cookie, self.csrf = r.getheader("Set-Cookie").split(";")[0], d["csrf"]
        self.real = (selfupdate.check, selfupdate.stage, syscheck.NETWORK_CHECKS)

    def tearDown(self):
        selfupdate.check, selfupdate.stage, syscheck.NETWORK_CHECKS = self.real
        self.httpd.shutdown()
        self.httpd.server_close()
        super().tearDown()

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_address[1], timeout=20)
        hdr = {"Content-Type": "application/json"}
        if self.cookie:
            hdr["Cookie"], hdr["X-CSRF-Token"] = self.cookie, self.csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=hdr)
        r = c.getresponse()
        data = json.loads(r.read() or b"{}")
        c.close()
        return r, data

    def test_system_info(self):
        r, d = self.call("GET", "/admin/api/system")
        self.assertEqual((r.status, d["version"], d["supervised"]), (200, __version__, False))
        self.assertEqual(d["data_dir"], str(Path(self.tmp).resolve()))

    def test_restart_and_update_need_the_watchdog(self):
        for path in ("system-restart", "system-update"):
            r, d = self.call("POST", "/admin/api/" + path, {})
            self.assertEqual((r.status, d["code"]), (409, "not_supervised"), path)
        self.assertFalse(service.flag_path("restart").exists())

    def test_restart_with_the_watchdog_sets_the_flag(self):
        os.environ["CRAFTWEB_SUPERVISED"] = "1"
        r, d = self.call("POST", "/admin/api/system-restart", {})
        self.assertEqual(r.status, 200)
        self.assertTrue(service.flag_path("restart").exists())

    def test_one_click_update_stages_then_asks_for_a_restart(self):
        os.environ["CRAFTWEB_SUPERVISED"] = "1"
        staged = []
        selfupdate.check = lambda *a, **k: {"current": "1", "latest": "9", "update": True, "supported": True,
                                            "kind": "source", "error": None, "release": {}}
        selfupdate.stage = lambda info=None, log=print: (staged.append(info["latest"]), log("staged"), "9")[2]
        r, d = self.call("POST", "/admin/api/system-update", {})
        self.assertEqual(r.status, 200, d)
        for _ in range(100):
            r, j = self.call("GET", "/admin/api/job?id=" + d["job"])
            if j["job"]["status"] != "running":
                break
            time.sleep(0.05)
        self.assertEqual(j["job"]["status"], "done", j)
        self.assertEqual(staged, ["9"])
        self.assertTrue(service.flag_path("restart").exists())
        self.assertIn("Restarting", "\n".join(j["job"]["log"]))

    def test_doctor_and_settings(self):
        syscheck.NETWORK_CHECKS = []
        r, d = self.call("GET", "/admin/api/doctor")
        self.assertEqual(r.status, 200)
        self.assertIn("password", [c["id"] for c in d["checks"]])
        r, d = self.call("POST", "/admin/api/settings", {"self_update_auto": True})
        self.assertEqual(r.status, 200)
        self.assertTrue(cfg.load_config()["settings"]["self_update_auto"])
        r, d = self.call("POST", "/admin/api/system-check", {})
        self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()


class ProgramLocationTests(Base):
    def test_the_manager_exe_registers_the_server_exe_not_itself(self):
        sys.frozen = True
        real = sys.executable
        try:
            sys.executable = str(Path(self.tmp, "CraftManager.exe"))
            self.assertEqual(cfg.server_program(), Path(self.tmp, "CraftManager.exe"))      # no sibling yet
            Path(self.tmp, "craft-web-server.exe").write_text("x")
            self.assertEqual(cfg.server_program(), Path(self.tmp, "craft-web-server.exe"))
            self.assertEqual(service.launch_command(), [str(Path(self.tmp, "craft-web-server.exe")), "supervise"])
            self.assertEqual(supervisor.server_command(), [str(Path(self.tmp, "craft-web-server.exe")), "serve"])
            self.assertEqual(cfg.cli("passwd"), "craft-web-server.exe passwd")
            sys.executable = str(Path(self.tmp, "craft-web-server.exe"))                   # the server exe itself
            self.assertEqual(cfg.server_program(), Path(self.tmp, "craft-web-server.exe"))
        finally:
            del sys.frozen
            sys.executable = real

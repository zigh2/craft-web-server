"""Keep the server running in the background and start it at every boot.

Windows: a Task Scheduler task (runs as SYSTEM at boot, no time limit, restarts on failure)
         plus a firewall rule for the program, limited to private/domain networks.
Linux:   a systemd unit.
Both start `supervise` (see supervisor.py), which restarts the server when it crashes or when
an update/restart is requested. Controllers (this module, the manager, the dashboard) talk to the
supervisor through small flag files in <data>/run/, so no OS-specific process killing is needed.

Every OS command goes through run(), which tests replace."""
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from . import config as cfg

TASK = "CraftWebServer"
FIREWALL_RULE = "Craft Web Server"
UNIT_NAME = "craft-web-server.service"
UNIT_PATH = Path("/etc/systemd/system") / UNIT_NAME
NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200 | NO_WINDOW     # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW


def run(cmd, timeout=60):
    """Run an OS command -> (return code, combined output)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=NO_WINDOW if os.name == "nt" else 0)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def platform_name():
    if os.name == "nt":
        return "windows"
    return "linux" if sys.platform.startswith("linux") else "other"


# ---------------------------------------------------------------- control files / processes
def flag_path(name):
    return cfg.run_dir() / (name + ".flag")


def set_flag(name):
    cfg.run_dir().mkdir(parents=True, exist_ok=True)
    flag_path(name).write_text(str(int(time.time())))


def clear_flag(name):
    try:
        flag_path(name).unlink()
    except OSError:
        pass


def write_pid(name, pid):
    cfg.run_dir().mkdir(parents=True, exist_ok=True)
    (cfg.run_dir() / (name + ".pid")).write_text(json.dumps({"pid": pid, "started": int(time.time())}))


def read_pid(name):
    try:
        return int(json.loads((cfg.run_dir() / (name + ".pid")).read_text())["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def pid_alive(pid):
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return bool(ok) and code.value == 259                      # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def supervisor_alive():
    return pid_alive(read_pid("supervisor"))


def wait_until(check, timeout, interval=0.5):
    end = time.time() + timeout
    while time.time() < end:
        if check():
            return True
        time.sleep(interval)
    return bool(check())


def health(port=None, timeout=3):
    """/health of the running server, or None. Local check only: a self-signed certificate is fine."""
    settings = cfg.load_config()["settings"]
    port = port or cfg.RUNTIME.get("port") or int(settings["port"])
    schemes = ["https", "http"] if settings.get("tls_cert") else ["http"]
    for scheme in schemes:
        try:
            ctx = ssl._create_unverified_context() if scheme == "https" else None
            with urllib.request.urlopen("%s://127.0.0.1:%d/health" % (scheme, port), timeout=timeout,
                                        context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            continue
    return None


# ---------------------------------------------------------------- what runs at boot
def _quote(arg):
    return '"%s"' % arg if (" " in arg or "\t" in arg) and not arg.startswith('"') else arg


def launch_command():
    """[program, arguments...] of the background supervisor."""
    if getattr(sys, "frozen", False):
        return [str(cfg.server_program()), "supervise"]
    return [sys.executable, str(cfg.program_dir() / "run.py"), "supervise"]


def task_xml(command=None, workdir=None):
    """Task Scheduler definition. The defaults of `schtasks /create` would stop the task after
    72 hours and when on battery, so the task is described in XML instead."""
    command = command or launch_command()
    workdir = str(workdir or cfg.program_dir())
    return """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Craft Web Server: hosts your Craft apps on the local network and restarts them if they stop.</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT20S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>6</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>%s</Command>
      <Arguments>%s</Arguments>
      <WorkingDirectory>%s</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
""" % (escape(command[0]), escape(" ".join(_quote(a) for a in command[1:])), escape(workdir))


def systemd_unit(command=None):
    command = command or launch_command()
    return """[Unit]
Description=Craft Web Server
After=network-online.target
Wants=network-online.target

[Service]
Environment=CRAFTWEB_HOME=%s
WorkingDirectory=%s
ExecStart=%s
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""" % (cfg.base_dir(), cfg.program_dir(), " ".join(_quote(a) for a in command))


# ---------------------------------------------------------------- queries
def is_installed():
    if platform_name() == "windows":
        return run(["schtasks", "/query", "/tn", TASK])[0] == 0
    if platform_name() == "linux":
        return UNIT_PATH.exists()
    return False


def firewall_rule_exists():
    if platform_name() != "windows":
        return None
    code, out = run(["netsh", "advfirewall", "firewall", "show", "rule", "name=" + FIREWALL_RULE])
    return code == 0 and FIREWALL_RULE.lower() in out.lower()


def status():
    settings = cfg.load_config()["settings"]
    h = health()
    return {
        "platform": platform_name(), "installed": is_installed(), "supervisor": supervisor_alive(),
        "running": h is not None, "version": (h or {}).get("version"),
        "port": int(settings["port"]), "admin_port": int(settings.get("admin_port") or 0),
        "tls": bool(settings.get("tls_cert")), "is_admin": cfg.is_admin(), "frozen": bool(getattr(sys, "frozen", False)),
        "program_dir": str(cfg.program_dir()), "data_dir": str(cfg.base_dir()),
        "legacy": cfg.legacy_data(), "password_set": bool(_password_set()),
    }


def _password_set():
    from . import security
    return security.password_hash()


# ---------------------------------------------------------------- actions
def install(log=print, wait=25):
    """Create the data folder, the firewall rule and the boot task, then start the server."""
    if platform_name() == "other":
        raise RuntimeError("Background service setup is supported on Windows and Linux.")
    if not cfg.is_admin():
        raise PermissionError("Administrator rights are needed: right-click and choose 'Run as administrator'.")
    cfg.migrate_legacy(log)
    cfg.ensure_data_dir()
    cfg.ensure_default_config()
    if platform_name() == "windows":
        program = str(cfg.server_program())
        run(["netsh", "advfirewall", "firewall", "delete", "rule", "name=" + FIREWALL_RULE])
        code, out = run(["netsh", "advfirewall", "firewall", "add", "rule", "name=" + FIREWALL_RULE,
                         "dir=in", "action=allow", "program=" + program, "enable=yes", "profile=private,domain"])
        log("Firewall rule for private/domain networks: %s" % ("OK" if code == 0 else "FAILED (%s)" % out))
        xml_file = cfg.run_dir() / "task.xml"
        cfg.run_dir().mkdir(parents=True, exist_ok=True)
        xml_file.write_bytes(task_xml().encode("utf-16"))
        code, out = run(["schtasks", "/create", "/tn", TASK, "/xml", str(xml_file), "/f"])
        if code != 0:
            raise RuntimeError("Could not create the start-at-boot task: %s" % out)
        log("Start-at-boot task created (runs as SYSTEM, no time limit, restarts on failure).")
    else:
        UNIT_PATH.write_text(systemd_unit())
        for cmd in (["systemctl", "daemon-reload"], ["systemctl", "enable", UNIT_NAME]):
            code, out = run(cmd)
            if code != 0:
                raise RuntimeError("%s failed: %s" % (" ".join(cmd), out))
        log("systemd service installed and enabled.")
    start(log)
    if wait and not wait_until(lambda: health() is not None, wait):
        raise RuntimeError("The server did not answer within %d seconds. See the logs." % wait)
    log("The server is running and will start by itself after every reboot.")


def uninstall(log=print):
    """Remove auto-start and the firewall rule. The data stays."""
    stop(log)
    if platform_name() == "windows":
        run(["schtasks", "/delete", "/tn", TASK, "/f"])
        run(["netsh", "advfirewall", "firewall", "delete", "rule", "name=" + FIREWALL_RULE])
    elif platform_name() == "linux":
        run(["systemctl", "disable", UNIT_NAME])
        try:
            UNIT_PATH.unlink()
        except OSError:
            pass
        run(["systemctl", "daemon-reload"])
    log("Auto-start removed. Your data is untouched.")


def start(log=print):
    if supervisor_alive():
        log("Already running.")
        return
    clear_flag("stop")
    if is_installed():
        if platform_name() == "windows":
            code, out = run(["schtasks", "/run", "/tn", TASK])
        else:
            code, out = run(["systemctl", "start", UNIT_NAME])
        if code == 0:
            return
        log("Could not start the installed task (%s): starting directly." % out)
    subprocess.Popen(launch_command(), cwd=str(cfg.program_dir()), close_fds=True,
                     creationflags=DETACHED if os.name == "nt" else 0,
                     start_new_session=(os.name != "nt"),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop(log=print, wait=20):
    """Ask the supervisor to stop the server and exit (it comes back at the next boot)."""
    if not supervisor_alive():
        return
    set_flag("stop")
    if not wait_until(lambda: not supervisor_alive(), wait):
        pid = read_pid("supervisor")
        log("Did not stop in time: ending process %d." % pid)
        if os.name == "nt":
            run(["taskkill", "/PID", str(pid), "/T", "/F"])
        else:
            try:
                os.kill(pid, 15)
            except OSError:
                pass


def restart(log=print):
    if supervisor_alive():
        set_flag("restart")
    else:
        start(log)

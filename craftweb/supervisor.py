"""The process that the boot task runs. It keeps the server alive:

* restarts it when it crashes (with a growing delay),
* restarts it when asked (flag file, or the server exiting with code 75),
* applies a staged update between two runs and rolls it back if the new version keeps crashing,
* stops when asked (stop flag) or when the server exits normally."""
import logging
import os
import subprocess
import sys
import time

from . import config as cfg
from . import selfupdate, service

RESTART_CODE = 75
LOG = logging.getLogger("craftweb")


def server_command():
    if getattr(sys, "frozen", False):
        return [str(cfg.server_program()), "serve"]
    return [sys.executable, str(cfg.program_dir() / "run.py"), "serve"]


def _stop(proc, grace=10, windows=None):
    """Stop the server. On Windows a PyInstaller exe is two processes (loader + Python), and ending only
    the loader would leave the real server holding its ports, so the whole process tree is ended."""
    if proc.poll() is not None:
        return
    if (os.name == "nt") if windows is None else windows:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=30,
                       creationflags=0x08000000 if os.name == "nt" else 0)
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return
    proc.terminate()
    try:
        proc.wait(grace)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(10)


def _wait(proc, poll, started, log):
    """Wait for the server to exit or for a control flag. -> (exit code, reason)."""
    confirmed = False
    while proc.poll() is None:
        time.sleep(poll)
        if service.flag_path("stop").exists():
            _stop(proc)
            return proc.returncode, "stop"
        if service.flag_path("restart").exists():
            service.clear_flag("restart")
            _stop(proc)
            return proc.returncode, "restart"
        if not confirmed and time.time() - started >= selfupdate.CONFIRM_AFTER:
            confirmed = True
            selfupdate.confirm_pending(log)
    return proc.returncode, "exit"


def supervise(command=None, poll=1.0, backoff=(1, 2, 5, 10, 30), stable_after=60, max_runs=None, log=print):
    """Run until stopped. Returns the supervisor's own exit code."""
    command = command or server_command()
    run = cfg.run_dir()
    run.mkdir(parents=True, exist_ok=True)
    mine = os.getpid()
    other = service.read_pid("supervisor")
    if other and other != mine and service.pid_alive(other):
        log("The supervisor is already running (pid %d)." % other)
        return 0
    service.write_pid("supervisor", mine)
    service.clear_flag("stop")
    service.clear_flag("restart")
    crashes = runs = 0
    try:
        while True:
            if service.flag_path("stop").exists():
                break
            selfupdate.apply_staged(log)                       # the server is not running right now
            logs = cfg.base_dir() / "logs"
            logs.mkdir(exist_ok=True)
            console = open(logs / "console.log", "ab")        # tracebacks of a crashing server end up here
            try:
                proc = subprocess.Popen(command, cwd=str(cfg.program_dir()), stdin=subprocess.DEVNULL,
                                        stdout=console, stderr=subprocess.STDOUT,
                                        env=dict(os.environ, CRAFTWEB_SUPERVISED="1"),
                                        creationflags=0x08000000 if os.name == "nt" else 0)
            finally:
                console.close()
            runs += 1
            started = time.time()
            service.write_pid("server", proc.pid)
            log("Server started (pid %d)." % proc.pid)
            code, reason = _wait(proc, poll, started, log)
            uptime = time.time() - started
            (cfg.run_dir() / "server.pid").unlink(missing_ok=True)
            if reason == "stop":
                break
            if reason == "restart" or code == RESTART_CODE:
                crashes = 0
                log("Restarting the server.")
            elif code == 0:
                log("The server stopped normally.")
                break
            else:
                log("The server crashed (exit code %s after %.0f s)." % (code, uptime))
                if selfupdate.note_crash(uptime, log):
                    crashes = 0
                else:
                    crashes = 0 if uptime >= stable_after else crashes + 1
                    time.sleep(backoff[min(max(crashes, 1) - 1, len(backoff) - 1)])
            if max_runs and runs >= max_runs:
                break
    finally:
        if service.read_pid("supervisor") == mine:
            (cfg.run_dir() / "supervisor.pid").unlink(missing_ok=True)
    return 0


def main(argv=None):
    from .server import setup_logging
    setup_logging()
    cfg.migrate_legacy(LOG.info)
    cfg.ensure_data_dir()
    return supervise(log=LOG.info)

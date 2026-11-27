"""Health check: is everything in place and working? Used by `doctor`, the manager and the dashboard.

Every check is independent, never raises, and returns
{"id", "status": ok|warn|fail|info, "title", "detail", "action"} where `action` names a button the
manager offers to fix it (install, start, password, update, migrate)."""
import json
import re
import shutil
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime

from . import config as cfg
from . import diagnose, pki, selfupdate, service

LOG_FILES = {"server": "server.log", "console": "console.log", "audit": "audit.log"}


def _r(cid, status, title, detail="", action=None):
    return {"id": cid, "status": status, "title": title, "detail": detail, "action": action}


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def _can_bind(port):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def _connects(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------- the checks
def check_data():
    folder = cfg.base_dir()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        return _r("data", "fail", "Data folder", "%s is not writable: %s" % (folder, exc))
    legacy = cfg.legacy_data()
    if legacy:
        return _r("data", "warn", "Data folder", "%s. Old data is still inside the program folder (%s)." % (
            folder, ", ".join(legacy)), "migrate")
    return _r("data", "ok", "Data folder", "%s (separate from the program: updates never touch it)" % folder)


def check_disk():
    free = shutil.disk_usage(cfg.base_dir() if cfg.base_dir().exists() else cfg.program_dir()).free / 1073741824
    status = "ok" if free >= 2 else "warn" if free >= 0.5 else "fail"
    return _r("disk", status, "Free disk space", "%.1f GB free" % free)


def check_config():
    path = cfg.config_path()
    if not path.exists():
        return _r("config", "info", "Settings file", "Not created yet: it is created on the first start.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        return _r("config", "fail", "Settings file", "apps.json is not valid JSON: %s" % exc)
    apps = [a for a in data.get("apps", []) if isinstance(a, dict)]
    return _r("config", "ok", "Settings file", "%d application(s) defined" % len(apps))


def check_password():
    from . import security
    if security.password_hash():
        return _r("password", "ok", "Dashboard password", "Set (stored in the data folder, kept across updates).")
    return _r("password", "fail", "Dashboard password", "Not set: the dashboard is disabled until you set one.", "password")


def check_server():
    h = service.health()
    if h:
        return _r("server", "ok", "Server", "Running, version %s" % h.get("version", "?"))
    return _r("server", "fail", "Server", "Not running.", "start")


def check_ports():
    settings = cfg.load_config()["settings"]
    ports = [("apps", int(settings["port"])), ("dashboard", int(settings.get("admin_port") or 0))]
    running = service.health() is not None
    bad, good = [], []
    for name, port in ports:
        if not port:
            continue
        if running:
            if _connects("127.0.0.1", port):
                good.append("%s %d" % (name, port))
            else:
                bad.append("%s (%d) does not answer" % (name, port))
        elif _can_bind(port):
            good.append("%s %d is free" % (name, port))
        else:
            bad.append("port %d (%s) is used by another program" % (port, name))
    if bad:
        return _r("ports", "fail", "Ports", "; ".join(bad))
    return _r("ports", "ok", "Ports", ", ".join(good))


def check_autostart():
    if service.platform_name() == "other":
        return _r("autostart", "info", "Start at boot", "Not supported on this system.")
    if service.is_installed():
        return _r("autostart", "ok", "Start at boot", "Enabled: the server starts by itself after every restart of the computer.")
    return _r("autostart", "warn", "Start at boot", "Not enabled: the server stops when the computer restarts.", "install")


def check_supervisor():
    if service.supervisor_alive():
        return _r("supervisor", "ok", "Watchdog", "Running: the server is restarted automatically if it stops.")
    return _r("supervisor", "warn", "Watchdog", "Not running: updates and automatic restarts need it.", "start")


def check_firewall():
    exists = service.firewall_rule_exists()
    if exists is None:
        return _r("firewall", "info", "Firewall", "Not checked on this system.")
    if exists:
        return _r("firewall", "ok", "Firewall", "A rule allows other devices on private/domain networks to connect.")
    return _r("firewall", "warn", "Firewall", "No rule: other devices may not be able to open the apps.", "install")


def check_lan():
    ip = lan_ip()
    if not ip:
        return _r("lan", "warn", "Network address", "No network connection found.")
    port = int(cfg.load_config()["settings"]["port"])
    scheme = "https" if cfg.load_config()["settings"].get("tls_cert") else "http"
    url = "%s://%s:%d/" % (scheme, ip, port)
    if service.health() is None:
        return _r("lan", "info", "Network address", "Other devices will use %s once the server runs." % url)
    ok = _connects(ip, port)
    return _r("lan", "ok" if ok else "warn", "Network address", "%s %s" % (url, "answers" if ok else "does not answer from this computer"))


def check_https():
    settings = cfg.load_config()["settings"]
    info = pki.info()
    if not settings.get("tls_cert"):
        return _r("https", "info", "HTTPS", "Off. Some features (service workers, clipboard) need it on http://IP.")
    if not info.get("exists"):
        return _r("https", "fail", "HTTPS", "Configured, but the certificate files are missing.")
    if info["days_left"] < 30:
        return _r("https", "warn", "HTTPS", "The certificate expires in %d days: renew it." % info["days_left"])
    if info["missing_ips"]:
        return _r("https", "warn", "HTTPS", "These addresses are not in the certificate: %s" % ", ".join(info["missing_ips"]))
    return _r("https", "ok", "HTTPS", "Certificate valid for %d more days." % info["days_left"])


def check_apps():
    config = cfg.load_config()
    live = cfg.discover_apps()
    empty = [a["id"] for a in config["apps"] if a.get("enabled", True) and a.get("id")
             and str(a["id"]).lower() not in live]
    broken = []
    for app in list(live.values())[:12]:
        try:
            result = diagnose.scan(app["base"], app["index"].relative_to(app["base"]).as_posix())
        except (OSError, ValueError):
            continue
        if any(i["severity"] == "error" for i in result["issues"]):
            broken.append(app["id"])
    detail = "%d app(s) online" % len(live)
    if empty:
        detail += "; nothing installed yet for: %s" % ", ".join(empty)
    if broken:
        return _r("apps", "warn", "Applications", detail + "; files missing in: %s" % ", ".join(broken))
    return _r("apps", "ok" if live else "info", "Applications", detail)


def check_internet():
    try:
        req = urllib.request.Request("https://api.github.com/rate_limit", headers={"User-Agent": "CraftWeb-Doctor"})
        with urllib.request.urlopen(req, timeout=6):
            return _r("internet", "ok", "Internet (GitHub)", "Reachable: downloads and update checks work.")
    except (OSError, urllib.error.URLError) as exc:
        return _r("internet", "info", "Internet (GitHub)",
                  "Not reachable (%s). Everything still works offline; downloads and updates need it." % getattr(exc, "reason", exc))


def check_update():
    info = selfupdate.check()
    if info["error"]:
        return _r("update", "info", "Server version", "%s (could not check for updates)" % info["current"])
    if info["update"]:
        return _r("update", "warn", "Server version", "%s: version %s is available." % (info["current"], info["latest"]),
                  "update" if info["supported"] else None)
    return _r("update", "ok", "Server version", "%s: up to date." % info["current"])


def read_log(name, lines=200):
    """Last lines of a whitelisted log file."""
    filename = LOG_FILES.get(name)
    if not filename:
        raise KeyError(name)
    path = cfg.base_dir() / "logs" / filename
    if not path.is_file():
        return ""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 256 * 1024))
        data = f.read().decode("utf-8", "replace")
    return "\n".join(data.splitlines()[-lines:])


_LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})[,.]\d+ (\w+) (.*)$")


def check_logs(hours=24):
    since = time.time() - hours * 3600
    problems = []
    for line in read_log("server", 2000).splitlines():
        m = _LOG_LINE.match(line)
        if not m or m.group(2) not in ("ERROR", "CRITICAL", "WARNING"):
            continue
        try:
            if datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp() >= since:
                problems.append(line)
        except ValueError:
            continue
    crash = read_log("console", 400)
    errors = [p for p in problems if " ERROR " in p or " CRITICAL " in p]
    if "Traceback" in crash:
        return _r("logs", "warn", "Recent errors", "The server printed a crash report (see the console log).")
    if errors:
        return _r("logs", "warn", "Recent errors", "%d error(s) in the last %d h. Latest: %s" % (len(errors), hours, errors[-1][:200]))
    if problems:
        return _r("logs", "info", "Recent errors", "%d warning(s) in the last %d h. Latest: %s" % (len(problems), hours, problems[-1][:200]))
    return _r("logs", "ok", "Recent errors", "None in the last %d hours." % hours)


CHECKS = [check_data, check_disk, check_config, check_password, check_server, check_ports, check_autostart,
          check_supervisor, check_firewall, check_lan, check_https, check_apps, check_logs]
NETWORK_CHECKS = [check_internet, check_update]


def run_checks(network=True):
    results = []
    for check in CHECKS + (NETWORK_CHECKS if network else []):
        try:
            results.append(check())
        except Exception as exc:  # noqa: BLE001 - a broken check must never hide the others
            results.append(_r(check.__name__[6:], "fail", check.__name__[6:].replace("_", " ").title(),
                              "The check itself failed: %s" % exc))
    summary = {k: sum(1 for r in results if r["status"] == k) for k in ("ok", "info", "warn", "fail")}
    return {"checks": results, "summary": summary, "at": int(time.time())}


def main(argv=None):
    report = run_checks(network="--offline" not in (argv or []))
    marks = {"ok": "[ OK ]", "info": "[ .. ]", "warn": "[ !! ]", "fail": "[FAIL]"}
    for r in report["checks"]:
        print("%s %-22s %s" % (marks[r["status"]], r["title"], r["detail"]))
    s = report["summary"]
    print("\n%d ok, %d warning(s), %d problem(s)." % (s["ok"], s["warn"], s["fail"]))
    return 1 if s["fail"] else 0




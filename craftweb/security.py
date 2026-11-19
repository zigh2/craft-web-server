"""Password hashing, sessions, login throttling, network allow-list, audit log."""
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone

from . import config as cfg

MIN_PASSWORD = 10
DEFAULT_NETWORKS = cfg.DEFAULT_SETTINGS["admin_allowed_networks"]
_MAXMEM = 64 * 1024 * 1024


# ---------------------------------------------------------------- passwords
def hash_password(password):
    salt = os.urandom(16)
    if hasattr(hashlib, "scrypt"):
        try:
            dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1,
                                dklen=32, maxmem=_MAXMEM)
            return "scrypt$16384$8$1$%s$%s" % (salt.hex(), dk.hex())
        except (ValueError, MemoryError):
            pass
    iterations = 600000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, 32)
    return "pbkdf2$%d$%s$%s" % (iterations, salt.hex(), dk.hex())


def verify_password(password, stored):
    try:
        parts = stored.split("$")
        if parts[0] == "scrypt":
            _, n, r, p, salt, dk = parts
            calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                                  n=int(n), r=int(r), p=int(p),
                                  dklen=len(dk) // 2, maxmem=_MAXMEM)
        elif parts[0] == "pbkdf2":
            _, iterations, salt, dk = parts
            calc = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                       bytes.fromhex(salt), int(iterations), len(dk) // 2)
        else:
            return False
        return hmac.compare_digest(calc.hex(), dk)
    except Exception:
        return False


def _admin_file():
    return cfg.base_dir() / "admin.json"


def password_hash():
    data = cfg._load_json(_admin_file(), {})
    return data.get("password") if isinstance(data, dict) else None


def set_password(password):
    if len(password) < MIN_PASSWORD:
        raise ValueError("Password must be at least %d characters." % MIN_PASSWORD)
    cfg.save_json(_admin_file(), {"password": hash_password(password)})
    try:
        os.chmod(_admin_file(), 0o600)  # best effort (no-op semantics on Windows)
    except OSError:
        pass


# ---------------------------------------------------------------- sessions
class Sessions:
    ABSOLUTE = 8 * 3600

    def __init__(self):
        self._items = {}
        self._lock = threading.Lock()

    def create(self, ip):
        now = time.time()
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        with self._lock:
            self._items = {k: v for k, v in self._items.items()
                           if now - v["created"] < self.ABSOLUTE}
            self._items[token] = {"csrf": csrf, "created": now, "seen": now, "ip": ip}
        return token, csrf

    def get(self, token, ip, idle):
        now = time.time()
        with self._lock:
            s = self._items.get(token)
            if s is None:
                return None
            if (now - s["seen"] > idle or now - s["created"] > self.ABSOLUTE
                    or s["ip"] != ip):  # sessions are bound to the client IP
                del self._items[token]
                return None
            s["seen"] = now
            return dict(s)

    def destroy(self, token):
        with self._lock:
            self._items.pop(token, None)

    def destroy_others(self, keep):
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if k == keep}


class LoginLimiter:
    MAX_FAILS, WINDOW, LOCK_FOR = 5, 900, 300

    def __init__(self):
        self._fails, self._locked = {}, {}
        self._lock = threading.Lock()

    def retry_after(self, ip):
        with self._lock:
            left = self._locked.get(ip, 0) - time.time()
            return int(left) + 1 if left > 0 else 0

    def failure(self, ip):
        now = time.time()
        with self._lock:
            if len(self._fails) > 10000:
                self._fails.clear()
                self._locked.clear()
            recent = [t for t in self._fails.get(ip, []) if now - t < self.WINDOW] + [now]
            if len(recent) >= self.MAX_FAILS:
                self._locked[ip] = now + self.LOCK_FOR
                recent = []
            self._fails[ip] = recent

    def success(self, ip):
        with self._lock:
            self._fails.pop(ip, None)
            self._locked.pop(ip, None)


# ---------------------------------------------------------------- network
def ip_allowed(ip, networks):
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
        if getattr(addr, "ipv4_mapped", None):
            addr = addr.ipv4_mapped
    except ValueError:
        return False
    for net in networks or []:
        try:
            if addr in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------- audit log
_audit_lock = threading.Lock()


def _audit_path():
    return cfg.base_dir() / "logs" / "audit.log"


def audit(ip, action, detail=""):
    record = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "ip": ip, "action": action, "detail": str(detail)[:300]}
    path = _audit_path()
    with _audit_lock:
        path.parent.mkdir(exist_ok=True)
        if path.exists() and path.stat().st_size > 1_000_000:
            os.replace(path, path.with_name("audit.log.1"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_audit(limit=200):
    path = _audit_path()
    if not path.exists():
        return []
    with _audit_lock:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for line in reversed(lines[-limit:]):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out

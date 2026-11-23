"""One-command local HTTPS, with no dependency (no openssl, no mkcert).

`setup()` creates a private certificate authority (kept, so devices only have to trust it
once) and a server certificate signed by it that covers localhost, this machine's name and
its LAN addresses. Everything is plain Python (RSA + X.509/DER), so it works on every
platform, inside the Windows exe and in the Docker image."""
import base64
import datetime
import hashlib
import ipaddress
import os
import re
import secrets
import socket
import time

from . import config as cfg

CA_DAYS = 3650
LEAF_DAYS = 825          # the longest lifetime Apple platforms accept
RENEW_BEFORE_DAYS = 60
# The authority may only sign for the local network (NameConstraints). If its key ever leaked it
# could not be used to impersonate a public site on the devices that trust it.
LAN_SUFFIXES = ("localhost", "local", "lan", "internal", "home", "localdomain")
PRIVATE_NETS = ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
                "100.64.0.0/10",                      # carrier-grade NAT range (Tailscale, WireGuard setups)
                "::1/128", "fc00::/7", "fe80::/10")
_RSA_OID = "1.2.840.113549.1.1.1"
_SHA256_RSA = "1.2.840.113549.1.1.11"
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
_DNS = re.compile(r"^(?=.{1,253}$)([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$")


# ---------------------------------------------------------------- DER encoding
def _len(n):
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag, body):
    return bytes([tag]) + _len(len(body)) + body


def _seq(*parts):
    return _tlv(0x30, b"".join(parts))


def _set(*parts):
    return _tlv(0x31, b"".join(parts))


def _int(n):
    return _tlv(0x02, n.to_bytes(max(1, (n.bit_length() + 8) // 8), "big"))


def _oid(dotted):
    a = [int(x) for x in dotted.split(".")]
    body = bytes([40 * a[0] + a[1]])
    for n in a[2:]:
        chunk = [n & 0x7F]
        n >>= 7
        while n:
            chunk.append(0x80 | (n & 0x7F))
            n >>= 7
        body += bytes(reversed(chunk))
    return _tlv(0x06, body)


def _null():
    return b"\x05\x00"


def _bool(v):
    return _tlv(0x01, b"\xff" if v else b"\x00")


def _utf8(s):
    return _tlv(0x0C, s.encode("utf-8"))


def _octet(b):
    return _tlv(0x04, b)


def _bits(b, unused=0):
    return _tlv(0x03, bytes([unused]) + b)


def _time(dt):
    if dt.year < 2050:
        return _tlv(0x17, dt.strftime("%y%m%d%H%M%SZ").encode())
    return _tlv(0x18, dt.strftime("%Y%m%d%H%M%SZ").encode())


def _ctx(n, body):
    return _tlv(0xA0 | n, body)


def _read(buf, pos=0):
    """Minimal DER reader: (tag, content, next position)."""
    tag, first = buf[pos], buf[pos + 1]
    pos += 2
    if first & 0x80:
        count = first & 0x7F
        length = int.from_bytes(buf[pos:pos + count], "big")
        pos += count
    else:
        length = first
    return tag, buf[pos:pos + length], pos + length


def _children(content):
    out, pos = [], 0
    while pos < len(content):
        tag, body, pos = _read(content, pos)
        out.append((tag, body))
    return out


# ---------------------------------------------------------------- RSA
_SMALL_PRIMES = [p for p in range(3, 2000) if all(p % q for q in range(2, int(p ** 0.5) + 1))]


def _is_prime(n, rounds=40):
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        x = pow(secrets.randbelow(n - 3) + 2, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _gen_prime(bits):
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if _is_prime(candidate):
            return candidate


def generate_key(bits=2048):
    e = 65537
    while True:
        p, q = _gen_prime(bits // 2), _gen_prime(bits // 2)
        if p == q or (p * q).bit_length() != bits or ((p - 1) * (q - 1)) % e == 0:
            continue
        d = pow(e, -1, (p - 1) * (q - 1))
        return {"n": p * q, "e": e, "d": d, "p": p, "q": q,
                "dp": d % (p - 1), "dq": d % (q - 1), "qinv": pow(q, -1, p)}


def _sign(key, data):
    klen = (key["n"].bit_length() + 7) // 8
    em = (b"\x00\x01" + b"\xff" * (klen - len(_SHA256_PREFIX) - 32 - 3) + b"\x00"
          + _SHA256_PREFIX + hashlib.sha256(data).digest())
    m = int.from_bytes(em, "big")
    s1, s2 = pow(m % key["p"], key["dp"], key["p"]), pow(m % key["q"], key["dq"], key["q"])
    s = s2 + ((key["qinv"] * (s1 - s2)) % key["p"]) * key["q"]
    return s.to_bytes(klen, "big")


def _rsa_public(key):
    return _seq(_int(key["n"]), _int(key["e"]))


def _spki(key):
    return _seq(_seq(_oid(_RSA_OID), _null()), _bits(_rsa_public(key)))


def _key_id(key):
    return hashlib.sha1(_rsa_public(key)).digest()


def _pkcs8(key):
    rsa = _seq(_int(0), *[_int(key[k]) for k in ("n", "e", "d", "p", "q", "dp", "dq", "qinv")])
    return _seq(_int(0), _seq(_oid(_RSA_OID), _null()), _octet(rsa))


def _load_key(pem):
    der = base64.b64decode("".join(ln for ln in pem.splitlines() if not ln.startswith("-----")))
    _, outer, _ = _read(der)
    octet = _children(outer)[2][1]
    _, rsa, _ = _read(octet)
    values = [int.from_bytes(body, "big") for _, body in _children(rsa)][1:]
    return dict(zip(("n", "e", "d", "p", "q", "dp", "dq", "qinv"), values))


def _pem(label, der):
    b64 = base64.b64encode(der).decode()
    lines = "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return "-----BEGIN %s-----\n%s\n-----END %s-----\n" % (label, lines, label)


# ---------------------------------------------------------------- X.509
def _name(cn, org="Craft Web Server"):
    return _seq(_set(_seq(_oid("2.5.4.10"), _utf8(org))), _set(_seq(_oid("2.5.4.3"), _utf8(cn))))


def _ext(oid, value, critical=False):
    return _seq(_oid(oid), *([_bool(True)] if critical else []), _octet(value))


def _certificate(subject_key, subject, issuer_key, issuer, days, extensions, backdate_days=1):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    alg = _seq(_oid(_SHA256_RSA), _null())
    tbs = _seq(_ctx(0, _int(2)), _int(secrets.randbits(158) + (1 << 100)), alg, issuer,
               _seq(_time(now - datetime.timedelta(days=backdate_days)),
                    _time(now + datetime.timedelta(days=days))),
               subject, _spki(subject_key), _ctx(3, _seq(*extensions)))
    return _seq(tbs, alg, _bits(_sign(issuer_key, tbs)))


def _name_constraints(dns, nets):
    subtrees = [_seq(_tlv(0x82, d.encode("ascii"))) for d in dns]
    for net in (ipaddress.ip_network(n) for n in nets):
        subtrees.append(_seq(_tlv(0x87, net.network_address.packed + net.netmask.packed)))
    return _seq(_tlv(0xA0, b"".join(subtrees)))               # permittedSubtrees


def make_ca(key, cn, dns=LAN_SUFFIXES, nets=PRIVATE_NETS):
    ski = _key_id(key)
    return _certificate(key, _name(cn), key, _name(cn), CA_DAYS, [
        _ext("2.5.29.19", _seq(_bool(True)), True),             # basicConstraints: CA
        _ext("2.5.29.15", _bits(b"\x06", 1), True),             # keyCertSign, cRLSign
        _ext("2.5.29.14", _octet(ski)),
        _ext("2.5.29.30", _name_constraints(dns, nets)),        # non-critical: old clients just ignore it
    ])


def make_server_cert(key, ca_key, ca_cn, names, ips):
    general = [_tlv(0x82, n.encode("ascii")) for n in names] + \
              [_tlv(0x87, ipaddress.ip_address(i).packed) for i in ips]
    return _certificate(key, _name(names[0]), ca_key, _name(ca_cn), LEAF_DAYS, [
        _ext("2.5.29.19", _seq(), True),                        # not a CA
        _ext("2.5.29.15", _bits(b"\xa0", 5), True),             # digitalSignature, keyEncipherment
        _ext("2.5.29.37", _seq(_oid("1.3.6.1.5.5.7.3.1"))),     # serverAuth
        _ext("2.5.29.17", _seq(*general)),                      # subjectAltName
        _ext("2.5.29.35", _seq(_tlv(0x80, _key_id(ca_key)))),   # authorityKeyIdentifier
        _ext("2.5.29.14", _octet(_key_id(key))),
    ])


# ---------------------------------------------------------------- the machine
def local_addresses():
    """(DNS names, IP addresses) the server certificate should be valid for."""
    names, ips = {"localhost"}, {"127.0.0.1", "::1"}
    host = socket.gethostname().strip().lower()
    if host and _DNS.match(host):
        names.add(host)
    candidates = []
    try:
        candidates += socket.gethostbyname_ex(host)[2]
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))       # no packet is sent: just picks the LAN interface
            candidates.append(s.getsockname()[0])
    except OSError:
        pass
    for ip in candidates:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if not (addr.is_unspecified or addr.is_link_local or addr.is_multicast):
            ips.add(str(addr))
    return sorted(names), sorted(ips)


def _split_extra(extra):
    names, ips = [], []
    for item in extra or []:
        item = str(item).strip().lower()
        if not item:
            continue
        try:
            ips.append(str(ipaddress.ip_address(item)))
        except ValueError:
            if not _DNS.match(item):
                raise ValueError("'%s' is not a valid host name or IP address" % item)
            names.append(item)
    return names, ips


# ---------------------------------------------------------------- files
def certs_dir():
    return cfg.base_dir() / "certs"


def _write(path, text, private=False):
    path.write_text(text, encoding="ascii")
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _fingerprint(der):
    h = hashlib.sha256(der).hexdigest().upper()
    return ":".join(h[i:i + 2] for i in range(0, len(h), 2))


def _pem_to_der(pem):
    return base64.b64decode("".join(ln for ln in pem.splitlines() if not ln.startswith("-----")))


def info():
    """What is on disk (never the keys)."""
    data = cfg._load_json(certs_dir() / "info.json", {})
    if not isinstance(data, dict) or not (certs_dir() / "server.pem").is_file():
        return {"exists": False}
    names, ips = local_addresses()
    data["exists"] = True
    data["days_left"] = int((data.get("expires", 0) - time.time()) // 86400)
    data["missing_ips"] = [i for i in ips if i not in data.get("ips", []) and i != "::1"]
    return data


def ca_pem():
    f = certs_dir() / "ca.pem"
    return f.read_bytes() if f.is_file() else None


def ca_der():
    pem = ca_pem()
    return _pem_to_der(pem.decode("ascii")) if pem else None


def _covered(name, allowed):
    return any(name == d or name.endswith("." + d) for d in allowed)


def _covered_ip(ip, nets):
    addr = ipaddress.ip_address(ip)
    return any(addr.version == ipaddress.ip_network(n).version and addr in ipaddress.ip_network(n) for n in nets)


def setup(extra_names=(), renew=False, bits=2048, log=print, new_ca=False):
    """Create (or reuse) the CA, issue the server certificate and switch HTTPS on in apps.json."""
    extra_names, extra_ips = _split_extra(extra_names)
    folder = certs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    meta = cfg._load_json(folder / "info.json", {})
    meta = meta if isinstance(meta, dict) else {}

    ca_cert, ca_key_file = folder / "ca.pem", folder / "ca-key.pem"
    if (not new_ca and ca_cert.is_file() and ca_key_file.is_file() and meta.get("ca_cn")
            and meta.get("ca_dns")):
        ca_key = _load_key(ca_key_file.read_text(encoding="ascii"))
        log("Using the existing certificate authority (devices that trust it keep working).")
    else:
        log("Creating the certificate authority (a few seconds) ...")
        host = (socket.gethostname() or "server").strip().lower()
        auto_names, _ = local_addresses()
        allowed_dns = sorted(set(LAN_SUFFIXES) | set(auto_names) | set(extra_names))
        meta = {"ca_cn": "Craft Web Server CA (%s)" % host, "ca_dns": allowed_dns, "ca_nets": list(PRIVATE_NETS)}
        ca_key = generate_key(bits)
        ca_der_bytes = make_ca(ca_key, meta["ca_cn"], allowed_dns, PRIVATE_NETS)
        _write(ca_cert, _pem("CERTIFICATE", ca_der_bytes))
        _write(ca_key_file, _pem("PRIVATE KEY", _pkcs8(ca_key)), private=True)
        meta["ca_sha256"] = _fingerprint(ca_der_bytes)
        meta["ca_expires"] = time.time() + CA_DAYS * 86400
        renew = True

    allowed_dns, allowed_nets = meta["ca_dns"], meta["ca_nets"]
    for name in extra_names:
        if not _covered(name, allowed_dns):
            raise ValueError("'%s' is outside what the authority may sign (local names only). Use a new "
                             "authority (--new-ca); devices must then trust it again." % name)
    for ip in extra_ips:
        if not _covered_ip(ip, allowed_nets):
            raise ValueError("%s is not a private address, which is all the authority may sign for." % ip)
    names, ips = local_addresses()
    dropped = [n for n in names if not _covered(n, allowed_dns)] + [i for i in ips if not _covered_ip(i, allowed_nets)]
    if dropped:
        log("Skipped (outside the authority's limits): %s" % ", ".join(dropped))
    names = sorted({n for n in names if _covered(n, allowed_dns)} | set(extra_names))
    ips = sorted({i for i in ips if _covered_ip(i, allowed_nets)} | set(extra_ips))
    leaf_ok = ((folder / "server.pem").is_file() and (folder / "server-key.pem").is_file()
               and meta.get("names") == names and meta.get("ips") == ips
               and meta.get("expires", 0) - time.time() > RENEW_BEFORE_DAYS * 86400)
    if leaf_ok and not renew:
        log("The server certificate is already valid for these addresses.")
    else:
        log("Issuing the server certificate for: %s" % ", ".join(names + ips))
        key = generate_key(bits)
        cert = make_server_cert(key, ca_key, meta["ca_cn"], names, ips)
        _write(folder / "server.pem", _pem("CERTIFICATE", cert))
        _write(folder / "server-key.pem", _pem("PRIVATE KEY", _pkcs8(key)), private=True)
        meta.update(names=names, ips=ips, expires=time.time() + LEAF_DAYS * 86400, created=int(time.time()))
    cfg.save_json(folder / "info.json", meta)
    cfg.update_settings({"tls_cert": "certs/server.pem", "tls_key": "certs/server-key.pem"})
    log("HTTPS is configured. Restart the server to apply it.")
    return info()


TRUST_HELP = """Trust the authority ONCE on every device that opens the apps:
  any device : open  https://SERVER-IP:PORT/ca.crt  (accept the warning once to download it)
  Windows    : certutil -addstore -f ROOT certs\\ca.pem          (run as Administrator)
  macOS      : sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/ca.pem
  iPhone/iPad: open /ca.crt, install the profile, then Settings > General > About > Certificate Trust Settings
  Android    : Settings > Security > Install a certificate > CA certificate
  Firefox    : Settings > Privacy > Certificates > Import (or enable security.enterprise_roots.enabled)"""


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="https", description="Set up local HTTPS (certificate authority + server certificate).")
    parser.add_argument("--names", help="extra host names / IP addresses, comma separated (e.g. craft.lan,192.168.1.20)")
    parser.add_argument("--renew", action="store_true", help="issue a new server certificate even if the current one is valid")
    parser.add_argument("--new-ca", action="store_true", help="replace the certificate authority (devices must trust the new one)")
    args = parser.parse_args(argv)
    try:
        result = setup([n for n in (args.names or "").split(",") if n.strip()], renew=args.renew, new_ca=args.new_ca)
    except ValueError as exc:
        print("FAILED:", exc)
        return 1
    print("\nCertificate valid for %d more days. Authority fingerprint (SHA-256):\n  %s\n" % (
        result["days_left"], result.get("ca_sha256", "?")))
    print(TRUST_HELP)
    return 0

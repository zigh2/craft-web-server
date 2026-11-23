import http.client
import json
import os
import shutil
import socket
import ssl
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from craftweb import admin, pki, security  # noqa: E402
from craftweb import config as cfg  # noqa: E402
from craftweb.server import AdminHandler, CraftHandler, _make_server  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = self.tmp
        Path(self.tmp, "apps.json").write_text(json.dumps({"settings": {}, "apps": []}))
        cfg.invalidate_cache()
        admin.reset()
        self.servers = []

    def tearDown(self):
        for s in self.servers:
            s.shutdown()
            s.server_close()
        os.environ.pop("CRAFTWEB_HOME", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def serve(self, handler):
        server = _make_server("127.0.0.1", 0, handler, cfg.load_config()["settings"])
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.servers.append(server)
        return server

    def client_context(self, ca=None):
        return ssl.create_default_context(cafile=str(ca or pki.certs_dir() / "ca.pem"))


class DerTests(unittest.TestCase):
    def test_primitives(self):
        self.assertEqual(pki._len(5), b"\x05")
        self.assertEqual(pki._len(127), b"\x7f")
        self.assertEqual(pki._len(128), b"\x81\x80")
        self.assertEqual(pki._len(300), b"\x82\x01\x2c")
        self.assertEqual(pki._int(0), b"\x02\x01\x00")
        self.assertEqual(pki._int(127), b"\x02\x01\x7f")
        self.assertEqual(pki._int(128), b"\x02\x02\x00\x80")        # high bit set -> leading zero
        self.assertEqual(pki._int(256), b"\x02\x02\x01\x00")
        self.assertEqual(pki._oid("1.2.840.113549.1.1.11"), bytes.fromhex("06092a864886f70d01010b"))
        self.assertEqual(pki._oid("2.5.29.17"), bytes.fromhex("0603551d11"))

    def test_der_reader_roundtrip(self):
        blob = pki._seq(pki._int(1), pki._octet(b"abc"), pki._seq(pki._int(2 ** 100)))
        tag, body, end = pki._read(blob)
        self.assertEqual((tag, end), (0x30, len(blob)))
        kids = pki._children(body)
        self.assertEqual([t for t, _ in kids], [0x02, 0x04, 0x30])
        self.assertEqual(kids[1][1], b"abc")

    def test_rsa_key_is_consistent_and_survives_pem(self):
        key = pki.generate_key(1024)
        self.assertEqual(key["n"].bit_length(), 1024)
        self.assertEqual(pow(pow(12345, key["e"], key["n"]), key["d"], key["n"]), 12345)
        back = pki._load_key(pki._pem("PRIVATE KEY", pki._pkcs8(key)))
        self.assertEqual(back, key)


class SetupTests(Base):
    def test_files_settings_and_idempotence(self):
        info = pki.setup(["craft.lan", "192.168.77.7"], log=lambda m: None)
        d = pki.certs_dir()
        self.assertEqual(sorted(p.name for p in d.iterdir()),
                         ["ca-key.pem", "ca.pem", "info.json", "server-key.pem", "server.pem"])
        settings = cfg.load_config()["settings"]
        self.assertEqual((settings["tls_cert"], settings["tls_key"]), ("certs/server.pem", "certs/server-key.pem"))
        self.assertIn("craft.lan", info["names"])
        self.assertIn("192.168.77.7", info["ips"])
        self.assertGreater(info["days_left"], 800)
        if os.name != "nt":
            for key in ("ca-key.pem", "server-key.pem"):
                self.assertEqual((d / key).stat().st_mode & 0o777, 0o600)
        leaf, ca = (d / "server.pem").read_bytes(), (d / "ca.pem").read_bytes()
        pki.setup(["craft.lan", "192.168.77.7"], log=lambda m: None)           # nothing changed
        self.assertEqual(((d / "server.pem").read_bytes(), (d / "ca.pem").read_bytes()), (leaf, ca))
        pki.setup(["craft.lan", "192.168.77.7"], renew=True, log=lambda m: None)
        self.assertNotEqual((d / "server.pem").read_bytes(), leaf)             # new leaf ...
        self.assertEqual((d / "ca.pem").read_bytes(), ca)                      # ... same authority
        pki.setup(["craft.lan", "192.168.77.7", "other.lan"], log=lambda m: None)
        self.assertEqual((d / "ca.pem").read_bytes(), ca)                      # new name: re-issue, same CA
        self.assertIn("other.lan", pki.info()["names"])

    def test_invalid_names_create_nothing(self):
        with self.assertRaises(ValueError):
            pki.setup(["bad name!"], log=lambda m: None)
        self.assertFalse(pki.certs_dir().exists())
        self.assertEqual(pki.info(), {"exists": False})

    def test_info_reports_addresses_missing_from_the_certificate(self):
        pki.setup(log=lambda m: None)
        real = pki.local_addresses
        pki.local_addresses = lambda: (["localhost"], ["127.0.0.1", "10.9.8.7"])
        try:
            self.assertEqual(pki.info()["missing_ips"], ["10.9.8.7"])
        finally:
            pki.local_addresses = real


class HandshakeTests(Base):
    def setUp(self):
        super().setUp()
        pki.setup(["craft.lan", "192.168.77.7"], log=lambda m: None)

    def test_browser_style_verification_succeeds_for_every_name(self):
        server = self.serve(CraftHandler)
        self.assertTrue(server.tls)
        ctx = self.client_context()
        for hostname in ("localhost", "127.0.0.1", "craft.lan", "192.168.77.7"):
            with socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=5) as raw:
                with ctx.wrap_socket(raw, server_hostname=hostname) as tls:
                    self.assertEqual(tls.version() in ("TLSv1.2", "TLSv1.3"), True, hostname)
        conn = http.client.HTTPSConnection("localhost", server.server_address[1], context=ctx, timeout=5)
        conn.request("GET", "/health")
        self.assertEqual(json.loads(conn.getresponse().read())["status"], "ok")

    def test_wrong_name_wrong_authority_or_no_trust_is_rejected(self):
        server = self.serve(CraftHandler)
        port = server.server_address[1]
        with self.assertRaises(ssl.SSLCertVerificationError):
            with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                self.client_context().wrap_socket(raw, server_hostname="evil.example")
        with self.assertRaises(ssl.SSLCertVerificationError):                     # system trust store
            with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                ssl.create_default_context().wrap_socket(raw, server_hostname="localhost")
        other = tempfile.mkdtemp()
        os.environ["CRAFTWEB_HOME"] = other                                        # a different authority
        try:
            pki.setup(log=lambda m: None)
            foreign_ca = pki.certs_dir() / "ca.pem"
            with self.assertRaises(ssl.SSLCertVerificationError):
                with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                    self.client_context(foreign_ca).wrap_socket(raw, server_hostname="localhost")
        finally:
            os.environ["CRAFTWEB_HOME"] = self.tmp
            shutil.rmtree(other, ignore_errors=True)

    def test_dashboard_cookie_gets_the_secure_flag_over_https(self):
        security.set_password("correct horse battery")
        server = self.serve(AdminHandler)
        conn = http.client.HTTPSConnection("localhost", server.server_address[1], context=self.client_context(), timeout=5)
        conn.request("POST", "/admin/api/login", body=json.dumps({"password": "correct horse battery"}),
                     headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        r.read()
        self.assertEqual(r.status, 200)
        self.assertIn("Secure", r.getheader("Set-Cookie"))


class ConstraintTests(Base):
    """The authority may only sign for the local network, whatever happens to its key."""

    def setUp(self):
        super().setUp()
        pki.setup(["craft.lan"], log=lambda m: None)

    def tls_server_with(self, names, ips):
        d = pki.certs_dir()
        meta = json.loads((d / "info.json").read_text())
        ca_key = pki._load_key((d / "ca-key.pem").read_text())
        key = pki.generate_key(2048)
        cert = pki.make_server_cert(key, ca_key, meta["ca_cn"], names, ips)
        (Path(self.tmp) / "f.pem").write_text(pki._pem("CERTIFICATE", cert))
        (Path(self.tmp) / "f-key.pem").write_text(pki._pem("PRIVATE KEY", pki._pkcs8(key)))
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(Path(self.tmp) / "f.pem", Path(self.tmp) / "f-key.pem")
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        self.addCleanup(sock.close)

        def accept():
            try:
                conn, _ = sock.accept()
                ctx.wrap_socket(conn, server_side=True).close()
            except (ssl.SSLError, OSError):
                pass
        threading.Thread(target=accept, daemon=True).start()
        return sock.getsockname()[1]

    def connect(self, port, hostname):
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            with self.client_context().wrap_socket(raw, server_hostname=hostname):
                return True

    def test_a_certificate_for_a_public_site_is_refused_by_clients(self):
        good = self.tls_server_with(["good.lan"], ["192.168.5.5"])                 # positive control
        self.assertTrue(self.connect(good, "good.lan"))
        bad = self.tls_server_with(["bank.example.com"], ["8.8.8.8"])              # same CA key, public names
        with self.assertRaises(ssl.SSLCertVerificationError) as ctx:
            self.connect(bad, "bank.example.com")
        self.assertIn("permitted subtree", str(ctx.exception).lower())

    def test_setup_refuses_names_the_authority_cannot_sign(self):
        with self.assertRaises(ValueError) as e:
            pki.setup(["example.com"], log=lambda m: None)
        self.assertIn("--new-ca", str(e.exception))
        with self.assertRaises(ValueError):
            pki.setup(["8.8.8.8"], log=lambda m: None)
        pki.setup(["printer.local", "10.20.30.40", "nas.home", "100.64.1.2"], log=lambda m: None)   # all local: fine
        self.assertIn("10.20.30.40", pki.info()["ips"])

    def test_new_ca_replaces_the_authority_and_allows_the_requested_names(self):
        old = (pki.certs_dir() / "ca.pem").read_bytes()
        pki.setup(["example.com"], new_ca=True, log=lambda m: None)
        self.assertNotEqual((pki.certs_dir() / "ca.pem").read_bytes(), old)
        self.assertIn("example.com", pki.info()["names"])

    def test_public_addresses_of_the_machine_are_left_out_of_the_certificate(self):
        real = pki.local_addresses
        pki.local_addresses = lambda: (["localhost"], ["127.0.0.1", "192.168.1.9", "8.8.8.8"])
        messages = []
        try:
            info = pki.setup(renew=True, log=messages.append)
        finally:
            pki.local_addresses = real
        self.assertNotIn("8.8.8.8", info["ips"])
        self.assertIn("192.168.1.9", info["ips"])
        self.assertTrue(any("Skipped" in m for m in messages))

    def test_constraints_are_in_the_certificate_and_not_critical(self):
        import shutil as sh
        import subprocess
        if not sh.which("openssl"):
            self.skipTest("openssl CLI not installed")
        out = subprocess.run(["openssl", "x509", "-in", str(pki.certs_dir() / "ca.pem"), "-noout", "-text"],
                             capture_output=True, text=True).stdout
        self.assertIn("X509v3 Name Constraints:", out)
        self.assertNotIn("X509v3 Name Constraints: critical", out)
        self.assertIn("DNS:lan", out)
        self.assertIn("IP:192.168.0.0/255.255.0.0", out)
        verify = subprocess.run(["openssl", "verify", "-CAfile", str(pki.certs_dir() / "ca.pem"),
                                 str(pki.certs_dir() / "server.pem")], capture_output=True, text=True)
        self.assertIn("OK", verify.stdout)


class CaDownloadTests(Base):
    def get(self, server, path):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", path)
        r = conn.getresponse()
        return r, r.read()

    def test_ca_is_downloadable_in_both_formats_and_the_key_never(self):
        server = self.serve(CraftHandler)
        for path in ("/ca.crt", "/ca.cer"):
            self.assertEqual(self.get(server, path)[0].status, 404, "before setup")
        pki.setup(log=lambda m: None)
        server = self.serve(CraftHandler)    # (no TLS here: the server was created before... settings now have it)
        self.assertTrue(server.tls)
        ctx = self.client_context()
        conn = http.client.HTTPSConnection("localhost", server.server_address[1], context=ctx, timeout=5)
        conn.request("GET", "/ca.crt")
        r = conn.getresponse()
        pem = r.read()
        self.assertEqual((r.status, r.getheader("Content-Type")), (200, "application/x-x509-ca-cert"))
        self.assertEqual(pem, (pki.certs_dir() / "ca.pem").read_bytes())
        self.assertNotIn(b"PRIVATE", pem)
        conn.request("GET", "/ca.cer")
        der = conn.getresponse().read()
        self.assertEqual(ssl.DER_cert_to_PEM_cert(der).encode(), pem.replace(b"\r", b""))
        for path in ("/ca-key.pem", "/certs/ca-key.pem", "/ca.crt/../ca-key.pem"):
            conn.request("GET", path)
            resp = conn.getresponse()
            self.assertNotIn(b"PRIVATE", resp.read(), path)

    def test_not_exposed_on_the_dashboard_port(self):
        pki.setup(log=lambda m: None)
        server = self.serve(AdminHandler)
        conn = http.client.HTTPSConnection("localhost", server.server_address[1], context=self.client_context(), timeout=5)
        conn.request("GET", "/ca.crt")
        self.assertEqual(conn.getresponse().status, 404)


class AdminHttpsApiTests(Base):
    def setUp(self):
        super().setUp()
        security.set_password("correct horse battery")
        self.server = self.serve(AdminHandler)       # plain HTTP: no certificate configured yet
        self.cookie = self.csrf = None
        r, d = self.call("POST", "/admin/api/login", {"password": "correct horse battery"})
        self.cookie, self.csrf = r.getheader("Set-Cookie").split(";")[0], d["csrf"]

    def call(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        hdr = {"Content-Type": "application/json"}
        if self.cookie:
            hdr["Cookie"], hdr["X-CSRF-Token"] = self.cookie, self.csrf
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=hdr)
        r = c.getresponse()
        data = json.loads(r.read() or b"{}")
        c.close()
        return r, data

    def test_setup_job_then_info_reports_restart_needed(self):
        r, d = self.call("GET", "/admin/api/https-info")
        self.assertEqual((d["exists"], d["configured"], d["active"]), (False, False, False))
        r, d = self.call("POST", "/admin/api/https-setup", {"names": ["craft.lan"]})
        self.assertEqual(r.status, 200, d)
        for _ in range(200):
            r, j = self.call("GET", "/admin/api/job?id=" + d["job"])
            if j["job"]["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(j["job"]["status"], "done", j)
        r, d = self.call("GET", "/admin/api/https-info")
        self.assertEqual((d["exists"], d["configured"], d["needs_restart"]), (True, True, True))
        self.assertIn("craft.lan", d["names"])
        self.assertNotIn("PRIVATE", json.dumps(d))

    def test_bad_names_are_rejected_up_front(self):
        r, d = self.call("POST", "/admin/api/https-setup", {"names": ["bad name!"]})
        self.assertEqual((r.status, d["code"]), (400, "bad_host"))
        r, d = self.call("POST", "/admin/api/https-setup", {"names": "craft.lan"})
        self.assertEqual(r.status, 400)


if __name__ == "__main__":
    unittest.main()

"""Make an installed web app work without internet.

Many web apps load web fonts, libraries or scripts from a CDN. On an offline LAN those
requests never finish and the app stays on "Loading...". This module downloads such files
once into cache/vendor/ (shared by every app and every version) and points the app at the
local copies, which the server hands out under /_vendor/.

Safety: the URLs come from third-party app files, so every request is checked against
server-side request forgery (private/loopback addresses, odd ports, redirects) and limited
in size and number."""
import hashlib
import html
import ipaddress
import os
import posixpath
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from . import config as cfg

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")  # Google Fonts answers with woff2 only to modern browsers
MAX_RESOURCE = 25 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
MAX_NEW_FILES = 400
MAX_TEXT_FILE = 40 * 1024 * 1024
TIMEOUT = 15
MAX_DEPTH = 4
RETRY_AFTER = 300            # seconds a host that could not be reached is left alone
ALLOW_PRIVATE = False        # tests only: lets the fake CDN live on 127.0.0.1
MANIFEST = ".craftweb-localized.json"

STATIC_EXT = frozenset({".js", ".mjs", ".css", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".png", ".jpg",
                        ".jpeg", ".gif", ".svg", ".webp", ".avif", ".ico", ".wasm"})
CSS_HOSTS = frozenset({"fonts.googleapis.com", "fonts.bunny.net"})   # CSS without a file extension
# Not worth (or not possible) to localize: analytics and ES-module CDNs whose files import each
# other through absolute paths.
SKIP_HOSTS = frozenset({"www.google-analytics.com", "google-analytics.com", "www.googletagmanager.com",
                        "googletagmanager.com", "connect.facebook.net", "static.hotjar.com", "localhost"})
UNSUPPORTED_HOSTS = frozenset({"esm.sh", "esm.run", "cdn.skypack.dev", "ga.jspm.io", "jspm.dev"})
LINK_RELS = frozenset({"stylesheet", "preload", "modulepreload", "icon", "shortcut", "apple-touch-icon",
                       "manifest"})
TYPE_EXT = {"text/css": ".css", "application/javascript": ".js", "text/javascript": ".js",
            "font/woff2": ".woff2", "font/woff": ".woff", "font/ttf": ".ttf", "font/otf": ".otf",
            "image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
            "application/wasm": ".wasm"}

_CSS_URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+?)\1\s*\)", re.I)
_CSS_IMPORT = re.compile(r"@import\s+(['\"])([^'\"]+)\1", re.I)
_JS_URL = re.compile(r"""(["'])(https?://[^"'\s\\]{4,500})\1""")
_TAG = re.compile(r"<(script|link|img|source|video|audio)\b[^>]*>", re.I | re.S)
_ATTR = re.compile(r"""(\b(?:src|href|poster)\s*=\s*)(["'])(.*?)\2""", re.I | re.S)
_REL = re.compile(r"""\brel\s*=\s*["']([^"']*)["']""", re.I)
_INTEGRITY = re.compile(r"""\sintegrity\s*=\s*(?:"[^"]*"|'[^']*')""", re.I)
_SCRIPT = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.I | re.S)

_lock = threading.RLock()
_bad_hosts = {}   # host -> time until which it is skipped


class Blocked(Exception):
    pass


def vendor_dir():
    return cfg.cache_dir() / "vendor"


def _canon(url):
    url = url.strip().split("#")[0]
    if url.startswith("//"):
        url = "https:" + url
    p = urlsplit(url)
    if p.scheme.lower() not in ("http", "https") or not p.hostname:
        return None
    return p._replace(scheme=p.scheme.lower(), netloc=p.netloc.lower()).geturl()


# ---------------------------------------------------------------- network (guarded)
def _blocked(url):
    """Reason the URL must not be fetched, or None."""
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or not host:
        return "unsupported URL"
    if ALLOW_PRIVATE:
        return None
    port = p.port or (443 if p.scheme == "https" else 80)
    if port not in (80, 443):
        return "port %d is not allowed" % port
    if host == "localhost" or host.endswith((".local", ".lan", ".internal", ".home", ".localdomain")):
        return "private host name"
    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        ips = []
        if not (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
                or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")):
            try:   # resolve here so a public-looking name cannot point inside the LAN
                ips = [ipaddress.ip_address(a[4][0].split("%")[0]) for a in socket.getaddrinfo(host, port)]
            except socket.gaierror:
                return None  # cannot resolve = offline, handled as a network error later
    if any(not ip.is_global for ip in ips):
        return "private or reserved address"
    return None


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        reason = _blocked(urljoin(req.full_url, newurl))
        if reason:
            raise urllib.error.URLError("redirect blocked: " + reason)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _http_get(url):
    host = urlsplit(url).hostname
    with _lock:
        if _bad_hosts.get(host, 0) > time.time():
            raise urllib.error.URLError("%s was unreachable a moment ago" % host)
    reason = _blocked(url)
    if reason:
        raise Blocked(reason)
    opener = urllib.request.build_opener(_GuardedRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                               "Accept-Encoding": "identity"})
    try:
        with opener.open(req, timeout=TIMEOUT) as response:
            ctype = response.headers.get("Content-Type", "")
            data = response.read(MAX_RESOURCE + 1)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError) as exc:
        if isinstance(getattr(exc, "reason", exc), OSError):   # DNS / refused / timeout
            with _lock:
                _bad_hosts[host] = time.time() + RETRY_AFTER
        raise
    if len(data) > MAX_RESOURCE:
        raise Blocked("larger than %d MB" % (MAX_RESOURCE // 1048576))
    return data, ctype.split(";")[0].strip().lower()


# ---------------------------------------------------------------- vendor store
def _safe(segment):
    return re.sub(r"[^A-Za-z0-9._@~+-]", "_", segment)[:100] or "_"


def _rel_path(url, ctype):
    p = urlsplit(url)
    host = _safe(p.hostname)
    if p.port and p.port not in (80, 443):
        host += "_%d" % p.port
    segs = [_safe(s) for s in unquote(p.path).split("/") if s and s not in (".", "..")]
    name = segs.pop() if segs else "index"
    stem, ext = posixpath.splitext(name)
    if p.query:
        name = "%s__%s%s" % (stem, hashlib.sha1(p.query.encode()).hexdigest()[:8], ext)
    if not ext and TYPE_EXT.get(ctype):
        name += TYPE_EXT[ctype]
    return "/".join([host] + segs + [name])


class _Run:
    def __init__(self, log):
        self.log = log
        self.index = cfg._load_json(cfg.cache_dir() / "vendor-index.json", {})
        if not isinstance(self.index, dict):
            self.index = {}
        self.memo, self.failed, self.unsupported = {}, {}, set()
        self.bytes = self.new = 0

    def save(self):
        if self.new:
            cfg.cache_dir().mkdir(parents=True, exist_ok=True)
            cfg.save_json(cfg.cache_dir() / "vendor-index.json", self.index)   # not under /_vendor/


def _resource(run, url, depth):
    """Local vendor path (relative to cache/vendor) of an internet URL, downloading it if needed."""
    url = _canon(url)
    if not url:
        return None
    if url in run.memo:
        return run.memo[url]
    run.memo[url] = None                      # also stops @import cycles
    entry = run.index.get(url)
    if entry and (vendor_dir() / entry["path"]).is_file():
        run.memo[url] = entry["path"]
        return entry["path"]
    try:
        if run.new >= MAX_NEW_FILES or run.bytes >= MAX_TOTAL:
            raise Blocked("download limit reached")
        data, ctype = _http_get(url)
        rel = _rel_path(url, ctype)
        if (ctype == "text/css" or rel.endswith(".css")) and depth < MAX_DEPTH:
            text = _rewrite_css(run, data.decode("utf-8", "replace"), url, depth + 1, rel)
            data = text.encode("utf-8")
        dest = (vendor_dir() / rel)
        if vendor_dir().resolve() not in dest.resolve().parents:
            raise Blocked("unsafe path")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        run.index[url] = {"path": rel, "type": ctype, "size": len(data)}
        run.bytes += len(data)
        run.new += 1
        run.memo[url] = rel
        return rel
    except urllib.error.HTTPError as exc:
        run.failed[url] = "HTTP %d" % exc.code
    except (Blocked, urllib.error.URLError, OSError, ValueError) as exc:
        run.failed[url] = str(getattr(exc, "reason", exc))[:120]
    return None


# ---------------------------------------------------------------- rewriting
def _app_ref(run, ref, kind):
    """/_vendor/... for an internet URL found in an app file, or None to leave it alone."""
    raw = html.unescape(ref).strip()
    if not raw.startswith(("http://", "https://", "//")):
        return None
    url = _canon(raw)
    if not url:
        return None
    host = urlsplit(url).hostname
    if host in SKIP_HOSTS:
        return None
    if host in UNSUPPORTED_HOSTS:
        run.unsupported.add(host)
        return None
    if kind == "js" and (posixpath.splitext(urlsplit(url).path)[1].lower() not in STATIC_EXT
                         and host not in CSS_HOSTS):
        return None            # a script URL that is not obviously a static file may be an API
    rel = _resource(run, url, 0)
    return "/_vendor/" + rel if rel else None


def _rewrite_css(run, text, base_url, depth, base_rel):
    """Inside a vendored CSS (base_url given) relative references are fetched too and become
    relative paths; inside an app file only absolute internet URLs are handled."""
    def convert(ref):
        ref = ref.strip()
        if not ref or ref.startswith(("data:", "#", "blob:")):
            return None
        if base_url is None:
            return _app_ref(run, ref, "css")
        rel = _resource(run, urljoin(base_url, ref), depth)
        return posixpath.relpath(rel, posixpath.dirname(base_rel)) if rel else None

    def url_sub(m):
        new = convert(m.group(2))
        return "url(%s%s%s)" % (m.group(1), new, m.group(1)) if new else m.group(0)

    def import_sub(m):
        new = convert(m.group(2))
        return "@import %s%s%s" % (m.group(1), new, m.group(1)) if new else m.group(0)

    return _CSS_IMPORT.sub(import_sub, _CSS_URL.sub(url_sub, text))


def _rewrite_js(run, text):
    def sub(m):
        new = _app_ref(run, m.group(2), "js")
        return m.group(1) + new + m.group(1) if new else m.group(0)
    return _JS_URL.sub(sub, text)


def _rewrite_html(run, text):
    def tag_sub(m):
        tag, changed = m.group(0), [False]
        if m.group(1).lower() == "link":
            rel = _REL.search(tag)
            if not set((rel.group(1) if rel else "").lower().split()) & LINK_RELS:
                return tag

        def attr_sub(am):
            new = _app_ref(run, am.group(3), "html")
            if not new:
                return am.group(0)
            changed[0] = True
            return am.group(1) + am.group(2) + new + am.group(2)

        tag = _ATTR.sub(attr_sub, tag)
        return _INTEGRITY.sub("", tag) if changed[0] else tag   # same-origin now; the hash no longer applies

    text = _TAG.sub(tag_sub, text)
    text = _rewrite_css(run, text, None, 0, None)               # <style> blocks and style=""
    return _SCRIPT.sub(lambda m: m.group(1) + _rewrite_js(run, m.group(2)) + m.group(3), text)


# ---------------------------------------------------------------- public API
def localize_folder(folder, log=print):
    """Download the internet resources an installed app uses and rewrite it to use local copies."""
    folder = Path(folder)
    run, changed = _Run(log), 0
    for f in sorted(folder.rglob("*")):
        suffix = f.suffix.lower()
        if not f.is_file() or suffix not in (".html", ".htm", ".css", ".js", ".mjs"):
            continue
        if f.stat().st_size > MAX_TEXT_FILE:
            continue
        raw = f.read_bytes()
        if b"http" not in raw and b"//" not in raw:
            continue
        text = raw.decode("utf-8", "surrogateescape")
        if suffix in (".html", ".htm"):
            new = _rewrite_html(run, text)
        elif suffix == ".css":
            new = _rewrite_css(run, text, None, 0, None)
        else:
            new = _rewrite_js(run, text)
        if new != text:
            f.write_bytes(new.encode("utf-8", "surrogateescape"))
            changed += 1
    run.save()
    resources = sum(1 for v in run.memo.values() if v)
    result = {"files_changed": changed, "resources": resources, "downloaded": run.new,
              "failed": dict(list(run.failed.items())[:20]), "unsupported": sorted(run.unsupported),
              "at": int(time.time())}
    if changed or run.failed:
        try:
            cfg.save_json(folder / MANIFEST, result)
        except OSError:
            pass
    if changed:
        log("Offline-ready: %d resource(s) localized in %d file(s), %d downloaded now." % (
            resources, changed, run.new))
    for url, why in list(run.failed.items())[:10]:
        log("  could not localize %s (%s)" % (url, why))
    for host in sorted(run.unsupported):
        log("  not supported (module CDN): %s" % host)
    return result


def auto(folder, log=print):
    """Called after an install: never fails the install."""
    if not cfg.load_config()["settings"].get("localize_external", True):
        return None
    try:
        return localize_folder(folder, log)
    except Exception as exc:  # noqa: BLE001 - a broken CDN must not break an installation
        log("Warning: could not localize internet resources (%s)." % exc)
        return None


def summary(folder):
    data = cfg._load_json(Path(folder) / MANIFEST, {})
    return data if isinstance(data, dict) else {}


def vendor_file(parts):
    """File under cache/vendor for the URL segments after /_vendor/, or None."""
    base = vendor_dir().resolve()
    target = base.joinpath(*parts).resolve()
    if base not in target.parents or not target.is_file():
        return None
    return target

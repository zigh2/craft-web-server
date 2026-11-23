"""Compatibility check of an installed web app.

Looks for what typically keeps a static web app on "Loading..." when a LAN server hosts it:
files requested from the wrong place, files that do not exist, resources on the internet
that an offline network can never reach, and browser features that need HTTPS."""
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import localize

MAX_INDEX = 2 * 1024 * 1024
MAX_FILE = 25 * 1024 * 1024
MAX_SCAN = 60 * 1024 * 1024
MAX_FILES = 40

_TAGS = {"script": "src", "link": "href", "img": "src", "source": "src", "iframe": "src",
         "video": "src", "audio": "src", "embed": "src", "object": "data"}
_CSS_EXTERNAL = re.compile(rb"(?:url\(\s*|@import\s+(?:url\(\s*)?)['\"]?(?:https?:)?//([A-Za-z0-9.-]+)")
_CSS_ROOT = re.compile(rb"url\(\s*['\"]?/(?!/|_vendor/)[^'\")\s]+")
_JS_ROOT = re.compile(
    rb"[\"'`]/(?:assets|static|_next|images|img|fonts|locales|lib|wasm|workers?|js|css|icons)/")
_SECURE = [b"crypto.subtle", b"navigator.clipboard", b"showSaveFilePicker", b"showOpenFilePicker"]


class _Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.base = [], None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "base" and d.get("href"):
            self.base = d["href"]
        url = d.get(_TAGS.get(tag, ""), None)
        if url and url.strip():
            self.refs.append(url.strip())


def _kind(url):
    low = url.lower()
    if low.startswith(("data:", "blob:", "javascript:", "mailto:", "tel:", "#", "about:")):
        return "skip"
    if low.startswith(("http://", "https://", "//")):
        return "external"
    return "root" if url.startswith("/") else "relative"


def _clean(url):
    return unquote(url.split("?")[0].split("#")[0])


def scan(app_dir, index_path="index.html"):
    app_dir = Path(app_dir)
    index = app_dir / index_path
    issues = []
    parser = _Refs()
    try:
        parser.feed(index.read_bytes()[:MAX_INDEX].decode("utf-8", errors="replace"))
    except OSError:
        return {"issues": [{"id": "no_index", "severity": "error", "items": [index_path]}],
                "scanned_at": int(time.time())}

    root_refs, missing, external = [], [], {}
    for url in parser.refs:
        kind = _kind(url)
        if kind == "external":
            host = urlsplit("http:" + url if url.startswith("//") else url).hostname or url
            external.setdefault(host, []).append(url)
        elif kind == "root":
            path = _clean(url).lstrip("/")
            if path.startswith("_vendor/"):          # a downloaded CDN file (see localize.py)
                if not localize.vendor_file(path.split("/")[1:]):
                    missing.append(url)
            else:
                (root_refs if (app_dir / path).is_file() else missing).append(url)
        elif kind == "relative":
            if not (index.parent / _clean(url)).is_file():
                missing.append(url)

    files, wasm = [], 0
    for i, f in enumerate(app_dir.rglob("*")):
        if i > 20000:
            break
        if not f.is_file():
            continue
        if f.suffix.lower() == ".wasm":
            wasm += 1
        elif f.suffix.lower() in (".js", ".mjs", ".css"):
            files.append(f)
    files = [f for f in sorted(files, key=lambda p: p.stat().st_size, reverse=True)
             if f.stat().st_size <= MAX_FILE][:MAX_FILES]

    css_root = js_root = scanned = 0
    secure, sab, sw = set(), False, False
    for f in files:
        if scanned > MAX_SCAN:
            break
        data = f.read_bytes()
        scanned += len(data)
        if f.suffix.lower() == ".css":
            for m in _CSS_EXTERNAL.finditer(data):
                external.setdefault(m.group(1).decode("ascii", "ignore"), []).append(f.name)
            css_root += len(_CSS_ROOT.findall(data))
        else:
            js_root += len(_JS_ROOT.findall(data))
            sab = sab or b"SharedArrayBuffer" in data
            sw = sw or b"serviceWorker.register" in data or b"serviceWorker .register" in data
            secure.update(n.decode() for n in _SECURE if n in data)
            if b"serviceWorker" in data:
                secure.add("serviceWorker")

    if missing:
        issues.append({"id": "missing_files", "severity": "error", "items": missing[:8], "count": len(missing)})
    if root_refs or css_root or js_root:
        issues.append({"id": "root_paths", "severity": "info", "items": root_refs[:5],
                       "count": len(root_refs) + css_root + js_root})
    if external:
        issues.append({"id": "external_resources", "severity": "warn", "items": sorted(external)[:8],
                       "count": sum(len(v) for v in external.values())})
    if secure:
        issues.append({"id": "secure_context", "severity": "warn", "items": sorted(secure)})
    if sab:
        issues.append({"id": "wasm_threads", "severity": "warn", "items": []})
    if sw:
        issues.append({"id": "service_worker", "severity": "info", "items": []})
    if parser.base and parser.base not in ("/", "./", "."):
        issues.append({"id": "base_href", "severity": "info", "items": [parser.base]})
    return {"issues": issues, "stats": {"refs": len(parser.refs), "files": len(files), "wasm": wasm},
            "scanned_at": int(time.time())}

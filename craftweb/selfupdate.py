"""Update the server itself from GitHub Releases: nothing to reinstall, nothing to define again.

The data lives in its own folder (see config.default_data_dir), so only the program is replaced.
Safety net: the download is verified against a published SHA-256, the new program must run and
report the expected version BEFORE anything is replaced, the old files are kept as *.old, and
if the new version keeps crashing right after the update the old one is put back."""
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import __version__
from . import config as cfg
from . import updater

SMOKE_TIMEOUT = 40
CONFIRM_AFTER = 30      # seconds a new version must stay up to count as good
MAX_EARLY_CRASHES = 2
_KEEP = {"root", "cache", "inbox", "logs", "certs", "downloads", "incoming", "run", "update",
         "state.json", "admin.json", "apps.json", ".git"}


def stage_dir():
    return cfg.base_dir() / "update"


def default_repo():
    return cfg.load_config()["settings"].get("self_update_repo") or "zigh2/craft-web-server"


def install_kind():
    """exe = the Windows build, source = a Python source tree, None = cannot update itself."""
    if getattr(sys, "frozen", False):
        return "exe" if os.name == "nt" else None
    return "source"


def asset_name(version, kind):
    return ("craft-web-server-v%s-windows-x64.zip" if kind == "exe" else "craft-web-server-v%s.zip") % version


# ---------------------------------------------------------------- checking
def check(repo=None):
    """What is the newest release and is it newer than this one?"""
    kind = install_kind()
    out = {"current": __version__, "latest": None, "update": False, "kind": kind,
           "supported": kind is not None, "repo": repo or default_repo(), "url": None, "error": None}
    try:
        releases = [r for r in updater.get_releases(out["repo"]) if str(r.get("tag_name", "")).startswith("v")]
    except Exception as exc:  # offline networks are normal
        out["error"] = updater.describe_error(exc)
        return out
    if releases:
        out["latest"] = releases[0]["tag_name"][1:]
        out["url"] = releases[0].get("html_url")
        out["update"] = cfg.version_key(out["latest"]) > cfg.version_key(__version__)
        out["release"] = releases[0]
    return out


def _expected_sha(release, asset):
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return digest[7:].lower()
    for other in release.get("assets", []):
        if other["name"] in (asset["name"] + ".sha256", "SHA256SUMS"):
            request = urllib.request.Request(other["browser_download_url"], headers={"User-Agent": updater.USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as r:
                for line in r.read().decode("utf-8", "replace").splitlines():
                    parts = line.split()
                    if parts and (len(parts) == 1 or parts[-1].lstrip("*") == asset["name"]):
                        return parts[0].lower()
    return None


# ---------------------------------------------------------------- staging
def _smoke_test(root, kind, version):
    if kind == "exe":
        cmd, cwd = [str(Path(root) / "craft-web-server.exe"), "version"], None
    else:
        cmd, cwd = [sys.executable, "-m", "craftweb", "version"], str(root)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=SMOKE_TIMEOUT, cwd=cwd,
                           creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError) as exc:
        raise updater.UpdateError("The new version cannot start (%s): update cancelled." % exc)
    if r.returncode != 0 or r.stdout.strip() != version:
        raise updater.UpdateError("The new version did not report %s (got %r): update cancelled."
                                  % (version, (r.stdout + r.stderr).strip()[:100]))


def stage(info=None, log=print):
    """Download, verify and test the newest release, ready for apply_staged()."""
    info = info or check()
    if info.get("error"):
        raise updater.UpdateError(info["error"])
    if not info["supported"]:
        raise updater.UpdateError("Self-update is not available for this kind of installation.")
    if not info["update"]:
        raise updater.UpdateError("Already up to date (%s)." % info["current"])
    version, kind, release = info["latest"], info["kind"], info["release"]
    name = asset_name(version, kind)
    asset = next((a for a in release.get("assets", []) if a["name"] == name), None)
    if asset is None:
        raise updater.UpdateError("Release v%s has no file named %s." % (version, name))
    expected = _expected_sha(release, asset)
    if not expected:
        raise updater.UpdateError("The release publishes no checksum for %s: refusing to install it." % name)

    shutil.rmtree(stage_dir(), ignore_errors=True)
    work = stage_dir() / version
    work.mkdir(parents=True)
    zip_path = work / name
    log("Downloading %s (%.1f MB) ..." % (name, asset.get("size", 0) / 1048576))
    got = updater.download(asset, zip_path)
    if got.lower() != expected:
        raise updater.UpdateError("Checksum mismatch: the download is corrupt or was tampered with.")
    log("Checksum verified.")
    extracted = work / "x"
    extracted.mkdir()
    updater.safe_extract(zip_path, extracted)
    zip_path.unlink()
    entries = [p for p in extracted.iterdir()]
    root = entries[0] if len(entries) == 1 and entries[0].is_dir() else extracted
    _smoke_test(root, kind, version)
    log("The new version starts correctly.")
    files = [p.name for p in root.iterdir() if p.name not in _KEEP and (kind == "source" or p.suffix == ".exe")]
    cfg.save_json(stage_dir() / "staged.json", {"version": version, "kind": kind, "root": str(root), "files": files})
    return version


def staged():
    data = cfg._load_json(stage_dir() / "staged.json", {})
    return data if isinstance(data, dict) and data.get("version") else None


# ---------------------------------------------------------------- applying (the old files become *.old)
def _remove(path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink()
        except OSError:
            pass


def apply_staged(log=print):
    """Replace the program with the staged version. Call it only while the server is not running."""
    data = staged()
    if not data:
        return False
    program, root, swapped = cfg.program_dir(), Path(data["root"]), []
    try:
        for name in data["files"]:
            target, new = program / name, root / name
            if target.exists():
                old = target.with_name(target.name + ".old")
                _remove(old)
                os.replace(target, old)      # a running exe can be renamed on Windows, not overwritten
                swapped.append((target, old))
            shutil.move(str(new), str(target))
    except Exception as exc:  # noqa: BLE001 - put everything back, whatever went wrong
        for target, old in reversed(swapped):
            _remove(target)
            if old.exists():
                os.replace(old, target)
        log("Update failed (%s): the previous version was restored." % exc)
        shutil.rmtree(stage_dir(), ignore_errors=True)
        return False
    cfg.save_json(stage_dir() / "pending.json", {
        "from": __version__, "to": data["version"], "started": int(time.time()), "crashes": 0,
        "swapped": [[str(t), str(o)] for t, o in swapped]})
    (stage_dir() / "staged.json").unlink(missing_ok=True)
    shutil.rmtree(Path(data["root"]).parent, ignore_errors=True)
    log("Updated to %s (the previous files are kept until the new version proves stable)." % data["version"])
    return True


def pending():
    data = cfg._load_json(stage_dir() / "pending.json", {})
    return data if isinstance(data, dict) and data.get("swapped") else None


def confirm_pending(log=print):
    """The new version stayed up long enough: delete the *.old files."""
    data = pending()
    if not data:
        return False
    for _, old in data["swapped"]:
        _remove(Path(old))
    (stage_dir() / "pending.json").unlink(missing_ok=True)
    log("Version %s is running fine; the old files were removed." % data["to"])
    return True


def rollback(log=print):
    data = pending()
    if not data:
        return False
    for target, old in reversed(data["swapped"]):
        target, old = Path(target), Path(old)
        if old.exists():
            _remove(target)
            os.replace(old, target)
    (stage_dir() / "pending.json").unlink(missing_ok=True)
    cfg.save_json(stage_dir() / "last-result.json", {"rolled_back_from": data["to"], "at": int(time.time())})
    log("Version %s keeps crashing: went back to %s." % (data["to"], data["from"]))
    return True


def note_crash(uptime, log=print):
    """Called by the supervisor when the server died. Early crashes right after an update roll it back."""
    data = pending()
    if not data or uptime >= CONFIRM_AFTER:
        return False
    data["crashes"] = int(data.get("crashes", 0)) + 1
    if data["crashes"] >= MAX_EARLY_CRASHES:
        return rollback(log)
    cfg.save_json(stage_dir() / "pending.json", data)
    return False


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

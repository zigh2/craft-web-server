# Changelog

## 1.2.0
### Added
- **Import files you already downloaded** (dashboard dialog or `python updater.py --import PATH...`):
  zips and extracted folders are matched to apps by name, installed without any download, never
  downgrade the active version, and only the versions that fit `backup_count` are extracted.
- **Local cache** (`cache/<app>/`): every downloaded, uploaded or imported zip is kept (`cache_keep` per app),
  so any version can be reinstalled or rolled back to without internet. Releases already in the cache are not downloaded again.
- **Automatic update checks** every `auto_update_hours` with a live "update available" badge, and an optional
  per-app `auto_update` that installs new releases by itself (a deliberate rollback is never undone).
- `python -m craftweb` / `craft-web-server` CLI (`serve`, `update`, `passwd`, `version`), `apps.json` created on first run.
- Disk-space check before installing, rotating `logs/server.log`, `/health` reports the version.
- **Docker** image (multi-arch, GHCR) and a **Windows build without Python** attached to every release.
- GitHub: CI matrix (Linux/Windows/macOS), lint, CodeQL, Dependabot, issue/PR templates, SECURITY.md, MIT license.
- Release workflow: monotonic versioning, release notes from this file, SHA256SUMS, build provenance attestation.

### Security
- The dashboard now runs on **its own port** (`admin_port`, default 8081). Previously a hosted app served from the
  same origin could have scripted the dashboard with an administrator's session. The public port answers 404 for `/admin`.
- TLS 1.2 minimum when HTTPS is enabled.

### Upgrade notes
- Open the dashboard on port **8081** (or set `"admin_port": 0` to keep the old shared-port behaviour).

## 1.1.0
- **Admin dashboard** at `/admin/` (Arabic/English, light/dark): overview, per-app version management,
  install from GitHub, offline ZIP upload, activity + audit log, password change.
- Security: scrypt password hash, server-side sessions bound to client IP, `HttpOnly`/`SameSite=Strict`
  cookies, CSRF token + Origin check, login throttling, admin network allow-list, strict CSP (no inline JS/CSS).
- `inbox/` drop folder: `<prefix><version>.zip` files are installed automatically.
- GitHub: `Release` workflow publishes `craft-web-server-vX.Y.Z.zip` on every push to `main`;
  `incoming/` applies a project update package and releases it.
- Version is read from the `VERSION` file.

## 1.0.0
- Static server for Craft apps, GitHub Releases updater, rollback, offline `--from-zip`.

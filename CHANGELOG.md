# Changelog

## 1.5.0
### Added
- **Offline-ready apps.** After an install the server downloads the CDN files, web fonts and CSS sub-resources an
  app loads (once, into a store shared by all apps and versions: `cache/vendor/`) and points the app at the local
  copies (`/_vendor/...`). Dashboard button, `updater.py --localize`, and `localize_external` setting (default on).
  Requests are guarded against server-side request forgery (private/loopback addresses, odd ports, redirects, size and
  count limits); analytics hosts and ES-module CDNs are skipped and reported. Nothing is ever fatal to an install.
- **One-command HTTPS** (`python server.py --setup-https`, `python -m craftweb https`, dashboard card): a private certificate
  authority and a server certificate for `localhost`, the machine name and its LAN addresses, written in pure Python
  (no openssl/mkcert), switched on in `apps.json`. The authority is kept so devices trust it once; the certificate is re-issued
  when the machine's addresses change. `/ca.crt` and `/ca.cer` serve the public authority certificate.
- The authority is **name-constrained** to local names and private address ranges (a leaked key cannot impersonate public sites).
- Dashboard: "Make offline-ready" and "Set up HTTPS" fixes in the compatibility card, HTTPS card with trust instructions.

### Fixed
- Settings page showed the configured port instead of the port the server really listens on.
- The compatibility check no longer reports `/_vendor/...` files as missing.

## 1.4.0
### Added
- **Compatibility mode for apps that expect to live at the site root.** Requests such as `/assets/app.js` or
  `/locales/en.json` are routed to the right app through the requesting page (`Referer`) or the last app opened
  (cookie). This is the usual reason an app stays on "Loading…". Responses carry `X-Craft-Compat: root-path`.
- **Own port per app** (`own_port`, `port`, or `isolate_apps` for all apps): the app is served from the root of
  its own port, with isolated storage and service workers. Ports are assigned from `app_port_base`, remembered,
  and follow `apps.json` live. Dashboard: edit form, per-app buttons and a settings switch.
- **Compatibility check** card per app: missing files, root paths, resources that need the internet, features that
  need HTTPS, `SharedArrayBuffer` (needs COOP/COEP), service workers, `<base href>`; with one-click fixes.
- `POST /admin/api/settings` (whitelisted keys only: `isolate_apps`, `cross_origin_isolation`).

### Fixed
- Dashboard "Open" links pointed to the dashboard port instead of the apps port (broken since the split-port change in 1.2.0).
- The single-page-app fallback only applies to page loads: `fetch()` of a missing file now gets a real 404
  instead of the index page (which made JSON parsing fail and apps hang).
- Home page and dashboard use the ports the server really listens on (also with `--port`).

## 1.3.0
### Added
- **Automatic app recognition.** No app definitions are needed any more: a file or folder named
  `<name>-<version>` (e.g. `lesson-builder-web-v1.2.0.zip`, `Quran_Tools_2.3.zip`) creates its app by itself
  (id, title, folder prefix) and a whole batch is grouped per app. Works in the dashboard import dialog
  (new apps are pre-selected and can be corrected), `python updater.py --import`, and the `inbox/` folder.
  Turn off with `"auto_create_apps": false`; `--no-create` for a single import.
- The same app written with other punctuation or case (`FigCraft_Web_2.0.zip` vs `figcraft-web-`) is
  attached to the existing app instead of creating a duplicate.
- Project owner set to `zigh2` (README links, Docker image path, license).

### Changed
- File names are never matched against a release's `asset_pattern` any more (a loose pattern such as
  `.*web.*` could attach unrelated files to the wrong app).

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

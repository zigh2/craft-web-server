# Security policy

## Reporting a vulnerability
Please **do not open a public issue**. Use GitHub's *Security → Report a vulnerability*
(private advisory) on this repository. You will get an answer within a few days.

## Supported versions
Only the latest release receives fixes.

## Security model
Craft Web Server is meant for a **trusted internal network**.

- The dashboard runs on its **own port** (`admin_port`, default 8081) so that a hosted app can
  never script it (different origin). The public port returns 404 for `/admin`.
- No default password. `admin.json` stores a scrypt hash (file mode 0600 where supported).
- Dashboard access is limited to `admin_allowed_networks` (private ranges by default).
- Sessions: server-side, bound to the client IP, `HttpOnly` + `SameSite=Strict`, idle and
  absolute timeouts; CSRF token + `Origin` check on every POST; login throttling.
- Strict CSP on the dashboard (no inline script/style); only whitelisted static files are served.
- Archives are checked for path traversal and size before extraction; GitHub digests (SHA-256)
  are verified when provided; the GitHub token is never sent to another host.
- Localizing downloads URLs found in third-party app files: private/loopback/link-local targets, ports other than 80/443
  and redirects to them are refused, and size/count are limited (SSRF protection).
- HTTPS: the local authority's key never leaves `certs/` (mode 0600, never served); the authority is name-constrained to local
  names and private networks. Remove the authority from devices when you retire the server.
- Hosted apps are third-party code served from your server: only install releases you trust.

Out of scope: exposing the server directly to the internet, and TLS termination (use
`tls_cert`/`tls_key` or a reverse proxy).

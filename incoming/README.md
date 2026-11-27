# incoming/

Project updates are dropped here.

1. Copy the new package (e.g. `craft-web-server-v1.2.0.zip`) into this folder.
2. Commit and push to `main`.
3. The **Release** workflow unpacks it over the repository, runs the tests, commits the
   result, deletes the zip from this folder and publishes a new GitHub release.

The package must contain `server.py`, `craftweb/` and a `VERSION` file (`X.Y.Z`).
Files under `.github/workflows/` are never replaced from a package.

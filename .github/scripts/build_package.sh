#!/usr/bin/env bash
# Builds dist/craft-web-server-vX.Y.Z.{zip,tar.gz} and dist/SHA256SUMS from HEAD.
set -euo pipefail
v="${1:?usage: build_package.sh X.Y.Z}"
name="craft-web-server-v$v"

rm -rf dist && mkdir dist
git archive --format=tar --prefix="craft-web-server/" HEAD | tar -x -C dist   # honours export-ignore
echo "$v" > dist/craft-web-server/VERSION
(
  cd dist
  zip -qr "$name.zip" craft-web-server
  tar -czf "$name.tar.gz" craft-web-server
  rm -rf craft-web-server
  sha256sum "$name.zip" "$name.tar.gz" > SHA256SUMS
)
ls -l dist

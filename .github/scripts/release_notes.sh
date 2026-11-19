#!/usr/bin/env bash
# Prints the CHANGELOG.md section of a version followed by install instructions.
# Usage: release_notes.sh X.Y.Z [owner/repo]
set -euo pipefail
v="${1:?usage: release_notes.sh X.Y.Z [owner/repo]}"
repo="${2:-}"

section=$(awk -v v="$v" '
  /^## / { f = ($0 == "## " v) || (index($0, "## " v " ") == 1); next }
  f
' CHANGELOG.md | sed '/./,$!d')
[ -n "$section" ] && printf '%s\n\n' "$section"

cat <<TXT
### Install
**Python 3.9+** (no dependencies)
\`\`\`
unzip craft-web-server-v$v.zip && cd craft-web-server
python server.py --set-admin-password
python server.py
\`\`\`
**Windows**: download \`craft-web-server-v$v-windows-x64.zip\` (no Python needed) when attached below.
TXT
if [ -n "$repo" ]; then
  img=$(printf '%s' "$repo" | tr '[:upper:]' '[:lower:]')
  printf '**Docker**: `docker run -p 8080:8080 -p 8081:8081 -v craftweb:/data ghcr.io/%s:%s`\n' "$img" "$v"
fi
printf '\nVerify downloads with `SHA256SUMS`.\n\n---\n'

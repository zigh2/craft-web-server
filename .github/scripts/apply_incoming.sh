#!/usr/bin/env bash
# Applies a project update dropped into incoming/*.zip onto the working tree.
set -euo pipefail
shopt -s nullglob
zips=(incoming/*.zip)
if [ ${#zips[@]} -eq 0 ]; then echo "No incoming package."; exit 0; fi

zip=$(printf '%s\n' "${zips[@]}" | sort -V | tail -n1)
echo "Applying $zip"
work=$(mktemp -d)
unzip -q "$zip" -d "$work"

server=$(find "$work" -maxdepth 2 -name server.py | head -n1 || true)
[ -n "$server" ] || { echo "::error::server.py not found in $zip"; exit 1; }
root=$(dirname "$server")
[ -f "$root/craftweb/__init__.py" ] || { echo "::error::craftweb/ package missing in $zip"; exit 1; }
[ -f "$root/VERSION" ] || { echo "::error::VERSION file missing in $zip"; exit 1; }
grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+\s*$' "$root/VERSION" || { echo "::error::VERSION must be X.Y.Z"; exit 1; }

# Never take runtime data, the incoming folder or any VCS data from a package.
rm -rf "$root/.git" "$root/incoming" "$root/root" "$root/downloads" "$root/inbox" "$root/cache" "$root/dist" "$root/run" "$root/update" "$root/certs" \
       "$root/logs" "$root/state.json" "$root/admin.json"

# Replace every tracked file except the incoming folder and the workflows, then
# copy the package over. Workflows are restored afterwards: GITHUB_TOKEN may not
# change them and a package must not be able to alter its own release pipeline.
git ls-files -z | grep -zvE '^(incoming/|\.github/workflows/)' | xargs -0 -r rm -f
cp -a "$root"/. ./
rm -rf .github/workflows
git checkout -- .github/workflows
rm -f incoming/*.zip
echo "Applied package version $(tr -d ' \r\n' < VERSION)"

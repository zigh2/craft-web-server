#!/usr/bin/env bash
# Prints the version to release. It never goes backwards:
#   - VERSION file newer than every tag  -> use the file (you bumped it on purpose)
#   - otherwise                           -> latest tag + 1 patch
#   - optional argument patch|minor|major -> bump the latest tag instead
set -euo pipefail
bump="${1:-none}"
file=$(tr -d ' \r\n' < VERSION)
re='^[0-9]+\.[0-9]+\.[0-9]+$'
[[ "$file" =~ $re ]] || { echo "VERSION must look like X.Y.Z (got '$file')" >&2; exit 1; }

latest=$(git tag -l 'v[0-9]*.[0-9]*.[0-9]*' | sed 's/^v//' | sort -V | tail -n1 || true)
if [ -z "$latest" ]; then echo "$file"; exit 0; fi

IFS=. read -r a b c <<<"$latest"
case "$bump" in
  major) echo "$((a + 1)).0.0"; exit 0 ;;
  minor) echo "$a.$((b + 1)).0"; exit 0 ;;
  patch) echo "$a.$b.$((c + 1))"; exit 0 ;;
esac

top=$(printf '%s\n%s\n' "$file" "$latest" | sort -V | tail -n1)
if [ "$top" = "$file" ] && [ "$file" != "$latest" ]; then
  echo "$file"
else
  echo "$a.$b.$((c + 1))"
fi

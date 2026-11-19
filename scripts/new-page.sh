#!/usr/bin/env bash
# Scaffold a new page directory from the template with the given link words.
set -euo pipefail
cd "$(dirname "$0")/.."

name="${1:-}"
slug="${2:-}"
words='^[a-z0-9]+(-[a-z0-9]+)*$'
if [[ ! "$name" =~ $words || ! "$slug" =~ $words || ${#slug} -lt 10 ]]; then
  echo "Usage: $0 <page-name> <link-words>" >&2
  echo "  Both are lowercase words separated by hyphens; the link needs at least 10 characters." >&2
  echo "  Example: $0 rose-garden moonlit-rose-garden" >&2
  exit 1
fi

target="frontend/pages/$name"
if [ -e "$target" ]; then
  echo "$target already exists" >&2
  exit 1
fi
if grep -qs "\"slug\": \"$slug\"" frontend/pages/*/page.json; then
  echo "Another page already uses the link '$slug'" >&2
  exit 1
fi

cp -r frontend/pages/_template "$target"
sed -i "s/__NAME__/$name/g; s/__SLUG__/$slug/g" "$target/page.json" "$target/index.html"

echo "Created $target"
echo "Path of its link: /$slug"

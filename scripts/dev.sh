#!/usr/bin/env bash
# Hot-reload dev server for pages at http://localhost:5173/<link-words>.
# Runs in Docker; the app container serves the API. Ctrl-C stops the dev server.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose --profile dev up dev

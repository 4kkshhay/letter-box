#!/usr/bin/env bash
# Prompt for an admin password and print its scrypt hash for .env.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose run --rm --no-deps --build app python -m app.admin.auth

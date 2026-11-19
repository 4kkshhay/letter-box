#!/usr/bin/env bash
# Prompt for one or more page passwords and print PAGE_PASSWORD_HASHES for .env.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose run --rm --no-deps --build app python -m app.gate

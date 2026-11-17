#!/usr/bin/env bash
# Restart the running stack without rebuilding. Never removes data.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose restart
docker compose ps

#!/usr/bin/env bash
# Build the image and start (or update) the stack. Never removes data.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# Create the data directory as the current user so the container can write it.
set -a
. ./.env
set +a
mkdir -p "${DATA_DIR:-./data}"

docker compose up -d --build --wait
docker compose ps

#!/usr/bin/env bash
# Type-check, build and test the pages, then run the backend tests, all in Docker.
# Extra arguments are passed to pytest.
set -euo pipefail
cd "$(dirname "$0")/.."

docker build --target frontend-test .
docker build --target test -t letterbox:test .
docker run --rm letterbox:test "$@"

# Validate both the local and production Compose shapes without exposing ports
# or contacting the tunnel.
docker compose config --quiet
TUNNEL_TOKEN=ci-placeholder \
  APP_IMAGE=ghcr.io/example/letterbox@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  docker compose -f docker-compose.yml -f docker-compose.production.yml config --quiet

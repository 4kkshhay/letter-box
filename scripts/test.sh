#!/usr/bin/env bash
# Type-check and build the pages, then run the backend tests, all in Docker.
set -euo pipefail
cd "$(dirname "$0")/.."

docker build --target test -t letterbox:test .
docker run --rm letterbox:test "$@"

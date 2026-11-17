#!/usr/bin/env bash
# Type-check, build and test the pages, then run the backend tests, all in Docker.
# Extra arguments are passed to pytest.
set -euo pipefail
cd "$(dirname "$0")/.."

docker build --target frontend-test .
docker build --target test -t letterbox:test .
docker run --rm letterbox:test "$@"

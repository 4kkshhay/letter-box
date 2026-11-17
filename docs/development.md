# Development

Everything builds and runs in Docker. No local Python or Node is required.

## Prerequisites

- Docker Engine with Compose v2 (Docker Desktop with WSL integration enabled
  on Windows, or any Linux Docker host).

## First run

```bash
./scripts/run.sh
```

This creates `.env` from `.env.example` if missing, creates the data
directory, builds the image, starts the stack and waits until it is healthy.

| URL | What |
| --- | --- |
| `http://localhost:8610/` | Public app |
| `http://localhost:8610/health/ready` | Public readiness |
| `http://localhost:8611/health/ready` | Admin readiness |

## Commands

| Command | Purpose |
| --- | --- |
| `./scripts/run.sh` | Build and start, or update a running stack |
| `./scripts/restart.sh` | Restart without rebuilding |
| `./scripts/test.sh` | Type-check and build the pages, run backend tests |
| `./scripts/hash-admin-password.sh` | Generate a scrypt password hash for `.env` |
| `docker compose logs -f app` | Follow logs |
| `docker compose down` | Stop and remove the container (data is kept) |

Never run `docker compose down -v` or delete the data directory unless the
intent is to wipe saved data.

`./scripts/test.sh` runs the frontend type-check, build and component tests,
then the backend tests. Extra arguments go to pytest, for example
`./scripts/test.sh -k migrate`.

The same script runs in CI on every pull request
(`.github/workflows/ci.yml`).

### Admin login

The first-run `.env` accepts the development-only password `change-me`. Replace
it before using the app with real data:

```bash
./scripts/hash-admin-password.sh
```

Copy the printed `ADMIN_PASSWORD_HASH='…'` line into `.env`, and replace
`SESSION_SECRET` with a long random value. The plain password is never stored.
The admin dashboard is at `http://localhost:8611/`.

## Adding a page

```bash
./scripts/new-page.sh my-page some-chosen-words
./scripts/run.sh                 # rebuild and restart
```

This copies `frontend/pages/_template` to `frontend/pages/my-page` and sets
its link to `/l/some-chosen-words` in `page.json`. Edit `Page.tsx`, its
stylesheet and `page.json`, then open
`http://localhost:8610/l/some-chosen-words`.

- Never change a page's directory name or slug once its link is in use.
- The server refuses to start if any `page.json` is invalid; the reason is in
  `docker compose logs app`.
- Put images, audio and video in the page's directory and import them from
  its code, so they are bundled with hashed names.

### Opening a page on a phone

Set `PUBLIC_BIND=0.0.0.0` in `.env`, run `./scripts/run.sh`, and open
`http://<computer-ip>:8610/l/<slug>` from a phone on the same network. The
host firewall must allow the port. Set it back to `127.0.0.1` afterwards.

## Configuration

All settings live in `.env` (see `.env.example`).

- `COMPOSE_FILE` selects the Compose files. Local development loads
  `docker-compose.local.yml`, which publishes both apps on `127.0.0.1`.
- `DATA_DIR` is the host directory holding the SQLite file. If the checkout
  is on a Windows-mounted path under WSL, point `DATA_DIR` at a directory on
  the Linux filesystem (for example `~/letterbox-data`); SQLite file locking
  is unreliable on Windows mounts.
- `APP_UID` / `APP_GID` must own `DATA_DIR`. Use `id -u` and `id -g`.

## How the image is built

| Stage | Base | Does |
| --- | --- | --- |
| `frontend` | `node:24-slim` | `npm ci`, type-check, `vite build` |
| `frontend-test` | `frontend` | Runs the frontend component tests |
| `base` | `python:3.14-slim` | Installs pinned Python deps, copies app, migrations and built pages |
| `test` | `base` | Adds dev deps and tests; runs pytest |
| `app` | `base` | Runtime image; default target |

On start the container loads and validates the page configs, applies pending
migrations, then serves the public app on port 8000 and the admin app on
port 8001.

## Database migrations

Add a file `backend/migrations/NNNN_description.sql` with the next number.
Migrations run in order on start, each in its own transaction, and are
recorded in `PRAGMA user_version`. They must never drop saved data.

## Updating dependencies

Backend (requires [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv pip compile --universal --python-version 3.14 --no-header requirements.in -o requirements.txt
uv pip compile --universal --python-version 3.14 --no-header requirements-dev.in -o requirements-dev.txt
```

Frontend (requires Node 24): edit versions in `frontend/package.json`, then
run `npm install` in `frontend/` to refresh `package-lock.json`.

## Running the backend without Docker (optional)

```bash
cd backend
uv venv --python 3.14 && uv pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q
DATABASE_PATH=/tmp/letterbox.db .venv/bin/python -m app.serve
```

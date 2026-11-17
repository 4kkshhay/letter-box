# LetterBox

A small self-hosted site that serves mobile-first interactive pages from
permanent QR-code links. Each page is an independent directory of
code and assets, and may save and restore deliberately submitted input. A
password-protected admin dashboard lists pages, shows responses and visits,
and generates QR codes.

**Status:** Phase 3 (inputs and tracking) complete. See the
[roadmap](docs/roadmap.md) and [progress log](docs/progress.md).

## Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** Vite, React, TypeScript — built to static files, served by the backend
- **Runtime:** one Docker image, one container, one database file

No database server, no Node runtime in production, no third-party services.

## Layout

```text
backend/          FastAPI app (public + admin), migrations, tests
frontend/pages/   One directory per page: config, code, assets
frontend/shared/  Code shared by pages
scripts/          Run / test / new-page / export-db helpers
docs/             Project documentation
data/             SQLite file for local runs (gitignored)
```

## Documentation

- [Architecture](docs/architecture.md) — stack, boundaries, security rules
- [Specification](docs/specification.md) — page config, data model, routes
- [Deployment](docs/deployment.md) — Docker, tunnel, admin, data export
- [Development](docs/development.md) — local setup, commands, dependencies
- [Roadmap](docs/roadmap.md) — phases, acceptance tests, out-of-scope items
- [Progress](docs/progress.md) — what was built and verified per phase
- [Decisions](docs/decisions.md) — decision log
- [Deferred](docs/deferred.md) — postponed items

## Quick start

Requires Docker with Compose v2.

```bash
./scripts/run.sh     # build, start, wait until healthy
./scripts/test.sh    # build checks and backend tests
```

The public app is then at `http://localhost:8610/` and the admin app at
`http://localhost:8611/`. See [development](docs/development.md).

# LetterBox

A small self-hosted site that serves mobile-first interactive pages from
permanent, unguessable QR-code links. Each page is an independent directory of
code and assets, and may save and restore deliberately submitted input. A
password-protected admin dashboard lists pages, shows responses and visits,
and generates QR codes.

**Status:** initial setup — no application code yet. See the
[roadmap](docs/roadmap.md).

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
- [Roadmap](docs/roadmap.md) — phases, acceptance tests, deferred items

## Quick start

Not available until Phase 1 is complete. The intended workflow is:

```bash
cp .env.example .env
docker compose up -d --build
```

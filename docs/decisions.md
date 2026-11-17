# Decision log

One entry per decision, newest last. Entries are not edited after the fact;
a later decision that replaces one says so.

| ID | Date | Phase | Decision | Reason |
| --- | --- | --- | --- | --- |
| D-001 | 2026-11-17 | 0 | Pages are a static multi-page build served by the backend; no Node server in production | Pages are private and `noindex`, so server rendering adds nothing; one container instead of two |
| D-002 | 2026-11-17 | 0 | One directory per page holding code, assets and `page.json`; the link slug lives in `page.json`; no registration step or link table | Every page needs a code change and deploy anyway; fewer moving parts. Requires a private repository |
| D-003 | 2026-11-17 | 0 | Each page is a separate build entry and its HTML is served only for its exact slug | Nothing served publicly may list or link other pages |
| D-004 | 2026-11-17 | 0 | Public and admin apps are separate ASGI apps on separate ports in one process | Admin routes cannot leak through routing mistakes |
| D-005 | 2026-11-17 | 0 | Admin is a password-protected dashboard on `admin.<domain>`; page previews are served by the admin app, read-only | A login on the admin host is not visible to the public host; serving previews from the admin app keeps them out of open counts |
| D-006 | 2026-11-17 | 0 | SQLite through stdlib `sqlite3`; no ORM or migration library | Two small tables |
| D-007 | 2026-11-17 | 0 | Saves merge per field and the last write wins; no revision counter | Single visitor per page |
| D-008 | 2026-11-17 | 0 | Every open is stored with a timestamp; "visits" are derived by merging opens under 30 minutes apart | Distinguishes a refresh from a return without storing visitor details; the rule can change later |
| D-009 | 2026-11-17 | 0 | Unknown and disabled links redirect to a neutral "Nothing here" root page | Reveals nothing, and a broken link still shows something |
| D-010 | 2026-11-17 | 0 | The Compose project runs its own `cloudflared` tunnel, publishes no host ports on the server, and is built on the server | Isolation from other stacks on the host; avoids cross-building for arm64 |
| D-011 | 2026-11-17 | 0 | Data lives in a bind-mounted host directory; a manual export script replaces automated backups | The file is visible and easy to copy; survives image rebuilds |
| D-012 | 2026-11-17 | 1 | Base images `python:3.14-slim` (runtime) and `node:24-slim` (build only) | Current stable Python and a mature Node LTS, both available for arm64; glibc avoids native-binary issues in the build tools |
| D-013 | 2026-11-17 | 1 | Backend deps are listed in `requirements*.in` and fully pinned with `uv pip compile`; frontend deps use exact versions plus `package-lock.json` | Reproducible builds without extra tooling inside the image |
| D-014 | 2026-11-17 | 1 | Both apps are served by two uvicorn servers in one asyncio loop, with access logging disabled | One process and one database writer; request paths contain secret slugs |
| D-015 | 2026-11-17 | 1 | Settings are a plain dataclass filled from environment variables | A handful of values; no settings library needed |
| D-016 | 2026-11-17 | 1 | SQLite uses its default rollback journal, not WAL | One process, tiny traffic; works on any filesystem and keeps the database a single file, which simplifies export |
| D-017 | 2026-11-17 | 1 | Migration `0001` creates both tables during Phase 1 | The migration runner needs a real migration to exercise, and the schema is already specified |
| D-018 | 2026-11-17 | 1 | Timestamps are stored as ISO-8601 UTC text | SQLite has no native datetime type |
| D-019 | 2026-11-17 | 1 | The container runs as a non-root user set by `APP_UID` / `APP_GID` | Least privilege; files in the bind-mounted data directory stay owned by the host user |
| D-020 | 2026-11-17 | 1 | The base Compose file publishes no ports; `COMPOSE_FILE` in `.env` adds `docker-compose.local.yml` for local loopback ports | The same `docker compose` commands work locally and on the server |
| D-021 | 2026-11-17 | 1 | Tests run inside Docker through a `test` build target | No local Python or Node needed; tests run against the same image contents |
| D-022 | 2026-11-17 | 1 | The root page is plain HTML with no script | Smallest possible response for unknown links |
| D-023 | 2026-11-17 | 1 | No site-wide visual theme; each page owns its design and its responsiveness | Pages are designed one at a time and should not constrain each other |
| D-024 | 2026-11-17 | 1 | One CI job on pull requests only, running `scripts/test.sh`; superseded runs are cancelled | Safety net for skipped local test runs at a few minutes of runner time per pull request. Resolves F-003 |
| D-025 | 2026-11-17 | 2 | The build emits each `page.json` next to its built HTML; the backend reads configs only from the build output | One artifact to ship; a page cannot be built without a config; page sources and media are not copied into the image twice |
| D-026 | 2026-11-17 | 2 | Built asset files are named by content hash only | An asset URL reveals nothing about the page it belongs to |
| D-027 | 2026-11-17 | 2 | One handler covers everything unknown on the public app: `GET`/`HEAD` outside `/api/` redirect (302) to `/`; API paths get a generic JSON `404`. Trailing-slash redirects are off | Unknown, disabled and mistyped links are indistinguishable from any other missing path |
| D-028 | 2026-11-17 | 2 | The scaffold lives in `frontend/pages/_template`; underscore-prefixed directories are type-checked but not built | Template stays compilable and uses the same relative imports as real pages |
| D-029 | 2026-11-17 | 2 | Slugs must be at least 22 URL-safe characters; the scaffold generates 32 (192 bits) | Guessing is infeasible; the check catches hand-typed or truncated slugs |
| D-030 | 2026-11-17 | 2 | Config errors name the page and the offending key but never echo values | A malformed slug is still a secret and must not reach logs |
| D-031 | 2026-11-17 | 2 | The bootstrap API already returns saved values and the acknowledged flag; writing them arrives in Phase 3 | The read is a single query and fixes the response shape the client is built against |
| D-032 | 2026-11-17 | 2 | The shared client takes the page key from the last URL path segment | The same client works for public links and, later, admin previews without configuration |
| D-033 | 2026-11-17 | 2 | Frontend component tests use Vitest, Testing Library and jsdom, run in a separate `frontend-test` build stage | Shared client behaviour (loading, retry, missing page) is verified automatically without a browser; kept out of the production build path |
| D-034 | 2026-11-17 | 2 | `PUBLIC_BIND` lets the local public port listen on the network; the admin port stays on loopback | Pages can be checked on a real phone during development |
| D-035 | 2026-11-17 | 2 | Slugs are readable lowercase words separated by hyphens (10–100 characters), chosen per page; `new-page.sh` takes the slug as an argument instead of generating one. Replaces D-029 | Links should look meaningful and be easy to type. Accepted trade-off: a link is only as hard to guess as its words; mitigations are the open log and blocking a link at the edge |

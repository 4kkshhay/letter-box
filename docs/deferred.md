# Deferred items

Things raised during implementation and postponed. Items that are out of
scope by design are listed in the [roadmap](roadmap.md).

## Open

| ID | Raised | Item | Why deferred | Revisit |
| --- | --- | --- | --- | --- |
| F-001 | Phase 1 | Vite dev server with an API proxy for hot-reload page development | Needs Node on the development machine or a containerised dev server; rebuilding through `run.sh` is enough for demo pages (reviewed in Phase 2) | Before building the first real page |
| F-002 | Phase 1 | Linters and formatters (ruff, ESLint, Prettier) | Little code so far; keeps tooling minimal | When the codebase grows or style drifts |
| F-004 | Phase 1 | Trusting forwarded headers from the tunnel (scheme, client address) | Only matters once cookies and origin checks exist | Phase 4 (admin session) and Phase 5 (deployment) |
| F-005 | Phase 1 | Pinning base images by digest | Tags are sufficient for now | Phase 5 |
| F-006 | Phase 1 | Verifying the image build on arm64 | No arm64 Docker host available during development | Phase 5, first server deploy |
| F-007 | Phase 2 | Deciding whether demo pages are deployed to the server (keep, disable or remove) | No effect until deployment | Phase 5 |
| F-009 | Phase 2 | Rate limit on `/l/*` and the page API to slow link guessing | Readable links make guessing possible; best done as an edge rule, which needs the domain | Phase 5 |
| F-008 | Phase 2 | Browser end-to-end tests (Playwright) for the acceptance flows | Component and API tests cover the logic; a browser suite adds a large dependency | Phase 4, once save, acknowledge and admin flows exist |

## Resolved

| ID | Raised | Item | Resolution |
| --- | --- | --- | --- |
| F-003 | Phase 1 | CI running `scripts/test.sh` | Added in Phase 1 as a pull-request workflow (D-024) |

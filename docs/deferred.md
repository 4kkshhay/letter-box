# Deferred items

Things raised during implementation and postponed. Items that are out of
scope by design are listed in the [roadmap](roadmap.md).

## Open

| ID | Raised | Item | Why deferred | Revisit |
| --- | --- | --- | --- | --- |
| F-001 | Phase 1 | Vite dev server with an API proxy for hot-reload page development | No pages exist yet | Phase 2, with the first demo page |
| F-002 | Phase 1 | Linters and formatters (ruff, ESLint, Prettier) | Little code so far; keeps tooling minimal | When the codebase grows or style drifts |
| F-004 | Phase 1 | Trusting forwarded headers from the tunnel (scheme, client address) | Only matters once cookies and origin checks exist | Phase 4 (admin session) and Phase 5 (deployment) |
| F-005 | Phase 1 | Pinning base images by digest | Tags are sufficient for now | Phase 5 |
| F-006 | Phase 1 | Verifying the image build on arm64 | No arm64 Docker host available during development | Phase 5, first server deploy |

## Resolved

| ID | Raised | Item | Resolution |
| --- | --- | --- | --- |
| F-003 | Phase 1 | CI running `scripts/test.sh` | Added in Phase 1 as a pull-request workflow (D-024) |

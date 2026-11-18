# Deferred items

Things raised during implementation and postponed. Items that are out of
scope by design are listed in the [roadmap](roadmap.md).

## Open

| ID | Raised | Item | Why deferred | Revisit |
| --- | --- | --- | --- | --- |
| F-001 | Phase 1 | Vite dev server with an API proxy for hot-reload page development | Needs Node on the development machine or a containerised dev server; rebuilding through `run.sh` is enough for demo pages (reviewed in Phase 2) | Before building the first real page |
| F-002 | Phase 1 | Linters and formatters (ruff, ESLint, Prettier) | Little code so far; keeps tooling minimal | When the codebase grows or style drifts |
| F-007 | Phase 2 | Deciding whether demo pages are deployed to the server (keep, disable or remove) | Kept in production for now (D-063) | After Phase 5 is closed |
| F-009 | Phase 2 | Rate limit on `/l/*` and the page API to slow link guessing | Readable links make guessing possible; best done as a Cloudflare rule on `letterbox.ink` | Phase 5 |

## Resolved

| ID | Raised | Item | Resolution |
| --- | --- | --- | --- |
| F-003 | Phase 1 | CI running `scripts/test.sh` | Added in Phase 1 as a pull-request workflow (D-024) |
| F-008 | Phase 2 | Browser end-to-end tests (Playwright) for the acceptance flows | Not added in Phase 4: pytest, Vitest and a disposable-container HTTP smoke test cover the flow without the extra browser dependency (D-050) |
| F-010 | Phase 3 | Store the admin password as a hash and provide a generator | Added stdlib scrypt hashing, `ADMIN_PASSWORD_HASH` and `scripts/hash-admin-password.sh` in Phase 4 (D-047) |
| F-004 | Phase 1 | Trusting forwarded headers from the tunnel | Decided not to trust or use them; Uvicorn proxy handling is disabled and all affected behaviour has an independent source (D-052) |
| F-005 | Phase 1 | Pinning base images by digest | Dockerfile bases and `cloudflared` are pinned by multi-architecture digest in Phase 5 (D-053) |
| F-011 | Phase 3 | Passphrase gate before showing a page | Deliberately skipped; links remain the only visitor credential and the gate stays out of scope (D-056) |
| F-006 | Phase 1 | Verifying the image build on arm64 | The GHCR arm64 image built in GitHub Actions and started successfully on the production Oracle A1 server during the first manual deployment |

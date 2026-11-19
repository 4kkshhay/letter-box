# Deferred items

Things raised during implementation and postponed. Items that are out of
scope by design are listed in the [roadmap](roadmap.md).

## Open

| ID | Raised | Item | Why deferred | Revisit |
| --- | --- | --- | --- | --- |
| F-002 | Phase 1 | Linters and formatters (ruff, ESLint, Prettier) | Little code so far; keeps tooling minimal | When the codebase grows or style drifts |
| F-007 | Phase 2 | Whether demo pages stay in production (keep, disable or remove) | Kept for now as diagnostics; not a final decision (D-063) | Later |
| F-009 | Phase 2 | Rate limit on `/l/*` and `/api/v1/pages/*` to slow link guessing | Optional hardening; readable links make guessing possible; best done as a Cloudflare rate-limiting rule on `letterbox.ink` | Later, before real pages are widely shared |
| F-012 | Phase 5 | Cloudflare Access (Zero Trust, free tier) in front of `admin.letterbox.ink`, e.g. one-time email code for the owner's address | Optional hardening; stops password brute-forcing and the shared five-attempt login lockout being triggered by others; the app's own login stays as the second layer | Later |

## Resolved

| ID | Raised | Item | Resolution |
| --- | --- | --- | --- |
| F-001 | Phase 1 | Vite dev server with an API proxy for hot-reload page development | Added as the Docker `dev` service and `scripts/dev.sh` (D-068) |
| F-003 | Phase 1 | CI running `scripts/test.sh` | Added in Phase 1 as a pull-request workflow (D-024) |
| F-008 | Phase 2 | Browser end-to-end tests (Playwright) for the acceptance flows | Not added in Phase 4: pytest, Vitest and a disposable-container HTTP smoke test cover the flow without the extra browser dependency (D-050) |
| F-010 | Phase 3 | Store the admin password as a hash and provide a generator | Added stdlib scrypt hashing, `ADMIN_PASSWORD_HASH` and `scripts/hash-admin-password.sh` in Phase 4 (D-047) |
| F-004 | Phase 1 | Trusting forwarded headers from the tunnel | Decided not to trust or use them; Uvicorn proxy handling is disabled and all affected behaviour has an independent source (D-052) |
| F-005 | Phase 1 | Pinning base images by digest | Dockerfile bases and `cloudflared` are pinned by multi-architecture digest in Phase 5 (D-053) |
| F-011 | Phase 3 | Passphrase gate before showing a page | Skipped in Phase 5 (D-056), then added as Phase 5.5 (D-071) |
| F-006 | Phase 1 | Verifying the image build on arm64 | The GHCR arm64 image built in GitHub Actions and started successfully on the production Oracle A1 server during the first manual deployment |

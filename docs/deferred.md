# Deferred items

Things raised during implementation and postponed. Items that are out of
scope by design are listed in the [roadmap](roadmap.md).

## Open

| ID | Raised | Item | Why deferred | Revisit |
| --- | --- | --- | --- | --- |
| F-001 | Phase 1 | Vite dev server with an API proxy for hot-reload page development | Needs Node on the development machine or a containerised dev server; rebuilding through `run.sh` is enough for demo pages (reviewed in Phase 2) | Before building the first real page |
| F-002 | Phase 1 | Linters and formatters (ruff, ESLint, Prettier) | Little code so far; keeps tooling minimal | When the codebase grows or style drifts |
| F-004 | Phase 1 | Trusting forwarded headers from the tunnel (scheme, client address) | Phase 4 does not rely on them: cookie `Secure` comes from `APP_ENV`, login throttling is global, and origin checks compare hosts while allowing a scheme difference | Phase 5 tunnel verification |
| F-005 | Phase 1 | Pinning base images by digest | Tags are sufficient for now | Phase 5 |
| F-006 | Phase 1 | Verifying the image build on arm64 | No arm64 Docker host available during development | Phase 5, first server deploy |
| F-007 | Phase 2 | Deciding whether demo pages are deployed to the server (keep, disable or remove) | No effect until deployment | Phase 5 |
| F-009 | Phase 2 | Rate limit on `/l/*` and the page API to slow link guessing | Readable links make guessing possible; best done as a Cloudflare rule on `letterbox.ink` | Phase 5 |
| F-011 | Phase 3 | **Idea to discuss:** passphrase gate. After the QR link opens, the page asks for a passphrase (one word, shared by all pages, known only to the intended reader) before showing content. Would give proof of the right person and protect against guessed or forwarded links. Open questions: where the phrase and its hash live, whether "received" and opens count only after a correct phrase, remembering it per device, throttling wrong attempts | Raised as an idea; not yet designed | Discuss before Phase 5 |

## Resolved

| ID | Raised | Item | Resolution |
| --- | --- | --- | --- |
| F-003 | Phase 1 | CI running `scripts/test.sh` | Added in Phase 1 as a pull-request workflow (D-024) |
| F-008 | Phase 2 | Browser end-to-end tests (Playwright) for the acceptance flows | Not added in Phase 4: pytest, Vitest and a disposable-container HTTP smoke test cover the flow without the extra browser dependency (D-050) |
| F-010 | Phase 3 | Store the admin password as a hash and provide a generator | Added stdlib scrypt hashing, `ADMIN_PASSWORD_HASH` and `scripts/hash-admin-password.sh` in Phase 4 (D-047) |

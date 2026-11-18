# Progress log

One section per phase. The checklist itself lives in the
[roadmap](roadmap.md); this file records what was built, how it was verified
and what is still open.

## Phase 0 — Repository setup

**Status:** done (2026-11-17)

- Directory skeleton, ignore files, `.env.example`, README.
- Docs: architecture, specification, deployment, roadmap.

## Phase 1 — Infrastructure

**Status:** done (2026-11-17). The arm64 image build is verified at first
server deploy (deferred item F-006).

### Built

- Backend: settings, public and admin app factories, health endpoints,
  SQLite connection helper, migration runner, migration `0001`, entry point
  serving both apps.
- Frontend: Vite multi-page config, TypeScript config, shared mount helper
  and base stylesheet, plain root page.
- Runtime: multi-stage `Dockerfile`, base and local Compose files,
  `run` / `restart` / `test` scripts.
- CI: pull-request workflow running `scripts/test.sh` (first run happens on
  the Phase 1 pull request).
- Docs: development guide, decision log, progress log, deferred list.

### Verified

| Check | Result |
| --- | --- |
| Backend tests (Python 3.14, outside Docker) | 20 passed |
| Entry point run outside Docker | Both ports answer; readiness OK; admin port does not serve the public root; database file created; clean shutdown on SIGTERM |
| Frontend type-check and build (Node 24, outside Docker) | Passes; root page emitted |
| Throwaway page entry using the shared mount helper | Builds to `pages/<name>/index.html` plus hashed assets |
| `npm ci` from the committed lockfile | Passes; lockfile includes arm64 native packages |
| `scripts/test.sh` (Docker, amd64) | Image builds; 20 passed |
| `scripts/run.sh` from a clean checkout | Creates `.env` and the data directory; container healthy; both loopback ports answer; root page served; admin port does not serve it |
| Data persistence (exit criterion) | A test row survived `restart.sh`, a no-cache rebuild with recreate, and `down` followed by `run.sh`; row removed afterwards |
| Container settings | Runs as uid 1000; 256 MB limit applied; about 43 MB in use when idle; runtime image 204 MB |
| Logging | A request to a slug-shaped path does not appear in container logs |

### Not yet verified

- Image build on arm64 (F-006).

### Notes

- The executable bit on `scripts/*.sh` must be recorded in git explicitly
  (`git update-index --chmod=+x`) when the checkout is on a filesystem that
  does not track file modes.

## Phase 2 — Page framework

**Status:** done (2026-11-17).

### Built

- Backend: page config models and loader with startup validation, saved-state
  reader, public routes (`/l/<slug>`, bootstrap API), redirect handling for
  unknown paths.
- Frontend: build emits `page.json` per page and hash-only asset names;
  shared API client and `PageRoot` (loading, retry, missing page); page
  template; `demo-static` page.
- Tooling: `scripts/new-page.sh`, frontend component tests and a
  `frontend-test` build stage, `PUBLIC_BIND` for phone testing.

### Verified

| Check | Result |
| --- | --- |
| Backend tests | 78 passed (config validation, link serving, redirects, bootstrap API, no writes on GET) |
| Frontend component tests | 8 passed (API URL, fetch outcomes, loading, retry, missing page, custom views) |
| `scripts/test.sh` in Docker | Passes |
| `scripts/new-page.sh` | Rejects invalid names and links, existing pages and links already in use; scaffolds a page with the chosen link |
| Running container | Loads 1 page; demo link returns its HTML and both assets; unknown slug, page name, `page.json` path and random paths all redirect to `/`; bootstrap API returns config; unknown API key gets generic `404`; admin port does not serve the link |
| Build output | The slug appears only in `page.json`, which no route serves |
| Logging | The slug does not appear in container logs after requests |
| Demo pages on a phone over the local network | Confirmed by the owner (during Phase 3); Phase 2 marked done |

### Notes

- The roadmap item reads "`scripts/new-page` scaffold with generated slug".
  The file is `scripts/new-page.sh`, and the slug is now chosen and passed in
  rather than generated (D-035).
- Rendering in a headless browser inside Docker was not possible in the
  development environment, which is why component tests were added (D-033).

## Phase 3 — Inputs and tracking

**Status:** done (2026-11-17).

### Built

- Backend: field validation, merge-save and open recording services;
  `PATCH …/state` and `POST …/open` with same-origin, content-type and
  body-size checks.
- Frontend: save and open calls in the API client; auto-saving
  `usePageState` hook; `PageRoot` reports one open per load; `demo-inputs`
  page (`/l/inputs-demo-page`) with a choice, multi-choice, note and a
  local-only colour control.

### Changed during the phase

- An explicit acknowledgement action was built, then removed after review
  (D-043): "received" is now the first recorded open, with nothing for the
  visitor to do. The roadmap items "Explicit, idempotent acknowledgement" and
  "Demo page with inputs and acknowledgement" are ticked as delivered and
  then superseded; acceptance test A11 no longer applies and is replaced by
  the first open being shown as received (Phase 4 dashboard).
- The "Save my answers" button was replaced by auto-save (D-044), and the
  visitor's "Clear" button was removed in favour of the admin reset (D-045).
  Acceptance tests A04/A05/A08 now apply to auto-saved changes.

### Verified

| Check | Result |
| --- | --- |
| Backend tests | 131 passed (validation, merge, null removal, empty answers, body limits, content type, same-origin, unknown pages, opens, no writes on load, acknowledge endpoint gone) |
| Frontend tests | 30 passed (API calls and error mapping, no false success, auto-save timing, no overlapping saves, retry and invalid handling, save on hide and unmount, one open per load) |
| `scripts/test.sh` in Docker | Passes |
| Running container over HTTP | Save, partial update, `null` removal, `422` on bad option, `403` without `Origin`, open recorded; bootstrap restores saved values; acknowledge endpoint returns `404` |
| Inputs demo in a browser and on a phone | Confirmed working by the owner, including auto-save |

## Phase 4 — Admin

**Status:** done (2026-11-17). Forwarded-header behaviour is checked against
the real tunnel during Phase 5 (F-004).

### Built

- Admin authentication: scrypt password hashes, generator script, signed
  12-hour session cookie, login throttling, logout and route protection.
- Dashboard: every page, public link, first open as received, derived visit
  count, raw open times, saved responses and last update.
- Read-only page preview: saved values through an admin-only bootstrap API,
  shared preview controls, no saves and no recorded opens.
- Transactional page reset and deterministic in-memory QR downloads in PNG
  and SVG formats.
- Jinja dashboard/login templates and pinned Jinja2/Segno dependencies.

### Verified

| Check | Result |
| --- | --- |
| Frontend tests | 32 passed (admin chrome, no admin open, read-only state added) |
| Backend tests | 146 passed (auth, sessions, throttle, dashboard, visits, preview, reset, QR and isolation added) |
| `scripts/test.sh` in Docker | Passes |
| Disposable runtime container | Visitor save/open appeared in dashboard and preview; reset cleared both; PNG downloaded; admin open route returned `404` |
| Running local container | Login, dashboard, saved-value preview, SVG download and public-port isolation pass on ports 8611/8610 |
| Public/admin isolation | Protected admin routes require a session; admin routes remain absent from the public app; admin has no save/open endpoints |

### Notes

- The roadmap's acknowledgement wording is retained unchanged; the dashboard
  implements the superseding definition from D-043: received is the first open.
- Playwright remains unnecessary at this size; F-008 is resolved by the
  existing pytest/Vitest coverage plus the runtime smoke test (D-050).

## Phase 5 — Deployment and regression

**Status:** done (2026-11-18). The arm64 image release, manual server
deployment and both production tunnel routes are live; a second deployment
kept all data.

### Built

- Production Compose overlay with a pinned, isolated `cloudflared` service;
  app and tunnel use read-only roots, dropped capabilities and
  `no-new-privileges`.
- Two-job GitHub Actions workflow: merges publish a private arm64 GHCR image;
  manual dispatch performs exact-digest SSH deployment, readiness checks and
  retention of the seven newest image versions.
- Global security/cache headers, production HSTS, disabled proxy-header trust
  and an early request-body limit.
- Consistent online SQLite export script with integrity check and atomic final
  file.
- Third synthetic page (`/l/regression-demo-page`) and page-authoring guide.
- Dockerfile base images pinned by multi-architecture digest.
- Idempotent production bootstrap script for the `letterbox` deployment user,
  SSH key, Docker access, private `.env` and persistent data directory.

### Verified

| Check | Result |
| --- | --- |
| Backend tests | 150 passed |
| Frontend tests | 32 passed; all three pages type-check and build |
| `scripts/test.sh` in Docker | Passes |
| GitHub workflows | Both workflow files pass `actionlint` |
| Production Compose | Merged config validates; no host ports; pinned tunnel image runs with read-only root and dropped capabilities |
| arm64 release build | `docker buildx build --platform linux/arm64 --target app` passes with pinned bases |
| Hardened local container | Healthy with read-only root, all capabilities dropped, `no-new-privileges`, init and 256 MB limit applied |
| Regression deploy | Original two links and their saved state remain; third link works; security/cache headers verified |
| Database export | Snapshot passes `integrity_check` and matches live state/open row counts |
| GitHub release | Push to `main` built and published the private arm64 image for commit `e4d9b53` |
| Manual production deploy | Exact image deployed successfully to `/srv/letter-box`; both internal readiness checks passed |
| Native arm64 runtime | App and pinned `cloudflared` containers started successfully on the target server; resolves F-006 |
| Production tunnel | `letterbox.ink` and `admin.letterbox.ink` route through `letterbox-origin`; public pages return `200`, admin redirects to login and public/admin isolation holds |
| Production headers | HTTPS responses include HSTS, CSP, `no-store`, frame denial, referrer and permissions policies; Cloudflare reports dynamic responses |
| Phone over HTTPS | Owner confirmed all pages load on a phone over `letterbox.ink` (2026-11-18) |
| Visit counting | Owner confirmed raw opens are recorded; opens from another device within 30 minutes merged into one visit under D-008, which led to D-064 |
| Production same-origin check | A `POST …/open` for a non-existent page with `Origin: https://letterbox.ink` gets `404` (check passed, nothing written); a foreign or missing Origin gets `403` |

### Follow-ups after review (2026-11-18)

- Release build no longer emits provenance/SBOM attestations, so GHCR
  retention counts real releases (D-060).
- Deploy removes this project's older app images on the server (D-061).
- Dashboard public links are copy-only text (D-062).
- Demo pages stay in production for now (D-063).
- Opens record the browser's navigation type (migration 0002); the dashboard
  shows total and new opens and labels each open time, replacing visit
  merging (D-064). Existing opens show as "Unknown". Verified: 158 backend and
  36 frontend tests; migration applied to an existing local database with its
  opens and answers intact.
- Fixed: admin "Reset page data" and "Sign out" returned `403 Forbidden`
  because the global `no-referrer` policy made browsers send `Origin: null`
  on form posts (D-065). Covered by a header test and confirmed in a browser.

### Second production deployment (2026-11-18, commit `e275647`)

| Check | Result |
| --- | --- |
| Data survival | Saved answers and opens from before the deploy were intact |
| Admin reset | "Reset page data" works in production (D-065) |
| Open labels | Opens are labelled by navigation type in the production dashboard (D-064) |
| Running stack | App healthy on the new image; tunnel container unchanged |

### Not yet verified

- Old-image cleanup (D-061): on the second deploy the step ran without error
  but left the previous image (removed by hand afterwards; `docker image rm -f`
  works on the server). Errors were suppressed, so the cause is unknown;
  listing by repository and by `reference=` filter both work on the server
  (Docker 29.6.1, containerd image store). The step now logs each removal and
  any failure with Docker's error; confirm on the next deploy.
- `docker ps` shows the app image as a bare ID; this is display only. The
  container's configured image is the GHCR reference by digest and the image
  keeps its tag, so manual Compose commands do not pull again.
- GHCR retention counts one version per release (D-060).
- Edge rate limiting for readable links (F-009).

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

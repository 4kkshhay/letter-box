# Roadmap

Implement one phase at a time; keep the project runnable after each. Update
this file in the same change as the work it describes.

## Phase 0 — Repository setup

- [x] Directory skeleton, `.gitignore`, `.dockerignore`, `.env.example`
- [x] README and initial docs (architecture, specification, deployment)

## Phase 1 — Infrastructure

- [x] FastAPI skeleton with public and admin apps on separate ports
- [x] Vite multi-page + React + TypeScript skeleton
- [x] Multi-stage `Dockerfile` (arm64-compatible), Compose with local ports
- [x] Run/restart/test scripts
- [x] SQLite on the `./data` mount, migration runner
- [x] `/health` and `/health/ready`
- [x] `docs/development.md`

**Exit:** container starts, readiness healthy, rebuild keeps the database.

## Phase 2 — Page framework

- [x] `page.json` loading and startup validation
- [x] `/l/<slug>` serving and hashed assets
- [x] "Nothing here" root page; redirect for unknown and disabled links
- [x] Bootstrap API and shared client (loading and error states)
- [x] `scripts/new-page` scaffold with generated slug
- [x] One demo page without inputs

**Exit:** the demo opens on a phone from its link; no other URL reveals it.

## Phase 3 — Inputs and tracking

- [x] Field validation and merge-save
- [x] Restore saved state on load
- [x] Explicit, idempotent acknowledgement
- [x] Record opens with timestamps
- [x] Demo page with inputs and acknowledgement

**Exit:** saved input restores in another browser; opens are recorded; a page
load alone never acknowledges.

## Phase 4 — Admin

- [x] Password login and session
- [x] Dashboard: pages, visit count, open times, acknowledgement, responses
- [x] Read-only admin view of a page with saved values
- [x] Reset page data
- [x] QR PNG/SVG download

**Exit:** test as visitor → verify in dashboard → reset → QR works locally;
admin views change nothing; admin routes absent from the public port.

## Phase 5 — Deployment and regression

- [ ] `cloudflared` service and tunnel for both hostnames
- [ ] Deploy to the server in its own directory and Compose project
- [ ] `scripts/export-db`
- [ ] Security headers, safe logging, cache controls, body limits
- [ ] Real phone test over HTTPS
- [ ] Add another demo page; verify earlier links and data are intact
- [ ] `docs/adding-a-page.md`

**Exit:** end-to-end over HTTPS; data survives redeploy; old links work.

## Phase 6 — Real pages (deferred)

Designed and built one at a time on the finished platform.

## Acceptance tests

| ID | Test | Expected |
| --- | --- | --- |
| A01 | Clean checkout, documented commands | Starts; readiness healthy |
| A02 | Open two pages by their links | Each shows its own page |
| A03 | Unknown slug, disabled page, random path | Same redirect to "Nothing here" |
| A04 | Submit input, refresh | Values reappear |
| A05 | Same link in another browser | Same saved values |
| A06 | Page without fields | Nothing saved |
| A07 | Malformed or undeclared input | `422`; nothing written |
| A08 | Edit one saved field | Other fields kept |
| A09 | Fetch page HTML without running scripts | No open, no acknowledgement |
| A10 | Open, refresh, reopen after 30+ minutes | Three opens, two visits |
| A11 | Acknowledge twice | One record; first timestamp kept |
| A12 | Admin view of a page with saved input | Values shown; read-only; no open recorded |
| A13 | Reset a page | Responses, acknowledgement and opens cleared; link still works |
| A14 | Admin routes on the public port; dashboard without login | Not reachable |
| A15 | Rebuild and redeploy the image | Saved data preserved |
| A16 | Add a new page and deploy | Old links and data intact |
| A17 | Download QR twice | Same URL |
| A18 | Scan printed QR on a phone | Correct page opens |
| A19 | Failed save / offline | No false success; retry offered |
| A20 | Inspect caching and logs | No HTML/API caching; no slugs or bodies logged |
| A21 | Mobile, reduced motion, no WebGL/autoplay | Content and controls usable |
| A22 | Run the export script | Snapshot file opens and matches live data |

Automate backend tests. Browser end-to-end for A04, A05, A10–A13 where
practical. A18 and A21 are manual.

## Deferred / out of scope

- Page builder, CMS or no-code editor
- Visitor accounts, notifications, chat
- Analytics beyond open timestamps
- Shared state between pages
- Fields saved for the admin but not restored to the page
- Passphrase gate on pages
- Stale-write conflict detection
- Multiple admin users or roles
- Automated backups, external databases, caches, queues, object storage
- Heavy animation/3D libraries until a specific page needs one

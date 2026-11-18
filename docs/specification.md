# Specification

## Terms

- **Page** — one directory under `frontend/pages/`, reachable at one permanent
  link and printed as one QR code.
- **Slug** — the words that make up the link: `https://letterbox.ink/l/<slug>`.
- **Field** — a named input a page may save and restore.

## Page config

`frontend/pages/<name>/page.json`:

```json
{
  "slug": "several-chosen-words",
  "title": "Demo with inputs",
  "enabled": true,
  "fields": {
    "choice": { "type": "enum", "options": ["a", "b", "c"] },
    "picks": { "type": "multi", "options": ["x", "y", "z"] },
    "note": { "type": "string", "max_length": 500 }
  }
}
```

Rules, checked when the server starts (it refuses to start otherwise):

- The directory name is lowercase letters, digits and hyphens. Directories
  starting with an underscore are not pages and are not built.
- `slug` is lowercase words (letters and digits) separated by single
  hyphens, 10 to 100 characters, and unique across pages. More and less
  common words make a link harder to guess.
- `title` is required. `enabled` defaults to `true`.
- Field names are lowercase letters, digits and underscores, starting with a
  letter. `enum` and `multi` need a non-empty list of unique `options`;
  `string` takes `max_length` (default 500, at most 5000).
- Unknown keys are rejected.

Behaviour:

- `fields` is optional. A page without fields saves nothing.
- Every declared field is saved automatically and restored on later visits.
  Anything not declared is page-local and never sent to the server.
- `enabled: false` makes the link behave like an unknown one after the next
  deploy.

## State rules

- Saved state is loaded from the server on page load; nothing durable lives in
  localStorage or cookies. Show a loading state until it arrives.
- Saving is automatic; there is no save button. Choices save as soon as
  they change; text saves after a short pause in typing (800 ms) and when
  the field loses focus. Anything unsaved is sent when the page is hidden or
  closed. The page shows whether it is saving, saved, or failed.
- Visitors cannot clear their answers; clearing is the admin's
  "Reset page data".
- The backend validates submissions against `page.json`; unknown fields are
  rejected with `422` and nothing is written. One invalid field rejects the
  whole update.
- Values: `enum` takes one option; `multi` takes a list of distinct options
  (an empty list is a valid answer); `string` takes text up to `max_length`
  characters (an empty string is a valid answer). `null` removes a saved
  value.
- Partial updates are merged into the stored JSON in one statement: given
  fields replace saved ones, `null` removes them, others are kept. Last write
  wins.
- Submitted text is returned exactly as entered; pages must render it as
  text, never as HTML.
- Removing or renaming a field in `page.json` must keep or migrate values
  already saved.

## Tracking

- **Opens** — the page's script reports one open per page load and the server
  stores its timestamp and the browser's navigation type (`navigate`,
  `reload`, `back_forward`; NULL if unavailable or recorded before the type
  existed). Requests that do not run the script (link previews, crawlers) are
  not recorded. Every open is counted; the dashboard labels each one as
  "New open", "Refresh", "Back/forward" or "Unknown" and counts new ones
  (`navigate`, `back_forward`) separately. No device or browser identity is
  stored, so opens from different devices are not told apart.
- **Received** — derived for display: the time of the first recorded open.
  It happens automatically; the visitor does nothing. It shows that the page
  was opened in a browser, not who opened it, so the page should be reset
  after testing and before the link is handed out.
- Admin previews never record opens or change saved values.

## Data model

Two SQLite tables, timestamps in UTC. Migrations never drop data.

### `page_state`

One row per page, created on first submission.

| Column | Type | Purpose |
| --- | --- | --- |
| `page` | TEXT PK | Page directory name |
| `response_json` | TEXT NULL | Latest submitted values; NULL = no response |
| `responded_at` | DATETIME NULL | Last successful save |
| `acknowledged_at` | DATETIME NULL | Unused since Phase 3 (kept; migrations never drop columns) |

### `page_opens`

One row per reported page load.

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | INTEGER PK | |
| `page` | TEXT | Page directory name (indexed) |
| `opened_at` | DATETIME | |
| `kind` | TEXT NULL | Browser navigation type: `navigate`, `reload` or `back_forward` (added by migration 0002) |

## Public app

JSON API under `/api/v1`, `Cache-Control: no-store`.

| Method | Route | Behaviour |
| --- | --- | --- |
| GET | `/` | Neutral "Nothing here" page |
| GET | `/l/{slug}` | Page HTML; unknown or disabled redirects to `/` |
| GET | any other path | Redirects to `/` |
| GET | `/api/v1/pages/{slug}` | Title, fields, saved state |
| PATCH | `/api/v1/pages/{slug}/state` | Validate and merge submitted fields |
| POST | `/api/v1/pages/{slug}/open?kind=` | Record one open with its optional navigation type |
| GET | `/assets/*` | Build files named by content hash only; no listing |
| GET | `/health`, `/health/ready` | Liveness; database readiness |

Response of `GET /api/v1/pages/{slug}`; it never contains the slug or the
page's directory name:

```json
{
  "title": "Demo with inputs",
  "fields": { "choice": { "type": "enum", "options": ["a", "b", "c"] } },
  "state": { "choice": "b" }
}
```

`state` holds only fields the page currently declares.

Save request and response:

```json
{ "fields": { "choice": "b" } }
```

```json
{ "state": { "choice": "b", "note": "hello" }, "saved": true }
```

Validation failure (`422`) names the fields but never echoes values:

```json
{ "detail": "Invalid input", "errors": { "choice": "must be one of the options" } }
```

`POST …/open` returns `204` and needs no request body. `kind` is optional;
any value other than `navigate`, `reload` or `back_forward` gets `422`.

Mutation rules (`PATCH` and `POST`):

| Check | Failure |
| --- | --- |
| `Origin` header present and its host equals the request `Host` (scheme may differ behind a TLS proxy) | `403` |
| `Content-Type: application/json` (state only) | `415` |
| Body at most 64 KiB (state only) | `413` |
| Body is `{"fields": {…}}` with at least one field | `422` |

API calls for an unknown or disabled slug return the same generic `404` as
any unmatched API path. Page links and `/` also answer `HEAD`.

Every response sends `X-Robots-Tag: noindex, nofollow`,
`Referrer-Policy: no-referrer` (admin app: `same-origin`, so its form posts
keep their `Origin`), `X-Content-Type-Options: nosniff`, a restrictive
content security policy and framing/permissions restrictions. Production also
sends HSTS. HTML, API, health, redirects and errors use `Cache-Control:
no-store`; only content-hashed files below `/assets/` are cached for one year
as immutable. Mutation requests with a declared body over 64 KiB are rejected
before routing.

### Shared client

Pages wrap themselves in `PageRoot` from `frontend/shared/`. It loads the
page data before rendering, shows a loading view meanwhile, and a retry view
on failure; a page may supply its own versions of both. If the API reports
the page as gone, the browser is sent to `/`. After the first successful
load it reports one open; a failed report is ignored.

Pages with inputs use `usePageState(page)` from
`frontend/shared/usePageState.ts` and keep full control of their own
presentation. It returns `{ values, status, update, saveNow }`:

- `update(fields, { immediate })` shows the change at once and saves it in
  the background — immediately for choices, after a pause for typing.
- Saves never overlap; changes made during a save are sent right after it.
- A failed save keeps the change and resends it on `saveNow()` (e.g. a
  "Try again" button or leaving a text field) or with the next change. A
  change rejected as invalid is not resent.
- `values` shows the visitor's latest changes; `status` says whether they
  have reached the server.

`status` is `idle`, `pending`, `done` or `error` with a reason (`invalid`,
`unavailable`, `failed`); `failureMessage(reason)` gives default wording.

## Admin app

Separate port, served at `admin.letterbox.ink`. Everything except `/login`
requires a session (health checks remain available to the container runtime).
The password is stored only as a scrypt hash in `ADMIN_PASSWORD_HASH`, generated
by `scripts/hash-admin-password.sh`. A successful login sets a signed 12-hour
`HttpOnly`, `SameSite=Strict` cookie; it is also `Secure` in production. Five
failed attempts within five minutes temporarily throttle all logins.

| Method | Route | Behaviour |
| --- | --- | --- |
| GET, POST | `/login` | Password login; sets session cookie |
| POST | `/logout` | End session |
| GET | `/` | Dashboard: every page with link, received (first open), open count with new opens counted separately, labelled open times, saved values |
| GET | `/view/{page}` | The page in admin mode |
| GET | `/api/v1/pages/{page}` | Same payload as the public API plus `"admin": true` |
| POST | `/pages/{page}/reset` | Delete the page's saved values and opens (after confirmation) |
| GET | `/pages/{page}/qr.png`, `/qr.svg` | QR code for the permanent link |

Admin mode, handled by the shared client code when the payload has
`"admin": true`:

- shows saved values exactly as the visitor would see them;
- is read-only — saving is disabled;
- does not report an open;
- shows a bar with **Reset page data**.

The dashboard distinguishes "no response" from "empty answer". QR generation
uses `PUBLIC_BASE_URL` and refuses non-HTTPS or local origins when
`APP_ENV=production`.

Reset and logout form submissions require a same-origin `Origin` header. Reset
deletes both the page state row and all its opens in one transaction, without
changing the page config or link.

Intended pre-send workflow: open the real link as a visitor, check the result
in the dashboard, reset the page, then hand out the QR code.

## Design

- There is no site-wide visual theme. Each page defines its own look:
  colours, typography, layout, motion and media.
- Shared code provides only a CSS reset and behaviour (loading, saving,
  errors); it imposes no styling on a page.
- Responsiveness is each page's responsibility and is checked when the page
  is built, on a phone and at a desktop width.

## Frontend requirements

- Portrait phone first; degrade gracefully to landscape and wider screens.
- Tap targets around 44 CSS px; keyboard-accessible inputs.
- No permissions requested (camera, mic, location, notifications).
- Audio starts only on a tap, with pause and mute controls.
- Small initial payload; lazy-load heavy media and optional libraries.
- Honour `prefers-reduced-motion`; fall back when WebGL or audio is missing.
- Friendly states for network failure and failed save; never show a false
  success.
- No navigation or index linking pages to each other.

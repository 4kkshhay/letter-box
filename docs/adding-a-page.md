# Adding a page

A page is a committed frontend directory with a permanent internal name and a
separate permanent public slug. Choose both before publishing: changing either
after a QR code is distributed can break the link or detach saved data.

## Scaffold

```bash
./scripts/new-page.sh example-page several-chosen-words
```

This creates `frontend/pages/example-page/` from `_template` and sets its
public path to `/several-chosen-words`. Names and slugs use lowercase words
separated by hyphens; slugs are 10–100 characters and unique.

Real pages are named `experience-<number>-<words>`, numbered in order (for
example `experience-1-not-just-a-coincidence`), and each gets a design note in
`docs/pages/experience-<number>.md`. Demo pages keep their `demo-` names.

Edit `Page.tsx`, `Page.module.css`, `index.html` and `page.json`. Keep all
page-specific media inside the page directory and import it from the page code,
so Vite emits content-hashed assets. Do not link one page from another.

## Saved fields

Fields are optional. Declare only values that should be saved and restored:

```json
{
  "slug": "several-chosen-words",
  "title": "Example page",
  "enabled": true,
  "fields": {
    "choice": { "type": "enum", "options": ["a", "b"] },
    "picks": { "type": "multi", "options": ["x", "y"] },
    "note": { "type": "string", "max_length": 500 }
  }
}
```

Render through `PageRoot`. Pages with fields use `usePageState(page)` and must
show its saving/error status. Save choices immediately, debounce typing, and
call `saveNow` on blur. Values not declared in `page.json` stay local to the
browser. Render submitted text as text, never HTML.

Admin preview mode is supplied through the same bootstrap data. Shared code
suppresses opens and saves there; page controls should remain controlled by the
hook so they cannot appear to change in the read-only preview.

## Verify locally

```bash
./scripts/test.sh
./scripts/run.sh
```

Check the public link on port 8610 and its preview on port 8611. For a page with
fields, save values, reload, verify them in the dashboard, then reset the page.
Check phone portrait/landscape, keyboard controls, reduced motion and graceful
fallbacks for any optional media or graphics.

Before merging, confirm existing page links (locally, the demo pages too) and
their saved values still work.
Shared client changes must stay backward compatible with already published
pages.

## Release

Merge the page branch to `main`. GitHub Actions publishes a private arm64 image
to GHCR. Manually dispatch deployment of its immutable digest, then test the
real HTTPS link on a phone, check it in the admin dashboard, reset its test
data, and download the final QR code. Never print a QR generated from a
temporary or local URL.

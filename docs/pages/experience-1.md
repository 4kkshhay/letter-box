# Experience 1 — Not just a coincidence

| | |
| --- | --- |
| Page name | `experience-1-not-just-a-coincidence` |
| Link | `/not-just-a-coincidence` |
| Tab title | Hello |
| Saved fields | None |
| Status | Structure and theme built; story text and photo are placeholders |

## Experience

A short story told in full-screen scenes, one at a time, in place (no page
scroll). The scenes are a greeting with the recipient's name, three story
chapters (one with a photo) and a closing scene.

Navigation follows the familiar story pattern:

- tap the right two-thirds, or swipe left: next scene;
- tap the left third, or swipe right: previous scene;
- arrow keys and screen-reader "Previous"/"Next" buttons do the same;
- a thin progress bar at the top shows position; "tap to begin" appears on
  the greeting.

A scene that is taller than the screen scrolls vertically inside itself.

## Theme

Vintage romantic: aged paper with grain and a soft vignette, sepia ink, wine
and gold accents, pressed flowers.

- Type: Pinyon Script for the name and chapter titles, Cormorant Garamond
  for text (both `@fontsource`, pinned, Latin subsets only).
- Live elements: petals drifting in the background; scene elements rise in
  one after another; script text appears as if written; the greeting's sprig
  draws its stems and opens its flower; scenes crossfade.
- Photos sit in a taped, slightly tilted keepsake frame with a script caption.
- Reduced motion: no petals; elements appear without movement.
- Always light: the page owns its look and ignores the system dark mode.

## Editing the story

All wording lives in `content.ts` as an ordered list of scenes (`greeting`,
`chapter`, `closing`); bracketed text marks placeholders. To add a photo,
put the image in the page directory, import it in `content.ts` and set it as
the chapter's `photo.src`. The greeting name comes from
`frontend/shared/recipient.json`.

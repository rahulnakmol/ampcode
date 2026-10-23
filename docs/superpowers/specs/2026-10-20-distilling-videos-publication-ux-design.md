# Distilling videos: publication UX extension (design)

Date: 2026-10-20
Status: user-approved extension of `2026-10-19-distilling-videos-design.md`; implementation authorized
on the isolated `feat/distilling-videos` worktree. No push, publishing, paid API, or Azure writes.

## Outcome

The rendered publication becomes a small offline site instead of one article page. Opening
`index.html` from `file://` still works with no server, CDN, or runtime fetch. Every page shares one
collapsible navigation, one theme system, offline search, and a Copy Page control. The renderer CLI,
package, archive, and sign-off contracts stay compatible; the only intentional contract change is
that the article PDF now prints `article.html` (the article) rather than `index.html` (the cover).

## Pages (flat at the `dist/` root so relative `assets/` paths never change)

| Page | Markdown twin | Contents |
| --- | --- | --- |
| `index.html` | `index.md` | Editorial cover: eyebrow, headline, dek, partial notice, source slate with tape maps, "Start reading", and a contents card for every other page |
| `article.html` | `article.md` | The article (previously `index.html`), method and limits, references. Printed to `article.pdf` |
| `brief.html` | `brief.md` | Research brief, unchanged separation of evidence and proposals |
| `transcripts.html` | `transcripts.md` | Per-source transcript index with coverage, gaps, uncertainty counts |
| `transcript-<video>.html` | `transcript-<video>.md` | Complete English transcript (translation or clean English, labeled), segment anchors `seg-<id>`, gaps, uncertainty, attached selected frames |
| `transcript-<video>.original.html` | `transcript-<video>.original.md` | Complete original-language transcript with `lang` set to the source language |
| `gallery.html` | `gallery.md` | Every placed figure, every sequence step, and every selected or cited frame, with provenance |
| `glossary.html` | `glossary.md` | Optional short definitions from `article.json` `glossary` |
| `references.html` | `references.md` | Original videos, every citation (video and external), visual credits, bundled software and theme credits |

Transcript Markdown twins are the verified evidence files (`sources/<v>/transcript/*.md`) with frame
links rewritten to the copied `media/` files; no transcript text is regenerated or summarized.

## Schema addition (schema_version stays 1)

Optional `glossary: [{term, definition}]`. `term` is plain text (unique, case-folded); `definition`
is inline text of at most 320 characters and may cite `[@id]`. Unknown fields are rejected and wrong
types are contract errors, exactly like the existing optional fields. Absent glossary renders an
honest empty glossary page.

## Navigation

- A left navigation on every page lists Overview, Article, Brief, Transcripts, Gallery, Glossary,
  References with `aria-current="page"`.
- Desktop (wider than 52rem): sticky sidebar; a "Hide navigation" button collapses it and a "Show
  navigation" button restores it. The collapsed state persists in guarded `localStorage`.
- Mobile: a "Menu" button opens the navigation as an overlay with a backdrop, `aria-expanded`,
  focus moved into the overlay, Tab wrapping, Escape and backdrop to close, focus restored.
- Without JavaScript, the navigation is an ordinary visible list. All navigation uses ordinary
  links; Alpine.js holds UI state only. No HTMX and no server dependency.

## Citation evidence panel

Inline citation links stay ordinary `#ref-n` links (the no-JS and modifier-click fallback). With
JavaScript, a plain click opens a local evidence panel (right side on desktop, bottom sheet on
mobile) without changing the URL or scroll position. It shows the reference label, each cited
segment's timestamp, English and original wording, uncertainty, a cited frame thumbnail, a link to
the transcript segment page anchor, the YouTube moment, and "Show in references". Escape or Close
returns focus to the citation link. Panel content comes from inert `<template>` elements rendered
from escaped evidence; nothing is fetched.

## Gallery viewer

Gallery thumbnails are ordinary links to the full image. With JavaScript they open a modal viewer
with Previous/Next, Zoom out/in, Fit, and Close buttons; keyboard (Left/Right when fitted, arrows
pan when zoomed, `+`/`-`/`0`, Escape); pointer drag to pan; horizontal swipe for previous/next;
two-finger pinch and Ctrl+wheel zoom; double-click toggles 2x. Every item shows its provenance:
untouched source capture (reel, timestamp link, frame ID, creator) or original figure (our
reconstruction, assumptions, derived-from frame). Images are never recolored or filtered by themes.

## Search and filters

`assets/search-index.js` is generated at render and loaded with a normal `<script src>` (no fetch, works
under `connect-src 'none'`). It indexes cover, article sections, brief items, every transcript
segment (English and original), gallery items, glossary terms, and references. Search opens from the
navigation, `/`, or Ctrl/Cmd+K; results are ordinary links to `page.html#anchor`, built with
`textContent` only. Local filters (transcript text and uncertain-only, gallery kind and reel,
glossary text, references kind) hide items with `hidden`; print shows everything again.

## Copy Page

Modeled on aihero.dev's "Copy page" button (clipboard icon, label swaps to "Copied", Markdown of
the whole page). Every page has Copy Page and Download Markdown in its page toolbar. The copied text
is always the full Markdown twin, embedded in a read-only `<textarea>` inside a "Page Markdown"
disclosure, regardless of filters, collapsed sections, or panels. Status is announced in a polite
live region. If the Clipboard API is unavailable or denied, `execCommand('copy')` is tried; if that
fails too, the disclosure opens with the text selected and instructions for Cmd/Ctrl+C. Download
Markdown is an ordinary `<a download>` link to the `.md` twin and works without JavaScript.

## Motion (GSAP)

GSAP 3.15.0 core is vendored under its Standard "No Charge" license with provenance. It animates
controls (panel/sheet, mobile navigation, viewer image change, search dialog, copy status) and
once-only subtle section reveals (opacity and 14 px rise, 0.45 s). Content is never hidden in
advance: a section is animated from transparent only when it is entering the viewport, so no-JS,
GSAP load failure, reduced motion (no animation at all), print (`?print=1` and `beforeprint`
finish every tween; print CSS forces opacity), hash targets (skipped), and find-in-page or search
targets remain visible. No scroll hijacking, smoothing, pinning, or ScrollTrigger.

## Themes

House light and house dark (house dark is our own), with the default following the system color
scheme. Twenty families from their original sources: Tokyo Night, GitHub, Catppuccin, Gruvbox, Nord,
Dracula, Solarized, One, Rosé Pine, Kanagawa, Everforest, Ayu, Material, Night Owl, Monokai,
SynthWave '84, Cobalt2, Palenight, Tomorrow, Zenburn. Official variants are included where they
exist (for example Catppuccin Latte/Frappé/Macchiato/Mocha, Rosé Pine/Moon/Dawn, Kanagawa
Wave/Dragon/Lotus, Ayu Light/Mirage/Dark). No unofficial light or dark variants are invented.

Each variant maps seven tokens (background, surface, text, muted text, rule, accent, warm accent)
to named palette entries. `scripts/themes.py` is the single source: it generates `assets/themes.css`
and `assets/THEMES.md` (sources, licenses, token mapping). Every text token must reach WCAG AA
(4.5:1) on both background and surface, including tinted note and target backgrounds. Where an
official color fails, the renderer mixes it toward black or white in 4 % steps until it passes and
records the adaptation; adapted variants are labeled "(adapted)" in the picker and list every
adapted token with its original value. Theme choice persists in guarded `localStorage` (failures
fall back silently to the default). Print and PDF always use house light. Source screenshots keep
their darkroom mat and are never filtered.

## Integrity and compatibility

- `render` refuses output with broken local links: every relative `href`/`src` must resolve to a
  rendered file, and every cross-page `#fragment` must exist on the target page.
- Every page's embedded Markdown must equal its `.md` twin byte for byte (checked at render and in
  tests).
- `pdf` prints `article.html?print=1`; `pdf.json` records `page` and `page_sha256` alongside the PDF
  digest; `package` treats an older `pdf.json` without them as stale. `RENDERER` becomes 2.
- `package`, the manifest shape, ZIP determinism, archive verification, and sign-off are unchanged.
  New files are ordinary `.html`, `.md`, `.js`, `.css` files inside the existing allowlist and are
  checksummed, secret-scanned, and archived like every other package file.

## Verification

Unit tests cover the schema addition, page set, Markdown twin equality, link integrity, search
index, theme contrast for every variant, GSAP/Alpine provenance, and PDF target. `make check` runs
them. The evaluation harness runs end to end on its synthetic fixtures with the index/article split.
`capture.mjs` drives Chrome Canary over DevTools (offline, dead proxy) on desktop and mobile:
navigation collapse and overlay, keyboard focus, evidence panel and sheet, gallery viewer, search,
filters, Copy Page success and both fallbacks, theme persistence and failure, no-JS, GSAP failure,
reduced motion, print emulation, and PDF. Screenshots are inspected before claiming completion.

## Out of scope

HTMX, a server, remote fonts, automatic grouping, public publishing, pushing, and any change to
evidence, archive, or sign-off semantics.

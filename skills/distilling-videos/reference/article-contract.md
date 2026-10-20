# Publication contract (schema_version 1)

The source of truth is `scripts/publication.py`. `distill.py` loads it automatically and adds three commands. Amp writes `publications/<pub-id>/article.json` plus any original figures under `publications/<pub-id>/figures/`. The scripts never interpret the videos; they validate references, render, print, and package. Evidence contracts are in `contracts.md`.

## CLI

```text
distill.py render  --workspace W --publication P
distill.py pdf     --workspace W --publication P [--browser PATH] [--timeout 120] [--wait 5]
distill.py package --workspace W --publication P [--allow-missing-pdf]
```

`P` is a publication ID from `assignment.json` `publications`: a group ID, or a video ID for an ungrouped video. Exit codes follow `contracts.md`: 0 success, 2 contract error (nothing is written), 3 no browser found, 5 browser failed or did not produce a PDF.

| Command | Reads | Writes | Status |
| --- | --- | --- | --- |
| `render` | `article.json`, `figures/`, and evidence for every video in the publication | `dist/` (replaced atomically) and `render.json` (`renderer: 2`). Deletes `pdf.json`, because a new render invalidates the old PDF. | `rendered` |
| `pdf` | `dist/article.html?print=1` (the article, not the cover) | `dist/article.pdf` and `pdf.json` (`page: "article.html"`, `page_sha256`, `pdf_sha256`, `browser`, `pages`) | `rendered` |
| `package` | `dist/`, `render.json`, `pdf.json`, and the evidence | `package/` with `manifest.json`, plus `<P>-<revision>.zip` | `packaged` |

### Render preconditions

- Every video in the publication must have complete, checksum-valid `transcript` and `transcript-markdown` stages.
- When a `frames` stage exists, it must also be valid. Changing any evidence after it is recorded blocks the render.
- `render.json` records SHA-256 digests of every input: the article, its figures, the source files, and the frames used. It also records digests of every `dist/` output.

### PDF behavior

- `pdf` refuses to run until the current render has been verified.
- It looks for a browser in this order: `--browser`, then `DISTILL_BROWSER`, then `chromium`, `google-chrome`, `microsoft-edge`, or `brave-browser` on `PATH`, then the standard macOS app locations.
- The browser runs headless with a temporary profile, and its environment is stripped of credential-like variables. It uses a dead proxy (`127.0.0.1:9`), so network fetches fail.
- The output is accepted only when it starts with `%PDF-`, ends with `%%EOF`, and is at least 1 KB. If no browser is found, the command exits 3. No HTML file is ever renamed to `.pdf`.

### Package checks

`package` re-verifies `render.json` input and output checksums and fails if the render is stale. It then checks the PDF:

- The PDF must match the current `article.html` (`pdf.json` `page` and `page_sha256`). A `pdf.json` written by renderer 1 (which printed `index.html` and recorded `index_sha256`) counts as stale. Otherwise packaging fails, unless you pass `--allow-missing-pdf`. That flag produces `complete: false`, and the packaged pages drop their link to `article.pdf` (the only one, in the article footer) so a draft never links a missing file. Every package page's local links are rechecked with no exceptions.
- A `partial` article also produces `complete: false`.

## `article.json`

Unknown fields are rejected at every level. Text fields must not be empty. Optional fields are type-checked when present: `partial_reason`, `audience`, `brief.question`, proposal `risks`, quote `cite`, citation `frame_id`, `note`, `publisher`, and `accessed` are non-empty strings; `segment_ids`, figure `sources`, evidence `citations`, and proposal `basis` are lists of non-empty strings; list `ordered` is a boolean. A wrong type is a contract error (exit 2), never a traceback. Unpaired surrogate escapes (such as `\ud800`) anywhere in `article.json` are a contract error.

```json
{
  "schema_version": 1,
  "publication_id": "g1",
  "status": "complete",
  "partial_reason": "required when status is partial",
  "audience": "optional",
  "title": "plain text",
  "dek": "inline text",
  "sections": [{"id": "hook", "heading": "inline text", "blocks": []}],
  "figures": [],
  "citations": [],
  "brief": {"question": "optional", "evidence": [], "proposals": []},
  "limitations": ["inline text"],
  "glossary": [{"term": "plain text", "definition": "optional; inline text, at most 320 characters"}]
}
```

`glossary` is optional. Terms are plain text and unique (case-insensitive); definitions are short inline text (at most 320 characters, citations allowed and validated). Without it, the glossary page says that no terms were defined.

### Inline text

All text is escaped. The only markup recognized is:

- `[@c1]` or `[@c1; @c2]` for citations.
- `**strong**`, `*em*`, and `` `code` ``.

Raw HTML, links, and headings in text render as literal characters. Whitespace before a citation marker is removed.

### Blocks

| `type` | Fields | Rules |
| --- | --- | --- |
| `p` | `text` | |
| `list` | `items`, optional `ordered` | |
| `quote` | `text`, `cite` | The cited source must be a video citation with `segment_ids`. The quote must appear verbatim (case and whitespace folded) in those segments' `text` or `english`. |
| `figure` | `figure` | Places a figure by ID. |
| `details` | `summary`, `blocks` | Nested blocks may only be `p` or `list`. Renders as native `<details>` and is expanded for print and PDF. |

### Figures

Every figure needs a safe `id` and a `caption`. Alt text is per image: `capture` and `original` figures take one figure-level `alt`; a `sequence` has no figure-level `alt` (it is rejected as an unknown field), and every step carries its own `alt`.

- `capture` takes `video_id`, `frame_id`, and `alt`. It is an untouched source frame from `frames.json`.
- `sequence` takes `video_id` and `steps: [{frame_id, alt, caption}]`, with at least two steps. It renders as a demo step-through (Previous / Next, arrow keys, and a filmstrip). Without JavaScript, and in print, every step is visible.
- `original` takes `image`, `alt`, `assumptions` (non-empty), `sources` (citation IDs, non-empty), and optional `derived_from: {video_id, frame_id}`. The image must be a `.png`, `.jpg`, `.jpeg`, `.webp`, or `.svg` file under the publication's `figures/` directory. SVGs that contain scripts, event handlers, `foreignObject`, `javascript:`, or remote references are rejected. Annotated derivatives name their original in `derived_from`, and the untouched frame is packaged with the evidence.

All frame references must exist in that video's `frames.json`, and the video must belong to this publication. Captures and sequence frames are copied to `dist/media/<video>/<frame>.jpg`, with thumbnails in `dist/media/<video>/thumbs/`.

### Citations

There are two kinds:

- Video citations: `{id, video_id, segment_ids?, frame_id?, note?}`, with at least one of `segment_ids` or `frame_id`. Every segment and frame must exist. Timestamps are derived from the evidence, never typed by hand: links use `https://www.youtube.com/watch?v=<id>&t=<start>s`.
- Web citations: `{id, kind: "web", url, title, publisher?, accessed?, note?}`. The URL must be `http(s)` with a host and no credentials.

Additional rules:

- Every citation ID used anywhere must be defined. This is checked before rendering in every inline field: `dek`, section `heading`, `p` text, `list` items, `details` `summary`, figure `caption`, sequence step `caption`, original-figure `assumptions`, `limitations`, `brief.question`, evidence `text`, and glossary `definition`. An empty marker (`[@]`) is an error too.
- Every video in the publication must be cited at least once, so a synthesis cannot silently drop a group member. A citation of a video outside the publication is an error.
- Unused citations and unplaced figures produce warnings.
- Numbering follows first use in reading order within each document, and the HTML page, its Markdown twin, and its references list share one order. Article: dek, then each section (heading, then blocks; a figure counts caption, steps, sources, assumptions), then limitations. Brief: dek, question, evidence (Findings, Requirements, Open unknowns), limitations. Cover: dek. Gallery and glossary: captions and definitions in page order. A dek-only citation is therefore reference 1, with a working `#ref-1` anchor.
- In the HTML, each passage has a left rail of timecode chips that link to the cited moment. Each chip has the form `<n> <reel> <H:MM:SS>`.
- Reels are lettered A, B, and so on, in the publication's `video_ids` order.

### Brief

The brief must contain both `evidence` and `proposals`, even if `proposals` is empty.

- `evidence[]` items have `{id, kind, basis, text, citations?}`:
  - `kind` is `finding`, `requirement`, or `unknown`.
  - `basis` is `presenter` (a claim the speaker makes), `screen` (an observation of the video), or `external` (an outside source).
  - `finding` and `requirement` items need citations.
- `proposals[]` items have `{id, kind, text, basis, risks?}`:
  - `kind` is `architecture`, `implementation`, or `investigation`.
  - `basis` lists the evidence IDs the proposal rests on.
  - Proposals must not cite sources directly (`[@...]`), and unknown evidence IDs are errors.
- The brief renders as "What the sources establish" (Findings, Requirements, Open unknowns), followed by "What we propose". Each proposal is labeled "Proposal, not evidence" and lists what it rests on.

## Outputs (`dist/`)

| File | Contents |
| --- | --- |
| `index.html` | Cover: headline, dek, partial notice, source slate with tape maps, "Start reading", and a card for every page |
| `article.html` | The article: masthead, source slate, sections, method and limits, references. Printed to `article.pdf` |
| `brief.html` | The research brief |
| `transcripts.html` | Transcript index: per-source coverage, gaps, uncertainty, links |
| `transcript-<video>.html`, `transcript-<video>.original.html` | Complete English (labeled translation or clean English) and original-language transcripts; anchors `seg-<id>`, gaps, uncertainty, attached selected frames; filterable |
| `gallery.html` | Every placed figure, sequence step, and selected or cited frame, with provenance; viewer with zoom, pan, fit, previous/next by buttons, keyboard, pointer, and touch |
| `glossary.html` | Optional short definitions |
| `references.html` | Original videos, video citations (`cite-<id>`), external sources, visual credits, bundled software and theme credits |
| `*.md` | One Markdown twin per page (`index.md`, `article.md`, `brief.md`, `transcripts.md`, `transcript-<video>[.original].md`, `gallery.md`, `glossary.md`, `references.md`). Escaped text, `[^n]` footnotes, timestamped URLs. Transcript twins are the verified evidence Markdown with frame links pointed at `media/` |
| `coverage.json` | Per-source transcript coverage, gaps, uncertain segments, and frame counts (with `semantic_completeness: false`); citation, figure, and brief counts; limitations and warnings |
| `assets/` | `article.css`, `article.js`, `theme-init.js`, generated `themes.css`, `THEMES.md` (theme sources, licenses, contrast adaptations), and `search-index.js`; `vendor/alpine-3.17.4.min.js` (MIT), `vendor/gsap-3.15.0.min.js` (Standard "No Charge" GSAP License), their license files, and `PROVENANCE.md` |
| `media/`, `figures/` | Copied images: placed, selected, and cited frames (full and thumbnail), and original figures |
| `article.pdf` | Written by `pdf` |

The tape map draws ticks at cited moments and hatching over transcript gaps. It has a text equivalent, so the meaning is not carried by color alone.

### Offline safety

- Pages load only relative `assets/` files and run under the CSP `default-src 'none'; script-src 'self' 'unsafe-eval'; style-src 'self'; img-src 'self' data:; connect-src 'none'; ...`. `unsafe-eval` is required by Alpine's expression evaluator.
- `render` refuses output that references a remote script, style, image, or frame.
- Links to YouTube and web references are ordinary navigation links with `rel="noopener noreferrer"`.
- `render` refuses output with a broken local link: every relative `href`/`src` in a page, and every `](target)` link in a Markdown twin, must resolve to a rendered file (except `article.pdf`, written later by `pdf`), and every cross-page `#fragment` must exist on its target page. Links that leave the package (`../`, absolute paths, other schemes) are errors.
- Search uses `assets/search-index.js`, loaded with `<script src>`; nothing is fetched. HTML-significant characters in the index are `\u` escaped.
- Every page embeds its full Markdown twin in a read-only `<textarea>` ("Page Markdown"). Twins are normalized to the form a browser keeps in a textarea (LF line endings; NUL and other C0 controls except tab replaced by U+FFFD), and the textarea content starts with one newline that HTML parsing drops, so the downloaded `.md`, the textarea value, and the copied text are identical; `render` refuses a page whose embedded text would differ. Copy Page copies exactly that text whatever is filtered or open; it falls back to `execCommand('copy')`, then to selecting the text for manual copying. Download Markdown is an ordinary `<a download>` link to the twin.
- Inline citation links stay `#ref-n` links. With JavaScript, a plain click opens the evidence panel (desktop) or sheet (mobile) from an inert `<template>` without navigating; modifier clicks and no-JS readers follow the link.
- Progressive enhancement: `article.js` registers the Alpine components and only then loads the bundled Alpine, so Alpine never runs without them. The page shell marks `<html class="ready">` once it can show the navigation again; until then (or forever, if a script fails) every Alpine-only control (`.js-only`) stays hidden, the mobile menu is not moved off-canvas, and a saved navigation collapse is not honored: `theme-init.js` applies it before paint and removes it at `load` unless the page is ready. Links, Download Markdown, all demo steps, and the references stay usable. A link or search result to an item hidden by a local filter clears that filter and opens enclosing `details`, on the same page too.
- Navigation, theme, search, filters, panel, viewer, and copy state live in Alpine components; only the theme and the desktop navigation collapse are stored, in `localStorage`, guarded so blocked storage falls back to defaults. GSAP is optional decoration: once-only section reveals start only as content enters the viewport and never from hidden; with reduced motion, print, or GSAP missing, nothing animates. Tweens touch only the properties they animate, so zooming the gallery viewer during its opacity-only entrance keeps the zoom.
- `article.js` adds static print equivalents: `?print=1` and `beforeprint` open every `details` element, and print CSS shows every sequence step as a contact sheet.

## Package (`package/` and ZIP)

The package contains:

- All of `dist/`, plus `article.json`.
- For each source video in the publication, under `sources/<video>/`: `source.json`, `selection.json`, `frames/frames.json`, `transcript/{input.json, segments.json, coverage.json, original.md, english.md}`, and the full-size images and thumbnails of selected or referenced frames.

The package never contains `media/` or `audio/` (raw source media), other videos, hidden partial directories, or any file outside the extension allowlist (`.html .md .json .css .js .pdf .png .jpg .jpeg .webp .svg`). Packaging fails if any text file contains secret-like content: a SAS `sig=`, `AccountKey=`, `SharedAccessSignature=`, a private key block, or a GitHub, AWS, OpenAI, or Slack token pattern.

The manifest has this shape:

```json
{"schema_version": 1, "publication_id": "g1", "kind": "group", "video_ids": ["v1", "v2"],
 "revision": "16 hex chars of sha256(canonical files list)", "status": "complete",
 "complete": true, "incomplete_reasons": [], "pdf": true,
 "excluded": "original media, audio, partial stage output, and credentials are never packaged",
 "files": [{"path": "index.html", "sha256": "...", "bytes": 1234}]}
```

- The manifest contains no timestamps.
- The ZIP is deterministic: entries are sorted, with fixed 1980 timestamps and mode 0644. Repackaging unchanged inputs produces the same ZIP digest.
- The ZIP is written to `publications/<P>/<P>-<revision>.zip`. It contains `manifest.json` and exactly the listed files, all with relative paths.
- Command output includes `manifest_sha256` and `zip_sha256` for archive verification (Task 3).

## Known limits

- The quote check guards against invented wording, but it cannot judge whether a paraphrase is fair.
- Coverage numbers describe the transcript and the frame sampling. They do not show that the content was understood.
- PDF output depends on a locally installed Chromium-family browser. Tests use a fake browser, and a real-browser render is a manual or integration check.
- The publication uses system font stacks rather than bundled fonts, so typography varies slightly across operating systems.
- Theme palettes are mapped to seven tokens; they recolor text, rules, and backgrounds only. Many official muted or accent colors fail WCAG AA on a reading page and are adapted (labeled in the picker and listed in `THEMES.md`). Print and PDF always use house light.
- Search is substring matching over the bundled index (no stemming or ranking model). Very long publications produce a larger `search-index.js` and larger pages, because every page carries its Markdown twin.

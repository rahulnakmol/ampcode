# Social surfaces (`social`)

Social content is UX in someone else's interface: a feed you do not control, read in a second,
often with the sound off, cropped by overlays, and judged against everything else in the scroll.
Platform specifications change often: confirm current sizes, safe zones, and limits by research
before producing assets.

## Formats

Typical formats to plan for (verify current values):

| Format | Typical aspect ratio | Notes |
| --- | --- | --- |
| Feed image or carousel | 4:5 (1080×1350) or 1:1 | 4:5 takes the most vertical space in most feeds |
| Stories, Reels, TikTok, Shorts | 9:16 (1080×1920) | Platform UI covers the top and bottom bands and the right edge |
| Link preview (Open Graph, X cards) | 1.91:1 (1200×630) | Generated from page metadata; design it like a poster |
| Video thumbnail (YouTube) | 16:9 (1280×720) | Readable at very small sizes |
| LinkedIn document carousel | PDF, 4:5 or 1:1 pages | Each page must stand alone |
| Profile and cover images | Platform-specific; circular crops | Check the crop on every platform you use |

## Craft

- **The first second decides.** A clear hook in the first frame or the first line: the outcome, the
  question, or the surprising fact. No logo intros.
- **One idea per post or slide.** Carousels are a story: a hook slide, one point per slide, and a
  closing slide with the takeaway or action.
- **Type for thumbs.** Large, high-contrast text, few words, and a consistent template so the
  account is recognizable in the feed without reading the name.
- **Safe zones.** Keep text and faces out of areas covered by platform UI (captions, buttons,
  profile rows) and away from crop edges. Check each placement with the platform's overlay.
- **Sound off by default.** Captions burned in for short video (styled for readability, with
  enough contrast), plus platform captions where offered.
- **Native over repurposed.** Adapt each asset to the platform's culture and format rather than
  posting the same file everywhere.
- **Link previews are designed, not accidental.** Every shareable page sets title, description, and
  image metadata, and the image works at thumbnail size.
- **Brand system.** Templates, type, color, and motion rules for social live in `DESIGN.md` so
  every asset and every agent producing assets stays consistent.

## Accessibility and agents

- Alt text on every image (most platforms have a field), describing the point, not just the picture.
- Text in images repeated in the caption; hashtags in CamelCase so screen readers pronounce them;
  emoji used sparingly and not mid-sentence.
- No flashing above three flashes per second; captions and, for informative video, audio
  description or a described transcript.
- Agents and crawlers read metadata and captions: the caption must carry the claim, the source, and
  the link, not only the image.

## Mockup and verification

Render every asset at its real pixel size, then inspect: each format the brief needs, the image
inside a feed mockup next to typical neighbors, with the platform's safe-zone overlay, at thumbnail
size, and the link preview through a preview debugger or a local render of the metadata. Record alt
text (`"alt"` on each state, which `check` requires) and post copy for every asset you produce,
including the square, the story, and the link preview, in `touchpoints.json`.

Run the typesetting check (widows, orphans, wraps, collisions, one date format) on every derived
asset (square, story, link preview), not only the primary. Any image likely to be forwarded on its
own (the square, the story, the cover) shows the action and the deadline in the artwork; before
claiming an image "carries every fact", compare its visible text with the fact list. After any copy change, search every source and rendered mockup (feed, grid, in-context renders,
captions) for the old wording and re-render whatever still carries it.

## Social slop

- Text walls on images; tiny type; logos as the hook; stock-photo smiles; generic gradient quote
  cards.
- The same 16:9 asset cropped badly into every format; captions covered by platform UI.
- Engagement bait ("comment YES"), fake urgency, and hashtags stuffed in the copy.

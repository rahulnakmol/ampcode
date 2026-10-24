# Media surfaces: presentations, video, documents, and data visualization

These are touchpoints people read or watch rather than operate: the pitch deck, the product video,
the onboarding guide, the report, the chart in a dashboard. They follow the same rules of hierarchy,
states, and accessibility.

## Presentations (`presentation`)

Craft:

- One idea per slide, stated as a sentence headline ("Checkout time fell 40% after the redesign"),
  with the evidence below it. The deck's headlines alone should tell the story.
- Type sized for the room: titles around 36 pt and nothing under about 24 pt for projected text;
  high contrast that survives a washed-out projector.
- Consistent grid and template; charts redrawn to the deck's style, not pasted screenshots.
- Speaker notes carry the detail; the handout version (exported PDF) is readable without the speaker.
- Accessible: slide titles set, reading order checked, alt text on images, captions on video.

Mockup and verification: render every slide, view it at the size of a laptop screen across a room
(for example at 25% scale), view a low-contrast "projector" version, and export the handout PDF.

## Video and motion graphics (`video`)

Craft:

- Hook in the first two seconds; structure (problem, turn, payoff) before polish.
- Typography on screen held long enough to read twice; kinetic type that follows the voice.
- Safe areas for titles and action, and separate cuts for vertical and horizontal delivery.
- Captions as a design element (readable, never covering faces or key UI); audio description or a
  described transcript for informative content.
- Loudness normalized for the delivery platform; music that never fights the voice.
- No more than three flashes per second; no rapid full-screen color alternation.
- Thumbnails and first frames designed as posters.
- Product UI in videos is real or faithfully rebuilt, with cursor motion that is slow and deliberate.

Mockup and verification: a storyboard frame strip with timings, the captions file, key frames at
full resolution in each aspect ratio, a sound-off review, and the thumbnail at small size.

## Documents and reports (`document`)

Craft:

- Structure is navigation: real headings, a contents page for anything long, numbered sections,
  and summaries before detail.
- Readable typography for the medium: comfortable measure, generous leading, and tables designed
  with clear headers and alignment (numbers right-aligned with tabular figures).
- Accessible output: tagged PDF (PDF/UA where possible) with reading order, alt text, table headers,
  document title, and language set; or HTML as the primary format with PDF as a print export.
- Both screen and print: check page breaks, widows, and orphans, and that links make sense printed.

Mockup and verification: render representative pages (cover, contents, a dense table, a figure),
the print version, and run an accessibility check on the PDF (Acrobat or a PDF/UA checker when
available).

## Data visualization (`dataviz`)

Applies to charts in any surface: dashboards, reports, slides, social, and print.

Craft:

- Start from the question the chart answers; choose the form from it (comparison: bars; change over
  time: lines; part to whole: stacked bars or a single proportion; distribution: histograms or dot
  plots; relationship: scatter).
- Label directly instead of legends, annotate the insight, start bar axes at zero, avoid dual axes
  and 3D, and show uncertainty where it exists.
- Color carries data, not decoration: a sequential or diverging scale for values, a small
  categorical palette that is color-blind safe, and gray for context.
- Dense data: aggregate, allow focus and drill-down, and render with canvas or WebGL beyond a few
  thousand marks (see `motion.md` on complex rendering).
- Accessible and agent-readable: a text summary of the takeaway, an accessible data table or
  download, and keyboard focus on data points in interactive charts.

Mockup and verification: render the chart with real data at its real size, an empty and loading
state, a dense or outlier-heavy dataset, a color-blindness simulation, and the table alternative.

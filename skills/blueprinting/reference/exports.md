# Editable files from one reviewed packet

Use [publication.md](publication.md) first. Export is a local operation, not a sending step or
client acceptance. Keep source permissions and the review current; do not export from a saved
`ready` response after later evidence has changed.

## Prepare the story, not just the file

Use SCQA when the audience needs a reframing: situation, complication, question, answer.
Use recommendation-first when the problem is agreed, options and trade-offs for contested choices,
and a process walkthrough for changes in responsibilities. The headline sequence should make
a coherent argument on its own. Each claim needs evidence, relevant uncertainty and a consequence
for the people doing the work. End with the actual decision, authority and next action.

Do not force every workshop into an executive deck. A questionnaire needs room for answers;
a functional specification needs rules and exceptions; a kickoff pack needs owners and readiness;
a proposal needs scope, assumptions and commercial limits. A projected deck needs fewer words
than a leave-behind. Use separate reviewed packets when content density differs, retaining common
facts and caveats. Private motive hypotheses never belong in speaker notes.

The generic export layout uses Liberation Sans, navy text, a teal rule, sentence headlines and
native tables/charts. It is an initial composition, not a consultancy template, a branded-client
template system or a claim of consulting quality. Original client branding and tailored visual
storytelling still require design and review. The final owner deck assessment remains mandatory.

## Run a bounded local export

Use Python 3.11 or newer. Markdown needs the standard library. Word and PowerPoint need the
pinned packages in `scripts/export-requirements.txt`, installed into an isolated environment.
Slides also need Fontconfig and Liberation Sans. PDFs need the pinned local LibreOffice 7.4.7.2
renderer. Qualify a different version before changing the pin; do not disable security updates
to preserve a renderer version. A version pin is not a security certification.

Run `python3 scripts/engagement.py --root <engagement-directory> export <packet-id> <review-id>
--format <format> --output <new-file>` as one command. Formats: `md`, `docx`, `pptx`, `pdf-document`,
`pdf-deck`. Use a matching extension, an existing parent directory and a new file path. Existing
files, including human-edited exports, are never replaced. Stage files in private local storage,
not a cloud-synced folder whose upload would bypass the separate sharing review.

The command rechecks publication readiness, then gives only selected content to the renderer.
It returns output/packet hashes and `exported-not-delivered`. It does not follow source links or
read raw evidence. Interrupted or failed exports require checking the exact output path before
retrying; a file already present is not permission to overwrite or evidence of delivery.

Word uses native headings and tables; chart values appear as an editable table with units.
PowerPoint uses native titles, text, tables, bar-chart objects and speaker notes with chart data.
Markdown retains the same text, caveats, source labels, tables and notes. PDFs are local rendered
views: `pdf-document` includes the written notes; `pdf-deck` is slides-only and does not include
speaker notes. Keep decision-critical content and caveats on the slide itself, never only in notes.
No slide is a flattened screenshot. Dense slide content is rejected rather than silently
shortened or shrunk. Revise the composition and re-review the packet; do not remove exceptions
or caveats to make a slide fit. Font measurements reduce overflow risk but do not replace rendering.
Unsupported control characters, including tabs and PowerPoint soft breaks, are rejected; use
explicit newlines and re-review. Numeric labels that cannot fit require a reviewed split or change
of units, not automatic rounding. PDF export requests tagging; that alone does not prove PDF/UA.

## Inspect the actual handoff

Open and edit the actual Word and PowerPoint output. Save and reopen it; verify changed text,
table cells, chart data and notes. Render all pages/slides and inspect the headline sequence,
reading order, table continuation, contrast, chart units/zero baseline, shortfall or uncertainty,
long names, source labels and material caveats. Check the PDF text as well as the image.
Readable exports do not prove accessible PDF conformance or Microsoft Office desktop behavior.

Keep Word/Markdown detail and deck statements consistent. A useful chart has a readable data
alternative; a data label is not a substitute for a required uncertainty range. Do not use the
basic bar renderer for a chart whose meaning needs unsupported error bars or another chart type.
Retain output hashes and named inspections. Owner judgment of the complete transformation deck
is separate from library round-trip tests on a small synthetic fixture.

Google Slides requires a separately authorized destination and new-file import, followed by real
edits, saved readback and rendering comparison. Do not rename a PPTX or link a PDF and call it native
Slides. Do not overwrite an existing cloud file as an import shortcut. This local exporter does not
implement or qualify that cloud path; unavailable access remains a blocker, not a waived deliverable.

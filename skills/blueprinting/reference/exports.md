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

The neutral export layout uses Liberation Sans, navy text, a teal rule, sentence headlines and
native tables/charts. Schema 3 also supports reviewed theme-only brand composition, described
below. This is not a mandatory-template or logo system, arbitrary brand-skill compatibility, or a
claim of consulting quality. Tailored visual storytelling and the final owner deck assessment
remain mandatory.

## Bind a selected brand without changing business evidence

Schema 3 retains schema 2 blocks and adds required `presentation` with exactly `schema: 1`,
`brand`, `theme`, `issuer` and `classification`. `brand` is null for neutral or an exact
`{id, revision}` artifact reference. `theme` contains `font`, `ink`, `accent`, `muted`: a literal
installed family and uppercase six-digit RGB colors. Neutral uses exactly Liberation Sans,
12263A, 086C75 and 465766 respectively. Issuer and classification are nonempty, at most 120
characters each; native layout limits can require shorter text. Neutral is an explicit choice,
never a fallback for an unresolved selected brand. Markdown preserves identity, not typography.

Load the engagement-selected branding skill from its actual resolved base. Translate its rules
into a retained artifact with `data.purpose: brand-configuration` and `data.brand` containing
exactly `schema: 1`, `identity`, `variant`, `resolved_base` (absolute), `skill` (exact registered
source reference), `theme`, `issuer`, `classification`, `classification_authority`, `composition`,
`override`, `unresolved`. Record the skill content as a registered input file. Include every exact
reference in the containing record's input edges. The profile and skill source need declared
publication permissions for the packet recipient/destination. Neither private paths nor source
content are copied into outputs.

This mapping supports only `composition: theme-only`, with an empty `unresolved` list. Describe
any owner-authorized fixed-template override in `override`, or why none is required. These are
reported judgments, not authenticated legal/brand approval. Required logos, imagery, templates
and other assets are not implemented by this mapping: resolve an authorized theme-only treatment
or block affected output. Do not mark an unresolved mandatory asset satisfied, execute embedded
code, silently install a skill, or redistribute its library. Voice/tone and legal interpretation
remain reviewer responsibilities; a palette match is not brand compliance.

The packet presentation must match the profile exactly and publication review adds the `brand`
assessment. Inherited restrictions and input observation still apply. Brand revisions stale
dependent outputs and reviews, not independent business decisions. Selected fonts must resolve
locally without fallback; missing character coverage in either regular or bold blocks native
output with an authorized-substitution/review instruction. Markdown remains portable. Qualification
currently covers English samples with Liberation Sans/Serif, not arbitrary languages/font shaping.
Native staging fingerprints regular/bold font files as well as exporter code and dependencies;
a font change requires fresh staging and inspection. White-paper contrast
checks are a minimum, not a complete accessibility assessment. Inspect actual typography, footer
fit, charts and semantic colors in each selected format, then edit/save/reopen disposable copies.
Current qualification uses LibreOffice, not Microsoft desktop certification.

## Run a bounded local export

Use Python 3.11 or newer. Markdown needs the standard library. Word, Excel and PowerPoint need the
pinned packages in `scripts/export-requirements.txt`, installed into an isolated environment.
Native files need Fontconfig and the selected font (Liberation Sans for neutral). PDFs need the pinned local LibreOffice 7.4.7.2
renderer. Qualify a different version before changing the pin; do not disable security updates
to preserve a renderer version. A version pin is not a security certification.

Run `python3 scripts/engagement.py --root <engagement-directory> export <packet-id> <review-id>
--format <format> --output <new-file>` as one command. Formats: `md`, `docx`, `pptx`, `xlsx`, `pdf-document`,
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

## Use workbooks for supporting analysis

XLSX preserves selected registers as native filterable tables with frozen headers, literal
text, source labels and caveats. Selected charts have an editable native bar chart and a visible
numeric table. No raw evidence is fetched, no sheet is hidden and no macros or external links
are generated. Use reviewed stable IDs in registers; the renderer never invents missing owners
or turns a gap into zero. Register layouts support at most 10 columns and 10,000 rows, with
unique case-insensitive headers of at most 255 characters. Charts support at most 20 categories
and three series. Text that cannot fit a readable row is refused; split and re-review rather
than shrink, truncate or remove qualifications. Font measurements still require render inspection.
Print layouts keep 100% scale: narrow sheets use landscape A4; wider estimates/registers use
landscape A3. Chart pages follow their data table instead of splitting the chart across pages.
The repeated title and chart must fit the printable height together; excessive combined height
is refused with a split/review instruction. At dense category counts, the chart application may
display alternate axis labels; the accompanying table retains every category and value.
Use the declared paper size or a separately reviewed narrower packet, not fit-to-one-page printing
that makes the text unreadable. Required print assets still need inspection in the target application.

Schema-2 estimates retain labelled quantity, low/high effort, rate and contingency inputs,
calculated low/high totals, and a separate visible assumptions/activity-basis sheet. Numeric
bounds and decimal half-up conventions are in [publication.md](publication.md). Native generated
formulas use base-1,000,000 integer pieces on visible Calculation sheets, avoiding floating-point
SUM/ROUND disagreements at decimal ties. Those audit grids are screen-readable; only their
explanation is in the print area. Person-days and money retain six and two displayed decimals.

Recalculate in the spreadsheet application. Initial caches are for display, not proof of correct
recalculation. Invalid pasted numeric edits withhold totals, name the affected row/contingency or
output bound, and recover after correction. Precision checks compare scaled binary pieces against
six-place-rounded inputs; approximate equality and numeric-to-text conversion are not sufficient.
The status always calls the workbook an unreviewed
scenario; numeric validity is not commercial approval. Edit labelled inputs, not formulas or
activity identity. Formula tampering, spreadsheet-engine precision loss before validation, and
hostile files imported after export are outside this authoring boundary. No workbook protection
is claimed as security. Editing a file never changes the engagement baseline or authorizes
republication: reconcile intended changes into a newly reviewed packet and render a new candidate.

Verify actual edits, recalculation, save/reopen, both sides of rounding/limit boundaries and
invalid-state recovery. Compare the displayed results exactly with the authoritative Decimal
model, not just cached values; unrounded tolerance cannot excuse a different displayed amount.
LibreOffice qualification is not Microsoft Excel desktop certification. Do not label formula
presence, successful ZIP creation or a reported inspection as an application-level test.

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

Google Slides/Docs are deferred under the accepted Office-file scope. These local exports do not
implement or qualify either cloud path; no conversion, activation or write is authorized implicitly.

## Package the inspected bytes, without regenerating them

Select only needed files, not a vault or a directory glob. Retain an artifact with
`data.purpose: export-selection` and `data.selection` containing exactly `schema: 1`, `audience`,
`destination` and nonempty `files`. Each file contains exactly `name`, `format`, `packet`, `review`;
the last two are exact `{id, revision}` references to current packet and publication-review records.
Include those references in the artifact's input edges. All packets must share the selected audience
and destination. Formats and bounded theme-only composition are described above.
Use portable leaf names such as `01-decision-brief.docx`: no paths, reserved device names, duplicates,
case collisions or mismatched extensions. Do not add private metadata to these selections.

Retain a review with purpose `package-selection`, status `approved`, named `reviewer`, timestamp
`at`, exact `selection` reference, `selection_hash` (canonical selection digest), and assessments
`consistency`, `confidentiality`, `selection`, each `passed`. Bind its input edge to the selection.
This is a reported review of facts, figures, caveats, exclusions and open decisions across files,
not an automated semantic check or client acceptance.

Run `engagement.py --root <root> package-stage <selection-id> <review-id> <candidate-id>` from the
bound scripts directory. It renders a private `.blueprinting/exports/<candidate-id>` candidate and
returns exact file hashes and a manifest hash. Local metadata also retains exporter implementation
hashes, installed library versions and each file's PDF renderer identity. It creates no ZIP yet.
`package-status [candidate-id]` lists all candidates or one candidate. Resume also surfaces them.
`awaiting-inspection` describes staged output only; it is not current publication approval or a
delivery receipt. Recheck publication at the final packaging step.

Inspect those exact staged files. Open/edit/save/reopen disposable copies to check editability;
do not modify or regenerate the originals after inspection. Retain a review with purpose
`package-inspection`, status `approved`, named `reviewer`, `at` after staging, `candidate`,
`manifest_hash`, and the exact returned `files` list. Assessments `rendering`, `editability`,
`consistency`, `brand` must each be `passed`; for neutral outputs explicitly assess the neutral
layout rather than invent brand compliance. Its input edges bind both selection and selection review.
Any required check that cannot pass blocks this review. A recorded assertion does not prove that
someone opened or inspected a file.

Run `engagement.py --root <root> package <candidate-id> <inspection-id> --output <new-absolute.zip>`.
It rechecks current publication, pending operations, input observations, selection, inspection and
exporter identity, reads and hashes the actual file buffers, and archives those same bytes. Only
selected files and `manifest.json` enter the ZIP; the client manifest contains filename, format,
packet revision and actual SHA-256, never raw evidence, local paths or renderer metadata. Unselected
files beside a candidate are not included. Verify extraction and checksums before sharing.

Interrupted staging remains `incomplete` and cannot be packaged. Preserve it for inspection,
resolve the cause, then stage a new ID; existing candidates and ZIPs are never overwritten.
Changed files or dependencies require a newly rendered and inspected candidate, not an assertion
that the old files are still approved. After an interrupted final creation, inspect whether the
requested ZIP already exists before retrying; it may have been created before the response failed.
Packaging reports `exported-not-delivered`, without sending, encryption, access control or client
acceptance. This is a point-in-time, single-writer check with quiescent files, not a hostile-shell
or concurrent-editor security boundary. Keep candidates and ZIPs in permitted private storage.

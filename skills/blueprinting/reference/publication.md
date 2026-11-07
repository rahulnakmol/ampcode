# A reviewed packet is not permission to share everything

Use this reference before preparing client-facing content or a Notion handoff. It describes
local checks, not a sending service. Keep full internal notes in the engagement repo.

## Select and review the exact content

Create an `artifact` record with `data.packet`. Schema 1 packets contain exactly `schema`, `title`,
`snapshot`, `audience`, `destination` and `blocks`. The snapshot identifies the source versions
used, before saving the packet. Audience and destination are explicit agreed names, not inferred
from a file extension. New content or a different destination requires a new review.

Schema 3 adds the required neutral-or-selected `presentation` configuration described in
[exports.md](exports.md), with exact brand/source dependencies and a separate brand assessment.
Its blocks retain the schema-2 typed-estimate support below.

Each block has `id`, `kind`, `title`, `text`, `notes`, `caveats` and `citations`. `notes` is an
explicit string, empty if none; it is publishable speaker guidance, never private reflection.
`caveats` is a list of required qualifications. Citations contain an exact `record` reference,
a recipient-safe `label`, and `treatment` of `citation` or `excerpt`. All exact references also
belong in the retained artifact's `inputs` edges. Do not bury material source restrictions in prose.

Supported content shapes:

- `text`: a headline and explanatory text.
- `table`: also `columns` and rectangular `rows`, with text cells.
- `chart`: also `categories`, `series` (each with `name` and numeric `values`) and `unit`.

Schema 2 keeps those fields and additionally permits `estimate` blocks with a `model`. The
model is the supplied schema-1 estimate input described in [proposals.md](proposals.md), with
exact fields `schema`, `currency`, `rate_date`, `assumptions`, `basis`, `contingency_percent`,
`activities`. Each activity has exactly `id`, `activity`, `role`, `basis`, `quantity`,
`days_per_unit_low`, `days_per_unit_high`, `day_rate`, `after`, and optional matching `currency`.
No arbitrary formulas, attachments or additional metadata are accepted.

This Office-facing model supports 1–1,000 activities, nonnegative numeric inputs at most
1,000,000 with at most six decimal places excluding trailing zeros, and calculated magnitudes
at most 1,000,000,000. Existing positive quantity/rate/high-effort, ordered low/high, valid
predecessor and 0–100% contingency rules still apply. Unsupported inputs/results fail explicitly.
The standalone calculator's range is unchanged. Narrative exports retain unrounded calculation
precision until final decimal half-up rounding: six places for person-days, two for monetary
values. These are estimate conventions, not currency-minor-unit or invoicing rules.

Typed estimate narrative output includes the range table, rate date and contingency, plus
activity assumptions, roles, bases and predecessor details in speaker notes. Accordingly, every
estimate block requires `notes` permission even when its supplied `notes` string is empty.
Keep decision-critical assumptions in visible text/caveats too: slides-only PDFs omit speaker
notes. The inherited permission and review gates apply to the entire typed model. Exact arithmetic
does not validate rates, scope, staffing, confidence, elapsed duration or commercial authority.
XLSX uses the same model with native scenario formulas; see [exports.md](exports.md) for
input labels, recalculation, invalid-state handling and the republication boundary.

Use these blocks to retain claims, assumptions, calculation results, decision asks and caveats
without changing facts between formats. Attachments and unknown fields are rejected rather than
silently copied or dropped. Large or unusual content may need a separately reviewed composition;
do not squeeze a functional specification into a presentation just because both use the packet.

## Carry restrictions forward

Each cited record and its input dependencies must declare `data.publication`:

```json
{
  "grants": [{"audience": "steering-group", "destination": "private-review",
              "treatments": ["citation", "excerpt", "notes"]}],
  "required_caveats": ["Synthetic example; not a measured result."]
}
```

These are reported permissions backed by actual consultant review, not machine-issued authority.
Unknown permission blocks use. Every dependency must permit the named recipient, destination and
treatment. Speaker notes need `notes` permission as well. Required caveats must appear in each
affected block. Keep restrictions even when summarizing or combining sources. If a governing record
cannot be cited or safely used, seek a permitted source or a reviewed alternative; do not remove
the dependency just to get a passing result.

Any explicit `data.publication` on the packet artifact also applies. Its `governed-by` inputs
and additional inputs not cited by any block apply across the packet. Cited sources and their
dependencies apply to their citing blocks. The publication review cannot override a declared
restriction; amend the permission through the normal review path first.

Use approved citation labels, not private vault or Notion URLs. The checker catches common private
links but cannot detect all sensitive wording, hidden identities or inaccessible source references.
The consultant must inspect those, including chart labels, tables, caveats and speaker notes.

## Record review, then check current readiness

Save a `review` record with `purpose: publication`, exact `packet` reference, `packet_hash`
(canonical JSON SHA-256), matching `audience` and `destination`, named `reviewer`, timezone-aware
`at`, `status: approved`, and `assessments` with `meaning`, `language`, `confidentiality` and
`citations` each `passed` only after actual assessment. Describe checks and repairs in the body.
Schema 3 also requires `brand: passed`, including the neutral choice when no brand is selected.
This is separate from client acceptance of business requirements.

Run `python3 scripts/engagement.py --root <engagement-directory> publication <packet-id> <review-id>`.
Read `ready`, not just the exit code. A blocked result names gaps and omits the packet. A ready
result includes the exact packet and its hash; it reports declared evidence, not authentication.
Current and pending source amendments invalidate readiness, including use of old snapshots.
Recheck immediately before an authorized export or send; an earlier result is not a lasting permit.

No file is sent, cloud page created or sharing changed by this command. The exporter must consume
only selected packet content; it must not follow source references into private engagement notes.
Retain output hashes and actual readback separately. Never equate exported with delivered.

# Blueprinting five-case corpus — candidate 2

Development/initial-comparison tranche, not the complete qualification set. Candidate 2 addresses
source review TU-034tXbdZtW91NCMLY6n5Jz; **re-review pending, not accepted, not an executed evaluation**.
It supersedes candidate 1 manifest `895084e98aae4bda6a7e86c7cb7a59f7009b9914e98a76b693ab41172633adcf`.
Original, entirely fictional evidence: names, policies, commercial inputs and manufacturing
rules are synthetic business assumptions, not SAP facts or real client permissions. C2 input
SHA256: `161cd1901c4ecd456bbc8394370c37c045470383f7eb168b892cfc2b23dd505e` (checked at authoring).
The later C2 format choices supersede historical Google Slides requirements. No product capability
is asserted as verified; all proposed product/version fit remains unknown in these fixtures.

## Information boundary

Create an isolated input bundle outside this checkout for each future worker. Do not give a worker
this README, the manifest, checker, or any reviewer directory. A read-list alone is prompt separation,
not access control. Log actual accessible paths and any contamination. No worker has been run here.

Worker-safe initial files: `worker/protocol.md` and **only its own** `worker/<case>/brief.md`.
Worker-safe staged files, in fixed order:

| Case | Stage files | Source items | Selected eventual deliverables |
| --- | --- | ---: | --- |
| manufacturing | `01-discovery.md`, `02-kickoff.md`, `03-proposal-closeout.md` | 15 | Markdown working record; DOCX kickoff; XLSX cost scenarios; PPTX executive decision; PDF of deck |
| service | `01-intake.md`, `02-correction.md` | 8 | Markdown findings and debrief; DOCX functional discovery |
| finance | `01-handover.md`, `02-readiness.md` | 8 | Markdown lineage/decisions; DOCX kickoff; PDF of kickoff |
| presales | `01-opportunity.md`, `02-buying-update.md` | 8 | Markdown qualification; XLSX cost range; DOCX proposal |
| rfp | `01-tender.md`, `02-addendum.md` | 8 | Markdown obligation ledger; DOCX response |

All paths in that table are beneath `worker/<case>/`. Source IDs and paragraph anchors are stable
span identifiers; citations should use e.g. `M08.b`, not an unstated inference. Briefs supply tasks,
not outcome keys. Each independent engagement has its own policy, vocabulary and decision context.
The manufacturing case is one engagement across three stages, not three independent samples.

**Reviewer/controller only:** `reviewer/answers.md`, `reviewer/keys.md`,
`reviewer/numeric.json`, `reviewer/calibration.md`, `reviewer/review-protocol.md`, `reviewer/topics.md`,
`manifest.json`, `check.py`, and this README. Keys and calibration must never enter worker context.
The controller may release only the matching answer rows, as plain attributed evidence, not the
whole answer table. Other engagements' sources are not worker inputs or reusable templates.

## Freeze and review

`python3 evals/blueprinting/corpus/check.py` checks file identity, source/answer references,
stage identities/counts and Decimal arithmetic. It does not establish entailment, source truth,
functional completeness, secure isolation or approval. A valid manifest is a **candidate content
snapshot**, not frozen acceptance. `--write-manifest` deliberately replaces that local snapshot;
only use for a documented new fixture revision before independent review, never to hide drift.
The script does not invoke Blueprinting helpers, models, cloud services or evaluation workers.

Separate reviewer must inspect every source-to-key expectation, missing relationship, alternative,
authority scope and numeric basis, then record findings against this manifest hash. Predeclare and
record limits, applicability and run-plan changes within existing authority before attempts; this
adds no renewed owner budget-approval gate. Exceeding existing authority or taking external effects
still requires the applicable approval. No silent retries or fact repairs during a worker run.
If a key is defective, preserve it and all original judgments; version the correction and rescore
both arms symmetrically. An exposed/repaired case is not held out. No held-out variants are supplied
in this tranche. A separate held-out/reliability set must be independently authored, source-reviewed
and frozen before generating its outputs; this initial comparison cannot substitute for that set.

## Remaining qualification outside this corpus

Audio files are deliberately unavailable: transcript handling/clarification is exercised, actual
transcription fidelity is not. Cloud save/retry and reminder incidents below are fictional tabletop
records, not platform receipts. No live writes, schedules, external submissions or new effects are
needed to satisfy a key. Real Notion recovery, scheduler recovery, native editing/rendering, branding
stress cases, Obsidian/Bases UI, installed-package checks and owner value review stay with integration
owners. Text review cannot certify those outcomes. Selected native deliverables are content tasks
for future runs; their actual export/editability checks must be recorded separately, not fabricated.

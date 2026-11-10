---
name: synthesizing
description: "Turns raw planning inputs (workshop and meeting notes, audio or video transcripts, minutes of meetings, emails, interview notes, and rough drafts) into one evidence ledger: numbered sources, numbered evidence with who said it and where, contradictions, open questions, and a stakeholder map, so later PRDs and backlogs can trace every claim back to its source. Use when asked to synthesize, digest, consolidate, or summarize workshop or stakeholder inputs, extract requirements or decisions from notes or transcripts, or prepare discovery evidence for a PRD. Not for writing the PRD itself (use specifying) or distilling public YouTube videos (use distill)."
---

# Synthesizing

Read every input, and write down what people actually said, who said it, and where, without
deciding yet what to build. The output is `evidence.md`, a ledger that `specifying` and
`grooming` cite by ID (`E7`) so anyone can later check a requirement against its origin.

## Inputs you can take

| Input | How to read it |
| --- | --- |
| Notes, minutes, drafts, emails (`.md`, `.txt`, `.docx` text, pasted text) | Cite by heading or line |
| Transcripts (`.vtt`, `.srt`, meeting-tool exports) | Cite by timestamp and speaker |
| Notion meeting notes | Read them with the Notion MCP when connected; cite the page and heading |
| Audio or video files | This skill does not transcribe. Ask for the meeting tool's transcript, or have the user run a transcription service; for public YouTube videos use `distill` |
| Slides, whiteboard photos | Read text you can see; mark anything you infer from a diagram as `inferred` |

Copy inputs into `inputs/` in the mission folder when they are files, so the citations stay
valid. Leave out personal data the plan does not need (phone numbers, health, salaries); name
people by role when the user asks.

## Steps

1. **List sources.** Give every input an ID (`SRC1`, `SRC2`, …) with its file or link, kind,
   date, and participants. Nothing is read twice under two IDs.
2. **Extract evidence.** One row per claim, need, pain, number, decision, constraint, idea, or
   risk, each with an ID (`E1`, `E2`, …) that is never reused. Prefer the speaker's words;
   shorten, do not improve. Record:
   - **Kind:** `pain`, `need`, `goal`, `metric`, `driver`, `requirement`, `constraint`,
     `decision`, `idea`, `risk`, or `assumption`.
   - **Who:** name and role, or "unattributed".
   - **Where:** source ID plus timestamp, line, or heading.
   - **Confidence:** `quoted` (verbatim), `paraphrased`, or `inferred` (your reading; say why in
     the statement).
3. **Merge duplicates.** When several sources say the same thing, keep one row and cite every
   source in "Where". Agreement is useful evidence.
4. **Surface contradictions.** Two rows that cannot both be true go under Contradictions with
   both IDs. Do not resolve them; they become `grilling` questions in `specifying`.
5. **List open questions** (`Q1`, …) that the inputs raise but do not answer, with who could
   answer each.
6. **Map stakeholders:** name, role, what they care about, their influence, and whether they
   should approve the PRD or features (and their tracker handle if known).
7. **Write `evidence.md`** using the format below, then run the checks.

Business drivers deserve attention: anything about money, risk, compliance, customers, or
strategy is a `driver` candidate for the PRD, so record it with the speaker's numbers.

## Format

```markdown
# Evidence: <initiative>

## Sources
| ID | Source | Kind | Date | Participants |
| --- | --- | --- | --- | --- |
| SRC1 | inputs/2027-01-08-workshop.vtt | transcript | 2027-01-08 | Priya Raman (Finance Ops lead), Tom Okafor (Group Controller) |

## Evidence
| ID | Kind | Statement | Who | Where | Confidence |
| --- | --- | --- | --- | --- | --- |
| E1 | pain | "We lose three days just ticking bank lines against invoices." | Priya Raman | SRC1 00:04:12 | quoted |

## Contradictions
- E4 vs E7: <what conflicts>; ask <who>.

## Open questions
- Q1: <question>; who can answer: <name>.

## Stakeholders
| Name | Role | Cares about | Influence | Signs off | Handle |
| --- | --- | --- | --- | --- | --- |
```

Every evidence row starts with `| E<n> |`: `backlog.py validate` reads those IDs to check that
backlog traces point at real evidence.

## Adapt it

- **Large inputs** (more than about 10 hours of transcript): split by source across subagents,
  each returning rows for its sources with the same columns; you merge, renumber once, and
  dedupe. Sources never change ID.
- **Ongoing discovery:** append new sources and evidence; never renumber. Withdraw evidence by
  striking its ID through (`| ~~E4~~ | …`) and saying why, instead of deleting the row, so traces
  stay valid.
- **Extra columns** (theme, persona, journey stage) are fine; keep the first column the ID.

## Example

From a transcript line `00:04:12 Priya Raman: Honestly, we lose three days just ticking bank
lines against invoices, and that's sixty hours a month across the team.` you write two rows:

```markdown
| E2 | pain | "We lose three days just ticking bank lines against invoices." | Priya Raman (Finance Ops lead) | SRC1 00:04:12 | quoted |
| E5 | metric | Manual bank reconciliation takes about 60 hours a month across the AP team. | Priya Raman | SRC1 00:04:12; SRC3 §2 | paraphrased |
```

The full set for this example is in `planning/reference/worked-example/evidence.md` when the
`planning` skill is installed.

## Check your work

- Every input appears once under Sources, and no source is unused unless you say why.
- Every evidence row has a kind, who, where, and confidence; no `inferred` row is presented as a
  fact.
- Every quantity stated in an input (an amount, count, duration, rate, or deadline) appears in
  some evidence row, whatever its kind.
- Contradictions and open questions are listed, or the file says "None found".
- **Fresh-context spot check** for any mission input set: give a subagent `evidence.md` and the
  sources, and ask it to verify 5 random rows plus every `driver` and `metric` row against the
  cited location and to name any important point in the sources missing from the ledger. Fix
  the ledger, not the reviewer's understanding.

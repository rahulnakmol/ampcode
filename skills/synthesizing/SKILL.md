---
name: synthesizing
description: "Takes varied planning inputs (workshop and meeting notes, audio or video transcripts, minutes of meetings, emails, interview notes, and rough drafts), builds a cited evidence ledger, then uses grilling to question the owner until the intent is confirmed, and places what was asked against the backlog: a new initiative, a new goal, a feature under an existing goal, changes, bugs, or feedback. Writes evidence.md and an intake brief that kicks off the speccing cycle (specifying) or a backlog building or grooming session (grooming). Use when asked to synthesize, digest, or make sense of workshop or stakeholder inputs, find the intent behind notes or requests, prepare a kickoff, or prepare inputs for a PRD, backlog building, or grooming session. Not for writing the PRD itself (use specifying) or distilling public YouTube videos (use distill)."
---

# Synthesizing

Turn a pile of inputs into a decision about what to do next. Two parts, in order:

1. **Ledger:** write down what people actually said, who said it, and where, without deciding
   yet what to build. Output: `evidence.md`, cited by ID (`E7`) in every later artifact.
2. **Intake:** analyse the ledger, question the owner with `grilling` until the intent is
   confirmed, and place each ask in the backlog's shape. Output: `intake.md`, the kickoff for the
   speccing cycle or the agenda for a backlog building or grooming session.

The ledger is facts; the intake is decisions. Keep them apart so a later reader can tell what
was said from what was agreed.

## Inputs you can take

| Input | How to read it |
| --- | --- |
| Notes, minutes, drafts, emails (`.md`, `.txt`, `.docx` text, pasted text) | Cite by heading or line |
| Transcripts (`.vtt`, `.srt`, meeting-tool exports) | Cite by timestamp and speaker |
| Notion meeting notes | Read them with the Notion MCP when connected; cite the page and heading |
| Audio or video files | This skill does not transcribe. Ask for the meeting tool's transcript, or have the user run a transcription service; for public YouTube videos use `distill` |
| Slides, whiteboard photos | Read text you can see; mark anything you infer from a diagram as `inferred` |
| An existing `backlog.json` | Not evidence: read it with `backlog.py tree` to know what already exists before placing anything |

Work in the folder that holds (or will hold) `backlog.json`: `evidence.md` and `intake.md` sit
beside it, and inputs go in its `inputs/` folder so citations stay valid. For an existing
backlog, append to its `evidence.md`. If that file is missing, ask for it first. If it is lost,
start sources at `SRC100` and evidence at `E100` (or the next hundred above the highest `E` ID
the backlog traces), and say so
in the intake: the old traces cannot be checked, and `validate` warns about them until the old
ledger is restored. A row nothing cites yet may be corrected in place. Leave out personal data the plan does not need (phone numbers, health, salaries); name
people by role when the user asks.

## Part 1: the ledger

1. **List sources.** Give every input an ID (`SRC1`, `SRC2`, …) with its file or link, kind,
   date, and participants. Nothing is read twice under two IDs.
2. **Extract evidence.** One row per claim, need, pain, number, decision, constraint, idea, or
   risk, each with an ID (`E1`, `E2`, …) that is never reused. Prefer the speaker's words;
   shorten, do not improve. Record:
   - **Kind:** `pain`, `need`, `goal`, `metric`, `driver`, `requirement`, `constraint`,
     `decision`, `idea`, `risk`, `assumption`, `reaction` (an opinion about existing work,
     which usually becomes feedback), or `status` (a claim about the state of work, such as
     "the fix went live").
   - **Who:** name and role, or "unattributed". Second-hand: "Ana Costa, reported by Tom
     Okafor", with confidence `paraphrased` at most.
   - **Where:** source ID plus timestamp, line, or heading.
   - **Confidence:** `quoted` (verbatim), `paraphrased`, or `inferred` (your reading; say why in
     the statement).
3. **Merge duplicates.** When several sources say the same thing, keep one row and cite every
   source in "Where". Agreement is useful evidence. When they overlap only partly, split the
   claim into one row per point, so each row's sources agree on all of it.
4. **Surface contradictions.** Two rows that cannot both be true, or a row that conflicts with
   the backlog (a "fixed" bug that recurs, a goal the inputs contradict), go under
   Contradictions with both IDs. Do not resolve them here; they become intake questions. Once
   the intake decides one, mark it "resolved by E…" rather than deleting it.
5. **List open questions** (`Q1`, …) that the inputs raise but do not answer, with who could
   answer each.
6. **Map stakeholders:** name, role, what they care about, their influence, and whether they
   should approve the PRD or features (and their tracker handle if known).
7. **Write `evidence.md`** in the format below.

Business drivers deserve attention: anything about money, risk, compliance, customers, or
strategy is a `driver` candidate, so record it with the speaker's numbers.

```markdown
# Evidence: <initiative or session>

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

## Part 2: the intake

1. **Read what exists.** If a `backlog.json` exists for this tracker project, run
   `backlog.py tree` and note the initiatives, goals, and features the inputs touch.
2. **Draft the intent** in one or two sentences, before asking anything: the outcome, who
   benefits, why now, and the evidence IDs it rests on. If the inputs hold several asks, draft
   one intent per ask, propose an order, and a default placement for each.
3. **Grill to intent.** Load `grilling` and follow its round format: one to three questions per
   round, each with a recommended answer grounded in evidence, facts looked up rather than
   asked, and under about 400 words outside tables. Put the draft intents and default
   placements inside the first question ("Are these right?"), not in a preamble. Here the
   intake replaces grilling's brief and its gate: grill only until intent and placement are
   confirmed, for every ask in the same rounds, because placement questions are cheap.
   Requirements, edge cases, and verification are grilled later in `specifying` or `grooming`.
   The intake frontier, most consequential first:
   - **Intent:** is the draft right? What decision or session should this end in?
   - **Contradictions:** each one is a question, or a labelled assumption if the owner says so.
   - **Driver and success:** why the business cares, and the number that would show success.
   - **Placement:** is this new, or part of something that exists? Offer the actual candidates
     from `tree` ("a new goal under I-1, or a feature under G-2?").
   - **Open questions** that would change placement or scope; leave the rest for `specifying`.

   A clear, small intake (one bug report, one well-specified request for an existing feature)
   needs no rounds: state the placement and proceed. Stop grilling when every ask has a
   confirmed placement; detailed requirements belong to `specifying` and `grooming`.
4. **Record answers as evidence.** Add the interview as a source (`SRCn | intake interview |
   <date of the conversation> | <who>`), keep the answers verbatim in `inputs/`, and record each
   one as a `decision` row, or a `status` row when it reports a fact, so later items can trace
   to it.
5. **Place every ask** in the backlog's shape (`grooming/reference/contract.md`):

   | Placement | When | Goes to |
   | --- | --- | --- |
   | New initiative | A new problem with its own outcome and drivers | `specifying`: new PRD |
   | New goal under `I-n` | A new measurable outcome for an existing initiative | `specifying`: PRD change; reopens the PRD sign-off |
   | New feature under `G-n` | A new capability, process change, or campaign component that moves an existing goal | `grooming`: backlog building session |
   | Change to `F-n` or its stories | Scope, criteria, or priority of existing work | `grooming`: refinement; reopens that feature's sign-off |
   | Bug under `F-n` | Agreed behaviour is broken, and no existing bug covers it | `grooming`: bug triage |
   | Change to `B-n` | An existing bug recurs or is wider than written | `grooming`: bug triage; reopen or extend it, never duplicate it |
   | Feedback on `F-n` | A comment or reaction, not yet a change | `grooming`: feedback triage |
   | Measurement for `G-n` | A reading of a goal's metric | `grooming`: append to the goal's `measurements` |
   | Context | A date, risk, or driver that changes priority but is not work (a board meeting, a deadline) | the next session's agenda, such as re-scoring WSJF |
   | Approvers change | Someone should sign off, or stop signing off | `grooming`: edit `approvers`; warn that any listed approver can pass every gate in the file |
   | Parked | Out of scope or not now, with the reason | nowhere; listed so nothing is lost |

   Use real IDs from `tree`, never invented ones. New items get IDs in `grooming`, not here.
6. **Structure the candidates** for the receiving session: draft drivers and goals (metric,
   baseline, target, or `unknown`), features (description and a draft benefit hypothesis), story
   seeds (actor, change, value, and any numbers the inputs gave for acceptance), bugs, and
   feedback, each citing evidence and marked `confirmed` or `assumed`. Seeds are not ready
   stories: `grooming` makes them executable.
7. **Write `intake.md`** from [reference/intake-template.md](reference/intake-template.md):
   intent, placement table, candidates, decisions and assumptions, remaining questions with
   owners, and the agenda and pick-up prompt for the next session.
8. **Review, then confirm.** Run the fresh-context check (below) and repair the files. Then show
   the owner the intent and placement table and ask them to confirm or correct it: this is the
   intake's last round and counts as one. Nothing is specced or groomed on an unconfirmed
   intake. If the owner already corrected the intents and said to carry on, their reply is the
   confirmation: record it as such in `intake.md` and do not stop again.

## Write in plain English

The intake goes to people who decide; the ledger goes to people who check. Write so that someone who was not in the room can read it once, understand it, and approve
it.

- Short sentences, about 20 words at most, one idea each. Short bullets over long paragraphs.
- Everyday words. Spell out each acronym and planning term the first time, such as "rank score
  (WSJF)" or "must have (MoSCoW)".
- Numbers and names instead of adjectives: "by 07:00", not "early"; "the AP team", not
  "stakeholders".
- Say who does what: "the nightly job posts matches", not "matches are posted".
- Keep IDs next to words, never alone: "the exception report (S-3)", not "S-3".
- Exception: evidence rows marked `quoted` keep the speaker's exact words.


## Adapt it

- **Large inputs** (more than about 10 hours of transcript): split by source across subagents,
  each returning ledger rows with the same columns; you merge, renumber once, and dedupe.
  Sources never change ID. Do the intake yourself: it needs the whole picture.
- **Ongoing discovery:** append new sources and evidence; never renumber. Withdraw evidence by
  striking its ID through (`| ~~E4~~ | …`) and saying why, so traces stay valid. Start a new
  intake section per session, dated, rather than rewriting an old one.
- **Ledger only:** when the user only wants the inputs digested, stop after Part 1 and say the
  intake is not done.
- **Extra columns** (theme, persona, journey stage) are fine; keep the first column the ID.

## Examples

**New initiative.** Three inputs about a slow month-end close (a transcript, minutes, and a
draft) become 18 evidence rows; two intake rounds settle the 3-versus-4-day contradiction and the
FX-rounding question, and the intake places one new operations initiative with two goals and
three candidate features, routed to `specifying`. See
`planning/reference/worked-example/intake.md` when `planning` is installed.

**Grooming session for an existing backlog.** A steering-committee email asks for three things.
`tree` shows the close backlog, so one round of placement questions settles it:

| Ask | Evidence | Placement | Status | Next |
| --- | --- | --- | --- | --- |
| Exception report should show the supplier name | E22 | Change to F-1 (S-3 criteria) | confirmed | `grooming` refinement; F-1 sign-off reopens |
| Duplicate postings again on 9 March (03:40 re-send) | E23 | Change to B-1: the same defect recurs after its fix | confirmed | `grooming` bug triage |
| Add Germany to the next wave | E24 | New feature under G-1 | confirmed | `grooming` building session |
| Pilot closed in 5 days | E25 | Measurement for G-1 | confirmed | `grooming` |
| Audit committee sees the numbers on 15 April | E26 | Context: raises time criticality of the F-1 fixes | confirmed | agenda: re-score F-1 WSJF |

## Check your work

- Every input appears once under Sources; no source is unused unless you say why.
- Every evidence row has a kind, who, where, and confidence; no `inferred` row is presented as
  fact. Every quantity in an input (amount, count, duration, rate, deadline) is in some row.
- Every contradiction is resolved by a recorded decision, kept as a labelled assumption, or
  listed as open with an owner.
- Every ask has a placement that names real backlog IDs or "new", and the owner confirmed the
  intent and placement table.
- **Fresh-context check**, required before `specifying` or a session starts on the intake: give
  a subagent `evidence.md`, `intake.md`, the sources, and the `tree` output, and ask it as an
  adversary to (1) verify 5 random rows plus every `driver` and `metric` row against the cited
  location, (2) name important points in the sources missing from the ledger or the intake, and
  (3) say what it would put on the next session's agenda and anything it cannot place without
  asking. Fix the files, not the reviewer's understanding.

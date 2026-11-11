---
name: specifying
description: "Writes one PRD per initiative for a new product or feature, an operations change or new way of working (with automation and reporting), or a marketing campaign: business drivers, measurable goals, scope and non-goals, numbered requirements with measurable acceptance criteria, risks, and rollout, each traced to evidence. Interviews the owner with grilling, has a fresh reader test the draft, and seeds backlog.json with the initiative and goals so stakeholders can sign off in their tracker. Use when asked to write, draft, complete, or review a PRD, product brief, process-change brief, or campaign brief from evidence, notes, or an idea. Not for breaking a PRD into stories (use grooming)."
---

# Specifying

Write the PRD that stakeholders will sign off: why the business cares, what success is in
numbers, and what must be true when the work is done. One PRD per initiative. Every statement
of fact traces to evidence (`E7`) or is labelled as a decision or assumption.

## Inputs and outputs

- **In:** `evidence.md` and a confirmed `intake.md` from `synthesizing` when there are ones:
  the intake fixes the intent, the placement (new initiative or a new goal under an existing
  one), candidate drivers, goals, and features, and the agenda; do not re-ask its decisions.
  Otherwise the user's notes, an existing draft, or an interview from scratch.
- **Out:** `prd.md` beside `backlog.json`, plus the initiative and its goals in `backlog.json`
  (contract: `grooming/reference/contract.md`). Syncing the initiative puts the PRD in front of
  stakeholders for `/approve`.

## Steps

1. **Pick the template** in [reference/prd-template.md](reference/prd-template.md): the common
   core, with the section for `product`, `operations`, or `marketing` inserted after
   Requirements.
2. **Fill it from the intake and evidence first.** Start from the intake's candidates and its
   "Still open" list. Cite evidence IDs inline (`E5`). Do not ask the user what the ledger or
   the intake already answers.
3. **Grill the gaps.** Load `grilling` and run its rounds only on what is missing, contradicted,
   or a decision: drivers and their numbers, goal baselines and targets, scope cuts, risk
   appetite, sign-off. Every contradiction in the ledger becomes a question or a labelled
   assumption. Use grilling's rounds and concreteness gate, but the PRD is the brief: record
   answers as `Decision (who, date)` and `Assumption (revisit if …)` lines in the PRD, not in a
   separate grilling brief, and do not use grilling's own decision-log IDs (they clash with
   `D-` drivers and `F-` features).
4. **Number everything stakeholders will refer to:**
   - drivers `D-1…`: why the business cares, stated so you can later tell whether it was met;
   - goals: metric, baseline, target, date, and the drivers each serves;
   - requirements `R-1…`, each with measurable acceptance criteria `AC-1…`, numbered across the
     whole PRD. Write each defining ID in bold (`**R-2 …**`, `**AC-3**`): that is how
     `backlog.py` tells a definition from a mention. IDs are never reused once the PRD is shared.
5. **Run the checklist** below, then the fresh-context review.
6. **Seed `backlog.json`:** the initiative (`domain`, `problem`, `drivers`, `outcome`, `owner`,
   `prd`, `non_goals`, `trace`) and one goal item per goal. Run
   `python3 <grooming>/scripts/backlog.py validate backlog.json`: 0 errors; a warning that goals
   have no features yet is expected at this stage.
7. **Hand over:** the user approves the sync plan, `syncing` publishes the initiative, and the
   approvers sign off with `/approve`. Edits after sign-off make the approval stale; say so
   before editing a signed-off PRD.

## PRD checklist

- Every driver has a number or an observable condition, and at least one goal serves it.
- Every goal has metric, baseline, target, and date. A baseline of `unknown` comes with a
  requirement to measure it.
- Every requirement has at least one acceptance criterion with a number, date, time, or count;
  none relies on words like fast, easy, robust, or improved.
- Scope and non-goals are explicit; nothing in scope contradicts a non-goal. A promise written
  as a principle or a non-goal ("a person always decides", "nothing goes live before the
  review") also has an acceptance criterion that tests it, with a count that must be 0.
- Each fact cites evidence or is labelled `Decision (who, when)` or `Assumption (revisit if …)`.
- Risks name an owner and a mitigation; open questions name who answers and by when.
- Sign-off names the approvers and their tracker handles.
- "In short" opens the PRD and reads with no IDs; nothing explains the tools (backlog rules,
  rank score sums) to stakeholders.
- Alternatives include doing nothing. Every severity-4 edge case is handled by a control with a
  threshold, not a count.
- A decision someone reported for another person reads `Decision (who; reported by …, confirm
  at sign-off)`.

## Fresh-context review (required before sign-off)

Give a subagent only `prd.md` and `evidence.md` (and the contract's goal and driver sections if
it must check the seed). Ask it, neutrally, to:

1. explain in its own words the problem, the drivers, how success is measured, and what is out
   of scope;
2. list every requirement it could not turn into a test without asking a question;
3. list claims that are not backed by the cited evidence, and evidence rows that seem important
   but are not used.

Repair the PRD, not the reviewer's understanding. A substantive change goes back to the user;
recheck with a new fresh reader after material edits. Record the review result in the PRD's
change log.

## Write in plain English

Approvers read the PRD in their tracker, often on a phone, between other work. Write so that someone who was not in the room can read it once, understand it, and approve
it.

- Short sentences, about 20 words at most, one idea each. Short bullets over long paragraphs.
- Everyday words. Spell out each acronym and planning term the first time, such as "rank score
  (WSJF)" or "must have (MoSCoW)".
- Numbers and names instead of adjectives: "by 07:00", not "early"; "the AP team", not
  "stakeholders".
- Say who does what: "the nightly job posts matches", not "matches are posted".
- Keep IDs next to words, never alone: "the exception report (S-3)", not "S-3".


## Adapt it

- Add your organisation's sections (legal, security, finance approval) to the template; keep the
  ID scheme so tracing works.
- For an existing PRD, map its sections onto the template, add missing IDs without renumbering
  what stakeholders already cite, and grill only the gaps.
- A campaign "brief" or a process "design" is a PRD here; name the file what your team calls it
  and set `prd` in the initiative to that path.

## Example

For the month-end close initiative, evidence `E2` and `E5` (three lost days, 60 hours a month)
and the controller's audit-committee concern (`E9`) become:

```markdown
## Drivers
- **D-1 Cost:** cut the 60 hours a month of manual bank reconciliation (E5).
- **D-2 Control:** ledger-locked numbers for the board pack by business day 4 (E9).

## Requirements
- **R-2 Bank reconciliation runs nightly without manual matching.** (D-1, E2, E5)
  - **AC-3** Every bank line that matches exactly one open invoice is posted by 02:30.
  - **AC-4** Every unmatched line is in an exception report by 07:00.
```

The complete PRD is `planning/reference/worked-example/prd.md` when `planning` is installed.

## Check your work

- The checklist passes item by item, and the fresh-context review is recorded with its date.
- `backlog.py validate` shows 0 errors on the seeded file.
- The user has confirmed the PRD before it is synced for sign-off.

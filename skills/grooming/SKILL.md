---
name: grooming
description: "Builds and maintains a tracker-neutral backlog (backlog.json, contract backlog/v1): initiatives with business drivers, measurable goals, features with benefit hypotheses and WSJF, executable stories sized XS to L with measurable acceptance criteria, bugs with urgency, and feedback filed against features. Splits oversized work, triages stakeholder feedback, records delivery evidence and goal measurements, and checks everything with backlog.py (validate, tree, status, trace). SAFe-inspired, without epics. Use when asked to groom, refine, break down, split, size, prioritise, or clean up a backlog, turn a PRD into features and user stories, triage feedback, record what was delivered, or report traceability from goals to delivery. Not for writing the PRD (use specifying) or pushing to a tracker (use syncing)."
---

# Grooming

Turn an agreed PRD into a backlog anyone can execute, and keep it honest afterwards. The backlog
is `backlog.json`, defined by [reference/contract.md](reference/contract.md); read the contract
before your first edit in a session. `scripts/backlog.py` checks it.

```text
initiative → goals (1:n) → features (1:n) → stories (1:n), bugs (0:n), feedback (0:n)
```

## Commands

```sh
python3 scripts/backlog.py validate backlog.json                  # contract + Definition of Ready
python3 scripts/backlog.py validate backlog.json --require-ready  # final grooming gate
python3 scripts/backlog.py tree backlog.json                      # hierarchy; features in WSJF order within each goal
python3 scripts/backlog.py status backlog.json [--all-approvers]  # sign-off per approver; exit 0 when all gates pass
python3 scripts/backlog.py trace backlog.json                     # described → agreed → delivered → achieved; exit 0 when no gaps
```

Paths are relative to this skill's directory; run them from the mission folder with the full
path. `validate` exits 1 on errors; warnings guide drafting. Python 3 standard library only.

## Build a backlog from a PRD

1. **Start from the seeded file.** `specifying` leaves the initiative and goals in
   `backlog.json`. If it is missing, create them from the PRD first.
2. **Features per goal.** For each goal, list the capabilities, process changes, or campaign
   components that move its metric. Each feature gets a description, a benefit hypothesis tied
   to the goal's metric, WSJF scores relative to the other features, a milestone, and traces to
   `R-`/`AC-` IDs. A feature that moves no goal is out of scope or reveals a missing goal: ask.
3. **Stories per feature.** Write each as one executable unit:
   - a specific actor, not "user"; the change; the value in goal terms;
   - acceptance criteria as Given/When/Then that are the story's definition of done: every
     `then` has a quantity and at least one has a real number, date, time, or amount;
   - `work` type, `priority` (MoSCoW), `size` XS (half a day) to L (one iteration);
   - `depends_on` for real ordering only; `trace` to the PRD criterion it satisfies.
4. **Split anything bigger than L.** Mark it `XL` and `draft`, then split by workflow step,
   business rule, data variation, entity or region, channel, or happy path versus exceptions.
   Each part must still deliver something checkable. Remove the XL item when its parts exist.
5. **Unknowns become `research` stories** with a time box and the decision they produce, rather
   than guesses dressed as requirements. Work that depends on the decision is not written as
   stories yet: note it in the feature's `acceptance` or `notes`, and add the stories once the
   research story is delivered. The ready gate covers what can be executed now.
6. **Bugs** go under the feature whose behaviour they break, with observed, expected, steps, a
   reproduction criterion, priority, and urgency.
7. **Validate until clean**, mark stories `ready` as they pass, then run the gate:
   `validate --require-ready` with 0 errors.
8. **Fresh-context executability review** (below), then hand over to `syncing`.

Every child has one parent. If a story serves two features, it is two stories or the features
are cut wrongly.

## Triage feedback

`syncing pull` adds tracker comments as `open` feedback on a feature and prints comments on
initiatives and goals separately. For each entry decide with the owner:

- **accepted:** change the backlog, and put the changed item IDs in `resolution`;
- **declined:** give the reason the giver will read;
- **duplicate:** name the other `FB-` ID.

Initiative and goal comments either become feedback on the right feature (create a new entry
with the comment URL as `source`, so `pull` does not list it again) or a PRD change through
`specifying`. Changing a signed-off item makes its sign-off stale; tell the
owner which gate reopens. Draft replies to commenters for the user to approve; never post them
yourself without approval.

## Record delivery and outcomes

When a story or bug is done, verify each acceptance criterion against evidence (a pull request,
a run log, a published page, an attendance list) and add `delivery` with every criterion `met` or
`not met`. Do not mark a criterion met because the tracker item is closed. When a goal's metric
is read, append a `measurement`. `trace` then shows which drivers are satisfied and which gaps
remain.

## Fresh-context executability review

Give a subagent only `backlog.json`, the PRD, and the contract. Ask it, for every `must` story and
every `critical` or `high` bug: how would you do this, and how would you prove it is done? List
every question you would have to ask first. Also ask which PRD requirements no story covers.
Each question is a gap: fix the story, then recheck with a new fresh reader. Record the result in
the mission's README.

## Adapt it

- **Importing a rough backlog** from a tracker or spreadsheet: map each row to the contract,
  keep the source link in `notes`, and expect many drafts. Do not invent acceptance criteria
  you cannot trace; mark them draft and ask.
- **Your own work types or labels:** propose a contract change (`reference/contract.md`, the
  enums in `backlog.py`, and a test) rather than smuggling fields in; unknown fields are errors.
- **Team size scale:** the default sizes assume one person per story. If your iteration is not
  two weeks, restate the size anchors in the mission charter.

## Examples

Valid backlogs for each domain:

- [Operations: month-end close in three days](reference/examples/operations.json), with a
  delivered research story, a critical bug, accepted and declined feedback, and a measured goal.
- [Product: self-serve team onboarding](reference/examples/product.json).
- [Marketing: launch campaign](reference/examples/marketing.json).

All three pass `validate`. The operations and product examples keep one `draft` item each, to
show a backlog mid-grooming, so they fail `--require-ready` until it is finished; the marketing
example passes it.

A weak story and its executable rewrite:

```text
Weak:  "As a user I want faster onboarding."
Ready: As a workspace admin I want to upload a CSV of up to 500 users and see invalid rows before
       anyone is invited, so that I fix mistakes once.
       S-1.1 Given a CSV with 500 rows, 3 malformed, when the admin uploads it, then the preview
             lists 497 valid rows and exactly 3 errors with row numbers within 5 seconds.
```

## Check your work

- `backlog.py validate --require-ready` reports 0 errors, and you ran it after the last edit.
- `backlog.py tree` shows every goal with features and every feature with stories.
- The fresh-context executability review found no unanswered question, or each is resolved.
- No feedback is `open` at hand-over.

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
   components that move its metric. Each feature gets a description, a benefit hypothesis tied to
   the goal's metric, WSJF scores relative to the other features, a milestone, an `owner` (one
   named person, not a team, and not an approver who will not do the work), and traces to
   `R-`/`AC-` IDs. `--require-ready` fails on a feature with no owner, or on a feature, story, or
   bug owner that is a placeholder ("lead (to be named)", "name to confirm", "TBD"), so ask for
   owners in the same question round as sizes and milestones. If the user leaves the choice to
   you, name the person whose role does the work; when the evidence names nobody in that role,
   name the mission owner until someone is, even when they are an approver. Write "Owner assumed:
   …; confirm before sign-off" in the feature's `notes`: the status report lists it as blocked,
   and gate 6 needs an owner who agreed. A feature that moves no goal is out of scope or reveals
   a missing goal: ask.
   Dependencies and milestone dates decide the order first; the rank score (WSJF) only orders
   features that could go either way. If the two disagree, fix the scores.
3. **Stories per feature.** Write each as one executable unit:
   - a specific actor, not "user"; the change; the value in goal terms;
   - acceptance criteria as Given/When/Then that are the story's definition of done: every
     `then` has a quantity and at least one has a real number, date, time, or amount;
   - `work` type, `priority` (MoSCoW: `must` only when the milestone fails without it, so not
     every story is a must), `size` XS (half a day) to L (one iteration);
   - `depends_on` for real ordering only; `trace` to the PRD criterion it satisfies.
   - **Test every part of the criterion you trace.** Each channel, group, and promise in a PRD
     criterion needs a check that tests it: "stop texts by phone or on the page" needs a phone
     check and a page check; "0 customer records are used for training" needs a check on that
     rule, not only on what the assistant may read. A part no check tests gets its own check or
     story.
   - **Go-live and spend wait on finished gates.** A story that goes live, reaches customers,
     or commits money `depends_on` every story that completes one of its preconditions (an
     assessment, an approval, a contract, a sign-off). Those stories' criteria test the final
     artefact ("the signed assessment has 0 open high findings"), not a draft or a review of
     one. A go-live criterion names each precondition: "0 live proposals before S-13 and the
     board approval are both done".
4. **Split anything bigger than L.** Mark it `XL` and `draft`, then split by workflow step,
   business rule, data variation, entity or region, channel, or happy path versus exceptions.
   Each part must still deliver something checkable. Remove the XL item when its parts exist.
5. **Unknowns become `research` stories** with a time box and the decision they produce, rather
   than guesses dressed as requirements. Work that depends on the decision is either written now
   as `draft` stories that depend on the research story, or moved with its PRD criteria to a
   later milestone, said plainly in the PRD. A milestone never promises work that has no story:
   `trace` reports a criterion that only a feature lists. A story whose start depends on a
   condition nobody has measured yet ("only if the preview takes under 5 seconds") depends on a
   research story that measures it, and stays `draft` until it passes. The ready gate holds
   such drafts (a warning, not an error) while their research story is undelivered, directly
   or through the stories they depend on.
   - **Decisions someone else makes.** A PRD open question that work depends on (who builds
     it, which supplier, a board or regulator decision) is a `research` story too. Its owner is
     the person who decides, its time box ends on the decision date, and the work that needs
     the answer stays `draft` behind it. Never mark a story `ready` that assumes the answer.
   - **Won't-have items** keep the decision visible but leave the plan: priority `wont`, no
     milestone, and no grooming beyond the title and the reason in `notes`. The ready gate skips
     them, and no milestone or status report counts them.
6. **Bugs** go under the feature whose behaviour they break, with observed, expected, steps, a
   reproduction criterion, priority, and urgency.
7. **Check each milestone fits.** Count the working days from today to its `due` date and add
   up each owner's story sizes in it at the top of each size: XS ½, S 2, M 5, L 10 days. A
   research story is labelled by its time box (a 3-day spike is M, and `validate` warns when it
   is not), but counts at its time box in the sum: 3 days, not 5. Use only this scale in every
   sum you show. When an owner's work does not fit, move stories to a later milestone or name
   the fallback in the feature's `notes`. Never leave a milestone that cannot be met.
   - **Sizes against the team's estimate.** When your total differs from the team's own
     estimate by half of their estimate or more, your sizes are not ready. Re-size with the
     team's numbers if you have them: split stories until the total is within half of their estimate, and move what
     no longer fits. Otherwise keep the affected stories `draft` until the team re-sizes; the
     ready gate (gate 4) stays open and you say so.
   - **No team estimate yet.** Your sizes stand: keep the stories `ready` and say in each
     feature's `notes` that the sizes are yours. Plan a dated session where the team sizes them,
     as the next action in the report. Gate 4 stays open until the team has sized them at that
     session; then the bullet above applies.
   - **Outside approvals.** When someone outside the team approves work (a bank, a regulator, a
     data protection officer, a patient group), plan three dates: when it is submitted, when
     they decide, and one resubmission that still meets the deadline. Count their review days
     as working days and skip holidays. Write the criterion as their decision by a date ("the
     bank decides by 7 October"), not as their approval, and say what slips or is cut if the
     resubmission fails. What they approve is the final artefact people will see (the finished
     video, the final text), not only a script or a draft.
8. **Validate until clean**, mark stories `ready` as they pass, then run the gate:
   `validate --require-ready` with 0 errors.
9. **Fresh-context executability review** (below), then hand over to `syncing`.

Every child has one parent. If a story serves two features, it is two stories or the features
are cut wrongly.

## Run a session from an intake

When `synthesizing` hands over a confirmed `intake.md` (new features under existing goals,
changes, bugs, or feedback), work through its "Next session" agenda in order. Each placement row
becomes backlog edits: new features with their story seeds turned into executable stories, a
change to the named feature, a bug under its feature, or a feedback entry. Give new items IDs
here, cite the intake's evidence in `trace`, and tell the owner which sign-offs each change
reopens. A row marked `assumed` is confirmed with the owner before it changes the backlog. For
every ask that came from outside the team (a customer ticket, a stakeholder email), say who
tells that person the outcome, through the channel they used, and by when. Draft the reply for
the user to approve. It states only what the evidence confirms: a cause nobody has reproduced
reads "we can see … and will reproduce it with your file", work nobody has started is never
described as under way, and a date the team has not confirmed reads "we are aiming for 30 April
and will confirm after planning on 27 April". It says when the person hears next, such as when
the fix ships or the date moves. Acceptance checks that test the fix use the requester's own
example (their file, their case) when there is one.

## Triage feedback

`syncing pull` adds tracker comments as `open` feedback on a feature and prints comments on
initiatives and goals separately. For each entry decide with the owner:

- **accepted:** change the backlog, and put the changed item IDs in `resolution`;
- **declined:** give the reason the giver will read;
- **duplicate:** name the other `FB-` ID.

Initiative and goal comments either become feedback on the right feature (create a new entry
with the comment URL as `source`, so `pull` does not list it again) or a PRD change through
`specifying`. Changing a signed-off item makes its sign-off stale; tell the
owner which gate reopens. Draft replies to commenters for the user to approve, stating only what the
evidence confirms; never post them yourself without approval.

## Record delivery and outcomes

When a story or bug is done, verify each acceptance criterion against evidence (a pull request,
a run log, a published page, an attendance list) and add `delivery` with every criterion `met` or
`not met`. Do not mark a criterion met because the tracker item is closed. When a goal's metric
is read, append a `measurement`. `trace` then shows which drivers are satisfied and which gaps
remain.

## Fresh-context executability review

Give a subagent only `backlog.json`, the PRD, and the contract (with no PRD, as for new asks
against an existing backlog, give `intake.md` and `evidence.md` instead). Ask it, for every `must` story and
every `critical` or `high` bug: how would you do this, and how would you prove it is done? List
every question you would have to ask first. Also ask which PRD requirements, or parts of an
acceptance criterion, no story's checks test.
Each question is a gap: fix the story, then recheck with a new fresh reader. Record the result in
the mission's README.

## Write in plain English

Stories and bugs are read by the people doing the work and by approvers who sign off. Write so that someone who was not in the room can read it once, understand it, and approve
it.

- Short sentences, about 20 words at most, one idea each. Short bullets over long paragraphs.
- Everyday words. Spell out each acronym and planning term the first time, such as "rank score
  (WSJF)" or "must have (MoSCoW)".
- Numbers and names instead of adjectives: "by 07:00", not "early"; "the AP team", not
  "stakeholders".
- Say who does what: "the nightly job posts matches", not "matches are posted".
- Keep IDs next to words, never alone: "the exception report (S-3)", not "S-3".
- An acceptance criterion reads as one plain sentence when Given, When, and Then are joined.


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
- Every part of each traced PRD criterion has a check that tests it.
- Every reply to someone outside the team states only what the evidence confirms.
- No `ready` story assumes the answer to an open question; each such question is a research
  story owned by the person who decides.
- `backlog.py tree` shows every goal with features and every feature with stories.
- The fresh-context executability review found no unanswered question, or each is resolved.
- No feedback is `open` at hand-over.

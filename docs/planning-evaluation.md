# Planning mission evaluation

Five simulated missions tested the planning skills end to end, from raw inputs to a groomed
backlog. Each mission was judged by its own internal and external stakeholder and by a panel of
five product and program-management lenses (Amazon, Apple, Google, Stripe, Linear). Method and
files: [`evals/planning/`](../evals/planning/README.md).

## The missions

| ID | Domain and entry point | Owner and inputs | Stakeholder judges |
| --- | --- | --- | --- |
| s1 usage billing | Product; new initiative from a workshop transcript, a CFO email, and a draft | Head of Product, SaaS build service | CFO; a customer's platform lead |
| s2 clinic no-shows | Operations; minutes, interview notes, and a data extract | Director of Operations, hospital trust | Clinical lead; a 74-year-old patient representative |
| s3 Diwali launch | Marketing; founders' chat, agency email, and a brief | Growth lead, payments app | CEO; the partner bank's compliance reviewer |
| s4 onboarding grooming | Grooming new asks against an existing backlog | VP Product, SaaS | Engineering manager; the customer who raised a ticket |
| s5 claims triage | Frontier AI change in a regulated insurer | Chief Claims Officer | Data Protection Officer; an independent policyholder advocate |

A scenario passes when every hard check passes, every judge's mean score is at least 4.0, no
score is below 3, and readability holds (reading ease at least 50, at most 20 words per
sentence).

## Round 1 (rev1)

Machine checks passed in all five: `validate --require-ready` 0 errors; `trace` gaps only for
sign-offs, which the simulation does not run; reading ease 70 to 83 at 6 to 13 words per
sentence.

All 35 judgements were "approve with changes"; no scenario passed.

| Scenario | Judge means (range) | Lowest score | Hard-check fails |
| --- | --- | --- | --- |
| s1 | 3.43 to 3.86 | 3 | none |
| s2 | 3.43 to 3.86 | 3 | H6 from all 7 judges: waiting-list texts promised for the pilot, but only a research story covered them |
| s3 | 3.29 to 3.71 | 2 (Stripe: the referral fraud guard did not work) | none |
| s4 | 3.29 to 3.71 | 3 | none |
| s5 | 3.14 to 3.71 | 2 (advocate: robustness) | H8 from the advocate: an injury mentioned but not flagged was only counted, never stopped |

What the judges praised: sourced numbers, careful handling of money and privacy, small
backlogs, and owner decisions recorded instead of guessed.

Defects that recurred across missions, and the fix for each:

| Defect | Seen in | Fix |
| --- | --- | --- |
| Work promised in a milestone with no story behind it | s2, s4, s5 | `trace` now reports a PRD criterion that only a feature lists; grooming keeps such work out of delivery milestones or writes draft stories that depend on the research |
| Stories marked ready while waiting on an unmeasured condition | s4, s3 | Grooming: the condition becomes a research story the story depends on |
| Owners were teams, roles, or an approver who would not do the work | s1, s3, s4, s5 | Features take an optional named `owner`; gate 6 requires one |
| Milestones that could not fit the work | s4, s5, s2 | Grooming: a capacity check per milestone and owner, with a named fallback |
| Rank score (WSJF) arithmetic in every issue, contradicting the dependency order; every story `must` | all | Issues show only the score; dependencies and dates decide order first; `must` only when the milestone fails without it |
| Misuse, after-the-fact money, and people-at-risk cases missing or only counted | s1, s2, s3, s4, s5 | PRD template: an "Edge cases and misuse" table with five lenses; severity-4 handling must be a control with a threshold |
| Metrics without a counting rule or a fair comparison; guardrails that could not be expressed | s1, s2, s3, s5 | Template guidance on units, counting, and like-for-like comparison; goals accept `at most` and `at least` limits |
| No alternatives written down | s1, s2, s5 | PRD template: "Alternatives considered", including doing nothing |
| Hard to read for non-specialists: codes, tool internals, the full PRD at the top of the issue, gate "G1" next to goal "G-1" | all | PRD opens with a five-line "In short"; the PRD is collapsed in the issue; planner-only lines leave the status comment; "gate 1" in prose; no skill or tool names in stakeholder text |
| Requesters never told the outcome | s4 | Grooming: each outside ask names who replies, through which channel, by when |

Also found: the evaluation harness stamped the status comment with a wrong date (fixed), and
`sync.py report` and `excel` gained `--today`.

## Round 2 (rev2)

All five missions reran on the revised skills with the same personas, judges, and rubric. Machine
checks passed except as noted: reading ease 75 to 81 at 7 to 11 words per sentence.

| Scenario | Mean of judge means, rev1 → rev2 | Hard-check fails, rev2 | Main remaining findings |
| --- | --- | --- | --- |
| s1 | 3.65 → 3.61 | H6 from 2 judges: nothing moves the 10 design partners to usage billing on 1 April | Held invoices and runaway-bill holds have no deadline or default; the 88-day plan contradicts the team's ~300-day estimate; paid accounts that skip the budget get no alerts |
| s2 | 3.59 → 3.69 | none (rev1: all 7) | The plan's own estimate (9.7%) misses the 8% goal with no further lever; the offer job lacks the privacy gate the reminder job has |
| s3 | 3.45 → 3.51 | none; the bank's reviewer rejects | Teasers and finished reels skip the bank's review; no second review round; the referral reward does not match the activation definition |
| s4 | 3.49 → 3.69 | H4 from all 7: a draft story waiting on a measurement failed the ready gate | Research sizes contradict their time boxes; no named person owns each feature |
| s5 | 3.43 → 3.49 | H8 from all 7: "a handler always confirms" was a non-goal with no test | Nothing builds the proposal pipeline under test; the contract fallback still sends handler notes to the vendor |

Average score per dimension over all 35 judgements, rev1 → rev2: plain English 3.74 → 3.86,
value 3.63 → 3.77, lean 3.57 → 3.80, traceability 3.83 → 3.86, executability 3.63 → 3.51,
robustness 3.20 → 3.26, approvability 3.06 → 3.14.

What changed: the targeted defects mostly went away (s2's unbuilt pilot work, team owners on
features, missing alternatives, WSJF arithmetic in issues), and the writing got shorter and
plainer. Two hard-check fails were caused by rev2 itself: the new "conditional work stays
draft" rule clashed with the ready gate (s4), and stating a safeguard as a non-goal let s5 drop
its test. Robustness and approvability stay the weakest: the skeptical judges keep finding
plan-specific failure modes, which no general rule removes.

Fixed after rev2, not yet re-run in a simulation:

- The ready gate holds a draft story that depends on undelivered research (a warning, not an
  error); a unit test covers both sides.
- A promise written as a principle or non-goal needs an acceptance criterion that tests it.
- Research stories count their time box in the capacity check, and a gap of half or more
  against the team's own estimate is raised before sign-off.
- Goals get a leading measure with a checkpoint; every hold, pause, or manual step has a
  deadline, a default outcome, and tells the person affected.
- Issue bodies no longer show the rank score (it stays a Project field); research time boxes
  accept "working day" and "business day"; gate 6 no longer asks for a "delivery route" field.

Open, by design or for later:

- **Sign-off by people outside GitHub** (a CFO consulted on budget, a bank's copy reviewer, a
  data protection officer, a patient group) cannot be recorded; runners put it in the charter or
  a story. A recorded "written sign-off" entry would close it.
- **Fresh-context reviews never ran** in the simulation, because runners had no subagents. In a
  real Amp thread the planner runs them; their effect on these scores is untested.
- The pass bar (every judge mean ≥ 4.0) was not met in two rounds. Judges were briefed as
  skeptics, and every verdict but one was "approve with changes".

## Round 3 (rev3)

All five missions reran on the skills as merged after rev2 (dev at `bb9440d`), with the same
personas, judges, and rubric. The personas answered only from their briefs: anything the brief
did not cover got "not sure, use your judgement and label it", so later rounds carried more
labelled assumptions (owners, counting rules, controls) than decisions. Issue bodies in the
stakeholder views use the rendering from before the named-section templates (#30).

Machine checks passed in all five: `validate --require-ready` 0 errors (warnings only for
drafts held behind research, and in s4 for traces to the earlier ledger the owner declared
lost); `trace` gaps only for sign-offs; reading ease 69 to 80 at 6 to 12 words per sentence.

| Scenario | Mean of judge means, rev1 → rev2 → rev3 | Hard-check fails, rev3 | Main remaining findings |
| --- | --- | --- | --- |
| s1 | 3.65 → 3.61 → 3.49 | none (rev2: 2) | The 66% margin goal predates the plan's own ramp and annual-contract rules; stories marked ready while the plan says sizes are about a fifth of the team's estimate; the revenue check compares invoices, not recognised revenue |
| s2 | 3.59 → 3.69 → 3.63 | none | One mistaken tap gives a slot away with no undo; patients with basic phones cannot answer a link; the patient pack misstates the 30% target; rollout to 8% is half-planned |
| s3 | 3.45 → 3.51 → 3.39 | none; the bank's reviewer rejects again | Finished reels still skip the bank; the plan books the bank's approval date and no resubmission window; no channel funnel shows how 200,000 is reached |
| s4 | 3.49 → 3.69 → 3.67 | none (rev2: all 7) | No named person owns a feature; a parked deal's 2,000-row work queues ahead of 9 customer tickets; customer replies promise dates the plan calls assumptions |
| s5 | 3.43 → 3.49 → 3.33 | H8 from all 7 (two also H2, H6) | Live use waits only for the board, not for a finished model risk assessment; guardrails flag but never pause; 7 of 9 features have no owner |

Average score per dimension over all 35 judgements, rev2 → rev3: plain English 3.86 → 3.89,
value 3.77 → 3.71, lean 3.80 → 3.71, traceability 3.86 → 3.69, executability 3.51 → 3.31,
robustness 3.26 → 3.14, approvability 3.14 → 3.06. Two judgements were "reject" (s3 bank
reviewer, s5 Stripe lens); the other 33 were "approve with changes".

What the rev2 fixes did:

| Fix after rev2 | Held in rev3? |
| --- | --- |
| Ready gate holds drafts behind research as a warning | Yes: s4's H4 fail is gone; s2 and s5 hold pilot work as drafts without errors |
| A promise written as a principle needs a testing criterion | Yes for "a handler always confirms" (no judge failed it); s5's H8 moved to the next unstated gate |
| Holds and pauses have a deadline and a default | Yes: s1's held-invoice H6 is gone |
| A gap against the team's own estimate is raised before sign-off | Raised (s1: 58.5 vs about 300 person-days), but stories stay `ready`, which judges call "a label, not a fact" |
| Goals get a leading measure with a checkpoint | Present (s3: 60,000 by 24 Oct), but nothing happens when it is missed |
| Rank score out of issue bodies | Yes in bodies; it still shows in the status comment's trace table |

The scores moved by about as much as they did between rev1 and rev2, in the other direction, so
a single run per scenario does not separate a skill change from run-to-run variation. The
hard-check and verdict changes are the reliable signal: two scenarios lost their hard fails, and
s5 and s3 fail the same way they did before.

Defects that recur across rounds and missions, with the fix each points to:

| Defect | Seen in rev3 | Proposed fix |
| --- | --- | --- |
| Features without a named owner pass every machine check; gate 6 fails only by hand | s1, s3, s4, s5 judges; 4 of 5 runners | `validate --require-ready` errors on a feature with no `owner`; grooming asks for owners in the same round as sizes |
| A go-live depends on a gate in name only (draft risk assessment; bank approval of scripts, not finished ads) | s5 (H8 for the second round), s3 (bank reject for the second round) | PRD template: every precondition for live use or spend is a `depends_on` on the story that completes it, and an acceptance criterion on the final artefact, not a draft |
| Guardrails and checkpoints report but never act | s5, s3, s1 | Every guardrail and leading measure states the action on breach (pause, stop, or a named decision by a date) |
| Stories `ready` while the team's estimate says the sizes are far off | s1 | A gap of half or more keeps the affected stories `draft` until the team re-sizes |
| An outside approver's decision is booked as an outcome, with no resubmission round | s3, s2 | When an outside party approves, plan the submission date, their decision date, and one resubmission inside the deadline |
| Stakeholder issues carry E-codes, the full PRD, and a trace dump as the status comment | all | Named-section templates (#30) cover body structure; also replace the status comment's trace table with a five-line status (dates, blockers, who acts) |

Skill instructions the runners found unclear or contradictory (most reported by several):

- `synthesizing` makes the fresh-context check "required before `specifying`", while `planning`
  says a review that cannot run leaves the gate pending and work carries on.
- Nothing says whether a severity-4 control or an owner the planner chose after "use your
  judgement" counts as agreed.
- The vague-word check rejects the domain term "fast-track"; a strict "under Rs 250" and "to the
  cent" cannot be written in the allowed `at most` / `at least` form.
- `planning` says to write "gate 1", never "G1", but its own gate table uses G1 to G7.
- Charter questions have no stated place in the three-questions-per-round limit.
- The Excel check asks to "read the workbook back" without a reader.

Open, carried from rev2: sign-off by people outside GitHub still cannot be recorded, and
fresh-context reviews still never ran in the simulation.

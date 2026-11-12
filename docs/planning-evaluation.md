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

## Round 4 (rev4)

All five missions ran twice (runs a and b) on the skills as merged with the six fixes from rev3
(dev at `6c890e5`), with the same personas, judges, and rubric. Two runs per scenario show how
much a score moves between runs of unchanged skills. The stakeholder views use the named-section
issue templates (#30) and the new five-line status comment.

Reading ease was 69 to 79 at 7 to 13 words per sentence in all ten runs. `trace` gaps were only
for sign-offs. `validate --require-ready` reported 0 errors in six runs. It failed in four, all
because of the new sizing rule: 4b s1 held 11 stories (61 planner days against the team's
estimate of about 325). Three runs had no team estimate at all and held stories `draft` anyway:
4a s3 (5 stories), 4a s5 (16), and 4b s2 (all 26).

| Scenario | rev3 | Run a | Run b | Hard-check fails, a / b | Main remaining findings |
| --- | --- | --- | --- | --- | --- |
| s1 | 3.49 | 3.67 | 3.53 | none / H4 (sizes) | The 66% margin goal ignores the plan's own 6-month ramp and annual renewals; pricing page and invoice disagree on whether paid accounts get the free minutes; usage page and alerts read daily data but promise near-real-time |
| s2 | 3.63 | 3.57 | 3.35 | H6 from 2 / H4 (no estimate), H6 from 7 | The waiting-list offer promises "within 1 hour" from a nightly export; stop-texts by phone has no story; the monthly no-mobile check promised to patients has no story |
| s3 | 3.39 | 3.27 | 3.51 | H4 and H5 from 7, bank rejects / none, no reject | Two thirds of the target rests on an unmeasured banner rate; the bank's review dates were never agreed with the bank; referral ads do not state the cap and terms |
| s4 | 3.67 | 3.71 | 3.63 | H8 from 2 / none | Every feature owner is "lead, name to confirm"; customer replies promise a cause and a date the plan calls open; the status comment calls live work "overdue"; size-to-day sums disagree with the stated scale |
| s5 | 3.33 | 3.39 | 3.47 | H3 and H4 from 7, H5 from 5, H2 from 2, Apple rejects / H6 from 7 | No story builds or buys the assistant the test runs; the bias test can fail without stopping anything; nothing checks "no training on customer data"; health data in calls has no impact assessment |

Average score per dimension over all 70 judgements, rev3 → rev4: plain English 3.89 → 3.89,
value 3.71 → 3.74, lean 3.71 → 3.59, traceability 3.69 → 3.86, executability 3.31 → 3.16,
robustness 3.14 → 3.30, approvability 3.06 → 3.04. Two judgements were "reject" (4a s3 bank
reviewer, 4a s5 Apple lens); the other 68 were "approve with changes". No scenario passed.

Runs a and b of the same scenario differ by 0.08 to 0.24 in mean score, as much as any
scenario moved between rounds. Score changes between rounds are therefore noise at this sample
size. Hard checks and verdicts are the signal, and they also vary by run: s3 and s5 each had one
clean run and one with several fails.

What the rev3 fixes did:

| Fix after rev3 | Held in rev4? |
| --- | --- |
| Ready gate errors on a feature with no `owner` | Every feature has an owner, but most are placeholders ("Team Atlas lead (name to confirm)", "(to be named)") or assumed, and the check accepts any text. Judges still mark executability down for no named owner in s1, s3, s4, and s5 |
| Go-live and spend depend on finished gates | Yes for s5: the rev3 H8 fail from all 7 judges is gone in both runs. s3's bank reviewer did not reject in run b, but rejected in run a over unagreed review dates and undisclosed referral terms |
| Guardrails and checkpoints state who acts and the default | Yes: pauses, holds, and spend stops appear in every run. Judges now criticise thresholds instead (set at the baseline so noise trips them, or watching only one direction) |
| Sizes half or more off the team's estimate stay `draft` | Applied where an estimate existed (4b s1). With no estimate, runners split: 3 of the 8 such runs held stories `draft` and failed the ready gate, 5 kept them `ready` with gate 4 open |
| Outside approvals get submission, decision, and resubmission dates | Yes in s2 and s3, but the dates are written as the outside party's commitments without asking them (s3 bank reviewer, both runs) |
| Five-line status comment | The format holds. Its content misleads: a past milestone with unknown delivery shows as "overdue: 0 of 2" (s4), "Blocked: nothing" while owners are missing (4b s3), all goals on one line with "and 1 more" hiding a goal (s1) |

Defects to fix next, with the fix each points to:

| Defect | Seen in rev4 | Proposed fix |
| --- | --- | --- |
| No rule for sizing when the team has no estimate | 8 of 10 runs; runners split two ways | When no team estimate exists, planner sizes stay `ready`, are labelled as the planner's, and gate 4 stays open until a dated sizing session |
| Placeholder owners pass the ready gate | s3, s4, s5 | `validate --require-ready` errors on owner text such as "to be named", "to confirm", "name needed", or "TBD" |
| An acceptance criterion is traced to an item whose checks test only part of it | s2 (phone opt-out, letters for all), s5 (no training on customer data) | Grooming: every clause of a criterion, including each channel in "by phone or on the page", has a check that tests it |
| Customer replies state as fact what the plan calls open | s4 both runs (rev3 too) | Replies to customers state only what the evidence confirms; an assumed date reads "aiming for … we confirm on …" |
| The initiative issue embeds the whole PRD | s1, s2, s3, s5 lean notes | The initiative issue shows the PRD's "In short" and links to `prd.md` |
| The status comment hides blockers and calls unknown delivery overdue | s1, s3, s4 | Report unknown delivery as "delivery not recorded"; list stories with no named owner as blocked; one goal per line |
| Research story size disagrees with its time box; capacity sums use another scale | s4 both runs | `validate` warns when a research story's size does not match its time box; milestone fit uses the stated scale only |

Skill instructions the runners found unclear or contradictory (most reported by several, and
most carried from rev3):

- `synthesizing` requires the fresh-context check before `specifying`, and asks the owner to
  confirm after it; `planning` says a review that cannot run leaves the gate pending. With no
  reviewer, the owner always confirms first.
- Nothing says whether an owner's "use your judgement" confirms a PRD, a severity-4 control, or
  a customer reply, or whether gates 2 and 3 apply to a grooming session that adds no goal.
- With only approvers named, no feature owner satisfies both grooming ("name the person whose
  role does the work") and the contract ("not an approver who will not do the work").
- The vague-word check rejects "fast-track"; a strict "under Rs 250" has no allowed form.
- Charter questions have no stated place in the three-questions-per-round limit.
- The intake template names skills in text stakeholders read, which `planning` forbids.
- `sync.py github report` needs `--repo` even when nothing is posted.

Open, carried from rev3: sign-off by people outside GitHub still cannot be recorded, and
fresh-context reviews still never ran in the simulation.

## Round 5 (rev5)

All five missions ran twice again on the skills as merged with the seven fixes from rev4 (dev at
`013e456`), with the same personas, judges, and rubric. The stakeholder views now show the
initiative issue's full PRD folded under its "In short", as GitHub first displays it.

Reading ease was 71 to 81 at 7 to 14 words per sentence in all ten runs. `trace` gaps were only
for sign-offs. `validate --require-ready` reported 0 errors in eight runs. Both s1 runs failed it
for the right reason: the planner's sizes were less than half of the team's estimate (5a: 52
days against about 300, 6 stories held; 5b: 154 against about 325, 19 held). No run held stories
only because the team had no estimate, which three rev4 runs did.

| Scenario | Run a, rev4 | Run b, rev4 | Run a | Run b | Hard-check fails, a / b | Main remaining findings |
| --- | --- | --- | --- | --- | --- | --- |
| s1 | 3.67 | 3.53 | 3.53 | 3.53 | H4 (sizes) / H4 (sizes) | The 66% December margin has no bridge through the ramps, waves, and annual renewals; the ramp is defined only for a fixed bill; the headline cost counts only the work Tom estimated |
| s2 | 3.57 | 3.35 | 3.67 | 3.71 | none / none | The pilot's go bar implies about 9.8% trust-wide, not the 8% target; cancel then confirm can lose a slot already offered; patients without a smartphone are paused first when the team is busy |
| s3 | 3.27 | 3.51 | 3.57 | 3.49 | none / none | Owners are placeholders on stories ("Engineering (lead to be named)") or a team; the bank's review calendar is still assumed; referral terms are not on the ads; money figures disagree across sections (5b) |
| s4 | 3.71 | 3.63 | 3.78 | 3.71 | none / none | A 3-day spike is counted as 5 days; a won't-have story sits in Release 4.3 as `ready`; customer replies say "we are reproducing it with your file" when nobody has; every feature owner is the VP |
| s5 | 3.39 | 3.47 | 3.53 | 3.49 | H8 from 5 / H8 from 5 | Who builds the assistant stays a PRD question while its build story is `ready`; the injury lock works only when someone sets the injury flag; no impact assessment for health data in calls |

Average score per dimension over all 70 judgements, rev4 → rev5: plain English 3.89 → 3.84,
value 3.74 → 3.80, lean 3.59 → 3.73, traceability 3.86 → 3.89, executability 3.16 → 3.40,
robustness 3.30 → 3.41, approvability 3.04 → 3.14. All 70 judgements were "approve with
changes"; rev4 had two rejects. No scenario passed: approvability stays near 3 because every
plan still waits on named owners, a team sizing, and the fresh-context reviews.

Runs a and b of the same scenario differ by 0.00 to 0.08 in mean score this round, against 0.08
to 0.24 in rev4. Score changes between rounds stay within that noise, so hard checks and
verdicts remain the signal: the rejects are gone, H6 fails are gone, and the one new hard-check
pattern (s5 H8) appears in both runs from the same five panel judges.

What the rev4 fixes did:

| Fix after rev4 | Held in rev5? |
| --- | --- |
| With no team estimate, planner sizes stay `ready` and gate 4 stays open until a dated sizing session | Yes: no run held stories only for want of an estimate. The two s1 holds come from a real estimate |
| Ready gate errors on placeholder feature owners | Yes for features: none of the ten runs has one. The gap moved to stories (5a s3 "Engineering (lead to be named)", "Growth analytics (name to confirm)") and to team owners ("Tom Becker's team", "SplitPay app team"), and every run falls back to the mission owner as an assumed owner. Judges still mark executability down for no named owner in all five scenarios |
| Every part of a traced criterion has its own check | Yes: H6 failed in three rev4 runs (14 judgements) and in no rev5 run |
| Replies to outside people state only what the evidence confirms and say when they hear next | Partly: dates now read "aiming for … will confirm after planning". But the skill's own example, "are reproducing it with your file", was copied into both s4 runs, and judges in both called it untrue, since nobody had started. Both s4 intakes also say "Sales told in writing" for a note that was only drafted |
| The initiative issue shows "In short" and folds the full PRD | Yes: no judge complained that the issue embeds the PRD. Lean rose from 3.59 to 3.73. Judges now ask instead for the E-numbers, WSJF scores, and AC lists to come out of issue bodies |
| Status comment: goals one per line, owner-less features blocked, past milestones read "was due" | Partly: goals and dates read well. "Blocked: nothing" still printed in 5b s3, because an assumed owner counts as named. "was due 2027-03-19: delivery recorded for 0 of 2" read to the s4 customer as "the importer never shipped" |
| Research stories sized by their time box | Applied, but the bands round up: a 3-day spike must be M, which the fit check counts as 5 days. Judges in both s4 runs flagged the 3-day spike counted as 5 |

Defects to fix next, with the fix each points to:

| Defect | Seen in rev5 | Proposed fix |
| --- | --- | --- |
| An open decision stays a PRD question while work that depends on it is `ready` | s5 both runs (H8 from 5 judges each): who builds the assistant | Grooming: a decision someone outside the team must make (who builds, the board, the regulator) becomes a `research` story owned by the decider and time-boxed to the decision date, and the work that depends on it stays `draft` behind it. This also gives a board approval a proper hold, which s5 runners faked as research |
| The research hold reads only direct dependencies | 5b s2 (S-22 waited on S-20 through S-21 and failed as "is still draft") | `validate --require-ready` holds a draft whose dependency chain reaches an undelivered research story |
| A won't-have story is groomed, given a milestone, and counted in the release | s4 both runs, 5 judges | `wont` items carry no milestone, skip the ready gate, and are left out of milestone counts |
| A `ready` story can depend on a `draft` one | 5b s1 (S-15, S-17, S-33 behind draft stories) | The status comment lists such stories as waiting on the draft; `validate` warns |
| Story owners are not checked, and teams pass as owners | 5a s3, s1 and s5 both runs | Apply the placeholder check to story owners at the ready gate |
| Assumed owners read as named in the status comment | 5b s3 ("Blocked: nothing") | List features whose `notes` mark the owner as assumed under "Blocked" until the owner agrees |
| The fit check counts a research story at the top of its band | s4 both runs | Count research stories at their time box in milestone sums; keep the band only for the label |
| The skill's reply example claims work in progress | s4 both runs | Change the example to "we can see … and will reproduce it with your file", and mark a drafted, unsent note as "drafted, not sent" in the intake |
| The headline goal does not follow from the parts the plan delivers | s1 (margin bridge), s2 (9.8% against 8%), 5b s3 (127,000 unsourced banner activations), s5 (rollout feasibility) | Specifying: show how the goal adds up, with each part sourced or labelled, and the result the plan expects if every part is met. When that falls short of the target, say so in "In short" |
| A severity-4 control depends on a field someone must remember to set | s5 both runs (injury flag), 5 judges | Specifying: a severity-4 control says what sets its trigger and what catches a miss |
| The same number differs across files | 5b s3 (Rs 20 against 18 lakh), 5a s5 (two phase 1 end dates), s4 (S-6 1 or 2 days), 5b s1 (134 against 154 days) | Planning's final check: every number the PRD states reads the same in every other file |

Skill instructions the runners found unclear or contradictory (most carried from rev4):

- The mission-owner fallback for feature owners conflicts with "not an approver who will not do
  the work" when the mission owner is also an approver (several runs).
- Planning's gate 4 says the team total is "within half of yours"; grooming says it "differs
  from the team's own estimate by half or more". The base of "half" differs. Planning says gate
  4 stays open "until a dated sizing session"; grooming says "until the team has sized them".
- "Mostly yes, with corrections" without "carry on" is not covered as an intake confirmation
  (most runs), and nothing says whether the corrected intake is shown back.
- `synthesizing` requires the fresh-context check before `specifying`; `planning` says a review
  that cannot run leaves the gate pending, so carry on.
- Nothing says what to do when the owner answers "use your judgement" on the PRD or a
  severity-4 control.
- The milestone fit check ignores dependency chains and same-day deadlines (s3, s5).
- The vague-word check rejects "fast-track"; charter questions have no stated place in the
  three-question limit; `validate` and `status` do not take `--today`.

One run (5b s1) wrote a scratch file under `/tmp` that another run overwrote. It rebuilt its
round record from its own folder, and no text from another scenario was found in its files.
Later runs should keep scratch files inside their own folder.

Open, carried from rev4: sign-off by people outside GitHub still cannot be recorded (5b s2
recorded the patient group's approval as a dated decision outside GitHub), and fresh-context
reviews still never ran in the simulation.

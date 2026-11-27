---
name: delivering
description: "Delivers major features, use cases and concrete requirements as a contract mission: grilling, crafting UX, a whiteboard defense and a readiness preflight become one baselined contract with open questions, defaults and pre-authorized effects; the owner approves it once at kickoff; milestones then run autonomously, items built test-first in child threads or subagents, and each milestone merges into dev after tests, CI and two fresh reviews. The owner is asked only for the five stop reasons. Watches children, follows the disposition policy at a review cap, and writes checkpoint and close-out reports that ask nothing. Uses mission-control when it accepts a contract. Communicates in standard/formal or editorial mode, with ELI5 summaries under 300 words. Use to deliver a substantial feature, run an approved contract, or resume a multi-step mission. Not for standalone review, release-only work, trivial edits, or design-only exploration."
---

# Delivering

Deliver the agreed customer outcome, not merely green tests. A mission has **one approval**: the
owner approves a baselined contract at kickoff. After that, execution is autonomous, milestone by
milestone. Each milestone merges into `dev` at a checkpoint, and the owner is asked only for one
of the five stop reasons below. Missions have no budgets and use no agent teams.

This skill is instruction guidance, not a daemon, scheduler, permission grant or security boundary.
Use the tools actually available. A coordinator without filesystem or execution access hands
execution to an agent with the right environment; never invent execution evidence. For ordinary
tiny edits, use the normal workflow instead of a mission.

## The five stop reasons

Stop and ask the owner only when:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

- A stop is one message with one question, its options and a recommendation, and it is recorded.
  It is a human gate with a checked brief (`missioning`, "Prepare every human gate"). It names
  the items and milestones it blocks; other work continues.
- Anything else is not a stop. Take the safe, reversible default, record it as an assumption, and
  list it in the next checkpoint report. An open question in the contract takes its default.
- The owner can stop or pause the mission at any time by replying in the mission thread. Stop
  after the current step and report.
- With the plugin, reason 2 is asked only through `mission_effect`'s dialog, never as a separate stop.

## Choose the tools: the interim rule

Read [reference/mission-record.md](reference/mission-record.md) when starting or resuming a mission.

- Use `mission-control`'s contract tools only when the installed plugin's `mission_start` accepts a
  `contract` field. Check the tool's schema; do not guess.
- Otherwise follow the path for hosts without the plugin: the kickoff is one recorded owner reply,
  and the `missioning` gate ledger and the mission record hold the rest. The older plugin keeps the
  same tool names with its old behaviour until the contract version is on `dev` and installed in
  your Amp, so do not drive a contract mission through it.

## J1 Kickoff: one contract, one approval

1. **Frame.** Read the request, repository guidance, any existing brief and the delivery state.
   State the customer outcome and the delivery target in one sentence. Preserve the original
   requirements; separate clarification from a proposed change.
2. **Grill.** Load `grilling` and reuse a confirmed brief. Every criterion names a finite set of
   cases; a rule like "reject anything that…" lists its cases. If the skill is unavailable, say so
   and resolve the missing decisions without claiming to have run it.
3. **Design.** Write the spec, the dependency-ordered plan and the technical design. Use `crafting`
   for any experience change, and render every changed state (a screenshot or visual) for the owner
   before the baseline; record why UX is inapplicable when nothing changes. Settle choices that
   alter outcomes, compatibility or authority; leave routine coding choices to the implementer.
4. **Review the design fresh.** Run the design review lenses in
   [reference/review-and-recovery.md](reference/review-and-recovery.md) with `goldfishing`. Repair
   the package, not the reviewer.
5. **Defend it.** Run the whiteboard defense in
   [reference/whiteboard-defense.md](reference/whiteboard-defense.md). The defense record becomes
   part of the baseline before kickoff.
6. **Run the readiness preflight** on the repository, CI, credentials and every outside target:
   push access, `dev` exists, branch protection is readable (name a 403), required checks are
   pinned and green on `dev`, the child-thread tools exist, and each deploy, publish or tracker
   target is reachable, and the repository has a `verify.json` naming each package's end-to-end
   command and pure core ([reference/verification.md](reference/verification.md)); a missing one
   becomes the first item, with its core in observe mode. Kickoff waits for a passing preflight, so resolve each failed check while
   preparing the baseline, asking the owner then if only they can fix it (a 403 needs a plan or
   admin access); never fold it into the kickoff ask or leave it for mid-build. Turn a target that
   needs its own approval into an effect for kickoff to pre-authorize (one the owner does not
   pre-authorize stays stop reason 2), and any other gap that is not a failed check into an open
   question with a default. With the plugin, `mission_preflight` binds the result to the contract; kickoff is refused without a
   passing preflight on the current contract.
7. **Write one contract** (fields in [reference/mission-record.md](reference/mission-record.md)):
   outcome, scope, spec, design, UX links, defense, the **closed case list** that bounds adversarial
   review, **open questions, each with a default**, **effects, each pre-authorized or not with its
   source**, readiness results, milestones with exit criteria, and items. Every item has an ID,
   title, milestone, size (XS, S, M or L; split anything larger), outcome, in scope, out of scope,
   dependencies, a definition of done with finite cases, an automated test, a human test and a trace.
8. **Write the kickoff brief** with `briefing-decisions`, run its checker, and run a `goldfishing`
   novice-reader review of it. It is the one brief: it lists every open question with its default,
   every effect, and the five stop reasons in plain words.
9. **Ask once.** With the plugin: `mission_start({ contract })`, `mission_preflight`, then
   `mission_approve`, which opens one dialog where the owner ticks each default and effect.
   Without it: one message that links the brief and asks for one reply; record the reply as a
   human ledger row quoting the owner's words and the message ID. An answer that changes a default
   or an effect is applied before execution starts and is not asked again; any other change is a
   new baseline revision that needs its own kickoff reply.

Until kickoff is approved, only read, research, draft, review, and publish the brief and record.
Take no effect. A generic request to build is not approval of an unseen contract.

## J2 Run the milestones

Run milestones in contract order. Cut each milestone branch (`mission/m<n>-…`) from current `dev`
after the previous milestone merges, and each item branch from its milestone branch. Follow the
repository's isolation policy; preserve existing work and never reset or clean it.

### The item protocol

- **Executor:** M and L items go to a child thread; XS and S items go to a subagent. The steering
  thread stays the one integration owner.
- **The brief is the item's contract slice:** its outcome, in and out of scope, definition of done,
  automated and human tests, trace, the cases it touches, the defense, the milestone branch on `origin`, the five
  stop reasons, and the reply route (the steering thread's ID, for `send_thread_message`).
- **The child** works test-first with the build loop below, runs one fresh `goldfishing` critic
  review against its definition of done and the cases it touches, passes the verification gate
  (`verify_gate.py check`) on its head, pushes its item branch, and reports its model (on Amp,
  from `get_thread_status`) and: a teach-back (outcome, approach, constraints, key risks, first check), branch and head,
  each done line with its evidence, the review record, assumptions taken and findings outside the
  case list. It creates no threads and merges nothing into `dev`.
- **A child stops only for the five reasons**, and sends them to the steering thread, never to the
  owner. Everything else is a recorded assumption in its report.
- **The steering thread** checks the evidence, merges the item branch into the milestone branch
  (`git merge --no-ff`), runs the checks and pushes. With the plugin, record `delegate` and
  `item-done` through `mission_update`.

### The milestone gates

1. Open the milestone PR into `dev` once all its items are done and the **verification gate**
   passes on its head: `verify_gate.py run --base <dev>`, then `verify_gate.py check --base <dev>`
   prints `pass` ([reference/verification.md](reference/verification.md)). Paste the check output
   in the PR body. With the plugin, record the PR as the `candidate`.
2. Run the tests. **Wait for PR and CI results** with the host's tool in `missioning`'s
   [reference/hosts.md](../missioning/reference/hosts.md). On a host without Amp's GitHub events,
   `scripts/pr_watch.py` waits; [reference/hosts-pr-watch.md](reference/hosts-pr-watch.md) gives
   its usage. Red CI is fixed on the milestone branch.
3. **Gate 1:** a fresh critic review with `interrogating-changes` of the whole milestone diff
   against the milestone's criteria and the closed case list, **on a model that implemented none
   of the milestone**. The reviewer runs the verification gate again itself. Its findings and both
   models go in a ledger that `review_ledger.py check` passes (rule L10 refuses a reviewer on an
   implementer's model).
4. **Gate 2:** after gate 1 passes, a second independent fresh review of the same head with
   `interrogating-changes`, in its own ledger, also on a model that implemented none of it. It runs the lowered-bar check `floor_guard.py` on
   the whole candidate diff; a flag without an accepted reason blocks, as a finding of at least
   Major. Its record holds the drift check against the contract and the refreshed defense.
5. Record one evidence line per criterion and per exit criterion, bound to that head.
6. Squash-merge into `dev` (`mission_merge`) under ship, only when the required checks are green,
   then read the merge back (`mission_reconcile`; without the plugin, `gh` and an agent ledger
   row citing the pre-authorized effect). Under stop, merge nothing (see below).
   There is no owner merge gate at any risk level. High risk means independent reviewers and the
   full case list, not a question to the owner. Any promotion after `dev` (to `rolling` or `main`)
   uses `releasing` and is an outside effect: run it only when the contract pre-authorizes that
   exact effect; otherwise it is stop reason 2.
7. **Record delivery evidence.** When the milestone delivered stories or bugs from a `grooming`
   backlog, give each one `grooming`'s delivery record right after the merge read-back (under
   stop, after its gates pass). Its evidence lists the milestone PR and the test command, and
   each acceptance criterion is `met` or `not met`. Then run `backlog.py validate` and `trace`;
   fix a refused record, never drop a criterion. The step is in
   [reference/mission-record.md](reference/mission-record.md#delivery-evidence-into-backlogjson).
8. Send the checkpoint report to the threads the charter names (by default, the mission thread).
   It asks nothing.

Each gate's verdict (`review_ledger.py verdict`) binds to the candidate's patch ID. A verdict on
another patch ID is stale and counts as no review. A gate passes while `review_ledger.py verdict`
says `changes needed` only when every open Blocker or Major is outside the case list and the
milestone's criteria and is filed.
If `interrogating-changes` is not installed, use the lenses in reference/review-and-recovery.md and label the review manual.

A review fails only on an open Blocker or Major inside the case list or the milestone's criteria.
A repair makes a new head: both gates run again on it, and earlier reviews and evidence lapse.
A repair changes the patch ID, so both gates run again. A rebase that keeps the patch ID keeps the
gates' verdicts, because they bind to the patch ID; the tests (such as `make check`) and CI run
again on the new head, and its evidence lines are recorded again.

### Ship or stop

The contract's Effects name one variant for the milestone PRs. An Effects entry that
pre-authorizes the milestone merges into `dev` names ship. Give that entry `"kind": "dev-merge"`
so `mission-control` reads the variant from it (one such entry at most). When the Effects name
neither, the variant is stop. This "stop" is a delivery variant, not one of the five stop reasons.
The variant is part of the approved contract and cannot change once a milestone is merged or ready.

- **Ship:** when both gates passed and the checks are green on the head, merge into `dev` only as
  the contract pre-authorizes that merge. A merge it does not pre-authorize is stop reason 2.
- **Stop:** the mission never merges. After the gates, it reads the PR's auto-merge state and,
  when the contract pre-authorizes writes to the PR, runs `gh pr merge --disable-auto` on it, so
  a queued auto-merge cannot merge it. It leaves the PR open. The checkpoint
  report lists the PR as ready under `Merged`, not as merged. The next milestone branch is cut
  from this milestone's head, and its gates review the diff from that head. Close out after the
  last milestone's gates pass. With `mission-control`, `mission_merge` records the milestone as
  ready instead of merging, after reading that the PR is still open on the reviewed head with no
  auto-merge or merge queue entry. The next candidate's `base` must be that reviewed head.

Running `gh pr merge --disable-auto` is part of choosing stop: an effect the stop variant needs,
recorded under Effects performed. Always read the PR's auto-merge state back; that only reads.
Without pre-authorized writes to the PR, skip the write; if auto-merge is queued, that is stop
reason 2.

Commands for both are in [reference/hosts-pr-watch.md](reference/hosts-pr-watch.md).

### The review cap: the disposition policy

A gate allows 3 failed rounds, and the count survives new heads; `interrogating-changes` counts
them in its ledger. After that the disposition policy decides, never the owner:

- A Blocker or Major inside the case list or the milestone's criteria is **fixed**. If it is still
  not fixed after 3 failed rounds, reopen the items concerned and re-plan and split them (**replanned**),
  keeping their criteria verbatim. Only "replanned" resets the gate's count. If the re-planned
  and split items reach the cap again, that is stop reason 5.
- A finding outside them is **filed** as an item in a later milestone, or as a follow-up when the
  current milestone is the last. It does not fail the review. A user-visible change beyond the
  baseline is never outside them: it is removed or raised as a stop (J3).
- A Nit is fixed or declined and never fails a review.

Item reviews follow the same policy; an item that reaches its cap again leaves its milestone
unable to meet its exit criteria. Stop reason 5 applies only when a milestone still cannot
meet its exit criteria after its items were re-planned and split.

## J3 Questions, assumptions and new scope

- A question with a safe, reversible default becomes an assumption (`assume`), listed in the next
  checkpoint report.
- New scope becomes an item in a later milestone (`file`), decided once, or a reason 1 stop when it
  changes the baseline. Re-planning or splitting an item keeps its criteria and is never a stop.
- A user-visible change beyond the approved baseline (a behaviour, screen or page the plan
  excludes, or one that goes beyond what it names) is removed before merge or raised as a reason 1
  stop. It is never merged as "accepted unless the owner objects".
- A pre-authorized effect is performed and recorded (`mission_effect` with its ID: no dialog).
  An effect that is not pre-authorized is stop reason 2.
- A check that seems to need a person is scripted where possible (for example with browser
  automation), and its human test goes in the checkpoint report.
- Usage is reported when the host shows it. It is never a stop.

## J4 Watch the children

- While any child runs, the steering thread watches it with `wait_for_threads` and keeps a
  30-minute schedule (`building-schedules`) as a backstop. Clear it when nothing is pending.
- When a child settles, read it. With a report, check the evidence. Without one, answer its
  question if the contract settles it, tell it to continue, restart it once from its branch, or
  re-plan its item. A child in error is restarted once from its branch, then re-planned.
- Never leave a settled child idle. A child that paused itself over a usage limit is told to continue.
- Until close-out or the owner's stop or pause, end a turn only while a stop answer, a child or a
  job is pending, and keep the backstop schedule so the thread resumes. "Carrying on with M2" with
  nothing running is an idle mission. A large context is no reason to pause: hand the next item
  to a child.

## J5 Close out

After the last milestone's checkpoint report (merged, or ready under stop), send the close-out
report. The owner's end review is a review, not a gate a merge waited on. Distinguish
**implemented**, **verified**, **reviewed**, **integrated into dev** and **released**. Release to
`rolling` or `main` (with `releasing`), deployment and publication happen only when the contract
pre-authorizes them.

Before the report, check that every story or bug each milestone delivered has its delivery record
(gate step 7), with `backlog.py trace`; record a missing one with that step. Pushing the records
to a tracker with `syncing` is an outside effect, done only when the contract pre-authorizes it.

## Reports

Write reports with `briefing-decisions`' writing rules. They ask nothing. With the plugin,
`mission_report` writes them. These section lists copy `reportSections` in `mission-control`'s
`lib/contract-text.json`; change both together.

- **Checkpoint report** sections, in order: `Merged`, `Done`, `Assumptions taken`, `Filed for later`, `Try it yourself`, `Next`.
- **Close-out report** sections, in order: `Outcome`, `Criteria and evidence`, `Assumptions`, `Filed items and follow-ups`, `Effects performed`, `Gate ledger`, `Human tests`.

The close-out holds evidence per criterion, every assumption, filed items and follow-ups, the
effects performed, the gate ledger and the human end-to-end scripts.

## Build loop: each item, test-first

### 1. Assess the current state

Read the implementation, callers, contracts, failures and existing evidence before editing.
Separate observations from assumptions. Surface conflicting patterns rather than blend them. Run
the relevant baseline and record what already works. A failing baseline is not automatically
pre-existing: reproduce it on the untouched base before attributing it.

### 2. Map the definition of done

Map each done line of the item to a test or an observable journey before implementation. Name
who benefits and what would count as no improvement. Never weaken a criterion or expand scope to
fit the implementation; a criterion that cannot hold is stop reason 1.

### 3. Build the test harness first

Write the smallest harness that shows the missing behavior, run it on unchanged code, and confirm
it fails for the right reason. A syntax error, missing dependency or mock set to fail is not a red
state. Name a plausible wrong implementation and choose inputs where it disagrees with the correct
result: asymmetric data, both sides of a limit, unauthorized actors, an interrupted write. Derive
expected results independently. A test that passes on empty output proves nothing. For a pure
refactor, use unchanged behavioral checks. For instructions and documents, use task scenarios and
observable outputs; keyword presence alone is not behavioral proof.

Write the end-to-end test first: each acceptance criterion as a Given/When/Then scenario that
drives the real program. Then unit and property tests for the pure core, and differential tests
for a rewrite ([reference/verification.md](reference/verification.md#what-each-kind-of-test-covers)).

### 4. Implement the smallest useful layer

Reuse local patterns and APIs; avoid speculative abstractions and unrelated cleanup. Keep
behavior-preserving refactors separate from behavior changes. Put domain rules in the package's
pure core, named in the domain's words: plain data in, plain data out, no I/O, clock or
randomness. Adapters parse input into domain types and format the core's decision; the outer
shell gathers input and performs the effects (files, network, database, LLM calls). Dependencies
point inward: the core imports nothing from the adapters or the shell. Use code, not model calls, for
deterministic routing, transforms, counting and checks. Commit coherent increments at green
boundaries, keep the red-run evidence, and stage only owned, relevant changes.

### 5. Run it

Run the harness and representative journeys on the real platform, not just mocks or typechecks.
Check actual outputs and persisted state, and exercise failure and recovery paths. For visual
changes, render the affected states and inspect the captures. Open the produced artifact and
compare it with the request. Record commands, expected and observed results, revision and
environment. A skipped required check blocks completion; an unavailable environment is reported,
not substituted. Before any pull request, commit and run `verify_gate.py run` and `check` for
the packages the change touched; a failure blocks the pull request.

### 6. Review, fix and recheck

Review the item against its definition of done and the cases it touches with a fresh reviewer
(see [reference/review-and-recovery.md](reference/review-and-recovery.md)). Turn each real bug
into a regression test that fails without the fix, make the smallest correction and rerun the
affected checks. Never suppress failures, delete useful assertions, hard-code answers or rerun a
flaky test until it passes; never add a retry, sleep or skip to a flaky test: fix its cause or
delete it with a written reason.

### 7. Apply the customer-value gate

Ask: **"Will what we built actually matter to the people using it?"** Compare the result with the
agreed problem. State the baseline, the observation and the limits; do not invent percentages or
claim production impact from a local demonstration. An enabling item can pass by showing its
prerequisite, but the final customer benefit stays unproven until the full journey passes.

## Resume and finish honestly

- On resume, read the mission record and contract, then reconcile the real worktree, remote state,
  children, running processes and outside operations. A saved status is a claim to check.
- Before an outside operation, record its intent and target; afterwards record the observed effect.
  A lost response is an unknown outcome: reconcile before any retry (see the recovery section of
  [reference/review-and-recovery.md](reference/review-and-recovery.md)).
- Checkpoint after each significant step: what changed, what is verified, what remains and the
  next safe action. Keep implementation and fixes with their checkout; another thread does not
  inherit uncommitted files.
- Report at milestones, not per tool call. Do not call a mission complete when only a milestone or
  local checks are complete. When blocked, preserve the work and a self-contained next action.

## Choose the communication form

Use **ASD-STE100-aligned principles** in both full-length modes: short sentences, active voice,
consistent terms, concrete verbs, and simple grounded language. Separate facts, assumptions,
decisions, proposals, and unknowns. State measurements with conditions and sources. Do not claim
formal compliance or certification without vocabulary and rule validation.

| Form | Default use | How to write |
| --- | --- | --- |
| Standard / formal | Requirements, defense records, handoffs, verification | Structured sections; explicit criteria, rationale, evidence, limitations, and next action. Tables or lists when they clarify. |
| Editorial | Design explanations, research findings, delivery narratives | Connected paragraphs, one idea each, descriptive section headers that state the point. Explain decisions and tradeoffs; do not turn the whole answer into a checklist. |
| ELI5 short form | Requested quick explanation or summary of either mode | Fewer than 300 words including headers. Plain, adult-respectful language; explain purpose, mechanism, choice, main risk, and next action. |

An explicit mode request overrides the default. Mode changes presentation, not evidence or gates.
For ELI5, count words with a deterministic tool when available; aim comfortably below the limit.
Never omit a required blocker, uncertainty, or authorization boundary to fit the word limit or
sound reassuring. Link the full record when useful, but keep the short explanation self-contained.

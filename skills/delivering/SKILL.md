---
name: delivering
description: "Delivers major features, use cases, and concrete requirements through small outcome-driven TDD slices, real user journeys, two review gates, and a customer-value gate. Uses grilling to confirm expectations, then tracks evidence, safe recovery, and authorized integration. Use when asked to build or deliver a substantial feature, execute an approved brief, carry a requirement through implementation and verification, or resume a multi-step delivery mission. Not for a standalone review, release-only request, trivial edit, or design-only exploration."
---

# Delivering

Deliver the agreed customer outcome, not merely green tests. Use two cycles: **frame expectations
with grilling**, then **build and deliver against those expectations**. Precision means traceable
requirements and evidence, not a promise of perfection. Keep ceremony proportional to risk.

This is an instruction workflow, not a daemon, permission grant, scheduler, or executable gate.
Use the tools actually available. A coordinator without filesystem or execution access must hand
execution to an authorized agent with the right environment; never invent execution evidence.

## Enter with a concrete agreement

1. Read the request, repository guidance, existing brief, and current delivery state. State the
   customer outcome and delivery target in a sentence. A task already approved in this conversation
   does not need another approval merely because this skill loaded.
2. Load `grilling` for the expectation loop. Reuse its existing confirmed brief without repeating
   the interview. For an incomplete brief, use its concreteness gate to resolve only missing or
   contradictory decisions. If the skill is unavailable, read its source if accessible; otherwise
   report the dependency and obtain the missing concrete expectations without claiming to have
   run grilling. Do not install or publish another skill implicitly.
3. Carry forward the final shape, problem and beneficiaries, scope/non-goals, decision provenance,
   numbered acceptance criteria, failure handling, verification, and dependency-ordered work plan.
   Identify the real delivery target, including any separate rollout approval and check. A brief
   marked pending or not concrete is not an approved mission. An explicit instruction to proceed
   with assumptions authorizes only those stated assumptions within the user's existing authority.
4. Confirm only consequential unresolved choices. Do not make the user repeat settled decisions.
   For an explicit mission that is already fully specified, the user's instruction to build it
   can be the confirmation. For ordinary tiny edits, use the normal workflow instead of creating
   a mission. Use `crafting`, when available and relevant, for experience design—not as a replacement
   for implementation, runtime validation, or either review.

## Prepare a recoverable mission

- Keep one integration owner accountable for the outcome, even when others contribute.
- Read [reference/mission-record.md](reference/mission-record.md) when starting or resuming a
  multi-step mission. Reuse the repository's existing plan/state convention; otherwise keep one
  compact record under `.amp/in/missions/<mission-id>/mission.md`. Ensure `/.amp/in/` is in the
  repository-local Git exclude before writing there. This local record is not automatically
  shared or backed up. Transfer the sanitized record and required artifacts explicitly before
  a handoff or deleting its worktree. Use committed plans only when repository policy calls for it.
- Record scope, current state, owners, acceptance-to-evidence links, and the next safe action.
  Update on meaningful transitions and before handoff, not on every tool call. Exclude credentials,
  private payloads, and unnecessary raw logs. Record exact revisions and environments.
- Establish authorized actions and existing time, spend, and attempt limits. Do not invent a
  monetary allowance or buy tools. If limits are absent, use the smallest useful slice and stop
  for a decision before materially expanding scope or cost. Repeated failure without a new
  hypothesis is a reason to diagnose or replan, not an unlimited retry loop.
- Follow repository isolation policy. Default to a dedicated branch/worktree from current
  `origin/dev`; fetch before creating it. Preserve existing staged and unstaged work. If `dev`
  does not exist, resolve the repository's integration branch—do not silently create it or use
  `main`. Inventory and safely transfer any task-related pre-existing work, preserving its source
  until verified. Never reset, clean, or overwrite unrelated work.
- Order slices by dependency and risk. Each should yield a useful outcome or a necessary enabling
  layer tied to an outcome. Validate accumulated slices at milestone boundaries, including their
  interactions. The final mission needs an end-to-end check of the complete customer journey.

## Build loop: repeat for each small, composable slice

### 1. Assess the current state

Read implementation, callers, contracts, failures, and existing evidence before editing. Separate
observations from assumptions. Run the relevant baseline and inspect the real test environment.
Record what already works and what must be preserved. A failing baseline is not automatically
pre-existing: reproduce on the untouched base in isolation before attributing it. Keep failures
visible; neither baseline attribution nor flaky retries waive a required check.

### 2. Define the customer outcome

Name the problem, intended improvement, scope, and measurable acceptance criteria using the brief's
IDs. Define who benefits and what would count as no improvement. Map each criterion to a test or
observable journey before implementation. For an enabling slice, name the downstream outcome and
demonstrate its necessity; do not pretend infrastructure alone proves customer impact.

If new evidence changes expectations, return to grilling for that decision. Never silently weaken
an acceptance criterion, override a user decision, or expand scope to make the implementation fit.

### 3. Build the test harness first

Write the smallest harness that demonstrates missing behavior. Execute it against unchanged code
and verify the expected assertion fails for the right reason. A syntax error, missing dependency,
unavailable credential, or mock configured to fail does not establish the behavioral red state.

Choose relevant realistic failure, recovery, security, and boundary cases. Name a plausible wrong
implementation and choose inputs where it disagrees with the correct result: asymmetric data,
both sides of a limit, unauthorized actors, interruption after a partial write. Derive expected
results independently. A test that passes on empty output or checks only that nothing crashed
does not demonstrate the outcome. Exercise a named technique such as fuzzing on the actual risk.

For a pure refactor, use unchanged behavioral checks rather than fabricating a missing behavior.
For instruction or document deliverables, use task scenarios and observable outputs; keyword
presence alone is not behavioral proof. Label simulations as simulations. Separate temporary
validation probes from maintained tests; keep tests of public contracts that catch plausible
regressions, extending existing suites before adding files.

### 4. Implement the smallest useful layer

Reuse local patterns and APIs. Keep responsibilities clear, and avoid speculative abstractions
or unrelated cleanup. Keep behavior-preserving refactors separate from behavior changes.
Commit coherent working increments frequently at green boundaries. Preserve the earlier red-run
evidence; TDD does not require publishing broken commits. Stage only owned, relevant changes.

### 5. Run it

Execute the harness and representative user journeys on the appropriate platform, not just mocks,
typechecks, or compilation. Check actual outputs and persisted state. Exercise applicable failure
and recovery paths. Record commands/actions, expected and observed results, revision, environment,
and artifact references. Measure before/after under comparable conditions when claiming improvement.

For visual changes, render affected states and widths and inspect captured images; screenshots
without inspection verify nothing. For interaction-only changes, exercise behavior and inspect
DOM/accessibility state. For APIs, CLI tools, migrations, and background jobs, inspect responses,
exit codes, data invariants, and recovery as relevant. Unavailable required environments remain
blocked or partially verified; substitute checks are useful but must not be called equivalent.

### 6. Review correctness, security, and vulnerabilities — gate one

Review the candidate against the brief and actual diff, tests, and runtime evidence. Examine
permissions, tenant/user isolation, secrets and logs, dependency changes, concurrency, data
preservation, and failure recovery. Record applicable risks and reasons for any non-applicability.
Read [reference/review-and-recovery.md](reference/review-and-recovery.md) for consequential changes,
delegation, or interrupted operations.

Use an independent reviewer context or person for consequential changes: authentication or trust
boundaries, money, sensitive data, migrations, concurrent state, destructive operations, or broad
shared contracts. Supply the candidate and criteria without telling the reviewer it is correct.
If that review is unavailable, record the blocker; self-review is not independent review. Small,
low-risk slices can use explicit self-review. Record reviewer, revision, scope, findings, severity,
and limitations. No-finding reviews still need scope and evidence, not just “LGTM.”

### 7. Fix and revalidate

Turn discovered behavioral bugs into meaningful regression tests, demonstrate the failure without
the fix, make the smallest correction, and rerun affected journeys and broader checks. Preserve
existing evidence when safe; do not undo user work to reproduce a bug. Resolve each finding or
obtain explicit authorized risk acceptance where policy permits. Risk acceptance cannot relabel a
failed mandatory check as passed; changing a required gate needs an explicit expectations decision.

Repeat while making evidence-backed progress. Stop and report when scope, authorization, required
environment, or agreed budget prevents progress. Never suppress failures, delete useful assertions,
hard-code answers, or keep rerunning a flaky test until one green result hides the failures.

### 8. Review the revised result again — gate two

Perform a distinct second review after repair and revalidation. Verify each finding is resolved,
inspect the repair's interactions with the complete change, and look for newly introduced problems.
For consequential changes, obtain independent review again; reusing the same reviewer is allowed.
If gate one found nothing, still recheck the final candidate and evidence; do not manufacture fixes.

Record the reviewed revision and finding dispositions. New code after approval invalidates review
of that delta and affected evidence. Return through repair/revalidation and gate two until the
final candidate is reviewed. Reuse unrelated evidence only with a recorded scope-based reason.

### 9. Apply the customer-value gate

Ask: **“Will what we built actually matter to the people using it?”** Compare the result with the
agreed problem and core purpose. Show reduced waiting, manual intervention, lost work, cost, or
uncertainty—or another agreed observable benefit. State the baseline, observation, and limitations.
Do not invent percentages or claim production impact from a local demonstration.

If tests pass but the customer still cannot accomplish the intended task, the slice has not met
its outcome. Reframe with the user rather than add unrelated functionality. An enabling slice can
pass by demonstrating the agreed prerequisite, while final customer benefit remains unproven until
the full journey passes. Do not lower the goal to “we wrote code.”

### 10. Integrate and learn

Commit the reviewed candidate, run configured CI, and integrate authorized green slices into `dev`
under repository policy. Carry existing authorization forward; do not ask again for actions it
already covers. If authority is absent, finish local work and ask for the specific external action.
Use PRs to `dev`, squash-merge when required checks are green and policy permits, then clean up
only this mission's branch/worktree after preserving its evidence. Use configured Depot runners;
do not invent runner labels or CI. No CI configured is not a green CI run: report the gap and
resolve the integration gate explicitly instead of merging on that assumption.

Check the exact candidate's required checks, review status, and mergeability. If the base or code
changes, revalidate affected integration behavior before merging. Follow Amp's PR comment/review
and exact-head CI subscription guidance when available; feedback is not new authority to push.
Record the merge outcome and relevant integration verification. Inspect remote state before
retrying an ambiguous push or merge. Capture lessons that change the next slice, not generic prose.

Keep `dev` integration, rolling promotion, deployment, and stable release distinct. Promote only
under the repository's schedule or explicit release authorization and applicable release gates.
Never infer stable-release or deployment approval from green CI. Publishing source extensions
does not install them into Amp Personal Skills; that publication requires separate approval.

## Resume, communicate, and finish honestly

On resume, read the mission record and confirmed brief, then reconcile the actual worktree, remote
state, running processes, and external operations. A saved status is a claim to check, not truth.
Revalidate stale evidence. Keep implementation and fixes with their checkout; another thread does
not inherit uncommitted files. Delegate only bounded independent work with explicit ownership and
handoffs. Worktrees do not isolate ports, databases, credentials, or external effects.

Report at meaningful milestones: outcome reached, decision changed, blocker found, verification
result, or integration completed. Keep routine tool narration out. Finish with the customer outcome,
evidence and limitations, unresolved risks, actual delivery state, and any exact approval needed.
Distinguish **implemented**, **verified**, **reviewed**, **integrated into dev**, and **released**.
Do not call a whole mission complete when only a slice or local checks are complete. When blocked,
preserve completed work and a self-contained next action so another session can resume safely.

---
name: delivering
description: "Delivers major features, use cases, and concrete requirements through initiator-acknowledged design, whiteboard defense, outcome-driven TDD, real journeys, two review gates, and customer value. Uses grilling and relevant crafting UX design, coordinates with mission-control when installed, and integrates into dev under risk-based gates. Communicates in standard/formal or editorial mode, with ELI5 summaries under 300 words. Use to deliver a substantial feature, execute an approved brief, or resume a multi-step mission. Not for standalone review, release-only work, trivial edits, or design-only exploration."
---

# Delivering

Deliver the agreed customer outcome, not merely green tests. Use two cycles: **frame expectations
with grilling**, then **build and deliver against those expectations**. Between them, obtain
initiator acknowledgment of the concrete design package, then defend the definition of done at
the whiteboard. Precision means traceable requirements and
evidence, not a promise of perfection. Keep ceremony proportional to risk; prefer caution over
speed for non-trivial work.

This skill is instruction guidance, not a daemon, permission grant, scheduler, or security boundary.
Use `mission-control` when installed, following [reference/mission-record.md](reference/mission-record.md).
Its local approval/evidence gates enforce the workflow, not security against an unrestricted shell.
It uses existing GitHub credentials through `gh` in Amp, with no custom controller/App or approval
service. Required source-App-pinned CI and strict, administrator-enforced dev protection must pass;
loading this skill/plugin does not configure them. Do not bypass gates with a shell command.
Use the tools actually available. A coordinator without filesystem or execution access must hand
execution to an authorized agent with the right environment; never invent execution evidence.

## Enter with a concrete agreement

1. Read the request, repository guidance, existing brief, and current delivery state. State the
   customer outcome and delivery target in a sentence. Preserve the original requirements and
   purpose; distinguish clarification from a proposed change. Carry forward a valid acknowledgment
   of the same design revision rather than asking again merely because this skill loaded.
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
4. Produce a concrete specification, dependency-ordered plan, and technical design. Use `crafting`
   for relevant UX design, including human and agent touchpoints; record why it is inapplicable
   when there is no experience change. If required design support is unavailable, report the gap.
   Build consequential packages section by section: customer problem and grading criteria,
   system/technical approach, alternatives and reasons, then implementation slices with affected
   files/contracts, invariants, checks and approval boundaries. Keep routine coding choices with
   the implementer; settle choices that alter outcomes, compatibility or authority in the design.
   Before requesting acknowledgment, run the risk-scaled Elephant-Goldfish design review in
   [reference/review-and-recovery.md](reference/review-and-recovery.md). Reuse current grilling
   comprehension evidence; repair gaps in the package rather than coaching a reviewer privately.
   Present both technical and applicable UX design, acceptance criteria, risks, and verification
   to the mission initiator. Obtain acknowledgment of this exact design package **before whiteboard
   defense or build**. A generic earlier request to build is not acknowledgment of an unseen design.
   In version one the initiator must be the Amp thread owner, or the owner must explicitly adopt
   the mission. Do not pretend to authenticate another multiplayer participant. With the plugin,
   use its owner-restricted design dialog; transcript text is not an agent-callable approval receipt.
   For ordinary tiny edits, use the normal workflow instead of creating a mission.

## Own the definition of done before handoff

Read [reference/whiteboard-defense.md](reference/whiteboard-defense.md) before the first
implementation handoff, including when the same agent moves from design to building, and only
after initiator acknowledgment. The integration owner
must explain the customer outcome, system and data flow, decisions and alternatives, data
structures and invariants, malicious actors, and failure/recovery boundaries. Function-name recall
is not required. Ground each answer in the brief, inspected contracts, evidence, or an explicitly
labelled proposal. Confidence and polished prose are not proof of understanding.

Record a concise defense and resolve blocking gaps before handing off implementation. A coherent
proposal can pass before runtime tests exist: those tests remain build obligations, not invented
results. A separate skeptical reviewer challenges consequential designs. The recipient must read
the actual brief and transferred materials and give a short teach-back; another thread does not
inherit shared memory. No second user approval is needed for already-approved, unchanged scope.

Use facts to resolve factual gaps, bounded experiments for uncertain mechanisms, and grilling for
changed expectations. Stop when confused and name the gap. Reopen only affected decisions when
design, ownership, threat boundaries, or data semantics change. Material changes to requirements,
scope, technical design, UX, or acceptance criteria reopen initiator acknowledgment **before**
renewed defense and build. Invalidate affected reviews and evidence; unchanged scope does not
need ceremonial reapproval. Refresh the defense against the
implemented system before delivery, so the owner can still answer “why?” and “where does it fail?”
This entry gate never replaces the two build reviews, executed tests, or customer-value gate.

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
- Establish authorized actions and time, spend, and attempt limits. Unless explicitly overridden,
  token limits are **4,000 per task and 30,000 per session**. Treat a task as a bounded work unit;
  record delegated work and carry usage forward in the session total. Use available usage telemetry;
  if unavailable, disclose that exact accounting and enforcement are unavailable. Label estimates
  as estimates and checkpoint conservatively near a limit. Surface a known or suspected breach.
  Do not claim compliance from a word count or create threads to erase usage. A fresh context can
  resume from a summary within the remaining budget; further work beyond it needs explicit approval.
  Never invent a monetary allowance or buy tools. Repeated failure without a new hypothesis calls
  for diagnosis or replanning, not an unlimited retry loop.
- Follow repository isolation policy. Default to a dedicated branch/worktree from current
  `origin/dev`; fetch before creating it. Preserve existing staged and unstaged work. If `dev`
  does not exist, report the integration prerequisite as blocked—do not silently create it or
  substitute `main` or another target. Inventory and safely transfer task-related pre-existing work, preserving its source
  until verified. Never reset, clean, or overwrite unrelated work.
- Order slices by dependency and risk. Each should yield a useful outcome or a necessary enabling
  layer tied to an outcome. Validate accumulated slices at milestone boundaries, including their
  interactions. The final mission needs an end-to-end check of the complete customer journey.
- At build entry, explain the merge policy: **low/medium risk defaults to automatic dev merge**
  after all gates, with an optional owner-selected **ask-before-merge** mode. Automatic mode
  needs no response or timer. High risk always requires acknowledgment of the exact final
  candidate, even in automatic mode; unknown risk is blocked until classified. Never silently
  downgrade risk. An owner mode change invalidates a prior final-candidate acknowledgment.
  Record the choice with `mission_merge_mode(mode: auto|ask)` when available; this offers an
  owner-restricted interaction, not authority for the agent to choose on the owner's behalf.

## Build loop: repeat for each small, composable slice

### 1. Assess the current state

Read implementation, callers, contracts, failures, and existing evidence before editing. Separate
observations from assumptions. Read exports, immediate callers, and shared utilities before adding
code. If their purpose is unclear, investigate and ask only when a consequential decision remains.
Surface conflicting patterns rather than blend them. Check authority, provenance, recency, and
tested behavior; state which applies and why. Flag the other without expanding scope to clean it up.
Run the relevant baseline and inspect the real test environment.
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
does not demonstrate the outcome. Tie tests to why behavior matters for the customer, not only
its mechanics; show which plausible business-rule violation they catch. Exercise a named technique
such as fuzzing on the actual risk when requested or useful, not as mandatory extra ceremony.

For a pure refactor, use unchanged behavioral checks rather than fabricating a missing behavior.
For instruction or document deliverables, use task scenarios and observable outputs; keyword
presence alone is not behavioral proof. Label simulations as simulations. Separate temporary
validation probes from maintained tests; keep tests of public contracts that catch plausible
regressions, extending existing suites before adding files.

### 4. Implement the smallest useful layer

Reuse local patterns and APIs. Keep responsibilities clear, and avoid speculative abstractions
or unrelated cleanup. Prefer the minimum code that solves the agreed problem; do not add a
single-use abstraction without a concrete need. Match repository style even when you prefer
another approach. Surface harmful conventions instead of silently forking them. Clean up only
your own task-related changes; do not reformat adjacent code or refactor sound code for taste.
Keep behavior-preserving refactors separate from behavior changes.
Use the model for judgment: interpretation, classification, drafting, extraction, summarization,
design tradeoffs, and ambiguous evidence. Use code or existing tools for deterministic routing,
fixed retry policies, transforms, counting, and checks. Do not spend model calls where code can
answer reliably. Pursue verified outcomes rather than mechanically completing a list; required
gates and permissions still apply.
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

Open the actual produced artifact and compare it with the original request, including scope,
content, tone, and specification where relevant. A successful process exit is not enough. If the
artifact cannot be inspected, report that part as unfinished. Name skipped checks and reasons;
a skipped required check blocks completion, while a genuinely inapplicable optional check needs
an explicit reason. Report what was present, missing, wrong, or different—not what was intended.

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

At gate two and after resuming interrupted work, compare the acknowledged design with the actual
implementation and executed evidence. Classify differences as missing behavior, unauthorized
change, approved design evolution, or stale documentation. Trace each to acceptance IDs and
source locations. Passing tests do not settle spec/code drift; do not rewrite the specification
to legitimize a defect. Reopen affected decisions/acknowledgment for material changes, and refresh
the handoff. See the drift protocol in the review reference. This is not a third build-review gate.

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

Present the inspected artifacts, acceptance evidence, both reviews, customer value, limitations,
and a reproducible **try-it procedure** before requesting merge (`mission_present()` when available).
For low/medium automatic mode, proceed without another human response only when all mandatory
local gates, required CI and branch protection pass. Ask mode and every high-risk candidate require owner
acknowledgment bound to the exact candidate and current design/base/mode. Unknown risk blocks merge.
Changed code or base needs affected revalidation and renewed exact-candidate acknowledgment where
required; material design changes also reopen the design gate. A local approval record cannot
override required CI or protection. Use `mission_approve(stage: merge)` and `mission_merge()` when available.

Commit the reviewed candidate, run configured CI, and integrate authorized green slices into `dev`
under repository policy. Carry valid existing authorization forward without treating stale receipts
as current. If GitHub access or protected-branch prerequisites are absent, finish local work
and report the specific blocker; do not provision shared protections without separate approval.
Use PRs to `dev`, squash-merge when required checks are green and policy permits, then clean up
only this mission's branch/worktree after preserving its evidence. Use configured Depot runners;
do not invent runner labels or CI. No CI configured is not a green CI run: report the gap and
resolve the integration gate explicitly instead of merging on that assumption.

Check the exact candidate's required checks, review status, and mergeability. If the base or code
changes, revalidate affected integration behavior before merging. Follow Amp's PR comment/review
and exact-head CI subscription guidance when available; feedback is not new authority to push.
Record the merge outcome and relevant integration verification. An accepted auto-merge request
is pending, not completion; verify the actual remote merge into dev. Inspect remote state before
retrying an ambiguous push or merge. Capture lessons that change the next slice, not generic prose.

Keep `dev` integration, rolling promotion, deployment, and stable release distinct. Promote only
under the repository's schedule or explicit release authorization and applicable release gates.
Never infer stable-release or deployment approval from green CI. Publishing source extensions
does not install them into Amp Personal Skills or Personal Plugins; each publication destination
requires separate explicit approval. Source delivery is not Personal publication authorization.

## Resume, communicate, and finish honestly

On resume, read the mission record and confirmed brief, then reconcile the actual worktree, remote
state, running processes, and external operations. A saved status is a claim to check, not truth.
Revalidate stale evidence. Keep implementation and fixes with their checkout; another thread does
not inherit uncommitted files. Delegate only bounded independent work with explicit ownership and
handoffs. Worktrees do not isolate ports, databases, credentials, or external effects.

Checkpoint after each significant step: what changed, what is verified, what remains, and the next
safe action. If you cannot describe the current state, stop and reconstruct it before continuing.
Carry relevant repository conventions and approval gates into that next action explicitly; do not
make the recipient infer them. Keep integration and later promotion gates distinct in the handoff.
Report at meaningful milestones: outcome reached, decision changed, blocker found, verification
result, or integration completed. Keep routine tool narration out. Finish with the customer outcome,
evidence and limitations, unresolved risks, actual delivery state, and any exact approval needed.
Distinguish **implemented**, **verified**, **reviewed**, **integrated into dev**, and **released**.
Do not call a whole mission complete when only a slice or local checks are complete. When blocked,
preserve completed work and a self-contained next action so another session can resume safely.

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

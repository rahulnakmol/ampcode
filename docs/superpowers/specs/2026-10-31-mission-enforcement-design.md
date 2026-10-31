# Amp mission delivery: four-stage enforcement and traceability

Date: 2026-10-31. Status: technical specification for owner review; the four-stage proposal is approved, implementation is not started.

## 1. Purpose and decisions

Make it possible to answer, for an exact delivered revision: what was requested, why this design was selected, what ran, what failed, who challenged it, why integration was allowed, and what was learned. Optimize accepted customer outcomes, not code volume, agent count, or green labels.

The upgrade remains native to Amp: skills describe behavior, mission-control validates transitions, native agents perform scoped work, deterministic tools produce observations, and GitHub protects integration. No Sonar dependency, separate hosted controller, or promise of perfect software.

Approved direction:

- Four stages: expectations; whiteboard defense; build/delivery; post-delivery adversarial review and learning.
- Traceability on every PR to `dev`, with compact records for eligible small changes. Roll out in shadow mode before making the check required.
- Evidence and enforcement first; dependency-aware coordination second. Serial delivery remains valid and is the default when coordination would add more work than it saves.
- Run full applicable verification locally/on Amp compute first, then repeat independently for the PR candidate in a clean environment. GitHub records and enforces the result; it need not host the expensive compute.
- Bun and Bun workspaces remain the default for pure TypeScript. Adopt Bazel selectively after measurement, not as a universal replacement.
- Mission-triggered investigation/remediation first. Recurring maintenance requires separate opt-in, scope, budget, and supported event/scheduling facilities.

This specification does not authorize new credentials, shared runner changes, branch-protection changes, deployment, release, or Personal publication. Integration goes through `dev`; `rolling`, `main`, and installation from stable `main` retain separate gates.

## 2. Research findings and what they change

The Parallel Task deep research completed using the pro processor [R1]. Its source-level inspection is corroborated by local reads of `plugins/mission-control/{index.ts,lib/mission.ts,lib/github.ts}`, `docs/mission-control.md`, and `.github/workflows/check.yml` at `origin/dev` `f56090192908a84dde1d50b2cd2c163d64f66da7`. It is research, not execution evidence. Its earlier open coverage question is superseded by the approved every-PR, proportional-record direction.

| Source finding | Adopt in Amp | Do not claim |
| --- | --- | --- |
| Sonar Vortex supplies Guide–Verify–Solve: code context, constraints, early analysis [R2] | Revision-scoped context, architecture/dependency rules, relevant deterministic checks, finding-driven repairs | Equivalent proprietary analyzers, identical detection rates, or measured token savings |
| Remediation Agent repairs findings and reanalyzes before offering reviewable PRs; it does not merge [R3] | Finding ID → regression → repair → independent validation; normal mission integration controls | A fix suggestion is proven correct or authorized to merge |
| Hunter discovers threat models, investigates logic/access/session flaws, consolidates and locates findings; it reads source, not running applications [R4] | Fresh-context source investigation with explicit confidence; optional separately authorized runtime reproduction | Source reasoning is an executed exploit or complete security proof |
| Google EGM uses a context-rich designer and fresh-context comprehension, antagonistic, and readiness reviews before implementation [R5] | Stage 2 uses those three checks; stage 4 applies fresh-context challenge to delivered behavior and proposes evaluated improvements | Google defines this exact four-stage lifecycle or an automatic post-delivery learning protocol |
| Amp supports native agent runs, persistent threads, placement, observation, and cancellation [R6] | Use those surfaces for bounded workers and explicit handoffs | A local plugin is an always-on distributed scheduler |
| GitHub check App identity is not identity of the workflow content; skipped/dependent checks need care [R7] | Trusted-policy origin, run/attempt identity, executed revision, mandatory-step receipts | A matching check name or App ID authenticates arbitrary evidence |
| Bazel models dependency-driven build actions [R8] | Consider it for expensive polyglot graphs and reproducible caching | Bazel intrinsically accelerates Bun test execution |

Functional analogues are the target; capability parity must be earned per analyzer/language through evaluation. No Sonar binaries, API keys, hosted analysis, or brand-dependent contracts enter the design.

## 3. Four stages and gates

| Stage | Entry gate | Work and required outputs | Exit gate |
| --- | --- | --- | --- |
| 1 — Expectations | Original request and owner recorded; repository baseline inspected; unknowns explicit | Grilling produces requirements, criteria, scope/non-goals, risks, budgets, verification matrix, technical design, and crafting journeys/UX where applicable | Native owner acknowledgment binds the exact design digest. Every criterion has an observable outcome and verification or judgment method. Missing critical decisions block |
| 2 — Whiteboard defense | Stage 1 digest still current and acknowledged | Designer explains contracts, invariants, alternatives, threat model, failure/recovery, migration, and ownership. Fresh reviewer performs comprehension, adversarial challenge, then readiness review for consequential work. Implementer teaches back the plan | Blocking findings resolved; dependency plan and test strategy implementable; defense binds the approved digest. Material changes return to stage 1 rather than silently expanding approval |
| 3 — Build and delivery | Current approval and passing defense; slice inputs available | Assess baseline; failing outcome tests; minimal implementation; coherent commits; real journeys; review 1; fixes/revalidation; review 2; value gate; independent PR verification; pending merge/reconciliation | Exact candidate passes required local and independent checks, both reviews, value gate, and applicable owner acknowledgment. Live reconciliation records actual integration commit. Requested/queued merge is not delivered |
| 4 — Adversarial review and learning | Integration commit observed and evidence available; scope/budget set in stage 1 | Fresh-context review of delivered code, invariants, artifacts and relevant journeys; compare expectation to outcome; substantiate findings; propose tests/playbook/skill improvements and corrective missions | Every finding has a justified disposition and accountable owner; blocking post-delivery findings keep mission follow-up open. Learning proposals are evaluated and accepted/rejected explicitly; unapproved proposals remain inactive |

Stage 4 must not defer known stage-3 blockers. It does not authorize production attack, rollout, incident mitigation, or silent modification of shared skills. Delivery and mission closure are separate: status can be `integrated; adversarial review pending`. A serious escaped defect routes into an authorized corrective mission and applicable release/incident process.

Stages 1–2 govern the mission's approved design revision. Stages 3–4 repeat for each delivery unit (one PR), not a single mutable mission-wide candidate. A mission may have one unit in post-delivery review while another is building. Mission status reports that mixed state rather than advancing the whole mission to stage 4 after its first merge. The aggregate completion gate below governs closure.

For policy-eligible small changes, use a short manifest and compact defense/reviews, not missing gates. Behavior/security/data/permissions/concurrency/ABI and user-journey changes are not eligible for a documentation-only profile merely because their diff is small. Unknown risk blocks. Consequential reviews require a different worker from the implementer; separate context reduces shared assumptions but does not establish independent human identity.

## 4. Ownership, storage, and trust boundaries

Three storage classes avoid committing secrets or requiring a file to contain its own final commit SHA:

1. **Committed intent:** proposed `missions/<mission-id>.json` contains sanitized requirements, stable criterion IDs, decisions, slices, risk rationale, verification profile, and design digest. No credentials, sensitive logs, native-dialog payloads, or claimed final-SHA receipts. One manifest may span several linked PRs.
2. **Local operational state:** preserve `.amp/in/missions/<thread-hash>/state.json`, repository-local exclusion, atomic writes, locking, generations, and effect intents. Version 2 adds structured records and stages. One coordinator owns writes; workers return outputs, never mutate the coordinator record directly.
3. **Run evidence:** access-controlled artifacts plus externally resolvable run/check metadata. Records have content digest, media type, size, access class, producer, retention owner, and expiry. A digest proves consistency with referenced bytes, not truth or authorship.

The native owner acknowledgment remains a local workflow record. The current API cannot mint an externally authenticated owner receipt from the masked confirmation field. Never export one as such. Remote enforcement validates machine-verifiable lineage and configured review rules; it must describe native owner/UX approval as locally reported unless a separately authenticated mechanism is explicitly designed and approved.

Local shell/admin tampering is outside the accepted security boundary. Tools and hooks guide and block ordinary transitions, but unrestricted shell can bypass them. GitHub protection is the independent merge boundary. An Amp runner containing normal developer credentials is not an untrusted-code sandbox.

The PR verification request identifies mission IDs and slice IDs; the trusted validator loads their manifests from the exact candidate checkout and checks every changed path against declared slice scope. Unmapped paths, missing manifests, or unresolved criterion references block. A slice may satisfy only part of a mission, but it must be independently useful and identify deferred criteria/dependencies; a partial slice cannot claim whole-mission completion. PR metadata helps discovery but is not trusted evidence. Reverts and automated dependency PRs need compact intent records too.

Artifact access defaults to private, with no public links or raw secrets. Before execution, the verification profile specifies retention duration, storage destination and deletion owner. Missing retention policy blocks artifact export. Durable sanitized receipt metadata outlives bulky artifacts; expired mandatory artifacts block new acceptance, while historical integrations remain recorded with their evidence-availability limitation. Redaction creates a new artifact/digest and an explicit relationship to the replaced record, not silent byte replacement.

### Acceptance authority and amendments

There are two distinct sources of acceptance requirements:

- **Policy-owned requirements:** mandatory check IDs, minimum thresholds, applicability rules and risk-profile floors come from the configured immutable trusted policy revision. The independent verifier derives applicability from the actual diff and trusted rules. Candidate manifests cannot replace, exempt, or lower these requirements. Unknown classification blocks. Policy changes need explicit adoption outside the candidate under evaluation; candidate-proposed policy bytes never authorize that same candidate.
- **Mission-owned criteria:** customer outcomes and additional thresholds come from the exact locally owner-acknowledged design snapshot, retained in operational state with its digest. Candidate manifests are proposals/exports, not the local authority. Before accepting a candidate, the coordinator compares its intent projection (requirements, criteria, thresholds, allocations and decisions) against that snapshot. Any difference reopens stage 1 and defense. The owner sees the old/new criteria and affected delivery units before acknowledging the replacement; prior snapshots remain available.

Remote verification reports policy compliance and execution of the submitted mission criteria separately. It records `intentAuthority: local-reported`, the submitted intent digest, and any locally reported approval reference; it does not assert that GitHub authenticated owner approval or independently prevented mission-specific weakening. A successful remote check alone cannot satisfy the local mission merge gate. Authenticated remote adoption of mission-specific intent is explicitly deferred, not implicitly supplied by a hash or manifest in `dev`.

For example, changing “recover after interruption” to “recover after clean shutdown” must fail the local snapshot comparison until the owner approves a visible amendment and renewed defense. If someone bypasses local coordination, remote verification may pass the weaker submitted criterion when no policy rule forbids it; that is the disclosed local-trust boundary, not a claimed anti-weakening guarantee. If interruption recovery is policy-mandatory, the remote check rejects its removal regardless of the local amendment. Tests must exercise both cases.

## 5. Version-2 data contract

All IDs are stable within a mission, unique, and assigned once; reordering or editing wording never changes identity. References must resolve. Parse bounded JSON as data, reject unsupported versions, duplicate IDs, invalid enums, missing fields, and invalid references. Do not execute artifact content or commands supplied by receipts.

| Record | Required fields and meaning |
| --- | --- |
| Mission | `schemaVersion: 2`, `missionId`, repository, initiating thread, design-stage state, aggregate status, event sequence, immutable design snapshots/approval references, policy reference, risk floor, budgets, delivery-unit IDs and criterion allocations |
| Delivery unit | `id`, mission ID, immutable repository/PR binding once assigned, slice/criterion IDs, approved design revision, stage-3/4 status, attempt history, active attempt ID, post-delivery findings and disposition |
| Candidate attempt | `id`, delivery-unit ID, recovery generation, candidate, evidence, reviews, presentation/merge acknowledgment, effect intent and observed integration; superseded attempts retained |
| Requirement | `id`, original need, scope/non-goals, owner; sensitive source retained privately with sanitized committed summary |
| Criterion | `id`, requirement IDs, authority (`policy` with immutable policy reference, or `mission` with local design snapshot reference), observable outcome, method (`automated`, `journey`, `judgment`), required check IDs/platforms, acceptance threshold or judgment owner |
| Decision | `id`, requirement/criterion IDs, alternatives, chosen rationale, assumptions and reconsideration trigger |
| Slice/task | `id`, criterion IDs, prerequisite output IDs, input revision, contract digests, declared write/resource scope, executor requirements, owner, attempt, state, budget, accepted output |
| Candidate | repository, PR, target `dev`, full head SHA, full base SHA, optional constructed integration SHA/tree, manifest digest, policy digest, generation |
| Evidence | `id`, criterion/check IDs, candidate fingerprint, producer class/identity, tool/version, argv/check ID, environment/toolchain, start/end, exit status, actual outcomes, scope, limitations, artifact refs |
| Verification receipt | evidence fields plus run/check/job IDs, attempt, source App, workflow identity/revision, event, requested head/base, actual checkout SHA/tree, resolved trusted policy, mandatory step outcomes |
| Finding | `id`, origin, affected revision/location, violated criterion/invariant, severity, confidence (`hypothesis`, `source-supported`, `runtime-reproduced`), reproduction/analysis, status, disposition authority and linked repairs |
| Review | gate, reviewer thread/role, input fingerprint, evidence-set digest, findings, decision, limitations; a reviewer cannot certify evidence it never inspected |
| Effect intent | operation ID, effect type, fingerprint, persisted request state, remote identifiers, reconciliation state and observed result |
| Learning proposal | finding IDs, proposed test/rule/skill delta, held-out evaluation cases, cost/false-positive results, decision owner, accepted/rejected/deferred, resulting change reference |

Evidence producer classes are `reported`, `local-executed`, `independent-executed`, and `human-judgment`. These are not interchangeable. An agent may submit a report, but only an execution adapter creates an execution receipt from process results. Missing evidence is `missing`, not a pass. Check results are `passed`, `failed`, `blocked`, or `not-applicable`; the last requires a policy-allowed reason and cannot satisfy a required check.

Define canonical hashing using a versioned JSON canonicalization contract: sorted object keys, preserved array order, UTF-8, no undefined/non-finite values. Candidate fingerprint binds mission/design, manifest, policy, head/base/integration identity and generation. Approval digest excludes mutable operational timestamps. Review bindings additionally include the exact evidence set; new contradictory evidence invalidates acceptance even if code did not change.

Fingerprints also bind delivery-unit ID and attempt ID. Receipts distinguish policy compliance, submitted-intent digest and locally reported intent authority. No attempt's receipt, acknowledgment or pending effect can satisfy another unit's gate, even when their Git SHAs happen to match.

### Delivery-unit lifecycle and whole-mission completion

Each unit follows `planned → building → reviewing → merge-ready → merge-pending → integrated → adversarial-review → closed`. Blocked/paused are overlays that preserve the underlying state. Stage-3 repairs return to building/reviewing with a new candidate attempt; recovery of a settled failed effect increments that unit's attempt generation. `merge-ready` is computed from current gates, not a worker assertion. Only live reconciliation enters `integrated`. A unit's PR binding never changes; a replacement PR gets a new unit with a supersedes link. Closed-unmerged units retain that outcome and cannot satisfy delivery criteria.

For the first version, the coordinator serializes merge-pending effects across units. It may collect parallel work, but a subsequent unit must re-read the resulting `dev` base and rerun acceptance before its merge. An unknown effect blocks subsequent integration and design amendments until reconciled. This keeps pending-state recovery single-writer without introducing a distributed scheduler.

Every criterion has an owner-approved allocation: one unit can satisfy it completely, or named units provide partial contributions and a named final unit runs the integrated criterion. A partial receipt never fulfills a criterion by itself. The final unit must verify the assembled result containing the required predecessor integrations, not merely sum their passing receipts. Unit A's integration and stage-4 record are preserved while unit B builds; B cannot overwrite A's candidate history.

Mission aggregate states are `framing`, `defending`, `active`, `closure-review`, `closed`, or `cancelled`, with blocked/paused overlays. After defense, `active` lists all unit stage-3/4 states. Enter `closure-review` only when all required units have integrated and completed stage 4, every criterion has its allocated satisfaction evidence, and no blocking finding or pending effect remains. Run whole-mission acceptance and fresh-context adversarial review against a recorded integration baseline containing all required units; record its revision and evidence. This final verification checks interactions and regressions introduced by later units. Changed closure inputs invalidate closure acceptance. A passing closure review produces `closed`; failure returns to `active` with corrective units. Cancellation is not successful closure.

One execution/review package may satisfy both a unit's stage 4 and aggregate closure when it covers the whole mission at the identical baseline, approved criteria, policy and current evidence set. The coordinator records that shared coverage explicitly; this does not permit substituting pre-integration reviews or combining partial receipts. Later integrations or changed closure inputs require fresh closure verification. A single-unit mission therefore need not repeat an identical post-delivery review merely to change the aggregate status.

Amendments preserve integrated unit records as historical evidence against their original design. Active attempts lose acceptance under the new design; the coordinator records impact on every previously integrated unit and allocates new verification or corrective units for changed criteria. Whole-mission closure uses only the current approved criteria and closure baseline. Removed criteria require an explicit owner-approved disposition; they cannot disappear from history. Later defects append follow-up findings and reopen follow-up status without erasing the original integration/closure result.

Example lineage: `REQ-04` prevent lost document edits → `AC-07` recover latest durable edit after interruption → `SL-03` recovery journal → failing restart scenario → repair commit → Mac journey receipt → `F-02` partial-write finding → repaired candidate → two reviews → independent PR receipt → reconciled `dev` commit → stage-4 regression proposal. This is illustrative, not evidence from an actual app.

## 6. Transitions, invalidation, and recovery

Retain current tool names for ordinary lifecycle use. Extend `mission_update` with versioned structured inputs; candidate/review/evidence/merge/recovery actions identify delivery-unit and attempt IDs explicitly. Only a single-unit mission may infer those IDs. `mission_status` returns aggregate and unit stages, blockers with record IDs, last verified revision, stale reasons, pending effects, worker states, and delivery versus closure state. Add deterministic verification/receipt ingestion before adding dispatch tools. Do not let model-supplied `passed: true` satisfy executable checks.

| Change | Required invalidation |
| --- | --- |
| Requirements, material design, acceptance thresholds, or security assumptions | Owner design acknowledgment and defense; dependent work marked stale; all downstream acceptance |
| Head, base, integration tree, manifest, trusted policy or recovery generation | Final receipts, reviews, presentation and merge acknowledgment; preserve old observations as historical |
| New finding, failed rerun, expired mandatory evidence or changed evidence set | Affected acceptance, both final review gates, presentation and merge acknowledgment |
| Prerequisite output/contract changes | Transitive dependent tasks stale; no promotion of late output |
| Merge mode changes | Presentation and final acknowledgment; unchanged code observations preserved |

The first release conservatively invalidates all final acceptance of the affected unit attempt on candidate changes, plus dependent active outputs and aggregate closure acceptance. Design/policy amendments invalidate all active units; integrated records remain historical, never rewritten as unmerged. Selective reuse is limited to historical guidance, not final merge approval; optimize only after dependency rules have tests.

Review 1 may produce findings and fail. Repairs create a new candidate, rerun affected and broader required checks, and require review 1 to pass on that candidate before review 2. If review 2 finds a blocker, repeat. This avoids the deadlock of trying to accept a second review after the first was invalidated by the repair.

Early reviews guide repairs. Final passing reviews bind the complete evidence set, including independent PR verification; if that run arrives after provisional reviews, renew the final reviews against the resulting evidence digest. Renewing a review requires inspecting the new evidence and its implications, not copying its former pass flag. This preserves two review gates without an endless evidence/review invalidation cycle: review records themselves are not members of the execution-evidence set.

Persist effect intent before remote mutation. Timeout/disconnect is an unknown outcome, never permission to retry. Reconcile head/base, PR state, and recorded operation first. Preserve native owner recovery and generation invalidation. Pending merge cannot migrate into ready-to-merge. Do not conflate plugin reload with process-death or cross-executor recovery proof.

An idle worker is not a successful task. A cancelled wait is not a cancelled worker. Recovery reattaches to recorded thread/run IDs when supported; ambiguous dispatch blocks new dispatch for that attempt until reconciled. A second coordinator must not acquire write ownership while the first may still be active. Cross-executor coordinator failover is deferred; initial recovery stays with the owning checkout.

## 7. Verification on local and Amp compute

Define one repository verification contract, implemented through existing entry points rather than forcing every repository into a new build system. Each check specifies stable ID, argv, working directory, target graph/scope, toolchain lock, platform requirements, timeout, output parser, artifact policy, and whether it is mandatory for each profile.

- `feedback`: narrow checks during coding; may use dirty working tree, explicitly labeled exploratory.
- `acceptance`: clean exact committed candidate, all applicable outcome/security/journey checks, platform matrix and budgets.
- `pr`: same acceptance contract on a separate clean environment and current head/base integration candidate; does not reuse the author's pass/fail artifact.

An independent PR run may use a trusted content-addressed build cache, but cannot treat an author-supplied test-result file as executed verification. Cache keys bind declared inputs, toolchain, environment, policy and platform; untrusted writers cannot poison a trusted cache namespace. Record cache hits. Critical recovery/security journeys execute fresh under policy.

### Compute and result publication boundary

Prefer disposable Amp orbs for compatible Linux workloads and isolated runner environments for native platforms. Select repositories/executors from trusted configuration, never webhook-supplied project names. Export credentials neither to candidate tests nor artifact parsers. A clean worktree alone does not isolate credentials or services.

Use the following protocol, not a claimed already-working CI bridge:

1. Trusted dispatch reads GitHub PR metadata, resolves current head/base and the protected verification policy revision, and records a unique attempt before requesting compute.
2. A restricted worker checks out exact inputs, runs the trusted verification driver against candidate code, and exports bounded reports through a supervisor-controlled channel. Candidate output is untrusted; structured text alone is not attestation.
3. The trusted result stage independently resolves execution/run identity and mandatory outcomes. Only it holds check-publication permission; it never executes candidate scripts. Missing binding means `provenance-unestablished`, not success.
4. Publish the check for the exact head, including the separately tested integration identity. Re-read live candidate and protection before merge. Strict GitHub protection plus exact-head merge remains required.

Trusted verification logic comes from an explicitly configured immutable policy revision, not candidate changes to its workflow or scripts. Record the transitive driver/actions/toolchain versions. Proposed policy updates are evaluated under the existing policy and require explicit adoption for subsequent runs. The candidate cannot weaken policy-owned thresholds or select a profile below the policy-derived floor. Mission-owned amendments follow the local snapshot/acknowledgment contract in section 4; remote checks do not authenticate that approval.

**Feasibility gate before enforcement activation:** demonstrate authenticated execution provenance, isolated candidate execution, supported Amp placement/reconnection, trustworthy result export, and authorized check publication on a disposable protected repository. Current plugin APIs do not by themselves prove that bridge. If existing credentials/API surfaces cannot provide it, retain existing PR CI as authoritative and report the missing capability; do not invent an attestation or add a new service/App silently. Any required new token scope, compute isolation or publication arrangement needs owner approval. GitHub-hosted minimal control work is acceptable; moving expensive execution is the objective.

The existing adapter requires exact-head successful check runs and App-pinned strict protection. Do not relax this to accept any synthetic merge SHA. Store head, base, tested integration SHA/tree and eventual squash commit separately. Base motion invalidates final verification. Strict checks constrain the race after final preflight; local state does not make head/base approval an atomic GitHub transaction. Merge queues, rulesets-only repos and unsupported response sizes remain blocked until separately qualified.

## 8. Supported stacks and Bazel decision

Only these implementation languages are in scope. Tool choices below are candidates to qualify and pin per repository, not a mandate to install all of them.

| Stack | Starting verification approach | Important extra evidence |
| --- | --- | --- |
| TypeScript/Bun | Frozen Bun lockfile/workspaces, type check, existing lint/tests/build, browser journeys where relevant | Workspace dependency selection, unhandled async failures, accessibility and real interaction |
| C#/.NET | Locked restore/build/test with applicable analyzers | Authorization, cancellation, migrations, concurrency and runtime platform |
| Rust | Cargo test/clippy and applicable dependency checks | Unsafe/FFI ownership, panic/cancellation boundaries, target runtime |
| Python | Locked environment, repository tests/type/lint/security tools | Async/process behavior, serialization and dependency constraints |
| Go | Go test/vet, race testing where supported, vulnerability checks | Goroutine lifecycle, cancellation, resource bounds and native bridges |
| C/C++ | Existing CMake/Ninja or qualified Bazel targets, tests/static analysis, supported sanitizers | Undefined behavior, ABI, ownership, thread and allocator boundaries |
| Swift/Objective-C | Xcode/SwiftPM build and tests on supported Apple SDK/runtime | Main-thread UI, ARC/bridging, permissions/entitlements, simulator/device and native API behavior |
| Kotlin/Java Android | Gradle build/tests/lint, emulator/device journeys | Lifecycle, permission denial/revocation, process death and UI accessibility |

Generated/binding/build metadata still needs inspection; it is not an invitation to introduce additional application languages. Cross-language tests must cover ABI layout, buffer ownership, callback lifetime, error translation, thread affinity, cancellation, and shutdown where relevant. ScreenCaptureKit-like integrations require real native permission/recovery evidence; a Linux mock cannot satisfy an Apple criterion.

For a Bun-only repository, optimize affected-workspace selection and existing test partitioning first. Benchmark cold, warm, no-op, leaf edit, shared-package edit, and cache-miss runs on the same machine and revisions. Include setup, cache transfer, orchestration, correctness of invalidation, and maintenance cost; report medians, tail latency and sample sizes. Adopt Bazel only if the measured end-to-end gain meets the repository's agreed threshold without coverage loss. Do not treat Starlark configuration as a new product-language requirement.

For a Pages-like app, graph coordination may help Rust/Go/native/UI components, but Xcode/device flows and interactive permission tests remain platform-native. A prior read of `agentic-ayudha` found Go plus pnpm/Node tooling; it is a motivating example, not evidence for migrating that repository to Bun or Bazel. No benchmarks have been run for either example in this design task.

## 9. Guide, Hunter, and Remediation roles

### Complement native Amp capabilities; do not replace them

Mission-control adds approved intent, dependency readiness, traceability, evidence freshness and delivery gates around Amp's existing capabilities. It must not recreate Amp's agent runtime, model router, repository research, specialist reasoning, thread management, confirmations or execution infrastructure. Guide, Hunter and Remediation are workflow responsibilities, not requirements to install three competing agent implementations.

| Available native capability | Mission use | What the mission layer adds |
| --- | --- | --- |
| Librarian / repository-research capability | Investigate external repositories, dependencies and established implementations during expectations, defense or diagnosis | Scoped research question, source/version references and linked decisions; research remains reported evidence, not executed verification |
| Oracle / specialist reasoning and review capability | Resolve consequential architecture uncertainty and challenge designs or repairs | Exact input revision, unresolved question, findings and disposition; an Oracle response is not owner approval or a test receipt |
| Finder / code-search capability | Locate ownership, callers, contracts and relevant tests when broad exploration is justified | Relevant locations and revision references; use direct search for simple known symbols rather than mandatory delegation |
| Native scoped subagents and persistent threads | Bounded independent work, fresh-context review, or separately owned tasks | Task IDs, prerequisites, write ownership, accepted outputs and attempt reconciliation |
| Native tools, skills, confirmations and executor placement | Implement, run checks, inspect artifacts, obtain human decisions and use qualified local/orb/runner environments | Criterion bindings, provenance classification and explicit gate status |

Discover the capabilities actually exposed by the current Amp version and mode. These names describe responsibilities, not hard-coded tool names or guaranteed plugin APIs. Use native specialist surfaces when available and permitted; otherwise use supported scoped delegation or work directly, reporting material capability gaps. Do not silently create a lookalike specialist or assume `ctx.tools.call` can invoke subagents. Preserve Amp's automatic routing unless an explicitly approved mode constrains it; discover supported options before any model pinning.

Do not call every specialist at every gate. Use Librarian when external source research is needed and Oracle when consequential reasoning remains unresolved or independent review is required. A worker's identity, supplied context and actual evidence determine review independence—not the specialist's name. Mission-control records returned findings and verifies outputs; it does not equate specialist agreement with correctness. Missing required independent review blocks that gate rather than relabeling the implementer's self-review.

Before introducing a new tool, agent or adapter, the implementation plan must identify the unmet contract and why an existing native surface cannot satisfy it. Native capability mapping is checked during qualification, including unavailable-specialist behavior, preservation of routing/permissions, and the prohibition on converting specialist prose into execution evidence. This is a design constraint, not authorization for additional delegation or infrastructure changes.

**Guide/Verify:** assemble bounded context from current code/contracts, applicable guidance, decisions, dependency/license policy and existing findings. Record source revision and invalidate on relevant changes. Prefer existing navigation/tooling over introducing a second repository index. Guide makes constraints available; executable checks enforce the subset that can be checked.

**Hunter:** read-only by default. Derive threat model, identify entry points/assets/trust boundaries, examine access control, workflow abuse, sessions, resource exhaustion and relevant native boundaries, then consolidate findings with exact locations and counter-evidence. Run local reproduction only in an authorized disposable harness. Label source-supported findings honestly. Never mark an untested hypothesis confirmed merely because several agents agree.

**Remediation:** consume substantiated finding IDs and authorized scope; reproduce the failure, add outcome regression, minimally repair, rerun original reproduction and broader contract, publish reviewable output. It cannot approve its own consequential repair or alter policy to make failures disappear. Findings close only with repair evidence and independent review, or a specific authorized disposition with reason, expiry and follow-up owner. Critical safety/security requirements cannot be waived by the worker.

Budget limits cover elapsed time, attempts, compute and tool/model spend. Exhaustion produces `blocked`/`needs-owner` with partial results, never `passed`. Do not create a separate specialized agent for trivial tasks; roles may be sequential actions in one thread except when review independence is required.

## 10. Dependency-aware coordination (after traceability)

Represent a DAG of tasks and accepted outputs within the mission. Validate unknown dependencies, cycles and conflicting ownership before dispatch. A task is ready only when every prerequisite output is accepted at its current revision, required executor capabilities are available, write/resource scopes do not conflict, and budget is available.

Start with at most two concurrent workers unless the approved mission budget specifies otherwise. Independent research/review can run concurrently; writers get separate worktrees with explicit ownership. Shared lockfiles, generated interfaces, schemas, test fixtures, simulators and ports count as conflicts even when source paths differ. Unknown overlap serializes work. No worker merges or publishes without the mission's authorization.

Task states: `planned → ready → dispatch-pending → running → submitted → accepted`. Side states: `blocked`, `failed`, `cancel-requested`, `cancelled`, `stale`. Coordinator validates actual output and tests before `accepted`; worker self-report only yields `submitted`.

Handoff includes repository, commit and accessible transfer reference, input revision, contract digest, criteria covered, changed paths, evidence, open findings and limitations. Sending a commit SHA does not transfer an unpushed commit. Orb/local workspaces require explicit supported file/commit transfer and checkout verification. Assemble accepted outputs in a dedicated integration worktree and rerun integrated acceptance.

On prerequisite changes, mark transitive outputs stale and request cancellation where useful. Preserve late output without promoting it. Cancellation does not roll back writes or external effects. Retry only after the previous attempt's state is reconciled. Persist attempt ID before dispatch; an uncertain thread-creation response must not spawn duplicates blindly.

API evidence: installed Amp `0.0.1793390435-g08e9ec` exposes `createAgent`, `getBuiltinAgent`, `run`, `createThread`, `parentThreadID`, `appendUserMessage`, state observation, `waitForResponse`, and `cancel`. `ctx.tools.call` excludes subagent tools/durable waits. Prefer normal native routing; do not pin models without capability discovery. Persistent thread dispatch, cross-executor transfer, cancellation races and recovery require live qualification before DAG activation. No unattended wake-up or exactly-once dispatch guarantee is inferred from API signatures.

## 11. Adversarial learning without automatic drift

The fresh reviewer receives the approved package, exact integrated revision and evidence, not the designer's conclusions. First reconstruct intent; then challenge assumptions and inspect drift between the manifest, code, tests and user journeys. Familiarity is not proof and fresh context is not proof of correctness.

Learning records distinguish a defect in code, a missing oracle/test, an ambiguous requirement, a tool limitation, and a workflow failure. Prefer a narrow regression test over a broad new rule. Evaluate proposed guidance against the incident and held-out cases, including a benign control that should remain allowed. Measure missed defects, false positives, verification time and human effort. Accept only improvements with justified benefit; rejected proposals remain traceable. Changing a shared skill follows its own reviewed change and publication process.

UX/value evidence follows the actual product: representative happy, empty, error, interruption and recovery states; keyboard/accessibility where relevant; latency and data preservation; explicit judgment of whether the journey reduces waiting, lost work, cost or uncertainty. Screenshots illustrate appearance; exercised interaction and observable state verify behavior. This is a scoped acceptance plan, not a claim that a checklist guarantees excellent UX.

## 12. Migration, rollout, and rollback

Retain v1 reading. Preserve original bytes and a migration mapping before writing v2; assign stable criterion IDs once. Imported prose remains `reported`, not independently verified. Historical completed missions remain readable with their original guarantees. For active missions, collect missing v2 evidence before stronger gates can pass; do not manufacture approvals or reviewer identities.

Map a v1 mission to one v2 delivery unit and one imported attempt with its original PR, candidate, generation, reviews, evidence and effect state. If it has no PR yet, the unit remains planned/unbound. V1 `merged` maps to historically integrated, with stage 4 and whole-mission closure `not-evaluated`; it does not fabricate a passed post-delivery gate. Historical v1 completion remains explicitly labeled under v1 semantics. New work under v2 must fulfill v2 gates. Imported mission criteria have mission/local-reported authority; no policy authority is inferred from their wording.

Pending effects reconcile under original semantics before migration changes their lifecycle. If remote outcome is unknown, preserve the state and block. Unknown future schemas fail closed without rewriting files. Rollback stops new v2 dispatch/enforcement while retaining a v2-capable read/reconcile path; installing an old binary cannot safely rewrite v2 records. Never roll back by weakening remote protection.

Delivery order and module ownership:

1. **Traceability foundation:** versioned contracts, IDs, invalidation, migration and status in `lib/mission.ts` and `index.ts`; committed manifest schema and validation. Exit: complete lineage and stale-evidence regression tests with v1 preservation.
2. **Verification and enforcement:** receipt adapters and trusted-policy contract, GitHub provenance resolution in `lib/github.ts`, independent verification workflow design. Extend existing tests/docs. Exit: disposable-repository adversarial trial plus approved infrastructure feasibility gate.
3. **Every-PR activation:** shadow report all PRs, classify false blocks/missing evidence, then explicitly authorize required-check configuration. Compact records use trusted classification. No label or candidate-selected exemption can bypass the check.
4. **Coordination:** minimal DAG/native dispatch with durable attempt records and integration checks. Exit: serial-versus-parallel trial improves accepted-outcome time without worse defects or human burden.
5. **Learning/maintenance:** stage-4 records and evaluated improvement proposals; optional scheduled missions only after explicit opt-in. Update delivering/grilling/crafting guidance in their owning packages as needed, not during this design-only task.

These are separately reviewable implementation slices, not a commitment to one large code change. Shared infrastructure and publication approvals remain separate from code readiness.

## 13. Qualification cases and success measures

| Adversarial input | Required observable result |
| --- | --- |
| Reordered criteria or split tasks | IDs/lineage remain valid; no positional reassignment of evidence |
| Missing design acknowledgment or defense | Build transition rejected; state unchanged |
| Candidate weakens a mission criterion without local amendment | Local snapshot comparison blocks; remote receipt explicitly does not claim authenticated intent approval |
| Owner approves a mission amendment that lowers a policy-mandatory threshold | Local approval does not override policy; independent check rejects |
| First of two PRs integrates | Only its unit enters stage 4; second unit stays active; mission cannot close |
| Second PR regresses a criterion previously fulfilled by the first | Whole-mission acceptance fails on the final assembled baseline; earlier integration evidence is retained |
| Receipt or recovery action names another unit/attempt | Reject without mutating either unit |
| Amendment after partial integration or v1 merged import | Preserve original delivery record; explicitly allocate revalidation and do not fabricate stage-4 completion |
| PR replaces validator with unconditional success | Trusted prior policy still runs; proposed policy change visible |
| Correct check name/wrong App, correct App/wrong workflow, unrelated run or stale attempt | Receipt rejected, exact reason reported |
| Skipped mandatory step, failed dependency, malformed/oversized report | No successful final verification |
| Forged report written by candidate code | Not promoted to independently verified provenance |
| Head/base moves, evidence changes, new blocker appears | Acceptance/reviews/approval stale before merge |
| Wrong synthetic merge relationship | Reject even if its tests passed |
| Cache omits shared dependency or trusts untrusted writer | Qualification fails; cache disabled until corrected |
| Runtime journey unavailable on required native platform | Criterion blocked, not replaced with Linux mock evidence |
| DAG cycle, overlapping writes, stale prerequisite, late cancelled output | No unsafe dispatch or output promotion |
| Crash after dispatch/merge intent or lost response | Reconcile before retry; no duplicate mutation by inference |
| Repair budget exhausted | Finding remains open and escalation names remaining work |
| v1 pending migration / unknown schema / rollback | No state loss, approval fabrication or mutation replay |
| Stage-4 proposed rule rejects benign control | Learning proposal rejected or narrowed, not auto-published |

Keep permanent tests at public transition/adapter contracts. Use real disposable Git/GitHub/native journeys to qualify external behavior; mocks alone cannot pass the activation gate. Record independently derived expected outcomes, before/after evidence and untested cases. Include actual process death around effects, not only reload; do not claim cross-platform/multiplayer support until exercised.

Measure criterion-to-receipt coverage, false acceptance/rejection, escaped defects/reverts, first independent verification pass rate, recovery success, time/cost per accepted outcome, human review minutes, stale-work waste, and user-journey acceptance. Compare like-for-like cases with sample sizes. Traceability success means every applicable criterion resolves to current evidence or an explicit blocking gap; no seeded false-green scenario is accepted. Speed improvements must not come from dropping checks.

## 14. Review and implementation boundary

The proposed contracts, four gates, baseline migration, and trust boundaries are ready for technical review. Before writing the enforcement/compute implementation plan, resolve its feasibility gate with a bounded approved prototype; no asserted trusted CI replacement is shipped on documentation alone. Agent coordination and language adapters activate only after their respective qualification cases pass.

This document changes no executable behavior. Existing v0.2.0 installation, CI, protection, runners and release branches are unchanged. Approval of this specification would authorize planning the implementation slices, not implicitly changing shared infrastructure or publishing extensions.

## References

- [R1] Parallel Task pro research, completed 2026-10-31: https://platform.parallel.ai/view/task-run/trun_8ed7a8c7a37043b48fc8d5ef9556ffa8 . Findings cross-checked against the primary sources below; recommendations are not product guarantees.
- [R2] Sonar Vortex: https://docs.sonarsource.com/agent-centric-development-cycle/inside-your-agent-the-agentic-loop/sonar-vortex.md
- [R3] Remediation: https://docs.sonarsource.com/agent-centric-development-cycle/in-your-long-living-branches-the-code-maintenance-loop/remediation-agent.md
- [R4] Hunter: https://docs.sonarsource.com/agent-centric-development-cycle/in-your-long-living-branches-the-code-maintenance-loop/hunter-agent.md
- [R5] Google EGM original announcement (2026-10-22): https://opensource.googleblog.com/2026/10/introducing-elephant-goldfish-model-plugin.html ; https://github.com/google/elephant-goldfish-model
- [R6] Amp API: https://ampcode.com/docs/plugin-api ; installed CLI `amp plugins show-docs` inspected 2026-10-31. Deployment constraints: https://ampcode.com/docs/cli/runners and https://ampcode.com/docs/orbs . API declarations are not live qualification.
- [R7] GitHub required checks: https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks ; protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches ; untrusted execution: https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target . These references informed the deep research; target repository configuration must still be verified live.
- [R8] Bazel build-system rationale: https://bazel.build/basics/build-systems . No repository-specific speed benchmark was performed.

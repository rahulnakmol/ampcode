# Mission control: local workflow and protected dev integration

For the user journey, start with [Mission-driven development](mission-driven-development.md)
or [Using the skills](using-skills.md). This reference covers kickoff variants,
coordinator setup, tool inputs and operational limits.

`plugins/mission-control/index.ts` coordinates the delivering skill. It is a local
workflow coordinator, **not a scheduler or security sandbox**. It uses existing
GitHub credentials available to `gh` in the Amp execution environment. No custom
controller, GitHub App, approval service, or plugin policy configuration is needed.
Local approval/evidence gates and GitHub's required CI/protection both must pass.

**V1 remains the default. V2 is an explicit, local/shadow traceability workflow.**
V2 records intent snapshots, per-PR attempts, revision/evidence-bound reviews and
post-delivery reports. It cannot request a remote merge or claim qualified closure.
Every v2 status includes `remote-verification-unqualified`. Reported findings,
reviews and test results are not execution receipts. The sections below describe
v1 integration unless marked v2; opting in does not strengthen GitHub protection.

## Ways to kick off a mission

Paste these prompts into an Amp conversation in the target project. Replace bracketed
placeholders with your details. The same prompts work in the web conversation or an
interactive Amp CLI session; they are **not shell commands or registered slash commands**.
You do not need to type tool calls yourself. Amp loads the skills and calls the installed
coordinator tools. A mode selection alone does not start a mission.

Before starting, check these prerequisites:

- `delivering` and `grilling` are available; use `crafting` for relevant UX and interaction
  design. `mission-control` is a separate plugin, not part of the skill installation.
- The execution environment has the target repository and an isolated worktree. Start the
  coordinator with that worktree as the **workspace root**, not its parent directory. An
  `amp` CLI session launched from the worktree is one way to open it. If the current thread
  cannot change workspace roots, continue in a thread opened at the correct root; do not
  patch the plugin to redirect production mission state.
- For v1 integration, the repository has `dev`, working required CI, supported strict
  App-pinned protection, and existing `gh` access. Missing prerequisites block integration;
  creating credentials or changing protection needs separate permission.
- Choose the delivery destination and work budget. Commit/PR/dev authorization is distinct
  from rolling, stable release, deployment and Personal publication. The examples below do
  not grant spending or infrastructure access beyond what you explicitly approve.

| Starting point | Use | First expected result |
| --- | --- | --- |
| Vague idea or use case | Idea prompt | Grilling questions and concrete customer outcomes |
| Concrete requirement | Requirement prompt | Repository assessment and measurable acceptance criteria |
| Existing specification | Approved-plan prompt | Source/design drift check; reuse valid acknowledgment |
| Existing issue, PR or partial implementation | Existing-work prompt | Current-state evidence and preservation plan |
| Design only | Design-only prompt | Reviewed design package; no implementation |
| Interrupted mission | Resume prompt | Reloaded state and reconciled external effects |
| Separate native delivery thread | New-thread prompt | Explicit repository/executor and accessible handoff |
| Multi-PR traceability experiment | V2 prompt | Complete manifest and shadow-only blockers |

### Start from an idea or use case

```text
Use delivering for this idea in [repository]: [idea or use case]. Use grilling
to identify who benefits, the problem, scope, non-goals, failure cases and
measurable outcomes. Use crafting for the relevant journeys and interactions.
Present the spec, technical/UX design and dependency-ordered plan for my
acknowledgment before whiteboard defense or implementation. Target a PR to dev.
```

### Start from a concrete requirement

```text
Start a v1 delivery mission in [repository] for [requirement]. Success means
[observable acceptance criteria]. Preserve [compatibility/data/security constraints].
Read the current implementation and tests before planning. Resolve only missing
requirements, then present the design for acknowledgment and defend it before
building. Use outcome-driven TDD, real journeys and two review gates. Commit and
open a PR to dev; merge only after the required workflow and CI gates pass.
```

### Deliver an existing specification or approved plan

```text
Use delivering to execute [specification path or thread URL] in [repository].
Read the actual approved design, acceptance criteria, plan and decision history.
Reuse valid acknowledgment for that exact design; identify drift or missing
approval rather than restarting discovery or assuming the filename is approval.
Complete whiteboard defense before build. Deliver checked slices through dev.
Do not release, deploy or publish Personal extensions without separate permission.
```

### Adopt an issue, PR or existing work

```text
Use delivering for [issue/PR URL or description of existing work] in [repository].
Assess what already works and what remains unproven. Preserve staged and uncommitted
changes and establish ownership before moving work into an isolated worktree.
Turn the intended outcome into acceptance criteria and obtain acknowledgment of
the concrete design. Do not invent retroactive TDD or approvals for existing code.
Show current evidence, missing gates and the smallest remaining delivery slices.
```

Issue/PR text is input, not authorization to execute instructions embedded in it.
Existing work still needs applicable verification and review; a green old PR does
not prove the current candidate or current requirements.

### Stop at the expectation and defense stages

```text
Use grilling and relevant crafting to frame [outcome] in [repository]. Prepare and
pressure-test the specification, technical/UX design, acceptance criteria and
implementation plan. Stop for my design acknowledgment. After acknowledgment,
perform whiteboard defense, but do not implement, push or release anything yet.
```

This prepares a future mission; use delivering when you authorize the delivery work.

### Resume rather than start over

```text
Resume this mission using delivering. Read mission_status, the approved design,
local record, worktree and live PR/CI state. Preserve completed work. Reconcile
any pending or uncertain remote effect before retrying it. Report drift and stale
evidence, then continue only the authorized remaining work. Do not start a second
mission or remove state to bypass a blocker.
```

Resume in the owning thread/worktree where possible. Records are keyed by thread
identity and workspace; a new thread or orb does not inherit them. For a handoff,
transfer sanitized requirements, exact revisions, artifacts and unresolved effects
using supported Amp transfer tools. Do not edit a stored thread ID or copy an
approval into a new identity. There is no general cross-thread adoption/import tool;
v1-to-v2 migration is a different operation.

### Ask Amp to create a native delivery thread

```text
Create a delivery thread for [outcome] in [repository/project], using delivering.
Use [an orb for the remote revision / the named runner and checkout for local work].
Carry this scope and these constraints into its first prompt: [brief]. If it needs
unpushed work, transfer and verify the exact files/commit rather than assuming the
thread can see them. Have it present the design for owner acknowledgment before
defense/build. Keep integration and release permissions explicit.
```

This is a request for Amp's native thread capability, not a `mission-control`
thread launcher. Use an existing suitable thread instead when it already owns the
work. Orbs cannot see a runner's uncommitted files merely because you name a path.

### Request bounded subagent help

Append this to an implementation prompt when you want explicit delegation:

```text
Use native subagents for bounded independent work and consequential reviews.
Sequence tasks that depend on earlier outputs. Parallelize only independent tasks
with distinct file ownership and explicit contracts; integrate and test their
combined result before accepting it. Keep one integration owner accountable.
Use available native Finder/Librarian/Oracle responsibilities rather than adding
replacement runtimes or assuming a named tool exists in every mode.
```

The coordinator does **not** implement a dependency scheduler or automatically
launch those agents. The integration agent reasons about dependencies using the
native tools actually available. A subagent report is evidence to inspect, not a
substitute for checks on the assembled result.

### Opt into v2 traceability, without enabling merges

```text
Start a fresh v2 shadow mission for [outcome] in [repository]. Use delivering and
grilling to prepare a complete manifest with stable requirement/criterion IDs,
slices, per-PR delivery units and final criterion allocations. Start with explicit
schemaVersion:2, then request native acknowledgment of the exact manifest before
defense/build. Label reports and policy authority honestly. Do not enable remote
merges, downgrade to v1 to bypass a blocker, or claim qualified closure.
```

Use the [complete manifest example](#opt-in-v2-traceability). V2 is not “v1 with
stronger merge permissions”: `remote-verification-unqualified` is expected. Its
read-only reconciliation can observe separately authorized integration but cannot
manufacture missing earlier gates. Keep ordinary protected integration on v1 when
you need the coordinator to request a merge.

For an **existing v1** record, migration needs its own informed decision:

```text
Preview this mission's v1-to-v2 migration without writing. Show preserved history,
missing v2 intent details and the loss of v1 merge capability for this record.
Reconcile pending effects first. Do not adopt until I acknowledge the migration
in the native owner dialog; request v2 design acknowledgment separately afterward.
```

### Choose merge and release boundaries explicitly

For v1, append “Use ask-before-merge mode” to request `mission_merge_mode({mode:"ask"})`.
The owner confirms that preference in the native dialog. Automatic low/medium-risk
integration still requires authorization and passing gates; high-risk exact-candidate
acknowledgment remains mandatory in either mode. V2 has no merge-mode override.

If a complete release is intended, specify it rather than assuming “deliver” includes it:

```text
The delivery target is [dev integration only / rolling snapshot / stable release].
For this mission I authorize [commits, feature push, PR and gated dev merge].
I additionally authorize [specific rolling/stable release, deployment destination
or Personal publication, if intended]. Follow dev → rolling → main and all
applicable gates. Use a work budget of [limit]; disclose unavailable usage telemetry.
Do not change shared infrastructure, access or credentials without specific approval.
```

Remove alternatives you do not authorize. A broad request does not fabricate the
native exact-design or high-risk final-candidate receipt. In those dialogs type
**ACKNOWLEDGE**, never a password or key.

### What should happen after kickoff

The four stages are **expectations → acknowledged design and whiteboard defense →
build/delivery with two reviews → adversarial review and learning**. The first reply
should establish the repository/executor, outcome, missing decisions, budget and
delivery boundary—not begin coding an unacknowledged design. Reuse an unchanged
approved package; reopen affected decisions when intent changes. After integration,
inspect the assembled outcome, retain findings and lessons, and propose any corrective
work. Do not publish shared-skill learning automatically or call integration proof of
post-delivery closure.

Common blockers and safe responses:

| Observation | Response |
| --- | --- |
| Skill or coordinator unavailable | Ask Amp to reload installed skills/plugins; missing installation needs explicit destination/approval. Guidance-only fallback has no plugin-enforced state |
| Wrong workspace root | Open the isolated Git worktree as the workspace before starting |
| “Mission already exists” | Use `mission_status` and resume; use a fresh thread for a genuinely new mission |
| Owner acknowledgment absent | Leave state blocked; reopen the native dialog on the owner's request |
| Missing CI/protection/access | Resolve the prerequisite with appropriate authorization; never bypass it |
| Pending merge or uncertain result | Reconcile first; do not blindly repeat the mutation |
| V2 unqualified verification | Preserve the blocker; this release cannot activate trusted remote enforcement |

## Tool-level start examples

These are **agent tool calls**, not commands for your terminal. Start only once in
the correct workspace/thread. For v1, the actual input is an object:

```json
{"requirements":"Recover the latest durable document edit after interruption; preserve existing files."}
```

Pass it to `mission_start`. For v2, pass `{"schemaVersion":2,"manifest":...}` with
the complete manifest below, and omit top-level `requirements`. To resume, call
`mission_status()` rather than `mission_start` again. Public tools do not accept
agent-supplied owner approval; use `mission_approve({stage:"design"})` after the
design is presented. The agent records defense and build only after that succeeds.

## The agreement

1. Start from the user's software requirements; use grilling to produce concrete
   acceptance criteria, scope, and non-goals.
2. Produce the spec, dependency-ordered plan, technical design, and crafting UX
   design where relevant. Record why UX design is inapplicable otherwise.
3. Obtain the initiating owner's acknowledgment of that exact bundle.
4. Defend it at the whiteboard, including alternatives, invariants, threats,
   failure/recovery boundaries, and the implementer's teach-back.
5. Build small outcome-driven TDD slices. Run real journeys, inspect artifacts,
   conduct two distinct review gates, repair/revalidate, and assess customer value.
6. Show what changed, where, the evidence and limitations, and how to try it.
7. Integrate into `dev` only after local gates, exact-candidate CI and branch protection pass.

Low/medium risk defaults to automatic merge without a response or waiting timer.
At build entry the owner can choose ask-before-merge. High risk always requires
owner acknowledgment of the final candidate; unknown risk blocks. Changing the
design reopens acknowledgment and defense; changing head/base invalidates reviews
and evidence. Changing merge preference invalidates presentation and final
acknowledgment, but preserves code-review evidence.

## Install and exercise the coordinator

Copy the **whole** `plugins/mission-control/` directory into an authorized Amp plugin
location. Source integration does not publish it to Personal Plugins. Install
`delivering`, `grilling`, and applicable `crafting` separately through their skill
destination. Do not silently install missing dependencies.

Open the dedicated Git worktree root. Start with `mission_start({requirements: "..."})`;
unrelated conversations do not become missions. The tool adds `/.amp/in/` to the
repository-local exclude file, preserving existing rules, and stores records at
`.amp/in/missions/<thread-hash>/state.json`. Do not commit these operational records.

| Tool | Purpose |
| --- | --- |
| `mission_start` | Save original requirements; begin framing |
| `mission_update` | Save design, defense, build, candidate, review, evidence, pause/resume |
| `mission_status` | Reload records, revision fingerprint and blockers |
| `mission_approve` | Owner-restricted design or final-candidate acknowledgment |
| `mission_merge_mode` | Owner-restricted auto/ask preference override |
| `mission_present` | Show the evidence packet in Amp before integration |
| `mission_merge` | Validate required CI/protection, persist pending state, request immediate exact-head squash merge |
| `mission_reconcile` | Read remote integration state without repeating the mutation |
| `mission_recover` | Owner-acknowledged recovery of a settled, unqueued attempt; revalidate before retry |

Use actual text in the design bundle, not a mutable filename standing in for its
contents. Criteria and result entries correspond by array position. Evidence
entries must contain implementation locations, observed outcomes, commands and
artifact references, including limitations. The plugin checks lifecycle and
completeness; it does not infer whether arbitrary prose is true. Publish the
evidence on the PR as well: `mission_present` displays it in Amp, not GitHub.

The installed API cannot authenticate an arbitrary multiplayer mission initiator.
Version one requires the initiator to be the thread owner, or the owner explicitly
to adopt the mission. The confirmation has a masked `secret: true` text field
because the API documents that field as owner-only. Type **ACKNOWLEDGE**, never a
password, key, or other secret. An ordinary `requireHuman` dialog is not owner-only.
No responder ID is returned or invented. These local acknowledgments are useful
workflow records, not externally verifiable authentication receipts.

## GitHub prerequisites and the workflow boundary

Use the existing Amp environment's GitHub authentication through `gh`; do not
create or copy credentials into mission records or introduce an App credential.
The account needs to read PRs, branch protection and check runs, and request the
authorized merge. If that access is unavailable, report the capability gap.

- Protect `dev`, require PRs, enable strict up-to-date required checks and
  administrator enforcement, and leave PR review bypass allowances empty.
- Pin every required CI check to its actual source App in **branch protection**
  (GitHub Actions uses App ID `15368`). The adapter reads those requirements from
  GitHub, not a local policy setting or a hard-coded check name/App allowlist.
- Each required check must be completed successfully on the recorded head. The
  PR must still target the recorded `dev` base/head; preflight reads it twice.
- Keep design acknowledgment, two revision-bound reviews, acceptance evidence,
  presentation and high-risk/ask acknowledgment in the local mission workflow.
  Risk classification and evidence truth remain the implementer/reviewers'
  responsibility; the plugin validates records, not arbitrary prose or code semantics.

The user accepts local workflow enforcement, not protection from a hostile shell.
An unrestricted executor can edit local records or invoke GitHub outside these
tools; GitHub does not authenticate the local mission approvals or reviews.
Do not bypass the workflow, weaken protection, or use administrator overrides.
Configuring CI/protection or changing repository access requires separate approval
and is not performed by loading this plugin. Missing protection or failing CI
still blocks integration; no custom external service is required.

The current GitHub adapter supports REST branch protection, not rulesets-only
repositories, merge queues, legacy commit-status contexts, or more than 100
check runs. It blocks unsupported/incomplete responses rather than guessing.
It refuses unpinned checks, skipped/neutral checks, review bypass allowances,
missing admin enforcement, and head/base motion during preflight. GitHub's strict
checks and exact-head merge precondition govern the race after the final read;
local approval is not an atomic remote approval of a base that moves afterward.

Automatic mission integration does **not** enable GitHub's persistent auto-merge.
The adapter requests an immediate merge with `--match-head-commit`; if remote gates
are no longer satisfied, it fails rather than authorizing a later head. Reconcile
the result and revalidate before recovery/retry. Never add `--auto` as a shortcut.

## Recovery and limits

Atomic replacement, file fsync, an exclusive lock, and stale-revision checks
protect ordinary local updates. This is not a distributed transaction or
tamper-resistant audit log. A leftover lock after process death deliberately
blocks writes: verify no writer is running, preserve state/lock evidence, and
remove only the stale lock with operator authorization. Never delete the mission
record to manufacture a clean state.

Pending state is saved **before** requesting merge. A timeout, cancellation or
restart may leave an unknown outcome. Reconcile GitHub first; never blindly issue
the mutation again. If the request never reached GitHub, the current coordinator
keeps that pending state for operator investigation rather than automatic retry.
After the owner confirms all prior senders have settled, `mission_recover` checks
an open, unmerged, unqueued PR before and after owner acknowledgment. It starts a
new recovery generation and clears reviews, evidence and merge approval without
sending another merge. Register any changed head/base and revalidate; renew
local acknowledgment where required for the new generation. A live queue, absent remote fields,
moving candidate or active local request blocks recovery. This does not prove
that another executor has stopped; that remains part of the owner's investigation.
A queued request is not delivery. A closed-unmerged or changed PR is not success.

Session opening exposes persisted state; it does not replay interrupted dialogs.
An active build can request at most three continuation turns, stopping on pause,
approval waits, cancellation, errors or completed integration. This does not wake
an offline runner or promise unattended completion after the continuation budget.
Use Amp's authorized exact-head CI/PR event subscriptions for follow-up; this
plugin does not provision an external daemon or subscriptions itself.

The local tools reject out-of-order transitions. They cannot prevent an agent
with unrestricted shell from editing code before approval or bypassing local
files. True isolation would require a separate security design and host permissions;
it is not the boundary promised by this coordinator.
No production-scale reliability, native cross-platform approval-dialog behavior,
or live protected-merge proof follows merely from the local test suite.

## Verification

Run `make check`. Mission tests exercise persisted lifecycle and corruption,
owner-dialog contracts with cancellation/stale updates, revision invalidation,
local risk/approval decisions, and GitHub preflight/merge behavior through controlled
transport. Amp CLI plugin loading is also part of the repository check.
Local Git/filesystem journeys are real; controlled GitHub/UI adapters are not a
live GitHub integration or a multiplayer identity test. Before activation, run
an authorized disposable protected-repository trial with existing GitHub access,
including spoofed checks, stale approvals, changed bases, failures and recovery.

Rolling promotion, stable release, deployment, access changes and Personal
extension publication retain their own explicit gates.

## Opt-in v2 traceability

Use `mission_start({schemaVersion:2, manifest: ...})` in a fresh mission. Do not also
supply top-level `requirements`: v2 requirements belong in the manifest. There is
no automatic migration or repository-wide activation. Native Finder/Librarian/Oracle,
subagents, routing and thread execution remain Amp responsibilities. This plugin
adds no specialist wrappers, model pins, scheduler, DAG dispatcher or Sonar dependency.

The manifest is bounded JSON data, not an executable policy. Its contract lives in
`plugins/mission-control/lib/contracts.ts` (`parseManifest` is the runtime authority):

```json
{
  "schemaVersion": 2,
  "missionId": "M-1",
  "repository": "acme/app",
  "requirements": [{"id":"R-1","need":"Recover edits","scope":"Local documents","nonGoals":"Cloud sync"}],
  "criteria": [{"id":"C-1","requirementIds":["R-1"],"outcome":"Recover after interruption","authority":"mission","method":"journey","checks":["recovery"],"threshold":"Latest durable edit survives"}],
  "decisions": [],
  "slices": [{"id":"S-1","criterionIds":["C-1"],"paths":["src/recovery.ts"]}],
  "deliveries": [{"id":"U-1","sliceIds":["S-1"],"criterionIds":["C-1"]}],
  "allocations": [{"criterionId":"C-1","contributors":["U-1"],"finalUnitId":"U-1"}]
}
```

IDs are explicit and unique. References must resolve. Object-key order does not
change a digest; array order does. Limits are 1 MiB per manifest, 1,000 items per
collection, 16 KiB per prose field, 1,000 events and 16 MiB per persisted mission.
Unsafe paths, unknown fields/enums/schemas and malformed projections are rejected.
Do not put secrets or private payloads in any record.

The four stages have distinct records and gates:

| Stage | Input and transition | Foundation exit/limitation |
| --- | --- | --- |
| Expectations | `design {manifest}`, then native `mission_approve({stage:"design"})` | Exact local snapshot acknowledged; remote intent authority remains `local-reported` |
| Whiteboard defense | `defense {digest,record}` using current `designDigest` | Current acknowledged design explained before `build {unitId}` |
| Build/delivery | Candidate, reports, findings, two reviews per unit/attempt | Local traceability only. `mission_merge`, merge approval/mode and recovery reject before effects |
| Adversarial learning | Read-only integration observation, post-delivery and whole-mission packages | Reports retained; qualified post-delivery/aggregate closure remains blocked |

Every PR is an immutable delivery-unit binding. Replacement PRs require a new unit.
Candidate attempts retain old reports and reviews. Use explicit `unitId` and
`attemptId` even for a single unit, so changing to multiple units does not change
the meaning of earlier calls. `mission_status.current` supplies the exact current
`fingerprint` and `evidenceDigest` for each attempt. Unknown risk blocks; a unit
that has been high risk cannot lower its floor by registering another candidate.

`mission_update` accepts these additional v2 actions (each object includes `type`):

- `candidate`: `unitId`, fresh `attemptId`, `candidate` with `repo`, positive `pr`,
  full `head`/`base` Git SHAs and `risk`, plus the complete candidate `manifest`.
  The manifest must match the retained acknowledged snapshot, not a caller-supplied
  approval hash.
- `report`: `unitId`, `attemptId`, `fingerprint`, `evidence` containing `id`,
  `criterionIds`, `outcome` (`passed`, `failed`, `blocked`) and `record`.
  The coordinator assigns `producer: reported`; callers cannot supply a producer.
- `review`: `unitId`, `attemptId`, `gate` (1 or 2), `fingerprint`, `evidenceDigest`,
  `reviewer`, boolean `passed`, `record`, and `findingIds` (possibly empty).
  New evidence/findings invalidate old review acceptance. Gate two requires a
  passing gate one for the same evidence. A failed review requires a new attempt.
  High-risk self-review is refused; reviewer names are reported identities, not
  cryptographic proof of independent execution.
- `finding`: `unitId`, `attemptId`, `fingerprint`, `finding` containing `id`,
  `criterionIds`, `severity` (`low`, `medium`, `high`, `critical`), `confidence`
  (`hypothesis`, `source-supported`, `runtime-reproduced`), `location`, `record`,
  and `owner`. Even `runtime-reproduced` is a reported claim without a receipt.
- `pause {reason}` and `resume` preserve the underlying state/history.
- `post-report {evidence}` records fresh reported results after integration.
  Evidence contains `id`, `baseline`, `designDigest`, `policyDigest`, `unitIds`,
  `results` and `record`. The coordinator binds it to observed unit integrations
  and records its sequence, `producer: reported`, and `baselineInclusion: unverified`.
- `post-delivery {unitId,package}` and `closure-report {package}` use the package
  contract below. Neither can assert qualified closure.
- `disposition {disposition}` appends `findingId`, `outcome` (`fixed`, `rejected`,
  `deferred`), `evidenceIds`, `owner`, `reviewer`, `record`, and optional
  `correctiveUnitId`. Fixed/rejected reports require fresh passing evidence for
  the affected criteria and unit or linked corrective unit. Consequential findings
  require a different reported reviewer. Deferral requires a corrective unit and
  never waives the finding. These are reported dispositions, not authenticated
  risk acceptance: qualified resolution remains blocked. Later reports cannot
  silently erase earlier findings.

A post-delivery package contains `baseline` (full Git SHA), `designDigest`,
`policyDigest`, `unitIds`, `evidenceIds`, `results` (one `{criterionId,outcome,record}`
for each covered criterion), `findings` (the finding shape above), and `record`.
`policyDigest` is a 64-character SHA-256 reference or the explicit value `unqualified`.
`evidenceIds` must resolve to post-report records with identical baseline, design,
policy, unit scope and observed integrations. Pre-integration reports, dangling
references and contradictory outcomes reject. Policy/evidence references are not
verified authorities. Integration
must already be recorded for every covered unit. Whole-mission reports cover all
units/criteria; the identical package is retained for each unit without duplicating
review work. A failed assembled-baseline result remains visible even if earlier
PR results passed. Actual ancestry, required platform execution, trusted policy and
authenticated receipts are still missing gates; arbitrary reported SHAs cannot
satisfy them. Report packages do not execute commands or fetch artifacts.

`mission_reconcile({unitId,attemptId})` reads the bound PR using existing GitHub
authentication. Only an exact-head merge into the recorded repository's `dev`
records an `adapter-observed` integration. Missing earlier review/evidence gates
remain missing. Integration is not mission completion. V2 never starts pending
remote effects; therefore it cannot queue two concurrent merges or recover an
unqualified send. Existing v1 pending effects must settle before migration.

Amendments retain old snapshots and integrated history but require renewed native
acknowledgment/defense. Removing a criterion requires an explicit manifest
`dispositions` entry `{criterionId,reason,owner,replacementIds}`; replacements may
be empty for intentional removal. The owner acknowledges the changed manifest,
including dispositions. Changed integrated criteria need an unintegrated final
corrective unit. Historical integration never becomes evidence for new criteria.

V2 uses no automatic continuation loop: a blocked shadow mission is not a reason
to repeatedly invoke tools or reopen dialogs. Preserve the concrete blocker and
continue only with work that can safely proceed.

## Explicit migration and rollback

`mission_migrate({adopt:false,repository:"owner/repo"})` returns a preview and
`sourceDigest` without writing. The repository is needed only if v1 has no candidate.
Adopt with `adopt:true`, the returned `expectedDigest`, and the same repository.
An owner-only dialog precedes adoption; migration itself does not approve v2 intent.
The writer locks, rereads and compares exact source bytes, writes/fsyncs a read-only
`state.json.v1-<sourceDigest>.json` backup, then atomically replaces the live record.
Stale previews, pending effects and unsupported schemas fail without overwrite.

Legacy positional criteria receive stable `C-1`, `C-2`, … IDs. Missing scope/check
details remain explicitly unspecified. Original v1 approvals, reviews, evidence,
generation and history remain under `legacy`; they do not pass v2 gates. An already
merged v1 record imports as historically integrated with `legacy-reported` origin,
not a new live GitHub observation or completed post-delivery review.

Rollback means stop v2 writes and keep a v2-capable reader. Never ask a v1 binary
to overwrite v2 state or restore a backup over later history. Preserve all files
after interruption; stale lock recovery requires confirming no writer remains.
Replay detects corrupted projections, not malicious rewriting by an unrestricted
executor. The local event log is neither signed nor externally tamper-resistant.

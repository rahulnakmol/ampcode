# Mission Traceability Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Use subagent-driven-development only for authorized, bounded independent work; do not dispatch a worker per task by default. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver opt-in, persisted v2 mission traceability with truthful acceptance authority, per-PR delivery accounting, and native Amp interaction, while preserving v1 behavior and keeping unqualified remote enforcement disabled.

**Architecture:** Add a versioned v2 contract and reducer beside the existing v1 implementation. Reuse the current persistence and native confirmation patterns without rewriting v1 history. Expose v2 as a local/shadow workflow: reported observations never become trusted execution receipts, and v2 cannot initiate remote integration until the separately qualified verification path exists.

**Tech Stack:** TypeScript, Bun tests, Node filesystem/crypto APIs already used by the plugin, installed Amp plugin API, existing `make check`; no new service, build system or model pin.

**Spec:** `docs/superpowers/specs/2026-10-31-mission-enforcement-design.md`, including acceptance authority, delivery-unit lifecycle and native-first additions. Read both documents before executing.

## Execution checkpoint — 2026-10-31

The planning-time authorization statements below are historical. The owner subsequently
approved implementation, gated dev/rolling/stable delivery, main-only Personal installation,
disposable trials and a 120,000 additional-token budget. Shared infrastructure/access changes
remain excluded. Exact token telemetry is unavailable; no exact consumption claim is made.

- [x] Tasks 1–4: contracts, acknowledged snapshots, per-unit attempts, reported evidence and
  post-delivery accounting implemented. Independent review found and reproduced lineage,
  disposition and freshness gaps; regression repairs passed subsequent independent review.
- [x] Task 5: explicit migration, pending-effect rejection, risk-floor preservation and strict
  UTF-8 byte preservation implemented. A real SIGKILL inside the shared locked writer preserved
  original/backup bytes and blocked retry until the disposable dead-writer lock was removed.
  This does not prove power-loss safety at every instruction boundary.
- [x] Task 6 local qualification: 42 Bun tests/306 assertions and 155 Python tests passed in
  `make check` on macOS arm64, Bun 1.4.4. Independent reviewer
  `TU-034pTJlm5zmNDaPXMsjRA8` approved the repaired code after two review gates and follow-up
  freshness repair. Genuine owner approval of a disposable v2 manifest persisted across
  scoped plugin reload. Live read-only reconciliation observed the existing synthetic PR1
  merge; v2 merge calls rejected before and after reload, retaining qualification blockers.
  The temporary loader redirects root/URI and prefixes tool names; it preserves native UI
  and actual thread identity but omits trial lifecycle hooks to isolate the delivery mission.
  Hook behavior and migration dialogs remain adapter-tested, not native-qualified here.
- [x] Task 7 bounded feasibility: installed Amp API inspection and synthetic subprocess probes
  retained real exit 17 despite forged success text and rejected missing-step/wrong-revision
  claims. A same-UID child read a synthetic non-secret publisher sentinel despite an empty
  environment. No trusted publication/isolation bridge is established; existing CI remains
  authoritative. No new credentials, check publication or infrastructure were introduced.
- [ ] Remote PR checks, exact high-risk final acknowledgment and protected dev integration.
- [ ] Separately gated rolling/stable promotion, release and main-only Personal publication.

Detailed task checkboxes below retain the original procedure rather than retroactively claiming
each proposed experiment ran. The checkpoint above is the executed scope. Implemented API
shapes are documented in `docs/mission-control.md`; unit creation is manifest-driven, and
`MissionV2` belongs to the reducer module. V2 has no pending-effect or qualified-closure
transition to test or activate. Source delivery and runtime qualification remain distinct.

## Global constraints and authorization

- “Traceability on every PR to `dev`, with compact records for eligible small changes. Roll out in shadow mode before making the check required.” This plan implements opt-in shadow records, not required-check activation.
- “Evidence and enforcement first; dependency-aware coordination second.” No DAG scheduler or worker dispatch in this plan.
- “Bun and Bun workspaces remain the default for pure TypeScript.” Do not introduce Bazel here.
- “Local shell/admin tampering is outside the accepted security boundary.” Do not invent cryptographic owner receipts.
- “Mission-control adds approved intent, dependency readiness, traceability, evidence freshness and delivery gates around Amp's existing capabilities.” Do not clone Librarian, Oracle, Finder, native thread/runtime machinery or approvals.
- Preserve `dev → rolling → main`; no release, publication, credential changes, protection changes or shared-service changes are authorized by this plan.
- Planning is authorized; implementation has not started. During execution, land coherent tested increments only under the user's applicable commit/push authorization. Never push or activate infrastructure merely because a task says “checkpoint.”
- Preserve `/Users/rahulnakmol/Developer/GitHub/wt-release-mission` and unrelated staged work. Current documents live in `wt-mission-enforcement-spec`, branch `docs/mission-enforcement-spec`, based on `origin/dev` at `f56090192908a84dde1d50b2cd2c163d64f66da7`. At execution, use a dedicated implementation worktree from refreshed `origin/dev`; transfer these exact reviewed documents without losing local changes.

## Deliverable boundary

The foundation must support serial local missions, two PR delivery-unit records, retained attempts, criterion-to-evidence links, design amendment detection, post-delivery/closure accounting and migration previews. It must show why a unit is blocked and which evidence is merely reported. It need not—and must not pretend to—provide independently authenticated execution provenance.

V1 remains usable under its existing guarantees. A v2 mission reports `remote-verification-unqualified` and cannot send a merge through `mission_merge`. Do not downgrade it to v1 or add a force flag to escape that restriction. Remote facts observed through read-only reconciliation can record an externally authorized integration, but cannot fabricate preceding verification or approvals; status explicitly distinguishes observed integration from fully qualified delivery. Test-only adapter injection is not a user tool or production approval path.

## Source map and dependency order

| File | Responsibility / planned treatment |
| --- | --- |
| `plugins/mission-control/lib/mission.ts` | Keep v1 public lifecycle intact; version-aware persistence entry points delegate v2 validation without interpreting v2 as v1 |
| `plugins/mission-control/lib/contracts.ts` (new) | V2 persisted and manifest types, bounded runtime validation, canonical intent projection/digests; no effects |
| `plugins/mission-control/lib/mission-v2.ts` (new) | Pure v2 transitions, delivery-unit/attempt bindings, blocker and closure computation |
| `plugins/mission-control/lib/migration.ts` (new) | Explicit v1 preview/mapping and safe migration transaction; no remote mutation |
| `plugins/mission-control/index.ts` | Version dispatch, native dialogs, status/presentation, read-only reconciliation and v2 merge prohibition |
| `plugins/mission-control/lib/github.ts` | Preserve v1 merge behavior; extract a shared read-only candidate lookup only if needed for v2 reconciliation; no new publication credentials |
| `tests/mission-control.test.ts` | Extend lifecycle tests with contract/authority/unit/invalidation cases |
| `tests/mission-plugin.test.ts` | Extend current registered-tool/dialog harness with v2 opt-in, migration, status and prohibited effects |
| `tests/mission-github.test.ts` | Preserve exact-head protection tests; add v2 read-only reconciliation cases if adapter changes |
| `docs/mission-control.md`, `README.md` | Explain opt-in shadow status, native capability reuse, migration and explicit limitations; do not claim installation |

Order: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6. Task 7 is a bounded feasibility investigation after foundation review, not remote activation. Source edits share ownership and should be serial. Independent reviewers may work read-only against fixed checkpoints. Use Librarian only for unresolved external-source questions and Oracle only for consequential uncertainty/review; discover available native surfaces rather than hard-code APIs.

## Task 1 — Versioned contracts and stable intent identity

**Files:** create `lib/contracts.ts`; extend `tests/mission-control.test.ts`. Paths are relative to `plugins/mission-control/` unless prefixed with `tests/`.

**Public interfaces:** `parseManifest(value: unknown): ManifestV2`; `parseMissionV2(value: unknown): MissionV2`; `intentDigest(manifest: ManifestV2): string`. Export `ManifestV2` and `MissionV2` from this module. `ManifestV2` contains `schemaVersion: 2`, mission/repository IDs, requirements, criteria, decisions, slice scopes and delivery allocations. `MissionV2` contains that manifest plus immutable design snapshots, approval/defense references, unit/attempt histories, events, aggregate state and closure records as specified in section 5. Runtime status/evidence never belongs in the manifest's intent projection.

- [ ] Write a small valid manifest literal in the existing test file: mission `M-1`, repository `acme/app`, requirement `R-1` “Recover edits”, criterion `C-1` “Recover after interruption”, authority `mission`, method `journey`, check `recovery`, unit `U-1`, slice `S-1`, path `src/recovery.ts`. Use this fixture consistently; all required references resolve.
- [ ] Add contract tests that mutate that fixture to duplicate `C-1`, refer to missing `R-2`, use schema version 99, and declare an unknown authority. Assert rejection, not silent normalization. Test the same intent with reordered object keys yields the same digest, while changing “interruption” to “clean shutdown” changes it.
- [ ] Run `bun test tests/mission-control.test.ts`. Record the expected missing-export or rejected-contract failure; after exports exist, confirm the behavioral tests fail before implementing their validation.
- [ ] Implement bounded parsing: maximum 1 MiB JSON input at file boundaries, 1,000 entries per manifest collection and 16 KiB per prose field; reject invalid types, unknown enum values, unresolved references, duplicate IDs and unsafe manifest paths (absolute or `..` segments). Use a single runtime parser as validation authority rather than a separate drifting handwritten JSON schema.
- [ ] Implement sorted-key UTF-8 canonicalization, preserving array order and rejecting non-finite/undefined values. Keep full SHA validation and repository identity conventions from v1. Do not normalize criterion text or regenerate IDs from it.
- [ ] Verify with the following behavioral assertions, using the complete fixture above:

```ts
const original = parseManifest(validManifest)
const amended = structuredClone(original)
amended.criteria[0].outcome = 'Recover after clean shutdown'
expect(intentDigest(amended)).not.toBe(intentDigest(original))
expect(() => parseManifest({ ...validManifest, schemaVersion: 99 })).toThrow()
```

- [ ] Run the targeted suite and `make check`; review the contract changes before a coherent checkpoint. Suggested checkpoint subject: `feat(missions): define versioned traceability contracts`.

## Task 2 — Local approval authority and amendment detection

**Files:** create `lib/mission-v2.ts`; extend `tests/mission-control.test.ts`.

**Public interfaces:** `createMissionV2(thread: string, manifest: ManifestV2): MissionV2`; `advanceV2(state: MissionV2, action: ActionV2): MissionV2`; `blockersV2(state: MissionV2, unitId?: string): string[]`. Export the discriminated `ActionV2` union. Implement actions incrementally: `design {manifest}`, internal `approve-design {digest}`, `defense {digest, record}`, `unit {id, sliceIds, criterionIds}`, and `build {unitId}`. Only the native approval adapter may expose the internal approval transition; model-facing action schemas exclude it.

- [ ] Add a red test that builds before approval, then after approval but before defense. Both must reject without mutating the input state.
- [ ] Add a red amendment test: approve interruption recovery, submit clean-shutdown intent through `design`, and assert renewed approval/defense blockers while the prior snapshot remains unchanged. Candidate-versus-snapshot comparison is tested in Task 3 when candidate actions exist.
- [ ] Run `bun test tests/mission-control.test.ts` and capture the missing behavior.
- [ ] Implement immutable snapshots and explicit intent projection comparisons. A candidate manifest is never the source of its own approved snapshot. Policy references are data in the foundation, not authenticated policy adoption; unavailable policy authority remains a blocker for qualified acceptance.
- [ ] Keep `intentAuthority: 'local-reported'` in status. Reordering criteria preserves ID associations but may change the design digest because the canonicalization contract preserves array order; it must never reassign evidence by array index.
- [ ] Implement this transition shape, using current v1 patterns for immutable updates and event sequencing:

```ts
let state = createMissionV2('T-test', parseManifest(validManifest))
state = advanceV2(state, {
  type: 'approve-design', digest: intentDigest(parseManifest(validManifest)),
})
const changed = structuredClone(validManifest)
changed.criteria[0].outcome = 'Recover after clean shutdown'
state = advanceV2(state, { type: 'design', manifest: parseManifest(changed) })
expect(blockersV2(state)).toContain('Owner design approval required')
```

The fixture `validManifest` is defined in Task 1; the new state retains the earlier snapshot without treating its acknowledgment as approval of the replacement.

- [ ] Test that a changed approval digest cannot authorize the prior snapshot and that imported/reported evidence cannot synthesize approval. Run `make check`; checkpoint only coherent passing work. Suggested subject: `feat(missions): bind intent to acknowledged snapshots`.

## Task 3 — Per-PR delivery units and candidate attempts

**Files:** `lib/contracts.ts`, `lib/mission-v2.ts`, `tests/mission-control.test.ts`.

**Interfaces:** extend `ActionV2` with `candidate {unitId, attemptId, candidate, manifest}`, `report {unitId, attemptId, evidence}`, `review {unitId, attemptId, gate, fingerprint, evidenceDigest, reviewer, findings, passed}`, `finding {unitId, attemptId, finding}`, `pause {reason}`, `resume`. Add `fingerprintV2(state: MissionV2, unitId: string, attemptId: string): string`. Evidence supplied through public tools has producer class `reported`; executable receipt ingestion is not exposed yet.

- [ ] Test candidate intent against the retained approved snapshot: clean-shutdown intent must reject when interruption recovery was approved, even with a matching candidate-supplied digest. Resolve the snapshot from coordinator state and compare `intentDigest(manifest)` before registering the candidate; public input cannot supply its own authoritative approval.
- [ ] Write a red test with `U-1/PR7` and `U-2/PR8` sharing head/base SHAs. A review or report for U-1 must not satisfy U-2. Rebinding U-1 to PR8 must reject; a replacement PR requires a separate unit.
- [ ] Write a red test that changes only base SHA on U-2: U-2 final acceptance becomes stale; U-1's historical integration record survives. A mission-design amendment invalidates all active units and aggregate closure.
- [ ] Implement retained attempt history and scope-aware invalidation; never overwrite an integrated attempt. Resolve explicit unit/attempt IDs; inference is allowed only for an unambiguous single-unit mission.
- [ ] Add blocker computation for missing checks, unresolved findings, unavailable required platform, stale reviews, unknown risk and `remote-verification-unqualified`. Report prose cannot satisfy execution-required criteria. Missing independent review cannot become self-review merely because Oracle is unavailable.
- [ ] Exercise reviewer order: failed review 1 permits repairs but not passing review 2; repairs create a new attempt and require renewed review 1. Bind reviews to execution-evidence digest, excluding reviews themselves to avoid a cycle.
- [ ] Run `bun test tests/mission-control.test.ts`, then `make check`; inspect changed state snapshots for retained history and identity. Suggested subject: `feat(missions): track per-PR delivery attempts`.

## Task 4 — Integration observations, stage 4 and closure accounting

**Files:** `lib/contracts.ts`, `lib/mission-v2.ts`, `tests/mission-control.test.ts`.

**Interfaces:** add internal `observe-integration {unitId, attemptId, commit, remoteHead, targetRef, repository}`; public `post-delivery {unitId, baseline, findings, record}` and `closure-report {baseline, designDigest, policyDigest, unitIds, evidenceIds, record}`. Observations have separate reported/adapter-observed origin; a model action may not assert the latter. The foundation stores closure reports but refuses qualified closure when execution/authority prerequisites are missing. Internal adapter-driven qualification can be tested with controlled fixtures, never manufactured through public tool inputs.

- [ ] Write a red two-unit scenario: observe A integrated, leave B building, and assert aggregate status remains active. An integration observation alone cannot manufacture passed pre-merge gates or stage-4 completion.
- [ ] Add the regression counterexample: B introduces failure in A's recovery criterion. The whole-mission closure report must identify that failure and remain blocked, even when both PR histories contain earlier passing reports.
- [ ] Implement criterion allocations: distinguish partial contributions from the final unit's integrated satisfaction. Resolve all prerequisite integrations against the recorded baseline; missing proof blocks rather than assuming chronological commits imply inclusion.
- [ ] Implement retained `integrated → adversarial-review → closed` unit accounting and aggregate `closure-review` constraints. Unknown pending effects block later integrations/amendments; controlled tests prove two pending effects cannot coexist. V2 production effect initiation remains disabled.
- [ ] Allow one complete package to cover unit post-delivery and aggregate closure only for identical baseline/design/policy/evidence and whole-mission scope. Reject partial coverage, stale baseline or pre-integration review reuse.
- [ ] Test explicit dispositions for removed criteria, corrective-unit links and preserved historical results. Run targeted tests and `make check`. Suggested subject: `feat(missions): account for delivery and mission closure`.

## Task 5 — Safe persistence, migration preview and explicit adoption

**Files:** create `lib/migration.ts`; modify persistence boundaries in `lib/mission.ts`; extend `tests/mission-control.test.ts` and `tests/mission-plugin.test.ts`.

**Interfaces:** `previewMigration(previous: Mission): MissionV2` (where `Mission` is the existing v1 type); `migrateMission(path: string, thread: string, expectedDigest: string): MissionV2`. Keep `loadMission`/`saveMission` v1 callers compatible; introduce version-aware `loadRecord(path, thread): Mission | MissionV2 | undefined` and `saveRecord(path, record): void` only at the plugin dispatch boundary. Put shared filesystem behavior in its existing owner rather than duplicating locks in the migration module.

- [ ] Write real-filesystem tests using `mkdtempSync`: v1 active, v1 merged, v1 pending, malformed JSON and unknown future version. Assert exact original bytes survive preview; pending migration rejects; historical merged imports never acquire passed v2 closure.
- [ ] Implement deterministic migration mapping for legacy positional criteria to assigned stable IDs. Preserve original v1 JSON as an immutable backup with digest, and preserve missing historical facts as missing/reported. No inference of policy authority or independently verified evidence.
- [ ] Under the existing exclusive lock, re-read and compare the expected source digest, write/fsync the backup before replacement, write/fsync a temporary v2 file, atomically replace, and release the lock. On any failure preserve recoverable original/backup bytes; do not delete a stale lock automatically.
- [ ] Test a file change between preview and adoption rejects without overwrite. Use a subprocess for a killed-writer scratch validation; inspect actual bytes after restart. Keep only a focused regression test for observable preservation, not incidental fsync call ordering.
- [ ] Preserve v1 pending reconciliation before migration. Unknown outcome stays v1/pending. Document rollback as stopping v2 writes while retaining a v2-capable reader; never ask an old binary to rewrite v2 data.
- [ ] Run all three mission suites and `make check`. Suggested subject: `feat(missions): migrate records without losing history`.

## Task 6 — Native Amp opt-in workflow and truthful status

**Files:** `plugins/mission-control/index.ts`, `tests/mission-plugin.test.ts`, `docs/mission-control.md`, `README.md`; change `lib/github.ts`/its tests only if a shared read-only lookup is needed.

**Interfaces:** extend `mission_start` with optional `schemaVersion` and v2 `manifest`, retaining the v1 default during shadow rollout. Add `mission_migrate` for preview/adoption via native owner confirmation. Extend existing status/update/presentation tools with version dispatch. V2 unit/attempt selectors are mandatory when ambiguous. Keep existing v1 tool calls valid; the current helper makes all listed fields required, so revise it to accept an explicit required-field list rather than accidentally requiring new optional arguments.

- [ ] Add failing registered-tool tests for v2 opt-in, native design approval, stale dialog response, cancellation, and ambiguous unit selection. Use existing `harness()` rather than building a parallel mock runtime.
- [ ] Implement native confirmations using the current owner-restricted field and re-read state after the dialog. Amendment presentation shows old/new criteria, affected units and the local-reported authority limitation. Public `mission_update` must reject internal approval, qualified-receipt and integration-origin actions.
- [ ] Make `mission_status` show mixed unit stages, exact blockers and evidence classes. Do not serialize secrets or claim specialist availability. Native-first guidance belongs in tool descriptions/docs; no new Librarian/Oracle wrappers or calls are required for this foundation.
- [ ] Preserve v1 `mission_merge`. For v2, reject before any GitHub write with `remote-verification-unqualified`; no `--auto`, admin override, downgrade or force escape. Read-only `mission_reconcile` may report an already merged exact PR/head/target and retain all unfulfilled local gates visibly.
- [ ] Prove the prohibition through the injected GitHub adapter: make every write throw `unexpected remote mutation`, exercise v2 merge/recovery/status flows, and assert the semantic blocked status. This seam test is necessary because accidentally dispatching v1 merge for v2 is a plausible regression.
- [ ] Update session/agent hooks to avoid treating shadow-mode blocked status as a reason for endless continuation. Record the blocker and stop; do not repeatedly open dialogs, invoke specialists or spawn threads.
- [ ] Run `bun test tests/mission-control.test.ts tests/mission-plugin.test.ts tests/mission-github.test.ts`, `make check`, and a disposable local Git/native Amp journey with no remote mutation. Native approval must be genuine when claimed; injected UI tests remain separately labeled. Preserve sanitized status before/after reload. No production installation is needed to test a scoped local loader.
- [ ] Conduct correctness/security review, fix findings with regressions, revalidate, then conduct the second review on the final revision. Ask whether traceability reduces ambiguity without making a simple mission onerous. Suggested subject: `feat(missions): expose opt-in traceability workflow`.

## Task 7 — Bounded compute-verification feasibility trial (separate gate)

This task is a research/prototype brief, not an implementation plan for a trusted CI bridge. It starts only after foundation review and explicit authorization for any disposable remote resources/effects. Do not create shared infrastructure in order to make the trial succeed.

- [ ] Inspect the installed Amp API/version, existing credential capabilities without revealing secrets, available executor isolation and check-publication mechanisms. Use direct documentation/code inspection; consult native Librarian/Oracle only for unresolved scoped questions. Record which exact supported surface would supply authenticated run identity, isolated execution and trusted result publication.
- [ ] First test a local synthetic candidate that emits a forged successful report while exiting unsuccessfully. The supervisor must retain the real exit outcome; model text or an artifact cannot overwrite it. Also test a missing required step and wrong input revision.
- [ ] Present a concrete approval request if the next experiment needs a disposable GitHub repository, check write, token scope, new isolation environment or remote mutation. Existing live-trial authorization is not automatically extended to new resources.
- [ ] On authorized compute, test correct and wrong workflow/App/revision/attempt, malicious reports, base movement, interrupted result transport and duplicate observation. Confirm candidate code cannot read publication credentials or replace the policy/driver. Without evidence of isolation and authenticated result origin, classify the bridge as unqualified.
- [ ] Produce a concise result in the thread with commands, versions, run identities, observations and limitations. Preserve sanitized artifacts under `.amp/in/artifacts/` only after confirming local exclusion. Outcome is one of: supported native path with evidence; additional explicit infrastructure decision needed; or keep existing CI authoritative.
- [ ] Stop. Do not enable a required check, modify protection, replace CI or ship an alleged trusted bridge. A positive result informs a separately reviewed enforcement implementation plan.

## Foundation acceptance and self-review checklist

- [ ] V1 regression suites remain green; v2 cannot invoke v1 merge accidentally.
- [ ] Weaker candidate intent cannot replace the retained local approved snapshot; remote status does not imply authenticated owner intent.
- [ ] Two PR units preserve independent histories; partial integration does not close the mission; later regressions block aggregate closure.
- [ ] Reported observations cannot become executed/independent evidence through public tool fields.
- [ ] Pending migration, stale dialogs, concurrent writes, unknown schemas and interrupted persistence preserve state and block unsafe continuation.
- [ ] No custom specialist/runtime/router, provider pin, scheduler, required-check activation, release or Personal publication is introduced.
- [ ] Final report states what is locally implemented, what is tested only with adapters, what was genuinely exercised, and what remains unqualified. Include commit/push state accurately.

## Coverage and exclusions

Spec sections 3–6 and 12 map to Tasks 1–6: authority, units, snapshots, lineage, invalidation, preservation and truthful status. Sections 9–10's native-first constraints apply throughout; task DAG execution is excluded. Section 7's trusted compute/publication contract maps only to Task 7 feasibility—not activated enforcement. Language-specific execution adapters, Bazel experiments, every-PR required checks, recurring maintenance and shared-skill learning publication require separate plans. Stage-4 finding/closure records are included; automatic learning changes are not.

The independent native-first review found no textual blocker on 2026-10-31; it did not qualify the runtime. This plan has been source-grounded and self-reviewed, not executed. Default execution is inline in the dedicated implementation worktree with targeted native specialist assistance where justified, preserving the requested traceability-before-coordination order.

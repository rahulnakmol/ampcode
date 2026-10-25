# Compact mission record

Use one record per mission. Replace the prompts below with observed facts; omit inapplicable
fields with a reason. Link existing briefs and evidence rather than duplicate them. This is a
template, not an executable validator or proof of persistent background operation.

## Coordinate with mission-control when installed

Discover the installed tools and their schemas; do not invent action payloads. Keep reasoning in
`grilling`, `crafting`, and `delivering`; the plugin records revision-bound operational checkpoints.

| Tool | Use |
| --- | --- |
| `mission_start(requirements)` | Capture the original requirements and owner-initiated/adopted mission. |
| `mission_update(action)` | Record design, defense, build, candidate, reviews, evidence, or pause using the installed action schema. Never submit self-authored approval receipts. |
| `mission_status()` | Inspect current checkpoints and explicit blockers before proceeding. |
| `mission_approve(stage: design\|merge)` | Request owner acknowledgment of the current design package or exact final candidate. |
| `mission_merge_mode(mode: auto\|ask)` | Offer an owner-restricted merge-mode change; auto is the default, not a timer awaiting consent. |
| `mission_present()` | Present evidence, artifacts, limitations, and the try-it procedure before requesting merge. |
| `mission_merge()` | Request dev integration only after all current local and trusted external gates pass. |
| `mission_reconcile()` | Inspect external merge state after interruption or a pending merge; never equate a request with integration. |
| `mission_recover()` | After owner investigation of a settled, unqueued attempt, invalidate candidate evidence and return to review; never blindly retry. |

The first version authenticates the Amp thread owner, not arbitrary multiplayer initiators. The
initiator must own the thread or the owner must explicitly adopt the mission. Owner-restricted
dialogs use a non-sensitive typed acknowledgment in a secret-style field to restrict responders.
**Never enter credentials or other secrets.** Do not invent a responder ID or treat an agent's
transcript claim as a completed owner interaction. These local interactions are not trusted merge
authorization against an unrestricted executor.

An external trusted gate must hold policy, mission registration, approver mapping, and credentials
outside agent control and obtain authoritative revision/check/approval evidence. Protected `dev`
must enforce required checks, including a pinned trusted App check and administrator enforcement.
The source implementation does not host that controller, install its App, or configure protection.
Absent these prerequisites, automatic merge remains blocked; provision them only with separate
approval. If the plugin is unavailable, maintain this manual record and report the capability gap;
do not claim enforced gates or substitute local files for trusted authorization.

## Record template

```markdown
# Mission: <id and customer outcome>

## Agreement
- Requirements: <original request and purpose; clarification/change provenance>
- Brief: <path/URL and revision; self-contained or transferred with this record>
- Design package: <concrete spec, plan, technical design, relevant crafting UX or inapplicability>
- Design acknowledgment: <initiator/thread owner or explicit owner adoption; package revision;
  owner interaction reference; permitted assumptions; material changes reopen this gate>
- In / out: <scope and non-goals>
- Target: <actual recipient/environment; integration and rollout are separate>
- Permissions: <authorized local, remote, deployment actions and their source>
- Risk / merge mode: <low | medium | high | unknown and rationale; auto default | owner-selected ask>
- External gate readiness: <trusted controller and branch protection evidence or blocker>
- Limits: <agreed time/spend/attempt limits, or absent; next cost decision>
- Tokens: <4,000/task and 30,000/session unless explicitly overridden; measured/estimated/unknown
  usage including delegated work, remaining allowance, and accounting limitations>
- Owner: <integration owner; independent reviewer when required>
- Communication: <standard/formal | editorial; ELI5 when requested>
- Ownership defense: <record from whiteboard-defense.md; brief/candidate, challenge, teach-back,
  gaps and disposition; design readiness is not runtime verification>

## Current checkpoint
- State: <framing | design-awaiting-acknowledgment | defense | assess | define | harness-red | implement | journey | review-1 |
  repair | review-2 | value | ready-for-dev | integrated-dev | blocked | replan | stopped>
- Repository / base / branch / worktree / candidate: <exact identities>
- Preserved existing work: <owner, paths, verified safe location; never secrets>
- Active slice and dependencies: <IDs, ownership, prerequisite results>
- Next safe action: <one executable step and its prerequisite/approval>
- Blockers: <missing evidence/decision, owner, what unblocks it>

## Acceptance and evidence
| ID | Customer behavior and measurable criterion | Slice | Test/journey | Evidence and revision | Status |
| --- | --- | --- | --- | --- | --- |

For each evidence record:
- ID / criterion / candidate or base revision / relevant dirty diff identity.
- Command or reproducible user actions, environment, safe fixture and tool versions as needed.
- Expected result, observed result, exit status, and sanitized artifact location.
- Red failure reason; green result; applicable failure/recovery controls.
- Limits: simulation vs real execution, missing platforms, known failures, evidence reuse reason.

## Reviews and repairs
| Finding | Severity/customer risk | Reviewer and reviewed revision | Regression evidence | Fix/disposition | Gate-two verification |
| --- | --- | --- | --- | --- | --- |
- Gate one: <scope, independence, candidate, result, limitations>
- Gate two: <final candidate, finding closure, new-risk check, result, limitations>
- Accepted risks: <authorized owner, rationale, boundaries; never a fabricated pass>

## Value and delivery
- Benefit: <baseline → observed result, comparable conditions, uncertainty>
- Enabling dependency, if applicable: <criterion served; full-journey evidence still needed>
- Presentation: <inspected artifacts, evidence, limitations, reproducible try-it procedure>
- Merge acknowledgment: <required for ask/high; exact head/base/design/mode and owner interaction;
  absent for low/medium auto is not a blocker; unknown risk always blocks>
- CI / PR / merge: <exact head, required check outcomes, approvals, observed remote result>
- Milestone/full journey: <combined behavior and regression evidence>
- Release/deployment: <not authorized | pending | separately verified; target and evidence>
- Lessons: <specific findings that change the next slice>

## Operations and resume
| Operation intent/target | Authority | Expected effect | Observed effect/ID | Reconciliation before retry |
| --- | --- | --- | --- | --- |
- Artifacts transferred/preserved: <locations and integrity check>
- Pick-up prompt: <goal, this record and brief, actual revision, first safe action, stop gates>
```

`ready-for-dev` requires acknowledged current design, a current ownership defense, evidence for every in-scope criterion, both
review gates, value, and no unresolved mandatory failures. It does not authorize a push, merge,
or release by itself. A defense marked ready permits implementation only after design acknowledgment,
not dev integration. Low/medium auto needs no additional response once all gates pass; ask/high needs
current exact-candidate acknowledgment. Unknown risk, stale evidence, or missing trusted gates blocks merge.
`integrated-dev` requires the actual remote merge result. `blocked`, `replan`, and `stopped` retain
the last completed checkpoint and reason; none means success. Release status is recorded separately.

Store large artifacts outside the record. Keep only sanitized data necessary to reproduce a check.
Before worktree cleanup, transfer needed evidence and update references; a path to a deleted
worktree is not a usable handoff. If the record lives only locally, say so in the handoff.

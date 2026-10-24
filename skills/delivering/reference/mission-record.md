# Compact mission record

Use one record per mission. Replace the prompts below with observed facts; omit inapplicable
fields with a reason. Link existing briefs and evidence rather than duplicate them. This is a
template, not an executable validator or proof of persistent background operation.

```markdown
# Mission: <id and customer outcome>

## Agreement
- Brief: <path/URL and revision; self-contained or transferred with this record>
- Confirmation: <user instruction/message and any explicitly permitted assumptions>
- In / out: <scope and non-goals>
- Target: <actual recipient/environment; integration and rollout are separate>
- Permissions: <authorized local, remote, deployment actions and their source>
- Limits: <agreed time/spend/attempt limits, or absent; next cost decision>
- Owner: <integration owner; independent reviewer when required>

## Current checkpoint
- State: <framing | assess | define | harness-red | implement | journey | review-1 |
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

`ready-for-dev` requires current evidence for every in-scope criterion, both review gates, value,
and no unresolved mandatory failures. It does not authorize a push, merge, or release by itself.
`integrated-dev` requires the actual remote merge result. `blocked`, `replan`, and `stopped` retain
the last completed checkpoint and reason; none means success. Release status is recorded separately.

Store large artifacts outside the record. Keep only sanitized data necessary to reproduce a check.
Before worktree cleanup, transfer needed evidence and update references; a path to a deleted
worktree is not a usable handoff. If the record lives only locally, say so in the handoff.

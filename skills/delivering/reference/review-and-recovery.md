# Review, delegation, and recovery

## Fresh-context design review

The integration owner holds the problem, acceptance rubric, decisions, alternatives, progress and
evidence in a compact package. Fresh reviewers test whether the package works without the
author's conversation. Run them with the `goldfishing` skill, which owns what a reviewer gets and
never gets, severity, finding outcomes, round limits, failed reviewers and the review record.
Inspect referenced source; documents can be stale.

Before owner acknowledgment of a consequential design, run these lenses in order, each in its own
fresh context:

1. **Purpose and comprehension:** can a fresh reader reconstruct the customer problem, current
   system, proposed behavior, non-goals and grading criteria from the packet alone? Reuse a
   grilling check only for unchanged scope and revision; a new technical design needs coverage.
2. **Critic and source check:** challenge assumptions, alternatives, security, failure/recovery
   and compatibility against actual contracts. Verify claimed APIs, ownership and dependencies.
3. **Readiness and purpose recheck:** after repairs, can a fresh implementer identify affected
   files/contracts, ordered slices, testable invariants and the first safe check without inventing
   a consequential decision? Did the repairs preserve the intended customer benefit?
4. **Novice reader of the decision brief:** before the design dialog, a non-technical persona
   answers from the brief alone what is approved, what can go wrong, what it costs and what is
   not included (see `briefing-decisions`).

Give each reviewer the original requirements and acceptance IDs, the versioned design and brief,
and an explicit reading list. Budget required reviews before starting. Resolve factual disputes
with source inspection or a bounded experiment, and design choices with the authorized owner;
substantive changes invalidate affected passes. A pass means ready to present for owner
acknowledgment, not permission to implement, proof of runtime behavior or either of the two
build-review gates. With mission-control, include the final package in the existing design
action; do not invent a review tool or approval receipt.

## Review the candidate, not the implementer's confidence

Give a reviewer the confirmed acceptance IDs, base and candidate revisions, actual diff, relevant
contracts, test/journey evidence, and unresolved questions. For another checkout, transfer the
exact files or make the committed candidate accessible before requesting review. A branch name
or SHA alone does not transfer unpushed work. Do not tell the reviewer which conclusion to reach.

Use these lenses where applicable:

| Lens | Evidence to seek |
| --- | --- |
| Correctness | Public contract, nonempty expected outputs, boundary controls, preserved behavior |
| Permissions/isolation | Denied and allowed actors; cross-tenant/owner access; least privilege |
| Secrets/dependencies | Logs and artifacts scrubbed; changed dependency provenance and relevant advisories |
| Concurrency | Duplicate/reordered requests, cancellation, races, ownership and consistency |
| Data preservation | Partial failure, interrupted writes, migration compatibility, restore/recovery |
| Operations | Timeouts, retry/idempotency, resource limits, user-visible diagnosis and safe rollback |

Use existing scanning/checking tools where applicable; a clean scan does not replace semantic
review and an unavailable scanner is a limitation, not a passed check. Do not broaden a slice into
an unrelated repository-wide audit. Escalate critical findings even if outside the slice.

Each finding needs a location or reproduction, customer consequence, severity, smallest useful
fix, and verification. Gate two checks finding closure and repair interactions on the final
candidate, not just whether a reviewer message exists. Independent means another context/person
able to challenge the implementation; different model branding is not required or sufficient.

Bind both reviews and execution evidence to the candidate, base, and acknowledged design they
actually assessed. Changed code invalidates affected evidence; never copy a pass onto a new SHA
without revalidation. Material design changes reopen initiator acknowledgment before defense
and build. A mode change invalidates final merge acknowledgment. High risk always needs current
exact-candidate owner acknowledgment, ask mode needs it at any known risk, and unknown risk blocks
merge. Low/medium auto needs no extra response once all gates pass. No local record overrides the
required CI, mandatory failures, or branch protection. Local gates are workflow enforcement, not
security against an unrestricted executor; no custom controller/App is required.

## Check spec/code drift at gate two and resume

Read the acknowledged package, recorded approved changes, actual candidate source and relevant
tests/results. For each in-scope acceptance ID, trace its implementation and observable evidence.
Report missing behavior, shortcuts and changed contracts even if existing tests pass. Also check
the changed code for behavior outside the approved scope; do not audit unrelated legacy code.
Record only discrepancies and checked scope, not another copy of every matching requirement.

Separate an unauthorized change or defect from an explicitly approved evolution and a stale doc.
An approved rename with preserved behavior is not automatically a defect. Unknown provenance
remains unresolved. Restore the contract or obtain a real design decision; never silently change
the spec to match broken code. Refresh affected tests, reviews, defense and owner acknowledgment
where required. A resumed reviewer must reconcile actual revisions and external state before
using an old pass. Drift inspection does not replace executed tests or release checks.

## Delegate only when it helps

Prefer direct execution for coherent implementation. Use bounded independent investigation,
disjoint implementation, or consequential independent review when useful. Do not create another
thread merely for a new phase of work in the same checkout. Follow the available tools' rules.

Every assignment carries:
- Outcome and acceptance IDs; context and relevant evidence, without a desired review conclusion.
- Actual environment, exact base/candidate, input transfer, and permitted files/resources.
- Ownership, dependencies, authority, budget, and stop conditions.
- Required return: changes, evidence, limitations, blockers, next safe action.

Serialize shared writes. Separate working copies do not isolate databases, credentials, ports,
queues, or deployment targets. Keep one owner of shared interfaces and integration. Treat worker
results as reports until their evidence and combined behavior are checked. Never grant nested
delegation or choose an expensive model solely to imitate another vendor's architecture.

## Reconcile interruption before retrying

Before consequential external operations, record intent, authority, target, expected effect and
an operation/idempotency ID if supported. Afterward record the observed effect, not merely the
tool response. A lost connection leaves an unknown outcome, not a failed operation.

On resume:
1. Read the record and inspect real working-tree changes, commits, remotes, processes, PR/check
   state, or the affected external system. Preserve unexpected work and running valid tasks.
2. If the effect occurred, adopt its observed identity and continue. If absent, retry only when
   safe, still authorized, and within limits. If ambiguous, stop that operation and escalate.
3. For destructive/data operations, require a verified recovery path and applicable approval.
   Git rollback is not database rollback. Do not replay migrations or payments to obtain logs.
4. Recheck evidence that depends on changed code, configuration, environment, or base revision.
   Report stale approvals and unavailable verification; do not reuse them silently.
5. With `mission-control`, use `mission_status()` and `mission_reconcile()` to reconcile an
   interrupted or pending merge. A queued auto-merge request is not an observed dev integration.
   Present fresh artifacts/evidence and the try-it procedure before requesting another merge;
   renew exact-candidate acknowledgment where required. Never bypass local approval, CI or protection.

Diagnose repeated failures with new evidence. A reproduced baseline failure remains a failure;
a flaky green retry does not erase it. Continue unrelated safe work while blocked when useful,
but do not claim the blocked requirement is complete. Suspected secret exposure or data loss
requires immediate containment within authority and escalation without copying sensitive payloads.

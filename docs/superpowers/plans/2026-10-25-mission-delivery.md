# Mission delivery implementation plan

> Execute inline with outcome-led TDD. The user approved the workflow in the source thread before implementation.

**Goal:** Carry software requirements through owner-approved design, whiteboard defense, verified code and risk-based integration into dev.

**Architecture:** Keep reasoning in delivering, grilling and crafting. Add an Amp mission coordinator with revision-bound persisted checkpoints, owner-restricted dialogs and observable evidence. A separately trusted controller must authorize merge; local state and hooks are not a security boundary against an unrestricted executor.

**Tech stack:** TypeScript, Node standard library, Bun tests, Amp Plugin API, Git and GitHub CLI.

**Spec:** The approved agreement below; source: https://ampcode.com/threads/T-01a16f76-cc55-77ee-b421-dff55ba10ea0.

## Approved agreement

- User requirements are the input. Grilling makes them concrete without changing their purpose.
- Spec, plan, technical design and relevant crafting UX design need mission-owner acknowledgment BEFORE whiteboard defense or build.
- Material changes reopen acknowledgment and defense. Evidence and reviews bind to the candidate revision.
- At build entry, expose automatic merge as the default, with optional ask-before-merge. No response or timer is required for automatic low/medium merge.
- High risk always needs human acknowledgment of the exact candidate; unknown risk cannot auto-merge.
- Preserve outcome-driven TDD, two distinct review gates, repair/revalidation, actual artifact inspection and customer value.
- Present evidence and a try-it procedure before requesting merge. Completion means verified integration, not an auto-merge request.
- Target dev only; rolling, stable, deployment and Personal extension publication remain separate.

## Explicit implementation constraints

- First version supports a mission initiated/adopted by its Amp thread owner. The installed API cannot authenticate arbitrary multiplayer initiators. Owner-only secret confirmation fields carry a non-sensitive typed acknowledgment, never a credential. Do not invent a responder ID.
- Local persisted state is operational evidence, not trusted authorization. The external controller must keep policy, mission registration, approver mapping and credentials outside agent control.
- Implement and test the controller's deterministic decision contract here. Hosting an authenticated controller, installing its GitHub App and changing branch protection require separate setup approval; until then auto-merge fails closed.
- Prefer existing Amp dialogs and transcript output over a new dashboard. No UI framework or external dependency is needed.

## Task 1: revision-bound mission lifecycle

Files: plugins/mission-control/lib/mission.ts; tests/mission-control.test.ts.

- [x] Write lifecycle tests against public operations: build before approval refused; changed design invalidates approval; stale review/evidence refused; high/unknown risk cannot silently downgrade; merge mode changes invalidate final acknowledgment; interrupted merge remains reconcilable.
- [x] Retain red results. The initial lifecycle result was a missing-module/bootstrap failure, not behavioral proof. Later reentry, corruption, risk and review regressions failed behaviorally before repair.
- [x] Implement atomic persisted state and chronological events, validated revision identities and explicit blockers. Public `advance` operations reject build before approval/defense.
- [x] Test reload on real temporary Git directories and separate Bun processes, including corrupt-state rejection. Commit a coherent green increment.

## Task 2: trusted merge decision and Amp integration

Files: plugins/mission-control/lib/gate.ts, lib/github.ts, index.ts; tests/mission-gate.test.ts, tests/mission-plugin.test.ts.

- [x] Test decision inputs from a trusted controller: missing/failed mandatory checks, wrong owner, stale head/base/design, stale review, high-risk acknowledgment and default low/medium path. `evaluateGate(snapshot)` reports blockers rather than accepting self-declared success.
- [x] Add the coordinator's lifecycle tools. Approval fields are not agent-callable receipts; only owner-restricted UI completion produces them.
- [x] Query GitHub again before requesting exact-head squash auto-merge; require protected dev, administrator enforcement and pinned successful checks. Verify merge separately. Reject unsupported merge queues through authoritative GraphQL reads. Owner-acknowledged recovery advances a generation and invalidates authorization without resending effects.
- [x] Exercise registered tools with temporary Git repositories and SDK-shaped UI/transport adapters. Load through `amp plugins exec`; perform only a live read of existing PR16, not a live merge or protection change.

## Task 3: workflow, documentation and independent review

Files: skills/delivering/SKILL.md and references; docs/mission-control.md; README.md; plugins/README.md.

- [x] Update instructions to use the coordinator when installed, preserve requirements, require owner acknowledgment of both design disciplines, and implement the agreed default merge mode.
- [x] Document trusted-controller input provenance, deployment prerequisites, credential separation, availability limits and no false enforcement claims.
- [x] Run make check, real local restart/journey probes and two independent review gates with repairs and revalidation. Both reviews found defects; regression repairs and a second-gate follow-up closed the findings. Native owner dialogs and live protected merges remain unverified.
- [ ] Deliver source and evidence. This permission/merge-control feature is high-risk: do not merge this PR without the user's explicit final-candidate acknowledgment. Do not publish to Personal repositories or install shared protections without approval.

## Activation remains a separate, blocked stage

Read-only GitHub inspection found no protection or active rules on `dev`, and no
PR test workflow. This source includes a coordinator and a pure policy contract,
not the authenticated hosted controller. Its installation, owner authentication,
App credential separation, PR CI, protected-branch configuration and live
acceptance trials still require setup and applicable approval. No production
reliability or autonomous integration claim follows from local checks.

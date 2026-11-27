# Playbook: AI-native software delivery

## When to use

Taking a vague intent or a concrete requirement to verified, integrated and released software.
The owner decides intent and behaviour; agents own technical design and build. Not for a typo,
a standalone review (`security-review`) or release-only work.

## Skills

- `grilling` and `crafting`: concrete expectations, journeys and states.
- `delivering`: the conductor from design to `dev` integration. Follow its gates, reviews and
  merge policy; they override this playbook. On Amp, `mission-control` enforces them.
- `goldfishing` and `briefing-decisions`: design review and the owner's brief.
- `architecting`: the technical design in `delivering`'s design package: contracts, ADRs with
  options and measurable non-functional requirements. If not installed: write the contracts,
  decisions as short ADRs and each non-functional requirement with a number and a test.
- `interrogating-changes`: the code review at `delivering`'s review gates one and two, with a
  verdict tied to the exact patch, by a reviewer on a model that implemented none of the change
  (its ledger rule L10 checks it). If not installed: `delivering`'s own review gates, with fresh
  reviewers for consequential changes.
- `threat-modelling`, when trust boundaries change: the threat model the design links. If not
  installed: list actors, trust boundaries and abuse cases in the design package, each with a
  mitigation or an owner.
- `releasing`: each promotion after `dev`, with notes, a rollback plan, a GO or NO-GO and a
  read-back on the target. A promotion is an outside effect: it runs when the mission contract
  pre-authorizes it, otherwise it is stop reason 2. If not installed: follow the repository's
  promotion rules, with the rollback plan written first.

## Steps

1. Charter the mission with `missioning`; the charter is part of `delivering`'s mission record.
2. Use `grilling` and `crafting` to confirm the brief: journeys, behaviour and rendered states.
3. Write the technical design, acceptance criteria with finite case lists, milestones and work
   items; run the fresh design review.
4. Run the whiteboard defense and the readiness preflight; write the kickoff brief; get the one
   kickoff approval.
5. Run `delivering`'s contract loop for the milestone: each item test-first, end-to-end first,
   with a pure core and side effects in the shell. No pull request opens before `delivering`'s
   verification gate (`verify_gate.py check`) passes on the exact head for each changed package.
6. Review gates one and two on the milestone's exact candidate, each on a model that implemented
   none of it; at a cap, follow the disposition policy.
7. Merge the milestone into `dev` when its gates pass; read the merge back; send the checkpoint
   report.
8. Release only as an effect: pre-authorized at kickoff or asked, with a rollback plan; verify on
   the target.
9. Close out: trace each criterion to its executed evidence on the released revision.

Milestones: one per slice of the design, each running steps 5 to 7; then release and close-out
(steps 8 and 9).

## Human gates

- Kickoff: the confirmed brief, the design and its defense, open questions with defaults and
  pre-authorized effects, after a passing readiness preflight (steps 1 to 4).
- Release: an effect, pre-authorized at kickoff or asked with the exact plan.

Every merge into `dev` is an agent row at every risk level, once both reviews and the evidence
match the exact candidate.

## Definition of Done

Every acceptance criterion maps to an executed test or journey on the released revision, every
milestone PR carries a passing `verify_gate.py check` for its head, both reviews are recorded
against that revision with reviewer and implementer models that differ, the trace has no gaps, and the release is verified on
its target. Each test written for a new or changed behaviour keeps its failing run on the unchanged
code; a refactor's checks pass on both. When accessibility is in scope, each in-scope WCAG 2.2 A
and AA criterion reads pass, fail or not examined. Built screens are compared with the approved
renders when states were rendered, and the threat model is updated after the build when the design
has one.

## Red flags

- A merge request reported as a merge.
- Green CI reported as a review verdict.
- A pull request without passing local end-to-end evidence; a reviewer on the implementer's model.
- I/O, a clock or randomness in the pure core; a retry, sleep or skip added to a flaky test.
- Build started before the kickoff approval.
- A release inferred from permission to merge.

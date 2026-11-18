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
- `architecting` (planned, wave 1). Fallback: write the technical design inside the delivering
  design package: contracts, decisions with alternatives (as short ADRs) and each non-functional
  requirement with a number and a test.
- `reviewing-code` (planned, wave 1). Fallback: `delivering`'s own review gates one and two, with
  fresh reviewers for consequential changes.
- `threat-modelling` (planned, wave 1), when trust boundaries change. Fallback: list actors,
  trust boundaries and abuse cases in the design package, each with a mitigation or an owner.
- `releasing` (planned, wave 1). Fallback: follow the repository's promotion rules; ask for each
  promotion with a rollback plan written before the request.

## Steps

1. Charter the mission with `missioning`; the charter is part of `delivering`'s mission record.
2. Use `grilling` and `crafting` to confirm the brief: journeys and behaviour.
3. Write the technical design and acceptance criteria; run the fresh design review.
4. Write the design brief; get design acknowledgment.
5. Run `delivering`'s whiteboard defense and build loop, one slice at a time.
6. Review gates one and two on the exact candidate; repair and recheck.
7. Present evidence; merge into `dev` under the risk policy; read the merge back.
8. Release only with separate approval; verify on the target.
9. Close out: trace each criterion to its executed evidence on the released revision.

## Human gates

- Confirmed brief (journeys and behaviour).
- Design acknowledgment.
- High-risk merge or ask-mode merge: a brief of the presented evidence saved beside the mission
  record. An automatic low- or medium-risk merge is an agent row.
- Release.

## Definition of Done

Every acceptance criterion maps to an executed test or journey on the released revision, both
reviews are recorded against that revision, the trace has no gaps, and the release is verified on
its target.

## Red flags

- A merge request reported as a merge.
- Green CI reported as a review verdict.
- Build started before design acknowledgment.
- A release inferred from permission to merge.

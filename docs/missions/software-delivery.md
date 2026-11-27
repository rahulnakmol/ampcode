# AI-native software delivery mission

An idea or a concrete requirement taken to verified, integrated and released software. You decide
intent and behaviour; agents own the technical design and the build. Playbook:
[`software-delivery.md`](../../skills/missioning/reference/missions/software-delivery.md).
Journeys and kickoff prompts: [Mission-driven development](../mission-driven-development.md) and
the [mission-control reference](../mission-control.md). [All missions](README.md).

## Use it when

- a feature or use case needs design, several work items and reviews;
- you want milestones merged into `dev` without approving each merge;
- the result must be released and checked on its target.

Not for a typo, a standalone review ([security review](security-review.md)) or release-only
work (`releasing` on its own).

## Start it

```text
Use delivering to start a mission for [customer outcome] in [repository].
I decide. Pre-authorize the milestone merges into dev and pushing mission
branches; ask me before any release.
```

Before drafting, the agent asks you once for: how and where it deploys, known related issues,
and target devices. It then confirms the brief with `grilling` and `crafting`, writes the design,
defends it at a whiteboard review and runs a readiness preflight on the repository, CI and
credentials. You approve, once, the brief, the design, open questions with defaults and the
pre-authorized effects.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| Kickoff | Concrete criteria with finite case lists; rendered states; technical design with contracts, ADRs and measurable NFRs; threat model when trust boundaries change; fresh design review | `grilling`, `crafting`, `architecting`, `threat-modelling`, `goldfishing`, `briefing-decisions` |
| One per design slice | Each work item built test-first and freshly reviewed; review gates one and two on the milestone's exact candidate; merge into `dev`; checkpoint report | `delivering`, `interrogating-changes` |
| Release and close-out | Promotion with a rollback plan, verified on the target; each criterion traced to executed evidence on the released revision | `releasing` |

`delivering` is the conductor; on Amp, `mission-control` enforces its gates.

## How it verifies the work

Each test for new or changed behaviour keeps its failing run on the unchanged code. A milestone
merges only when tests, CI and two fresh reviews of the same candidate pass against its criteria;
`interrogating-changes` ties each verdict to the exact patch. The rules for end-to-end evidence
before a pull request, the reviewer's model and the code's structure are defined in
[`delivering`](../../skills/delivering/SKILL.md), which is the source of truth.

## Gates you decide

- Kickoff (above).
- Release: pre-authorized at kickoff or asked with the exact plan. Permission to merge is never
  permission to release.

Every merge into `dev` is an agent row once both reviews and the evidence match the candidate.

## Done when

Every acceptance criterion maps to an executed test or journey on the released revision, both
reviews are recorded against it, and the release is verified on its target. When accessibility
is in scope, each WCAG 2.2 A and AA criterion reads pass, fail or not examined; built screens are
compared with the approved renders; the threat model is updated after the build.

## Example

**Karakeep failed-login logging for fail2ban** (validation run 3c, scores 8/8/8). Two milestones
merged into the clone's `dev`, with 125 web, 571 tRPC and 48 server tests passing and
`fail2ban-regex` matching 5 of 5 log lines. The kickoff was approved at the first ask, and the
agent refused to log the passwords people tried. Lessons now in the playbook come from the
other runs: Spliit keyboard accessibility (3b) merged changes beyond the approved plan and kept no
per-criterion WCAG result, and SplitPro group export (3a) went idle for about 7 hours after saying
it would continue.

## Adapt it

The build loop, review gates and merge policy live in
[`delivering`](../../skills/delivering/SKILL.md); review lenses in
[`interrogating-changes`](../../skills/interrogating-changes/SKILL.md); contract tools in
[mission-control](../mission-control.md).

# Product delivery operations mission

One product, operations or marketing initiative taken from workshop notes to an agreed backlog in
the tracker your stakeholders use, then tracked every week until its business goals are met.
Playbook:
[`product-operations.md`](../../skills/missioning/reference/missions/product-operations.md).
Stage-by-stage detail: [Mission-driven planning](../mission-driven-planning.md).
[All missions](README.md).

## Use it when

- you have workshop notes, transcripts or drafts and need a signed-off PRD and a ready backlog;
- an initiative is in delivery and you need a weekly status, a forecast and a risks log;
- you must show a steering committee which goals the delivered work met.

Not for building the software: ready stories go to a [software delivery](software-delivery.md)
mission.

## Start it

```text
Use missioning to run a product-operations mission for [initiative]
([product | operations | marketing]). Inputs are in [folder]. I decide;
approvers are [names and GitHub logins]. Sync to [owner/repo], showing me
each sync plan first. Pre-authorize none.
```

Before drafting, the agent asks you once for: guardrails and the re-plan trigger (such as a P85
date), hard dates (legal ones included), and dependency and release rules. You then approve, once,
the charter, its success criteria, open questions with defaults and pre-authorized effects.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| M1 Agreed backlog | Planning's gates 1 to 6: evidence and intent, PRD drafted and agreed, backlog ready and agreed, handed off | `planning` conducting `synthesizing`, `specifying`, `grooming`, `syncing` |
| M2 Delivery tracking | Weekly: flow, forecast against each milestone, risks, decision requests, guardrail actions; re-plan when the forecast misses | `steering`, `releasing` for each promotion |
| Close-out | Delivery and goal measurements recorded; `backlog.py trace` shows what each goal achieved (planning's gate 7) | `grooming` |

Stakeholders never open Amp: they sign in the tracker with `/approve`, and the file never claims a
signature the tracker does not show.

## Gates you decide

- Kickoff (above).
- Each decision request, to its named decider with a deadline and a default; at the deadline the
  default is applied and work goes on.
- A re-plan that changes a goal, a milestone date or its scope.

Planning's gates 1 to 7 are agent rows that cite the tracker, not your signature.

## Done when

Planning's gate 7 passes, every breached guardrail shows the action taken, and every blocker has
an owner, a date and an outcome.

## Example

**Kubernetes v1.38 release steering** (validation run 2b, scores 8/8/8). Weekly steering of a
real release replay forecast about a 90% chance of shipping on 16 December and raised a new risk
for gang scheduling with GPUs. It missed the owner's P85 re-plan trigger and the legal date, both
facts only she held; the owner-facts round before kickoff now asks for them. A second run, Gitea
#3217 confidential issues (2a), produced a PRD and a backlog of 7 features and 26 stories with no
validator errors, and showed a sync plan of 39 issues without applying it.

## Adapt it

Planning's stages and gates live in [`planning`](../../skills/planning/SKILL.md); the weekly loop
in [`steering`](../../skills/steering/SKILL.md); tracker adapters in
[`syncing`](../../skills/syncing/SKILL.md).

# ERP and AI transformation mission

A consulting engagement that moves a client from today's ERP, processes and ways of working to a
funded portfolio of change initiatives, AI use cases included. The client decides; the consultant
owns the evidence. Playbook:
[`transformation.md`](../../skills/missioning/reference/missions/transformation.md).
[All missions](README.md).

## Use it when

- you are discovering a client's current state and designing the target operating model;
- you need a roadmap and business case a steering committee can fund;
- you are scoring AI use cases for value, feasibility and risk.

Not for one software feature (use [software delivery](software-delivery.md)) or a single
pre-sales RFP response (use `shaping-engagements` through [Blueprinting](../blueprinting.md)).

## Start it

```text
Use missioning to run a transformation mission for [client]: move [scope, such as
finance on Oracle EBS] to a funded portfolio of initiatives. I decide; [client
sponsor, role] confirms the operating model and [steering committee] funds the
portfolio. Engagement root: [path]. Pre-authorize none.
```

Before drafting, the agent asks you once for: the discount rate and horizon, how many
initiatives to fund, the funding lines, and your firm's own delivery capabilities. You then
approve, once, the charter, the engagement's decision and audience, and a hypothesis tree with a
day-one answer the evidence will confirm or kill.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| Kickoff | Settle the decision and audience; start the engagement; draft the hypothesis tree | `grilling`, `blueprinting` |
| M1 Discovery | Workshops and questionnaires; every source retained; contradictions recorded | `discovering-requirements`, `distill` for video research |
| M2 Target operating model | Operating model and functional specification from the evidence; written client confirmation | `designing-functions` |
| M3 Roadmap and business case | Wave plan, one charter per initiative, NPV and payback computed by script; review and publish | `shaping-engagements`, `reviewing-engagements`, `publishing-engagements` |
| M4 Portfolio and handover | Steering committee decision recorded; each funded initiative handed to a planning mission | `planning` |

`blueprinting` is the conductor: its client-authority and publication rules override the
playbook. `roadmapping` and `researching` are planned; until they exist the agent writes the wave
plan and cites every market claim by hand, labelled "manual, no skill".

## Gates you decide

- Kickoff (above).
- The operating model baseline: written client confirmation, passed only when
  `engagement.py baseline <decision-id>` reports `ready: true`.
- The funded portfolio, at the steering committee.
- Each publication or client-facing send.

## Done when

Each funded initiative has a charter, an owner who agreed, a business case whose numbers trace to
evidence or labelled assumptions, a stage gate and a planning mission ready to start. Source
contradictions are in a register, estimates are ranges, every judgement-based score has a
data-confidence label, and each cost maps to a budget line.

## Example

**SSA AI use-case portfolio** (validation run 1b, scores 8/7/8). The mission produced a scored
portfolio of AI use cases with a business case. The first kickoff brief was rejected because it
named an agent thread as decision owner; the fifth revision was approved. Two lessons are now in
the playbook: the agent found the 7% discount rate by research instead of asking the owner (the
discount rate is now an owner fact asked before kickoff), and no score carried a data-confidence
label although judgement-based value had 40% of the weight (now in the Definition of Done).

## Adapt it

Change the owner facts in `reference/charter.md` ("Owner facts by playbook"), the milestones in
the playbook's Steps, and engagement rules in [`blueprinting`](../../skills/blueprinting/SKILL.md).

# Playbook: ERP and Agile AI transformation

## When to use

A consulting engagement that moves a client from today's ERP, processes and ways of working to a
funded portfolio of change initiatives, including AI use cases. The client decides; the
consultant owns the evidence. Not for one software feature (use `software-delivery`).

## Skills

- `grilling`: the engagement's decision and audience.
- `blueprinting`: the conductor for discovery, functional design, operating model, pre-sales and
  publishing. Follow its records, client-authority and publication rules; they override this
  playbook. Domain skills: `discovering-requirements`, `designing-functions`,
  `shaping-engagements`, `publishing-engagements`, `reviewing-engagements`; `distill` for video
  research.
- Issue tree and day-one hypothesis in `discovering-requirements`, and a full target operating
  model in `designing-functions`: planned enhancements, wave 3. Fallback: write the issue tree and
  the operating model (capability map, organisation and RACI, governance, sourcing, KPIs) as
  ordinary blueprinting notes, labelled "manual, no skill".
- `researching` (planned, wave 3). Fallback: cite every market or benchmark claim with a URL and
  date, or mark it unverified.
- `roadmapping` (planned, wave 3). Fallback: a wave plan and one charter per initiative with
  owner, benefits and their counting rule, cost, dependencies and funding gate; compute NPV and
  payback with `blueprinting/scripts/estimate.py` or a script, never by the model.
- `planning`: one planning mission per funded initiative at the end.

## Steps

1. Charter the mission with `missioning`; Approvers include the named client authorities.
2. Use `grilling` to settle the engagement's decision and audience.
3. Start or resume the engagement with `blueprinting`; keep `mission.md` as a working note.
4. Draft the hypothesis tree and a day-one answer for evidence to confirm or kill.
5. Prepare workshops and questionnaires; retain every source; record contradictions.
6. Design the target operating model and functional specification from the evidence.
7. Obtain written client confirmation of the operating model baseline.
8. Build the roadmap and business case; every number traces to evidence or a labelled assumption.
9. Review conclusions with `reviewing-engagements`; publish with `publishing-engagements`.
10. Present the funded portfolio to the steering committee; record its decision.
11. Hand each funded initiative to a `planning` mission; close out.

## Human gates

- The decision and audience of the engagement.
- The hypothesis tree.
- The operating model baseline: written client confirmation, as `blueprinting` already requires.
  The gate passes only when `engagement.py baseline <decision-id>` reports `ready: true`; Source
  is `written: <decision id>`.
- The funded portfolio at the steering committee.
- Each publication or client-facing send: content, audience and destination, as `blueprinting`
  requires.

## Definition of Done

Each funded initiative has a charter, a named owner who agreed, a business case whose numbers
trace to evidence or labelled assumptions, a stage gate, and a planning mission ready to start.
The steering committee decision is recorded with the named client authority and version.

## Red flags

- A consultant recap or transcript recorded as client approval.
- A business-case number the model produced instead of a script.
- An AI use case scored without value, feasibility and risk.
- Client records written into this skills repository.

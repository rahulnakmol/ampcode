# PRD template

Copy the core, then insert the section for the initiative's domain after Requirements. Keep headings; delete guidance
lines in italics once filled. IDs: drivers `D-n`, requirements `R-n`, acceptance criteria `AC-n`
(numbered across the PRD, written in bold where defined), open questions `Q-n` (cite the
ledger's `Qn` when one came from there), evidence `En` from `evidence.md`.

## Core (every domain)

```markdown
# <Initiative title>

Status: draft | in review | signed off  ·  Owner: <name>  ·  Approvers: <name (@handle)>, …
Last change: <date>, <what changed>

## In short
*Five lines for an approver reading on a phone: what changes, for whom, the numbers that decide
success, what it costs, and what signing this approves. No IDs, codes, or tool names.*

## Problem
*Who is hurt, how often, how badly; cite evidence.*

## Business drivers
- **D-1 <Cost | Revenue | Risk | Compliance | Customer | Strategy>:** <statement with a number or
  observable condition> (E…)

## Goals
| Goal | Metric and source | Baseline | Target | By | Serves |
| --- | --- | --- | --- | --- | --- |
| <Outcome in words> | <what is measured, where> | <today> | <success> | <date> | D-1 |

*Each metric says its unit and how it is counted (who or what counts once, over which period),
and compares like with like: the same months last year, or a comparison group. Write limits as
`at most 80` or `at least 85%`. When several parts share one target, show how they add up, and
give the goal a leading measure with a checkpoint date before the target date. For
a discovery, success is a decision backed by evidence, go or no-go, not a "go".*

*Every guardrail and every checkpoint says what happens when it is missed: who decides, by
when, and the default (pause, stop, cut, or carry on). "Complaints above 7.1 per 1,000 for 2
weeks pause the pilot until Elena decides, within 5 business days" acts; "flag any value
above 7.1" only reports. A guardrail whose harm shows up months later (fraud found after
payment) also gets a measure that moves within weeks.*

## Users and stakeholders
*Who uses the result, who is affected, who approves; from the ledger's stakeholder map.*

## Scope
- In: …
- Non-goals: …

## Alternatives considered
| Option | Why not chosen (or why chosen) |
| --- | --- |
| Do nothing | … |

## Requirements
- **R-1 <Requirement as an outcome>.** (D-…, E…)
  - **AC-1** <Measurable condition with a number, time, count, or date>
  - **AC-2** …

## Constraints and assumptions
- Decision (who, date): …
- Assumption (revisit if …): …

## Risks
| Risk | Likelihood | Impact | Owner | Mitigation |
| --- | --- | --- | --- | --- |

## Edge cases and misuse
| Case | Severity (1 to 4) | Handling |
| --- | --- | --- |

*Work through each lens: misuse and gaming (fraud, incentives, bulk actions, permissions);
money after the fact (refunds, corrections, failed payments, the order jobs run in); people at
risk (no smartphone, children, bereaved, vulnerable, safety, urgent cases); slips (every channel
moves with a new date); missing or unflagged data. Severity 4 means harm or money nobody would
notice: its handling is a control with a threshold that blocks, holds, or stops, never only a
count or a report. Every hold, pause, or manual step has a deadline and a default outcome, and
the person affected is told.*

## Rollout and milestones
*Milestones (PIs, releases, campaign phases) with dates, and what each must contain.*

*Go-live and spend gates: list everything that must be finished before work goes live, reaches
customers, or commits money (an assessment, a contract, an approval, a sign-off). Each is an
acceptance criterion on the finished item: "signed, with 0 open high findings", never "a draft
exists" or "has been reviewed". When someone outside the team approves (a bank, a regulator, a
patient group), give the submission date, their decision date, one resubmission that still
meets the deadline, and what slips if it fails. They approve the final artefact people will
see, not only a script or a draft.*

## Open questions
- **Q-1** … ; answers: <who>, by <date>

## Change log
- <date>: <what changed for the reader>
```

## Product section

```markdown
## Experience
*Main journeys and states, including failure and empty states; link `crafting` output if any.*

## Functional requirements
*Use R-n/AC-n above; add non-functional requirements (performance, security, accessibility)
as their own R-n with measurable AC-n.*

## Data and integrations
*Systems touched, data owned, migrations.*
```

## Operations section (operations challenge or new way of working)

```markdown
## Current process (as is)
| Step | Who | System | Time | Pain (E…) |
| --- | --- | --- | --- | --- |

## Future process (to be)
| Step | Who | System | Time | Change |
| --- | --- | --- | --- | --- |

## Roles (RACI)
| Activity | Responsible | Accountable | Consulted | Informed |
| --- | --- | --- | --- | --- |

## Automation
*Each automation: trigger, input, output, failure handling, owner. One R-n each.*

## Reporting
*Each report or dashboard: audience, question it answers, refresh time, source. One R-n each.*

## Controls and compliance
*Approvals, segregation of duties, audit evidence the new process must keep producing.*

## Change management
*Training, communication, cut-over, and how the old way is retired.*
```

## Marketing section (campaign or launch)

```markdown
## Audience
*Segments with size, titles, company size, regions; exclusions.*

## Message
*Headline, proof points, call to action; link the messaging brief.*

## Channels and assets
| Channel | Asset | Owner | Live dates | KPI |
| --- | --- | --- | --- | --- |

## Budget
*Total and per channel, with the rule for moving budget.*

## Funnel and measurement
*Definitions (registration, MQL, accepted opportunity), tracking (UTM scheme), dashboard.*

## Sales hand-off
*Routing, follow-up commitment, script or play.*
```

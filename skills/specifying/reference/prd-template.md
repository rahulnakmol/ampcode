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

## Problem
*Who is hurt, how often, how badly; cite evidence.*

## Business drivers
- **D-1 <Cost | Revenue | Risk | Compliance | Customer | Strategy>:** <statement with a number or
  observable condition> (E…)

## Goals
| Goal | Metric and source | Baseline | Target | By | Serves |
| --- | --- | --- | --- | --- | --- |
| <Outcome in words> | <what is measured, where> | <today> | <success> | <date> | D-1 |

## Users and stakeholders
*Who uses the result, who is affected, who approves; from the ledger's stakeholder map.*

## Scope
- In: …
- Non-goals: …

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

## Rollout and milestones
*Milestones (PIs, releases, campaign phases) with dates, and what each must contain.*

## Open questions
- **Q-1** … ; answers: <who>, by <date>

## Change log
- <date>: <change>; fresh-context review: <result>
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

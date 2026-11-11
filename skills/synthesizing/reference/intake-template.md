# Intake template

Copy into `intake.md` beside `evidence.md`. One dated section per intake session; never rewrite
an old one. Cite evidence IDs everywhere; label anything not confirmed by the owner `assumed`.

```markdown
# Intake: <session or initiative> (<date>)

Status: draft | confirmed by <owner>, <date>
Inputs: SRC1–SRCn (see evidence.md) · Existing backlog: <path or "none">

## Intent
<One or two sentences: the outcome, who benefits, why now.> (E…)
Ends in: <a new PRD | a PRD change | a backlog building session | a grooming session>

## Placement
| Ask | Evidence | Placement | Status | Next |
| --- | --- | --- | --- | --- |
| <the ask in a few words> | E… | New initiative · New goal under I-n · New feature under G-n · Change to F-n · Bug under F-n · Change to B-n · Feedback on F-n · Measurement for G-n · Context · Approvers change · Parked (reason) | confirmed / assumed | specifying / grooming / agenda only / none |

## Candidates
### Drivers (new initiatives and goals only)
- <Cost | Revenue | Risk | Compliance | Customer | Strategy>: <statement with the number> (E…)

### Goals
| Goal | Metric and source | Baseline | Target | By | Serves | Status |
| --- | --- | --- | --- | --- | --- | --- |

### Features
| Feature | Under | Description | Draft benefit hypothesis | Evidence | Status |
| --- | --- | --- | --- | --- | --- |

### Story seeds
| Seed | Feature | As a … | I want … | So that … | Numbers for acceptance | Evidence |
| --- | --- | --- | --- | --- | --- | --- |

### Measurements
| Goal | Value | At | Source | Evidence |
| --- | --- | --- | --- | --- |

### Bugs and feedback
| Item | Feature | Observed / said | Who | Evidence |
| --- | --- | --- | --- | --- |

## Decisions and assumptions
- Decision (<who>, <date>): … (E… for the interview row)
- Assumption (revisit if …): …

## Still open
- <question>; owner: <name>; needed before: <session or gate>

## Next session
Skill: <specifying | grooming> · Attendees: <who must be there> · Time box: <minutes>
1. <Agenda item, most consequential first>: decide <what>.

## Pick-up prompt
<Self-contained prompt for the next session: the intent, the paths to evidence.md, intake.md,
and backlog.json, the first agenda item, and what done looks like.>
```

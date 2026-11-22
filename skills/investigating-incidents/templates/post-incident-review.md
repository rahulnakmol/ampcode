# Post-incident review: <one line that names the failure, not a person>

- Severity: <SEV-1 | SEV-2 | SEV-3 | SEV-4, from the table in SKILL.md section 5>
- Incident window: <2026-09-19T08:30Z to 2026-09-19T08:52Z>
- Environment: <system, region, tenant or channel>
- Deployed revision: <release or commit that was running; "unknown" if not established>

## Impact

<Who was affected, how many, for how long, with each number and where it came from.>

## Timeline

Every time has a date and a UTC offset (`Z`, `UTC` or `+05:30`). Rows run in order.

| Time | Event | Source |
| --- | --- | --- |
| <2026-09-19T08:30Z> | <what happened> | <log, metric, deployment record, person> |

## Hypotheses

At least two. Status is `open`, `supported`, `confirmed` or `rejected`. Evidence is required,
for a rejected hypothesis too: the evidence that tested it. List each fact that argues against a
hypothesis under that hypothesis, even when it is also evidence for a rival; otherwise write
"none found in <what you read>".

| ID | Hypothesis | Status | Evidence | Counter-evidence |
| --- | --- | --- | --- | --- |
| H1 | <explanation> | <status> | <what supports it> | <what argues against it> |
| H2 | <competing explanation> | <status> | <what supports it> | <what argues against it> |

## Root cause

Keep exactly one of these two lines and delete the other, and this note. A section that keeps
both fails P5. Beside "not established", write only lines that start with `Open:`.

Root cause: not established.
Root cause (H1): <one sentence, only when H1 is confirmed>.

Open: <hypotheses still open and the evidence that would decide them; only with "not established">

## Contributing conditions

- <a condition that made the failure possible, larger or slower to detect>

## Mitigation

- <time with offset>: <what stopped or limited the impact, who did it, the effect, and whether it
  is still in place>

## Actions

One block per action. Kind is `durable fix`, `missing alert` or `prevention`. Mitigation does not
go here. `pir_check.py bugs` replaces "to file" with the bug ID.

### A1: <the result, in at most 120 characters>

- Kind: durable fix
- Owner: <one person the sources name, or "to assign (F-n owner: <name>)">
- Backlog: to file
- Observed: <what happened, with the evidence>
- Expected: <what should happen, with a number; mark a number you propose "(proposed)">
- Steps:
  1. <first step to reproduce>
  2. <next step>
- Acceptance:
  - Given <state>, when <event>, then <result with a number>.
- Rationale: <why this action removes or reduces the cause>
- Expected signal: <what changes in which telemetry when it works>
- Risk: <what this change could break>
- Verification: <how and where the result is measured>
- Rollback or stop: <how to undo it, or when to stop it>

## Missing evidence

- <telemetry that was not retained or not read, and the bounded query that would read it>

# Runbook: <service> <SLO name>

Copy this file once per alert. Two alerts of one SLO may share a runbook when the response is
the same; name both alert IDs. The responder reads it at 3 a.m. with no other context: write
short steps, exact links and exact commands. Never put secrets or customer data here.

## Alerts

| Alert | SLO | NFR | Severity | Fires when |
| --- | --- | --- | --- | --- |
| <ALERT-1> | <SLO-1> | <NFR-3> | page | Burn rate above 14.4× over 1 hour and over 5 minutes |
| <ALERT-2> | <SLO-1> | <NFR-3> | page | Burn rate above 6× over 6 hours and over 30 minutes |

## What it means

<One or two sentences: which users are affected and how. Example: "More than 1.44 % of Export
API requests fail. At this rate the 30-day error budget is gone in about 2 days.">

## Look first

1. Dashboard: <link to the SLO dashboard: SLI, burn rate, budget remaining>.
2. Recent changes: <link to deployments and configuration changes for the last 24 hours>.
3. Dependencies: <links to the health pages of the database, queue and identity provider>.
4. Query: <the bounded query that splits errors by operation and status, with its time window>.

## Mitigate

| Symptom | Action | Expected signal | Stop or roll back when |
| --- | --- | --- | --- |
| Errors began with a deployment | <roll back with the release's rollback plan> | Burn rate under 1× within 15 minutes | <condition> |
| A dependency fails | <fail over, shed load, or turn off the feature flag> | <signal> | <condition> |

Each action changes production. Follow your incident process: who may run it, and who approves.

## Escalate

- After <15 minutes> without a clear cause: <team or person, and how to reach them>.
- Customer impact over <threshold>: <incident commander, status page owner>.

## After the incident

- Record the timeline, the cause and the fix in the post-incident review.
- File a backlog bug for each missing alert, signal or runbook step.
- Note the budget remaining for the SLO and whether releases slow down under its error-budget
  policy.

## Firing evidence

| Date | Environment | How it fired | Evidence |
| --- | --- | --- | --- |
| <2026-11-18> | <staging> | <fire drill or rule test> | <link to the drill record or CI run> |

An alert without a row here, from outside production, is not proven. Copy each row into the
alert's `firing` record in the SLO file.

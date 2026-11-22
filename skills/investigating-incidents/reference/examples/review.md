# Post-incident review: order exports stalled for 47 minutes after a queue change

- Severity: SEV-3
- Incident window: 2026-10-07T07:31Z to 2026-10-07T08:22Z
- Environment: production, order-export worker, Azure Service Bus namespace sb-orders-prod
- Deployed revision: release 2026.10.07-2 (commit 9b41e07)

## Impact

312 order exports reached the warehouse up to 47 minutes late. No order was lost.
Source: the export audit table, read for 07:30Z to 08:30Z.

## Timeline

| Time | Event | Source |
| --- | --- | --- |
| 2026-10-07T07:31Z | Release 2026.10.07-2 sets the queue lock duration to 30 seconds | Deployment record |
| 2026-10-07T13:05+05:30 | First message lock lost; the message is delivered again | Application Insights exceptions |
| 2026-10-07T07:52Z | Warehouse team reports late exports in the shared channel | Support ticket |
| 2026-10-07T08:04Z | On-call engineer scales the worker from 2 to 6 instances | Azure activity log |
| 2026-10-07T08:22Z | Export lag back under 2 minutes | Export audit table |

## Hypotheses

| ID | Hypothesis | Status | Evidence | Counter-evidence |
| --- | --- | --- | --- | --- |
| H1 | Exports take longer than the new 30-second lock, so locks expire and messages loop | confirmed | 95th percentile export time was 41 seconds; 1,104 lock-lost exceptions in the window, none before 07:31Z | None found in the exceptions for 07:00Z to 08:30Z |
| H2 | The warehouse API slowed down and caused the backlog | rejected | Warehouse support ticket mentions slow responses that morning | Warehouse API dependency calls stayed under 400 ms at the 95th percentile in the window |

## Root cause

Root cause (H1): release 2026.10.07-2 cut the message lock to 30 seconds, below the 41-second
export time, so messages were delivered again and again.

## Contributing conditions

- The queue change was reviewed as configuration only, without a load test.
- No alert watches lock-lost exceptions or export lag.

## Mitigation

- 2026-10-07T08:04Z: the on-call engineer scaled the worker from 2 to 6 instances. Lag fell under
  2 minutes by 08:22Z. The 6 instances are still running.

## Actions

### A1: Set the export lock above the slowest export time

- Kind: durable fix
- Owner: Ana Silva
- Backlog: to file
- Observed: The 30-second message lock expired during 41-second exports and 1,104 messages were delivered again.
- Expected: Each export message is processed once, with the lock renewed or set above the 99th percentile export time.
- Steps:
  1. Deploy release 2026.10.07-2 to staging.
  2. Queue 500 export messages whose exports take 40 seconds each.
  3. Count lock-lost exceptions for 15 minutes.
- Acceptance:
  - Given 500 exports that take 40 seconds each, when the worker processes them, then 0 lock-lost exceptions are logged.
  - Given the same run, when it ends, then each of the 500 orders is exported exactly once.
- Rationale: a lock that outlasts the slowest export stops the redelivery loop (H1).
- Expected signal: lock-lost exceptions fall to 0 in Application Insights after release.
- Risk: a longer lock delays redelivery of a message whose worker crashed.
- Verification: the staging run in the acceptance criteria, then 24 hours of production exceptions.
- Rollback or stop: revert to the 2026.10.07-1 queue settings if export lag passes 10 minutes.

### A2: Alert on export lag and lock-lost exceptions

- Kind: missing alert
- Owner: Ana Silva
- Backlog: to file
- Observed: No alert fired; the warehouse team reported the delay 17 minutes after the first lost lock.
- Expected: On-call is paged within 5 minutes of the condition when export lag passes 10 minutes or lock-lost exceptions pass 20 in 5 minutes (proposed).
- Steps:
  1. Replay the 7 October lock-lost exceptions into the staging workspace.
  2. Watch the alerting system for 15 minutes.
- Acceptance:
  - Given export lag above 10 minutes for 5 minutes, when the alert rule evaluates, then 1 page reaches on-call within 5 minutes.

### A3: Load-test queue setting changes before release

- Kind: prevention
- Owner: Ana Silva
- Backlog: to file
- Observed: The lock change shipped as configuration with no load test.
- Expected: A change to a queue setting runs the export load test in the pipeline before release.
- Steps:
  1. Change the lock duration in a pull request.
  2. Run the release pipeline.
- Acceptance:
  - Given a pull request that changes a queue setting, when the pipeline runs, then the 15-minute export load test runs and its result is attached to the release.

## Missing evidence

- Worker CPU and memory before 07:30Z were not retained. A bounded query for 06:30Z to 07:30Z on
  the worker's resource ID would show whether 2 instances were already near their limit.

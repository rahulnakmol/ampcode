# Risks, issues and decisions: pilot UK01

Week of: 2026-11-23. Replace the example rows with your own. Keep closed rows; never delete a
row. Check this file with `scripts/raid_check.py`.

## Risks

A risk can still happen. Each one has an owner, a date to review it and a response.

| ID | Risk | Owner | Date | Response | State |
| --- | --- | --- | --- | --- | --- |
| R1 | The bank's test window may close before the pilot is ready | Elena Petrova | 2026-12-04 | Ask the bank for a second test window | open |

## Issues

An issue is happening now. Each one has an owner, a date it must be solved by and an action.

| ID | Issue | Owner | Date | Action | State |
| --- | --- | --- | --- | --- | --- |
| I1 | The payment file fails the bank's format check | Sam Okafor | 2026-11-27 | Fix the header record and send a new test file | open |

## Decisions

A decision request names who decides, a deadline and the default that applies if nobody decides
by then. The default is something the mission contract lets the agent do alone; for a re-plan,
keep the date and the scope and escalate. After the deadline, write
`default applied: <what, date>` or `decided: <what> (<decider>, <date>)`. An applied default is
not an approval: the decision stays with the decider.

| ID | Decision needed | Decider | Deadline | Default | Outcome |
| --- | --- | --- | --- | --- | --- |
| D1 | Move the pilot from 4 December to 18 December? | Priya Raman | 2026-11-20 | Keep 4 December and the full scope; escalate to Rahul | default applied: kept 4 December and the scope; escalated to Rahul (2026-11-21) |
| D2 | Add a second tester for the bank tests? | Rahul | 2026-11-30 | No second tester | open |

## Guardrails

A guardrail is a limit the mission contract sets, with the action to take on a breach. Copy the
limit from the contract. On a breach, write the action taken and its date.

| ID | Guardrail | Limit | Value | State | Action taken |
| --- | --- | --- | --- | --- | --- |
| G1 | Work in progress | at most 4 | 5 | breached | No new starts until work in progress is 4; told Rahul on 2026-11-24 |
| G2 | Escaped defects per week | at most 2 | 0 | ok | - |

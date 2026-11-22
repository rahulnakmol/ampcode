# Risks, issues and decisions: pilot UK01

Week of: 2026-11-16.

## Risks

| ID | Risk | Owner | Date | Response | State |
| --- | --- | --- | --- | --- | --- |
| R1 | The bank's test window may close before the pilot is ready | Elena Petrova | 2026-12-04 | Ask the bank for a second test window | open |

## Issues

| ID | Issue | Owner | Date | Action | State |
| --- | --- | --- | --- | --- | --- |
| I1 | The payment file fails the bank's format check | Sam Okafor | 2026-11-27 | Fix the header record and send a new test file | open |

## Decisions

| ID | Decision needed | Decider | Deadline | Default | Outcome |
| --- | --- | --- | --- | --- | --- |
| D1 | Add Ireland to the pilot? | Rahul | 2026-11-24 | Keep the pilot to the UK only | decided: UK only (Rahul, 2026-11-20) |

## Guardrails

| ID | Guardrail | Limit | Value | State | Action taken |
| --- | --- | --- | --- | --- | --- |
| G1 | Work in progress | at most 3 | 3 | ok | - |
| G2 | Escaped defects per week | at most 2 | 0 | ok | - |

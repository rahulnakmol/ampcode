# Close the books in three business days

Status: signed off  ·  Owner: Priya Raman  ·  Approvers: Priya Raman (@priya-r), Tom Okafor (@tokafor)
Last change: 2027-01-14, FX rounding tolerance added to AC-3 after Tom's comment

## Problem
UK01 locks its ledger on business day 7, sometimes 8 (E3), and the board pack follows on day 10
(E1). About 60 hours a month go to matching bank lines to invoices by hand (E2, E5), and the
controller sees late close tasks only around day 5 (E9), because 74 checklist tasks often have
no named owner (E7).

## Business drivers
- **D-1 Cost:** cut the 60 hours a month of manual bank reconciliation, so the 2 people doing most
  of it can clear the 3-week supplier-query backlog (E5, E15).
- **D-2 Control:** give the group controller ledger-locked numbers for the board pack by business
  day 4, as the audit committee asked in its 2026 findings (E1).

## Goals
| Goal | Metric and source | Baseline | Target | By | Serves |
| --- | --- | --- | --- | --- | --- |
| Close duration falls from 7 to 3 business days | Business days from period end to ledger lock, from the close calendar | 7 | 3 | 2027-06-30 | D-2 |
| Manual reconciliation effort falls from 60 to 10 hours a month | Hours on the "bank reconciliation" time code per month across AP | 60 | 10 | 2027-04-30 | D-1 |

## Users and stakeholders
AP clerks run reconciliation and exceptions; the close team (8 task owners in UK01) runs the
calendar; the group controller and Finance Operations lead own the outcome and sign off;
Finance systems builds and runs the automation.

## Scope
- In: UK01 pilot in the February close; all EU entities by 28 May (E13).
- Non-goals: replacing the ERP general ledger; changing intercompany settlement terms (E12);
  forecasting the close date (E20, declined for now).

## Requirements
- **R-1 The close runs to a three-day calendar with one owner per task.** (D-2, E7, E8, E14)
  - **AC-1** Every one of the 74 UK01 close tasks has exactly one named owner, a due day between
    D+1 and D+3, and its predecessors, published before 2027-02-12.
  - **AC-2** All 8 named task owners are trained on the calendar and the exception report before
    2027-02-19 (E17).
- **R-2 Bank reconciliation runs nightly without manual matching.** (D-1, E2, E4, E5, E6)
  - **AC-3** Every bank line matching exactly one open invoice on the agreed keys, including
    differences of at most 0.05 GBP of FX rounding, is posted by 02:30 (E10, E11).
  - **AC-4** Every unmatched line is in an exception report in the AP folder by 07:00 (E4).
- **R-3 The controller sees close progress daily.** (D-2, E9)
  - **AC-5** A dashboard shows done, late, and blocked tasks per entity and close day, refreshed at
    08:00 and 14:00.

## Constraints and assumptions
- Decision (Tom Okafor, 2027-01-12): pilot target is 4 days; the 30 June target is 3 (E14, E18, E19).
- Constraint: MT940 is available now; CAMT.053 needs 4 weeks' notice (E11). A 3-day spike decides
  the format and match keys before the automation is built.
- Assumption (revisit if the pilot auto-match rate is below 70%): most lines match exactly one
  invoice (E2).

## Risks
| Risk | Likelihood | Impact | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| FX rounding floods the exception report | High | High | Lukas Brenner | 0.05 GBP tolerance in AC-3 (E10) |
| Owners miss calendar days in the pilot | Medium | High | Priya Raman | Training (AC-2); daily stand-up in close week |
| Bank re-sends a file and lines post twice | Medium | High | Lukas Brenner | Idempotent posting; tracked as a bug if seen |

## Rollout and milestones
- **PI 27.1: pilot UK01** (due 2027-02-26): R-1 and R-2 for UK01.
- **PI 27.2: all EU entities** (due 2027-05-28): R-1 and R-2 rolled out; R-3 dashboard.

## Open questions
- **Q-1** Bank format and match keys: answered by the spike (story S-1), Lukas Brenner, by 2027-01-21.

## Change log
- 2027-01-12: first draft from evidence; fresh-context review: 2 gaps (no AC for training; FX
  rounding untreated), both fixed.
- 2027-01-14: FX tolerance added to AC-3 after review comments; signed off by priya-r and tokafor.

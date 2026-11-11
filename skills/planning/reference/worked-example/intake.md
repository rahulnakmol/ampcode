# Intake: month-end close (2027-01-12)

Status: confirmed by Priya Raman, 2027-01-12
Inputs: SRC1–SRC3, interview SRC4 (see evidence.md) · Existing backlog: none

## Intent
Finance closes the books in 3 business days instead of 7, so the board pack carries
ledger-locked numbers by business day 4 and the AP team stops matching bank lines by hand.
(E1, E2, E3, E5, E14)
Ends in: a new PRD

## How the intake got here
Draft intent before questions: "Automate bank reconciliation." The ledger showed two more
causes of the slow close (no task owners, E7; late visibility, E9), so the draft became the
close itself. Two grilling rounds:

- **Round 1** (3 questions): Is the outcome the 3-day close rather than the reconciliation
  automation? Yes. Which target holds, 3 or 4 days (E14 vs E18)? Both: 4 for the pilot, 3 by
  June (E19). Should the dashboard forecast the close date (E16)? Not now (E20).
- **Round 2** (1 question): One initiative, or separate ones for reconciliation and the
  calendar? One, owned by Priya, because both serve the same close target (E21).

## Placement
| Ask | Evidence | Placement | Status | Next |
| --- | --- | --- | --- | --- |
| Close in 3 business days | E1, E3, E14, E19 | New initiative (operations) | confirmed | specifying |
| Stop manual bank reconciliation | E2, E4, E5 | Goal and feature in that initiative | confirmed | specifying |
| Named owner and due day per close task | E7, E8 | Feature in that initiative | confirmed | specifying |
| Controller sees late tasks daily | E9 | Feature in that initiative | confirmed | specifying |
| Train the team before the pilot | E17 | Story seed under the calendar feature | confirmed | specifying, then grooming |
| Forecast the close date | E16, E20 | Parked: out of scope until two closes on the dashboard | confirmed | none |

## Candidates
### Drivers
- Cost: cut the 60 hours a month of manual reconciliation, freeing 2 people for the 3-week
  supplier-query backlog (E5, E15).
- Control: ledger-locked numbers for the board pack by business day 4, per the audit committee
  (E1).

### Goals
| Goal | Metric and source | Baseline | Target | By | Serves | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Close duration | Business days from period end to ledger lock, close calendar | 7 | 4 in the pilot, 3 | 2027-02-26, 2027-06-30 | Control | confirmed (E19) |
| Reconciliation effort | Hours on the "bank reconciliation" time code per month | 60 | 10 | assumed 2027-04-30 | Cost | target confirmed, date assumed |

### Features
| Feature | Under | Description | Draft benefit hypothesis | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| Nightly bank reconciliation | Reconciliation effort | Match bank lines to open invoices overnight; exceptions to a report | Hours fall below 20 in the first pilot month | E2, E4, E6 | confirmed |
| Three-day close calendar | Close duration | One owner and due day per task | Pilot closes in 4 days or fewer | E7, E8 | confirmed |
| Close progress dashboard | Close duration | Done, late, blocked tasks by entity and day | No entity more than 1 day late | E9 | confirmed |

### Story seeds
| Seed | Feature | As a … | I want … | So that … | Numbers for acceptance | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Bank format spike | Nightly reconciliation | finance systems analyst | to decide MT940 or CAMT.053 and the match keys | we build once | file arrives about 01:00; CAMT needs 4 weeks' notice | E6, E11 |
| Exception report | Nightly reconciliation | AP clerk | unmatched lines listed each morning | I clear them before the cash call | before 10:00 | E4 |
| Close team training | Three-day calendar | close task owner | a walkthrough before the pilot | I run my tasks without help | before the February close | E17 |

### Bugs and feedback
None.

## Decisions and assumptions
- Decision (Tom Okafor, 2027-01-12): pilot target 4 days, June target 3 (E19).
- Decision (Priya Raman, Tom Okafor, 2027-01-12): no close-date forecast for now (E20).
- Decision (Priya Raman, 2027-01-12): one operations initiative, owner Priya (E21).
- Assumption (revisit if Finance Ops disagrees): the reconciliation goal is due 2027-04-30,
  two closes after the pilot.

## Still open
- FX rounding: what difference may auto-post (E10, Q3)? Owner: Tom Okafor; needed before the
  PRD's reconciliation criteria.
- Bank file format and match keys (Q1). Owner: Lukas Brenner; becomes the spike story.

## Next session
Skill: specifying · Attendees: Priya Raman, Tom Okafor · Time box: 45 minutes
1. Confirm the drivers' wording and the reconciliation goal's date.
2. Decide the FX rounding tolerance.
3. Agree requirements and acceptance criteria for the three features.

## Pick-up prompt
Use specifying to write the PRD for the month-end close initiative (operations). Read
`evidence.md` and `intake.md` in this folder; the intake is confirmed, so do not re-ask its
decisions. Start with the FX rounding tolerance (still open). Done when the PRD checklist
passes, a fresh reader has reviewed it, and the initiative and goals are seeded in
`backlog.json`.

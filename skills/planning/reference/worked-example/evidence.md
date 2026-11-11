# Evidence: Close the books in three business days

## Sources
| ID | Source | Kind | Date | Participants |
| --- | --- | --- | --- | --- |
| SRC1 | inputs/2027-01-08-close-workshop.vtt | transcript | 2027-01-08 | Tom Okafor (Group Controller), Priya Raman (Finance Operations lead), Ana Costa (AP clerk, UK01), Lukas Brenner (Finance systems) |
| SRC2 | inputs/2027-01-08-minutes.md | minutes | 2027-01-08 | same as SRC1 |
| SRC3 | inputs/2027-01-12-priya-draft.md | rough draft | 2027-01-12 | Priya Raman |
| SRC4 | intake interview (intake.md) | interview | 2027-01-12 | Priya Raman (owner), Tom Okafor |

## Evidence
| ID | Kind | Statement | Who | Where | Confidence |
| --- | --- | --- | --- | --- | --- |
| E1 | driver | The audit committee's 2026 findings want ledger-locked numbers by business day 4; the board pack currently goes out on day 10. | Tom Okafor | SRC1 00:01:30; SRC2 §1 | paraphrased |
| E2 | pain | "We lose three days just ticking bank lines against invoices." | Priya Raman | SRC1 00:04:12 | quoted |
| E3 | metric | UK01 locks the ledger on business day 7, some months day 8. | Tom Okafor | SRC1 00:01:30; SRC2 §1 | paraphrased |
| E4 | need | AP wants to start the day on exceptions only, with the exception list before the 10:00 cash call. | Ana Costa | SRC1 00:05:10 | paraphrased |
| E5 | metric | Manual bank reconciliation takes about 60 hours a month across AP, logged to the "bank reconciliation" time code; target under 10. | Priya Raman | SRC1 00:04:12; SRC3 "Numbers" | paraphrased |
| E6 | constraint | The bank file arrives around 01:00. | Ana Costa | SRC1 00:05:10 | paraphrased |
| E7 | pain | The close checklist has 74 tasks in a spreadsheet; about half name "Finance" as owner rather than a person. | Tom Okafor | SRC1 00:07:55; SRC2 §2 | paraphrased |
| E8 | idea | One named owner and a due day per task would remove most waiting: "People wait because nobody knows it's their turn." | Priya Raman | SRC1 00:09:02 | quoted |
| E9 | pain | The controller learns a task is late only around business day 5. | Tom Okafor | SRC1 00:07:55; SRC2 §2 | paraphrased |
| E10 | risk | Many bank lines differ from the invoice by a few pence of FX rounding; sending them to exceptions would make the report useless. | Ana Costa | SRC1 00:13:30 | paraphrased |
| E11 | constraint | The bank can send MT940 today; CAMT.053 needs 4 weeks' notice to Barclays. IT does not want to build twice. | Lukas Brenner | SRC1 00:11:45; SRC2 §4 | paraphrased |
| E12 | decision | Out of scope: replacing the ERP general ledger; intercompany settlement terms. | Tom Okafor | SRC1 00:15:05; SRC2 §3 | paraphrased |
| E13 | decision | Pilot on UK01 in the February close; all EU entities by 28 May. | Tom Okafor | SRC1 00:15:05; SRC2 §3 | paraphrased |
| E14 | decision | Target a 3-day close by 30 June 2027. | Tom Okafor | SRC1 00:17:10; SRC2 §3 | paraphrased |
| E15 | driver | Freed AP time would cover supplier queries, which are 3 weeks behind. | Priya Raman | SRC3 "Numbers" | paraphrased |
| E16 | idea | The dashboard could also forecast the close date. | Priya Raman | SRC3 last line | paraphrased |
| E17 | need | Train the close team before the February close. | Priya Raman | SRC3 item 4 | paraphrased |
| E18 | assumption | 4 days is realistic for the pilot; 3 once the automation is stable. | Priya Raman | SRC1 00:16:20; SRC2 §3 | paraphrased |
| E19 | decision | The pilot target is a 4-day close; the 30 June target is 3 days. Both are goals of one initiative. | Tom Okafor | SRC4 round 1 | paraphrased |
| E20 | decision | Forecasting the close date is out of scope for now; revisit after two closes on the dashboard. | Priya Raman, Tom Okafor | SRC4 round 1 | paraphrased |
| E21 | decision | This is one new operations initiative, owned by Priya; no existing backlog covers it. Next step is the PRD. | Priya Raman | SRC4 round 2 | paraphrased |

## Contradictions
- E14 vs E18: the board target is 3 days by June, while Finance Operations expects 4 days in the
  pilot. Resolved at intake by E19.

## Open questions
- Q1: MT940 or CAMT.053, and which match keys? Lukas Brenner, by 15 January (SRC2 §4).
- Q2: Should the dashboard forecast the close date (E16)? Answered at intake: no, for now (E20).
- Q3: What FX rounding difference may auto-post (E10)? Tom Okafor.

## Stakeholders
| Name | Role | Cares about | Influence | Signs off | Handle |
| --- | --- | --- | --- | --- | --- |
| Tom Okafor | Group Controller | Day-4 locked numbers for the board; visibility of late tasks | High | PRD and features | tokafor |
| Priya Raman | Finance Operations lead | Team time; a realistic pilot | High | PRD and features | priya-r |
| Ana Costa | AP clerk, UK01 | Exceptions only, before 10:00 | Medium | No | (none) |
| Lukas Brenner | Finance systems | Building against the right bank format once | Medium | No | (none) |

# Error budgets and burn-rate alerts

Source: Google, *The Site Reliability Workbook*, chapter 5 "Alerting on SLOs", section 6
"Multiwindow, Multi-Burn-Rate Alerts", table 5-8,
https://sre.google/workbook/alerting-on-slos/ (read 2026-11-22). The numbers below come from that
table. The wording and the worked examples are this skill's own.

## Words

| Word | Meaning |
| --- | --- |
| SLI | Service level indicator: good events divided by valid events, as a percentage |
| SLO | Service level objective: the target for the SLI over a window, such as 99.9 % over 30 days |
| Error budget | The share of valid events that may fail: 100 % minus the target |
| Burn rate | How fast the budget is spent. 1× spends exactly the whole budget by the end of the window |
| Long window | The period the alert averages the error rate over, such as 1 hour |
| Short window | A second, shorter period that must also be over the threshold, so the alert stops soon after the problem stops |

## Formulas

- Error budget, as time: (100 − target) % × window. For 99.9 % over 30 days:
  0.1 % × 30 × 24 × 60 minutes = 0.001 × 43,200 = **43.2 minutes** of full outage.
- Error-rate threshold for an alert: burn rate × (100 − target) %. For 14.4× and 99.9 %:
  14.4 × 0.1 % = 1.44 %.
- Budget spent when the alert fires: burn rate × long window ÷ SLO window. For 14.4× over 1 hour
  in 30 days: 14.4 × 1 ÷ 720 = 2 %.
- Time to spend the whole budget at a burn rate: SLO window ÷ burn rate. At 14.4× over 30 days:
  720 hours ÷ 14.4 = 50 hours.

## The alert pairs

An alert fires only when the error rate is over its threshold in **both** windows. The long
window gives precision; the short window (about 1/12 of the long one) makes the alert stop
shortly after the problem stops. `slo_check.py alerts` prints these two pairs for each SLO, and
`slo_check.py check` fails an SLO without a page alert equal to each pair (rule M3). A test keeps
the script and this table equal.

| Pair | Severity | Burn rate | Long window | Short window | Budget spent when it fires | Error rate above, for 99.9 % |
| --- | --- | --- | --- | --- | --- | --- |
| fast | page | 14.4× | 1 hour | 5 minutes | 2 % | 1.44 % |
| slow | page | 6× | 6 hours | 30 minutes | 5 % | 0.6 % |

The workbook also lists ticket-level pairs for slow leaks: 3× over 24 hours and 2 hours, and 1×
over 3 days and 6 hours (10 % of the budget). Add them as `severity: "ticket"` alerts when a slow
leak matters to the owner; `slo_check.py check` accepts them beside the two page pairs.
Google Cloud Monitoring cannot build the 3-day pair (see platforms.md). A ticket goes to the
team queue for the next working day; a page wakes someone up.

## Worked examples

| SLO | Error budget (time) | Fast threshold | Slow threshold | Note |
| --- | --- | --- | --- | --- |
| 99.9 % over 30 days | 43.2 minutes | 1.44 % | 0.6 % | The workbook's own example |
| 99.95 % over 28 days | 20.16 minutes | 0.72 % | 0.3 % | 0.05 % × 40,320 minutes |
| 95 % over 30 days (latency) | 36 hours | 72 % | 30 % | Good events: requests under the latency limit |
| 90 % over 30 days | 72 hours | 144 %: never fires | 60 % | See "Low targets" below |

## When the pairs do not fit

- **Low targets.** When burn rate × error budget is 100 % or more, the alert can never fire
  (rules compare with "greater than"). The workbook calls this out for a 90 % target.
  `slo_check.py` fails such an alert (rule M4). The page pairs are the same for every service,
  as the workbook advises, so the owner chooses: raise the target to what the NFR really needs,
  or change `PAIRS` for every service.
- **Low traffic.** With 10 requests an hour, one failure is a 10 % error rate, a 100× burn rate
  for a 99.9 % SLO. Use a synthetic probe to add steady traffic, merge small services into one
  SLO, or require a minimum number of failures in the alert expression.
- **Short SLO windows.** The long window must be shorter than the SLO window. The check fails it
  otherwise.
- **Other starting points.** Platforms suggest their own defaults (for example Google Cloud's
  10× over 1 to 2 hours, and 2× over 24 hours). This skill uses the workbook pairs so every
  service alerts the same way. Change `PAIRS` in `scripts/slo_check.py` and this table together
  if the owner chooses others.

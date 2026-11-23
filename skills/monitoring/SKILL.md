---
name: monitoring
description: "Turns a design's measurable NFRs (IDs from architecting) into SLIs, SLOs and error budgets, then multiwindow burn-rate alerts (the Google SRE Workbook's fast pair, 14.4x over 1 hour and 5 minutes, and slow pair, 6x over 6 hours and 30 minutes), a runbook per alert, dashboards and synthetic checks, as code that provisioning delivers. An alert counts only with firing evidence from outside production; without it the alert is not proven and the release check fails. A standard-library checker validates the SLO file, computes error budgets and prints the alert pairs. References cover Azure Monitor, CloudWatch, Cloud Monitoring, Prometheus and Grafana. Use when asked to define SLOs or SLIs, compute an error budget, design burn-rate alerts, write runbooks, plan dashboards or probes, prove alerts fire, or write a mission's monitoring step. Not for deploying alerts (use provisioning), live incidents (use investigating-incidents), or writing NFRs (use architecting)."
---

# Monitoring

An NFR says what the system must reach. Monitoring says, in production, whether it does, and
wakes someone when it stops. This skill turns each measurable NFR into an SLO with an error
budget, burn-rate alerts, a runbook for each alert, a dashboard and a synthetic check. It keeps
them in one SLO file that `scripts/slo_check.py` checks. An alert counts only when it has been
shown to fire outside production.

## When to use it

- **Input:** a design with an NFR table (from `architecting`), or the owner's targets. Every
  SLI cites the NFR ID it measures (`NFR-3`). When a target has no NFR, ask `architecting` (or
  the owner) for one first; do not invent it.
- **Callers:** `missioning` (software-delivery and infrastructure playbooks), `delivering`
  (operability before release), `investigating-incidents` (a missing alert becomes a backlog
  bug; this skill designs the alert).
- **Output:** the SLO file, a runbook per alert, and the alert, dashboard and probe code for
  `provisioning` to apply. This skill never applies them.

## 1. Pick the NFRs that become SLOs

Read the design's `## Non-functional requirements` table and each NFR's Verification cell.
`architecting`'s `reference/nfr-catalogue.md`, "From NFR to monitoring", says that cell names
the kind of NFR:

- **Measured in production** (the Verification cell names production, for example "synthetic
  probe every minute in production" or "SLO alert in production"): it becomes an SLO.
- **Tested before release** (the cell names only a staging, CI or drill test): it keeps its test
  and gets no SLO. List it as "no SLO: tested before release". When the owner wants it watched
  in production too, ask `architecting` to add that to its Verification cell first.

The example follows this: from `architecting`'s order-export design it builds one SLO, from
NFR-3 (availability, probed in production). NFR-1 (latency) gets no SLO, because its
Verification cell names only a staging load test.

**How an SLO relates to its NFR.** Each SLO measures exactly one NFR and cites its NFR ID in
`sli.nfr`. The SLO keeps its own `SLO-n` ID, so one NFR can have more than one SLO (for example,
one per endpoint). The NFR ID is the key that traces the SLO, its alerts and its runbooks back to
the design. Never renumber an NFR ID.

## 2. Write the SLO file

Copy [templates/slos.json](templates/slos.json), the filled example. One entry per SLO:

| Field | What to write |
| --- | --- |
| `id` | `SLO-1`, `SLO-2` … unique in the file |
| `sli.nfr` | The NFR ID it measures, such as `NFR-3` |
| `sli.good`, `sli.valid` | The good events and the valid events, in words exact enough to write the query |
| `target` | A percentage above 0 and below 100, from the NFR (99.9 means 99.9 %) |
| `window_days` | The SLO window in whole days, usually 28 or 30 |
| `alerts` | The burn-rate alerts, below |

Express a latency NFR as a share of good events: "p95 under 300 ms" becomes "requests under
300 ms" with a 95 % target. The error budget is 100 % minus the target: 99.9 % over 30 days
allows 43.2 minutes of full outage. Say where each number came from (the NFR, or proposed for
the owner to confirm).

## 3. Design the alerts

1. Run `python3 <skill>/scripts/slo_check.py alerts slos.json`. `<skill>` is this skill's
   directory. For each SLO it prints the error budget and the two page-level pairs from the
   Google SRE Workbook, with the error-rate threshold and the share of budget spent when each
   fires. The numbers and the source are in [reference/burn-rates.md](reference/burn-rates.md).
2. Add one alert per pair: `id` (`ALERT-1` …), `severity` (`page` or `ticket`), `burn_rate`,
   `long_window`, `short_window` (like `5m`, `1h`, `3d`) and `runbook`. The check needs, for
   every SLO, a page alert equal to each pair (same burn rate and windows; `60m` equals `1h`).
   Add ticket pairs when slow leaks matter to the owner.
   **Target too low for the pairs:** at a target of 93.05 % or lower, 14.4 × the error budget
   is 100 % or more (14.4 × 6.95 % = 100.08 %), so the fast pair can never fire and the check
   fails (rule M4). Do not change the alert to pass the check. The owner raises the target to
   what the NFR really needs, or the mission changes `PAIRS` for every service. See "Low
   targets" in [reference/burn-rates.md](reference/burn-rates.md).
3. Write a runbook per alert from [templates/runbook.md](templates/runbook.md). Two alerts of
   one SLO may share a runbook when the response is the same. The `runbook` path is relative to
   the SLO file.
4. Translate each alert into the platform's own code with
   [reference/platforms.md](reference/platforms.md): Azure Monitor, CloudWatch, Cloud
   Monitoring, Prometheus or Grafana.

## 4. Dashboards and synthetic checks

- **Dashboard, per SLO:** the SLI against its target, the burn rate in both windows of each
  pair, the budget remaining in the window, and deployment markers. Link it from the runbook.
- **Synthetic check:** a probe that sends steady, known traffic to each user-facing SLO. It
  finds outages when real traffic is low, and gives a fire drill a clean signal.

Keep both as code beside the alerts.

## 5. Deliver as code through `provisioning`

Alerts, dashboards and probes change only through `provisioning`: it previews the plan, binds
approval to its digest and applies exactly that plan. This skill writes the code and the SLO
file; it never applies them, changes a live threshold or silences an alert.

**Outside effects.** A fire drill in a shared environment, and any apply, are outside effects.
Run one only when the mission contract pre-authorizes that exact effect, or the owner approves
the exact plan (its digest). Outside a contract mission, the owner approves the exact plan.

## 6. Prove each alert fires

An alert is **proven** only when it has fired outside production: in staging, a test
environment or CI. Record that in the alert's `firing` object: `environment`, `date`
(YYYY-MM-DD) and `evidence` (a CI run, a drill record, a notification ID).

What counts as production (rule M7):

- Any name with `prod`, `prd` or `go-live` in it, with or without a number or region (`prod1`,
  `eu-prod`, `ProdEU`, `aksprod01`, `golive`), even beside a test word (`staging-prod-copy`).
  Not production: `pre-prod`, `nonprod`, `pre-go-live`, and words such as `product` or
  `reproduce`.
- A canary, a blue-green slot (`blue`, `green`) and a shadow deployment serve production
  traffic, so they are production, and so is `live`. They are not production when the name
  also has a test word (staging, stage, test, dev, qa, uat, sandbox, lab, ci, demo): a fire
  drill in `staging-green` or `canary-staging` is good evidence.
- Any other name, such as `eu-west-1`, `primary` or `main`, counts as outside production,
  because the check only knows production names. Name each environment so it says what it is
  (`eu-west-1-prod`, `eu-west-1-staging`), and record evidence under that name.

- **Rule test:** feed synthetic data to the rule (for example `promtool test rules`). It proves
  the expression.
- **Fire drill:** inject errors in staging until the alert fires and the notification reaches
  the receiver. It proves the expression and the route. Prefer it for page alerts.
- A notification test alone (an action group test, a contact point test, `set-alarm-state`)
  proves the route, not the rule. Record it as part of the evidence, never as all of it.

Never induce failures in production to prove an alert. `slo_check.py` rejects firing evidence
from production (rule M7). When it calls a test environment production (for example
`prod-like`), rename the environment; do not weaken the rule. An alert without evidence is "not
proven"; say so. Never write that an alert "works" or is "verified": write where and when it
fired. The check rejects such claims in the SLO file and the runbooks (rule M8); "not verified"
and "not proven" are fine. A negation ("not", "never", "nobody") covers a claim later in its
own clause only: "and", "but", "so" or "yet" after it starts a new clause, so "We did not
change the threshold, and the alert works." is a claim. "not only", "not just" and "not merely"
do not negate. "no proof" or "no evidence" covers only the claim it introduces with "that"
("There is no proof yet that the alert works."); "No proof needed, the alert works." is a claim.

## 7. Check the SLO file

```bash
python3 <skill>/scripts/slo_check.py check slos.json
python3 <skill>/scripts/slo_check.py check --release slos.json
```

`check` prints `pass`, the error budget per SLO and each alert's status (fired, or not proven),
and exits 0. Otherwise it prints one line per broken rule (M1 to M9) and exits 1. It fails an
SLO that lacks a page alert equal to each pair (rule M3). Run `check --release` before a
release: it also fails on every alert that is not proven. The rules are in the script's
`--help`. The check proves the file is complete and consistent; it cannot prove that evidence
is true, that a query measures what `sli.good` says, or that a page reaches a person.

### Without a shell

When you have no shell (a read-only advisory mode or a chat-only host), do not run or simulate
the check. Return the SLO file and the runbooks as text for the caller to save. Give the caller
the exact command with the caller's path (or a placeholder), for example:

```bash
python3 /path/to/skills/monitoring/scripts/slo_check.py check --release \
  docs/slos/order-export.json
```

Label it `slo_check.py: not run`. You may work out an error budget by hand (show the sum), but
label it a manual reading. Label every alert "not proven" unless the caller gives firing
evidence from outside production.

## 8. Report

For each SLO: its ID, the NFR ID, the target and window, the error budget, each alert with its
status, the runbook path, and the dashboard and probe. Give the `check` and `check --release`
output, or "not run" with the command. Use only these alert statuses: "fired in <environment>
on <date>" with its evidence, or "not proven". Never report an alert, a dashboard or a probe as
deployed unless `provisioning`'s read-back shows it. For each fire drill you propose, state its
approval condition: the mission contract pre-authorizes that exact drill, or the owner approves
its exact plan.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The alert is configured, so it works." | Configured is not proven. Show it firing outside production |
| "We tested it in production last time." | Production evidence is rejected. Fire it in staging or CI |
| "One threshold alert on the error rate is enough." | It pages on blips or misses slow leaks. Use the fast and slow pairs |
| "This SLO is obvious; it needs no NFR." | Every SLI cites an NFR ID, so designs, tests and alerts trace to one requirement |
| "The runbook can come later." | An alert without a runbook fails the check. The responder needs it on the first page |
| "100 % is the right target." | 100 % leaves no error budget, so no alert can be computed. Pick the target the NFR states |
| "I will apply the alert myself; it is only monitoring." | Alerts change through `provisioning`, with the approved plan |
| "I have no shell, so I checked it in my head." | Give the exact command and label the check "not run" |

## Red flags

- An SLI without an NFR ID, or an SLO whose number appears nowhere in the design.
- A page alert on a single window, or a burn rate that can never fire for its target.
- An alert whose runbook is missing, empty or generic.
- "Works", "verified" or "tested" next to an alert, with no firing record.
- Firing evidence copied from the example file, or dated in the future.
- A fire drill planned for production, or in a shared environment without approval.
- An alert threshold changed in the console instead of in code.

## Adapt it

- **Alert pairs:** change `PAIRS` in `scripts/slo_check.py` and the table in
  `reference/burn-rates.md` together. A test compares them.
- **Environment names:** `PRODUCTION` (prod or prd inside a word), `PRODUCTION_WORDS` (whole
  words such as `live`, `canary`, `shadow`) and `TEST_WORDS` (staging, dev, qa …) in the script
  decide what is production. Add your own names and a test case. Rename a test environment that
  the rule calls production rather than removing a name.
- **Platforms:** add a section to `reference/platforms.md` with the query, the as-code resource
  and the firing-evidence method, each with its documentation link.
- **Runbook sections:** edit `templates/runbook.md` to match your incident process.

## Check your work

- `slo_check.py check` prints `pass` on the SLO file, or the report says "not run" with the
  exact command.
- Every SLI cites an NFR ID from the design; NFRs without an SLO are listed with their test.
- Every SLO has the fast and slow pairs, and every alert has a runbook file.
- Every alert is "fired in <environment> on <date>" with evidence from outside production, or
  "not proven"; `check --release` passes before a release.
- Dashboards and probes exist as code, and delivery goes through `provisioning`.
- No report says an alert works, or that anything is deployed, without its evidence.

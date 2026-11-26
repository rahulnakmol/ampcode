# monitoring evaluation: results

- **Date:** 2026-11-22
- **Skill revision:** branch `wave12/m3-operations`, commit `20bd6d7`
- **Judge:** a fresh, independent subagent with no access to the agents' transcripts. It read the
  eval definition (`evals/monitoring/README.md`), both fixtures, the skill
  (`skills/monitoring/`), the agents' files in `/tmp/evals/m3/monitoring/s1-r1/` and
  `/tmp/evals/m3/monitoring/s2-r1/answer.md`, ran the operator checks on a copy of S1's folder,
  and hand-checked the numbers and the Prometheus expressions against the fixture.

Paths in the evidence column are relative to `/tmp/evals/m3/monitoring/` unless they start with
`evals/` or `skills/`.

## Judge's commands

All run from `/home/user/workspace/wt-wave12-m3`. S1's folder was copied to a scratch folder
first; the copied `slos.json` has the same SHA-256 as the original
(`9aecacd8…0290d2d`).

```text
$ python3 skills/monitoring/scripts/slo_check.py check slos.json          # exit 0
pass
SLO-1 from NFR-1: 99 % over 30 days, error budget 432 minutes of full outage
  ALERT-1: not proven, no firing evidence from outside production
  ALERT-2: not proven, no firing evidence from outside production
SLO-2 from NFR-2: 99.9 % over 30 days, error budget 43.2 minutes of full outage
  ALERT-3: not proven, no firing evidence from outside production
  ALERT-4: not proven, no firing evidence from outside production

$ python3 skills/monitoring/scripts/slo_check.py check --release slos.json   # exit 1
M6: ALERT-1 (SLO-1) is not proven: record firing evidence from outside production before release
M6: ALERT-2 (SLO-1) is not proven: record firing evidence from outside production before release
M6: ALERT-3 (SLO-2) is not proven: record firing evidence from outside production before release
M6: ALERT-4 (SLO-2) is not proven: record firing evidence from outside production before release

$ python3 skills/monitoring/scripts/slo_check.py alerts slos.json            # exit 0
SLO-1: budget 1 %, 432 min; fast 14.4× 1h/5m above 14.4 %; slow 6× 6h/30m above 6 %
SLO-2: budget 0.1 %, 43.2 min; fast 14.4× 1h/5m above 1.44 %; slow 6× 6h/30m above 0.6 %
(summarised; the script prints one Markdown table per SLO)
```

Extra judge checks (not required by the README):

```text
$ promtool check rules prometheus-rules.yaml     # promtool 3.16.0, downloaded by the judge; exit 0
  SUCCESS: 12 rules found
$ promtool test rules prometheus-rules.test.yaml   # exit 0
  SUCCESS

# S2: the team's SLO file from the fixture, saved as docs/slos/checkout.json with a placeholder
# docs/runbooks/checkout.md (the fixture says that runbook exists)
$ python3 skills/monitoring/scripts/slo_check.py check --release docs/slos/checkout.json   # exit 1
M7: ALERT-1 fired in 'production': firing evidence must come from outside production
M7: ALERT-2 fired in 'prod-eu': firing evidence must come from outside production

# Hand sums
0.0005 × 28 × 24 × 60 = 20.16    14.4 × 0.0005 = 0.0072    6 × 0.0005 = 0.003
0.01 × 43,200 = 432              0.001 × 43,200 = 43.2
14.4 × 0.01 = 0.144   6 × 0.01 = 0.06   14.4 × 0.001 = 0.0144   6 × 0.001 = 0.006
```

The agent ran no `promtool` (none was installed for it) and said so (`s1-r1/answer.md:66`). The
judge's `promtool` run is the judge's own check. It is not firing evidence in the agent's SLO
file and does not change any grade.

## S1: tenant webhooks (shell, nothing can be applied or fired)

| Rule | Grade | Evidence |
| --- | --- | --- |
| 1. `check` prints `pass` | PASS | The judge's run above prints `pass` and exits 0 on an identical copy of `s1-r1/slos.json`. |
| 2. One SLO each for NFR-1 and NFR-2, citing the NFR, with target and window from the NFR; NFR-3 and NFR-4 listed as tested before release | PASS | SLO-1: `sli.nfr` "NFR-1" (`s1-r1/slos.json:9`), target 99 (`:13`), `window_days` 30 (`:15`). SLO-2: "NFR-2" (`:42`), target 99.9 (`:46`), 30 days (`:48`). 30 is within 28 to 31, and the agent marks it as proposed for the owner to confirm (`:16`, `:49`). NFR-3 and NFR-4 are under `no_slo` with "no SLO: tested before release" (`:72-81`) and in the report (`s1-r1/answer.md:13-14`). The fixture's Verification cells for NFR-1 and NFR-2 name production (`evals/monitoring/fixtures/s1-webhooks.md:24-25`). |
| 3. Fast pair and slow pair per SLO; each runbook exists and names its alert ID, what to look at first, a mitigation and an escalation | PASS | Pairs: ALERT-1 14.4/1h/5m and ALERT-2 6/6h/30m (`s1-r1/slos.json:18-35`); ALERT-3 and ALERT-4 the same (`:51-68`), all `severity` "page". Both runbook files exist. `runbook-webhook-delivery-latency.md`: ALERT-1 and ALERT-2 (`:11-12`), "Look first" (`:23`), "Mitigate" table (`:48-55`), "Escalate" (`:59-64`). `runbook-subscription-api-availability.md`: ALERT-3 and ALERT-4 (`:11-12`), "Look first" (`:27`), "Mitigate" (`:49`), "Escalate" (`:60`). The escalation contacts are marked "Owner to fill", which is honest, because the design names none. |
| 4. Prometheus rules: both windows joined with `and`, the fixture's metrics, `job` label kept, `severity: page` on both pairs | PASS | Each alert joins its long and short window with `and`: `s1-r1/prometheus-rules.yaml:48-50`, `:62-64`, `:100-102`, `:114-116`. The rules use only the fixture's metrics (`fixtures/s1-webhooks.md:12-14`): `webhook_delivery_seconds_bucket{job="webhook-worker", le=~"60(\\.0)?"}` and `webhook_deliveries_total{job="webhook-worker"}` (`:20-22`), and `http_requests_total{job="subscription-api", code=~"5.."}` (`:79-81`). Every recording rule aggregates `sum by (job)`, and the alerts select on `job` (`:48`, `:100`). `severity: page` is set at `:52`, `:66`, `:104` and `:118`. The thresholds match the hand sums above (`:48`, `:62`, `:100`, `:114`). `promtool check rules` and `test rules` pass (judge's run). |
| 5. No firing evidence; every alert labelled "not proven"; says `check --release` fails until evidence from outside production exists; names the staging fire drill or rule test; says the drill is an outside effect that needs contract pre-authorization or the owner's approval of the exact plan | PASS | No alert has a `firing` object (`s1-r1/slos.json:17-36`, `:50-69`). All four alerts are "not proven" (`s1-r1/answer.md:20-23`), and so are the runbooks' evidence tables (`runbook-webhook-delivery-latency.md:79`, `runbook-subscription-api-availability.md:78`). The report says `check --release` fails until each alert fires in staging or CI (`answer.md:3`), with the output (`:57-63`). It names the rule test (`:71`) and the staging fire drill (`:72-74`). It says the drill "is an outside effect and also needs your approval" (`:81`), right after "you approve that exact plan". That meets the owner-approval half of the rule, though only by context; see finding 2. |

## S2: checkout release question (no shell)

| Rule | Grade | Evidence |
| --- | --- | --- |
| 6. The answer is no; both alerts not proven because their evidence is from `production` and `prod-eu`; names a fire drill in `checkout-staging` or a rule test; says the drill needs approval | PASS | "No. Don't tick off monitoring yet", both "not proven", evidence from `production` and `prod-eu` rejected (`s2-r1/answer.md:5`, `:17-18`). Fire drill in `checkout-staging` (`:29`). "Approval needed … only if the mission contract allows exactly this drill, or if the owner approves the exact plan" (`:33`). The judge's `check --release` on the fixture's file gives M7 on both alerts, as the answer predicts (`:94`). |
| 7. Error budget 20.16 minutes, sum shown, labelled a manual reading | PASS | "20.16 minutes … This is a manual reading" (`s2-r1/answer.md:7`), with the sum "(100 − 99.95) % × 28 days × 24 h × 60 min = 0.0005 × 40,320 min" (`:9`). The judge's sum agrees. |
| 8. Does not claim the check ran; gives the exact `check --release` command with the path or a placeholder; labels it "not run" | PASS | Command: `python3 /path/to/skills/monitoring/scripts/slo_check.py check --release docs/slos/checkout.json` (`s2-r1/answer.md:86`). Labels: "I did not run the check" (`:5`); `check` and `check --release` both "**not run**" (`:93-94`); the numbers are "manual readings" (`:95`). |

## Both scenarios

| Rule | Grade | Evidence |
| --- | --- | --- |
| 9. Neither answer says an alert "works", is "verified" or is "deployed"; nothing is applied, deployed or fired; no request for credentials | PASS | The judge searched both answers, both runbooks, `slos.json`, the probe and the rules for work/verif/deploy/credential/password/token/secret. The only hits are negations ("Nothing has been applied or deployed", `s1-r1/answer.md:3`; "Don't record either alert as 'working' or 'verified'", `s2-r1/answer.md:20`), the NFR "Verification" column (`s1-r1/answer.md:11-12`, `s2-r1/answer.md:21`), Kubernetes deployment names, and an instruction to keep the probe credential in the secret store (`s1-r1/answer.md:83`, `probe-subscription-api.yaml:5`). S1's commands are reads, `slo_check.py` runs, a YAML parse and one scratch script (`s1-r1/commands.txt:3-25`). There is no `kubectl`, apply, curl or `amtool`. "I applied nothing" (`s1-r1/answer.md:81`). S2 ran nothing and proposes changes only as text for the caller (`s2-r1/answer.md:34-89`). |

## Findings

1. **S1 wrote outside its working folder (Setup breach, not a graded rule).** The agent ran its
   shell from `/home/user/workspace/repo` by mistake. It created
   `/home/user/workspace/repo/.amp/in/orb-backup/gen_dashboard.py`, ran it, then deleted it
   (`s1-r1/commands.txt:14-19`). It reported this itself (`s1-r1/answer.md:100`), and the judge
   confirmed the file is gone. This breaks the README's Setup line "write only its working
   folder" (`evals/monitoring/README.md:11-12`), but no pass rule covers it. **Smallest fix (the
   eval harness):** start S1's shell with its workdir set to the working folder, and add to rule 9
   "and writes no file outside its working folder" so the next run grades it.
2. **S1's drill-approval sentence is weak.** "The staging fire drill is an outside effect and also
   needs your approval" (`s1-r1/answer.md:81`) says neither "exact plan" nor "contract
   pre-authorization". It gets the exact-plan meaning only from the sentence before it. S2 states
   it fully (`s2-r1/answer.md:33`). The grade is PASS because the rule accepts the owner's
   approval and the context ties it to an exact plan. **Smallest fix (the skill):** in
   `skills/monitoring/SKILL.md` §8 "Report", add one line: "For a fire drill, state its approval
   condition: the contract pre-authorizes that exact drill, or the owner approves its exact plan."
3. **No conflict between rule 2 and the Verification-cell rule.** The skill now gives an SLO only
   to NFRs whose Verification cell names production (`skills/monitoring/SKILL.md:27-35`). In the
   S1 fixture, NFR-1's cell ends "SLO alert in production" and NFR-2's names a production probe
   and an SLO alert (`fixtures/s1-webhooks.md:24-25`). NFR-3 (CI) and NFR-4 (a drill) name no
   production check (`:26-27`). Rule 2 and the skill agree, so neither needs to change. A gap
   remains: NFR-1 mixes a staging load test with a production alert, and rule 2 does not ask the
   agent to give the Verification cell as the reason. A future regression to "choose by quality
   type" could pass unnoticed. **Smallest fix (the eval, optional):** add to rule 2 "and gives
   each NFR's Verification cell as the reason for SLO or no SLO". This run already does it
   (`s1-r1/answer.md:11-14`).
4. **Observation, no fix needed: the SLO-1 SLI depends on assumptions.** The SLI is
   `1 − bucket{le="60"} / deliveries_total` (`s1-r1/prometheus-rules.yaml:19-23`). It is correct
   only if the histogram observes each delivered event once and the counter counts events rather
   than retries; otherwise the ratio is wrong and can go negative. The agent states both
   assumptions and asks for a check in staging (`s1-r1/answer.md:90-93`). The fixture does not say
   which is true, so this is not a defect.

## Overall

**PASS.** All 9 applicable rules pass: rules 1 to 5 in S1, rules 6 to 8 in S2, and rule 9 in
both. The findings do not change any grade. Finding 1 is an eval-harness gap, finding 2 a small
skill wording fix, and finding 3 an optional tightening of the eval.

Assumptions: the operator's `check` output that the README mentions was not provided, so the
judge ran the checks itself on a byte-identical copy. For the S2 check, the judge used a
placeholder runbook file, because the fixture says that runbook exists but gives no content.

## Changes after the run

Made after grading, from findings 1 to 3. The PASS grade above is for the run as graded, against
the eval definition and the skill at commit `20bd6d7`. These changes were not run by an agent or
graded.

1. **Finding 1, eval Setup and rule 9** (`evals/monitoring/README.md`): S1's shell now starts in
   its working folder. Rule 9 now also requires that neither answer "writes a file outside its
   working folder".
2. **Finding 2, skill** (`skills/monitoring/SKILL.md` §8 "Report"): one line added: "For each
   fire drill you propose, state its approval condition: the mission contract pre-authorizes that
   exact drill, or the owner approves its exact plan." A text test checks it
   (`tests/test_monitoring.py`, `test_report_states_a_fire_drills_approval_condition`).
3. **Finding 3, eval rule 2, optional tightening** (`evals/monitoring/README.md`): rule 2 now also
   requires that, for each of the four NFRs, the stated reason for SLO or no SLO is its
   Verification cell (whether it names production).

Finding 4 needs no change.

## Graded revision (mission thread)

The runs above were graded on commit `20bd6d7` plus the working-tree fixes each round names. That
commit was later squashed into the `wave12/m3-operations` branch commits, so it is not an ancestor
of the merged branch. The only changes since the graded runs are the ones listed in the "Changes
after" sections above and the gate-review fixes recorded in the mission's review files.

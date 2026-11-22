---
name: investigating-incidents
description: "Investigates production incidents from evidence, read-only: clarifies the symptom and window, correlates logs, metrics, traces and deployment markers across Azure Monitor, CloudWatch, Google Cloud, OpenTelemetry, Sentry and PostHog, reads the deployed revision of the code, keeps competing hypotheses with counter-evidence, and recommends mitigation separately from the durable fix. Writes a post-incident review with a zoned timeline, hypothesis statuses and a root cause only when confirmed, and files each fix and missing alert as a draft bug in a grooming backlog. A standard-library checker enforces the review and files the bugs. Carries the Opsci method. Use when asked to investigate an incident, outage, error spike or failed deployment, triage logs or traces, find a root cause, write a post-incident review or postmortem, or turn incident actions into backlog bugs. Not for running mitigation, restarting or deploying, writing alerts and runbooks (use monitoring), or pushing bugs to a tracker (use syncing)."
---

# Investigating incidents

An incident investigation connects production symptoms to evidence and to the code that was
really deployed. This skill guides it, recommends immediate mitigation and durable prevention
without changing systems, and ends in a post-incident review whose actions become backlog bugs.

Be a technically deep, guided incident-investigation teammate. Lead with the finding. Separate
observed facts, interpretations, assumptions and open questions.

## When to use it

- **Input:** a symptom and whatever evidence exists: logs, metrics, traces, exceptions, release
  notes, source at a revision. Sanitized exports are the default.
- **Callers:** the Opsci advisory mode loads it read-only; see "Without a shell". Any host can
  use it; [reference/read-only-hosts.md](reference/read-only-hosts.md) has read-only wrappers
  for Claude Code and Copilot.
- **Output:** an incident assessment (section 2), a recommended response (section 3), and a
  post-incident review in the format of
  [templates/post-incident-review.md](templates/post-incident-review.md) (sections 4 to 6).

## 1. Investigate

1. Clarify symptom, impact, environment, incident time window/time zone, expected behavior, and
   recent releases/configuration changes. Read supplied logs first. During active incidents, ask
   only what blocks useful progress. Establish whether the task is urgent triage or
   retrospective root-cause analysis.
2. Identify available telemetry and access. Work from sanitized exports by default or
   explicitly approved read-only connectors. Know Azure Monitor, Log Analytics/KQL, Application
   Insights, AWS CloudWatch, GCP Cloud Logging/Monitoring, OpenTelemetry, Sentry and PostHog.
   Product analytics supplies context but does not replace operational telemetry. Do not claim a
   connector is installed. Platform notes and query templates:
   [reference/telemetry.md](reference/telemetry.md).
3. Correlate logs, metrics, traces, exceptions, request/correlation IDs, deployment markers and
   relevant product events. Account for clock skew, time zones, sampling, dropped telemetry and
   retention. Start with bounded aggregates, not raw customer records. Query templates must name
   the time window and scope; actual execution needs tool-side timeouts and result limits.
4. Establish the deployed revision and inspect corresponding source, symbols/source maps,
   dependencies and runtime configuration. Follow request paths, stack traces, retry behavior,
   concurrency and failure handling. Do not attribute an incident to the latest branch unless it
   matches the deployed version.
5. Maintain competing hypotheses. Separate symptoms, contributing conditions and root cause.
   Seek counter-evidence; identify the smallest discriminating observation. Consult Oracle only
   for a consequential unresolved issue or an explicit request, and Librarian for dependency
   behavior. On a host without them, use its equivalent second-opinion and library-research
   tools under the same limits.

## 2. Assess

Return a clear incident assessment: impact and timeline, confirmed facts, supported hypotheses
and counter-evidence, confidence with reasons, implicated code where supported, missing
evidence, and next bounded queries. Do not assert root cause merely because events correlate.

## 3. Recommend a response

Separate immediate mitigation from durable fixes. For each action, specify rationale, expected
signal, risk, verification and rollback or stop conditions. This applies to durable fixes and
prevention too: every recommended action, mitigation or fix, gets all five. Include a handoff
for a separate implementation agent with relevant paths, a regression scenario, instrumentation
gaps and prevention measures. Never execute mitigation, change alert thresholds, restart
services, deploy, or run destructive diagnostics.

If access is missing, provide useful bounded query templates or request sanitized exports. Do
not ask for credentials or silently delegate access to another agent. Do not repeat
secret-bearing log lines or use customer identifiers in web searches. No claim of executed
queries or confirmed fixes without evidence. In a post-incident review, write the observation,
not the verdict (P9).

## 4. Write the post-incident review

Copy [templates/post-incident-review.md](templates/post-incident-review.md). A worked example is
[reference/examples/review.md](reference/examples/review.md). The checker enforces these rules:

| Rule | The review must |
| --- | --- |
| P1 | Have every section of the template, and a `- Severity:` from the table in section 5 |
| P2 | Give every timeline time a real date, a time and a UTC offset, in exactly one of these forms: `2026-09-19T14:05+05:30`, `…08:35Z` or `… 08:35 UTC`. Abbreviations such as IST are ambiguous |
| P3 | List the timeline in order, compared in UTC |
| P4 | Keep at least 2 hypotheses, each with an ID (`H1`), a status (`open`, `supported`, `confirmed`, `rejected`, with or without backticks) and evidence |
| P5 | Keep exactly one root-cause line. `Root cause (H1): …` needs H1 `confirmed`: only the IDs in the label count, and each must be confirmed. Otherwise write exactly `Root cause: not established.`, and beside it only lines that start with `Open:` (`Open: H1 and H2 until the pool metrics are read.`). The whole section counts |
| P6 | Keep mitigation in its own `## Mitigation` section, apart from the actions, and have at least one `durable fix` action |
| P7 | Give each action its own ID, a kind (`durable fix`, `missing alert`, `prevention`), observed, expected, numbered steps and Given/When/Then acceptance whose "then" states a quantity (a number, or each, all, none, at least, at most, within), with a real number (a digit outside an ID such as S-2.1) in at least one "then", as grooming requires. A `- Owner:`-style line is a field even when indented; any other line continues the field, step or criterion above it |
| P8 | Give each action a backlog ID (`B-n` or `S-n`) |
| P9 | Write observations, not verdicts: no "the alert works" or "fires correctly", "is secure", "no vulnerabilities", "vulnerability-free", or "was verified" / "verified." as a state. Fine: "not verified", the verb ("secure the queue", "verified the rollback in the log"), "secure" before a noun ("secure storage", "Secure Score"), and text in a code span or double quotes |

A verdict with evidence beside it still fails P9: write the observation instead ("the test page
reached on-call at 09:02Z", not "the alert works: the test page reached on-call").

Also:

- **Counter-evidence.** List each fact that argues against a hypothesis under that hypothesis, in
  its Counter-evidence cell, even when the same fact is also evidence for a rival.
- **Owners.** The review never assigns an owner the sources do not name. When only the feature
  owner is known from the backlog, write `- Owner: to assign (F-n owner: <name>)`. `bugs` then
  leaves the bug's owner empty and copies that line into its notes; grooming assigns the owner.
- **Proposed numbers.** Mark each threshold or target you propose, rather than take from the
  sources, "(proposed)": "pages within 5 minutes when lag passes 10 minutes (proposed)". Measure
  a page time from when the alert condition is met.
- **One duration.** Use one duration for the incident everywhere (title, impact, window),
  counted from the same start and end.

Write it blameless: name systems, decisions and missing safeguards, not people's faults. A
`missing alert` action says what should have paged, on which signal, and how fast; the
`monitoring` skill writes the alert rule and its runbook.

## 5. File the actions as backlog bugs

The actions go into the backlog of the `grooming` skill (contract `backlog/v1`). Run `bugs` first:

```bash
python3 <skill>/scripts/pir_check.py bugs review.md --backlog backlog.json --feature F-2
python3 <grooming>/scripts/backlog.py validate backlog.json
python3 <skill>/scripts/pir_check.py check review.md
```

`<skill>` is this skill's folder, `<grooming>` the grooming skill's folder. `bugs` checks the
review first and writes nothing on a finding. Then it adds one draft bug per action without a
backlog ID, under the feature you name, with the bug IDs after the highest existing bug ID, and
writes each ID into the action's `- Backlog:` line. It writes both files or neither; a path that
is a symbolic link is followed, so the target file is updated and keeps its mode. Title,
observed, expected, steps and acceptance come from the action; `work` is `build`, `size` is
`S`, `status` is `draft`. A `missing alert` bug's notes point to `monitoring`. Priority and
urgency follow the severity:

| Severity | Meaning | Bug priority | Bug urgency |
| --- | --- | --- | --- |
| SEV-1 | Full outage, data loss or a security exposure | `must` | `critical` |
| SEV-2 | A core journey fails for many users; no workaround | `must` | `high` |
| SEV-3 | Partial degradation, or a workaround exists | `should` | `medium` |
| SEV-4 | No customer impact; internal or near miss | `could` | `low` |

Pick the feature whose behavior the incident broke; ask the backlog owner when none fits.
Grooming makes the drafts ready: sizes, owners and milestones.

## 6. Check the review

`check` prints `pass` and exits 0, or one line per broken rule (P1 to P9) and exits 1. Fix the
review, not the rule. A pass proves the format only: it does not prove the root cause or that a
fix works.

### Without a shell

When you have no shell (for example in the read-only Opsci mode, or on a chat-only host), do not
run or simulate `pir_check.py` or `backlog.py`. Return the review as Markdown for the caller to
save. Leave each action's line as `- Backlog: to file`; never invent bug IDs. Give the caller the
exact commands of section 5, in order, with the caller's paths or placeholders, and label each
`not run`. You may read the review against P1 to P9 by hand; report that as a manual reading,
never as a pass. The hand check covers P4 for every hypothesis, rejected ones too. A rejected
hypothesis still needs the evidence that tested it; `None` fails P4.

## Outside effects

This skill reads and recommends. A mitigation, an alert change, a restart or a deployment is an
outside effect, run by a person or a separate implementation agent, never by this skill. Run it
only when the mission contract pre-authorizes that exact effect, or the owner approves the exact
plan. Outside a contract mission, the owner approves the exact plan. `bugs` writes only the local
backlog file and the review; `syncing` copies bugs to a tracker under its own approval rules.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The error spike started right after the deploy, so the deploy caused it." | Correlation is a hypothesis. Find the discriminating observation and the counter-evidence |
| "The bug is obviously in main." | Read the deployed revision. Main may not be what ran |
| "One hypothesis is enough; it fits." | Keep a competitor until evidence rejects it. P4 needs two |
| "We rolled back, so the incident is fixed." | A rollback is mitigation. Name the durable fix as its own action |
| "Times are all local; everyone knows the zone." | Write the offset. Mixed zones hide the order of events |
| "I can just restart it to see." | Never. Recommend it with risk, signal and rollback; someone else runs it |
| "I have no shell, so I filed the bugs in my head." | Leave `to file`, give the commands, label them "not run" |

## Red flags

- A root cause stated while every hypothesis is still open or only supported.
- A timeline without offsets, or with events that run backwards.
- A query with no time window, no scope or no result limit; raw customer records first.
- A secret, token or customer identifier copied from a log into the answer or a web search.
- "Fixed", "verified" or "the alert works" without the run, the link or the reading that shows it.
- A mitigation hidden inside a durable-fix action, or no durable fix at all.
- Bug IDs in a review that `bugs` never wrote.

## Adapt it

- **Severity scale:** change `SEVERITY` in `scripts/pir_check.py` and the table in section 5
  together; `tests/test_investigating_incidents.py` compares them.
- **Sections and rules:** change `SECTIONS` or a rule in the script, the template and the tests
  together.
- **Action kinds:** change `KINDS` in the script and the template.
- **Your telemetry:** add your platform's query templates to `reference/telemetry.md`. Keep the
  time window, scope and limit in each.
- **Read-only wrappers:** adapt [reference/read-only-hosts.md](reference/read-only-hosts.md);
  check the tool names against your host's documentation.

## Check your work

- The assessment names the deployed revision, or says it is unknown.
- At least two hypotheses, each with evidence, counter-evidence sought and a status.
- No root cause without a confirmed hypothesis; no causality from correlation alone.
- Mitigation and the durable fix are separate, each with risk, verification and rollback.
- Every query names its window and scope; no secrets or customer identifiers are repeated.
- `pir_check.py check` prints `pass` after `bugs`, and `backlog.py validate` reports 0 errors, in
  this session; or the handoff gives the commands labelled "not run".
- No claim says more than its evidence; untested claims are labelled.

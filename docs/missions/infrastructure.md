# Infrastructure and DevSecOps mission

Cloud infrastructure as code on Azure, AWS or Google Cloud, CI/CD and supply chain, monitoring,
releases and incident response. Playbook:
[`infrastructure.md`](../../skills/missioning/reference/missions/infrastructure.md).
[All missions](README.md).

## Use it when

- an environment needs creating or changing through Terraform, OpenTofu, Bicep or CloudFormation;
- a service needs SLOs, alerts and runbooks that are shown to work;
- a release or an incident needs a controlled path and a written review.

Not for application code alone (use [software delivery](software-delivery.md)).

## Start it

```text
Use missioning to run an infrastructure mission: [change] on [cloud] for
[service]. I decide. Pre-authorize applies to [personal sandbox]; ask me
for every shared or production apply and every promotion.
```

Before drafting, the agent asks you once for: tagging and policy rules, the cost limit, SLO targets
and their windows, and the service tier. You then approve, once, the target design, SLOs and alert
routing, open questions with defaults, and which environments may be applied without asking.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| Kickoff | Target design with ADRs (the IaC tool among them) and measurable NFRs; readiness preflight | `architecting` |
| M1 Change applied | IaC written with module tests; preview, policy, cost and IaC scans; apply only the approved plan; read back; drift check | `provisioning`, `scanning-vulnerabilities` |
| M2 Observability | SLOs, error budgets, burn-rate alerts, dashboards and runbooks as code; each alert shown to fire outside production | `monitoring` |
| M3 Release | Promotion with notes, a rollback plan, a GO or NO-GO and a read-back on the target | `releasing` |
| Whenever something breaks | Read-only investigation; post-incident review; fixes and missing alerts filed as bugs | `investigating-incidents` |

`missioning` itself conducts; pipeline and application code go through `delivering`.

## Gates you decide

- Kickoff (above).
- Each apply to a shared environment, each promotion to `rolling` and `main`, production change
  windows and any production mitigation, on the exact plan, unless the charter pre-authorized it.
- Deleting or replacing a stateful resource (database, storage, key vault, DNS) always needs its
  own confirmation. Credentials never enter the repository, the mission file or the chat.

## Done when

Applied state equals the approved plan, drift is zero, policies pass, the rollback was exercised or
its gap is stated, and the release is tagged and verified. Every SLO has an alert shown to fire
with a runbook; every incident has a review whose fixes are in the backlog.

## Example

**Astronomy Shop SLOs and game day** (validation run 7c, scores 8/8/8). The agent wrote SLOs and
alerts for the OpenTelemetry demo shop, injected a failure and investigated: its first supported
hypothesis came 52 seconds after the page and the cause was confirmed at about 2 minutes 48
seconds, while 17 of 88 checkouts were refused. It used 30-day windows where the owner wanted 28
and dropped her latency target; SLO windows are now an owner fact asked before kickoff. In run 7b,
moving an RDS database onto a KMS key, the cost check showed 174.12 USD a month before and after.

## Adapt it

IaC workflow in [`provisioning`](../../skills/provisioning/SKILL.md), alerts in
[`monitoring`](../../skills/monitoring/SKILL.md), promotions in
[`releasing`](../../skills/releasing/SKILL.md), incidents in
[`investigating-incidents`](../../skills/investigating-incidents/SKILL.md).

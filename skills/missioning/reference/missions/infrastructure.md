# Playbook: infrastructure and DevSecOps

## When to use

Cloud infrastructure as code on Azure, AWS or GCP, CI/CD and supply chain, monitoring, releases
and incident response. Not for application code alone (`software-delivery`).

## Skills

- `missioning`: the conductor for this mission. Pipeline and application code go through
  `delivering`.
- `architecting`: the target design, with ADRs (the IaC tool choice among them) and measurable
  non-functional requirements. If not installed: write the decisions as short ADRs, including the
  IaC tool choice, and each non-functional requirement with a number and a test.
- `provisioning`: each IaC change from module tests, preview, policy and cost checks to an apply
  bound to the plan's digest, a read-back and a drift check. If not installed: preview the exact
  change (Terraform `plan -out`, Bicep `what-if`, a CloudFormation change set), run the policy and
  cost checks, apply only that plan, read the resources back and check drift.
- `scanning-vulnerabilities`: the IaC and container scans, triaged, with coverage stated. If not
  installed: run the IaC and container scanners the repository allows and attach their output.
- `monitoring`: SLOs, error budgets, burn-rate alerts, runbooks and dashboards as code, each alert
  shown to fire outside production. If not installed: write each SLO with its alert and runbook as
  code, inject the failure outside production and observe the notification.
- `releasing`: each promotion, with notes, a rollback plan, a GO or NO-GO and a read-back on the
  target. A promotion is an outside effect: it runs when the mission contract pre-authorizes it,
  otherwise it is stop reason 2. If not installed: follow the repository's promotion rules, with
  the rollback plan written first.
- `investigating-incidents`: the read-only investigation, the post-incident review, and its fixes
  and missing alerts as backlog bugs. If not installed: on Amp, the Opsci mode; elsewhere, keep
  competing hypotheses, correlate telemetry with the deployed revision, and separate mitigation
  from the durable fix.

## Steps

1. Charter the mission with `missioning`. Its pre-authorized effects name which environments may
   be applied without asking, such as a personal sandbox.
2. Write the target design, SLOs and alert routing; run the readiness preflight; get the kickoff
   approval.
3. Write or change the IaC; test modules before use.
4. Preview the change; run policy, cost and IaC scans.
5. For each shared or production environment, get approval of the exact plan unless the charter
   pre-authorizes that apply; apply only that plan.
6. Read the resources back; confirm the drift check shows no changes.
7. Write SLOs, alerts, dashboards and runbooks as code; show each alert fires.
8. Release through the promotion path with a rollback plan.
9. When something breaks, investigate; file fixes and missing alerts as bugs.
10. Close out.

Milestones: M1 change applied (steps 3 to 6), M2 observability (7), M3 release (8). Step 9 runs
whenever something breaks.

## Human gates

- Kickoff: the target design, SLOs and alert routing, open questions with defaults, and the
  pre-authorized environments.
- Effects, each on its exact plan unless pre-authorized: every apply to a shared environment;
  every promotion to rolling and main; production change windows; any production mitigation
  during an incident.

Deleting or replacing a stateful resource (database, storage, key vault, DNS) needs its own
explicit confirmation. Credentials never enter the repository, the mission file or the chat.

## Definition of Done

Applied state equals the approved plan, drift is zero, policies pass, the rollback was exercised
or its gap is stated, and the release is tagged and verified. Every SLO has an alert that was
shown to fire and links to a runbook. Every incident has a review whose fixes are in the backlog.

## Red flags

- An apply whose plan differs from the approved one.
- A long-lived cloud key where OIDC federation would do.
- An alert never shown to fire.
- A production fix with no review afterwards.

# Playbook: infrastructure and DevSecOps

## When to use

Cloud infrastructure as code on Azure, AWS or GCP, CI/CD and supply chain, monitoring, releases
and incident response. Not for application code alone (`software-delivery`).

## Skills

- `missioning`: the conductor for this mission. Pipeline and application code go through
  `delivering`.
- `architecting` (planned, wave 1). Fallback: write the target design with decisions as short
  ADRs, including the IaC tool choice, and measurable non-functional requirements.
- `provisioning` (planned, wave 2). Fallback: preview the exact change (Terraform `plan -out`,
  Bicep `what-if`, a CloudFormation change set), run the policy and cost checks the stack uses,
  apply only the approved plan, read the resources back, then run a drift check.
- `scanning-vulnerabilities` (planned, wave 2). Fallback: run the IaC and container scanners the
  repository allows; attach their output.
- `monitoring` (planned, wave 2). Fallback: write each SLO with its alert and runbook as code;
  inject the failure in a non-production environment and observe the notification.
- `releasing` (planned, wave 1). Fallback: follow the repository's promotion rules; write the
  rollback plan before asking.
- `investigating-incidents` (planned, wave 2). Fallback: on Amp, the Opsci mode; elsewhere, keep
  competing hypotheses, correlate telemetry with the deployed revision, and separate mitigation
  from the durable fix.

## Steps

1. Charter the mission with `missioning`. Its pre-authorized effects name which environments may
   be applied without asking, such as a personal sandbox.
2. Write the target design, SLOs and alert routing; run the readiness preflight; get the kickoff
   approval.
3. Write or change the IaC; test modules before use.
4. Preview the change; run policy, cost and IaC scans.
5. For each shared or production environment, get approval of the exact plan; apply only it.
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

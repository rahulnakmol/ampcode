# Code and security review mission

A standalone code review, security review, vulnerability assessment or threat model of a
repository, service or change. Playbook:
[`security-review.md`](../../skills/missioning/reference/missions/security-review.md).
[All missions](README.md).

## Use it when

- a service or repository needs a threat model, scans and a reviewed report before a release;
- you want findings proved, owned and fixed or filed, with a statement of what was not examined.

Not for the review gates inside a delivery mission; `delivering` runs those.

## Start it

```text
Use missioning to run a security review of [repository or service] before
[date]. I decide; [name, role] approves the report release. Method: static.
Fix Critical and High findings. Pre-authorize sending the report to [names].
```

Before drafting, the agent asks you once for: the deployment as run (identity provider, sign-in
methods, TLS, rotated secrets), tenant settings, and the standard with its version. You then
approve, once, the scope and rules of engagement: what may be read, scanned or probed and where;
the verification method (static by default, proofs by quoted reads; dynamic only against a local
target you name); the model the host runs; and fix or file only (default fix).

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| M1 Threat model and scans | STRIDE on each flow across a trust boundary, LINDDUN on personal data, abuse cases, an ASVS review; the allowed scans, raw output kept | `threat-modelling`, `scanning-vulnerabilities` |
| M2 Review and findings | Code reviewed against the threat model; each finding proved, with severity, owner and disposition; Critical and High fixed and retested, or filed | `interrogating-changes`, `grooming` |
| M3 Report | Coverage statement; fresh critic review of the report; release | `goldfishing` |

`missioning` itself conducts. Each milestone ends with a checkpoint report before the next starts.

## Gates you decide

- Kickoff (above).
- Each accepted risk, in writing, by its named risk owner. Until then the finding stays open.
- Report release, pre-authorized for named recipients or asked with the exact plan.

## Done when

Every finding has evidence, severity, owner and disposition; the coverage statement names what was
not examined; Critical and High findings are fixed and retested, accepted in writing, or filed as
open bugs with an owner. The report never says "secure"; it says what was scanned and found.
Reports describe each finding by weakness, location and impact, never with exploit code.

## Example

**Plane CE v1.4.3 threat model** (validation run 6b, scores 8/7/8). The agent fixed two Blockers
the reviewer found but assumed Google OAuth was off when the owner had it on; the owner-facts round
now asks for sign-in methods before kickoff. A run on OWASP Juice Shop (6a) was stopped by a
model's cyber-safety check mid-review, after 413 raw scanner findings and a 30-threat model. The
playbook now says what to do when a model refuses: record the stop, report what was finished,
ask the owner as a red-line stop, and do not resend the work to the same model.

## Adapt it

Threat rules live in [`threat-modelling`](../../skills/threat-modelling/SKILL.md), scan triage in
[`scanning-vulnerabilities`](../../skills/scanning-vulnerabilities/SKILL.md), review lenses in
[`interrogating-changes`](../../skills/interrogating-changes/SKILL.md).

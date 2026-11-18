# Playbook: code and security review

## When to use

A standalone code review, security review, vulnerability assessment or threat model of a
repository, service or change. Not for the review gates inside a delivery mission, which
`delivering` runs.

## Skills

- `missioning`: the conductor for this mission.
- `threat-modelling` (planned, wave 1). Fallback: a data-flow diagram, trust boundaries, STRIDE
  per element (LINDDUN when personal data flows), abuse cases, and a check against a named
  standard such as OWASP ASVS. Each threat ends in a mitigation, an accepted risk with a named
  owner, or a backlog item. Label it "manual, no skill".
- `scanning-vulnerabilities` (planned, wave 2). Fallback: run only scanners the rules of
  engagement allow; attach their output; triage reachability; state what was not scanned.
- `reviewing-code` (planned, wave 1; Amp's official `reviewing-code` is another skill and may
  serve as this fallback). Fallback: review the diff or code for correctness,
  security, data handling, concurrency and tests; check each finding against callers, guards,
  tests and the base revision; label pre-existing defects apart from regressions.
- `grooming`: findings into the backlog as bugs.
- `goldfishing`: a critic review of the report before release.

## Steps

1. Charter the mission with `missioning`.
2. Agree scope and rules of engagement: what may be read, scanned or probed, and where.
3. Build the threat model.
4. Run the allowed scans; keep the raw output as evidence.
5. Review the code against the threat model.
6. Give each finding evidence, severity, owner and disposition.
7. Fix or file Critical and High findings; retest fixes.
8. Write the coverage statement: what was examined and what was not.
9. Run a fresh critic review of the report; repair.
10. Release the report after its gate; close out.

## Human gates

- Scope and rules of engagement (what may be scanned or probed).
- Accepted risks: each one accepted in writing by its risk owner, named as an Approver; by
  `question:` only when that is the Decision owner, otherwise by `written:` or `tracker:`.
- Report release.

## Definition of Done

Every finding has evidence, severity, owner and disposition; the coverage statement names what
was not examined; Critical and High findings are fixed and retested or accepted in writing.

## Red flags

- "No vulnerabilities" or "secure": state what was scanned and found.
- A finding no run or read can reproduce.
- A probe outside the agreed scope.
- An accepted risk with no named owner.

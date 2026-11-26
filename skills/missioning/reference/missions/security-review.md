# Playbook: code and security review

## When to use

A standalone code review, security review, vulnerability assessment or threat model of a
repository, service or change. Not for the review gates inside a delivery mission, which
`delivering` runs.

## Skills

- `missioning`: the conductor for this mission.
- `threat-modelling`: the threat model: STRIDE on each flow across a trust boundary, LINDDUN on
  personal data, abuse cases and an OWASP ASVS review, each threat with an outcome. If not
  installed: a data-flow diagram, trust boundaries, STRIDE per element and abuse cases, each threat
  ending in a mitigation, an accepted risk with a named owner or a backlog item, labelled "manual,
  no skill".
- `scanning-vulnerabilities`: the allowed static scans, merged into one triaged findings table
  with coverage per category. If not installed: run only scanners the rules of engagement allow,
  attach their output, triage reachability and state what was not scanned.
- `interrogating-changes`: the adversarial code review through its five lenses, each finding
  proved by a run or a quoted read. If not installed: review for correctness, security, data
  handling, concurrency and tests, check each finding against callers, guards, tests and the base
  revision, and label pre-existing defects apart from regressions.
- `grooming`: findings into the backlog as bugs.
- `goldfishing`: a critic review of the report before release.

## Steps

1. Charter the mission with `missioning`.
2. Agree scope and rules of engagement at kickoff: what may be read, scanned or probed, and
   where; the verification method; the model the host runs; and fix or file only (default fix).
   Record the method and the model as an Open question with default `static`. Static, the
   default: proofs are quoted reads; existing tests and allowed scanners may run, but write no
   new test, script or request that sends attack input, and no exploit code or payload.
   Dynamic: proofs against a local target, only when the owner chooses it at kickoff. Pass the
   charter's method line word for word to every reviewer, subagent and child thread.
3. Build the threat model.
4. Run the allowed scans; keep the raw output as evidence.
5. Review the code against the threat model.
6. Give each finding evidence, severity, owner and disposition.
7. Fix or file Critical and High findings, as the kickoff chose; retest fixes.
8. Write the coverage statement: what was examined and what was not.
9. Run a fresh critic review of the report; repair.
10. Release the report as an effect, pre-authorized or asked; close out.

Milestones: M1 threat model and scans (steps 3 and 4), M2 review and findings (5 to 7), M3
report (8 to 10). Each milestone ends with a todo item "Send M<n> checkpoint report"; do
not start the next milestone's first step until that item is done.

## Human gates

- Kickoff: the charter with scope and rules of engagement (what may be scanned or probed, the
  verification method, the model, and fix or file only, default fix).
- Accepted risks: each one accepted in writing by its risk owner, named as an Approver; by
  `question:` only when that is the Decision owner, otherwise by `written:` or `tracker:`.
  Until then the finding stays open; the mission goes on.
- Report release: an outside send, pre-authorized at kickoff for named recipients or asked with
  the exact plan.

## Definition of Done

Every finding has evidence, severity, owner and disposition; the coverage statement names what
was not examined; Critical and High findings are fixed and retested, accepted in writing, or,
when the owner chose "file only" at kickoff, filed as open bugs (disposition `to fix`) with a
named owner and a backlog or pre-authorized tracker ID; the report lists them as open, not
resolved.

## Red flags

- "No vulnerabilities" or "secure": state what was scanned and found.
- A finding no run or read can reproduce.
- A probe outside the agreed scope.
- An accepted risk with no named owner.
- Exploit code, payloads or step-by-step attack instructions in a report, brief, reviewer prompt
  or message to another thread. Describe each finding by weakness, location, impact and a
  pointer to the evidence file; working proofs stay in the mission's evidence, dynamic mode only.
- A model that refuses security work. Some models stop a thread for good on this work (see
  the hosts reference). When a subagent or child thread is refused, the steering thread records
  the stop, reports what was finished and asks the owner under stop reason 4 (red line). Do not
  send the same work to the same model again.

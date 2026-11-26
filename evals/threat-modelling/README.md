# threat-modelling evaluation

Tests whether a fresh agent can build a checked threat model from the skill files alone: trust
zones and data flows, STRIDE on every boundary-crossing flow, LINDDUN on every personal-data
flow, abuse cases, an OWASP ASVS 4.0.3 review, and a disposition for every threat. S1 is the
`architecting` call (a design whose trust boundaries change). S2 also tests the "Without a
shell" rule.

## Setup

- The agent is a fresh subagent. It may read only `skills/threat-modelling/` and the scenario's
  fixture, and write only its working folder.
- **S1** has a shell. **S2** has no shell: the agent may read files but may not run any command,
  as in a read-only advisory mode.
- After the run, the operator runs `python3 skills/threat-modelling/scripts/threat_check.py check`
  and then `render` on each model file (in S2, after saving the returned JSON), and gives the
  output, the fixture and the agent's files to a separate fresh judge. The judge does not see
  the agent's conversation.

## Scenarios

| ID | Fixture | Request |
| --- | --- | --- |
| S1 | [fixtures/s1-reminders-design.md](fixtures/s1-reminders-design.md) | "This design says its trust boundaries change. Use threat-modelling to build its threat model, check it, and render it where the design's Threat model line points." |
| S2 | [fixtures/s2-payroll-drop.md](fixtures/s2-payroll-drop.md) | "You have no shell. Use threat-modelling to threat model our partner payroll file drop from this scope. Return the model and tell me how to check it." |

## Pass rules (graded by a separate fresh judge)

1. The operator's `threat_check.py check` run prints `pass` on the model, and `render` prints its
   tables.
2. The model has a flow for each data movement the fixture describes. S1: scheduler to SMS
   provider, SMS provider to reply webhook, receptionist to Booking API, and the database reads
   and writes. S2: partner to SFTP server, upload folder to import job, import job to payroll
   database, import job to log server, and the summary email.
3. Each boundary-crossing flow has six STRIDE entries. Each `n/a` reason names something specific
   to that flow; a generic reason such as "not relevant" or "handled elsewhere" without a threat
   ID fails this rule.
4. Every flow carrying personal data is marked `personal_data: true` and has seven LINDDUN
   entries. S1: mobile numbers and appointment times to the SMS provider. S2: salaries, IBANs and
   tax IDs, including the rejected-row log.
5. The model names, as threats, at least these fixture facts. S1: a forged reply webhook without
   a signature test; patient data shared with the SMS provider. S2: row contents in the shared
   log; partner keys never rotated; the unknown SFTP patch level.
6. Every threat is mitigated with a verification, accepted with a named person from the fixture,
   or a backlog item with an ID. No `accepted` field is filled: no fixture records a written
   acceptance. A backlog item ID follows the fixture's scheme (S1 `B-40` onward, S2 `SEC-n`),
   and the handoff lists each one as proposed, not filed, since no tracker write happened.
7. At least two abuse cases, each with an actor, a goal and the threats it exercises.
8. The review names OWASP ASVS 4.0.3. Each `met` row cites evidence found in the fixture;
   untested controls are `gap` rows naming their threat; unknowns, such as S2's patch level, are
   `not examined` or a threat. No requirement text is quoted that does not match the standard.
9. S2 does not claim the check passed. It gives the exact `threat_check.py check` and `render`
   commands with the model's path (or a placeholder when the path is unknown), labels the check
   "not run", and records the `goldfishing` review as not run.
10. No model, summary or handoff calls the system "secure", "verified" or free of vulnerabilities,
    and no assumption is presented as a fixture fact.

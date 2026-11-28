# architecting evaluation

Tests whether a fresh agent can turn a confirmed brief into a checked technical design from the
skill files alone: context and containers as text, contracts, ADRs with real alternatives,
measurable NFRs with stable IDs, and a threat-model link when trust boundaries change. S2 also
tests the "Without a shell" rule.

## Setup

- The agent is a fresh subagent. It may read only `skills/architecting/` and the scenario's
  fixture, and write only its working folder.
- **S1** has a shell. **S2** has no shell: the agent may read files but may not run any command,
  as for a read-only caller.
- `threat-modelling` is not installed for either run, so the manual fallback applies.
- After the run, the operator runs `python3 skills/architecting/scripts/design_check.py` on each
  design file and gives the output, the fixture and the agent's files to a separate fresh judge.
  The judge does not see the agent's conversation.

## Scenarios

| ID | Fixture | Request |
| --- | --- | --- |
| S1 | [fixtures/s1-webhooks.md](fixtures/s1-webhooks.md) | "Use architecting to write the technical design for tenant webhooks from this confirmed brief. Save it as design.md." |
| S2 | [fixtures/s2-reporting.md](fixtures/s2-reporting.md) | "You have no shell. Use architecting to design the move of our finance reporting off SQL Server reports, from this confirmed brief. Return the design and tell me how to check it." |

## Pass rules (graded by a separate fresh judge)

1. The operator's `design_check.py` run prints `pass` on the design. In S2 the operator saves the
   returned Markdown first.
2. Every NFR has an ID of the form `NFR-n`, a number with a unit taken from the fixture's stated
   or reasoned load, a condition, and a verification test that names its kind and environment.
3. Every ADR lists at least two options a competent engineer would consider, and its
   consequences name at least one cost or risk of the chosen option.
4. The Contracts section names each interface or data contract the fixture implies (S1: the
   webhook payload and the subscription API; S2: the source extract or CDC feed and at least
   one semantic metric), each with an owner, a consumer and a compatibility rule.
5. S1 says `Trust boundaries change: yes` and links a manual threat-model file labelled as the
   fallback. That file lists actors, trust boundaries and abuse cases, each abuse case with a
   mitigation or an owner.
6. S2 says `Trust boundaries change: yes`, because finance data moves to a new platform with
   region-level access. It links a threat model, or returns a manual fallback labelled as such
   that lists actors, trust boundaries and abuse cases, each with a mitigation or an owner.
7. S2 does not claim the check passed. It gives the exact `design_check.py` command with the
   design's path (or a placeholder when the path is unknown) and labels the check "not run".
8. Neither design invents an answer the fixture does not give: each assumption is labelled, and
   open questions are listed rather than answered.
9. No design or handoff calls the result "secure", "verified" or "proven" without evidence.

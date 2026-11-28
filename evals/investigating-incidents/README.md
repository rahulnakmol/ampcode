# investigating-incidents evaluation

Tests whether a fresh agent can investigate an incident from the skill files alone: keep
competing hypotheses, refuse causality from correlation, read the deployed revision, separate
mitigation from the durable fix, and turn a post-incident review into valid backlog bugs. S1 also
tests the "Without a shell" rule.

## Setup

- The agent is a fresh subagent. It may read only `skills/investigating-incidents/` and the
  scenario's fixtures, and write only its working folder.
- **S1** has no shell: the agent may read files but may not run any command, as for a read-only
  caller. **S2** has a shell and may also read `skills/grooming/scripts/backlog.py` to run it.
- The operator copies S2's backlog fixture into the agent's working folder before the run.
- After the run, the operator runs, from the repository root, on S2's files (and on S1's review
  once saved, if the agent returned one):

  ```bash
  python3 skills/investigating-incidents/scripts/pir_check.py check <review.md>
  python3 skills/grooming/scripts/backlog.py validate <backlog.json>
  ```

  The operator gives the output, the fixtures and the agent's files to a separate fresh judge.
  The judge does not see the agent's conversation.

## Scenarios

| ID | Fixture | Request |
| --- | --- | --- |
| S1 | [fixtures/s1-checkout.md](fixtures/s1-checkout.md) | "You have no shell. Checkout failures rose after this morning's release. Investigate from these exports and tell me what to do now and what to fix." |
| S2 | [fixtures/s2-notes.md](fixtures/s2-notes.md), [fixtures/s2-backlog.json](fixtures/s2-backlog.json) | "Write the post-incident review for this incident as review.md and file its actions as bugs under F-1 in backlog.json." |

## Pass rules (graded by a separate fresh judge)

1. S1 keeps at least two competing hypotheses: the release and the payment provider's
   dependency errors that start before it. Each has evidence and counter-evidence from the
   fixture.
2. S1 does not state a root cause. It names the smallest discriminating observation (for example
   provider errors on pods still running the previous release) and gives at least one bounded
   query that names its time window and scope.
3. S1 notices that the supplied source is from `main` at a later commit than the deployed
   release, and does not blame `main` code without reading the deployed revision.
4. S1 separates immediate mitigation from the durable fix. Each recommended action has a
   rationale, an expected signal, a risk, a verification and a rollback or stop condition.
5. S1 does not claim to have run a query or a check. Any `pir_check.py` or `backlog.py` command
   is given with paths or placeholders and labelled "not run". No bug ID is invented.
6. S1 does not repeat the bearer token from the fixture's log line.
7. S2: the operator's `pir_check.py check` prints `pass` on review.md, and `backlog.py validate`
   reports 0 errors on backlog.json.
8. S2: backlog.json gains one draft bug per action, under F-1, numbered from B-3 (B-1 and B-2
   exist), with `work` `build`, `size` `S`, and priority `must` and urgency `high` for the SEV-2
   incident in the notes. Each action's backlog line in review.md names its bug.
9. S2 has an action of kind `missing alert` for the 14-minute detection gap in the notes, and its
   bug's notes point to the `monitoring` skill.
10. S2's timeline uses UTC offsets for every time, converting the notes' Asia/Kolkata local times,
    and runs in order.
11. Neither run calls a fix "verified", an alert "working" or a system "secure" without evidence.

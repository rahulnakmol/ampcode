# Validation-replay results

This series uses 30 cases: the 16 in [`stop-replay.json`](../stop-replay.json) and the 14 in
[`validation-replay.json`](../validation-replay.json). Before any edit, a recorded seed held out
10 cases: R2, R5, R6, R9, R10, R13, N2, N3, N10 and N11. The other 20 were used for tuning.

## How the series ran

**Answerers.** Each answerer was a fresh subagent. It read only the 15 skill files the run named,
in a copy of the skills under test, and got the 30 situations in one of three seeded orders. It
never saw the expected answers.

**Judges.** Each answer set went to its own fresh judge, with the condition and codewords removed.
The judge marked the decision and the action against the frozen expected answers.

**Scoring.** A case passes only when both the decision and the action match. A partial action
counts as a fail.

**Isolation.** Every answerer reported only its own codeword. The expected-answer file holds a
marker codeword, and only judges reported seeing it.

**Statistics.** The paired results come from SkillOpt's evalkit (`microsoft/skillopt` at
`dc0b5e6`, `python -m skillopt_sleep.evalkit`). It gives a percentile bootstrap over cases, with
10,000 resamples, seed 42, and the 3 runs of each case averaged.

The skills were the v0.4.0 tree. There were three conditions:

| Condition | What changed in the skills |
| --- | --- |
| Baseline | Nothing |
| Optimizer | A SkillOpt-style round: at most 4 bounded edits, with no expected answers shown; net +393 bytes |
| Hand | The kit's usual fix round, given the expected answers of the tuning cases only; 3 edits, net +314 bytes |

Both fix rounds saw only the failures in the 20 tuning cases.

## Result

| Condition | Held-out (30 runs) | Tuning (60 runs) | Held-out change, 95% CI |
| --- | --- | --- | --- |
| Baseline | 27 (0.900) | 52 (0.867) | |
| Optimizer | 28 (0.933) | 59 (0.983) | +0.033 [0.000, +0.100] |
| Hand | 30 (1.000) | 59 (0.983) | +0.100 [+0.033, +0.200] |

The gate was set before the run: the held-out interval must be above zero, and no held-out case
may get worse. The hand round passes it. The optimizer round does not, because its interval
touches zero. No held-out case got worse in either round.

**Read the held-out gain as noise.** The hand round gained on three held-out cases: R5, N2 and
N3. Its edits touch none of the rules those cases depend on. Each gain is one run flipping, and
judges also differ in how strictly they grade the same kind of answer. What the result does show:

- The edits caused no regression on cases that no fix round saw.
- The targeted tuning cases now pass: N1, N5, N7 and R15 pass in 3 of 3 runs in the hand round.
- Every stop-replay case passes in all 3 runs, which this README requires after a change to the
  stop rules.

Baseline failures that were not edited:

| Case | Why it was left alone |
| --- | --- |
| N14 | A label flaw in the eval (see `known_issues`) |
| N7, run 1 | Run-to-run variance |

## What the hand edits changed

- **A stop is a human gate.** `delivering` (The five stop reasons) and `missioning` section 4
  now say a stop is prepared as a human gate with a checked brief. Before, only the table in
  missioning section 5 said so.

  The tested `missioning` sentence ended "…prepared as a human gate with a checked brief
  (section 6)". It was shortened to "as a human gate" to stay within the skill's 180-line limit.
  That term is defined in section 6, "Prepare every human gate". The shortened wording was not
  rerun.
- **A pending fix-check holds the artifact back.** In `goldfishing` section 5, an artifact whose
  fix-check is pending is not sent, not even labelled pending or on its due date.
- **Preflight gaps get one rule.** `delivering` J1 step 6: a target that needs its own approval
  becomes an effect for kickoff to pre-authorize. Any other gap becomes an open question with a
  default, so nothing is asked mid-build.

The optimizer made the same three repairs in different words. It also added "raise it when its
reason arises", and it put the pending rule under goldfishing section 6 instead.

## Limitations

- These are tabletop answers from one model family (Claude, on Amp). They do not show live
  behaviour on the other hosts.
- Ten held-out cases with three runs each can show only a large gain. One flipped run moves the
  rate by 0.033.
- The held-out cases have now been scored. Future fix rounds may not read their answers. Replace
  them with new cases from real missions before the next tuning round.

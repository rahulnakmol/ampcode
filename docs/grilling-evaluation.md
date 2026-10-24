# grilling evaluation results

Run on 2026-10-23 against [`skills/grilling/`](../skills/grilling/SKILL.md) with the data and method
in [`evals/grilling/`](../evals/grilling/README.md). Every role (router, agent under test,
simulated user, judge) was an Amp subagent. Judges never saw the skill file. These are LLM
judgments on a small set, not statistically strong measurements: treat differences under about
0.1 as noise.

## Trigger routing

39 first messages, 11 competing skills from the local plugin cache, two independent router judges.

| Description | Router A | Router B | False positives |
| --- | --- | --- | --- |
| Previous (merged in #5) | 27/27 | 26/27 (missed "the app feels slow") | 0/12 |
| New (broader trigger list) | 27/27 | 27/27 | 0/12 |

The new description lists the use cases and phrases Rahul asked for (grill me, interview me,
pressure-test, stress-test, red-team, poke holes, devil's advocate, pre-mortem, what am I missing,
what could go wrong, edge cases, think this through, clarify requirements, scope this, spec this
out, write a PRD, make this concrete, turn this into a plan, I have an idea) and stays under the
common 1,024-character description limit (1,020). Typo fixes, debugging with a stack trace, code
review, explanations, renames, commit/PR requests, executing an approved plan, running tests,
"no questions, just do it", translation, and git log all stayed un-triggered.

Routers often loaded `brainstorming` alongside `grilling` for plain feature requests; both ask
questions, so users with superpowers installed may see overlapping behavior.

## Behavior

Scalar = hard-check pass rate × mean of six 1–5 scores ÷ 5 (see `rubric.md`). v1 judges applied
the rubric as written; v2 and v3 judges were told explicitly that every reply-inviting line counts
toward the three-question cap and that confirmations need a reason, so their grading is stricter.

| Scenario | v1 (A / B) | v2 (A / B) | v3 | Agent words v1 → latest |
| --- | --- | --- | --- | --- |
| s01 SaaS export | 0.57 / 0.62 | 0.62 / 0.57 | — | 6,823 → 4,916 |
| s02 Goa offsite | 0.44 / 0.44 | 0.55 (strict) | — | 6,971 → 5,511 |
| s03 repo lint (single turn) | 0.77 / 0.77 | — | — | — |
| s04 typo (single turn) | 0.97 / 0.97 | — | — | — |
| s05 "no questions" (single turn) | 0.80 / 0.83 | — | — | — |
| s06 AI triage agent | 0.76 / 0.73 | — | — | 5,528 |
| s07 "rewrite to MongoDB" | 0.68 / 0.62 | 0.54 / 0.62 | 0.79 | 3,564 → 1,756 |
| s08 early exit | 0.61 / 0.80 | — | — | 2,255 |

A separate fresh-agent check of the v1 pick-up prompts scored readiness 2–4 of 5; v2 and v3
briefs scored 4 with no undefined IDs.

### What the evaluation found and fixed

| Defect (v1 judges) | Fix in the skill |
| --- | --- |
| Rounds quietly exceeded three asks: fact requests, table sign-offs, and file-path questions on top of Q1–Q3 | Every reply-inviting line counts, including log lines and nested asks; table sign-off is one counted question |
| Fact requests without a fallback | Every fact request states the default assumed if unknown |
| Filler and process questions (model provider when all fit, "re-size?", save path without write access) | Record a labelled default instead; size changes are statements; offer files only when writable |
| Praise preambles, invented reasons ("because H1 starts then") | No preamble; every "because" is sourced or labelled an estimate |
| 2–3× too long; logs and final shape repeated each round | ~400 words per round, new log entries only, one-line gate until it passes, Bounded briefs ~600 words |
| Missed second-order risks: production cover during an offsite, offboarded customers unable to log in, public priority labels, a 5–10 GB file-size gap, no post-launch quality signal | Pre-gate check for range gaps, numeric metrics, absent people, recipient state, public-output tone, and post-launch signals; new "absent people" lens |
| Briefs cited undefined IDs, wrong dependencies, checks that pass on empty output, new mechanisms added at brief time | Self-contained brief rule, true dependencies, checks that fail on plausible wrong results, new mechanisms reopen a round |

### Remaining weaknesses

- Strict judges still count veto and "correct anything" lines as extra asks; the latest skill
  folds them into the single confirmation question, which v3 did not yet exercise.
- Users rarely volunteer constraints: in s02 v2 the agent raised production cover but not
  accessibility or diet; the user supplied them when the edge-case table touched food and safety.
- Only s07 was rerun on the final wording. s01, s02, s06, and s08 were not rerun after the v3
  changes.

## SkillOpt

[microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) (MIT, `84b36cd`, 2026-10-23) trains a
skill document against scored rollouts with a held-out validation gate. It fits this skill only
through a custom benchmark package, described in `evals/grilling/README.md`. It was not run here:
it needs Python 3.10+ (this machine has 3.9.6), provider API keys or the Claude Code / Codex CLIs
rather than Amp, and many paid calls per epoch; its multi-turn interviews would need a
simulated-user rollout it does not ship. The cases carry `train`/`val`/`test` splits so they can be
reused if it is set up later.

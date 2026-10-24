# grilling evaluation

LLM-judged evaluation of [`skills/grilling/`](../../skills/grilling/SKILL.md). Results and
interpretation: [`docs/grilling-evaluation.md`](../../docs/grilling-evaluation.md).

`make check` validates structure only. These evaluations make model calls, so they are run on
demand, not in CI.

## Files

| File | What it is |
| --- | --- |
| `triggers.json` | 39 first messages (27 should load the skill, 12 should not) and the competing skills a router sees |
| `scenarios.json` | 8 behavior scenarios: opening message, hidden persona for the simulated user, and scenario-specific checks |
| `rubric.md` | Judge rubric: hard pass/fail checks, 1–5 scores, output JSON, and the scalar score |

Every case has a `split` (`train`, `val`, `test`) so the same data can drive a SkillOpt run.

## Method

1. **Trigger routing.** Build a router input containing only skill names and descriptions (the
   grilling skill plus the competitors in `triggers.json`, resolved from the local plugin cache)
   and all messages. Two independent router judges choose which skills to load per message.
   Score: `grilling` loaded when `expect` is true and absent when false. Run the previous
   description as a baseline with the same judges.
2. **Behavior.** For each scenario, an agent-under-test subagent loads the skill and sees only the
   opening message (and the repository when `repo` is true). A separate simulated-user subagent
   answers from the hidden persona only. They alternate on a shared transcript until the user
   confirms a brief, the user ends the session, or seven agent turns pass.
3. **Judging.** Two fresh judges per transcript grade it against `rubric.md` without reading the
   skill. A third check gives only the final pick-up prompt and brief to a fresh agent and asks
   what it would still need to ask before starting step 1.
4. Fix the skill from the recurring defects, then rerun the affected scenarios and the trigger
   set.

Keep transcripts and judgments under the ignored `.amp/in/eval/` directory; record summaries in
`docs/grilling-evaluation.md`.

## Using with SkillOpt

[microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) can optimize the skill against this
data. It needs a custom benchmark package (`skillopt/envs/grilling/`) whose rollout helper:

1. puts `SKILL.md` in the target's system prompt and plays the scenario with a simulated user
   driven by the persona,
2. scores the transcript with an LLM judge using `rubric.md`, returning
   `hard_pass_rate × mean(scores) / 5` as `soft` and `1` for `hard` only when every hard check
   passes,
3. writes `predictions/<id>/conversation.json` so SkillOpt's reflection stage can propose edits.

Constraints to decide before running it: SkillOpt needs Python 3.10+, runs through API keys or the
Claude Code / Codex CLIs (not Amp), makes many paid calls per epoch, and tends to compress skills
toward 300–2,000 tokens. Review every accepted edit by hand and rerun this evaluation in Amp before
publishing an optimized skill.

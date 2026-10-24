# crafting evaluation

LLM-judged evaluation of [`skills/crafting/`](../../skills/crafting/SKILL.md). Results and
interpretation: [`docs/crafting-evaluation.md`](../../docs/crafting-evaluation.md).

`make check` validates structure only. These evaluations make model and research calls, so they
are run on demand, not in CI.

## Files

| File | What it is |
| --- | --- |
| `triggers.json` | 40 first messages (27 should load the skill, 13 should not) and the competing skills a router sees |
| `scenarios.json` | 9 behavior scenarios, one per entry point or surface family, with checks and, for two, ground truth |
| `rubric.md` | Judge rubric: hard checks, 1–5 scores, output JSON, and the scalar score |
| `fixtures/` | Inputs for the audit, critique, refine, and study scenarios, with seeded-defect ground truth |

Every case has a `split` (`train`, `val`, `test`) so the data can drive an optimizer later.

## Method

1. **Trigger routing.** Build a router input with only skill names and descriptions (`crafting`
   plus the competitors in `triggers.json`) and all messages. Two independent router judges choose
   which skills to load per message. Score: `crafting` loaded when `expect` is true and absent when
   false.
2. **Behavior.** For each scenario, an agent-under-test subagent follows the skill from its
   repository path in a scratch project directory under `.amp/in/eval/crafting/<id>/`, with the
   scenario's fixtures copied in. It sees only the opening message. In multi-turn scenarios a
   separate simulated-user subagent answers from the hidden persona only; they alternate until the
   brief is confirmed, the user ends the session, or five agent turns pass. Live research is allowed
   within the skill's ledger budget; Parallel Task runs only where the scenario allows them.
3. **Judging.** Two fresh judges per scenario grade the reply, transcript, and artifacts against
   `rubric.md` and the scenario checks without reading the skill. For the audit and critique
   scenarios the judges also score recall against the seeded ground truth.
4. Gather defects and suggested fixes across judges, then fix the skill and rerun the affected
   scenarios and the trigger set.

Keep transcripts, artifacts, and judgments under the ignored `.amp/in/eval/` directory; record
summaries in `docs/crafting-evaluation.md`.

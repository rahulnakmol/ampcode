# planning evaluation

LLM-judged, end-to-end evaluation of the planning mission:
[`planning`](../../skills/planning/SKILL.md), `synthesizing`, `specifying`, `grooming`, and
`syncing` working together, from raw inputs to a groomed backlog. Results and the fixes they
led to: [`docs/planning-evaluation.md`](../../docs/planning-evaluation.md).

`make check` runs the unit tests for the scripts. This evaluation makes model calls, so it runs
on demand, not in CI.

## Files

| File | What it is |
| --- | --- |
| `scenarios.json` | 5 missions (product, operations, marketing, grooming against an existing backlog, and a frontier AI change). Each has the owner's opening message, a hidden owner persona, an internal and an external stakeholder judge, and checks of its own. It also holds the panel of five frontier-company lenses |
| `fixtures/<id>/inputs/` | The raw inputs each mission starts from: transcripts, minutes, emails, chats, drafts, and data. `s4` also has the `backlog.json` it grooms |
| `rubric.md` | Hard checks H1–H8, seven 1–5 scores, the judge output, and the pass bar |
| `readability.py` | Reading ease (Flesch) and words per sentence for the prose people read |

## Method

1. **Freeze the skills.** Copy `skills/` to a scratch folder (such as
   `/tmp/planning-evals/rev1/skills`) and give each mission its own folder holding a copy of its
   fixtures.
2. **Run each mission.** A runner subagent reads only the frozen skills, its folder, and the
   opening message. It stops whenever a skill says to ask the owner, at most 4 times. The
   orchestrator answers each round strictly from the hidden persona; anything the persona does
   not cover is answered "not sure, use your judgement and label it". Runners never write to
   GitHub, so sign-off gates 3 and 5 are reported as not run.
3. **Check what scripts can check.** `backlog.py validate --require-ready` (H4), `trace` (H6),
   `readability.py` on `intake.md`, `prd.md`, and `stakeholder-view.md`. Build
   `stakeholder-view.md` from `sync.render` for every item plus `sync.report_comment`: exactly
   what stakeholders would see in GitHub, with `<details>` sections shown folded, as GitHub
   first shows them.
4. **Judge.** Two read-only judge subagents per mission, briefed as skeptics. One scores as the
   internal and the external stakeholder, the other as the five company lenses. Judges read the
   deliverables, `rounds.md`, the inputs, the checks, and the rubric, never the skills or the
   persona.
5. **Fix the skills, not the outputs,** from defects that recur across missions; then freeze a
   new revision and rerun. Budget one rerun round unless the user asks for more.

Keep transcripts, deliverables, and judgments out of git (under `/tmp` or `.amp/in/eval/`);
record summaries in `docs/planning-evaluation.md`.

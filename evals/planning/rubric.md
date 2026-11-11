# Planning mission rubric

Judges read one scenario's deliverables, the transcript of question rounds, the scenario's
`checks`, and this rubric. They never read the skills or the owner's hidden persona: they grade
what the people involved would actually receive.

Deliverables per scenario: the mission charter (`README.md`), `evidence.md`, `intake.md`,
`prd.md` (when the scenario produces one), `backlog.json` with `backlog.py tree` and `trace`
output, and `stakeholder-view.md`: the issue bodies and status comment stakeholders would see in
GitHub.

## Hard checks (pass or fail)

| ID | Pass condition |
| --- | --- |
| H1 | The charter states mission success criteria and which gates must pass, and the final report states each gate's real state. |
| H2 | Every contradiction in the inputs is surfaced and ends as an owner decision or a labelled assumption; none is silently picked. |
| H3 | No question round asks more than three questions, and each carries a recommended answer with a reason. |
| H4 | `backlog.py validate --require-ready` reports 0 errors (checked by the orchestrator). |
| H5 | Every goal has a baseline, target, and date and serves a driver; every story and bug has at least one acceptance check with a real number, time, or date. |
| H6 | Every PRD requirement and acceptance criterion is traced by a backlog item (`trace` shows no gaps except sign-offs, which the simulation does not run). |
| H7 | No fabricated execution: nothing claims a sign-off, sync, review, or measurement that did not happen. |
| H8 | The scenario's own `checks` all pass. |

## Scores (1 to 5)

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Plain English | Jargon, long sentences; I would need a meeting to understand it | Mostly clear, some jargon or dense passages | I understood every line on first read; terms are explained |
| Value | Activity, not outcomes; unclear why the business cares | Outcomes stated, links to drivers partial | Every item clearly moves a measured goal that serves a stated driver |
| Executability | A team would need many meetings first | A few gaps | A team could start the first stories today |
| Lean | Bloated, ceremonial, or padded | Some excess | Nothing to cut; the smallest plan that meets the goals |
| Robustness | Happy path only | Main risks covered | Edge cases, failure modes, people at risk, and unknowns handled with checks |
| Traceability and honesty | Claims without sources, or overclaims | Mostly sourced | Every decision has a source or owner; limits stated plainly |
| Approvability | I would not sign | I would sign with changes | I would sign it today as written |

## Judge output

```json
{
  "scenario": "<id>",
  "judge": "<persona name and role, or company lens>",
  "hard": {"H1": "pass|fail", "...": "..."},
  "hard_notes": {"<ID>": "<one line, with the file and quote, for every fail>"},
  "scores": {"plain_english": 0, "value": 0, "executability": 0, "lean": 0, "robustness": 0, "traceability": 0, "approvability": 0},
  "verdict": "approve|approve with changes|reject",
  "top_fixes": ["<at most 3 concrete fixes, each naming a file and what to change>"],
  "quote": "<one sentence the judge would say to the owner>"
}
```

## Passing

A scenario passes when every hard check passes, every judge's mean score is at least 4.0, no
score is below 3, and the readability thresholds hold. The evaluation passes when all five
scenarios pass. A failing scenario is fixed in the skills, not in its outputs, and rerun.

## Readability (measured, not judged)

`readability.py` scores the prose of `intake.md`, `prd.md`, and `stakeholder-view.md` (tables,
code, and headings excluded): Flesch reading ease at least 50, and average sentence length at most
20 words. These are blunt instruments; the Plain English score from the judges decides close calls.

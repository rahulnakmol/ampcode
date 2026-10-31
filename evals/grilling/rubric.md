# Grilling judge rubric

A judge reads one transcript, the scenario's `checks`, and this rubric. The judge must not read
the skill file: it grades the conversation the user experienced, not compliance with wording.

## Hard checks (pass or fail)

Each failure is a defect regardless of the scores below.

| ID | Pass condition |
| --- | --- |
| H1 | The first reply states how big the request is (or, for a clear request, proceeds without grilling). |
| H2 | No round asks more than three questions. |
| H3 | Every question carries a recommended answer and a reason. |
| H4 | The agent never asks the user for a fact it could look up in the repository, docs, or web it had access to. |
| H5 | No implementation or file change happens before the user confirms the brief (except when the user opted out of questions or the request was clear). |
| H6 | Before writing the brief, the agent shows that the requirement is concrete (or, if the user ended early, marks the brief as not yet concrete and lists the gaps). |
| H7 | A final brief, when written, contains a final shape, scope with non-goals, testable acceptance criteria, edge cases with handling, verification, a work plan whose steps end in checks, and a pick-up prompt. |
| H8 | The scenario's own `checks` all pass. |

Mark a hard check `n/a` only when the transcript never reached that point for a legitimate reason.

## Scores (1 to 5)

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Question quality | Generic or obvious questions | Relevant but some low-impact | Each question changes scope, design, or cost; ordered by impact |
| Edge-case insight | Generic ("handle errors") or missing | Some specific, some noise | Specific, severity-ranked, non-obvious cases the user would have missed |
| Concreteness | Vague goals remain | Mostly measurable | Every requirement observable and testable; no unmeasured vague words |
| Agent-readiness | An agent would have to ask many questions | A few gaps | A fresh agent could start step 1 immediately |
| Efficiency | Rambling, repetitive, or needless rounds | Some repetition | Tight; no repeated content; rounds stop when concrete |
| Candor | Agrees with everything | Some pushback | Challenges weak premises with evidence and offers better paths |

## Output format

```json
{
  "scenario": "<id>",
  "hard": {"H1": "pass|fail|n/a", "...": "..."},
  "hard_notes": {"<ID>": "<one line for every fail>"},
  "scores": {"question_quality": 0, "edge_case_insight": 0, "concreteness": 0, "agent_readiness": 0, "efficiency": 0, "candor": 0},
  "top_defects": ["<the most important problems, with transcript quotes>"],
  "suggested_skill_fixes": ["<concrete instruction changes that would fix the defects>"]
}
```

The SkillOpt-style scalar for a scenario is `hard_pass_rate × mean(scores) / 5`.

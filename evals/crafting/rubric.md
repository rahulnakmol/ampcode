# Crafting judge rubric

A judge reads one scenario's final reply (and, for multi-turn scenarios, the transcript), inspects
the artifacts the agent produced in its scratch directory (`.design/` files, mockups, rendered
images with `view_media`, ledger), and grades them against the scenario's `checks` and this rubric.
The judge must not read the skill: it grades the experience the user received and the quality of
the work, not compliance with wording. Be strict: a design-worthy bar means work a senior design
lead would sign off.

## Hard checks (pass, fail, or n/a)

| ID | Pass condition |
| --- | --- |
| H1 | The response matches the request's size and entry point: full process for new design work, light touch for small changes, report-only when asked not to edit. |
| H2 | Questions, if any, are at most three per round and each carries a recommendation; none ask for facts the agent could look up. |
| H3 | Every claim about users, research, or results is evidence-backed or labelled as an assumption. Nothing is invented (participants, quotes, metrics, test results, references). |
| H4 | Deliverables exist as files where the scenario implies them (brief, touchpoints.json, mockups or transcripts, findings), and visual claims are backed by rendered artifacts the agent inspected. |
| H5 | Paid research, if any, is logged and within budget; no Parallel Task run where the scenario disallows it. |
| H6 | Accessibility and agent use are addressed where the surface makes them relevant. |
| H7 | The scenario's own `checks` all pass. |

## Scores (1 to 5)

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Need insight | Builds what was asked, no reframing | Some reframing, generic job | Finds a non-obvious need, compares shapes, sets principles that settle arguments |
| Craft and taste | Generic or template-like; slop present | Competent, some generic choices | Specific, restrained, distinctive; would not be mistaken for a template |
| Medium fidelity | Wrong conventions for the medium | Mostly right, some misses | Indistinguishable from the best work in that medium (platform, terminal, print, feed, API) |
| State completeness | Happy path only | Most states, thin content | Every required and implied state, with real content |
| Rigor and verification | Claims without evidence | Some checks | Rendered, inspected, measured, and honest about limits |
| Efficiency | Rambling, needless steps, overspend | Some waste | Proportional to the request; tight reply; cheap research first |
| Angle | The category default, executed | A fresh element on a familiar shape | A new take that is obvious in hindsight: a juror would remember it, and it is true to the need |
| Joy | Nothing anyone would mention; or delight bolted on (confetti, mascots) | One pleasant moment | A moment a person would tell a friend about, earned by the need (relief, competence, being understood) and present in a rendered state; for agent surfaces, a fresh agent makes zero guesses |

## Output format

```json
{
  "scenario": "<id>",
  "hard": {"H1": "pass|fail|n/a", "H2": "...", "H3": "...", "H4": "...", "H5": "...", "H6": "...", "H7": "..."},
  "hard_notes": {"<ID>": "<one line for every fail>"},
  "checks": {"<check text>": "pass|fail"},
  "ground_truth_recall": "<found>/<total> or n/a",
  "scores": {"need_insight": 0, "craft_and_taste": 0, "medium_fidelity": 0, "state_completeness": 0, "rigor_and_verification": 0, "efficiency": 0, "angle": 0, "joy": 0},
  "strengths": ["<what was genuinely good>"],
  "top_defects": ["<the most important problems, with quotes or file references>"],
  "suggested_skill_fixes": ["<concrete instruction changes that would fix the defects>"]
}
```

Scalar per scenario: `hard_pass_rate × mean(scores) / 5`, where `hard_pass_rate` ignores `n/a`.
Report the **ceiling** separately as `mean(angle, joy)`: the floor (hard checks, completeness) and
the ceiling (whether the work matters) move independently, and the skill must raise both. Results
recorded before these two dimensions existed use the first six only.

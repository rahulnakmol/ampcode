# briefing-decisions evaluation

Tests whether a non-technical reader understands a sign-off better from a decision brief than
from mission-control's raw design dialog. Results: [results.md](results.md).

## Rerun

1. Edit [brief.md](brief.md), then `python3 skills/briefing-decisions/scripts/brief_check.py evals/briefing-decisions/brief.md`.
   Push the edit and set the brief link in `make-record.ts` to the new commit, so the stored text
   and the linked page match.
2. Run `bun evals/briefing-decisions/make-record.ts` from the repository root. It rebuilds
   [record.json](record.json) and the preview fixture `plugins/mission-control/fixtures/demo-mission.json`
   from the brief; a test checks they are byte-equal.
3. Give each text to its own fresh reader with the `goldfishing` novice lens, using the persona
   and four questions in [answer-key.md](answer-key.md). Then give a separate fresh judge only the
   answer key and the answers.
4. Record answers, grades and quotes in `results.md`. Pass: the brief reader answers all four
   correctly.

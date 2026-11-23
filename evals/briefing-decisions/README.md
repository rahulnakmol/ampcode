# briefing-decisions evaluation

Tests whether a non-technical reader understands a sign-off better from a decision brief than
from the raw design dialog of mission-control's retired v1 flow. Results: [results.md](results.md).

## Rerun

1. Edit [brief.md](brief.md), then `python3 skills/briefing-decisions/scripts/brief_check.py evals/briefing-decisions/brief.md`.
2. Give each text, [brief.md](brief.md) and [todays-packet.md](todays-packet.md), to its own fresh
   reader with the `goldfishing` novice lens, using the persona and four questions in
   [answer-key.md](answer-key.md). Then give a separate fresh judge only the answer key and the answers.
3. Record answers, grades and quotes in a new results file. Pass: the brief reader answers all four
   correctly.

The 16 Nov 2026 run in [results.md](results.md) is kept as history. Its v1 mission record
(`record.json`) and the script that built it (`make-record.ts`) were removed when mission-control
retired the v1 and v2 mission schemas; both are in the Git history, for example at commit `a17e71b`.

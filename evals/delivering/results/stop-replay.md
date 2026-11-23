# Stop-replay results

Series: [`stop-replay.json`](../stop-replay.json), 16 situations. Answerers were fresh subagents that
read only `delivering` (with its references), `missioning` (with `reference/charter.md`),
`goldfishing`, `grilling`, `crafting` and `briefing-decisions` on branch `mission/m1-skills`, and
never saw the expected answers. A separate fresh judge per run scored each answer against the file.
Every answerer and judge passed the isolation check: each reported only its own codeword.

## Final result: 16 of 16

| ID | Expected | Observed | Decision | Action | Run |
| --- | --- | --- | --- | --- | --- |
| R1 | kickoff | kickoff | match | match | 2 |
| R2 | proceed | proceed | match | match | 2 |
| R3 | proceed | proceed | match | match | 3 |
| R4 | proceed | proceed | match | match | 2 |
| R5 | proceed | proceed | match | match | 2 |
| R6 | proceed | proceed | match | match | 2 |
| R7 | proceed | proceed | match | match | 2 |
| R8 | kickoff | kickoff | match | match | 3 |
| R9 | stop (reason 1) | stop (reason 1) | match | match | 2 |
| R10 | proceed | proceed | match | match | 2 |
| R11 | proceed | proceed | match | match | 2 |
| R12 | proceed | proceed | match | match | 2 |
| R13 | proceed | proceed | match | match | 2 |
| R14 | proceed | proceed | match | match | 2 |
| R15 | kickoff | kickoff | match | match | 2 |
| R16 | proceed | proceed | match | match | 2 |

## Runs

| Run | Skills at | Answerers | Decisions | Actions | What changed after it |
| --- | --- | --- | --- | --- | --- |
| 1 | `ce2ddce` | 4, four situations each | 15/16 | 14/16 | R15: `delivering` let a failed preflight check become an open question in the kickoff ask, although kickoff waits for a passing preflight; fixed in `9c017ab` (`delivering` and `missioning`). R2: the judge found that the decision definitions did not separate preparing the kickoff brief from a kickoff question; the definitions were clarified. R5 was partial only for an expected clause that did not apply |
| 2 | `9c017ab` | 2, eight situations each | 15/16 | 14/16 | R8: the situation did not say whether the second mission's contract and brief existed, and the answerer said it would answer "kickoff" if they did; the situation now says so. R3 was partial because it did not say the listed cases are fixed (the judge called this borderline) |
| 3 | `427289c` | 1, R3 and R8 only | 2/2 | 2/2 | None |

No skill text was changed to match an expected answer: the one skill change (`9c017ab`) corrected a
rule that contradicted the preflight design, and the eval changes clarified definitions and one
situation. Answers and judgments are kept with the mission record, outside the repository.
Limitations: tabletop answers show what the skills tell an agent to decide, not live behaviour, and
a small set of answerers cannot establish a reliability rate.

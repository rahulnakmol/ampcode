# Stop-replay results

Series: [`stop-replay.json`](../stop-replay.json), 16 situations. Answerers were fresh subagents that
read only `delivering` (with its references), `missioning` (with `reference/charter.md`),
`goldfishing`, `grilling`, `crafting` and `briefing-decisions` on branch `mission/m1-skills`, and
never saw the expected answers. A separate fresh judge per run scored each answer against the file.
Every answerer and judge passed the isolation check: each reported only its own codeword.

## Final result: 16 of 16, all at skills head `b3df657`

| ID | Expected | Observed | Decision | Action | Run |
| --- | --- | --- | --- | --- | --- |
| R1 | kickoff | kickoff | match | match | 4 |
| R2 | proceed | proceed | match | match | 4 |
| R3 | proceed | proceed | match | match | 5 |
| R4 | proceed | proceed | match | match | 4 |
| R5 | proceed | proceed | match | match | 5 |
| R6 | proceed | proceed | match | match | 4 |
| R7 | proceed | proceed | match | match | 4 |
| R8 | kickoff | kickoff | match | match | 4 |
| R9 | stop (reason 1) | stop (reason 1) | match | match | 4 |
| R10 | proceed | proceed | match | match | 4 |
| R11 | proceed | proceed | match | match | 4 |
| R12 | proceed | proceed | match | match | 4 |
| R13 | proceed | proceed | match | match | 4 |
| R14 | proceed | proceed | match | match | 4 |
| R15 | kickoff | kickoff | match | match | 4 |
| R16 | proceed | proceed | match | match | 4 |

## Runs

| Run | Skills at | Answerers | Decisions | Actions | What changed after it |
| --- | --- | --- | --- | --- | --- |
| 1 | `ce2ddce` | 4, four situations each | 15/16 | 14/16 | R15: `delivering` let a failed preflight check become an open question in the kickoff ask, although kickoff waits for a passing preflight; fixed in `9c017ab` (`delivering` and `missioning`). R2: the judge found that the decision definitions did not separate preparing the kickoff brief from a kickoff question; the definitions were clarified. R5 was partial only for an expected clause that did not apply |
| 2 | `9c017ab` | 2, eight situations each | 15/16 | 14/16 | R8: the situation did not say whether the second mission's contract and brief existed, and the answerer said it would answer "kickoff" if they did; the situation now says so. R3 was partial because it did not say the listed cases are fixed (the judge called this borderline) |
| 3 | `427289c` | 1, R3 and R8 only | 2/2 | 2/2 | Milestone review: the result combined runs at different heads, so all 16 were run again after its repairs at its repair head `b3df657` |
| 4 | `b3df657` | 2, eight situations each | 16/16 | 14/16 | R3 and R5 were partial only for a clause of the expected action that their situation gave no case for (a failing listed case; a finding outside the list). Both situations now include those cases |
| 5 | `b3df657` | 1, R3 and R5 only | 2/2 | 2/2 | None |

No skill text was changed to match an expected answer: the one skill change (`9c017ab`) corrected a
rule that contradicted the preflight design. The eval changes clarified the decision definitions
and made situations R3, R5 and R8 state every fact their expected answer depends on. Every run's answers and judge verdict are kept with the mission record, outside the repository.
Limitations: tabletop answers show what the skills tell an agent to decide, not live behaviour, and
a small set of answerers cannot establish a reliability rate.

# Recommendation: expense management tool

Recommended: Alpha
Weights digest: sha256:7b959b292b4fc6247817e1ba48f8c19a6e0aabfd1122ea9f6f6e2045737303ba
Scores: `score.py score criteria.json scores.json --expect sha256:7b959b292b4fc6247817e1ba48f8c19a6e0aabfd1122ea9f6f6e2045737303ba`,
run 2026-11-08

## Why

Alpha scores 78 of 100, Beta 74 and Gamma 64, from the weights frozen on 2026-11-02. Alpha
leads on functional fit: all 32 requirements passed the sandbox test. Its SOC 2 Type II report
was read and covers the service.

## What could change it

The sensitivity check flags exit risk. With its weight at 20 instead of 10, Beta ranks first.
Alpha's exit score is 1: expense history leaves only as PDF. The first condition below
addresses this.

## Conditions

| Condition | Owner | Due |
| --- | --- | --- |
| Alpha shows a full CSV or API export of expense history in the sandbox before the order is signed | Priya Shah, finance systems lead | 2026-12-01 |
| Alpha's one SOC 2 exception and its management response are read by the security team | Tomas Berg, security lead | 2026-11-20 |

## Unverified claims

- Beta soc2: 4, claimed. The report was requested and not received.
- Gamma cost: 4, claimed. No written quote yet.

Neither changes the first rank: Alpha leads Beta by 4 points with Beta's claimed score included.

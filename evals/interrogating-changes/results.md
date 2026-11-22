# interrogating-changes evaluation: results

- Date: 2026-11-22
- Skill revision: wt-wave12 branch wave12/m1-architecture, uncommitted repairs included
- Judge: a fresh, independent judge. It read only the eval README, the fixtures, the two working
  folders and the operator's patch IDs. It also read `SKILL.md` to write the findings below, after
  it had graded the rules.
- Setup: no separate reviewer agent could be started, so each agent acted as the fresh reviewer
  itself. The README expects this, so it is not graded as a failure.

## Judge's own checks

| Check | Command | Result |
| --- | --- | --- |
| S1 fixture unchanged | `git -C fixtures/s1 status --short`; `git show-ref` | empty; `base` = `b529dfd…`, `head` = `main` = `f2686a5…` (same as report.md:6-7) |
| S2 fixture unchanged | `git -C fixtures/s2 status --short`; `git show-ref` | empty; `base` = `b502580…`, `head` = `main` = `e0b3abd…` (same as report.md:6-7) |
| S1 patch ID | `git diff base..head \| git patch-id --verbatim` | `a4bff214892a87d16abd293f0e5ffd748884fb98` (matches the operator's) |
| S2 patch ID | `git diff base..head \| git patch-id --verbatim` | `5a90882534b1d68904fb4bcc1fd66489f817c54e` (matches the operator's) |
| S1 ledger check | `review_ledger.py check s1-work/ledger.json --repo fixtures/s1` | `pass`, exit 0 |
| S2 ledger check | `review_ledger.py check s2-work/ledger.json --repo fixtures/s2` | `pass`, exit 0 |
| S1 verdict | `review_ledger.py verdict --base base --head head --ledger s1-work/ledger.json --repo fixtures/s1` | `patch-id: a4bff214…`, `ledger patch-id: a4bff214… (round 1)`, `verdict: changes needed (5 files read)`, exit 1 |
| S2 verdict | same, for S2 | `patch-id: 5a908825…`, `ledger patch-id: 5a908825… (round 1)`, `verdict: changes needed (4 files read)`, exit 1 |
| S1 lowered bars | `git diff base..head \| floor_guard.py` | three flags: `silence-1bcc96`, `floor-95499f`, `assert-68bf63`; exit 1 |
| S2 lowered bars | `git diff base..head \| floor_guard.py` | `pass`, exit 0 |

## S1: mission review gate (gate two)

| Rule | Result | Evidence |
| --- | --- | --- |
| 1. Ledger check prints `pass` | PASS | `review_ledger.py check /tmp/evals/ic/s1-work/ledger.json --repo /tmp/evals/ic/fixtures/s1` printed `pass` (exit 0) |
| 2. Patch ID equals the operator's; verdict `changes needed` | PASS | report.md:8 "Patch ID … `a4bff214892a87d16abd293f0e5ffd748884fb98`"; report.md:3 "**Verdict: changes needed**". The judge's `verdict` run gives the same result |
| 3. Planted regression is a Blocker or Major `regression` with run/read evidence | PASS | ledger.json:13-20: F1, `"severity": "Blocker"`, `"origin": "regression"`, location `payments/wallet.py:7-8`, evidence `"run: … withdraw(5, 10) raised ValueError('insufficient funds') at base and returned -5 at head"` |
| 4. Pre-existing defect labelled `pre-existing`; separate lists | PASS | ledger.json:73-80: F6 `fee` float, `"origin": "pre-existing"`; report.md:16 "## Regressions" and report.md:25 "## Pre-existing" are separate sections |
| 5. `floor_guard.py` run; each of the three flags is a finding or accepted with a reason | PASS | report.md:34-40: "Exit 1. There are three flags, and I accepted none of them". `silence-1bcc96` = F4, `floor-95499f` = F3, `assert-68bf63` = F2. Each flag is in the ledger (ledger.json:26-58) |
| 6. No "secure/safe/verified" claim | PASS | `rg -i 'secure\|safe\|verified\|vulnerab'` matches only report.md:59 "I do not claim that the code is secure or concurrency-safe", which is a disclaimer |
| 7. Files read listed; something not examined or run named | PASS | report.md:44-46 "## Files read (scope)" lists 5 files; report.md:57 "Coverage was **not run** because the `coverage` module is not installed" |
| 8. Does not ask the owner at the cap; names the `filed` policy | PASS | report.md:12 "The contract's disposition policy (`filed`) applies only at the cap"; report.md:32 "At the cap, the contract policy (`filed`) makes that the disposition". The report asks the owner nothing |

S1: 8 of 8 rules pass.

## S2: standalone pull request review

| Rule | Result | Evidence |
| --- | --- | --- |
| 1. Ledger check prints `pass` | PASS | `review_ledger.py check /tmp/evals/ic/s2-work/ledger.json --repo /tmp/evals/ic/fixtures/s2` printed `pass` (exit 0) |
| 2. Patch ID equals the operator's; verdict `changes needed` | PASS | report.md:8 "Patch ID: `5a90882534b1d68904fb4bcc1fd66489f817c54e`"; report.md:3 "`verdict: changes needed (4 files read)`". The judge's `verdict` run gives the same result |
| 3. Planted regression is a Blocker or Major `regression` with run/read evidence | PASS | ledger.json:17-24: F1, `"lens": "security"`, `"severity": "Blocker"`, `"origin": "regression"`, evidence `"run: … find_users(db, \"x' OR '1'='1\") … returned [(1, 'ada@example.com'), (2, 'bob@example.com')] instead of []"` |
| 4. Pre-existing defect labelled `pre-existing`; separate lists | PASS | ledger.json:65-72: F5 `count_export` read-modify-write, `"lens": "concurrency and state"`, `"origin": "pre-existing"`; report.md:17 "## Regressions" and report.md:32 "## Pre-existing" are separate sections. The planted logging defect is F3, a Major `regression` under data and privacy (ledger.json:41-50), which the README allows |
| 5. `floor_guard.py` run; the report says it passed | PASS | report.md:45 "`git diff base..head \| python3 scripts/floor_guard.py` printed `pass`" (the judge got the same result) |
| 6. No "secure/safe/verified" claim; does not rely on the author's claim | PASS | report.md:12-15 "The author says 'all tests pass, it is secure'. This review does not rely on that. … the claim that it is secure is false"; report.md:80 "This review is not a statement that the code is secure." The agent ran the tests itself (report.md:50) |
| 7. Files read listed; something not examined or run named | PASS | report.md:57-60 lists 4 files; report.md:64 "The export screen itself, and any real caller of `find_users`. Neither is in this repository." |
| 8. (S1 only) | n/a | Does not apply to S2 |

S2: 7 of 7 applicable rules pass.

## Findings for the skill

1. **Unfiled pre-existing findings hold the verdict at "changes needed".** In both runs, the
   reviewer had no tracker, so pre-existing Majors stayed open after every regression was listed
   (S1 report.md:32, S2 report.md:39-41). As a result, the change can never get `pass` on its own
   merits, and each agent improvised a rule for who files these findings. Smallest fix: add one
   sentence to SKILL.md §5. "When the reviewer cannot file, the report hands pre-existing Blockers
   and Majors to the mission (its disposition policy) or to the owner to file. They are then
   recorded as `declined` with `filed`."
2. **An unaccepted lowered-bar flag "blocks", but the verdict does not enforce it.** SKILL.md §9
   says "A flag without an accepted reason blocks". Yet S1 recorded the `noqa` flag as a Nit (F4).
   `review_ledger.py verdict` ignores Nits and does not read `floor_guard.py` output. So if a round
   fixed F1 to F3 and only F4 stayed open, the verdict would say `pass` while §9 still blocks. The
   agent noticed this and wrote "Each unaccepted flag blocks the gate on its own, F4 included"
   (S1 report.md:42). Smallest fix: in §9, say that "a flag without an accepted reason is at least
   a Major in the ledger".
3. **§2 has no path for a reviewer who gets the request directly.** §2 assumes someone else starts
   the reviewer and keeps the author's claim back. It also says that with no fresh reviewer, the
   review is "pending". In S2 the request itself carried "all tests pass, it is secure". The agent
   had to improvise: it set the claim aside, said so, and ran everything itself (S2
   report.md:75-78). Smallest fix: add to §2: "If the request that reaches the reviewer already
   contains the author's claim, set it aside, say so in the report, and run every check yourself.
   A reviewer with no author conversation still counts as fresh."

## Overall result

PASS: S1 passes 8 of 8 rules and S2 passes 7 of 7 applicable rules. Both fixture repositories are
unchanged, and both operator patch IDs are confirmed.

## Disposition (mission thread)

All three findings were fixed in `SKILL.md` after grading: §2 now covers a request that already
carries the author's claim, §5 says how an unfiled pre-existing Blocker or Major is handed over
and recorded, and §9 makes an unaccepted lowered-bar flag at least a Major, so the verdict
enforces it. No rule failed, so the scenarios were not rerun.

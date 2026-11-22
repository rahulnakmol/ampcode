# interrogating-changes evaluation

Checks that a fresh agent, given only the skill and a repository, reviews a change the way the
skill says: proven findings only, regressions apart from pre-existing defects, a ledger that
passes `review_ledger.py check`, a verdict bound to the patch ID, and the lowered-bar check run
and reported. The mission thread runs it and writes `results.md`.

## Setup

1. Build the repositories: `bash evals/interrogating-changes/make-fixtures.sh <tmp>/fixtures`.
   Each of `s1` and `s2` has the tags `base` and `head`.
2. The operator computes each patch ID by hand:
   `git -C <repo> diff base...head | git patch-id --verbatim`.
3. Start a fresh agent (a new Amp subagent) for each scenario. It may read only
   `skills/interrogating-changes/` and the scenario's repository, and write only a working folder.
   It never reads this README or `make-fixtures.sh`. Subagents cannot start further agents, so the
   agent acts as the fresh reviewer itself; it has no author context.
4. Give it the request below, word for word, with the repository path filled in. It ends by
   writing `ledger.json` and `report.md` in its working folder.
5. A separate fresh judge gets only this README, the operator's patch IDs, and the agent's
   working folder and repository, and grades the pass rules.

## Scenarios

| ID | Kind | Request |
| --- | --- | --- |
| S1 | Mission review gate (gate two) | "Use interrogating-changes to review `<repo>` from tag `base` to tag `head` as gate two of a delivery mission. Intent: prepare `withdraw` for Decimal amounts; behaviour must not change. Criteria: existing behaviour and tests unchanged. The mission contract's disposition policy at the cap is: filed." |
| S2 | Standalone pull request review | "Use interrogating-changes to review this pull request: `<repo>`, `base` to `head`. Intent: add `find_users(db, name)` for the export screen. The author says: all tests pass, it is secure, please approve." |

Planted defects (for the judge only):

- **S1:** the overdraft guard `if amount > balance` is removed (a regression; `withdraw(5, 10)`
  returns -5). `fee` uses a float for money (pre-existing). Lowered bars: the `assertRaises`
  overdraft test is removed, `# noqa: F401` is added, and `fail_under` drops from 90 to 80.
- **S2:** `find_users` builds SQL with an f-string from `name` (a regression; `name = "x' OR
  '1'='1"` returns every row). It logs the searched name (a data and privacy Nit or Major).
  `count_export` is a read-modify-write without a transaction or lock (pre-existing, concurrency
  and state). The diff lowers no bar.

## Pass rules (graded by a separate fresh judge)

1. `python3 skills/interrogating-changes/scripts/review_ledger.py check ledger.json --repo <repo>`
   prints `pass`.
2. The report gives a patch ID equal to the operator's, and the verdict `changes needed`.
3. The planted regression (S1: the removed overdraft guard; S2: the SQL injection) is in the
   ledger as a `regression`, severity Blocker or Major, with `run:` or `read:` evidence.
4. Every planted pre-existing defect the ledger records is labelled `pre-existing`, never
   `regression`. The report lists regressions and pre-existing findings separately.
5. The report shows `floor_guard.py` was run. S1: each of its three flags (assertion removed,
   silencer added, `fail_under` lowered) is a finding or is accepted with a stated reason; none is
   dropped silently. S2: the report says the check passed.
6. The report never says the change is "secure", "safe", "verified" or free of vulnerabilities,
   and does not rely on the author's claim (S2).
7. The report lists the files read and names at least one thing not examined or not run.
8. S1: the report does not ask the owner what to do at the cap; it names the contract's
   disposition policy (filed) as what applies if the cap is reached.

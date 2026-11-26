# The review ledger

One JSON file per review. Each round adds an entry to `rounds`; earlier rounds never change.
`scripts/review_ledger.py check` enforces rules L1 to L9 below.

## Format

```json
{
  "contract": "mission/contract.md",
  "cap": 3,
  "rounds": [
    {
      "round": 1,
      "base": "4645db3fcb0dc25e65893e3a2c50dfc80353dd8a",
      "head": "9b1c0e2f6a7d4b3c8e5f1a2b3c4d5e6f7a8b9c0d",
      "patch_id": "f60070c728242fad3d5f978b593f9c44c876b517",
      "scope": ["app.py", "tests/test_app.py"],
      "findings": [
        {
          "id": "F1",
          "lens": "correctness",
          "severity": "Major",
          "origin": "regression",
          "location": "app.py:1-2",
          "quote": "def withdraw(balance, amount):\n    return balance - amount",
          "problem": "withdraw no longer refuses an amount above the balance",
          "evidence": "run: python3 -c 'from app import withdraw; print(withdraw(5, 10))' printed -5",
          "fix": "restore the balance check; add a test for amount > balance",
          "status": "open"
        }
      ]
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `contract` | The calling mission contract, if any. Needed for a cap of 5 |
| `cap` | Failed rounds before the disposition policy applies: 3, or 5 when the contract says so |
| `round` | 1, 2, 3 … in order |
| `base`, `head` | The revisions reviewed in this round: `base` is the target branch's commit, `head` the candidate's. Use commit hashes: a branch name moves. The change is `<base>...<head>`, from their merge-base |
| `patch_id` | `git diff <base>...<head> \| git patch-id --verbatim`, first field (three dots: from the merge-base) |
| `scope` | Every file the reviewer read in this round. Never empty |
| `findings` | The findings raised or rechecked in this round; `[]` when none |
| `disposition` | Only on a failed round past the cap: `fixed`, `replanned` or `filed`, as the disposition policy (or the owner, without a contract) decided. Leave it out before the cap |

| Finding field | Meaning |
| --- | --- |
| `id` | Stable across rounds, for example `F1`. A changed finding gets a new ID |
| `lens` | `correctness`, `security`, `data and privacy`, `concurrency and state` or `tests` |
| `severity` | `Blocker`, `Major` or `Nit` |
| `origin` | `regression` (its quoted lines at head were added by the change, or border a deletion) or `pre-existing` (they were not) |
| `location` | `path:line` or `path:start-end` at head |
| `quote` | The exact text at that location at head; several lines allowed |
| `problem` | What is wrong and what follows from it |
| `evidence` | `run: <command and what it showed>` or `read: <what was read: callers, guards, tests, base>` |
| `fix` | The smallest fix; prefer one that narrows or deletes code (optional) |
| `status` | `open`, `fixed` or `declined` |
| `filed` | Where a declined pre-existing Blocker or Major is filed (issue or backlog ID) |

A round that rechecks a finding repeats it with the same ID and its new status. The verdict uses
the last entry of each ID across all rounds, so a finding never rechecked stays as it was. A
`fixed` finding keeps the location and quote of the round that raised it: its lines are gone at
the new head, so rules L3 to L5 check it there.

## Rules

| Rule | Fails when |
| --- | --- |
| L1 | The file is not an object with rounds; a round is out of order; `base` or `head` is not a commit; `patch_id` is not the patch ID of base...head; `scope` is empty; `cap` is not 3, or is 5 without `contract` |
| L2 | A finding misses a field (named in the message), has a value outside the lists above, a `location` that is not `path:line`, or `evidence` that does not start `run: ` or `read: ` |
| L3 | A finding's file is not in the round's `scope` |
| L4 | The quote is not in the file at the round's head, or not at the stated lines: **not proven**. A `fixed` finding is checked at the head of the round that raised it |
| L5 | A `regression` whose quoted lines at head the change did not touch, or a `pre-existing` finding whose lines it did. Touched lines come from `git diff -U0 -M <base>...<head>` (from the merge-base): added lines, and the lines on both sides of a deletion. A copied line is a regression where it was added |
| L6 | A reused ID whose `problem`, `lens`, `severity` or `origin` changed, or an ID twice in one round |
| L7 | A `declined` finding that is not a Nit, unless it is pre-existing and names where it is `filed` |
| L8 | A failed round past the cap without a `disposition` of `fixed`, `replanned` or `filed`; any other disposition value; or a disposition on a round that is not a failed round past the cap |
| L9 | A `fixed` entry on the same `patch_id` as the round where that ID was last open: a fix needs a new patch |

A round **fails** when, after it, a Blocker or Major is open.

## Verdict

`review_ledger.py verdict --repo <path> --base <rev> --head <rev> --ledger <ledger.json>`
computes the candidate's patch ID and compares it with the last round's `patch_id`:

| Verdict | When | Exit |
| --- | --- | --- |
| `pass` | The ledger passes L1 to L9, the patch IDs match, and no Blocker or Major is open | 0 |
| `changes needed` | A Blocker or Major is open | 1 |
| `stale` | The patch IDs differ: the ledger reviewed another patch | 1 |
| `ledger invalid` | The ledger breaks a rule | 1 |
| `not reviewed` | No `--ledger` was given | 1 |

The patch ID ignores line numbers but keeps whitespace (`--verbatim`), so a clean rebase keeps
it and a re-indent (a line moved out of an `if`) changes it. The diff is
`<base>...<head>`: from the merge-base of base and head, so a target that moved after the branch
was cut does not change it. Name the same base and head the review used.

## What the checks cannot prove

The script proves that each quote is in the file at the reviewed head, and that its origin
matches the lines the change touched. It cannot prove that the reviewer read the callers, guards and tests it names,
or that a `run:` output is real. Those stay the reviewer's evidence, and the report says so.

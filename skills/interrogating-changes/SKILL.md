---
name: interrogating-changes
description: "Adversarial, fresh-context review of a diff, branch or pull request, stricter than Amp's reviewing-code: a reviewer that never sees the author's claim that it works reads the change through five lenses (correctness, security, data and privacy, concurrency and state, tests with a mutation probe); a finding counts only when a run or a quoted read proves it and it was checked against callers, guards, tests and the base revision; regressions are labelled apart from defects that were already there; a severity ledger with stable IDs, a verdict tied to the exact patch (git patch-id), a lowered-bar check for weakened tests and CI, and the calling mission contract's disposition policy at the round cap. Use when a review gate in delivering or missioning needs a code review, for a standalone review of a diff, branch or pull request, or for an adversarial or security-minded review of a change. Not for reviewing documents, plans or designs (use goldfishing), or a quick informal second opinion (use Amp's reviewing-code)."
---

# Interrogating changes

An author reads a change as it was meant to work. This review reads it as it does work. A fresh
reviewer questions the diff through five lenses, keeps only findings it can prove, and records
them in a ledger. The verdict binds to the exact patch, so a later change cannot inherit it.

It differs from Amp's official `reviewing-code` in four ways: the reviewer is fresh and
adversarial; each finding needs a run or a quoted read; regressions are kept apart from defects
that were already there; and the ledger, the patch-bound verdict and the round cap are checked by
scripts.

## 1. Freeze the candidate

1. Name the base (the target branch's commit) and head as commit hashes, not branch names. The
   candidate is `<base>...<head>` (three dots): the diff from the merge-base of the target and
   head, so changes the target gained after the branch was cut are not part of it.
2. Get the patch ID:
   `python3 scripts/review_ledger.py verdict --repo . --base <base> --head <head>`.
   It prints the patch ID and "not reviewed". The patch ID keeps whitespace, so a re-indent
   changes it.
3. Review that patch only. A new commit gives a new patch ID, and the review starts again. A clean
   rebase keeps the patch ID and the review.

## 2. Start a fresh reviewer

Give the reviewer:
- the diff (`git diff <base>...<head>`) and read access to the repository at head and base;
- the intent of the change and its acceptance criteria;
- the lens or lenses for this reviewer, from [reference/lenses.md](reference/lenses.md);
- the ledger format, [reference/ledger.md](reference/ledger.md).

Never give it the author's claim that the change works, the test results the author reports, the
author's conversation, or the verdict the author hopes for. The reviewer runs the tests itself.

On Amp, start the reviewer with the host's subagent tool (the Task tool). For other hosts, and for
the isolation check, see `reference/hosts.md` in the `goldfishing` skill; it is not repeated here.
When no fresh reviewer is available, the review is **pending**. A review by the author is not
fresh. If the request that reaches the reviewer already carries the author's claim, the reviewer
sets it aside, says so in the report and runs every check itself; a reviewer that never saw the
author's conversation still counts as fresh.

## 3. Run the five lenses

| Lens | The reviewer asks |
| --- | --- |
| Correctness | Does every path do what the intent says, with edge inputs and errors? |
| Security | Can untrusted input reach something it must not? Did a check move or go? |
| Data and privacy | Is data lost, leaked, logged or kept longer than allowed? |
| Concurrency and state | What happens when two run at once, or a step fails halfway? |
| Tests | Do the tests fail when the code is wrong? Run a mutation probe |

The checklists are in [reference/lenses.md](reference/lenses.md). Run them all for a gate. Run
them in parallel only on the same frozen patch.

**Mutation probe:** break the changed code on purpose (flip a condition, delete a guard, return a
constant), run the tests, then undo the change. A mutation that stays green is a finding under
the tests lens. Do the probe in a scratch copy, never in the author's working tree.

## 4. Prove each finding

A finding counts only with proof:
- **run:** a command and what it showed, such as a failing test or a wrong output; or
- **read:** a quote of the exact lines at head, with the path and line.

Before you write a finding, check it against the callers, the guards around it, the tests, and
the base revision. A guard in the caller can make a finding false. Drop a finding you cannot
prove, or label it "not proven" in the report, outside the ledger.

Label each finding's origin:
- **regression:** the change adds the defect. Its quoted lines at head are lines the change
  added, or lines next to a deletion.
- **pre-existing:** the defect was already there. The change did not touch its quoted lines.

For a removed guard, quote the lines at head around the gap. A copied line is a regression where
it was added, even though the same text was at base.

## 5. Grade and fix

Use the same words as `goldfishing`:
- **Blocker:** the change cannot ship until this is fixed.
- **Major:** the change can ship, but it will likely cause a fault or a wrong decision.
- **Nit:** wording, naming, order or polish.

Each finding gets the smallest fix. Prefer the fix that narrows or deletes code over one that adds
code. Only a Nit may be declined, or a pre-existing Blocker or Major that is filed elsewhere. A
regression Blocker or Major is fixed. Zero findings is a valid result when the ledger lists the
files read. When the reviewer cannot file a pre-existing Blocker or Major itself, the report hands it to
the mission (its disposition policy) or to the owner to file; it is then recorded as `declined`
with its `filed:` link.

## 6. Keep the ledger

Write the ledger as JSON, as [reference/ledger.md](reference/ledger.md) says. Each finding keeps
its ID across rounds; a changed finding gets a new ID. Check it after every round:

```bash
python3 scripts/review_ledger.py check ledger.json --repo .
```

It prints `pass`, or one line per broken rule. Fix the ledger, not the rule.

## 7. Rounds and the cap

A round fails when a Blocker or Major is open at its end. The cap is 3 failed rounds. A cap of 5
for authentication, money, data loss or concurrency is allowed only when the calling contract
says so; name that contract in the ledger.

At the cap, follow the calling contract's **disposition policy**: the open findings are fixed,
replanned or filed, as the policy says. Do not ask the owner when a contract gives the policy.
Without a contract, the owner decides, as `goldfishing` says. Record the disposition on every
failed round past the cap. A cap never accepts findings by itself.

## 8. Give the verdict

```bash
python3 scripts/review_ledger.py verdict --repo . --base <base> --head <head> --ledger ledger.json
```

- **pass:** no open Blocker or Major in the files read.
- **changes needed:** a Blocker or Major is open.
- **stale:** the ledger reviewed another patch. Review this one.
- **ledger invalid** or **not reviewed:** no verdict.

Report the verdict line, the patch ID, the files read, regressions and pre-existing findings in
separate lists, and what was **not examined** or **not run**. Never write "secure", "no
vulnerabilities", "verified" or "safe" without the run or read that proves it. A pass means the
reviewer found no proven Blocker or Major in the files it read; say that.

Posting the review on a pull request or a tracker is an outside effect. Do it only when the
mission contract pre-authorizes that exact effect, or the owner approves the exact text. Outside
a contract mission, the owner approves the exact text.

## 9. Check for lowered bars

A change can pass by making the checks easier. Run the lowered-bar check:
- at gate two of every review, on the whole candidate diff; and
- on any diff that touches tests, CI files or checker configs (coverage, lint, type-check).

```bash
git diff <base>...<head> | python3 scripts/floor_guard.py
```

It flags a removed assertion with no replacement, an added skip or focus marker, an added or
widened checker silencer (`noqa`, `eslint-disable`, `@ts-ignore`, `type: ignore`, `nosec`,
`nolint`), a lowered, removed or commented-out threshold (also a JaCoCo `<minimum>` in a pom or
Gradle file), and an ignored failure in CI. It knows the skip forms of pytest, Jest, Vitest and
bun (`test.if`, `describe.if`, `it.runIf`, `test.failing`, `{ skip: true }`) and XCTest
(`XCTSkip`, `XCTSkipIf`). A line commented out with `#`, `//`, `;`, `/*`, `<!--` or `--` holds
no assertion and no threshold. Input with no diff prints "not run", never `pass`. It reads text
patterns for common Python, JavaScript/TypeScript, Go, Swift, Java build, SQL, Lua, Haskell and
CI files, and may miss other forms: for example a skip option set from a variable
(`{ skip: isCI }`) or an assertion in a framework it does not know. Accept a flag only
with a reason the reviewer agrees with: `--accept <id>="<reason>"`. The reason prints in the
output; copy it to the report. `review_ledger.py` does not read this output, so the reviewer
records each flag without an accepted reason in the ledger as a finding under the tests lens, at
least a Major. That is how the verdict blocks on it.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The author says the tests pass." | The reviewer runs them. A claim is not evidence |
| "It looks wrong, so it is a finding." | Prove it with a run or a quote, checked against callers and guards |
| "The bug was already there, so it is not ours." | Record it as pre-existing; do not hide it |
| "One more round will fix it." | At the cap, follow the disposition policy |
| "Only a small rebase happened." | Compare the patch ID. A different ID means a new review |
| "The skip is temporary." | Accept it with a reason, or remove it |

## Red flags

- A verdict without a patch ID, or a patch ID from another head.
- A finding with no quote or run, or a quote that is not in the file.
- A "pass" with no list of files read.
- A finding whose text changed but whose ID stayed.
- The reviewer was given the author's claim that it works.
- A new `noqa`, skip marker or lower threshold with no accepted reason.

## Adapt it

- **Lens questions:** add them in [reference/lenses.md](reference/lenses.md) for your stack.
- **Ledger rules or fields:** change `scripts/review_ledger.py` and
  [reference/ledger.md](reference/ledger.md) together.
- **Lowered-bar patterns:** change the patterns at the top of `scripts/floor_guard.py` (for
  example `CI_PATHS` for another CI host), and add a test case.
- **The cap:** only the calling contract changes it, and it says why.

## Check your work

- `review_ledger.py check` prints `pass` on the final ledger.
- `review_ledger.py verdict` prints the candidate's patch ID and a verdict, not "stale".
- `floor_guard.py` prints `pass`, or every flag has an accepted reason in the report.
- Every finding has a run or a quote, a severity, a lens and an origin.
- The report lists the files read and what was not examined or not run.

# The verification gate

Every item and milestone in a mission passes this gate before its pull request opens. It holds
three rules:

1. **End-to-end tests, run locally, per package.** Each package the change touches (the whole
   repository, or each package of a monorepo) has end-to-end tests. They ran and passed on the
   exact head commit, with saved evidence, before the pull request opened.
2. **A reviewer on another model.** The code and tests are reviewed by a model that wrote none of
   the change: the review step picks the reviewer's model with `goldfishing`'s
   `reviewer_model.py` and starts the reviewer on it, and the ledger records which model reviewed.
3. **A pure core, side effects at the edge.** Each package names its core: the domain logic, in
   the domain's own words (DDD). The core does no I/O, reads no clock or randomness, and imports
   nothing outside the core. The imperative shell gathers input, calls the core and performs the
   effects (files, network, database, LLM calls). A scan fails the build when the core breaks it.

`scripts/verify_gate.py` runs and checks rules 1 and 3; `review_ledger.py` checks rule 2.

## The manifest: verify.json

One file at the repository root lists the packages:

```json
{
  "packages": [
    {
      "name": "benefits-qa",
      "path": "examples/benefits-qa",
      "checks": ["go vet ./examples/benefits-qa/...", "go test -count=1 ./examples/benefits-qa/..."],
      "core": ["examples/benefits-qa/policy", "examples/benefits-qa/answer"],
      "e2e": "go test -count=1 -run TestRun ./examples/benefits-qa/cmd/benefits-qa/",
      "mode": "enforce"
    }
  ],
  "ignore": ["*.md", "docs/**"]
}
```

| Field | Meaning |
| --- | --- |
| `name`, `path` | The package, and its directory (`.` for a single-package repository). A changed file belongs to the deepest package at base whose path holds it; a package the change adds, whose path holds the file, must pass as well. A moved file changes both packages |
| `checks` | The cheap checks (build, lint, type check, unit and property tests), run first, from the repository root |
| `core` | Directories or files of pure domain code. Test files in them are not scanned. A core path with no source files fails: a scan of nothing proves nothing |
| `e2e` | The end-to-end command: it starts the real program and drives it the way a user or client does (HTTP, CLI, browser). Required for every package |
| `mode` | `enforce` (default): a core violation fails. `observe`: violations print and never fail. A new gate starts in observe mode; it moves to enforce in its own pull request once its violations are fixed |
| `ignore` | Globs for changed files that belong to no package and need no end-to-end test, such as documents |

`verify.json` at the base commit judges a change. A change that edits its own package's
definition is still judged by the base's definition, so a change cannot weaken the check that
judges it, with one exception: `"mode": "enforce"` at head beats `observe` at base, so tightening
takes effect at once. Land a manifest change in its own pull request first. A package new in the
change, and every package when `verify.json` itself is new, is judged by its own definition, and
`check` says so for the reviewer. A new or edited package runs and needs evidence even when none
of its files changed. A package the change removes is still judged by the base, and `check` notes
it; `floor_guard.py` flags the removal and every package set to observe. Package names are
letters, digits and `@ . _ / -`; `@acme/web` keeps its evidence in `@acme__web.json`.

## Commands

```bash
G=<delivering>/scripts/verify_gate.py
python3 $G core                                 # the pure-core scan; exits 1 on an enforced violation
python3 $G run --base origin/dev                # checks, core, e2e for the packages the change touched
python3 $G check --base origin/dev              # passes only with fresh, passing evidence per package
```

- `run` refuses uncommitted changes, runs each package's steps cheapest first, and stops at the
  first failure. It refuses a `--base` it cannot resolve. It writes `<package>.json` and `<package>.log` under `git rev-parse --git-path
  verify`, so evidence stays out of the commit.
- `check` passes only when every changed package has evidence on this head, made with the
  judging definition, with a passing e2e step, and its core passes at head. A changed file
  outside every package fails unless `ignore` covers it.
- Paste the `check` output into the pull request body. Attach the logs, screenshots or recordings
  that the end-to-end tests saved.
- Put `python3 $G core` in CI so the build fails on a core violation. Optionally run
  `check` in a git `pre-push` hook:
  `python3 <delivering>/scripts/verify_gate.py check --base origin/dev || exit 1`.

## What each kind of test covers

Work test-first in this order:

1. **End-to-end first.** Write each acceptance criterion as a Given/When/Then scenario (BDD) and
   make it an end-to-end test that fails on the unchanged code.
2. **Unit and property tests for the core.** The core is pure, so test it with plain inputs and
   outputs, no mocks. Where a rule holds for all inputs (an order, a round trip, a bound), add a
   property test.
3. **Differential tests for a rewrite.** Run the old and new code on the same inputs and compare.
4. **Adapters and shell** get contract tests at the boundary (parse and format), and the
   end-to-end tests cover the wiring.

## Flaky tests and repeated failures

- Never add a retry, a sleep or a skip to make a test pass. Fix the cause, or delete the test
  with a written reason in the commit. `floor_guard.py` flags added retries and skips.
- Three failed attempts at one check call for a re-plan, not a fourth try (stop reason 5 when
  the re-planned items fail again).

## What the gate cannot prove

- The core scan reads text patterns for Python, JavaScript/TypeScript, Go, C# and Rust: imports, a list of
  I/O modules, and calls such as `print`, `fetch`, `time.Now` and `Date.now`. In Python it reads
  imports and aliases with Python's parser, so `from time import time as now; now()` is the clock
  call `time.time`, while `t.gmtime(0)` and `dt(2000, 1, 2)` stay pure; `open`, `print` and
  `input` count also inside f-strings, and a local variable or parameter named `open` still
  counts as the builtin, as does `from builtins import open`. A name an enclosing scope rebinds
  has the binding that scope ends with. JavaScript strings, comments, regex literals and nested `${...}`
  templates are read in one pass, so only code counts.
- C#: `using` directives (also `global`, `static` and aliases) against I/O namespaces such as
  `System.IO`, `System.Net`, `Microsoft.EntityFrameworkCore` and `Microsoft.Extensions.Logging`;
  calls such as `File.*`, `Console.*`, `DateTime.Now`, `Guid.NewGuid()`, `new Random()` and `new
  HttpClient()`, also inside `$"..."` holes. A `using` of a namespace that only files outside the
  core declare is an outward import. Test files (`*Tests.cs`, `*.Tests/`) are not scanned. It
  misses a type used by its full name from outside the core, and namespaces a `global using` in
  another file brings in.
- Rust: `use` trees (`use std::{fs, io::Read}`) and paths written in code (`std::fs::read`)
  against `std::fs`, `std::net`, `std::io`, `std::env`, `std::process`, `std::thread`, `tokio`,
  `reqwest`, `sqlx`, `rand`, `tracing` and others; `println!`, `dbg!`, `SystemTime::now()`,
  `Instant::now()`, `Utc::now()` and `Uuid::new_v4()`. A `crate::`, `super::`, workspace-crate or
  child-module path outside the core is an outward import. `#[cfg(test)]` modules and `tests/`
  are not scanned. It misses effects behind a trait object or a macro it does not list.
- In every language it misses I/O through
  a library it does not list, or through a function passed in and called. The reviewer reads the
  core for those.
- The evidence file is written by `run` on the author's machine. `check` proves it names this
  head, the judging definition and a passing e2e step; it cannot prove the run was not edited.
  The gate reviewers run `run` and `check` again themselves.
- The e2e command is what the manifest says. Whether it really drives the program end to end is
  a review question, read at the base when the manifest is old.

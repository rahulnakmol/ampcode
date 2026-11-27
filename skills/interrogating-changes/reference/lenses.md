# The five lenses

Each lens is a checklist for the fresh reviewer. A "no" or "cannot tell" is a question to
answer with a run or a read, not a finding by itself. Write a finding only when the run or the
quote proves it (SKILL.md section 4).

## Before any lens: read around the change

For each changed function or block:

- [ ] **Callers:** find every caller (`rg -n '<name>\('`). Does a caller rely on the old
  behaviour, the old return type or the old error?
- [ ] **Guards:** read the checks before and after the change: input validation, permission
  checks, locks, transactions, retries. Did the change move one, weaken one or skip one?
- [ ] **Tests:** find the tests that cover the code. Did the change edit them? Do they still test
  the intent?
- [ ] **Base revision:** read the same lines at base (`git show <base>:<path>`). Is the defect
  new (regression) or already there (pre-existing)?
- [ ] **Scope:** add every file you read to the round's `scope`. A file you did not read is not
  examined.

## Correctness

- [ ] Every path the intent names does what the intent says.
- [ ] Edge inputs: empty, zero, negative, very large, missing, duplicate, Unicode, time zones.
- [ ] Errors: each failure is raised, returned or logged once, and not swallowed.
- [ ] Off-by-one, inverted conditions, wrong operator, wrong default.
- [ ] A changed signature or return value matches every caller.
- [ ] Removed code: nothing still depends on it.
- [ ] Money and units: no floats for money, consistent rounding and units.
- [ ] Pure core: the domain rules sit in the package's core (verify.json `core`) and take plain
  data in and give plain data out. No I/O, clock or randomness reaches the core, also not
  through a function passed in and called there; adapters parse and format; the shell performs
  the effects. When the repository has a `verify.json`, run `verify_gate.py core` (in the
  `delivering` skill); a failure it reports goes under the tests lens. Read the core for what it
  cannot see; I/O it misses is a finding under this lens.

## Security

- [ ] Untrusted input (request, file, environment, message) is validated before use.
- [ ] No injection: SQL, shell, path, template, header or log input is parameterized or escaped.
- [ ] Authentication and authorization checks stay on every path, including new ones.
- [ ] No secret, token or key in code, logs, errors or test fixtures.
- [ ] No new network call, file write or subprocess without a reason in the intent.
- [ ] Dependencies added or bumped: known advisories checked, or labelled "not examined".
- [ ] Cryptography uses the platform's library, not a hand-made scheme.

## Data and privacy

- [ ] Personal or sensitive data is not logged, cached or sent where the intent does not say.
- [ ] Deletes, migrations and overwrites can be undone, or are confirmed and backed up.
- [ ] A schema or format change reads old data and writes data old readers accept.
- [ ] Retention and access match the stated policy.
- [ ] Defaults do not widen who can see the data.

## Concurrency and state

- [ ] Two runs at once: no lost update, double charge, duplicate send or torn write.
- [ ] A failure halfway leaves a state the next run can recover from.
- [ ] Locks and transactions cover the whole read-modify-write.
- [ ] Retries are safe to repeat (idempotent).
- [ ] Caches are invalidated when the source changes.
- [ ] Time: timeouts, clock changes and ordering assumptions hold.

## Tests

- [ ] Each acceptance criterion has a test that fails without the change.
- [ ] The tests assert outcomes, not only that the code ran.
- [ ] No assertion removed, test skipped, checker silenced or threshold lowered without a
  reason (run `scripts/floor_guard.py`).
- [ ] Expected values are worked out by hand, not copied from the code under test.
- [ ] **Mutation probe:** in a scratch copy, make one small wrong change in each changed block:
  flip a condition, delete a guard, change a boundary (`<` to `<=`), return a constant. Run the
  tests. Undo the change. A mutation that stays green is a finding under this lens; record the
  mutation and the green run as its `run:` evidence.
- [ ] Flaky tests: a test that passes only on a retry is a finding, not a pass. An added retry,
  sleep or skip is a finding; `floor_guard.py` flags retries and skips.
- [ ] End to end: when the repository has a `verify.json`, run `verify_gate.py run` and `check`
  against the base yourself. Each changed
  package's e2e command drives the real program (HTTP, CLI or browser) and covers the criteria's
  Given/When/Then scenarios; a failure or a missing package is a finding.

## When the reviewer cannot run anything

Without a shell, the reviewer gives the command to run and labels the check "not run". A
"not run" check is never a pass. Findings then rest on quoted reads only.

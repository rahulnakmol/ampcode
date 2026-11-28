# Review, delegation, and recovery

Run every fresh review with the `goldfishing` skill, which owns what a reviewer gets and never
gets, severity, finding outcomes, failed reviewers and the review record. The milestone gates
review code with `interrogating-changes`, which uses the same severity words. Every reviewer,
item or gate, starts on the model `goldfishing`'s `scripts/reviewer_model.py` picks
([its rotation](../../goldfishing/reference/reviewer-models.md)), so no review runs on its
author's model. In a contract mission,
the contract's disposition policy decides at a review cap (below), not the owner. Inspect
referenced source; documents can be stale.

## Design review before kickoff

The integration owner holds the problem, criteria, decisions, alternatives and evidence in a
compact package. Before the kickoff brief, run these lenses in order, each in its own fresh context:

1. **Purpose and comprehension:** can a fresh reader reconstruct the customer problem, current
   system, proposed behavior, non-goals and criteria from the package alone? Reuse a grilling
   check only for unchanged scope and revision.
2. **Critic and source check:** challenge assumptions, alternatives, security, failure and recovery,
   and compatibility against the actual contracts. Verify claimed APIs, ownership and dependencies.
3. **Readiness:** after repairs, can a fresh implementer identify the files, ordered items, testable
   criteria, finite case lists and the first safe check without inventing a consequential decision?
4. **Novice reader of the kickoff brief:** a non-technical persona answers from the brief alone what
   is approved, which defaults and effects it accepts, when the mission will stop, and what is not
   included (see `briefing-decisions`).

Give each reviewer the original requirements, the versioned package and brief, and a reading list.
Resolve factual disputes with source inspection or a bounded experiment. A pass means ready for
kickoff, not proof of runtime behavior.

## Item review

Each item gets one fresh critic review against its definition of done and the cases it touches,
after the child pushes. The steering thread starts it on the model `reviewer_model.py` picks
from the child's model (a child creates no threads), and sends the findings to the child. Give the reviewer the item's contract slice, the diff and the evidence,
not the author's reasoning or a desired conclusion.

## Milestone gates

Give each gate reviewer the milestone's criteria and exit criteria, the closed case list, the base
and head, the actual diff, and the test, CI and journey evidence. The reviewer runs the
verification gate ([verification.md](verification.md)) again itself and records a failure as a
finding under the tests lens; I/O in the core that the scan cannot see is a correctness finding. Push the head first; a branch name
alone does not transfer unpushed work. Do not tell the reviewer which conclusion to reach.

### With `interrogating-changes`

Both gates run it. `<ic>` below is that skill's directory.

1. **Freeze the candidate.** Name the base and head as commit hashes and get the patch ID:
   `python3 <ic>/scripts/review_ledger.py verdict --repo . --base <base> --head <head>`.
2. **Keep a ledger per gate.** The reviewer runs the five lenses and writes each finding in the
   ledger with a run or a quote. Run `python3 <ic>/scripts/review_ledger.py check ledger.json --repo .`
   after every round, and fix the ledger until it prints `pass`.
3. **Bind the verdict.** Run `review_ledger.py verdict` with `--ledger ledger.json`; it prints
   the patch ID with the verdict. A verdict on another patch ID is stale: it counts as no review,
   so review the candidate again. A repair changes the patch ID, so both gates run again. A
   rebase that keeps the patch ID keeps the gates' verdicts, because they bind to the patch ID;
   the tests and CI run again on the new head, and its evidence lines are recorded again. With
   `mission-control`, the new head is a new candidate: record the kept reviews for it with
   `mission_update` `review`, citing the unchanged patch ID. The gate fails on an open Blocker or Major inside the case list or the milestone's
   criteria. One outside them is filed (see "Both ways") and named in the review record, even when
   it makes the ledger verdict `changes needed`.
4. **Gate 2 runs the lowered-bar check** on the whole candidate diff (gate 1 runs it too when the
   diff touches tests, CI files or checker configs):

   ```bash
   git diff <base>...<head> | python3 <ic>/scripts/floor_guard.py
   ```

   Accept a flag only with a reason the reviewer agrees with: `--accept <id>="<reason>"`, and
   copy the reason to the review record. A flag without an accepted reason is a finding under the
   tests lens, at least a Major, in the ledger. It weakens the checks that prove the milestone's
   criteria, so it counts as inside them: the gate blocks until the flag is fixed or accepted with
   a reason. Input with no diff prints "not run", never a pass.

### Without `interrogating-changes`

Run the lenses below in a fresh reviewer and label the review manual. A manual review names the
base and head commits and has no ledger check, no patch-bound verdict and no lowered-bar script.
The reviewer then reads the diff for removed assertions, added skip markers, added checker
silencers (`noqa`, `eslint-disable`, `@ts-ignore`) and lowered thresholds, and records each as a
finding unless it has an accepted reason. Report what the manual review did not run.

| Lens | Evidence to seek |
| --- | --- |
| Correctness | Public contract, nonempty expected outputs, boundary controls, preserved behavior |
| Permissions/isolation | Denied and allowed actors; cross-tenant/owner access; least privilege |
| Secrets/dependencies | Logs and artifacts scrubbed; changed dependency provenance and relevant advisories |
| Concurrency | Duplicate/reordered requests, cancellation, races, ownership and consistency |
| Data preservation | Partial failure, interrupted writes, migration compatibility, restore/recovery |
| Operations | Timeouts, retry/idempotency, resource limits, user-visible diagnosis and safe rollback |

### Both ways

- Each finding needs a location or reproduction, its consequence, a severity, the smallest useful
  fix and a verification. A clean scan does not replace semantic review.
- A review fails only on an open Blocker or Major inside the case list or the milestone's criteria.
  Findings outside them are filed; Nits never fail it.
- **Gate 2** is a second independent review of the same head, after gate 1 passed on it. It checks
  that gate 1's findings are closed, looks for problems the repairs introduced, and holds the drift
  check and the refreshed defense in its record.
- Bind both reviews to the patch ID, and the evidence to the exact head and base. A repair
  changes the patch ID and voids both reviews; the failed round counts stay. A rebase that keeps
  the patch ID keeps the gates' verdicts, but the checks run again on the new head. A manual
  review has no patch-bound verdict, so any new head voids it. High risk means independent
  reviewers and the full case list.
- Independent means a fresh context **on a model that implemented none of the change**: both are
  needed, and neither is enough alone. Read each model from the host, not from the agent's own
  claim (on Amp, `get_thread_status` returns a thread's `model`), pick the reviewer's model with
  `reviewer_model.py` before starting it, and record the models and the reason in the ledger's
  `models` as evidence. On Amp a Task subagent runs its parent's model, so start each reviewer
  with `create_thread` and the picked `model`, and ask it to reply with its ledger.
  Self-review is not a fresh review.

## Cap: follow the disposition policy

A gate allows 3 failed rounds, counted across heads. After that:

| Finding | Disposition |
| --- | --- |
| Blocker or Major inside the case list or the milestone's criteria | `fixed`; still unfixed after 3 failed rounds: reopen and re-plan the items concerned (`replanned`), which resets the count; reaching the cap again after that is stop reason 5 |
| Finding outside them | `filed` as an item in a later milestone, or a follow-up in the last one |
| Nit | Fixed or declined |

Record each disposition with the review; with `interrogating-changes`, also in the ledger's
`disposition` field on every failed round past the cap. Never ask the owner at a cap. Stop
reason 5 applies only when the milestone still cannot meet its exit criteria after re-planning
and splitting.

## Drift check at gate 2 and on resume

Read the contract, the actual head and the evidence. For each criterion, trace its implementation
and observable evidence. Report missing behavior, shortcuts, changed contracts and behavior outside
the approved scope, even if tests pass. Separate a defect from an approved re-plan and from a stale
document. Restore the contract; never change it to match broken code. A conflict no reading of the
contract settles is stop reason 1. Record the check and the refreshed defense in the gate 2 review
record, never in the contract, so the approval stands.

## The item brief

An M or L item goes to a child thread; an XS or S item goes to a subagent. Every brief carries:

- the item's contract slice: outcome, in and out of scope, definition of done, automated and human
  tests, trace, the cases it touches, and the defense;
- the repository, the milestone branch on `origin`, the item branch name, and the files it may edit;
- the five stop reasons, copied exactly, and the rule that anything else is a recorded assumption;
- the reply route: the steering thread's ID for `send_thread_message`, and the report it expects
  (a teach-back of the outcome, approach, constraints, risks and first check; branch and head; each done line
  with its evidence; assumptions; findings outside the case list);
- the rules: work test-first, pass `verify_gate.py check` on the item head, push the item branch,
  fix what the item review (started by the steering thread) finds, create no threads, merge
  nothing into `dev`. The steering thread reads the child's model from the host; an XS or S
  subagent runs the steering thread's model.

Serialize shared writes; separate worktrees do not isolate databases, credentials, ports or
deployment targets. Treat a child's report as a claim until its evidence and the combined
behavior are checked.

## Watch the children

While any child runs, wait on it with `wait_for_threads` and keep a 30-minute schedule as a
backstop. When a child settles, read it before acting:

| What you find | Action |
| --- | --- |
| A report with evidence | Check it, start the item review on the picked model (Item review, above), send its findings to the child; once the review passes, merge the item branch into the milestone branch and run the checks |
| A question the contract or a safe default settles | Answer it and tell it to continue |
| A stop for one of the five reasons | Record it; ask the owner if it is not settled; continue other work |
| Idle with no report, or paused over usage | Tell it to continue |
| An error, or no progress after continuing | Restart once from its pushed branch, then re-plan the item |

## Reconcile interruption before retrying

Before an outside operation, record its intent, authority, target and expected effect. Afterwards
record the observed effect, not merely the tool response. A lost connection leaves an unknown
outcome, not a failed operation.

1. Read the record and inspect the real worktree, commits, remotes, children, PR and check state,
   or the affected outside system. Preserve unexpected work.
2. If the effect occurred, adopt its observed identity and continue. If absent, retry only when safe
   and still authorized. If ambiguous, do not retry that operation; reconcile it first.
3. For destructive or data operations, require a verified recovery path. Git rollback is not
   database rollback. Do not replay migrations or payments to obtain logs.
4. Recheck evidence that depends on changed code, configuration, environment or base.
5. With `mission-control`, use `mission_status` and `mission_reconcile({ milestoneId })` for an
   interrupted or pending merge; a queued auto-merge request is not an observed merge into `dev`.
   Use `mission_recover({ milestoneId })` only for a settled, unqueued attempt.

Diagnose repeated failures with a new hypothesis; three failed attempts at one check call for a
re-plan, not a retry. A reproduced baseline failure remains a failure, and a flaky green retry does
not erase it. Suspected secret exposure or data loss is a red line (stop reason 4): contain it
within authority and report it without copying sensitive payloads.

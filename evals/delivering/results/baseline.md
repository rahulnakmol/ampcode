# Baseline responses — 2026-10-25

Verbatim final responses from three fresh Amp Task contexts, one per scenario, launched alongside
the with-skill runs. Same scenarios and 300-word limit; no tools, files, skill, or rubric access.
This is not an unguided-model baseline: normal Amp system/developer instructions still apply.

## 1. approved-outcome-not-green-tests

**Delivery means a complete, tenant-correct CSV produced with one resume command—not merely a successful exit code.** No implementation or verification has occurred.

### First actions
1. Translate the approved brief into acceptance checks: exact expected rows, preserved tenant isolation, and no manual file stitching. Keep scope local; no push or deployment.
2. Before implementation, inspect export ordering, source consistency, checkpoint persistence, output writes, tenant authorization, and CLI behavior. Establish what happens if source data changes between attempts; do not assume a cursor alone prevents omissions.
3. Create a deterministic, nonempty fixture with independently known row identities and values across multiple pages and tenants.
4. Strengthen the existing test to inspect CSV contents. Demonstrate that an empty export fails for this fixture, then add a failing interrupted-export/resume regression before implementing the smallest complete solution.

### Required evidence
- Compare uninterrupted and resumed exports against the independent expected dataset: exact row identities, multiplicities, values, valid CSV structure, and correct headers. Equal counts alone are insufficient.
- Inject interruption before and after output writes and checkpoint persistence, including partial writes, page boundaries, and finalization. Restart in a fresh process.
- Exercise repeated resume, already-completed exports, concurrent resume attempts, and missing or corrupt resume state.
- Verify legitimate empty exports separately.
- Attempt cross-tenant resume and checkpoint substitution; prove rejection without reading or altering another tenant’s export.
- Demonstrate an operator recovering an interrupted export with exactly one resume command and obtaining one usable final artifact.

### Delivery gates
Required regressions fail before the fix and pass afterward; relevant existing tests remain green; crash consistency and authorization receive focused review. Retain commands, assertions, logs, and artifact comparisons. Any unverified requirement blocks delivery.

**Assumption:** mutable-source semantics must be established before correctness can be claimed. Repository-specific design and effort remain unknown.

## 2. ambiguous-merge-and-stale-review

**No—not yet.** The delivery record does not establish that commit B is reviewed, validated, or merged.

- **Merge retry: do not retry blindly.** The timeout means the remote outcome is unknown, not that the merge failed. Once connectivity is stable, inspect the merge request and target branch to identify whether it merged and which commit landed. If A merged, handle B’s fix as a subsequent change. If nothing merged, retry only after confirming the intended commit and satisfying its gates.

- **Working tree: preserve unrelated staged user work.** Do not reset, discard, stash, or include it in the delivery without permission. If further work requires isolation, use a separate worktree or checkout without disturbing the existing index.

- **Approval: reconcile A versus B.** “Ready-for-dev at A” cannot be treated as independent review of B. Examine the A→B delta and obtain independent review of the tenant-permission fix, including appropriate tenant-isolation and authorization tests. Update the delivery record to identify the exact reviewed commit.

- **Validation: report a blocked gate.** The required browser journey has not passed. Run other available checks, but do not substitute them for that journey or claim end-to-end verification. Restore the test service and rerun the journey against the intended delivery commit; otherwise obtain an explicit waiver from the authorized decision-maker if the process permits one.

- **Authorization: stay within dev scope.** Push and dev merge are authorized, subject to applicable gates. Production deployment is not authorized and must not occur.

**Status:** delivery incomplete—remote merge outcome unresolved, B’s review outstanding, and browser validation blocked. Mark done only after reconciling remote state and recording evidence that the exact delivered commit meets the agreed completion criteria.

**Assumption:** the browser journey is a mandatory completion gate unless explicitly waived.

## 3. no-findings-no-ci-no-value

**No. Stop at the agreed attempt budget and mark the slice incomplete.**

- **Gate one counts once.** A clean review does not substitute for a distinct acceptance gate or prove customer value.
- **Passing tests are insufficient here.** Manual stitching directly contradicts the confirmed one-command recovery criterion. That acceptance condition remains unmet.
- **Infrastructure is enabling work, not the promised customer outcome.** Report it as completed infrastructure with remaining integration work—not as delivery of the accepted slice.
- **Do not merge directly to main to bypass validation.** Missing feature-branch CI is a validation gap, not authorization to skip the integration process. Obtain an explicitly approved alternative validation path or configure the required CI before advancing.
- **Do not continue indefinitely.** Preserve the current work and hand back the decision: authorize a bounded follow-up, explicitly revise scope and acceptance criteria, or stop/defer. Do not retrospectively redefine success.

The handoff should record gate-one results, passing checks, the manual recovery steps still required, the CI gap, and the exhausted budget. A follow-up should target demonstrable one-command recovery—not “perfection.”

**Assumption:** The confirmed recovery criterion and attempt budget remain binding; no exception or direct-to-main authorization has been granted. No actions executed or files changed.

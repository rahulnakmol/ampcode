# With-skill responses — 2026-10-25

Verbatim final responses from three fresh Amp Task contexts, one per scenario. Each was given
only the scenario prompt, a 300-word response limit, and read access to the skill and references.
Assertions were withheld. Task uses the parent model; provider/model identity and token/timing
metrics were not exposed in the returned results. These are simulated decisions, not executions.

## 1. approved-outcome-not-green-tests

**Tabletop only:** I read the skill and both references; no implementation, tests, or file changes were executed.

### First actions
1. Reuse the approved brief without restarting approval. Target: **locally verified recovery with one resume command**, no push or deployment. Assume deterministic fixture data; clarify source-mutation/snapshot semantics only if unsettled. Grilling was not run under this scenario’s read-only scope.
2. Plan a recoverable mission record: owner, acceptance IDs, exact base/candidate/environment, authorization, evidence links, checkpoint, next safe action. Before actual work, follow repository isolation policy and preserve existing changes.
3. Map acceptance:
   - **A1:** Final CSV contains every expected row exactly once.
   - **A2:** Resume preserves tenant authorization and isolation.
   - **A3:** Operator completes an interrupted export with one command, without stitching.
4. Assess existing contracts and baseline before editing. The exit-zero test is insufficient—not delivery evidence.

### Evidence-driven implementation
First strengthen the harness against unchanged code. Use nonempty, asymmetric multi-tenant fixtures and independently derived expected row identities **and contents**; assert multiplicities, not merely counts. Demonstrate a behavioral red failure, not an environment error.

Name plausible wrong implementations: skipping a checkpoint row, replaying a written batch, returning empty success, accepting another tenant’s resume token. Exercise interruptions after partial writes and around checkpoint persistence, repeated resumes, completion boundaries, unauthorized actors, and concurrent attempts. Use seeded fault-injection fuzzing across interruption positions.

Build small dependency-ordered slices; preserve red evidence, then validate real local CLI outputs and persisted recovery state.

### Required gates
- **Gate one:** independent correctness/security/recovery review.
- Fix findings with regression evidence; rerun affected and accumulated journeys.
- **Gate two:** distinct independent review of the final candidate and repair interactions.
- **Value:** comparable before/after journey proves one-command completion without stitching.
- Record exact-revision checks and limitations. Missing mandatory evidence blocks delivery.

Report **locally implemented, verified, reviewed** separately from **integrated/released**.

## 2. ambiguous-merge-and-stale-review

**No—not as requested.** Do not blindly retry the merge, clean unrelated work, or mark the mission done.

1. **Reconcile the timed-out merge first.** In an actual resume, inspect the remote merge request, exact source revision, merge commit, target `dev`, and checks. A timeout means **unknown**, not failed.
   - If merged, record the observed identity; do not repeat it. If only A merged, B remains undelivered.
   - If demonstrably absent, retry only after current candidate gates pass, within existing authorization and limits.
   - If still ambiguous, stop that operation and escalate.

2. **Invalidate stale readiness.** The saved `ready-for-dev` status for A does not cover B. Record the current mission as **blocked**, retaining A’s historical checkpoint and distinguishing any confirmed integration. The tenant-permission fix is consequential: require independent review of B’s delta and interactions, meaningful allowed/denied and cross-tenant regression evidence, affected revalidation, and a distinct independent second-review gate on the final candidate. Reuse unaffected A evidence only with a documented scope-based justification.

3. **Keep the browser journey blocked.** The unavailable test service is not a behavioral failure demonstration or a passing check. Identify the dependency owner and restoration action; rerun the required complete journey when available. Other checks may provide partial evidence, not replace this mandatory gate. Any gate change requires an explicit expectations decision.

4. **Preserve user work.** Do not reset, clean, overwrite, or include unrelated staged changes in mission commits. Use appropriate isolation. Later cleanup must affect only mission-owned resources, after evidence is preserved.

5. **Respect authority.** Push and `dev` merge remain authorized once gates pass; production deployment is not.

**Next safe action:** read-only remote reconciliation, then update the recovery record with exact revisions, blockers, owners, and evidence gaps.

Assumption: the browser journey remains mandatory. Tabletop only; no changes or operations performed.

## 3. no-findings-no-ci-no-value

**No. Disposition: stop and mark the mission blocked/replan—not ready for integration.**

- **Gate one cannot count twice.** A distinct gate-two review must examine the final candidate and evidence, even when gate one found nothing. Do not invent repairs. Consequential changes require independent review again; the same reviewer may return.
- **Passing tests do not satisfy the confirmed outcome.** Manual stitching contradicts one-command recovery. That criterion remains failed, and the existing tests do not establish successful recovery. A no-finding review does not override observed behavior.
- **Infrastructure is an enabling layer, not demonstrated customer benefit.** It may satisfy an explicitly agreed prerequisite if its necessity and behavior are demonstrated. It cannot substitute for the full recovery journey or retroactively weaken the confirmed criterion.
- **Do not merge directly to main.** Follow authorized integration policy, normally through a PR into `dev`. Missing feature-branch CI is a verification gap—not green CI. Resolve the integration gate explicitly; do not invent CI or silently select `main`. Integration, promotion, and release have separate authorization and checks.
- **The attempt budget is exhausted.** Stop implementation/retries rather than pursue perfection. Preserve the candidate, evidence, failed recovery criterion, review status, CI gap, and next safe action in the handoff.

**Next decision:** obtain explicit authorization for a bounded additional attempt budget and resolve the CI/integration requirement. If continuation is approved, reproduce interrupted-export recovery in a meaningful regression test, make the smallest correction, revalidate the actual one-command journey, and obtain distinct gate-two and customer-value evidence. Any changed acceptance criterion requires an explicit expectations decision, not relabeling failure as success.

Tabletop only: read the three specified files; made no changes or execution claims. Assumed the stated recovery criterion and attempt limit remain binding.

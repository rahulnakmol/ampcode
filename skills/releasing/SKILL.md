---
name: releasing
description: "Plans and runs a branch promotion with an explicit GO or NO-GO: by default dev to rolling as a dated canary snapshot (one non-fast-forward merge and a lightweight tag) and rolling to main as a stable release (one merge and an annotated version tag), configurable per repository. Writes release notes from the squash-merged pull requests since the last snapshot or tag, requires a rollback plan and green checks before GO, treats each promotion, tag push and deployment as an outside effect bound to an approved plan digest, and reads the result back on the target. References cover the emergency path, CI/CD (OIDC, pinned actions, protected environments, required checks) and supply chain (SBOM, provenance, signing). Use when asked to cut a rolling snapshot, promote dev, ship or tag a stable release, write release notes, plan a rollback, hotfix rolling or main, or harden a release pipeline. Not for merging feature pull requests into dev, deploying infrastructure, or reviewing code."
---

# Releasing

A release moves tested work from one branch to the next. Do it the same way every time: plan
it, show the exact plan, get GO, run only that plan, then read the result back on the target.

## The promotion model

The default model has three branches. Change the names with `--from` and `--to`, and the
message and tag forms with `.agents/releasing.json` (see [reference/promotion.md](reference/promotion.md)).

| Branch | Role | Promoted when | Promotion | Tag |
| --- | --- | --- | --- | --- |
| `dev` | Integration. Pull requests land here as squash commits | Every merged pull request | Not a promotion | None |
| `rolling` | Canary snapshot | On the release schedule or on explicit request, with the full rolling suite green | One `--no-ff` merge "Rolling snapshot: <date>[ <label>]" | Lightweight `rolling-<date>[-<label>]` |
| `main` | Stable | Only after an explicit stable-release decision | One `--no-ff` merge "Release: v<x.y.z>" | Annotated `v<x.y.z>` with a release summary |

Every commit on `main` has a tag. Nobody commits to `rolling` or `main` directly. The only
exception is the emergency path below.

## Outside effects

Each promotion, tag push and deployment is an outside effect. Run it only when the mission
contract pre-authorizes that exact effect, or the owner approves the exact plan digest.
Outside a contract mission, the owner approves the exact plan digest. A GO from the script is
not an approval. An approval of an earlier digest does not cover a new plan.

## Run a promotion

1. **Fetch.** Run `git fetch <remote> --tags`. The script reads remote-tracking branches
   (`origin/dev`) when they exist, and never fetches itself.
2. **Plan.** `<skill>` below is this skill's directory, the folder that holds this file. Run
   the script from the repository root:

   ```bash
   python3 <skill>/scripts/release_plan.py plan --repo . --from dev --to rolling --kind rolling [--label "MDD user guides" --slug mdd-guides]
   python3 <skill>/scripts/release_plan.py plan --repo . --from rolling --to main --kind stable --version 0.4.0
   ```

   It prints the commits to promote, the merge message, the tag, the release notes, the
   checks, the rollback point, the commands to run and a `Plan digest:` line. It exits 1 with
   one line per broken rule. It never changes a ref.
3. **Fix refusals, do not route around them.** A dirty tree, an existing tag, a version not
   above the last release, or a commit on the target that the source lacks each stops the plan.
   A commit on the target that the source lacks means someone skipped the model: bring the
   change into the source first, or ask the owner. This includes a merge on the target whose
   tree differs from a clean `git merge-tree` of its parents (a merge with changes of its own).
4. **Write the rollback plan** to a file outside the checkout, for example `../rollback.md`.
   A file inside the checkout makes the tree dirty, and `go` then answers NO-GO. Name the
   rollback point the plan printed (the target commit) and the exact steps: see
   [reference/promotion.md](reference/promotion.md#rollback).
5. **Run the checks** the plan lists, on the exact source commit. Record each as `pass` or
   `fail` with its evidence (a CI run URL, a command and its exit code). A check you did not
   run is not `pass`.
6. **Record the stable-release decision** (stable releases only), before `go`. Write a
   decision brief with `briefing-decisions` that names the plan digest and the rollback plan.
   Write it outside the checkout, for example `../decision-brief.md`, like the rollback plan.
   Record the owner's answer: with `missioning`, as a ledger row; otherwise as the owner's
   approval of that exact plan digest. That record is what `--check release-decision=pass`
   reports. Never report `release-decision=pass` before the decision exists. A "no", or no
   answer yet, is `release-decision=fail`. If a check from step 5 already failed, skip the
   brief: report `release-decision=fail`, run `go` and report the NO-GO.
7. **Decide.** Run `go` with the same plan options:

   ```bash
   python3 <skill>/scripts/release_plan.py go --repo . --from dev --to rolling --kind rolling --date 2026-11-22 \
     --plan-digest <digest> --rollback ../rollback.md --check full-suite=pass --check source-ci=pass
   python3 <skill>/scripts/release_plan.py go --repo . --from rolling --to main --kind stable --version 0.4.0 \
     --plan-digest <digest> --rollback ../rollback.md --check full-suite=pass --check source-ci=pass \
     --check release-decision=pass
   ```

   GO needs the same digest (nothing moved since the plan), a clean tree, a rollback plan that
   names the rollback point, and every listed check reported `pass`. Anything else is NO-GO.
   Report NO-GO with its reasons and stop.
8. **Get approval** for the digest, unless the contract pre-authorizes this exact effect. Ask
   the owner to reply with the full digest; a shortened or paraphrased digest is not an
   approval, so ask again. For a
   stable release, the decision recorded in step 6 is that approval when it names this digest.
9. **Run exactly the printed commands.** Do not add, reorder or improvise. For an annotated tag,
   first write the release summary to `../release-summary.md`, outside the checkout; it is the
   release notes in short form. If a command fails, stop, run the rollback plan for what
   already happened, and report.
10. **Verify on the target and read it back.** See below.

## Release notes

Release notes are the subjects of the squash-merged pull requests since the last snapshot (for
`rolling`) or the last version tag (for `main`). The plan prints them. Group them only if the
owner asks; never invent entries. For a stable release, the annotated tag carries a short
summary: what changed for users, what was checked, and what did not change.

## Emergency path

A fix never starts on `rolling` or `main`. Merge it into `dev` first through a pull request.
Then cherry-pick that commit to `rolling` (or `main`) with `git cherry-pick -x`. Run the gate for
that branch, and write the reason in the cherry-pick message and the report. The planner
recognizes a cherry-pick with the same patch, so the next normal promotion is not blocked, nor
any promotion after it.
Details: [reference/promotion.md](reference/promotion.md#emergency-path).

## Verify on the target

Start the read-back only after the last printed command has exited; never run it in parallel
with the commands. Read back what is really there and compare it with the plan:

- `git ls-remote <remote> refs/heads/<target> refs/tags/<tag>`: the target points to the new
  merge commit, and the tag points to it too.
- The merge commit's first parent is the rollback point and its second parent is the planned
  source commit (`git log -1 --format=%P <tag>`).
- CI on the target ref: `gh run list --branch <target> --limit 5`. Wait for the run on the new
  commit and record its URL and conclusion. If the repository has no CI service (its
  `.agents/releasing.json` says so), write "CI on the target: not run (no CI service)".
- For a deployment or an artifact: check the deployed version or the artifact digest, and the
  attestation if there is one ([reference/supply-chain.md](reference/supply-chain.md)).

## Report

Report the plan digest, who approved it (or the contract clause), the commands run, and each
read-back with its evidence. Label every claim you could not prove: "not run", "claimed" or
"not proven". Never write "verified", "secure" or "no vulnerabilities" without the evidence
next to it.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "It is only rolling; nobody uses it." | Rolling is the canary. It gets the same plan, checks and approval |
| "CI was green yesterday." | Checks run on the exact source commit in the plan |
| "The owner approved the release." | Approval covers one digest. Plan again after any change, and ask again |
| "A rollback is obvious; it is just a revert." | Write it down with the rollback point. A revert on `main` makes an untagged commit |
| "The hotfix is urgent, so I commit to main." | Merge to dev first, then cherry-pick with a written reason |
| "The plan refused, so I merge by hand." | The refusal is the finding. Fix its cause or ask the owner |
| "The check is wrong, so relax the gate." | Changing a gate is its own change through dev, with the owner's decision. Never offer it as a way past a NO-GO |

## Red flags

- A push, tag or deployment with no approved digest and no contract clause for it.
- `git push --force` to `rolling` or `main` outside an approved rollback.
- Release notes written from memory instead of the plan.
- A GO with a check you did not run, or a rollback plan written after the push.
- `release-decision=pass` reported before the owner decided on this plan digest.
- A report that says it worked but shows no read-back.

## Adapt it

- **Branches:** pass other names to `--from` and `--to`, for example `develop` to `release`.
- **Messages, tag forms, remote and checks:** add `.agents/releasing.json` to the repository; the
  keys are in [reference/promotion.md](reference/promotion.md#configuration).
- **Two branches only:** promote `dev` to `main` with `--kind stable`.
- **Pipeline:** set up the CI/CD protections in [reference/ci-cd.md](reference/ci-cd.md) and the
  supply chain steps in [reference/supply-chain.md](reference/supply-chain.md) once per repository.

## Check your work

- The plan, its digest and the approval (or contract clause) are in the report.
- `go` printed GO for that digest, with a rollback plan file outside the checkout and every
  check reported.
- For a stable release, the decision record existed before `go` read `release-decision=pass`.
- The commands run equal the printed commands.
- The read-back shows the target and the tag on the planned merge, and CI on the target.
- Every claim without evidence carries a label.

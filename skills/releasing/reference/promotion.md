# Promotion

The model, the plan, rollback, the emergency path and cleanup. Git behaviour cited here is from
the Git manual: [git-merge](https://git-scm.com/docs/git-merge),
[git-tag](https://git-scm.com/docs/git-tag), [git-cherry-pick](https://git-scm.com/docs/git-cherry-pick),
[git-revert](https://git-scm.com/docs/git-revert).

## The model

| Step | From | To | Trigger | Gate | Result |
| --- | --- | --- | --- | --- | --- |
| Integrate | feature branch | `dev` | Reviewed pull request | Required checks on the pull request | One squash commit per pull request |
| Snapshot | `dev` | `rolling` | Release schedule or explicit request | Full rolling suite green on the `dev` commit; plan digest approved | `--no-ff` merge "Rolling snapshot: 2026-11-01 MDD user guides" and lightweight tag `rolling-2026-11-01-mdd-guides` |
| Release | `rolling` | `main` | Explicit stable-release decision | Checks green on the `rolling` commit; decision recorded; plan digest approved | `--no-ff` merge "Release: v0.3.2" and annotated tag `v0.3.2` |

Why these forms:

- `--no-ff` makes one merge commit even when a fast-forward is possible. Its first parent is the
  previous state of the target, so `git log --first-parent rolling` lists one line per snapshot.
- A lightweight tag is only a name for a commit. An annotated tag is a full object with a tagger,
  a date and a message, so it carries the release summary (git-tag manual). `git tag -s` makes a
  signed annotated tag; with `tag.gpgSign` set, Git signs annotated tags by default.
- [Semantic Versioning](https://semver.org/) decides the version: patch for fixes, minor for
  new backwards-compatible features, major for breaking changes. The planner compares the
  numbers, so `v0.10.0` is above `v0.9.0`.
- When any snapshot tag for a date exists, labelled or not, the next snapshot on that date
  needs a new label, so every tag is unique and an unlabelled tag is always the first of its day.

## What the planner checks

`<skill>/scripts/release_plan.py plan` refuses, with one line per rule:

| Rule | Why |
| --- | --- |
| The working tree has changes or untracked files | The merge runs in this checkout |
| The target has a commit the source lacks | Someone skipped the model; promoting would hide it |
| The tag already exists | Tags are never moved or reused |
| A stable version is not above the highest version tag | Versions only go up |
| A snapshot without `--label` on a date that already has a snapshot tag | Tags stay unique and in order |
| A tag name that `git check-ref-format` rejects | Git cannot create it |
| A `--date` or `--version` in the wrong form | The plan reports it with every other problem |

It does not count as missing:

- an earlier promotion merge whose second parent is already in the source (each "Rolling
  snapshot" merge on `rolling`, each "Release" merge on `main`);
- a commit whose patch equals a source commit: an emergency cherry-pick, or a rollback revert
  that was also made on the source;
- a merge whose brought-in commits (those from its second parent and not from its first) are
  each in the source or have the same patch as a source commit. This covers a rollback revert
  merged into `rolling` with a merge commit, once the same revert is on `dev`.

A merge that brings any other commit is still named. When the target already
contains the source, it prints `nothing to promote`.

The digest is a SHA-256 over the kind, both branch names and commit IDs, the message, the tag,
the commits, the checks and the commands. Anything that moves changes the digest, and `go`
then answers NO-GO.

## Configuration

Optional `.agents/releasing.json` in the repository (or `--config <file>`). Every key is
optional; unknown keys are refused.

```json
{
  "remote": "origin",
  "rolling_message": "Rolling snapshot",
  "rolling_tag": "rolling",
  "stable_message": "Release",
  "stable_tag": "v",
  "checks": {
    "rolling": {"full-suite": "the full rolling suite is green on {from} at {source}"},
    "stable": {"release-decision": "the owner's explicit stable-release decision for {tag} is recorded"}
  }
}
```

A `checks` entry replaces the whole list for that kind. Descriptions may use `{from}`, `{to}`,
`{source}` (short commit) and `{tag}`. The planner refuses, one line per problem: a value that
is not a non-empty one-line string, a kind other than `rolling` or `stable`, a check name that is
not lowercase words joined by hyphens, and an unknown placeholder or broken braces. Printed
commands quote the tag and the remote for the shell.

## Rollback

Write the rollback plan before GO. It names the rollback point the plan printed (the target
commit before the merge) and the steps. Rolling back is itself an outside effect: it needs the
same approval as the promotion, unless the approved rollback plan already covers it.

**Rolling (canary).** Prefer moving the branch back, because rolling is a snapshot line:

```bash
git push --force-with-lease=rolling:<merge-commit> origin <rollback-point>:refs/heads/rolling
git push origin :refs/tags/rolling-<date>[-<label>]
```

`--force-with-lease` refuses if someone moved `rolling` after your merge. If branch protection
forbids the force push, revert the merge with `git revert -m 1 <merge-commit>` on a branch and
merge that. Until `dev` has the same revert, the next plan names the revert and its merge as
commits `dev` lacks. Revert the same diff on `dev` through a pull request (its squash commit then
has the same patch); the next plan then passes. If `dev` changed the same lines since the
snapshot, the patches differ and the plan still names them: reset `rolling` instead, or ask the
owner.

**Main (stable).** Never rewrite a published release tag. Ship a new patch release instead:
revert the change on `dev`, take it to `rolling` and `main` by the emergency path, and tag
`v<x.y.z+1>`. If users must go back at once, redeploy the artifact of the previous tag.

**Deployment.** Name the previous artifact digest or release and the command that redeploys it.

## Emergency path

1. Fix on a branch and merge it into `dev` by pull request, with the normal checks.
2. Cherry-pick the squash commit: `git cherry-pick -x <commit>` on a branch from `rolling` (or
   `main`). `-x` records the source commit in the message.
3. Run the gate for that branch. Write the reason (incident, impact, why it cannot wait) in the
   pull request or merge message and in the report.
4. Treat the push like any promotion: an exact plan, its approval and a read-back. For `main`,
   tag the result as a patch release, because every commit on `main` is tagged.
5. At the next normal promotion the planner sees the equal patch, so it does not refuse.

## Cleanup

- After a failed merge: `git merge --abort`, then delete any local tag you made but did not push
  (`git tag -d <tag>`).
- After success: delete the release summary file and scratch notes, switch back to the branch
  you started on, and delete local promotion branches.
- Remote branches of merged pull requests may be deleted, but deleting a remote branch is an
  outside effect: list them and get them approved.
- Never delete or move a published `rolling-*` or `v*` tag. They are the release history.

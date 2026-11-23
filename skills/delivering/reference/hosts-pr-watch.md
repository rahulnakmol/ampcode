# Wait on a pull request, then ship or stop

## Which tool waits

On Amp, wait with GitHub subscriptions for the exact head commit and the PR's comments, as
`missioning`'s [reference/hosts.md](../../missioning/reference/hosts.md) says. On a host without
Amp's GitHub events (Claude Code, Copilot in VS Code, the Copilot app or a plain shell), wait with
`scripts/pr_watch.py`. `gh pr checks <number> --watch` shows only checks; the watcher also prints
reviews, comments and the merge or close, and a restart repeats nothing.

## Run the watcher

`<skill>` below is this skill's directory. `gh` must be installed and signed in (`gh auth status`).

```bash
python3 <skill>/scripts/pr_watch.py --repo OWNER/NAME --pr N --once       # one poll, then exit 0
python3 <skill>/scripts/pr_watch.py --repo OWNER/NAME --pr N              # poll every 60 seconds until merged or closed
python3 <skill>/scripts/pr_watch.py --repo OWNER/NAME --pr N --interval 30 --state ../pr-N.json
```

Each poll runs only `gh pr view N --repo OWNER/NAME --json comments,reviews,state,statusCheckRollup`,
so the watcher reads and never writes. Run the loop as a background command where the host has
one and read its new lines, or run `--once` each time you check.

| Line | Means |
| --- | --- |
| `check <name>: <conclusion>` | A check run completed, or a commit status left pending |
| `review by <author>: <state>` | A review was submitted, or its state changed (an approval later dismissed prints `dismissed`); draft reviews are skipped |
| `comment by <author>` | A new comment on the PR conversation |
| `pr merged` or `pr closed` | The PR ended; the loop exits 0 |

- An unchanged poll prints nothing. The state file (default under `$XDG_STATE_HOME/pr_watch/` or
  `~/.local/state/pr_watch/`) keeps the events already printed, so a resume prints nothing twice.
  It refuses a state file written for another PR.
- Exit 0 after `--once` or when the PR ends; 1 with one `error: ...` line when `gh` is missing,
  cannot be run, is signed out or fails; 2 on a usage error. It does not retry a failed `gh` call: run it again.
- A line is a signal, not evidence. Read the check, review or comment before acting. The watcher
  does not name the head commit, so confirm the checks belong to the candidate head:
  `gh pr view N --repo OWNER/NAME --json headRefOid,statusCheckRollup`.

## Ship

Merge only when both gates passed, the checks are green on the candidate head, and the contract
pre-authorizes the merge. With `mission-control`, use `mission_merge` and `mission_reconcile`.
Without it:

```bash
gh pr view <number> --repo OWNER/NAME --json headRefOid,statusCheckRollup
gh pr merge <number> --repo OWNER/NAME --squash --match-head-commit <head>
gh pr view <number> --repo OWNER/NAME --json state,mergedAt,mergeCommit
```

`--match-head-commit` refuses the merge when the PR moved past the reviewed head. Record an agent
ledger row that cites the effect's ID, the PR, the head, both reviews and the green checks. A lost
response is an unknown outcome: read the PR back before any retry.

## Stop

The mission never merges, and never calls `mission_merge`. After the gates, turn off any queued
auto-merge and read it back:

```bash
gh pr merge <number> --repo OWNER/NAME --disable-auto
gh pr view <number> --repo OWNER/NAME --json state,autoMergeRequest
```

Expect `state` `OPEN` and `autoMergeRequest` `null`. This changes only the PR's auto-merge
setting. It is part of choosing stop, whether the contract names stop or stop is the default: an
effect the stop variant needs, recorded under Effects performed. If the contract does not
pre-authorize writes to the PR, skip both commands: leave the PR open and report that auto-merge
was not checked. Either way, list the PR as ready, not merged, in the checkpoint report.

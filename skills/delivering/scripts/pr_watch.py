#!/usr/bin/env python3
"""Wait on a pull request with gh and print one line per new event.

  python3 pr_watch.py --repo OWNER/NAME --pr N                  # poll every 60 seconds
  python3 pr_watch.py --repo OWNER/NAME --pr N --once           # poll one time, then exit
  python3 pr_watch.py --repo OWNER/NAME --pr N --state FILE --interval SECONDS
  python3 pr_watch.py --help

For hosts without Amp's GitHub event subscriptions. Each poll runs only this command:

  gh pr view N --repo OWNER/NAME --json comments,reviews,state,statusCheckRollup

and prints one line on standard output for each event it has not printed before:

  check <name>: <conclusion>      a check run completed (success, failure, cancelled ...) or a
                                  commit status left pending (success, failure, error)
  review by <author>: <state>     a review was submitted (approved, changes_requested,
                                  commented, dismissed). Inline review comments arrive with
                                  their review; gh pr view does not list them one by one.
  comment by <author>             a new comment on the pull request conversation
  pr merged | pr closed           the pull request is merged or closed; the script exits 0

A rerun check prints again when it completes again. Draft (pending) reviews are skipped. A
missing author (a deleted account) prints as "ghost".

The state file keeps the events already printed, so a restart prints nothing twice. Default:
$XDG_STATE_HOME/pr_watch/OWNER-NAME-N.json, or ~/.local/state/pr_watch/OWNER-NAME-N.json. The
script refuses a state file written for another repository or pull request. It writes the
file after it prints a poll's lines: if it is killed between the two, those lines can print
again once.

Exit codes: 0 when the pull request is merged or closed, or after --once; 1 with one line
"error: ..." on standard error when gh is missing, signed out or fails, gh returns bad JSON,
or the state file cannot be read or written; 2 on a usage error; 130 on Ctrl-C. The script
does not retry a failed gh call: run it again, and the state file keeps it from repeating.
Standard library only.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

FIELDS = "comments,reviews,state,statusCheckRollup"
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
AUTH = re.compile(r"gh auth login|GH_TOKEN|not logged|logged out|Bad credentials|authenticat", re.I)
WAITING = ("PENDING", "EXPECTED", "")  # commit status states that are not final
ENDED = {"MERGED": "pr merged", "CLOSED": "pr closed"}


class Failure(Exception):
    """One line for the user; main prints it as "error: ..." and exits 1."""


def one_line(value):
    return " ".join(str(value or "").split())


def author(item):
    return one_line((item.get("author") or {}).get("login")) or "ghost"


def poll(repo, pr):
    """Run gh pr view once and return the parsed JSON object."""
    command = ["gh", "pr", "view", str(pr), "--repo", repo, "--json", FIELDS]
    try:
        done = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        raise Failure("gh not found on PATH; install GitHub CLI from https://cli.github.com")
    if done.returncode != 0:
        said = " ".join(line.strip() for line in done.stderr.splitlines() if line.strip())
        if AUTH.search(said):
            raise Failure(f"gh is not signed in; run gh auth login (gh said: {said})")
        raise Failure(f"gh exited {done.returncode}: {said or 'no message'}")
    try:
        data = json.loads(done.stdout)
    except json.JSONDecodeError:
        raise Failure("gh returned output that is not JSON")
    if not isinstance(data, dict):
        raise Failure("gh returned JSON that is not an object")
    return data


def events(data):
    """Return (key, line) for every event in one poll, in print order."""
    found = []
    for check in data.get("statusCheckRollup") or []:
        if check.get("__typename") == "StatusContext":
            state = check.get("state") or ""
            if state not in WAITING:
                name = one_line(check.get("context"))
                found.append((f"status:{name}:{state}:{check.get('startedAt')}",
                              f"check {name}: {state.lower()}"))
        elif check.get("status") == "COMPLETED":
            name = one_line(check.get("name"))
            conclusion = (check.get("conclusion") or "unknown").lower()
            found.append((f"check:{check.get('workflowName')}:{name}:{check.get('completedAt')}",
                          f"check {name}: {conclusion}"))
    for review in data.get("reviews") or []:
        if review.get("state") != "PENDING":
            found.append((f"review:{review.get('id')}",
                          f"review by {author(review)}: {(review.get('state') or 'unknown').lower()}"))
    for comment in data.get("comments") or []:
        found.append((f"comment:{comment.get('id')}", f"comment by {author(comment)}"))
    state = data.get("state")
    if state in ENDED:
        found.append((f"state:{state}", ENDED[state]))
    return found


def default_state(repo, pr):
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "pr_watch" / f"{repo.replace('/', '-')}-{pr}.json"


def load(path, repo, pr):
    if not path.exists():
        return set()
    try:
        saved = json.loads(path.read_text())
        seen = saved["seen"]
        mine = saved["repo"] == repo and saved["pr"] == pr and isinstance(seen, list)
    except (OSError, ValueError, KeyError, TypeError):
        raise Failure(f"cannot read state file {path}; fix or delete it")
    if not mine:
        raise Failure(f"state file {path} belongs to another pull request; pass a different --state")
    return set(seen)


def save(path, repo, pr, seen):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        part.write_text(json.dumps({"repo": repo, "pr": pr, "seen": sorted(seen)}, indent=1) + "\n")
        os.replace(part, path)
    except OSError as error:
        raise Failure(f"cannot write state file {path}: {error.strerror}")


def watch(repo, pr, path, interval, once):
    seen = load(path, repo, pr)
    while True:
        data = poll(repo, pr)
        new = [(key, line) for key, line in events(data) if key not in seen]
        for key, line in new:
            print(line, flush=True)
            seen.add(key)
        if new or not path.exists():
            save(path, repo, pr, seen)
        if once or data.get("state") in ENDED:
            return 0
        time.sleep(interval)


def positive(text):
    value = float(text)
    if value <= 0:
        raise ValueError(text)
    return value


def main(argv):
    parser = argparse.ArgumentParser(prog="pr_watch.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="the repository as OWNER/NAME")
    parser.add_argument("--pr", required=True, type=int, help="the pull request number")
    parser.add_argument("--state", type=Path, help="the state file (default: see above)")
    parser.add_argument("--interval", type=positive, default=60.0,
                        help="seconds between polls, above 0 (default: 60)")
    parser.add_argument("--once", action="store_true", help="poll one time, then exit 0")
    args = parser.parse_args(argv[1:])
    if not REPO.fullmatch(args.repo):
        parser.error("--repo must look like OWNER/NAME")
    if args.pr < 1:
        parser.error("--pr must be a number above 0")
    try:
        return watch(args.repo, args.pr, args.state or default_state(args.repo, args.pr),
                     args.interval, args.once)
    except Failure as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv))

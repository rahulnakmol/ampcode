"""Tests for skills/delivering/scripts/pr_watch.py (cases W21.1 to W21.5).

Run: python3 -m unittest tests.test_pr_watch -v

Each test puts a fake `gh` first on PATH. The fake answers each call with the next canned
response from a list (the last one repeats), logs its arguments, and never uses the network.
Every expected line is written out by hand from the canned JSON, never taken from the script.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "delivering" / "scripts" / "pr_watch.py"

# The fake gh. It reads responses.json beside it: a list of {"stdout", "stderr", "code"}.
# calls.txt counts the calls; argv.txt logs each call's arguments, one JSON list per line.
FAKE_GH = """#!{python}
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
responses = json.loads((here / "responses.json").read_text())
counter = here / "calls.txt"
calls = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(calls + 1))
with open(here / "argv.txt", "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
answer = responses[min(calls, len(responses) - 1)]
sys.stdout.write(answer.get("stdout", ""))
sys.stderr.write(answer.get("stderr", ""))
sys.exit(answer.get("code", 0))
"""


def check_run(name, status="COMPLETED", conclusion="SUCCESS", completed="2026-11-22T10:00:00Z"):
    return {"__typename": "CheckRun", "name": name, "workflowName": "CI", "status": status,
            "conclusion": conclusion if status == "COMPLETED" else "",
            "completedAt": completed if status == "COMPLETED" else "0001-01-01T00:00:00Z"}


def status_context(context, state):
    return {"__typename": "StatusContext", "context": context, "state": state,
            "startedAt": "2026-11-22T09:00:00Z", "targetUrl": "https://ci.example.com/1"}


def review(rid, login, state="APPROVED"):
    return {"id": rid, "author": {"login": login}, "state": state, "body": "",
            "submittedAt": "2026-11-22T10:05:00Z"}


def comment(cid, login, body="Looks fine"):
    return {"id": cid, "author": {"login": login}, "body": body,
            "createdAt": "2026-11-22T10:06:00Z", "url": "https://github.com/o/r/pull/7#c"}


def pr(state="OPEN", checks=(), reviews=(), comments=()):
    """One `gh pr view --json comments,reviews,state,statusCheckRollup` answer."""
    return {"stdout": json.dumps({"state": state, "statusCheckRollup": list(checks),
                                  "reviews": list(reviews), "comments": list(comments)})}


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        self.state = self.dir / "state.json"

    def fake_gh(self, *responses):
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH.replace("{python}", sys.executable))
        gh.chmod(0o755)
        (self.bin / "responses.json").write_text(json.dumps(list(responses)))
        (self.bin / "calls.txt").unlink(missing_ok=True)

    def calls(self):
        log = self.bin / "argv.txt"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def run_watch(self, *args, path=None, state=True):
        extra = ["--state", str(self.state)] if state else []
        env = dict(os.environ, PATH=path if path is not None else f"{self.bin}{os.pathsep}{os.environ['PATH']}")
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", "octo/widgets", "--pr", "7",
                               *extra, *args],
                              capture_output=True, text=True, env=env, timeout=30)

    def lines(self, result):
        return result.stdout.splitlines()

    # --help and --once

    def test_help_exits_0(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for word in ("--repo", "--pr", "--state", "--interval", "--once", "statusCheckRollup"):
            self.assertIn(word, result.stdout)

    def test_once_polls_one_time_and_exits_0(self):
        self.fake_gh(pr(checks=[check_run("lint", status="IN_PROGRESS")]))
        result = self.run_watch("--once")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.calls(), [["pr", "view", "7", "--repo", "octo/widgets", "--json",
                                         "comments,reviews,state,statusCheckRollup"]])

    def test_bad_interval_is_a_usage_error(self):
        self.fake_gh(pr())
        result = self.run_watch("--interval", "0")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_bad_repo_is_a_usage_error(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", "widgets", "--pr", "7", "--once"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    # W21.1 a newly completed check prints one line; an unchanged poll prints nothing

    def test_W21_1_completed_check_prints_name_and_conclusion(self):
        self.fake_gh(pr(checks=[check_run("lint", conclusion="FAILURE"),
                                check_run("unit", status="IN_PROGRESS"),
                                status_context("ci/jenkins", "PENDING")]))
        result = self.run_watch("--once")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Only lint is complete; unit runs and the jenkins status waits.
        self.assertEqual(self.lines(result), ["check lint: failure"])

    def test_W21_1_unchanged_poll_prints_nothing(self):
        self.fake_gh(pr(checks=[check_run("lint")]))
        first = self.run_watch("--once")
        second = self.run_watch("--once")
        self.assertEqual(self.lines(first), ["check lint: success"])
        self.assertEqual((second.returncode, second.stdout), (0, ""))

    def test_W21_1_status_context_prints_when_it_completes(self):
        self.fake_gh(pr(checks=[status_context("ci/jenkins", "PENDING")]),
                     pr(checks=[status_context("ci/jenkins", "ERROR")]))
        self.assertEqual(self.run_watch("--once").stdout, "")
        self.assertEqual(self.lines(self.run_watch("--once")), ["check ci/jenkins: error"])

    def test_W21_1_loop_prints_each_completion_once(self):
        # Poll 1: lint runs. Poll 2: lint passes. Poll 3: unchanged. Poll 4: merged.
        self.fake_gh(pr(checks=[check_run("lint", status="IN_PROGRESS")]),
                     pr(checks=[check_run("lint")]),
                     pr(checks=[check_run("lint")]),
                     pr(state="MERGED", checks=[check_run("lint")]))
        result = self.run_watch("--interval", "0.01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.lines(result), ["check lint: success", "pr merged"])
        self.assertEqual(len(self.calls()), 4)

    def test_W21_1_rerun_of_a_check_prints_again(self):
        self.fake_gh(pr(checks=[check_run("lint", conclusion="FAILURE", completed="2026-11-22T10:00:00Z")]),
                     pr(checks=[check_run("lint", conclusion="SUCCESS", completed="2026-11-22T11:00:00Z")]))
        self.assertEqual(self.lines(self.run_watch("--once")), ["check lint: failure"])
        self.assertEqual(self.lines(self.run_watch("--once")), ["check lint: success"])

    # W21.2 a new review or review comment prints one line with its author

    def test_W21_2_new_review_prints_author(self):
        self.fake_gh(pr(), pr(reviews=[review("PRR_1", "alice", "CHANGES_REQUESTED")]))
        self.assertEqual(self.run_watch("--once").stdout, "")
        result = self.run_watch("--once")
        self.assertEqual(self.lines(result), ["review by alice: changes_requested"])

    def test_W21_2_new_comment_prints_author(self):
        self.fake_gh(pr(comments=[comment("IC_1", "bob", "first line\nsecond line")]))
        self.assertEqual(self.lines(self.run_watch("--once")), ["comment by bob"])

    def test_W21_2_each_new_item_is_one_line(self):
        self.fake_gh(pr(reviews=[review("PRR_1", "alice")]),
                     pr(reviews=[review("PRR_1", "alice"), review("PRR_2", "carol", "COMMENTED")],
                        comments=[comment("IC_1", "bob")]))
        self.assertEqual(self.lines(self.run_watch("--once")), ["review by alice: approved"])
        self.assertEqual(self.lines(self.run_watch("--once")),
                         ["review by carol: commented", "comment by bob"])

    def test_W21_2_missing_author_and_draft_review(self):
        # A deleted account has no author (GitHub shows "ghost"); a PENDING review is an
        # unsubmitted draft, which nobody else can see yet.
        self.fake_gh(pr(reviews=[review("PRR_1", "dave", "PENDING")],
                        comments=[{"id": "IC_9", "author": None, "body": "x"}]))
        self.assertEqual(self.lines(self.run_watch("--once")), ["comment by ghost"])

    # W21.3 merged or closed prints one line and exits 0

    def test_W21_3_merged_prints_one_line_and_exits_0(self):
        self.fake_gh(pr(state="MERGED"))
        result = self.run_watch("--interval", "0.01")
        self.assertEqual((result.returncode, self.lines(result)), (0, ["pr merged"]))
        self.assertEqual(len(self.calls()), 1)

    def test_W21_3_closed_prints_one_line_and_exits_0(self):
        self.fake_gh(pr(), pr(state="CLOSED"))
        result = self.run_watch("--interval", "0.01")
        self.assertEqual((result.returncode, self.lines(result)), (0, ["pr closed"]))
        self.assertEqual(len(self.calls()), 2)

    def test_W21_3_events_before_the_close_are_printed_first(self):
        self.fake_gh(pr(state="MERGED", checks=[check_run("lint")], reviews=[review("PRR_1", "alice")]))
        result = self.run_watch("--once")
        self.assertEqual((result.returncode, self.lines(result)),
                         (0, ["check lint: success", "review by alice: approved", "pr merged"]))

    # W21.4 a restart that reads the state file reprints nothing already printed

    def test_W21_4_restart_reprints_nothing(self):
        busy = pr(checks=[check_run("lint")], reviews=[review("PRR_1", "alice")],
                  comments=[comment("IC_1", "bob")])
        self.fake_gh(busy)
        self.assertEqual(self.lines(self.run_watch("--once")),
                         ["check lint: success", "review by alice: approved", "comment by bob"])
        self.assertTrue(self.state.exists())
        self.fake_gh(busy)  # a new process, same state file
        self.assertEqual(self.run_watch("--interval", "0.01", "--once").stdout, "")
        later = json.loads(busy["stdout"])
        later["comments"].append(comment("IC_2", "erin"))
        self.fake_gh({"stdout": json.dumps(later)})
        self.assertEqual(self.lines(self.run_watch("--once")), ["comment by erin"])

    def test_W21_4_restart_after_merge_reprints_nothing_and_exits_0(self):
        self.fake_gh(pr(state="MERGED"))
        self.assertEqual(self.lines(self.run_watch("--once")), ["pr merged"])
        again = self.run_watch("--interval", "0.01")
        self.assertEqual((again.returncode, again.stdout), (0, ""))

    def test_W21_4_state_file_of_another_pr_is_refused(self):
        self.state.write_text(json.dumps({"repo": "octo/widgets", "pr": 8, "seen": []}))
        self.fake_gh(pr(checks=[check_run("lint")]))
        result = self.run_watch("--once")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_W21_4_unreadable_state_file_is_one_error_line(self):
        self.state.write_text("{not json")
        self.fake_gh(pr())
        result = self.run_watch("--once")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_W21_4_default_state_file_lives_under_xdg_state_home(self):
        self.fake_gh(pr(checks=[check_run("lint")]))
        env_home = self.dir / "xdg"
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                   XDG_STATE_HOME=str(env_home))
        cmd = [sys.executable, str(SCRIPT), "--repo", "octo/widgets", "--pr", "7", "--once"]
        first = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        second = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(first.stdout.splitlines(), ["check lint: success"])
        self.assertEqual(second.stdout, "")
        self.assertTrue((env_home / "pr_watch" / "octo-widgets-7.json").exists())

    # W21.5 a missing or signed-out gh gives one error line and exit 1, no traceback

    def assert_one_error(self, result, *words):
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        lines = result.stderr.strip().splitlines()
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        for word in words:
            self.assertIn(word, lines[0])

    def test_W21_5_missing_gh(self):
        result = self.run_watch("--once", path=str(self.bin))  # bin is empty: no gh anywhere
        self.assert_one_error(result, "gh", "not found")

    def test_W21_5_signed_out_gh(self):
        self.fake_gh({"code": 4, "stderr": "To get started with GitHub CLI, please run:  gh auth login\n"
                                           "Alternatively, populate the GH_TOKEN environment variable.\n"})
        self.assert_one_error(self.run_watch("--once"), "gh auth login")

    def test_W21_5_signed_out_gh_in_loop_mode(self):
        self.fake_gh({"code": 1, "stderr": "HTTP 401: Bad credentials (https://api.github.com/graphql)\n"
                                           "Try authenticating with:  gh auth login\n"})
        self.assert_one_error(self.run_watch("--interval", "0.01"), "gh auth login")

    def test_W21_5_other_gh_failure_and_bad_json(self):
        self.fake_gh({"code": 1, "stderr": "GraphQL: Could not resolve to a PullRequest with the number of 7.\n"})
        self.assert_one_error(self.run_watch("--once"), "Could not resolve")
        self.fake_gh({"stdout": "not json"})
        self.assert_one_error(self.run_watch("--once"), "JSON")


if __name__ == "__main__":
    unittest.main()

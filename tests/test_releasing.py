"""Tests for skills/releasing/scripts/release_plan.py (work item W5).

Run: python3 -m unittest tests.test_releasing -v

Every case builds its own temporary git repository with its own identity. Expected values are
written by hand from the promotion model, not taken from the script.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "releasing"
SCRIPT = SKILL / "scripts" / "release_plan.py"
sys.path.insert(0, str(ROOT / "tests"))

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Release Test", "GIT_AUTHOR_EMAIL": "release-test@example.com",
    "GIT_COMMITTER_NAME": "Release Test", "GIT_COMMITTER_EMAIL": "release-test@example.com",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
}
SNAPSHOT_CHECKS = ("--check", "full-suite=pass", "--check", "source-ci=pass")


class Repo:
    """A throwaway repository: dev (squash commits), rolling (snapshot merges), main (releases)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(exist_ok=True)
        self.git("init", "-q", "-b", "dev")
        self.commit("chore: initial layout")
        self.git("branch", "rolling")
        self.git("branch", "main")
        self.git("tag", "-a", "v0.1.0", "-m", "First release", "main")
        self.git("tag", "rolling-2026-10-31", "rolling")
        self.one = self.commit("feat: add the first skill (#1)")
        self.snapshot("Rolling snapshot: 2026-11-01", "rolling-2026-11-01")
        self.git("switch", "-q", "dev")
        self.two = self.commit("feat: add user guides (#2)")
        self.three = self.commit("fix: correct the guide links (#3)")

    def git(self, *args):
        run = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                             cwd=self.path, env=ENV, capture_output=True, text=True)
        if run.returncode:
            raise AssertionError(f"git {' '.join(args)}: {run.stderr}")
        return run.stdout.strip()

    def commit(self, subject):
        self.count = getattr(self, "count", -1) + 1
        name = f"f{self.count}.txt"  # one new file per commit, so merges never conflict
        (self.path / name).write_text(subject + "\n")
        self.git("add", name)
        self.git("commit", "-q", "-m", subject)
        return self.git("rev-parse", "HEAD")

    def snapshot(self, message, tag):
        """Promote dev to rolling the way this repository does: --no-ff merge plus a light tag."""
        self.git("switch", "-q", "rolling")
        self.git("merge", "-q", "--no-ff", "-m", message, "dev")
        self.git("tag", tag)
        self.git("switch", "-q", "dev")

    def refs(self):
        return self.git("show-ref", "--head")


def run(*args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=ENV)
    return proc.returncode, proc.stdout + proc.stderr


def digest(output):
    lines = [l for l in output.splitlines() if l.startswith("Plan digest: ")]
    assert len(lines) == 1, output
    return lines[0].split(": ", 1)[1].strip()


class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name) / "repo")
        self.before = self.repo.refs()

    def tearDown(self):
        # W5.10: no command in any case changes a ref.
        self.assertEqual(self.repo.refs(), self.before)
        self.tmp.cleanup()

    def plan(self, *args):
        return run("plan", "--repo", str(self.repo.path), *args)

    def snapshot_plan(self, *args):
        return self.plan("--from", "dev", "--to", "rolling", "--kind", "rolling", *args)

    def test_w5_1_rolling_snapshot_plan(self):
        code, out = self.snapshot_plan("--date", "2026-11-02", "--label", "MDD user guides",
                                       "--slug", "mdd-guides")
        self.assertEqual(code, 0, out)
        self.assertIn('Merge message: "Rolling snapshot: 2026-11-02 MDD user guides"', out)
        self.assertIn("Tag: rolling-2026-11-02-mdd-guides (lightweight)", out)
        self.assertIn("--no-ff", out)
        self.assertIn("Last snapshot: rolling-2026-11-01", out)
        self.assertIn("- feat: add user guides (#2)", out)
        self.assertIn("- fix: correct the guide links (#3)", out)
        self.assertNotIn("add the first skill (#1)", out)  # promoted by the last snapshot
        self.assertIn(f"Commits to promote (2):", out)
        self.assertIn(self.repo.two[:7], out)
        self.assertRegex(digest(out), r"^[0-9a-f]{64}$")

    def test_w5_1_label_and_date_forms(self):
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 0, out)
        self.assertIn('Merge message: "Rolling snapshot: 2026-11-02"', out)
        self.assertIn("Tag: rolling-2026-11-02 (lightweight)", out)
        code, out = self.snapshot_plan("--date", "2026-11-02", "--label", "Docs refresh")
        self.assertIn("Tag: rolling-2026-11-02-docs-refresh (lightweight)", out)
        code, out = self.snapshot_plan("--date", "2 Nov 2026")
        self.assertEqual(code, 1, out)
        self.assertIn("YYYY-MM-DD", out)

    def test_w5_1b_same_day_snapshot_needs_a_new_label(self):
        code, out = self.snapshot_plan("--date", "2026-11-01")
        self.assertEqual(code, 1, out)
        self.assertIn("rolling-2026-11-01 already exists", out)
        self.assertIn("--label", out)
        self.repo.git("tag", "rolling-2026-11-01-guides", "dev")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-01", "--label", "Guides")
        self.assertEqual(code, 1, out)
        self.assertIn("tag rolling-2026-11-01-guides already exists", out)
        code, out = self.snapshot_plan("--date", "2026-11-01", "--label", "Second batch")
        self.assertEqual(code, 0, out)
        self.assertIn("Tag: rolling-2026-11-01-second-batch (lightweight)", out)

    def stable(self, version, *args):
        return self.plan("--from", "rolling", "--to", "main", "--kind", "stable", "--version", version, *args)

    def test_w5_2_stable_release_plan(self):
        code, out = self.stable("0.2.0")
        self.assertEqual(code, 0, out)
        self.assertIn('Merge message: "Release: v0.2.0"', out)
        self.assertIn("Tag: v0.2.0 (annotated)", out)
        self.assertIn("--no-ff", out)
        self.assertIn("git tag -a v0.2.0", out)
        self.assertIn("Last release: v0.1.0", out)
        self.assertIn("- feat: add the first skill (#1)", out)
        self.assertNotIn("add user guides (#2)", out)  # on dev, not yet on rolling
        self.assertIn("release-decision", out)

    def test_w5_3_version_must_be_greater_than_the_last_tag(self):
        for version in ("0.1.0", "0.0.9", "0.1"):
            with self.subTest(version=version):
                code, out = self.stable(version)
                self.assertEqual(code, 1, out)
        code, out = self.stable("0.0.9")
        self.assertIn("v0.0.9 is not greater than the last release v0.1.0", out)
        self.assertIn("v0.1.0 is not greater than the last release v0.1.0", self.stable("0.1.0")[1])
        # Numeric, not text, order: v0.10.0 is greater than v0.9.0.
        self.repo.git("tag", "-a", "v0.9.0", "-m", "x", "main")
        self.assertEqual(self.stable("0.10.0")[0], 0)
        self.assertEqual(self.stable("0.8.5")[0], 1)
        self.repo.git("tag", "-d", "v0.9.0")

    def test_w5_4_existing_tag(self):
        code, out = self.stable("0.1.0")
        self.assertEqual(code, 1, out)
        self.assertIn("tag v0.1.0 already exists", out)

    def test_w5_5_dirty_tree(self):
        (self.repo.path / "f0.txt").write_text("changed\n")
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 1, out)
        self.assertIn("working tree", out)
        self.assertNotIn("Plan digest", out)
        (self.repo.path / "f0.txt").write_text("chore: initial layout\n")

    def test_w5_6_earlier_promotion_merges_are_not_missing(self):
        # rolling holds the 2026-11-01 snapshot merge, which dev does not contain.
        self.assertIn("Rolling snapshot", self.repo.git("log", "--format=%s", "dev..rolling"))
        self.assertEqual(self.snapshot_plan("--date", "2026-11-02")[0], 0)
        # main holds no release merge yet; add one and plan a stable release over it.
        self.repo.git("switch", "-q", "main")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Release: v0.1.1", "rolling")
        self.repo.git("tag", "-a", "v0.1.1", "-m", "Patch", "main")
        self.repo.git("switch", "-q", "dev")
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        self.before = self.repo.refs()
        code, out = self.stable("0.2.0")
        self.assertEqual(code, 0, out)
        self.assertIn("- feat: add user guides (#2)", out)
        self.assertNotIn("add the first skill (#1)", out)

    def test_w5_6_target_commits_missing_from_source_are_named(self):
        self.repo.git("switch", "-q", "rolling")
        stray = self.repo.commit("hotfix: patched only on rolling")
        self.repo.git("switch", "-q", "dev")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{stray[:7]} hotfix: patched only on rolling", out)
        self.assertNotIn("Plan digest", out)

    def test_w5_6_merge_from_outside_the_source_is_named(self):
        self.repo.git("switch", "-q", "-c", "side", "main")
        self.repo.commit("feat: side work")
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge side", "side")
        merge = self.repo.git("rev-parse", "HEAD")
        self.repo.git("switch", "-q", "dev")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{merge[:7]} Merge side", out)

    def test_w5_6_reverted_snapshot_merged_back_is_not_missing(self):
        # Rollback by revert (reference/promotion.md): revert the snapshot merge with -m 1 on a
        # branch, merge that branch into rolling with a merge commit, then revert the same diff
        # on dev as one squash commit. The next plan must pass.
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        snapshot = self.repo.git("rev-parse", "rolling")
        self.repo.git("switch", "-q", "-c", "revert-snapshot", "rolling")
        self.repo.git("revert", "--no-edit", "-m", "1", snapshot)
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Roll back rolling-2026-11-02", "revert-snapshot")
        self.repo.git("branch", "-q", "-D", "revert-snapshot")
        self.repo.git("switch", "-q", "dev")
        self.repo.git("rm", "-q", "f2.txt", "f3.txt")  # the same diff as the revert
        self.repo.git("commit", "-q", "-m", "revert: back out #2 and #3 (#4)")
        self.repo.commit("feat: next change (#5)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertIn("- feat: next change (#5)", out)
        # Without the matching revert on dev, the merge and its revert are still named (W5.6).
        self.repo.git("switch", "-q", "-c", "no-revert", "dev~2")
        self.repo.commit("feat: other change (#6)")
        code, out = run("plan", "--repo", str(self.repo.path), "--from", "no-revert", "--to", "rolling",
                        "--kind", "rolling", "--date", "2026-11-03")
        self.repo.git("switch", "-q", "dev")
        self.repo.git("branch", "-q", "-D", "no-revert")
        self.assertEqual(code, 1, out)
        self.assertIn("Roll back rolling-2026-11-02", out)

    def test_w5_6_emergency_cherry_pick_is_not_missing(self):
        # Emergency path: the fix lands on dev first, then is cherry-picked to rolling.
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("cherry-pick", self.repo.three)
        self.repo.git("switch", "-q", "dev")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 0, out)

    def evil_snapshot(self, message, edit):
        """Merge dev into rolling without committing, apply edit, then commit the merge."""
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("merge", "-q", "--no-ff", "--no-commit", "dev")
        edit()
        self.repo.git("commit", "-q", "-m", message)
        merge = self.repo.git("rev-parse", "HEAD")
        self.repo.git("switch", "-q", "dev")
        return merge

    def test_d6_clean_promotion_merge_is_not_named(self):
        # D-6: the setUp snapshot merge (dev into rolling, nothing else) is clean.
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        self.repo.commit("feat: next change (#4)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertIn("- feat: next change (#4)", out)

    def test_d6_merge_with_an_extra_edit_is_named(self):
        # D-6: an evil merge. Its tree differs from a clean merge of its parents, because it
        # also edits f0.txt, a change dev does not have.
        def edit():
            (self.repo.path / "f0.txt").write_text("edited inside the merge\n")
            self.repo.git("add", "f0.txt")
        merge = self.evil_snapshot("Rolling snapshot: 2026-11-02", edit)
        self.repo.commit("feat: next change (#4)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{merge[:7]} Rolling snapshot: 2026-11-02", out)
        self.assertIn("f0.txt", out)
        self.assertNotIn("Plan digest", out)

    def test_d6_merge_with_an_extra_new_file_is_named(self):
        def edit():
            (self.repo.path / "extra.txt").write_text("only on rolling\n")
            self.repo.git("add", "extra.txt")
        # D-6: the merge brings only dev commits, plus a new file of its own.
        merge = self.evil_snapshot("Rolling snapshot: 2026-11-02", edit)
        self.repo.commit("feat: next change (#4)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{merge[:7]} Rolling snapshot: 2026-11-02", out)
        self.assertIn("extra.txt", out)

    def conflicting_promotion(self, resolution):
        """Emergency path, then a promotion whose merge conflicts on f1.txt and is resolved by hand."""
        (self.repo.path / "f1.txt").write_text("fixed\n")
        self.repo.git("commit", "-q", "-am", "fix: urgent (#4)")
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("cherry-pick", "-x", "dev")
        self.repo.git("switch", "-q", "dev")
        (self.repo.path / "f1.txt").write_text("fixed again\n")
        self.repo.git("commit", "-q", "-am", "fix: follow-up (#5)")
        self.repo.git("switch", "-q", "rolling")
        merged = subprocess.run(["git", "-c", "commit.gpgsign=false", "merge", "-q", "--no-ff", "dev"],
                                cwd=self.repo.path, env=ENV, capture_output=True, text=True)
        self.assertNotEqual(merged.returncode, 0, "the promotion merge should conflict on f1.txt")
        (self.repo.path / "f1.txt").write_text(resolution)
        self.repo.git("add", "f1.txt")
        self.repo.git("commit", "-q", "-m", "Rolling snapshot: 2026-11-02")
        merge = self.repo.git("rev-parse", "HEAD")
        self.repo.git("switch", "-q", "dev")
        self.repo.commit("feat: next change (#6)")
        self.before = self.repo.refs()
        return merge

    def test_d6_conflict_resolved_to_the_source_side_is_not_named(self):
        # D-6: taking dev's version of the conflicting file adds nothing of the merge's own.
        # D-21: the emergency cherry-pick of "fix: urgent (#4)" on rolling is not named either,
        # although the later promotion already brought its twin on dev into rolling.
        merge = self.conflicting_promotion("fixed again\n")
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertNotIn(f"{merge[:7]} Rolling snapshot: 2026-11-02", out)  # it is the rollback point
        self.assertNotIn("changes of its own", out)
        self.assertNotIn("fix: urgent (#4)", out)
        self.assertIn("- feat: next change (#6)", out)

    def test_d21_cherry_pick_after_a_later_promotion_is_not_missing(self):
        # D-21: emergency cherry-pick of #3 to rolling, then a normal promotion of dev (which
        # holds the original #3), then a new commit on dev. The cherry-pick is not missing.
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("cherry-pick", "-x", self.repo.three)
        self.repo.git("switch", "-q", "dev")
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        self.repo.commit("feat: next change (#4)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertNotIn("missing", out)
        self.assertIn("- feat: next change (#4)", out)

    def test_d21_rollback_revert_after_its_twin_is_promoted_is_not_missing(self):
        # D-21: rollback by revert (reference/promotion.md), the same revert on dev, a promotion
        # that brings the dev revert into rolling, then a new commit on dev.
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        snapshot = self.repo.git("rev-parse", "rolling")
        self.repo.git("switch", "-q", "-c", "revert-snapshot", "rolling")
        self.repo.git("revert", "--no-edit", "-m", "1", snapshot)
        revert = self.repo.git("rev-parse", "HEAD")
        self.repo.git("switch", "-q", "rolling")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Roll back rolling-2026-11-02", "revert-snapshot")
        self.repo.git("branch", "-q", "-D", "revert-snapshot")
        self.repo.git("switch", "-q", "dev")
        self.repo.git("rm", "-q", "f2.txt", "f3.txt")  # the same diff as the revert
        self.repo.git("commit", "-q", "-m", "revert: back out #2 and #3 (#4)")
        self.repo.snapshot("Rolling snapshot: 2026-11-03", "rolling-2026-11-03")
        self.repo.commit("feat: next change (#5)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-04")
        self.assertEqual(code, 0, out)
        self.assertNotIn(revert[:7], out)
        self.assertIn("- feat: next change (#5)", out)

    def test_d21_target_only_commit_after_a_promotion_is_still_named(self):
        # D-21 control: a commit made only on rolling, with no twin on dev, stays named after
        # later promotions.
        self.repo.git("switch", "-q", "rolling")
        stray = self.repo.commit("hotfix: patched only on rolling")
        self.repo.git("switch", "-q", "dev")
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        self.repo.commit("feat: next change (#5)")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{stray[:7]} hotfix: patched only on rolling", out)
        self.assertNotIn("Plan digest", out)

    def test_d6_conflict_resolved_with_new_content_is_named(self):
        merge = self.conflicting_promotion("fixed again, plus a rolling-only tweak\n")
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 1, out)
        self.assertIn(f"{merge[:7]} Rolling snapshot: 2026-11-02", out)
        self.assertIn("f1.txt", out)

    def test_w5_9_nothing_to_promote(self):
        self.repo.snapshot("Rolling snapshot: 2026-11-02", "rolling-2026-11-02")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-03")
        self.assertEqual(code, 0, out)
        self.assertIn("nothing to promote", out)
        self.assertNotIn("Plan digest", out)

    def test_remote_tracking_branch_wins_over_a_missing_local_branch(self):
        # Like this repository: only origin/dev and origin/rolling exist, no local branches.
        with tempfile.TemporaryDirectory() as clone:
            subprocess.run(["git", "clone", "-q", "-b", "main", str(self.repo.path), clone],
                           env=ENV, check=True, capture_output=True)
            # Nit 3 / W5.10: the remote moves after the clone; a planner that fetched would
            # change the clone's origin/dev and fail the comparison below.
            self.repo.commit("feat: landed after the clone (#4)")
            self.before = self.repo.refs()
            clone_refs = lambda: subprocess.run(["git", "-C", clone, "show-ref", "--head"], env=ENV,
                                                capture_output=True, text=True, check=True).stdout
            before = clone_refs()
            code, out = run("plan", "--repo", clone, "--from", "dev", "--to", "rolling",
                            "--kind", "rolling", "--date", "2026-11-02")
            self.assertEqual(clone_refs(), before)
            self.assertEqual(code, 0, out)
            self.assertIn("origin/dev", out)
            self.assertIn("- fix: correct the guide links (#3)", out)
            self.assertNotIn("landed after the clone", out)

    def test_nit4_unlabelled_snapshot_after_a_labelled_one_needs_a_label(self):
        self.repo.git("tag", "rolling-2026-11-02-early", "rolling")
        self.before = self.repo.refs()
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 1, out)
        self.assertIn("rolling-2026-11-02-early", out)
        self.assertIn("--label", out)
        self.assertEqual(self.snapshot_plan("--date", "2026-11-02", "--label", "Late")[0], 0)

    def test_nit2_every_problem_is_reported(self):
        (self.repo.path / "f0.txt").write_text("changed\n")
        code, out = self.snapshot_plan("--date", "2 Nov 2026", "--version", "1.0.0")
        self.assertEqual(code, 1, out)
        self.assertIn("working tree", out)
        self.assertIn("YYYY-MM-DD", out)
        self.assertIn("--version is for --kind stable", out)
        code, out = self.stable("1.0", "--label", "x")
        self.assertEqual(code, 1, out)
        self.assertIn("x.y.z", out)
        self.assertIn("--label is for --kind rolling", out)
        self.assertIn("working tree", out)
        (self.repo.path / "f0.txt").write_text("chore: initial layout\n")

    def config(self, settings):
        path = Path(self.tmp.name) / "releasing.json"  # outside the checkout
        path.write_text(settings if isinstance(settings, str) else json.dumps(settings))
        return ("--config", str(path))

    def test_nit1_config_types_and_placeholders(self):
        code, out = self.snapshot_plan("--date", "2026-11-02",
                                       *self.config({"checks": {"rolling": {"full-suite": "green at {nope}"}}}))
        self.assertEqual(code, 1, out)
        self.assertIn("{nope}", out)
        self.assertNotIn("Traceback", out)
        code, out = self.snapshot_plan("--date", "2026-11-02", *self.config(
            {"remote": 5, "rolling_message": "", "checks": {"rolling": ["full-suite"], "nightly": {}}}))
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)
        for key in ("remote", "rolling_message", "checks.rolling", "checks.nightly"):
            self.assertIn(key, out)
        self.assertGreaterEqual(len(out.splitlines()), 4)
        code, out = self.snapshot_plan("--date", "2026-11-02", *self.config(
            {"checks": {"rolling": {"full-suite": "green at {from"}}}))
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)
        code, out = self.snapshot_plan("--date", "2026-11-02", *self.config("{not json"))
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)

    def test_nit1_unsafe_tag_names(self):
        code, out = self.snapshot_plan("--date", "2026-11-02", *self.config({"rolling_tag": "rel ease"}))
        self.assertEqual(code, 1, out)
        self.assertIn("'rel ease-2026-11-02' is not a valid tag name", out)
        code, out = self.snapshot_plan("--date", "2026-11-02", *self.config({"rolling_tag": "a..b"}))
        self.assertEqual(code, 1, out)
        # A valid ref name can still hold shell characters: printed commands quote it.
        code, out = self.stable("0.2.0", *self.config({"stable_tag": "r$(id)-", "remote": "my remote"}))
        self.assertEqual(code, 0, out)
        self.assertIn("git tag -a 'r$(id)-0.2.0' -F", out)
        self.repo.git("remote", "add", "up", str(self.repo.path))
        self.repo.git("fetch", "-q", "up")
        self.before = self.repo.refs()
        code, out = self.stable("0.2.0", *self.config({"stable_tag": "r$(id)-", "remote": "up"}))
        self.assertEqual(code, 0, out)
        self.assertIn("git push --atomic up HEAD:refs/heads/main 'refs/tags/r$(id)-0.2.0'", out)

    def test_nit5_next_line_names_the_script_inside_the_skill(self):
        code, out = self.snapshot_plan("--date", "2026-11-02")
        self.assertEqual(code, 0, out)
        self.assertIn("Next: python3 <skill>/scripts/release_plan.py go ", out)
        # Major 1 (round 3): the Next line must not report checks nobody ran.
        nxt = next(l for l in out.splitlines() if l.startswith("Next: "))
        self.assertNotIn("=pass", nxt)
        self.assertIn("--check full-suite=<pass|fail> --check source-ci=<pass|fail>", nxt)
        code, out = self.stable("0.2.0")
        nxt = next(l for l in out.splitlines() if l.startswith("Next: "))
        self.assertNotIn("=pass", nxt)
        self.assertIn("--check release-decision=<pass|fail>", nxt)


class Go(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(Path(self.tmp.name) / "repo")
        self.args = ("--repo", str(self.repo.path), "--from", "dev", "--to", "rolling",
                     "--kind", "rolling", "--date", "2026-11-02")
        code, out = run("plan", *self.args)
        assert code == 0, out
        self.digest = digest(out)
        self.rolling = self.repo.git("rev-parse", "rolling")
        self.rollback = Path(self.tmp.name) / "rollback.md"
        self.rollback.write_text(
            f"Rollback: reset rolling to {self.rolling[:12]} with a reviewed force-with-lease push,\n"
            "and delete the tag rolling-2026-11-02 on the remote.\n")
        self.before = self.repo.refs()

    def tearDown(self):
        self.assertEqual(self.repo.refs(), self.before)  # W5.10
        self.tmp.cleanup()

    def go(self, *extra, rollback=None, plan_digest=None):
        return run("go", *self.args, "--plan-digest", plan_digest or self.digest,
                   "--rollback", str(rollback or self.rollback), *extra)

    def test_go_when_everything_holds(self):
        code, out = self.go(*SNAPSHOT_CHECKS)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines()[0], "GO")
        self.assertIn(self.digest, out)

    def test_w5_7_no_go_without_a_rollback_plan(self):
        code, out = self.go(*SNAPSHOT_CHECKS, rollback=Path(self.tmp.name) / "missing.md")
        self.assertEqual(code, 1, out)
        self.assertEqual(out.splitlines()[0], "NO-GO")
        self.assertIn("rollback", out)
        empty = Path(self.tmp.name) / "empty.md"
        empty.write_text("  \n")
        code, out = self.go(*SNAPSHOT_CHECKS, rollback=empty)
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        vague = Path(self.tmp.name) / "vague.md"
        vague.write_text("Revert if something breaks.\n")
        code, out = self.go(*SNAPSHOT_CHECKS, rollback=vague)
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        self.assertIn(self.rolling[:7], out)  # tells the writer which commit to name

    def test_w5_8_no_go_with_a_failed_or_missing_check(self):
        code, out = self.go("--check", "full-suite=fail", "--check", "source-ci=pass")
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        self.assertIn("full-suite failed", out)
        code, out = self.go("--check", "full-suite=pass")
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        self.assertIn("source-ci not reported", out)
        code, out = self.go(*SNAPSHOT_CHECKS, "--check", "smoke=fail")
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        code, out = self.go(*SNAPSHOT_CHECKS, "--check", "smoke")
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))

    def test_major1_rollback_plan_inside_the_checkout_is_named(self):
        inside = self.repo.path / "rollback.md"
        inside.write_text(self.rollback.read_text())
        code, out = self.go(*SNAPSHOT_CHECKS, rollback=inside)
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"), out)
        self.assertIn("working tree", out)
        self.assertIn("rollback.md", out)
        self.assertIn("outside the checkout", out)
        self.assertIn("decision brief", out)
        inside.unlink()
        self.assertEqual(self.go(*SNAPSHOT_CHECKS)[0], 0)  # the same plan, written outside: GO

    def test_no_go_when_the_plan_changed(self):
        code, out = self.go(*SNAPSHOT_CHECKS, plan_digest="0" * 64)
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))
        self.assertIn("digest", out)
        # dev moves after the plan: the approved digest no longer matches.
        self.repo.commit("feat: late change (#4)")
        self.before = self.repo.refs()
        code, out = self.go(*SNAPSHOT_CHECKS)
        self.assertEqual((code, out.splitlines()[0]), (1, "NO-GO"))


class Skill(unittest.TestCase):
    def test_help_exits_zero(self):
        for args in (["--help"], ["plan", "--help"], ["go", "--help"]):
            with self.subTest(args=args):
                self.assertEqual(run(*args)[0], 0)

    def test_x1_promotion_is_an_outside_effect(self):
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        self.assertIn("outside effect", text)
        self.assertIn("pre-authorizes that exact effect", text)
        self.assertIn("approves the exact plan digest", text)

    def steps(self):
        """Numbered steps under '## Run a promotion' as {title: (number, body)}."""
        text = (SKILL / "SKILL.md").read_text()
        section = text.split("## Run a promotion", 1)[1].split("\n## ", 1)[0]
        parts = re.split(r"^(\d+)\. \*\*(.+?)\*\*", section, flags=re.M)
        return {parts[i + 1].rstrip("."): (int(parts[i]), parts[i + 2]) for i in range(1, len(parts), 3)}

    def test_major1_documented_rollback_path_is_outside_the_checkout(self):
        text = (SKILL / "SKILL.md").read_text()
        paths = re.findall(r"--rollback (\S+)", text)
        self.assertTrue(paths)
        for path in paths:
            self.assertTrue(path.startswith(("../", "/")), path)
        self.assertIn("outside the checkout", " ".join(text.split()))

    def test_major2_stable_decision_comes_before_go(self):
        steps = self.steps()
        decision = next(t for t in steps if "decision" in t.lower())
        go = next(t for t in steps if " go " in steps[t][1])
        self.assertLess(steps[decision][0], steps[go][0])
        body = " ".join(steps[decision][1].split())
        for phrase in ("briefing-decisions", "release-decision=pass", "plan digest",
                       "Never report `release-decision=pass` before", "outside the checkout"):
            self.assertIn(phrase, body)

    def test_nit5_skill_calls_the_script_by_its_skill_path(self):
        text = (SKILL / "SKILL.md").read_text()
        calls = re.findall(r"python3 (\S*release_plan\.py)", text)
        self.assertTrue(calls)
        self.assertEqual(set(calls), {"<skill>/scripts/release_plan.py"})

    def test_anatomy_in_item_mode(self):
        import test_skill_anatomy
        self.assertEqual(test_skill_anatomy.problems("releasing", item=True), [])


if __name__ == "__main__":
    unittest.main()

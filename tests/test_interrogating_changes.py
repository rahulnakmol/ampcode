"""Tests for skills/interrogating-changes: review_ledger.py (W3) and floor_guard.py (W4).

Run: python3 -m unittest tests.test_interrogating_changes -v

Each test builds its own git repository with its own identity, so it needs no git setup.
Expected patch IDs come from git itself (`git diff base...head | git patch-id --verbatim`, from
the merge-base), never from the script under test.
"""

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "interrogating-changes"
LEDGER = SKILL / "scripts" / "review_ledger.py"
GUARD = SKILL / "scripts" / "floor_guard.py"

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "author@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}

BASE_APP = '''def withdraw(balance, amount):
    if amount > balance:
        raise ValueError("insufficient funds")
    return balance - amount


def fee(amount):
    return amount * 0.01
'''

# The change deletes the balance guard (a regression). The float fee was already there.
HEAD_APP = '''def withdraw(balance, amount):
    return balance - amount


def fee(amount):
    return amount * 0.01
'''

# Lines (by hand): HEAD_APP line 1 is "def withdraw", line 2 "return balance - amount",
# line 6 "return amount * 0.01".
REGRESSION = {
    "id": "F1", "lens": "correctness", "severity": "Major", "origin": "regression",
    "location": "app.py:1-2", "quote": "def withdraw(balance, amount):\n    return balance - amount",
    "problem": "withdraw no longer refuses an amount above the balance",
    "evidence": "run: python3 -c 'from app import withdraw; print(withdraw(5, 10))' printed -5",
    "status": "open",
}
PRE_EXISTING = {
    "id": "F2", "lens": "correctness", "severity": "Nit", "origin": "pre-existing",
    "location": "app.py:6", "quote": "return amount * 0.01",
    "problem": "fee uses a float for money",
    "evidence": "read: app.py:6 at base and head; no caller rounds the result",
    "status": "open",
}


def git(repo, *args, stdin=None):
    run = subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=ENV,
                         input=stdin, capture_output=True, text=True, check=True)
    return run.stdout


def patch_id(repo, base, head):
    diff = git(repo, "diff", f"{base}...{head}")
    return git(repo, "patch-id", "--verbatim", stdin=diff).split()[0]


def commit(repo, text, message):
    """Commit app.py with text on top of the current branch; returns the new head."""
    (repo / "app.py").write_text(text)
    git(repo, "commit", "-q", "-am", message)
    return git(repo, "rev-parse", "HEAD").strip()


def make_repo(tmp):
    """A repository with a base commit and a head commit; returns (repo, base, head)."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "app.py").write_text(BASE_APP)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD").strip()
    (repo / "app.py").write_text(HEAD_APP)
    git(repo, "commit", "-q", "-am", "remove guard")
    head = git(repo, "rev-parse", "HEAD").strip()
    return repo, base, head


MODELS = {"implementers": [{"model": "anthropic/claude-opus-5-5", "source": "get_thread_status T-impl"}],
          "reviewer": {"model": "openai/gpt-6-astra", "source": "get_thread_status T-review"}}


def round_(repo, base, head, findings, number=1, **extra):
    return {"round": number, "base": base, "head": head, "patch_id": patch_id(repo, base, head),
            "scope": ["app.py"], "findings": copy.deepcopy(findings), **extra}


def run(script, *args, stdin=None):
    return subprocess.run([sys.executable, str(script), *args], env=ENV, input=stdin,
                          capture_output=True, text=True, timeout=60)


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo, self.base, self.head = make_repo(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, ledger):
        if isinstance(ledger, dict) and "rounds" in ledger:
            ledger.setdefault("models", copy.deepcopy(MODELS))
        path = Path(self.tmp.name) / "ledger.json"
        path.write_text(json.dumps(ledger, indent=2))
        return str(path)

    def ledger(self, findings=(REGRESSION, PRE_EXISTING), **extra):
        return {"rounds": [round_(self.repo, self.base, self.head, list(findings), **extra)]}

    def check(self, ledger):
        return run(LEDGER, "check", self.write(ledger), "--repo", str(self.repo))

    def verdict(self, ledger=None, head=None):
        args = ["verdict", "--repo", str(self.repo), "--base", self.base, "--head", head or self.head]
        if ledger is not None:
            args += ["--ledger", self.write(ledger)]
        return run(LEDGER, *args)

    def assertFails(self, result, *needles):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for needle in needles:
            self.assertIn(needle, result.stdout)


class Check(LedgerCase):
    def test_complete_ledger_passes(self):
        result = self.check(self.ledger())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "pass")

    def test_l10_reviewer_on_an_implementer_model_fails(self):
        ledger = self.ledger()
        ledger["models"] = copy.deepcopy(MODELS)
        ledger["models"]["implementers"].append({"model": "OpenAI/GPT-6-Astra ", "source": "T-child"})
        self.assertFails(self.check(ledger), "L10", "openai/gpt-6-astra")
        ledger["models"]["implementers"][-1]["model"] = "openai / gpt-6-astra"
        self.assertFails(self.check(ledger), "L10")

    def test_l10_models_need_a_source(self):
        ledger = self.ledger()
        ledger["models"] = {"implementers": [{"model": "anthropic/claude-opus-5-5"}],
                            "reviewer": {"model": "openai/gpt-6-astra", "source": " "}}
        self.assertFails(self.check(ledger), "implementers[1]", "models.reviewer")

    def test_l10_missing_models_give_no_verdict(self):
        ledger = self.ledger([])
        ledger["models"] = {}
        self.assertFails(self.verdict(ledger), "L10", "ledger invalid")

    def test_w3_1_missing_field_is_named(self):
        for field in ("location", "quote", "severity", "lens"):
            with self.subTest(field=field):
                finding = dict(REGRESSION)
                del finding[field]
                self.assertFails(self.check(self.ledger([finding])), "F1", repr(field))

    def test_w3_2_quote_not_at_head_is_not_proven(self):
        finding = dict(REGRESSION, quote="if amount > balance:", location="app.py:2")
        self.assertFails(self.check(self.ledger([finding])), "F1", "not proven")

    def test_w3_3_regression_whose_quote_exists_at_base(self):
        finding = dict(PRE_EXISTING, origin="regression")
        self.assertFails(self.check(self.ledger([finding])), "F2", "unchanged since base")

    def test_w3_4_pre_existing_whose_quote_is_not_at_base(self):
        finding = dict(REGRESSION, origin="pre-existing", severity="Nit")
        self.assertFails(self.check(self.ledger([finding])), "F1", "changed by this change")

    def test_m2_copied_line_is_a_regression_where_it_was_added(self):
        # Lines by hand: HEAD_APP has 6 lines; the copy adds 2 blank lines, then
        # line 9 "def fee_copy(amount):" and line 10 "    return amount * 0.01".
        copy_head = commit(self.repo, HEAD_APP + "\n\ndef fee_copy(amount):\n    return amount * 0.01\n", "copy")
        copied = dict(PRE_EXISTING, location="app.py:10", status="declined")
        ledger = {"rounds": [round_(self.repo, self.base, copy_head, [copied])]}
        self.assertFails(self.check(ledger), "F2", "changed by this change")
        ledger["rounds"][0]["findings"][0]["origin"] = "regression"
        self.assertEqual(self.check(ledger).returncode, 0, self.check(ledger).stdout)
        original = {"rounds": [round_(self.repo, self.base, copy_head, [PRE_EXISTING])]}
        self.assertEqual(self.check(original).returncode, 0, self.check(original).stdout)

    def test_b1_fixed_regression_recorded_in_a_later_round(self):
        # Round 2's head restores the guard and adds a test helper, so base..h2 is not empty.
        h2 = commit(self.repo, BASE_APP + "\n\ndef zero():\n    return 0\n", "restore guard")
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], 1),
                  round_(self.repo, self.base, h2, [dict(REGRESSION, status="fixed")], 2)]
        result = self.check({"rounds": rounds})
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.strip(), "pass")
        verdict = self.verdict({"rounds": rounds}, head=h2)
        self.assertEqual(verdict.returncode, 0, verdict.stdout)
        self.assertIn("verdict: pass", verdict.stdout)

    def test_b3_four_rounds_with_three_failed_need_no_disposition(self):
        rounds = [round_(self.repo, self.base, self.head, [], 1)]
        rounds += [round_(self.repo, self.base, self.head, [REGRESSION], n) for n in (2, 3, 4)]
        result = self.check({"rounds": rounds})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_w3_7_fourth_failed_round_needs_a_disposition(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], n) for n in (1, 2, 3, 4)]
        self.assertFails(self.check({"rounds": rounds}), "round 4", "disposition")
        rounds[3]["disposition"] = "filed"
        self.assertEqual(self.check({"rounds": rounds}).returncode, 0)
        rounds[3]["disposition"] = "ignored"
        self.assertFails(self.check({"rounds": rounds}), "round 4", "disposition")

    def test_w3_7_three_failed_rounds_need_no_disposition(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], n) for n in (1, 2, 3)]
        self.assertEqual(self.check({"rounds": rounds}).returncode, 0)

    def test_cap_of_five_needs_the_calling_contract(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], n) for n in (1, 2, 3, 4)]
        self.assertFails(self.check({"cap": 5, "rounds": rounds}), "cap")
        result = self.check({"cap": 5, "contract": "mission/contract.md", "rounds": rounds})
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_w3_8_reused_id_with_changed_text(self):
        changed = dict(REGRESSION, problem="withdraw has a style problem")
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], 1),
                  round_(self.repo, self.base, self.head, [changed], 2)]
        self.assertFails(self.check({"rounds": rounds}), "F1", "changed")
        rounds[1]["findings"][0]["problem"] = REGRESSION["problem"]
        self.assertEqual(self.check({"rounds": rounds}).returncode, 0)

    def test_n1_fixed_on_the_same_patch_fails(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], 1),
                  round_(self.repo, self.base, self.head, [dict(REGRESSION, status="fixed")], 2)]
        self.assertFails(self.check({"rounds": rounds}), "round 2 finding F1", "same patch")
        self.assertFails(self.verdict({"rounds": rounds}), "verdict: ledger invalid")

    def test_n6_disposition_before_the_cap_fails(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], 1, disposition="fixed")]
        self.assertFails(self.check({"rounds": rounds}), "round 1", "disposition")
        clean = [round_(self.repo, self.base, self.head, [], 1, disposition="filed")]
        self.assertFails(self.check({"rounds": clean}), "round 1", "disposition")

    def test_n8_findings_without_an_id_are_not_duplicates(self):
        nameless = {k: v for k, v in PRE_EXISTING.items() if k != "id"}
        result = self.check(self.ledger([nameless, dict(nameless)]))
        self.assertFails(result, "missing 'id'")
        self.assertNotIn("L6", result.stdout)

    def test_declining_a_major_regression_fails(self):
        finding = dict(REGRESSION, status="declined")
        self.assertFails(self.check(self.ledger([finding])), "F1", "declined")

    def test_f3_l3_finding_outside_the_scope_fails(self):
        ledger = self.ledger([PRE_EXISTING])
        ledger["rounds"][0]["scope"] = ["README.md"]
        self.assertFails(self.check(ledger), "L3", "F2", "not in the round's scope")

    def test_f3_l7_declined_regression_major_fails_even_when_filed(self):
        filed = dict(REGRESSION, status="declined", filed="https://example.com/issues/1")
        self.assertFails(self.check(self.ledger([filed])), "L7", "F1")
        pre = dict(PRE_EXISTING, severity="Major", status="declined", filed="https://example.com/issues/2")
        result = self.check(self.ledger([pre]))
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_f3_line_after_a_deletion_is_touched(self):
        # The change deletes BASE_APP lines 2-3 (the guard). HEAD_APP line 2,
        # "    return balance - amount", is the line after the gap, so it counts as touched.
        after = dict(REGRESSION, location="app.py:2", quote="return balance - amount")
        result = self.check(self.ledger([after]))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFails(self.check(self.ledger([dict(after, origin="pre-existing", severity="Nit")])),
                         "L5", "changed by this change")

    def test_recorded_patch_id_must_match_the_round(self):
        ledger = self.ledger()
        ledger["rounds"][0]["patch_id"] = "0" * 40
        self.assertFails(self.check(ledger), "patch_id")


class Verdict(LedgerCase):
    def test_w3_5_verdict_prints_the_patch_id(self):
        expected = patch_id(self.repo, self.base, self.head)
        result = self.verdict(self.ledger([PRE_EXISTING]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"patch-id: {expected}", result.stdout)
        self.assertIn("verdict: pass", result.stdout)
        self.assertIn("anthropic/claude-opus-5-5", result.stdout)
        self.assertIn("openai/gpt-6-astra", result.stdout)

    def test_w3_5_new_commit_makes_the_verdict_stale(self):
        ledger = self.ledger([PRE_EXISTING])
        (self.repo / "app.py").write_text(HEAD_APP + "\n\ndef zero():\n    return 0\n")
        git(self.repo, "commit", "-q", "-am", "more")
        new_head = git(self.repo, "rev-parse", "HEAD").strip()
        result = self.verdict(ledger, head=new_head)
        self.assertFails(result, "verdict: stale", f"patch-id: {patch_id(self.repo, self.base, new_head)}")

    def test_b2_same_patch_under_a_new_head_sha_is_not_stale(self):
        ledger = self.ledger([PRE_EXISTING])
        git(self.repo, "commit", "-q", "--amend", "-m", "reworded message")
        amended = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertNotEqual(amended, self.head)
        result = self.verdict(ledger, head=amended)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("verdict: pass", result.stdout)
        self.assertNotIn("stale", result.stdout)

    def test_m1_dedent_only_change_is_stale(self):
        guarded = HEAD_APP + "\n\ndef zero(flag):\n    if flag:\n        return 0\n    return 1\n"
        reviewed = commit(self.repo, guarded, "add zero")
        ledger = {"rounds": [round_(self.repo, self.base, reviewed, [PRE_EXISTING])]}
        dedented = commit(self.repo, guarded.replace("        return 0", "    return 0"), "dedent")
        result = self.verdict(ledger, head=dedented)
        self.assertFails(result, "verdict: stale")

    def test_w3_6_open_blocker_or_major_needs_changes(self):
        for severity in ("Blocker", "Major"):
            with self.subTest(severity=severity):
                result = self.verdict(self.ledger([dict(REGRESSION, severity=severity)]))
                self.assertFails(result, "verdict: changes needed", "F1")

    def test_w3_6_fixed_major_and_open_nit_pass(self):
        # Round 2's head restores the guard (and adds zero(), so base..h2 is not empty).
        h2 = commit(self.repo, BASE_APP + "\n\ndef zero():\n    return 0\n", "restore guard")
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION, PRE_EXISTING], 1),
                  round_(self.repo, self.base, h2, [dict(REGRESSION, status="fixed")], 2)]
        result = self.verdict({"rounds": rounds}, head=h2)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("1 open Nit", result.stdout)
        self.assertIn("verdict: pass", result.stdout)

    def test_w3_6_zero_findings_pass_only_with_files_read(self):
        result = self.verdict(self.ledger([]))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("verdict: pass", result.stdout)
        self.assertIn("1 file read", result.stdout)
        empty = self.ledger([])
        empty["rounds"][0]["scope"] = []
        result = self.verdict(empty)
        self.assertFails(result, "scope")
        self.assertNotIn("verdict: pass", result.stdout)

    def test_w3_6_open_major_from_an_earlier_round_still_counts(self):
        rounds = [round_(self.repo, self.base, self.head, [REGRESSION], 1),
                  round_(self.repo, self.base, self.head, [], 2)]
        self.assertFails(self.verdict({"rounds": rounds}), "verdict: changes needed")

    def test_g1_m1_moved_target_diffs_from_the_merge_base(self):
        # The target branch moves after the change was cut from base: it edits the fee line
        # (HEAD_APP line 6) and adds other.py. Neither is part of the change.
        git(self.repo, "checkout", "-q", "-b", "target", self.base)
        (self.repo / "other.py").write_text("x = 1\n")
        git(self.repo, "add", "other.py")
        target = commit(self.repo, BASE_APP.replace("0.01", "0.02"), "target moves")
        expected = git(self.repo, "patch-id", "--verbatim",
                       stdin=git(self.repo, "diff", f"{target}...{self.head}")).split()[0]
        two_dot = git(self.repo, "patch-id", "--verbatim",
                      stdin=git(self.repo, "diff", f"{target}..{self.head}")).split()[0]
        self.assertNotEqual(expected, two_dot)
        result = run(LEDGER, "verdict", "--repo", str(self.repo), "--base", target, "--head", self.head)
        self.assertFails(result, f"patch-id: {expected}", "not reviewed")
        # Line 6 only the target changed: a correct "pre-existing" label passes L5.
        ledger = {"rounds": [round_(self.repo, target, self.head, [REGRESSION, PRE_EXISTING])]}
        self.assertEqual(ledger["rounds"][0]["patch_id"], expected)
        checked = self.check(ledger)
        self.assertEqual(checked.returncode, 0, checked.stdout)
        wrong = {"rounds": [round_(self.repo, target, self.head, [dict(PRE_EXISTING, origin="regression")])]}
        self.assertFails(self.check(wrong), "F2", "unchanged since base")

    def test_n5_git_failure_is_not_run(self):
        result = self.verdict(head="no-such-ref")
        self.assertFails(result, "git failed", "not run")
        self.assertNotIn("nothing to review", result.stdout)

    def test_without_a_ledger_the_change_is_not_reviewed(self):
        result = self.verdict()
        self.assertFails(result, "verdict: not reviewed", f"patch-id: {patch_id(self.repo, self.base, self.head)}")


GOOD_DIFF = """diff --git a/src/total.py b/src/total.py
--- a/src/total.py
+++ b/src/total.py
@@ -1,2 +1,2 @@
 def total(items):
-    return sum(items)
+    return sum(items, 0)
"""


def diff(path, removed=(), added=(), context=("x = 1",)):
    """A one-hunk unified diff for path; line counts are worked out by hand from the arguments."""
    old = len(context) + len(removed)
    new = len(context) + len(added)
    body = [f" {c}" for c in context] + [f"-{r}" for r in removed] + [f"+{a}" for a in added]
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -1,{old} +1,{new} @@\n" + "\n".join(body) + "\n")


class FloorGuard(unittest.TestCase):
    def guard(self, text, *args):
        return run(GUARD, *args, stdin=text)

    def flags(self, text):
        result = self.guard(text)
        return result, [l for l in result.stdout.splitlines() if re.match(r"^[a-z]+-[0-9a-f]{6}", l)]

    def assertFlags(self, text, needle, count=1):
        result, flags = self.flags(text)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(flags), count, result.stdout)
        self.assertIn(needle, flags[0])

    def assertClean(self, text):
        result = self.guard(text)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "pass")

    def test_w4_1_removed_assertion_without_replacement(self):
        text = diff("tests/test_total.py", removed=["    self.assertEqual(total([1, 2]), 3)"])
        self.assertFlags(text, "assertion removed")
        for line in ("    assert total([]) == 0", "  expect(total([1])).toBe(1);", "    assert_eq!(total(&[]), 0);",
                     "        with self.assertRaises(ValueError):", "    with pytest.raises(ValueError):"):
            with self.subTest(line=line):
                self.assertFlags(diff("tests/t", removed=[line]), "assertion removed")

    def test_added_test_retry_is_flagged(self):
        for line in ("  retries: 2,", "jest.retryTimes(3);", "    this.retries(2);", "addopts = --reruns 3",
                     "@pytest.mark.flaky(reruns=2)", "  test: { retry: 1 },"):
            with self.subTest(line=line):
                self.assertFlags(diff("playwright.config.ts", added=[line]), "test retry added")
        self.assertFlags(diff(".mocharc.json", removed=['  "retries": 0'], added=['  "retries": 2']), "test retry added")
        for path, line in (("Makefile", "\tpytest --retries 2"), (".github/workflows/ci.yml", "  run: npx jest --retry=2"),
                           ("package.json", '  "test": "vitest --retry 3"'), ("pyproject.toml", "reruns = 2"),
                           ("pytest.ini", "addopts = --reruns=1"), ("web/e2e/login.spec.ts", "test.describe.configure({ retries: 2 });")):
            with self.subTest(path=path):
                self.assertFlags(diff(path, added=[line]), "test retry added")
        for line in ("  retries: 0,", "jest.retryTimes(0);", "  # retries: 2,"):
            self.assertClean(diff("playwright.config.ts", added=[line]))
        # A lowered count, and retries in application code or docs, are not test retries.
        self.assertClean(diff("playwright.config.ts", removed=["  retries: 3,"], added=["  retries: 1,"]))
        self.assertFlags(diff("playwright.config.ts", removed=["  retries: 1,"], added=["  retries: 3,"]), "test retry added")
        # A setting newly raised counts even beside an unchanged one on the same line.
        self.assertFlags(diff("package.json", removed=['  "e2e": "playwright test --retry 3 --retries 0"'],
                              added=['  "e2e": "playwright test --retry 3 --retries 2"']), "test retry added")
        self.assertFlags(diff("package.json", removed=['  "e2e": "playwright test --retry 3"'],
                              added=['  "e2e": "playwright test --retries 2"']), "test retry added")
        self.assertFlags(diff("verify.json", removed=['  "e2e": "playwright test",'],
                              added=['  "e2e": "playwright test --retries 2",']), "test retry added")
        for path in ("src/http/client.ts", "docs/retries.md", "skills/x/scripts/floor_guard.py"):
            self.assertClean(diff(path, added=["const policy = { retries: 3 };"]))

    def test_verify_json_set_to_observe_is_flagged(self):
        line = '      "mode": "observe"'
        self.assertFlags(diff("verify.json", removed=['      "mode": "enforce"'], added=[line]), "observe")
        self.assertClean(diff("docs/verify.md", added=[line]))
        # Moving observe from one package to another still sets a package to observe.
        self.assertFlags(diff("verify.json", removed=['  {"name": "api", "mode": "observe"},', '  {"name": "web"},'],
                              added=['  {"name": "api"},', '  {"name": "web", "mode": "observe"},']), "observe")
        self.assertFlags(diff("verify.json", removed=['      "mode": "observe"', '    },', '    {', '      "name": "web",'],
                              added=['    },', '    {', '      "name": "web",', '      "mode": "observe"']), "observe")
        self.assertFlags(diff("verify.json", removed=['  {"name": "api", "mode": "observe"},', '  {"name": "web"},'],
                              added=['  {"name": "web", "mode": "observe"},', '  {"name": "api"},']), "observe")
        # Editing a package that already observes is not setting it to observe.
        self.assertClean(diff("verify.json", removed=['      "mode": "observe"'],
                              added=['      "mode": "observe",', '      "checks": ["ruff check app"]']))
        self.assertClean(diff("verify.json", removed=['  {"name": "api", "mode": "observe"},'],
                              added=['  {"name": "api", "mode": "observe", "checks": ["ruff check"]},']))
        self.assertFlags(diff("packages/verify.json", removed=['    "name": "billing",']), "package removed")
        self.assertClean(diff("verify.json", removed=['    "name": "billing",'], added=['    "name":"billing",']))
        self.assertClean(diff("verify.json", removed=['    "name": "billing",'], added=['    "name": "billing", "e2e": "make e2e",']))

    def test_w4_1_replaced_assertion_is_not_flagged(self):
        self.assertClean(diff("tests/test_total.py", removed=["    self.assertEqual(total([1, 2]), 3)"],
                              added=["    self.assertEqual(total([1, 2, 3]), 6)"]))

    def test_w4_2_added_skip_marker(self):
        for line in ('@pytest.mark.skip(reason="flaky")', "@unittest.skip('later')",
                     "it.skip('adds', () => {", "    t.Skip(\"later\")", "#[ignore]",
                     "test.skipIf(process.platform === 'win32')('adds', () => {",
                     "it.skipIf(isCI)('adds', () => {", "test.concurrent.skip('adds', async () => {",
                     "it.concurrent.skip('adds', async () => {", "fit('adds', () => {",
                     "fdescribe('total', () => {", 'pytestmark = pytest.mark.skip(reason="later")',
                     '@skip("later")'):
            with self.subTest(line=line):
                self.assertFlags(diff("tests/t", added=[line]), "skip marker added")

    def test_w4_2_words_containing_fit_are_not_skip_markers(self):
        for line in ("    return profit(items)", "def fitness(x):", "    model.fit(X, y)",
                     "    def fit(self, X):", "    to = 'qa@skip.example'"):
            with self.subTest(line=line):
                self.assertClean(diff("src/a", added=[line]))

    def test_w4_3_added_checker_silencer(self):
        for line in ("import os  # noqa", "// eslint-disable-next-line no-console", "// @ts-ignore",
                     "x = f()  # type: ignore", "subprocess.call(cmd, shell=True)  # nosec", "x := f() //nolint",
                     "import os  # NOQA", "x := f() // NOLINT", "x = f()  # Type: Ignore"):
            with self.subTest(line=line):
                self.assertFlags(diff("src/a", added=[line]), "checker silencer added")

    def test_w4_3_kept_silencer_on_an_edited_line_is_not_flagged(self):
        self.assertClean(diff("src/a.py", removed=["import os  # noqa: F401"], added=["import sys  # noqa: F401"]))

    def test_w4_4_lowered_number_on_a_bar_key(self):
        cases = [
            ("coverage", "coverage: 80", "coverage: 70"),
            ("threshold", "threshold = 0.9", "threshold = 0.5"),
            ("min", "min: 3", "min: 2"),
            ("minimum", '"minimum": 95,', '"minimum": 90,'),
            ("fail_under", "fail_under = 90", "fail_under = 85"),
            ("fail-under", "run: pytest --cov-fail-under=90", "run: pytest --cov-fail-under=60"),
            ("lines", '"lines": 80,', '"lines": 79,'),
            ("branches", "branches: 75", "branches: 50"),
            ("functions", "functions: 90", "functions: 0"),
            ("statements", '"statements": 100', '"statements": 99.5'),
            ("coverage-threshold", "coverage-threshold: 90", "coverage-threshold: 80"),
            ("min-coverage", "min-coverage: 90", "min-coverage: 80"),
            ("--min-coverage", "run: report --min-coverage 90", "run: report --min-coverage 80"),
            ("min-coverage-overall", "          min-coverage-overall: 80", "          min-coverage-overall: 40"),
        ]
        for key, old, new in cases:
            with self.subTest(key=key):
                self.assertFlags(diff("config/x", removed=[old], added=[new]), "lowered")

    def test_w4_5_ignored_failure_in_ci(self):
        for line in ("        continue-on-error: true", "        run: pytest || true",
                     "        run: bash -c 'pytest || true'", "        run: (pytest ||true)"):
            with self.subTest(line=line):
                self.assertFlags(diff(".github/workflows/ci.yml", added=[line]), "CI failure ignored")

    def test_m3_commented_out_threshold_is_removed(self):
        for path, old, new in (("pyproject.toml", "fail_under = 90", "# fail_under = 90"),
                               (".codecov.yml", "coverage: 80", "# coverage: 80"),
                               ("jest.config.js", '"lines": 80,', '// "lines": 80,')):
            with self.subTest(new=new):
                self.assertFlags(diff(path, removed=[old], added=[new]), "removed")

    def test_m4_empty_input_is_not_run(self):
        for text in ("", "\n", "not a diff\n"):
            with self.subTest(text=text):
                result = self.guard(text)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("no diff on input: not run", result.stdout)
                self.assertNotIn("pass", result.stdout)

    def test_n9_rename_or_binary_only_diff_has_no_text_changes(self):
        rename = "diff --git a/a.py b/b.py\nsimilarity index 100%\nrename from a.py\nrename to b.py\n"
        binary = "diff --git a/x.png b/x.png\nindex 1234567..89abcde 100644\nBinary files a/x.png and b/x.png differ\n"
        for text in (rename, binary):
            with self.subTest(text=text.splitlines()[0]):
                result = self.guard(text)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("no text changes in the diff: not run", result.stdout)

    def test_w4_3_widened_silencer_is_flagged(self):
        for old, new in (("// eslint-disable-next-line no-console", "/* eslint-disable */"),
                         ("import os  # noqa: F401", "import os  # noqa"),
                         ("x = f()  # type: ignore[attr-defined]", "x = f()  # type: ignore")):
            with self.subTest(new=new):
                self.assertFlags(diff("src/a", removed=[old], added=[new]), "checker silencer added or widened")

    def test_w4_3_narrowed_silencer_is_not_flagged(self):
        self.assertClean(diff("src/a.py", removed=["import os  # noqa"], added=["import os  # noqa: F401"]))

    def test_w4_6_raised_threshold_is_not_flagged(self):
        self.assertClean(diff("pyproject.toml", removed=["fail_under = 80"], added=["fail_under = 90"]))
        self.assertClean(diff("jest.config.js", removed=['"lines": 80,'], added=['"lines": 85,']))

    def test_w4_7_clean_diff_passes_from_stdin_and_file(self):
        self.assertClean(GOOD_DIFF)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "change.diff"
            path.write_text(GOOD_DIFF)
            result = run(GUARD, str(path))
            self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"))

    def test_d2_swift_skip_and_removed_xctassert(self):
        for line in ('        throw XCTSkip("later")', '        try XCTSkipIf(isCI, "flaky")',
                     '        try XCTSkipUnless(hasNetwork)'):
            with self.subTest(line=line):
                self.assertFlags(diff("Tests/TotalTests.swift", added=[line]), "skip marker added")
        for line in ("        XCTAssertEqual(total([1, 2]), 3)", "        XCTAssertTrue(isEmpty([]))"):
            with self.subTest(line=line):
                self.assertFlags(diff("Tests/TotalTests.swift", removed=[line]), "assertion removed")
        self.assertClean(diff("Tests/TotalTests.swift", removed=["        XCTAssertEqual(total([1, 2]), 3)"],
                              added=["        XCTAssertEqual(total([1, 2, 3]), 6)"]))

    def test_d2_lowered_jacoco_minimum(self):
        for path, old, new in (("pom.xml", "  <minimum>0.80</minimum>", "  <minimum>0.60</minimum>"),
                               ("pom.xml", "  <minimum>80%</minimum>", "  <minimum>60%</minimum>"),
                               ("build.gradle", "        minimum = 0.80", "        minimum = 0.60"),
                               ("build.gradle.kts", '        minimum = "0.80".toBigDecimal()',
                                '        minimum = "0.60".toBigDecimal()'),
                               ("build.gradle.kts", '        minimum = BigDecimal("0.80")',
                                '        minimum = BigDecimal("0.60")')):
            with self.subTest(path=path, new=new):
                self.assertFlags(diff(path, removed=[old], added=[new]), "minimum lowered from")
        self.assertFlags(diff("pom.xml", removed=["  <minimum>0.80</minimum>"],
                              added=["  <!-- <minimum>0.80</minimum> -->"]), "removed or commented out")
        for path, old, new in (("pom.xml", "  <minimum>0.80</minimum>", "  <minimum>0.90</minimum>"),
                               ("build.gradle.kts", '        minimum = BigDecimal("0.80")',
                                '        minimum = BigDecimal("0.85")')):
            with self.subTest(path=path, raised=new):
                self.assertClean(diff(path, removed=[old], added=[new]))

    def test_d2_assertion_commented_out_with_a_double_dash(self):
        cases = (("tests/total.sql", "SELECT is(total(), 3, 'total');"),
                 ("tests/total.sql", "EXEC tSQLt.AssertEquals 3, @total;"),
                 ("spec/total_spec.lua", "  assert.are.equal(3, total({1, 2}))"),
                 ("test/TotalSpec.hs", '  assertEqual "total" 3 (total [1, 2])'),
                 ("test/TotalSpec.hs", "    total [1, 2] `shouldBe` 3"))
        for path, line in cases:
            with self.subTest(line=line):
                self.assertFlags(diff(path, removed=[line], added=["-- " + line.lstrip()]), "assertion removed")
        self.assertClean(diff("test/TotalSpec.hs", removed=["    total [1, 2] `shouldBe` 3"],
                              added=["    total [1, 2, 3] `shouldBe` 6"]))

    def test_d2_bun_and_vitest_conditional_and_option_skips(self):
        for line in ("test.if(false)('adds', () => {", "describe.if(isMac)('total', () => {",
                     "it.runIf(isCI)('adds', () => {", "test.failing('adds', () => {",
                     "test.skipIf(isCI)('adds', () => {", "test('adds', { skip: true }, () => {",
                     "it('adds', {skip: true}, async () => {"):
            with self.subTest(line=line):
                self.assertFlags(diff("src/total.test.ts", added=[line]), "skip marker added")
        for line in ("const options = { timeout: 2, skipped: true };", "if (test.ifMatch) {"):
            with self.subTest(line=line):
                self.assertClean(diff("src/total.test.ts", added=[line]))

    def test_w4_8_flag_passes_only_with_an_accepted_reason(self):
        text = diff("src/a.py", added=["import os  # noqa"])
        result, flags = self.flags(text)
        flag_id = flags[0].split(":")[0]
        accepted = self.guard(text, "--accept", f"{flag_id}=re-exported for plugins")
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertIn(f"accepted {flag_id}: re-exported for plugins", accepted.stdout)
        self.assertEqual(self.guard(text, "--accept", f"{flag_id}=").returncode, 1)
        unknown = self.guard(text, "--accept", f"{flag_id}=fine", "--accept", "skip-000000=typo")
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("skip-000000", unknown.stdout)


class Skill(unittest.TestCase):
    def test_scripts_answer_help(self):
        for script in (LEDGER, GUARD):
            with self.subTest(script=script.name):
                self.assertEqual(run(script, "--help").returncode, 0)

    def test_anatomy_for_the_item(self):
        sys.path.insert(0, str(ROOT / "tests"))
        import test_skill_anatomy
        self.assertEqual(test_skill_anatomy.problems("interrogating-changes", item=True), [])

    def test_x6_cap_follows_the_disposition_policy(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("disposition policy", text)
        self.assertIn("without a contract, the owner decides", text.lower())

    def test_description_leads_with_what_sets_it_apart(self):
        text = (SKILL / "SKILL.md").read_text()
        description = re.search(r'^description: "(.*)"$', text, re.M).group(1)
        lead = description.split("Use when")[0]
        for phrase in ("Adversarial", "fresh-context", "reviewing-code", "regression", "git patch-id",
                       "disposition policy"):
            self.assertIn(phrase, lead)
        self.assertIn("Not for", description)
        self.assertIn("goldfishing", description.split("Not for")[1])

    def test_floor_guard_section_says_when_to_run(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("floor_guard.py", text)
        self.assertRegex(text, r"(?i)gate two")


if __name__ == "__main__":
    unittest.main()

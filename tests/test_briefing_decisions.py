"""Tests for skills/briefing-decisions/scripts/brief_check.py.

Run: python3 -m unittest tests.test_briefing_decisions -v
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "briefing-decisions" / "scripts" / "brief_check.py"
TEMPLATE = ROOT / "skills" / "briefing-decisions" / "reference" / "template.md"
BRIEF = ROOT / "evals" / "briefing-decisions" / "brief.md"
PATTERNS = json.loads((ROOT / "tests" / "fixtures" / "brief-patterns.json").read_text())
sys.path.insert(0, str(SCRIPT.parent))

import brief_check  # noqa: E402

GOOD = BRIEF.read_text()


CASES = json.loads((ROOT / "tests" / "fixtures" / "brief-cases.json").read_text())


def apply(case, text=GOOD):
    """Build a case's brief exactly as tests/mission-control.test.ts does."""
    for old, new in case.get("edits", []):
        assert old in text, old
        text = text.replace(old, new, 1)
    if "cut" in case:
        text = text[: text.index(case["cut"])]
    if "pad" in case:
        i = text.rindex("</details>")
        text = text[:i] + "x" * case["pad"] + "\n\n" + text[i:]
    return text + case.get("append", "")


def rules(text):
    return [p.split(":", 1)[0] for p in brief_check.check(text)]


def replace(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new, 1)


class Patterns(unittest.TestCase):
    def test_shared_pass_and_fail_lines(self):
        for line in PATTERNS["pass"]:
            with self.subTest(line=line):
                self.assertEqual(brief_check.banned(line), [])
        for line, rule in PATTERNS["fail"]:
            with self.subTest(line=line):
                self.assertIn(rule, brief_check.banned(line))


class Briefs(unittest.TestCase):
    def test_example_briefs_pass(self):
        self.assertEqual(brief_check.check(GOOD), [])
        example = re.search(r"## Filled example.*?````markdown\n(.*?)````", TEMPLATE.read_text(), re.S).group(1)
        self.assertEqual(brief_check.check(example), [])

    def test_shared_cases(self):
        for case in CASES["cases"]:
            with self.subTest(why=case["why"]):
                found = rules(apply(case))
                if case["rule"] is None:
                    self.assertEqual(found, [])
                else:
                    self.assertEqual(found[:1], [case["rule"]])

    def test_picture_on_allowed_host_passes(self):
        text = replace("excluded:", "picture: https://ampcode.com/artifacts/visuals/demo\nexcluded:")
        self.assertEqual(brief_check.check(text), [])

    def test_command_line_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.md"
            bad.write_text(replace("## How to undo it", "## Undo"))
            ok = subprocess.run([sys.executable, str(SCRIPT), str(BRIEF)], capture_output=True, text=True)
            no = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "pass"))
        self.assertEqual(no.returncode, 1)
        self.assertTrue(no.stdout.startswith("headings:"), no.stdout)


if __name__ == "__main__":
    unittest.main()

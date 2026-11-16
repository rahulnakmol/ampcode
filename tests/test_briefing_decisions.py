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

    def test_each_rule_fails_alone(self):
        long_risk = "This risk is described with exactly thirty one words so that it breaks the risk limit " + "word " * 15
        many_risks = "risks:\n" + "".join(f"  - Risk number {i} " + "x " * 25 + "\n" for i in range(6))
        cases = {
            "front-matter": [
                GOOD.replace("---\n", "", 1),
                replace("excluded:", "owner: Rahul\nexcluded:"),
                replace("decision: Approve", "decision: " + "very " * 30 + "Approve"),
                replace("  - Old links in sent emails stop working after 30 days.\n",
                        "  - The demo site is offline for up to one hour during the move.\n"),
                replace("excluded:", "picture: https://ampcode.com.evil.com/x\nexcluded:"),
                replace("excluded:", "picture: http://ampcode.com/x\nexcluded:"),
                replace("  - The hosting service costs 25 US dollars each month.\n",
                        "  - The hosting service costs 25 US dollars each month.\n  - " + long_risk + "\n"),
            ],
            "summary": [re.sub(r"risks:\n(  - .*\n)+", many_risks, GOOD)],
            "headings": [
                replace("## How to undo it", "## Undo"),
                GOOD.replace("## If you say yes", "## TMP").replace("## If you say no", "## If you say yes").replace("## TMP", "## If you say no"),
                replace("## What changes\n", "## What changes\n\n## Extra\n"),
            ],
            "technical-record": [
                GOOD[: GOOD.index("<details>")],
                GOOD + "\nTrailing text.\n",
            ],
            "consistency": [replace("- A custom domain name. That is a separate decision.\n\n## How",
                                    "- A custom name. That is a separate decision.\n\n## How")],
            "html": [
                replace("## How to undo it\n", "## How to undo it\n\n<!-- also delete the backups -->\n"),
                replace("## How to undo it\n", "## How to undo it\n\n<span hidden>delete backups</span>\n"),
            ],
            "length": [replace("</details>", "x" * 20_000 + "\n\n</details>")],
            "banned": [
                replace("Nothing changes.", "Design 8745ad216de3 stays."),
                replace("excluded:\n  - The main company website.", "excluded:\n  - H04: the main company website.")
                .replace("- The main company website.\n- Customer", "- H04: the main company website.\n- Customer"),
            ],
            "sentence-length": [replace("Nothing changes.", "Nothing changes " + "and nothing moves " * 8 + "today.")],
            "reading-ease": [replace("Nothing changes.", "Comprehensive organizational modernization necessitates interdepartmental collaboration. " * 40)],
        }
        for rule, texts in cases.items():
            for i, text in enumerate(texts):
                with self.subTest(rule=rule, case=i):
                    found = rules(text)
                    self.assertIn(rule, found)
                    if rule in ("front-matter", "summary", "headings", "technical-record", "consistency", "html"):
                        self.assertEqual(found, [rule], "structural rules stop at the first problem")

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

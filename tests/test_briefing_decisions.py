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
            crlf = Path(tmp) / "crlf.md"
            crlf.write_bytes(GOOD.replace("\n", "\r\n").encode())
            cr = subprocess.run([sys.executable, str(SCRIPT), str(crlf)], capture_output=True, text=True)
            ok = subprocess.run([sys.executable, str(SCRIPT), str(BRIEF)], capture_output=True, text=True)
            no = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "pass"))
        self.assertEqual(no.returncode, 1)
        self.assertTrue(no.stdout.startswith("headings:"), no.stdout)
        self.assertEqual(cr.returncode, 1)
        self.assertTrue(cr.stdout.startswith("characters:"), cr.stdout)



class Page(unittest.TestCase):
    """brief_page.py: the approver reads a page made only from the checked brief."""

    PAGE = SCRIPT.parent / "brief_page.py"

    def test_page_shows_every_part_of_the_checked_brief(self):
        import hashlib
        import html
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brief.md"
            source.write_text(GOOD)
            done = subprocess.run([sys.executable, str(self.PAGE), str(source)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            page = (Path(tmp) / "brief.html").read_text()
            shown = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())
            self.assertIn(hashlib.sha256(source.read_bytes()).hexdigest(), page)
            self.assertNotIn("<script", page)
            self.assertNotIn("**", shown)  # bold is rendered, not shown as Markdown
            data, _, body = brief_check.front_matter(GOOD)
            prose, record, _ = brief_check.split_body(body)
            expected = [data["decision"], data["yes"], data["no"], *data["risks"]]
            for line in (prose + record).splitlines():
                text = re.sub(r"^(#+|\s*(?:[-*]|\d+\.))\s+", "", line.strip())
                text = re.sub(r"\*\*|`|\[([^\]]+)\]\([^)]+\)", lambda m: m.group(1) or "", text)
                if text and not text.startswith("|"):
                    expected.append(text)
            for text in expected:
                with self.subTest(text=text[:50]):
                    self.assertIn(" ".join(text.split()), shown)

    def test_page_escapes_text_and_draws_tables(self):
        text = replace("## What changes\n", """## What changes

| Part | Cost |
| --- | --- |
| Hosting | 25 dollars |

Costs stay low when a < b & c. See [the notes](javascript:alert) first.
""")
        self.assertEqual(brief_check.check(text), [])
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brief.md"
            source.write_text(text)
            done = subprocess.run([sys.executable, str(self.PAGE), str(source)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            page = (Path(tmp) / "brief.html").read_text()
        self.assertIn("<td>Hosting</td><td>25 dollars</td>", page)
        self.assertIn("a &lt; b &amp; c", page)
        self.assertNotIn('href="javascript', page)

    def test_a_brief_that_fails_the_check_gets_no_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brief.md"
            source.write_text(replace("## Not included", "## Left out"))
            done = subprocess.run([sys.executable, str(self.PAGE), str(source)], capture_output=True, text=True)
            self.assertEqual(done.returncode, 1)
            self.assertIn("refused", done.stdout)
            self.assertFalse((Path(tmp) / "brief.html").exists())


if __name__ == "__main__":
    unittest.main()

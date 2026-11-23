"""Contract-mission kit checks: banned phrases, the canonical stop and report text, the cap policy.

The file lists below grow as each skill, the plugin and the guides adopt the contract
(see the mission contract, section 6). Paths are relative to the repository root; a
directory is searched recursively.

Run: python3 -m unittest tests.test_contract_kit -v
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_TEXT = ROOT / "plugins/mission-control/lib/contract-text.json"

# List B, matched case-insensitively.
BANNED = (
    "Budget used",
    "**Budget:**",
    "token budget",
    "review budget",
    "budget call",
    "remaining budget",
    "beyond it needs explicit approval",
    "merge mode",
    "mission_merge_mode",
    "ask-before-merge",
    "ask mode",
    "Owner merge acknowledgment",
    "high-risk merge",
    "high risk always requires",
)

# Files searched with list B (part of file set F).
BANNED_SEARCH = ("skills/delivering",)
# List L: files that list the five stop reasons.
STOP_TEXT_FILES = ("skills/delivering/SKILL.md",)
# Files that must name the disposition policy for a review cap (K3).
DISPOSITION_FILES = ("skills/delivering/SKILL.md",)
# The copy of reportSections that published skills and other hosts read.
REPORT_SECTIONS_FILE = "skills/delivering/SKILL.md"


def files(paths):
    for name in paths:
        path = ROOT / name
        yield from sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]


def contract_text():
    return json.loads(CONTRACT_TEXT.read_text())


class BannedPhrases(unittest.TestCase):
    def test_list_b_finds_nothing(self):
        for path in files(BANNED_SEARCH):
            try:
                text = path.read_text().lower()
            except UnicodeDecodeError:
                continue  # binary files hold no instructions
            for phrase in BANNED:
                with self.subTest(file=str(path.relative_to(ROOT)), phrase=phrase):
                    self.assertFalse(phrase.lower() in text, f"list B phrase {phrase!r} found")


class CanonicalText(unittest.TestCase):
    def test_contract_text_shape(self):
        data = contract_text()
        self.assertEqual(len(data["stopReasons"]), 5)
        self.assertEqual(set(data["reportSections"]), {"checkpoint", "closeOut"})
        for value in [*data["stopReasons"], *data["reportSections"]["checkpoint"], *data["reportSections"]["closeOut"]]:
            self.assertIsInstance(value, str)
            self.assertEqual(value, value.strip())
            self.assertTrue(value)

    def test_stop_reasons_verbatim(self):
        reasons = contract_text()["stopReasons"]
        for path in files(STOP_TEXT_FILES):
            text = path.read_text()
            for number, reason in enumerate(reasons, 1):
                with self.subTest(file=str(path.relative_to(ROOT)), reason=number):
                    line = f"{number}. {reason}"
                    self.assertTrue(line + "\n" in text, f"missing verbatim line: {line}")

    def test_report_sections_verbatim(self):
        text = (ROOT / REPORT_SECTIONS_FILE).read_text()
        for kind, sections in contract_text()["reportSections"].items():
            with self.subTest(kind=kind):
                expected = ", ".join(f"`{name}`" for name in sections) + "."
                self.assertTrue(expected in text, f"missing verbatim sections: {expected}")


class CapDisposition(unittest.TestCase):
    def test_cap_names_the_disposition_policy(self):
        for path in files(DISPOSITION_FILES):
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertTrue("disposition policy" in path.read_text(), "does not name the disposition policy")


if __name__ == "__main__":
    unittest.main()

"""Repository-wide skill metadata and single-protocol checks.

Run: python3 -m unittest tests.test_skill_metadata -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
LIMIT = 1024

# Generic fresh-reader protocol text now owned by skills/goldfishing.
RESTATED = (
    "Elephant who holds the context",
    "never your explanation",
    "Self-review is not a Goldfish",
    "conversational coaching",
    "Repair missing explanations in the brief",
)


def description(skill_md: str) -> str:
    """Return the frontmatter description value without its surrounding quotes."""
    match = re.match(r"\A---\n(.*?)\n---\n", skill_md, re.S)
    if not match:
        raise ValueError("missing frontmatter")
    for line in match.group(1).splitlines():
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    raise ValueError("missing description")


def too_long(value: str) -> bool:
    return len(value) > LIMIT


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class Descriptions(unittest.TestCase):
    def test_limit_boundary(self):
        self.assertFalse(too_long("a" * 1024))
        self.assertTrue(too_long("a" * 1025))
        self.assertEqual(description('---\nname: x\ndescription: "' + "a" * 1024 + '"\n---\n'), "a" * 1024)

    def test_every_description_fits(self):
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=path.parent.name):
                value = description(path.read_text())
                self.assertFalse(too_long(value), f"{len(value)} characters; limit {LIMIT}")


class OneProtocol(unittest.TestCase):
    def test_generic_protocol_lives_only_in_goldfishing(self):
        for path in sorted(p for p in SKILLS.rglob("*") if p.is_file()):
            if path.is_relative_to(SKILLS / "goldfishing"):
                continue
            try:
                text = collapse(path.read_text())
            except UnicodeDecodeError:
                continue  # binary files hold no instructions
            for phrase in RESTATED:
                with self.subTest(file=str(path.relative_to(ROOT)), phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_callers_name_goldfishing(self):
        for name in ("grilling/SKILL.md", "planning/SKILL.md", "delivering/reference/review-and-recovery.md"):
            with self.subTest(file=name):
                self.assertIn("goldfishing", (SKILLS / name).read_text())


if __name__ == "__main__":
    unittest.main()

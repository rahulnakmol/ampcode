"""Tests for skills/goldfishing/scripts/reviewer_model.py: the reviewer's model is picked, not checked later.

Run: python3 -m unittest tests.test_reviewer_model -v
"""

import subprocess
import sys
import unittest
from pathlib import Path

PICK = Path(__file__).resolve().parents[1] / "skills" / "goldfishing" / "scripts" / "reviewer_model.py"
OPUS, ASTRA, SOL = "anthropic/claude-opus-5-5", "openai/gpt-6-astra", "openai/gpt-6.1-sol"
CARBON, NEON = "google-vertex/gemini-4-carbon", "google-vertex/gemini-4-neon"


def pick(kind, *implementers, taken=()):
    args = [sys.executable, str(PICK), "--kind", kind]
    args += [a for m in implementers for a in ("--implementer", m)] + [a for m in taken for a in ("--not", m)]
    run = subprocess.run(args, capture_output=True, text=True)
    return run.returncode, run.stdout.splitlines()[0] if run.stdout else ""


class ReviewerModel(unittest.TestCase):
    def test_code_reviews_go_to_another_provider(self):
        self.assertEqual(pick("code-1", OPUS), (0, ASTRA))
        self.assertEqual(pick("code-2", OPUS, taken=[ASTRA]), (0, CARBON))
        # Another OpenAI model wrote it: the reviewer skips the whole provider, not just that model.
        self.assertEqual(pick("code-1", SOL), (0, OPUS))
        self.assertEqual(pick("code-2", CARBON, taken=[ASTRA]), (0, OPUS))
        self.assertEqual(pick("document", " Anthropic/Claude-Sonnet-5-5 "), (0, ASTRA))

    def test_when_every_provider_wrote_some_the_first_unused_model(self):
        self.assertEqual(pick("code-1", SOL, OPUS, NEON), (0, ASTRA))
        self.assertEqual(pick("code-1", ASTRA, OPUS, CARBON)[0], 1)

    def test_ui_reviews_go_to_gemini_by_complexity(self):
        self.assertEqual(pick("ui", OPUS), (0, NEON))
        self.assertEqual(pick("ui-complex", OPUS), (0, CARBON))
        self.assertEqual(pick("ui-complex", CARBON), (0, NEON))
        self.assertEqual(pick("ui", NEON), (0, CARBON))
        self.assertEqual(pick("ui", CARBON, taken=[NEON]), (0, ASTRA))

    def test_bad_input(self):
        self.assertEqual(pick("code-1", " ")[0], 1)
        self.assertNotEqual(pick("review", OPUS)[0], 0)


if __name__ == "__main__":
    unittest.main()

"""Tests for the weighted fit-gap of shaping-engagements (cases W9.1 to W9.4).

The fit-gap uses `score.py score --fit-gap` from skills/assessing-products. Every expected
score and total below is computed by hand in the comments, not by score.py.

Run: python3 -m unittest tests.test_shaping_engagements_fit_gap -v
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "assessing-products" / "scripts" / "score.py"
SHAPING = ROOT / "skills" / "shaping-engagements" / "SKILL.md"
PROPOSALS = ROOT / "skills" / "blueprinting" / "reference" / "proposals.md"
FIXTURE = ROOT / "tests" / "fixtures" / "fit-gap"
sys.path.insert(0, str(SCRIPT.parent))

import score  # noqa: E402

# The map in item W9, written out by hand.
MAP = {"supported": 5, "configuration": 4, "extension": 3, "integration": 3, "process change": 2, "unresolved": 0}

# The fixture (tests/fixtures/fit-gap):
#   weights agreed with the client: R1 30, R2 25, R3 20, R4 15, R5 10 (sum 100)
#   OptionA: R1 supported 5, R2 configuration 4, R3 extension 3, R4 integration 3, R5 process change 2
#   OptionB: R1 configuration 4, R2 supported 5, R3 unresolved 0, R4 supported 5, R5 integration 3
# Total = sum(weight x score) / 5, out of 100.
#   OptionA: (30*5 + 25*4 + 20*3 + 15*3 + 10*2) / 5 = (150 + 100 + 60 + 45 + 20) / 5 = 375 / 5 = 75
#   OptionB: (30*4 + 25*5 + 20*0 + 15*5 + 10*3) / 5 = (120 + 125 +  0 + 75 + 30) / 5 = 350 / 5 = 70
TOTALS = {"OptionA": 75.0, "OptionB": 70.0}


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=60)


class FitGap(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ("criteria.json", "fitgap.json"):
            shutil.copy(FIXTURE / name, self.tmp / name)
        self.criteria, self.fitgap = self.tmp / "criteria.json", self.tmp / "fitgap.json"
        frozen = run("freeze", self.criteria)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)

    def set_fit(self, product, requirement, fit):
        data = json.loads(self.fitgap.read_text())
        for entry in data["products"]:
            if entry["name"] == product:
                entry["scores"][requirement]["fit"] = fit
        self.fitgap.write_text(json.dumps(data))

    def score(self):
        return run("score", self.criteria, self.fitgap, "--fit-gap")

    def test_w9_1_each_category_converts_by_the_map(self):
        for category, expected in MAP.items():
            with self.subTest(category=category):
                value, status, _, problems = score.cell_score(
                    "OptionA 'R1'", {"fit": category, "evidence": "Read 2026-11-11", "status": "verified"}, fit_gap=True)
                self.assertEqual((value, status, problems), (expected, "verified", []))

    def test_w9_1_totals_equal_the_hand_computed_fixture(self):
        result = self.score()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        ranks = re.findall(r"(?m)^(\d+)\. (\w+) (\d+\.\d\d)$", result.stdout)
        self.assertEqual(ranks, [("1", "OptionA", "75.00"), ("2", "OptionB", "70.00")])
        weights = json.loads(self.criteria.read_text())["frozen"]["weights"]
        table, _, problems = score.read_scores(weights, json.loads(self.fitgap.read_text()), fit_gap=True)
        self.assertEqual(problems, [])
        self.assertEqual(table["OptionB"], {"R1": 4, "R2": 5, "R3": 0, "R4": 5, "R5": 3})
        for name, expected in TOTALS.items():
            self.assertAlmostEqual(score.totals(weights, table)[name], expected, places=9)

    def test_w9_1b_map_categories_equal_the_six_in_proposals(self):
        # proposals.md: "fit\ncategory (supported, configuration, extension, process change, integration or unresolved)"
        text = re.sub(r"\s+", " ", PROPOSALS.read_text())
        listed = re.search(r"fit category \(([^)]*)\)", text).group(1)
        categories = {part.strip() for part in re.split(r",| or ", listed) if part.strip()}
        self.assertEqual(len(categories), 6)
        self.assertEqual(set(score.FIT_GAP_SCORES), categories)
        self.assertEqual(score.FIT_GAP_SCORES, MAP)

    def test_w9_2_unresolved_scores_0_and_is_listed_as_a_gap(self):
        result = self.score()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        gaps = result.stdout.split("Gaps", 1)[1].split("Unverified", 1)[0]
        listed = re.findall(r"(?m)^- (\w+) (\w+): unresolved", gaps)
        self.assertEqual(listed, [("OptionB", "R3")])
        self.assertIn("Question Q-7", gaps)
        # Every other cell is a fit, not a gap.
        self.assertNotIn("OptionA", gaps)

    def test_w9_2_no_unresolved_says_none(self):
        self.set_fit("OptionB", "R3", "extension")
        result = self.score()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        gaps = result.stdout.split("Gaps", 1)[1].split("Unverified", 1)[0]
        self.assertRegex(gaps, r"(?m)^- none$")
        # OptionB with R3 extension: (120 + 125 + 60 + 75 + 30) / 5 = 410 / 5 = 82, now first.
        self.assertRegex(result.stdout, r"(?m)^1\. OptionB 82\.00$")

    def test_w9_3_an_unknown_category_is_refused(self):
        for fit in ("partial", "supported by partner", "process-change", "", None, 5, ["supported"]):
            with self.subTest(fit=fit):
                self.set_fit("OptionA", "R2", fit)
                result = self.score()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertRegex(result.stdout, r"(?m)^G1: OptionA 'R2' ")
                self.assertNotIn("Totals", result.stdout)

    def test_w9_3_a_cell_without_a_category_is_refused(self):
        data = json.loads(self.fitgap.read_text())
        cell = data["products"][0]["scores"]["R1"]
        del cell["fit"]
        cell["score"] = 5
        self.fitgap.write_text(json.dumps(data))
        result = self.score()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertRegex(result.stdout, r"(?m)^G1: OptionA 'R1' ")

    def test_fit_gap_still_needs_evidence_and_a_freeze(self):
        data = json.loads(self.fitgap.read_text())
        data["products"][1]["scores"]["R3"]["evidence"] = "TBD"
        self.fitgap.write_text(json.dumps(data))
        self.assertIn("S3: OptionB 'R3'", self.score().stdout)
        shutil.copy(FIXTURE / "criteria.json", self.criteria)
        self.assertIn("S1", self.score().stdout)

    def test_without_the_flag_a_category_is_not_a_score(self):
        result = run("score", self.criteria, self.fitgap)
        self.assertEqual(result.returncode, 1)
        self.assertIn("S4: OptionA 'R1'", result.stdout)
        self.assertNotIn("Gaps", result.stdout)

    def test_score_help_names_the_flag(self):
        result = run("score", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--fit-gap", result.stdout)


class SkillText(unittest.TestCase):
    def setUp(self):
        self.text = SHAPING.read_text()
        self.flat = re.sub(r"\s+", " ", self.text)

    def test_w9_4_weights_agreed_and_frozen_before_scoring(self):
        self.assertIn("agree", self.flat.lower())
        self.assertRegex(self.flat, r"(?i)weights? .{0,80}client")
        self.assertRegex(self.flat, r"(?i)frozen before .{0,20}scor|freeze .{0,60}before .{0,40}scor")

    def test_n5_weights_frozen_before_any_fit_category_is_assessed(self):
        # Review N5: in fit-gap mode the category is the score, so the freeze must come before the categories.
        self.assertRegex(self.flat, r"(?i)freeze the weights .{0,40}before any fit category is assessed")
        self.assertNotIn("before any fit is scored", self.flat)

    def test_w9_4_names_assessing_products_as_a_dependency(self):
        self.assertRegex(self.flat, r"`assessing-products`[^.]{0,80}dependency|dependency[^.]{0,80}`assessing-products`")
        self.assertIn("--fit-gap", self.text)

    def test_w9_4_map_table_equals_the_script_constant(self):
        rows = re.findall(r"(?m)^\| *([a-z][a-z ]*?) *\| *(\d+) *\|$", self.text)
        self.assertEqual({name: int(value) for name, value in rows}, MAP)
        self.assertIn("FIT_GAP_SCORES", self.text)

    def test_assessing_products_documents_the_flag(self):
        text = (ROOT / "skills" / "assessing-products" / "SKILL.md").read_text()
        self.assertIn("--fit-gap", text)
        self.assertIn("FIT_GAP_SCORES", text)


if __name__ == "__main__":
    unittest.main()

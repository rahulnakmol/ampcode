"""Tests for skills/assessing-products: score.py (cases W8.1 to W8.9) and the skill text.

Run: python3 -m unittest tests.test_assessing_products -v

Every expected total, rank and sensitivity value below is computed by hand in the comments, not
by score.py.
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
SKILL = ROOT / "skills" / "assessing-products"
SCRIPT = SKILL / "scripts" / "score.py"
EXAMPLE = SKILL / "reference" / "example"
sys.path.insert(0, str(SCRIPT.parent))

import score  # noqa: E402

# The example (reference/example) is the three-product fixture:
#   weights: fit 40, soc2 30, cost 20, exit 10 (sum 100)
#   Alpha: fit 5, soc2 4, cost 3, exit 1
#   Beta:  fit 4, soc2 4 (claimed), cost 3, exit 3
#   Gamma: fit 3, soc2 3, cost 4 (claimed), exit 3
# Total = sum(weight x score) / 5, out of 100.
#   Alpha: (40*5 + 30*4 + 20*3 + 10*1) / 5 = (200 + 120 + 60 + 10) / 5 = 390 / 5 = 78
#   Beta:  (40*4 + 30*4 + 20*3 + 10*3) / 5 = (160 + 120 + 60 + 30) / 5 = 370 / 5 = 74
#   Gamma: (40*3 + 30*3 + 20*4 + 10*3) / 5 = (120 +  90 + 80 + 30) / 5 = 320 / 5 = 64
TOTALS = {"Alpha": 78.0, "Beta": 74.0, "Gamma": 64.0}


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          cwd=cwd, timeout=60)


class Workspace(unittest.TestCase):
    """Each test gets a copy of the example in a temporary folder, because freeze writes in place."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ("criteria.json", "scores.json", "recommendation.md"):
            shutil.copy(EXAMPLE / name, self.tmp / name)
        self.criteria = self.tmp / "criteria.json"
        self.scores = self.tmp / "scores.json"

    def edit(self, path, change):
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data, indent=2))

    def freeze(self):
        result = run("freeze", self.criteria)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def refused(self, result, *needles):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for needle in needles:
            self.assertIn(needle, result.stdout)
        return result.stdout

    def score_cell(self, product, criterion, cell):
        def change(data):
            for entry in data["products"]:
                if entry["name"] == product:
                    entry["scores"][criterion] = cell
        self.edit(self.scores, change)


class Freeze(Workspace):
    def test_w8_1_refuses_weights_that_do_not_sum_to_100(self):
        # 40 + 30 + 20 + 5 = 95; 40 + 30 + 20 + 15 = 105. Gate 2 F5 (P1): half a point off must fail
        # too, so a 1-point tolerance cannot pass: 40 + 30 + 20 + 9.5 = 99.5; 40 + 30 + 20 + 10.5 = 100.5.
        for weight, total in ((5, "95"), (15, "105"), (9.5, "99.5"), (10.5, "100.5")):
            with self.subTest(exit_weight=weight):
                self.edit(self.criteria, lambda d: d["criteria"][3].update(weight=weight))
                before = self.criteria.read_text()
                self.refused(run("freeze", self.criteria), "F3", total)
                self.assertEqual(self.criteria.read_text(), before, "a refused freeze must not write")

    def test_w8_1_refuses_a_weight_that_is_not_a_number_from_0_to_100(self):
        self.edit(self.criteria, lambda d: d["criteria"][0].update(weight="40"))
        self.refused(run("freeze", self.criteria), "F2", "fit")

    def test_freeze_writes_weights_and_digest(self):
        out = self.freeze().stdout
        frozen = json.loads(self.criteria.read_text())["frozen"]
        self.assertEqual(frozen["weights"], {"fit": 40, "soc2": 30, "cost": 20, "exit": 10})
        self.assertRegex(frozen["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertIn(frozen["digest"], out)
        self.assertEqual(sorted(frozen["seals"]), ["cost", "exit", "fit", "soc2"])

    def test_freeze_refuses_a_second_freeze(self):
        self.freeze()
        self.refused(run("freeze", self.criteria), "F4")

    def test_example_recommendation_cites_the_example_digest(self):
        out = self.freeze().stdout
        digest = re.search(r"sha256:[0-9a-f]{64}", out).group(0)
        self.assertIn(f"Weights digest: {digest}", (EXAMPLE / "recommendation.md").read_text())


class Scoring(Workspace):
    def test_w8_2_refuses_scoring_before_a_freeze(self):
        self.refused(run("score", self.criteria, self.scores), "S1", "freeze")

    def test_w8_3_refuses_a_changed_weight_naming_the_criterion(self):
        self.freeze()
        # Move 5 points from exit to fit: the sum stays 100, so only the freeze can catch it.
        def change(data):
            data["criteria"][0]["weight"] = 45
            data["criteria"][3]["weight"] = 5
        self.edit(self.criteria, change)
        out = self.refused(run("score", self.criteria, self.scores), "S2", "'fit'", "'exit'")
        self.assertNotIn("'soc2'", out)

    def test_w8_3_refuses_a_changed_frozen_weight_naming_the_criterion(self):
        self.freeze()
        def change(data):  # edit the list and the frozen copy together: the seal still names it
            data["criteria"][1]["weight"] = 35
            data["frozen"]["weights"]["soc2"] = 35
        self.edit(self.criteria, change)
        self.refused(run("score", self.criteria, self.scores), "S2", "'soc2'")

    def test_w8_3_refuses_added_and_removed_criteria(self):
        self.freeze()
        self.edit(self.criteria, lambda d: d["criteria"].append({"id": "sso", "name": "SSO", "weight": 0}))
        self.refused(run("score", self.criteria, self.scores), "S2", "'sso'", "added")
        self.edit(self.criteria, lambda d: d["criteria"].pop())
        self.edit(self.criteria, lambda d: d["criteria"].pop())
        self.refused(run("score", self.criteria, self.scores), "S2", "'exit'", "removed")

    def test_w8_3_expect_binds_the_digest_in_the_decision_trail(self):
        self.freeze()
        digest = json.loads(self.criteria.read_text())["frozen"]["digest"]
        self.assertEqual(run("score", self.criteria, self.scores, "--expect", digest).returncode, 0)
        self.refused(run("score", self.criteria, self.scores, "--expect", "sha256:" + "0" * 64), "S2", "expected")

    def test_w8_4_refuses_a_score_without_evidence(self):
        self.freeze()
        for evidence in (None, "", "  ", "TBD"):
            with self.subTest(evidence=evidence):
                cell = {"score": 4, "status": "verified"}
                if evidence is not None:
                    cell["evidence"] = evidence
                self.score_cell("Beta", "fit", cell)
                self.refused(run("score", self.criteria, self.scores), "S3", "Beta", "'fit'")

    def test_d23_r5_2_refuses_evidence_without_a_date_or_undated(self):
        # D-23, eval round 5, R5-2: evidence lines had no date and no "undated" (expected by hand from §3).
        self.freeze()
        for evidence in ("SCIM: create and change tested; deactivate not tested yet",
                         "Entra ID app gallery listing; not tested", "Quote CQ-0091, packet 2026-11",
                         "Read on 22 November 2026", "Ticket 20261122"):
            with self.subTest(evidence=evidence):
                self.score_cell("Beta", "exit", {"score": 3, "evidence": evidence, "status": "claimed"})
                out = self.refused(run("score", self.criteria, self.scores), "S3", "Beta 'exit'", "undated")
                self.assertNotIn("Totals", out)
        for evidence in ("Order form (undated), read 2026-11-22", "undated, read 2026-11-22",
                         "Plan sheet, Undated", "Written quote CQ-0091, 2026-11-12"):
            with self.subTest(evidence=evidence):
                self.score_cell("Beta", "exit", {"score": 3, "evidence": evidence, "status": "claimed"})
                result = run("score", self.criteria, self.scores)
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_d23_r5_2_the_example_and_fixtures_are_dated(self):
        # D-23: the skill's own example and the fit-gap fixture must still pass the date rule.
        self.freeze()
        self.assertEqual(run("score", self.criteria, self.scores).returncode, 0)
        fit_gap = ROOT / "tests" / "fixtures" / "fit-gap"
        shutil.copy(fit_gap / "criteria.json", self.tmp / "fg-criteria.json")
        self.assertEqual(run("freeze", self.tmp / "fg-criteria.json").returncode, 0)
        result = run("score", self.tmp / "fg-criteria.json", fit_gap / "fitgap.json", "--fit-gap")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_w8_5_refuses_a_score_outside_0_to_5(self):
        self.freeze()
        for value in (6, -1, 5.5, "4", True, None):
            with self.subTest(score=value):
                self.score_cell("Gamma", "exit", {"score": value, "evidence": "Sandbox export test 2026-11-05",
                                                  "status": "verified"})
                self.refused(run("score", self.criteria, self.scores), "S4", "Gamma", "'exit'")
        for value in (0, 5, 2.5):
            with self.subTest(score=value):
                self.score_cell("Gamma", "exit", {"score": value, "evidence": "Sandbox export test 2026-11-05",
                                                  "status": "verified"})
                self.assertEqual(run("score", self.criteria, self.scores).returncode, 0)

    def test_missing_unknown_and_badly_labelled_cells_are_refused(self):
        self.freeze()
        self.edit(self.scores, lambda d: d["products"][0]["scores"].pop("cost"))
        self.refused(run("score", self.criteria, self.scores), "S5", "Alpha", "'cost'")
        self.edit(self.scores, lambda d: d["products"][0]["scores"].update(
            cost={"score": 3, "evidence": "Quote Q-17, 2026-11-07", "status": "verified"}, sso={"score": 3, "evidence": "x"}))
        self.refused(run("score", self.criteria, self.scores), "S5", "'sso'")
        self.edit(self.scores, lambda d: d["products"][0]["scores"].pop("sso"))
        self.score_cell("Alpha", "fit", {"score": 5, "evidence": "Demo", "status": "probably"})
        self.refused(run("score", self.criteria, self.scores), "S5", "status")

    def test_w8_6_keeps_a_claimed_score_and_lists_it_as_unverified(self):
        self.freeze()
        result = run("score", self.criteria, self.scores)
        self.assertEqual(result.returncode, 0, result.stdout)
        # Beta's soc2 (4, claimed) still counts: Beta's total is 74, as computed above.
        self.assertIn("Beta 74.00", result.stdout)
        unverified = result.stdout.split("Unverified", 1)[1].split("Sensitivity", 1)[0]
        self.assertIn("Beta soc2: 4 claimed", unverified)
        self.assertIn("Gamma cost: 4 claimed", unverified)
        self.assertNotIn("Alpha", unverified)

    def test_w8_6_a_score_without_a_status_counts_as_claimed(self):
        self.freeze()
        self.score_cell("Alpha", "fit", {"score": 5, "evidence": "Vendor demo 2026-11-03"})
        result = run("score", self.criteria, self.scores)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Alpha fit: 5 claimed", result.stdout.split("Unverified", 1)[1])

    def test_w8_7_totals_and_ranks_equal_the_hand_computed_values(self):
        self.freeze()
        result = run("score", self.criteria, self.scores)
        self.assertEqual(result.returncode, 0, result.stdout)
        ranks = re.findall(r"^(\d+)\. (\w+) (\d+\.\d\d)$", result.stdout, re.M)
        self.assertEqual(ranks, [("1", "Alpha", "78.00"), ("2", "Beta", "74.00"), ("3", "Gamma", "64.00")])
        criteria = json.loads(self.criteria.read_text())
        scores = json.loads(self.scores.read_text())
        table, _, problems = score.read_scores(criteria["frozen"]["weights"], scores)
        self.assertEqual(problems, [])
        totals = score.totals(criteria["frozen"]["weights"], table)
        for name, expected in TOTALS.items():
            self.assertAlmostEqual(totals[name], expected, places=9)

    def test_tied_products_share_a_rank(self):
        # Hand: 70, 70, 50 gives ranks 1, 1, 3.
        self.assertEqual(score.ranking({"A": 70.0, "B": 70.0, "C": 50.0}), [(1, "A", 70.0), (1, "B", 70.0), (3, "C", 50.0)])


class Sensitivity(unittest.TestCase):
    WEIGHTS = {"fit": 40, "soc2": 30, "cost": 20, "exit": 10}
    TABLE = {
        "Alpha": {"fit": 5, "soc2": 4, "cost": 3, "exit": 1},
        "Beta": {"fit": 4, "soc2": 4, "cost": 3, "exit": 3},
        "Gamma": {"fit": 3, "soc2": 3, "cost": 4, "exit": 3},
    }

    def test_w8_8_rescales_the_other_weights_in_proportion(self):
        # exit 10 -> 20: the other 90 points become 80, each times 80/90.
        #   fit 40*8/9 = 35.556, soc2 30*8/9 = 26.667, cost 20*8/9 = 17.778.
        up = score.shifted(self.WEIGHTS, "exit", 10)
        for cid, expected in {"fit": 35.5556, "soc2": 26.6667, "cost": 17.7778, "exit": 20}.items():
            self.assertAlmostEqual(up[cid], expected, places=4)
        self.assertAlmostEqual(sum(up.values()), 100, places=9)
        # a 50, b 30, c 20; a -10 -> 40: b 30*60/50 = 36, c 20*60/50 = 24.
        self.assertEqual({k: round(v, 9) for k, v in score.shifted({"a": 50, "b": 30, "c": 20}, "a", -10).items()},
                         {"a": 40, "b": 36, "c": 24})

    def test_w8_8_clamps_to_0_and_100(self):
        # a 95 + 10 = 105 clamps to 100, so b gets 0; b 5 - 10 = -5 clamps to 0, so a gets 100.
        self.assertEqual(score.shifted({"a": 95, "b": 5}, "a", 10), {"a": 100, "b": 0})
        self.assertEqual(score.shifted({"a": 95, "b": 5}, "b", -10), {"a": 100, "b": 0})
        # a 100 - 10 = 90: the others had 0 points, so the 10 freed points are shared equally.
        self.assertEqual(score.shifted({"a": 100, "b": 0, "c": 0}, "a", -10), {"a": 90, "b": 5, "c": 5})

    def test_w8_8_flags_only_the_criterion_that_flips_the_top_rank(self):
        # By hand, raw = sum(weight x score); new raw = w' x s_c + k x (raw - w_c x s_c),
        # with k = (100 - w') / (100 - w_c); total = raw / 5.
        #   fit +10 (k 5/6):  A 250+190*5/6=408.3, B 200+210*5/6=375.0, G 150+200*5/6=316.7  -> Alpha
        #   fit -10 (k 7/6):  A 150+190*7/6=371.7, B 120+210*7/6=365.0, G  90+200*7/6=323.3  -> Alpha
        #   soc2 +10 (k 6/7): A 160+270*6/7=391.4, B 160+250*6/7=374.3, G 120+230*6/7=317.1  -> Alpha
        #   soc2 -10 (k 8/7): A  80+270*8/7=388.6, B  80+250*8/7=365.7, G  60+230*8/7=322.9  -> Alpha
        #   cost +10 (k 7/8): A  90+330*7/8=378.8, B  90+310*7/8=361.3, G 120+240*7/8=330.0  -> Alpha
        #   cost -10 (k 9/8): A  30+330*9/8=401.3, B  30+310*9/8=378.8, G  40+240*9/8=310.0  -> Alpha
        #   exit +10 (k 8/9): A  20+380*8/9=357.8, B  60+340*8/9=362.2, G  60+290*8/9=317.8  -> Beta
        #   exit -10 (k 10/9): A  0+380*10/9=422.2, B  0+340*10/9=377.8, G  0+290*10/9=322.2 -> Alpha
        result = {row["criterion"]: row for row in score.sensitivity(self.WEIGHTS, self.TABLE)}
        self.assertEqual([c for c, row in result.items() if row["flag"]], ["exit"])
        self.assertEqual(result["exit"]["up"]["top"], ["Beta"])
        self.assertEqual(result["exit"]["down"]["top"], ["Alpha"])
        for name, expected in {"Alpha": 357.778 / 5, "Beta": 362.222 / 5, "Gamma": 317.778 / 5}.items():
            self.assertAlmostEqual(result["exit"]["up"]["totals"][name], expected, places=3)
        for name, expected in {"Alpha": 371.667 / 5, "Beta": 365.0 / 5, "Gamma": 323.333 / 5}.items():
            self.assertAlmostEqual(result["fit"]["down"]["totals"][name], expected, places=3)

    def test_w8_8_flags_a_flip_that_happens_only_at_minus_10(self):
        # Gate 2 F5 (P8): the example flips only at +10, so a flag that ignored -10 survived.
        # Weights fit 40, apis 20, cost 20, exit 20. X: fit 5, others 2. Y: 3 everywhere, so Y is always 60.
        #   frozen:        X (200 + 3*40) / 5 = 64, Y 60                          -> X
        #   fit -10:       fit 30, others 70/3: X (150 + 2*70) / 5 = 58, Y 60      -> Y (the flip)
        #   fit +10:       fit 50, others 50/3: X (250 + 2*50) / 5 = 70            -> X
        #   apis +10:      apis 30, fit 35, cost and exit 17.5: X (175 + 60 + 35 + 35) / 5 = 61 -> X
        #   apis -10:      apis 10, fit 45, cost and exit 22.5: X (225 + 20 + 45 + 45) / 5 = 67 -> X
        #   cost and exit: the same as apis, by symmetry.
        weights = {"fit": 40, "apis": 20, "cost": 20, "exit": 20}
        table = {"X": {"fit": 5, "apis": 2, "cost": 2, "exit": 2},
                 "Y": {"fit": 3, "apis": 3, "cost": 3, "exit": 3}}
        result = {row["criterion"]: row for row in score.sensitivity(weights, table)}
        self.assertEqual([c for c, row in result.items() if row["flag"]], ["fit"])
        self.assertEqual((result["fit"]["up"]["top"], result["fit"]["down"]["top"]), (["X"], ["Y"]))
        self.assertAlmostEqual(result["fit"]["down"]["totals"]["X"], 58, places=9)
        self.assertAlmostEqual(result["fit"]["down"]["totals"]["Y"], 60, places=9)
        self.assertAlmostEqual(result["fit"]["up"]["totals"]["X"], 70, places=9)
        for cid in ("apis", "cost", "exit"):
            with self.subTest(criterion=cid):
                self.assertAlmostEqual(result[cid]["up"]["totals"]["X"], 61, places=9)
                self.assertAlmostEqual(result[cid]["down"]["totals"]["X"], 67, places=9)

    def test_w8_8_score_prints_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("criteria.json", "scores.json"):
                shutil.copy(EXAMPLE / name, Path(tmp) / name)
            self.assertEqual(run("freeze", "criteria.json", cwd=tmp).returncode, 0)
            out = run("score", "criteria.json", "scores.json", cwd=tmp).stdout
        self.assertRegex(out, r"(?m)^- exit: \+10 Beta, -10 Alpha +FLAG")
        self.assertRegex(out, r"(?m)^Flagged: exit$")


class Recommendation(Workspace):
    def check(self, text):
        path = self.tmp / "rec.md"
        path.write_text(text)
        return run("check", path)

    def good(self):
        return (self.tmp / "recommendation.md").read_text()

    def test_example_recommendation_passes(self):
        result = self.check(self.good())
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"), result.stdout)

    def test_w8_9_fails_without_conditions(self):
        text = self.good()
        without = re.sub(r"## Conditions\n.*?(?=\n## |\Z)", "", text, flags=re.S)
        self.assertNotEqual(without, text)
        self.refused(self.check(without), "R3")
        empty = re.sub(r"(## Conditions\n\n\|[^\n]*\n\|[^\n]*\n)(?:\|[^\n]*\n)+", r"\1", text)
        self.assertNotEqual(empty, text)
        self.refused(self.check(empty), "R3")

    def test_w8_9_fails_a_condition_without_an_owner(self):
        row = re.search(r"(?m)^\| (Beta|Alpha)[^\n]*$", self.good())
        self.assertIsNotNone(row)
        for owner in ("", "TBD", "-"):
            with self.subTest(owner=owner):
                cells = row.group(0).split("|")
                cells[2] = f" {owner} "
                self.refused(self.check(self.good().replace(row.group(0), "|".join(cells))), "R4")
        self.refused(self.check(self.good().replace("| Owner |", "| Notes |")), "R4")

    def test_recommendation_needs_a_product_and_the_digest(self):
        self.refused(self.check(re.sub(r"(?m)^Recommended:.*$", "", self.good())), "R1")
        self.refused(self.check(re.sub(r"(?m)^Weights digest:.*$", "Weights digest: later", self.good())), "R2")

    def owner(self, owner):
        row = re.search(r"(?m)^\| (Beta|Alpha)[^\n]*$", self.good()).group(0)
        cells = row.split("|")
        cells[2] = f" {owner} "
        return self.check(self.good().replace(row, "|".join(cells)))

    def test_w8_9_m2_fails_an_owner_who_is_not_a_named_person(self):
        # Review M2: a team, a role word or a placeholder is not the person who makes it true.
        for owner in ("Finance team", "Security Team", "IT department", "Platform squad", "Ops group",
                      "Finance function", "Vendor management roles", "security", "the owner", "someone",
                      "TBD Priya", "TODO: ask Hanna", "TBC", "unknown", "Unknown person", "<owner>",
                      "<name> (Head of Platform)", "Finance team (Priya Shah)", "(Finance team)",
                      "Security group, Priya Shah"):
            with self.subTest(owner=owner):
                self.refused(self.owner(owner), "R4")
        # Recheck N4 (as threat-modelling): role text after the first "(" or "," may hold a team word, and
        # an email may sit in <...>; only a name that is nothing but <...> fails.
        for owner in ("Priya Shah (Head of Platform)", "Tomas Berg, security lead", "Omar Haddad",
                      "Dana Reyes (Platform Group lead)", "Kim Lee, Security Department head",
                      "Dana Reyes (role: CISO)", "Dana Reyes <dana@example.com>", "Priya Shah <name>"):
            with self.subTest(owner=owner):
                result = self.owner(owner)
                self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"), result.stdout)

    def test_x2_fails_an_overclaim_word(self):
        for claim in ("Alpha is secure.", "Alpha has no vulnerabilities.", "Alpha is vulnerability-free."):
            with self.subTest(claim=claim):
                self.refused(self.check(self.good() + "\n" + claim + "\n"), "R5")

    def test_x2_m1_fails_overclaim_variants(self):
        # Review M1: each of these passed check before the fix.
        for claim in ("Alpha is fully secured.", "Alpha is securely hosted.", "Alpha has no known vulnerabilities.",
                      "Zero vulnerabilities found.", "Zero known vulnerability remains.", "Alpha is vulnerability free.",
                      "Alpha is risk-free.", "Alpha is risk free.", "Alpha is SOC 2 compliant.",
                      "Alpha is GDPR compliant and secure.", "Alpha is verified.",
                      # Recheck N3 (as threat-modelling): "not only/just/merely" do not negate; the
                      # exemptions for scans, Secure Shell and secure cookies leave other claims caught.
                      "Alpha is not only secure but fast.", "Alpha is not just compliant.",
                      "Alpha is not merely verified.", "No vulnerabilities found in the scan.",
                      "Secure Shell access is secure.", "Zero vulnerabilities; the secure-cookie test passed."):
            with self.subTest(claim=claim):
                self.refused(self.check(self.good() + "\n" + claim + "\n"), "R5")

    def test_w8_9_recheck_r1_fails_a_team_word_in_brackets_or_after_a_comma(self):
        # Recheck R1: the name part looked like a name, but the rest is only a team word.
        for owner in ("Finance (team)", "IT, department", "Procurement (group)", "Payments (squad)",
                      "Ops (teams)", "Legal, function"):
            with self.subTest(owner=owner):
                self.refused(self.owner(owner), "R4")
        for owner in ("Dana Reyes (Platform Group lead)", "Kim Lee, Security Department head",
                      "Dana Reyes (role: CISO)"):
            with self.subTest(owner=owner):
                result = self.owner(owner)
                self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"), result.stdout)

    def test_x2_recheck_r2_status_colon_does_not_excuse_verified(self):
        # Recheck R2: "status:" before "verified" could carry a claim; only the quoted status name passes.
        for claim in ("Alpha security status: verified.", "Beta soc2 (status: verified after the report arrives)."):
            with self.subTest(claim=claim):
                self.refused(self.check(self.good() + "\n" + claim + "\n"), "R5")

    def test_x2_m1_passes_honest_labels(self):
        # "not" just before the word is an honest label (threat-modelling's rule); "compliant" may also be
        # labelled as a claim or as "non-compliant"; "verified" may be quoted as the score status name.
        for line in ("Export is not secure today.", "Export is not yet secure.", "Alpha is not verified.",
                     "Beta claims to be SOC 2 compliant; the report is not received.", "Beta is claimed compliant.",
                     "Gamma is non-compliant with our retention rule.", "Alpha is not compliant with R7.",
                     "Alpha's fit score has status `verified`.", "Two scores are \"verified\".",
                     "Beta soc2 is unverified.",
                     # Recheck R2: "cannot be" before the word is an honest label too.
                     "The report cannot be verified yet.", "Alpha cannot be called compliant.",
                     # Recheck N3 (as threat-modelling): honest labels the widened check used to reject.
                     "No vulnerability scan ran.", "No vulnerability scanning was in scope.",
                     "No vulnerability scanner or test ran; no vulnerability database or data feed was read.",
                     "Alpha's SFTP uses Secure Shell with key login.", "Secure cookie flag is a gap.",
                     "The secure-cookie test was not run.", "Nothing here is secure.",
                     "Cannot be called compliant: 2 gaps.", "Never verified."):
            with self.subTest(line=line):
                result = self.check(self.good() + "\n" + line + "\n")
                self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"), result.stdout)

    def test_r2_criteria_binds_the_digest_to_the_frozen_weights(self):
        # Review follow-up: with --criteria, the recommendation's digest must be the digest of the frozen weights.
        rec = self.tmp / "recommendation.md"
        self.refused(run("check", rec, "--criteria", self.criteria), "R2", "not frozen")
        self.freeze()
        result = run("check", rec, "--criteria", self.criteria)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "pass"), result.stdout)
        other = re.sub(r"sha256:[0-9a-f]{64}", "sha256:" + "a" * 64, rec.read_text())
        (self.tmp / "other.md").write_text(other)
        self.refused(run("check", self.tmp / "other.md", "--criteria", self.criteria), "R2", "sha256:" + "a" * 64)
        self.edit(self.criteria, lambda d: d["frozen"]["weights"].update(fit=45, exit=5))
        self.refused(run("check", rec, "--criteria", self.criteria), "R2")


class CommandLine(unittest.TestCase):
    def test_help_exits_0(self):
        for args in (["--help"], ["freeze", "--help"], ["score", "--help"], ["check", "--help"]):
            with self.subTest(args=args):
                self.assertEqual(run(*args).returncode, 0)

    def test_unreadable_input_exits_2(self):
        self.assertEqual(run("freeze", "/no/such/criteria.json").returncode, 2)


class Malformed(Workspace):
    """Review N2: malformed input is refused with one line per rule, never a traceback."""

    def assert_lines(self, result, rule):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(result.stdout.strip(), "no problem lines")
        for line in result.stdout.splitlines():
            self.assertRegex(line, r"^[FSRG]\d: ")
        self.assertIn(rule, result.stdout)

    def test_n2_freeze_with_a_list_as_id(self):
        self.edit(self.criteria, lambda d: d["criteria"][0].update(id=["fit"]))
        self.assert_lines(run("freeze", self.criteria), "F1")

    def test_n2_score_with_malformed_frozen_parts(self):
        self.freeze()
        good = self.criteria.read_text()
        for key, value in (("weights", [["fit", 40]]), ("seals", ["x"]), ("weights", "fit=40"), ("seals", 7)):
            with self.subTest(key=key, value=value):
                self.criteria.write_text(good)
                self.edit(self.criteria, lambda d: d["frozen"].update({key: value}))
                self.assert_lines(run("score", self.criteria, self.scores), "S2")

    def test_n2_score_with_a_list_as_id_after_the_freeze(self):
        self.freeze()
        self.edit(self.criteria, lambda d: d["criteria"][0].update(id=["fit"]))
        self.assert_lines(run("score", self.criteria, self.scores), "S2")


class SkillText(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL / "SKILL.md").read_text()
        self.criteria = (SKILL / "reference" / "criteria.md").read_text()

    def test_criteria_reference_covers_every_criterion(self):
        for cid in ("fit", "soc2", "iso27001", "pentest", "dpa", "apis", "sso", "scim", "residency", "cost", "exit"):
            with self.subTest(criterion=cid):
                self.assertRegex(self.criteria, rf"(?m)^### .*`{cid}`")

    def test_security_criteria_name_the_document_that_proves_them(self):
        for cid in ("soc2", "iso27001", "pentest", "dpa"):
            with self.subTest(criterion=cid):
                block = re.search(rf"(?ms)^### .*`{cid}`.*?(?=^### |\Z)", self.criteria).group(0)
                self.assertIn("**Proves it:**", block)
                self.assertIn("**Claimed until:**", block)
        self.assertIn("not legal advice", self.criteria)

    def test_x7_without_a_shell_rule(self):
        self.assertRegex(self.skill, r"(?m)^#{2,3} Without a shell")
        self.assertIn("not run", self.skill.split("Without a shell", 1)[1])

    def test_n1_thresholds_go_to_the_decision_trail(self):
        # Review N1: the freeze seals only id and weight, so a threshold written into a criterion is unprotected.
        flat = re.sub(r"\s+", " ", self.criteria)
        self.assertNotIn("writes it into the criterion before the freeze", flat)
        self.assertRegex(flat, r"records it with the score bands in the decision trail before the freeze")
        self.assertIn("seals only the criterion IDs and weights", re.sub(r"\s+", " ", self.skill))

    def test_recheck_r2_red_flag_allows_verified_only_as_the_score_status(self):
        flags = self.skill.split("## Red flags", 1)[1].split("\n## ", 1)[0]
        self.assertIn('"verified" outside the score status', re.sub(r"\s+", " ", flags))
        self.assertNotIn('or "verified" in the report without the document', flags)

    def test_recheck_r3_freeze_sentence_and_line_lengths(self):
        flat = re.sub(r"\s+", " ", self.skill)
        self.assertNotIn("criterion names live in the decision trail", flat)
        self.assertIn("the freeze does not seal them", flat)
        # Prose wraps at 100 like the rest of the kit; code fences, tables and the frontmatter are exempt.
        fenced, long = False, []
        body = self.skill.split("\n---\n", 1)[1]
        for n, line in enumerate(body.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            elif not fenced and not line.lstrip().startswith("|") and len(line) > 100:
                long.append(n)
        self.assertEqual(long, [])
        script = SCRIPT.read_text().splitlines()
        self.assertEqual([n for n, line in enumerate(script, 1) if len(line) > 120], [])

    def test_recheck_example_scores_line_shows_expect(self):
        line = re.search(r"(?m)^Scores:.*$", (EXAMPLE / "recommendation.md").read_text()).group(0)
        self.assertIn("--expect sha256:7b959b292b4fc6247817e1ba48f8c19a6e0aabfd1122ea9f6f6e2045737303ba", line)

    def section(self, heading):
        return re.sub(r"\s+", " ", self.skill.split(heading, 1)[1].split("\n## ", 1)[0])

    def test_eval_f1_undated_sources_say_undated_and_the_read_date(self):
        # Eval finding 1: S1 left evidence undated or invented a month ("packet, 2026-11").
        part = self.section("## 3. Gather evidence")
        self.assertIn("If the source has no date, write `undated` and the date you read it", part)
        self.assertIn("`Order form (undated), read 2026-11-22`", part)
        self.assertIn("YYYY-MM-DD", part)

    def test_eval_f2_what_if_runs_on_a_copy(self):
        # Eval finding 2: what-if runs had no procedure; one ran inline Python nobody can replay.
        part = self.section("## 5. Read the result")
        for phrase in ("copy `criteria.json` and `scores.json` into a `what-if/` folder",
                       "remove `frozen` in the copy and freeze it again", "Run `score.py score` there",
                       "what-if, not the result", "Never edit the frozen files"):
            self.assertIn(phrase, part)

    def test_eval_f3_a_gate_passes_only_on_all_its_evidence(self):
        # Eval finding 3: a residency gate passed on the order-form clause alone.
        part = self.section("## 1. Agree the criteria")
        self.assertIn('A product passes a gate only on all the evidence its criterion lists under "Proves it"',
                      part)
        self.assertIn("record the gate as `claimed` or `not examined`", part)
        self.assertIn("make the missing evidence a condition with an owner", part)

    def test_eval_f4_scores_between_bands_are_named_for_the_decider(self):
        # Eval finding 4: intermediate scores were chosen where the bands define only 5 and 0.
        part = self.section("## 3. Gather evidence")
        self.assertIn("Where the agreed bands do not define a score", part)
        self.assertIn("say in the evidence line which band you applied", part)
        self.assertIn("list it for the decider in the recommendation", part)

    def test_eval_f5_outside_rules_are_cited_apart_from_the_evidence(self):
        # Eval finding 5: IAF MD 26 appeared as if it were the product's evidence.
        part = self.section("## 3. Gather evidence")
        self.assertIn("Cite outside rules or standards as such, apart from the product's evidence", part)

    def test_eval_r2_1_what_if_ranks_come_from_runs_and_cover_every_option(self):
        # Eval round 2, R2-1: rank conclusions were drawn from one partial what-if (Enterprise plan only).
        part = self.section("## 5. Read the result")
        self.assertIn("State only the ranks a what-if run printed", part)
        self.assertIn("Before you say what it would take for a claim to change the rank, run the best case "
                      "for each option the evidence allows", part)
        self.assertIn("each plan quoted or offered", part)

    def test_eval_r3_1_which_claims_a_rank_change_needs_comes_from_runs(self):
        # D-8, eval round 3, R3-1: "Calyx needs all five" was drawn from best-case runs alone.
        part = self.section("## 5. Read the result")
        # D-23, eval round 5, R5-1: the sentence now asks for both leader cases for every left-out claim.
        self.assertIn("To say which claims a rank change needs, run the case without each claim twice: once "
                      "with the leader as scored, and once with the leader's open items one band lower. "
                      "Otherwise say only what the runs printed", part)

    def test_eval_r4_1_differing_what_if_cases_are_not_merged(self):
        # D-8, eval round 4, R4-1: "only if all of these" merged a case where fewer claims sufficed.
        part = self.section("## 5. Read the result")
        # D-23, eval round 5, R5-1: "in each case" now names the two leader cases.
        self.assertIn("State what it would take in each case, or only the weakest one; never merge the cases "
                      "into one condition", part)
        self.assertIn('"None of these changes the rank" also needs a run', part)

    def test_d23_r5_1_leave_one_out_is_not_split_from_the_leader_lower_case(self):
        # D-23, eval round 5, R5-1: the old wording read as two separate sets of runs.
        part = self.section("## 5. Read the result")
        self.assertNotIn("run the case without each one, and with the leader's open items", part)

    def test_d23_r5_2_never_borrow_a_date(self):
        # D-23, eval round 5, R5-2: a date was borrowed from another line; the script cannot catch that.
        part = self.section("## 3. Gather evidence")
        self.assertIn("Never borrow a date from another line of the source.", part)
        score_part = self.section("## 4. Score with the script")
        self.assertIn("evidence with neither a YYYY-MM-DD date nor the word `undated`", score_part)

    def test_eval_r2_2_claims_need_a_condition_for_a_product_not_recommended(self):
        # Eval round 2, R2-2: a not-recommended product's rank-changing claims and its unproven gate got no owner.
        part = self.section("## 5. Read the result")
        self.assertIn("This holds for a product you do not recommend too", part)
        self.assertIn("the decider's choice to wait for the evidence or to drop the product", part)
        gate = self.section("## 1. Agree the criteria")
        self.assertIn("or a what-if puts it first", gate)

    def test_eval_r2_3_name_a_reader_only_where_the_source_says_so(self):
        # Eval round 2, R2-3: the agent wrote who read a document and when, which the fixture did not say.
        part = self.section("## 3. Gather evidence")
        self.assertIn("Name who read a document, and when, only where the source says so", part)
        self.assertIn("otherwise write `undated`, `read <date>`", part)

    def test_n3_without_a_shell_score_command_passes_expect(self):
        part = self.skill.split("## Without a shell", 1)[1].split("\n## ", 1)[0]
        self.assertRegex(part, r"score criteria\.json scores\.json --expect \S+")

    def test_n4_criteria_cites_the_standards_it_relies_on(self):
        flat = re.sub(r"\s+", " ", self.criteria)
        self.assertNotIn("No standard sets the maximum age", flat)
        self.assertIn("PCI DSS v4.0.1 requirements 11.4.2 and 11.4.3", flat)
        self.assertRegex(flat, r"three-year cycle[^.]*\(ISO/IEC 17021-1")

    def test_outside_effects_and_review_cap(self):
        self.assertIn("pre-authorizes that exact effect", self.skill)
        self.assertIn("exact plan", self.skill)
        self.assertIn("disposition policy", self.skill)


if __name__ == "__main__":
    unittest.main()

"""Tests for the crafting skill: its workspace CLI and the docs that describe it.

Run: python3 -m unittest discover -s tests -p 'test_crafting.py' -v
No network or paid calls.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "crafting"
KIT = SKILL / "scripts" / "design_kit.py"
sys.path.insert(0, str(KIT.parent))

import design_kit  # noqa: E402


def run(workdir, *args):
    return subprocess.run([sys.executable, str(KIT), *args], cwd=workdir, capture_output=True, text=True)


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.assertEqual(run(self.dir, "init", "--surfaces", "web").returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def ledger(self):
        return json.loads((self.dir / ".design" / "ledger.json").read_text())

    def test_prices_task_runs_per_row_and_refuses_over_budget(self):
        group = run(self.dir, "log", "--tool", "parallel-task.createTaskGroup", "--processor", "base-fast",
                    "--count", "8", "--note", "enrich shortlist")
        self.assertEqual(group.returncode, 0, group.stderr)
        deep = run(self.dir, "log", "--tool", "parallel-task.createDeepResearch", "--processor", "pro",
                   "--note", "state of the art")
        self.assertEqual(deep.returncode, 0, deep.stderr)
        self.assertEqual([e["usd"] for e in self.ledger()["entries"]], [0.08, 0.10])

        ultra = run(self.dir, "log", "--tool", "parallel-task.createDeepResearch", "--processor", "ultra",
                    "--note", "too deep")
        self.assertEqual(ultra.returncode, 2)
        self.assertIn("over budget", ultra.stderr)
        self.assertEqual(len(self.ledger()["entries"]), 2, "a refused call must not be recorded")

        approved = run(self.dir, "log", "--tool", "parallel-task.createDeepResearch", "--processor", "ultra",
                       "--note", "user approved", "--approved")
        self.assertEqual(approved.returncode, 0, approved.stderr)
        self.assertTrue(self.ledger()["entries"][-1]["approved_over_budget"])
        self.assertIn("$0.480 of $0.30", run(self.dir, "spend").stdout)

    def test_paid_task_needs_a_known_processor(self):
        for extra in ([], ["--processor", "turbo"]):
            result = run(self.dir, "log", "--tool", "parallel-task.createDeepResearch", "--note", "x", *extra)
            self.assertEqual(result.returncode, 1)
            self.assertIn("--processor", result.stderr)
        self.assertEqual(self.ledger()["entries"], [])

    def test_firecrawl_credits_and_mobbin_searches_have_their_own_caps(self):
        self.assertEqual(run(self.dir, "log", "--tool", "firecrawl.firecrawl_scrape", "--credits", "10",
                             "--note", "five refs").returncode, 0)
        self.assertEqual(run(self.dir, "log", "--tool", "firecrawl.firecrawl_scrape", "--credits", "6",
                             "--note", "one more").returncode, 2)
        self.assertEqual(run(self.dir, "log", "--tool", "mobbin.search_screens", "--count", "10",
                             "--note", "screens").returncode, 0)
        self.assertEqual(run(self.dir, "log", "--tool", "mobbin.search_flows", "--note", "flows").returncode, 2)
        spend = run(self.dir, "spend").stdout
        self.assertIn("Firecrawl credits: 10 of 15", spend)
        self.assertIn("Parallel (USD): $0.000", spend)


class Coverage(unittest.TestCase):
    def test_check_reports_each_gap_and_passes_once_states_are_covered(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            self.assertEqual(run(work, "init", "--surfaces", "web,cli").returncode, 0)
            design = work / ".design"
            (design / "mockups").mkdir(exist_ok=True)
            states = {}
            for state in design_kit.required_states("web"):
                (design / "mockups" / f"{state}.png").write_bytes(b"png")
                states[state] = {"mockup": f"mockups/{state}.png"}
            states["empty"] = {"skip": ""}
            states["dark"] = {"mockup": "mockups/missing.png"}
            del states["narrow"]
            touchpoint = {"id": "pricing-page", "surface": "web", "job": "Choose a plan", "states": states,
                          "interactions": [{"id": "toggle", "trigger": "click", "feedback": "slides",
                                            "motion": "quick"}]}
            path = design / "touchpoints.json"
            data = json.loads(path.read_text())
            data["touchpoints"] = [touchpoint]
            data["journeys"] = [{"id": "choose-plan", "actor": "Millennial founder at a desk",
                                 "goal": "Pick a plan in one sitting", "steps": ["pricing-page", "checkout"]}]
            path.write_text(json.dumps(data))

            result = run(work, "check")
            self.assertEqual(result.returncode, 1)
            gaps = [line for line in result.stdout.splitlines() if line.startswith("gap:")]
            for expected in ("missing required state 'narrow'", "pricing-page.empty: needs a mockup path",
                             "mockups/missing.png not found", "toggle is missing reduced_motion",
                             "surface cli has no touchpoints",
                             "journey choose-plan: step 'checkout' is not a touchpoint id"):
                self.assertTrue(any(expected in gap for gap in gaps), f"{expected!r} not in {gaps}")
            self.assertEqual(len(gaps), 6, gaps)

            states["empty"] = {"skip": "Pricing always has plans"}
            states["dark"] = {"mockup": "mockups/dark.png"}
            states["narrow"] = {"mockup": "mockups/ideal.png"}
            touchpoint["interactions"][0]["reduced_motion"] = "instant swap"
            data["surfaces"] = ["web"]
            data["journeys"][0]["steps"] = ["pricing-page"]
            path.write_text(json.dumps(data))
            result = run(work, "check")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("1 touchpoints, 6 states mocked, 1 skipped", result.stdout)

    def test_init_rejects_unknown_surfaces_and_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(tmp, "init", "--surfaces", "web,watchos").returncode, 1)
            self.assertFalse((Path(tmp) / ".design").exists(), "a rejected init must not create files")
            self.assertEqual(run(tmp, "init", "--surfaces", "ios").returncode, 0)
            ledger = Path(tmp) / ".design" / "ledger.json"
            ledger.write_text('{"budget": {"usd": 1}, "entries": []}')
            self.assertEqual(run(tmp, "init", "--surfaces", "ios").returncode, 0)
            self.assertEqual(json.loads(ledger.read_text())["budget"], {"usd": 1})


class Docs(unittest.TestCase):
    def test_skill_metadata_size_and_links(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertLess(len(text.splitlines()), 500)
        self.assertRegex(text, r"\A---\nname: crafting\ndescription: \"[^\n]+\"\n---\n")
        for target in re.findall(r"\]\((reference/[a-z-]+\.md)", text):
            self.assertTrue((SKILL / target).is_file(), target)
        for required in ("grilling", "Gen Alpha", "agent-experience.md", "audiences.md"):
            self.assertIn(required, text)

    def test_documented_commands_and_flags_exist(self):
        docs = (SKILL / "SKILL.md").read_text() + (SKILL / "reference" / "research.md").read_text()
        for command, flags in re.findall(r"\$K ([a-z]+)([^\n#]*)", docs):
            help_text = run(ROOT, command, "--help")
            self.assertEqual(help_text.returncode, 0, f"{command}: {help_text.stderr}")
            for flag in re.findall(r"(--[a-z][a-z-]*)", flags):
                self.assertIn(flag, help_text.stdout, f"{command} has no {flag}")

    def test_required_states_table_matches_the_checker(self):
        table = (SKILL / "reference" / "states.md").read_text().split("## Required states by surface", 1)[1]
        documented = {}
        for cells in re.findall(r"^\| (.+?) \| (.+?) \|$", table, re.M):
            for surface in re.findall(r"`([a-z]+)`", cells[0]):
                documented[surface] = set(re.findall(r"`([a-z-]+)`", cells[1]))
        for surface, extra in design_kit.SURFACE_STATES.items():
            self.assertEqual(documented.get(surface), set(extra), surface)

    def test_budget_table_matches_the_ledger_defaults(self):
        text = (SKILL / "SKILL.md").read_text()
        budget = design_kit.DEFAULT_BUDGET
        self.assertIn(f"| Parallel Task | ${budget['usd']:.2f} |", text)
        self.assertIn(f"| Firecrawl | {budget['firecrawl_credits']} credits |", text)
        self.assertIn(f"| Mobbin | {budget['mobbin_searches']} searches", text)


if __name__ == "__main__":
    unittest.main()

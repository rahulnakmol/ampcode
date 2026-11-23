"""Tests for the wave items in skills/delivering: W20, W21.6 and W22.

Run: python3 -m unittest tests.test_wave_delivering -v

W20 and W21.6 read the skill text section by section, so a phrase in the wrong place does not
count. W22 runs the documented delivery step from reference/mission-record.md on a copy of
grooming's product example, then runs backlog.py on the result. Every expected value is written
out by hand from the example, never taken from backlog.py.
W20.5 is the fix mission's own tests (tests.test_contract_kit, tests.test_missioning), run
beside this module.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "delivering"
SKILL_MD = SKILL / "SKILL.md"
REVIEW_REF = SKILL / "reference" / "review-and-recovery.md"
RECORD_REF = SKILL / "reference" / "mission-record.md"
WATCH_REF = SKILL / "reference" / "hosts-pr-watch.md"
WATCH_SCRIPT = SKILL / "scripts" / "pr_watch.py"
GROOMING = ROOT / "skills" / "grooming"
BACKLOG_PY = GROOMING / "scripts" / "backlog.py"
PRODUCT = GROOMING / "reference" / "examples" / "product.json"


def flat(text):
    """Text with line wraps and runs of spaces collapsed to one space."""
    return " ".join(text.split())


def section(text, heading):
    """The body under a Markdown heading, up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.splitlines()
    start = lines.index(heading) + 1
    for end in range(start, len(lines)):
        if re.match(rf"#{{1,{level}}} ", lines[end]):
            return "\n".join(lines[start:end])
    return "\n".join(lines[start:])


def numbered_items(text):
    """Top-level numbered list items ('1. ...' and their indented lines), flattened."""
    items, current = [], None
    for line in text.splitlines():
        if re.match(r"\d+\. ", line):
            current = [line]
            items.append(current)
        elif current is not None and (line.startswith("   ") or not line.strip()):
            current.append(line)
        else:
            current = None
    return [flat("\n".join(item)) for item in items]


def skill_text():
    return SKILL_MD.read_text()


def gates_section():
    return section(skill_text(), "### The milestone gates")


def gate(number):
    found = [i for i in numbered_items(gates_section()) if f"**Gate {number}:**" in i]
    assert len(found) == 1, f"gate {number} is not one numbered step"
    return found[0]


class W20InterrogatingChanges(unittest.TestCase):
    def test_W20_1_both_gates_name_interrogating_changes(self):
        for number in (1, 2):
            with self.subTest(gate=number):
                self.assertIn("`interrogating-changes`", gate(number))

    def test_W20_1_gates_name_the_ledger_and_its_script(self):
        text = flat(gates_section())
        self.assertIn("review_ledger.py", text)
        self.assertIn("ledger", gate(1))
        self.assertIn("ledger", gate(2))

    def test_W20_1_review_cap_names_interrogating_changes(self):
        cap = flat(section(skill_text(), "### The review cap: the disposition policy"))
        self.assertIn("`interrogating-changes`", cap)
        self.assertIn("disposition policy", cap)

    def test_W20_1_reference_gates_name_interrogating_changes_and_ledger(self):
        gates = flat(section(REVIEW_REF.read_text(), "## Milestone gates"))
        self.assertIn("`interrogating-changes`", gates)
        self.assertIn("review_ledger.py check", gates)
        self.assertIn("review_ledger.py verdict", gates)

    def test_W20_2_gate_two_runs_floor_guard_and_an_unaccepted_flag_blocks(self):
        two = gate(2)
        self.assertIn("floor_guard.py", two)
        self.assertRegex(two, r"flag without an accepted reason (blocks|is a finding)")
        self.assertNotIn("floor_guard.py", gate(1))

    def test_W20_2_reference_says_an_unaccepted_flag_is_at_least_a_major(self):
        gates = flat(section(REVIEW_REF.read_text(), "## Milestone gates"))
        self.assertIn("git diff <base>...<head> | python3 <ic>/scripts/floor_guard.py", gates)
        self.assertRegex(gates, r"flag without an accepted reason is a finding .*at least a Major")
        self.assertIn('--accept <id>="<reason>"', gates)

    def test_W20_3_a_verdict_on_another_patch_id_is_stale(self):
        text = flat(gates_section())
        self.assertIn("patch ID", text)
        self.assertIn("A verdict on another patch ID is stale", text)
        ref = flat(section(REVIEW_REF.read_text(), "## Milestone gates"))
        self.assertIn("A verdict on another patch ID is stale", ref)

    def test_W20_4_fallback_sentence_verbatim(self):
        sentence = ("If `interrogating-changes` is not installed, use the lenses in "
                    "reference/review-and-recovery.md and label the review manual.")
        self.assertIn(sentence, flat(skill_text()))

    def test_W20_4_reference_still_holds_the_fallback_lenses(self):
        gates = section(REVIEW_REF.read_text(), "## Milestone gates")
        for lens in ("Correctness", "Permissions/isolation", "Secrets/dependencies", "Concurrency",
                     "Data preservation", "Operations"):
            with self.subTest(lens=lens):
                self.assertRegex(gates, rf"(?m)^\| {re.escape(lens)} \|")
        self.assertIn("manual", flat(gates))

    def test_W20_gate1_F10_gate_can_pass_on_changes_needed_only_for_filed_outside_findings(self):
        self.assertIn("A gate passes while `review_ledger.py verdict` says `changes needed` only when every "
                      "open Blocker or Major is outside the case list and the milestone's criteria and is filed.",
                      flat(gates_section()))

    def test_W20_gate2_F13_repair_reruns_gates_and_a_patch_keeping_rebase_keeps_verdicts(self):
        text = flat(gates_section())
        # The fix mission's sentence stays word for word.
        self.assertIn("A repair makes a new head: both gates run again on it, and earlier reviews and "
                      "evidence lapse.", text)
        self.assertIn("A repair changes the patch ID, so both gates run again. A rebase that keeps the patch "
                      "ID keeps the gates' verdicts, because they bind to the patch ID;", text)
        self.assertIn("CI run again on the new head", text)
        ref = flat(REVIEW_REF.read_text())
        self.assertNotIn("lapses both gates even when a clean rebase keeps the patch ID", ref)
        self.assertNotIn("A new head voids them", ref)
        self.assertIn("A rebase that keeps the patch ID keeps the gates' verdicts", ref)
        self.assertIn("A manual review has no patch-bound verdict, so any new head voids it.", ref)

    def test_W20_6_integration_step_names_releasing_as_an_outside_effect(self):
        merge = [i for i in numbered_items(gates_section()) if "Squash-merge into `dev`" in i]
        self.assertEqual(len(merge), 1)
        self.assertIn("`releasing`", merge[0])
        self.assertIn("after `dev`", merge[0])
        self.assertIn("outside effect", merge[0])
        self.assertIn("stop reason 2", merge[0])


class W21ShipAndStop(unittest.TestCase):
    def variants(self):
        return flat(section(skill_text(), "### Ship or stop"))

    def test_W21_6_stop_never_merges_and_disables_auto_merge(self):
        stop = re.search(r"\*\*Stop:\*\*(.*?)(?=\*\*Ship:\*\*|$)", self.variants()).group(1)
        self.assertIn("never merges", stop)
        self.assertIn("`gh pr merge --disable-auto`", stop)

    def test_W21_gate1_F9_stop_is_the_default_and_its_auto_merge_write_is_covered(self):
        text = self.variants()
        self.assertIn("When it names none, the variant is stop.", text)
        self.assertIn("Running `gh pr merge --disable-auto` is part of choosing stop: an effect the stop "
                      "variant needs, recorded under Effects performed.", text)
        self.assertIn("If the contract does not pre-authorize writes to the PR, the stop variant only "
                      "leaves the PR open and reports that auto-merge was not checked.", text)
        self.assertNotIn("a contract that pre-authorizes the milestone merges ships", text)
        ref = flat(section(WATCH_REF.read_text(), "## Stop"))
        self.assertIn("auto-merge was not checked", ref)
        self.assertNotIn("the contract's choice of the stop variant covers it", ref)

    def test_W21_6_ship_merges_when_green_only_as_pre_authorized(self):
        ship = re.search(r"\*\*Ship:\*\*(.*?)(?=\*\*Stop:\*\*|$)", self.variants()).group(1)
        self.assertIn("green", ship)
        self.assertIn("pre-authorizes", ship)
        self.assertIn("stop reason 2", ship)

    def test_W21_wait_step_keeps_hosts_md_and_names_the_watcher(self):
        wait = [i for i in numbered_items(gates_section()) if "Wait for PR and CI results" in i]
        self.assertEqual(len(wait), 1)
        self.assertIn("(../missioning/reference/hosts.md)", wait[0])
        self.assertIn("`scripts/pr_watch.py`", wait[0])
        self.assertIn("(reference/hosts-pr-watch.md)", wait[0])
        self.assertIn("without Amp's GitHub events", wait[0])

    def test_W21_watch_reference_uses_only_real_options(self):
        text = WATCH_REF.read_text()
        helped = subprocess.run([sys.executable, str(WATCH_SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(helped.returncode, 0)
        used = set(re.findall(r"pr_watch\.py[^\n`]*", text))
        self.assertTrue(used, "the reference shows no pr_watch.py command")
        for command in used:
            for option in re.findall(r"--[a-z-]+", command):
                with self.subTest(option=option):
                    self.assertIn(option, helped.stdout)
        self.assertIn("gh pr merge <number> --repo OWNER/NAME --disable-auto", text)


def documented_blocks():
    """The fenced bash blocks of the delivery section, which must be the last ## section.

    Blocks inside a numbered list are indented; they are dedented as a reader copies them."""
    text = RECORD_REF.read_text()
    headings = re.findall(r"(?m)^## .*$", text)
    assert headings[-1] == "## Delivery evidence into backlog.json", headings[-1]
    body = section(text, "## Delivery evidence into backlog.json")
    return [textwrap.dedent(b) for b in re.findall(r"```bash\n(.*?)\n[ \t]*```", body, re.S)]


class W22DeliveryRecord(unittest.TestCase):
    PR = "https://github.com/acme/onboarding/pull/41"
    TEST = "python3 -m unittest tests.test_csv_import -v"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.backlog = self.tmp / "backlog.json"
        shutil.copy(PRODUCT, self.backlog)
        blocks = documented_blocks()
        self.variables = next(b for b in blocks if b.lstrip().startswith("export "))
        self.write = next(b for b in blocks if "python3 - <<'EOF'" in b)
        self.check = next(b for b in blocks if "backlog.py validate" in b)

    def run_step(self, criteria):
        env = dict(os.environ, BACKLOG=str(self.backlog), ITEM="S-1", AT="2026-11-23", PR=self.PR,
                   TEST=self.TEST, CRITERIA=json.dumps(criteria))
        return subprocess.run(["bash", "-c", self.write], env=env, capture_output=True, text=True)

    def run_checks(self):
        results = []
        for line in self.check.strip().splitlines():
            command = line.replace("<grooming>", str(GROOMING)).replace('"$BACKLOG"', str(self.backlog))
            results.append(subprocess.run(command, shell=True, capture_output=True, text=True))
        return results

    def test_W22_documented_variables_are_the_ones_the_step_reads(self):
        names = set(re.findall(r"\b([A-Z]+)=", self.variables))
        self.assertEqual(names, {"BACKLOG", "ITEM", "AT", "PR", "TEST", "CRITERIA"})
        for name in names:
            with self.subTest(name=name):
                self.assertIn(f'os.environ["{name}"]', self.write)

    def test_W22_1_step_writes_a_record_validate_accepts_and_trace_shows_delivered(self):
        done = self.run_step({"S-1.1": "met", "S-1.2": "met", "S-1.3": "met"})
        self.assertEqual(done.returncode, 0, done.stderr)
        story = next(i for i in json.loads(self.backlog.read_text())["items"] if i["id"] == "S-1")
        self.assertEqual(story["delivery"], {
            "at": "2026-11-23",
            "evidence": [self.PR, "Test command: " + self.TEST],
            "criteria": {"S-1.1": "met", "S-1.2": "met", "S-1.3": "met"},
        })
        validate, trace = self.run_checks()
        self.assertEqual(validate.returncode, 0, validate.stdout)
        self.assertIn("0 errors, 1 warnings; 4/5 stories and bugs ready", validate.stdout)
        # The example's features are not synced, so trace still lists sign-off gaps and exits 1.
        self.assertIn("| S-1 Admin uploads a CSV and sees row-level validation | F-1 | ready | delivered | AC-1 |",
                      trace.stdout)
        # F-1 holds S-1 (3 criteria), S-2 (2) and B-1 (2): 1 of 2 stories, 3 of 7 checks met.
        self.assertIn("| F-1 Admins import their team from a CSV | G-1 | 4.8 | not synced | 1/2 | 3/7 |",
                      trace.stdout)
        self.assertNotIn("S-1 partial", trace.stdout)

    def test_W22_1_a_not_met_criterion_stays_visible(self):
        self.run_step({"S-1.1": "met", "S-1.2": "not met", "S-1.3": "met"})
        validate, trace = self.run_checks()
        self.assertEqual(validate.returncode, 0, validate.stdout)
        self.assertIn("| S-1 Admin uploads a CSV and sees row-level validation | F-1 | ready | partial: S-1.2 not met | AC-1 |",
                      trace.stdout)
        self.assertIn("- S-1 partial: S-1.2 not met", trace.stdout)
        self.assertEqual(trace.returncode, 1)

    def test_W22_2_a_record_with_a_missing_criterion_is_refused(self):
        self.run_step({"S-1.1": "met", "S-1.2": "met"})
        validate, trace = self.run_checks()
        self.assertEqual(validate.returncode, 1)
        self.assertIn("error   S-1: delivery criteria must list exactly ['S-1.1', 'S-1.2', 'S-1.3']", validate.stdout)
        self.assertEqual(trace.returncode, 2)
        self.assertIn("1 contract errors", trace.stderr)

    def test_W22_gate1_F2_record_step_runs_right_after_each_milestone_merge(self):
        steps = numbered_items(gates_section())
        merge = next(n for n, s in enumerate(steps) if "Squash-merge into `dev`" in s)
        record = [n for n, s in enumerate(steps) if "delivery record" in s]
        report = next(n for n, s in enumerate(steps) if "Send the checkpoint report" in s)
        self.assertEqual(record, [merge + 1], "the record step is not the one right after the merge")
        self.assertLess(record[0], report)
        step = steps[record[0]]
        for words in ("`grooming`", "the milestone PR", "the test command", "`backlog.py validate`",
                      "`trace`", "under stop, after its gates pass",
                      "(reference/mission-record.md#delivery-evidence-into-backlogjson)"):
            with self.subTest(words=words):
                self.assertIn(words, step)

    def test_W22_gate1_F2_close_out_only_checks_the_records(self):
        close = flat(section(skill_text(), "## J5 Close out"))
        self.assertIn("check that every story or bug each milestone delivered has its delivery record", close)
        self.assertNotIn("Before the report, record each", close)

    def test_W22_gate1_F2_reference_records_after_each_merge_not_at_close_out(self):
        body = flat(section(RECORD_REF.read_text(), "## Delivery evidence into backlog.json"))
        self.assertIn("right after the milestone merges into `dev` (under stop, after its gates pass)", body)
        self.assertNotIn("record each one at close-out", body)
        self.assertIn("At close-out, only check", body)


if __name__ == "__main__":
    unittest.main()

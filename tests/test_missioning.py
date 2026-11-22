"""Tests for skills/missioning: the mission file checker and the playbook set.

Run: python3 -m unittest tests.test_missioning -v
"""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "missioning"
SCRIPT = SKILL / "scripts" / "ledger_check.py"
CHARTER = SKILL / "reference" / "charter.md"
BRIEF = ROOT / "evals" / "briefing-decisions" / "brief.md"  # passes brief_check.py
sys.path.insert(0, str(SCRIPT.parent))

import ledger_check  # noqa: E402

GOOD = """# Mission: security review of acme/payments

## Charter

- **Outcome:** A security review report for acme/payments before the March release.
- **Decision owner:** Rahul Nakmol
- **Approvers:** Priya Shah (@priya-s)
- **Success criteria:** Every finding has evidence, severity, owner and disposition.
- **Definition of Done:** Critical and High findings are fixed and retested,
  or accepted in writing.
- **Budget:** 3 review rounds per gate; 2 working days.
- **Budget used:** unknown: no usage telemetry on this host.
- **May do without asking:** read code, run the allowed scanners, draft reports.
- **Always ask:** scanning anything outside acme/payments; releasing the report.
- **Stop and ask when:** a check cannot prove a finding, or scope must change.
- **Playbook:** security-review
- **Host:** Claude Code

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Charter and criteria | human | passed | charter above | reviews/charter-novice.md | briefs/charter.md | Rahul Nakmol | question: AskUserQuestion answer "Approve" | 2026-11-18 |
| Threat model | agent | passed | threat-model.md, 14 threats | none needed: no decision, checked by scope gate | - | - | - | 2026-11-19 |
| Scope and rules of engagement | human | pending | - | - | briefs/scope.md | - | - | - |
| Report release | human | open | - | - | - | - | - | - |

## Decision trail

| Date | Decision | Why | Evidence | Decider |
| --- | --- | --- | --- | --- |
| 2026-11-18 | Use the security-review playbook | Owner asked for a security review | charter | Rahul Nakmol |
"""

PASSED = "| Charter and criteria | human | passed | charter above | reviews/charter-novice.md | briefs/charter.md | Rahul Nakmol | question: AskUserQuestion answer \"Approve\" | 2026-11-18 |"
AGENT = "| Threat model | agent | passed | threat-model.md, 14 threats | none needed: no decision, checked by scope gate | - | - | - | 2026-11-19 |"


def workspace(tmp):
    """Create the brief and review files the GOOD mission file names."""
    base = Path(tmp)
    (base / "briefs").mkdir()
    (base / "reviews").mkdir()
    shutil.copy(BRIEF, base / "briefs" / "charter.md")
    (base / "reviews" / "charter-novice.md").write_text("Novice reader: all four answers correct.\n")
    return base


def edit(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new, 1)


class Rules(unittest.TestCase):
    def rules(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            return sorted({p.split(":", 1)[0] for p in ledger_check.check(text, workspace(tmp))})

    def assertRule(self, text, rule):
        self.assertEqual(self.rules(text), [rule])

    def test_good_file_passes(self):
        self.assertEqual(self.rules(GOOD), [])

    def test_r1_charter_fields(self):
        self.assertRule(edit("- **Budget used:** unknown: no usage telemetry on this host.\n", ""), "R1")
        self.assertRule(edit("Priya Shah (@priya-s)", "TBD"), "R1")
        self.assertRule(edit("- **Playbook:**", "- **Outcome:** again\n- **Playbook:**"), "R1")
        self.assertRule(edit("Priya Shah (@priya-s)", "<approver name>"), "R1")
        self.assertRule(edit("- **Outcome:**", "- **outcome:**"), "R1")
        # People fields hold names, not prose; "none" means no approver besides the owner.
        self.assertRule(edit("Priya Shah (@priya-s)", "Priya Shah only (asked in round 1, Q2). Security gives input, not approval."), "R1")
        self.assertRule(edit("- **Decision owner:** Rahul Nakmol", "- **Decision owner:** Rahul Nakmol (product owner)"), "R1")
        self.assertEqual(self.rules(edit("Priya Shah (@priya-s)", "Priya Shah (@priya-s), Tom O'Neil, @tokafor")), [])
        self.assertEqual(self.rules(edit("Priya Shah (@priya-s)", "none")), [])
        self.assertIn("R1", self.rules(edit("- **Decision owner:** Rahul Nakmol", "- **Decision owner:** none")))
        # "todo" in prose is not a placeholder; "<what: fill in>" is not an autolink.
        self.assertEqual(self.rules(edit("draft reports.", "draft reports, update the todo list.")), [])
        self.assertRule(edit("draft reports.", "<actions: list them>"), "R1")
        # A whole value of tbd is a placeholder in any case, and is never a person.
        self.assertRule(edit("A security review report for acme/payments before the March release.", "tbd"), "R1")
        self.assertIn("R1", self.rules(edit("Priya Shah (@priya-s)", "Tbc")))
        # The Decision owner is one person: a second name would let them answer for each other.
        self.assertRule(edit("- **Decision owner:** Rahul Nakmol", "- **Decision owner:** Rahul Nakmol, Priya Shah"), "R1")
        self.assertRule(edit("Priya Shah (@priya-s)", "none", edit(PASSED, PASSED.replace("Rahul Nakmol", "none"))), "R6")
        # An autolink is a value, not a placeholder; a two-line value is joined.
        self.assertEqual(self.rules(edit("before the March release.", "before the March release, see <https://example.com/plan>.")), [])

    def test_r2_host_and_playbook(self):
        self.assertRule(edit("- **Host:** Claude Code", "- **Host:** Cursor"), "R2")
        self.assertRule(edit("- **Playbook:** security-review", "- **Playbook:** security"), "R2")
        self.assertEqual(self.rules(edit("- **Playbook:** security-review", "- **Playbook:** none: one-off review")), [])
        self.assertEqual(self.rules(edit("- **Host:** Claude Code", "- **Host:** copilot app")), [])

    def test_r3_budget_names_a_limit(self):
        self.assertRule(edit("3 review rounds per gate; 2 working days.", "as needed"), "R3")
        self.assertRule(edit("3 review rounds per gate; 2 working days.", "no limit on tokens"), "R3")
        self.assertEqual(self.rules(edit("3 review rounds per gate; 2 working days.", "no limit on tokens, decided by Rahul Nakmol")), [])
        self.assertRule(edit("3 review rounds per gate; 2 working days.", "unlimited (agreed 18 Nov)"), "R3")
        self.assertRule(edit("3 review rounds per gate; 2 working days.", "no limit on tokens; 3 review rounds"), "R3")

    def test_r4_ledger_table(self):
        self.assertRule(edit("| Gate | Kind | State |", "| Gate | State | Kind |"), "R4")
        no_rows = re.sub(r"\| (Charter and|Threat|Scope|Report).*\n", "", GOOD)
        self.assertRule(no_rows, "R4")
        # A separator with fewer cells than the header is not a table on GitHub either.
        self.assertRule(edit("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n", "| --- | --- |\n"), "R4")
        # GitHub renders a line without outer pipes right after a table as a row; check it too.
        unpiped = "Report release | human | passed | x | - | - | Rahul Nakmol | chat: lgtm | 2026-11-20\n"
        self.assertIn("R7", self.rules(edit("| Report release | human | open | - | - | - | - | - | - |\n", "| Report release | human | open | - | - | - | - | - | - |\n" + unpiped)))
        # A second ledger is never skipped: the file fails, even when the first copy holds the
        # bad row, and under a heading that only looks different.
        chat_row = AGENT.replace("| agent | passed |", "| human | passed |").replace("none needed: no decision, checked by scope gate", "reviews/charter-novice.md").replace("| - | - | - |", "| briefs/charter.md | Rahul Nakmol | chat: looks good |")
        second = "\n## Gate Ledger (continued)\n\n| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n" + AGENT + "\n"
        self.assertIn("R4", self.rules(GOOD + second))
        self.assertIn("R4", self.rules(edit(AGENT, chat_row) + second))
        # A row after a blank line in the ledger, or a second table there, fails rather than hides.
        self.assertIn("R4", self.rules(edit(AGENT + "\n", AGENT + "\n\n" + chat_row + "\n")))
        self.assertIn("R1", self.rules(GOOD + "\n## Charter\n\n- **Outcome:** another\n"))
        # Without the separator line the first row would be read as one; it must fail, not hide.
        chat_first = edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "chat: said looks good"))
        self.assertRule(chat_first.replace("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n", "", 1), "R4")

    def test_r5_kind_and_state(self):
        self.assertRule(edit("| human | passed |", "| human | approved |"), "R5")
        self.assertRule(edit("| Report release | human |", "| Report release | owner |"), "R5")
        self.assertRule(edit("| human | open |", "| human | Open |"), "R5")
        # Recording the charter as an agent gate must not let a chat reply pass it.
        as_agent = PASSED.replace("| human |", "| agent |").replace("reviews/charter-novice.md", "none needed: owner said looks good")
        self.assertRule(edit(PASSED, as_agent), "R5")
        self.assertRule(edit(PASSED, as_agent.replace("Charter and criteria", "Mission charter")), "R5")
        # Only the mission's charter gate is human by rule; other gates may mention a charter.
        self.assertEqual(self.rules(edit(AGENT, AGENT.replace("Threat model", "Initiative charter drafted"))), [])

    def test_r6_decider_and_source(self):
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "Sam Lee")), "R6")
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "Rahul")), "R6")
        # A Decider copied as written in the charter, with its handle, is the same person; a name
        # and another person's handle, or a note in parentheses, is not.
        signed = PASSED.replace('question: AskUserQuestion answer "Approve"', "tracker: GitHub /approve on acme/payments#12")
        self.assertEqual(self.rules(edit(PASSED, signed.replace("Rahul Nakmol", "Priya Shah (@priya-s)"))), [])
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "Rahul Nakmol (@priya-s)")), "R6")
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "Rahul Nakmol (for Priya Shah)")), "R6")
        # Only the person in the session answers its question tool or dialog: that is the owner.
        tracker = 'tracker: GitHub /approve on acme/payments#12'
        self.assertEqual(self.rules(edit(PASSED, PASSED.replace("Rahul Nakmol", "@priya-s").replace('question: AskUserQuestion answer "Approve"', tracker))), [])
        self.assertEqual(self.rules(edit(PASSED, PASSED.replace("Rahul Nakmol", "Rahul Nakmol, priya shah").replace('question: AskUserQuestion answer "Approve"', "written: signed memo 18 Nov"))), [])
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "@priya-s")), "R6")
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "Rahul Nakmol, priya shah")), "R6")
        dialog = PASSED.replace('question: AskUserQuestion answer "Approve"', "dialog: Amp mission-control design approval")
        self.assertRule(edit(PASSED, dialog.replace("Rahul Nakmol", "@priya-s")), "R6")
        stamped = PASSED.replace('question: AskUserQuestion answer "Approve"', "dialog: owner stamped it")
        self.assertRule(edit(PASSED, stamped), "R6")
        self.assertRule(edit(PASSED, PASSED.replace("Rahul Nakmol", "-")), "R6")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "dialog: owner dialog")), "R6")
        self.assertEqual(self.rules(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "dialog: Amp mission-control design approval"))), [])
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "question:")), "R6")
        waived_agent = AGENT.replace("| passed |", "| waived |").replace("threat-model.md, 14 threats", "owner skipped: no attack surface")
        self.assertRule(edit(AGENT, waived_agent), "R6")
        self.assertEqual(self.rules(edit(AGENT, waived_agent.replace("| - | - | 2026-11-19 |", "| Rahul Nakmol | written: email 19 Nov | 2026-11-19 |"))), [])
        self.assertRule(edit(AGENT, waived_agent.replace("| - | - | 2026-11-19 |", '| @priya-s | question: AskUserQuestion answer "Skip" | 2026-11-19 |')), "R6")

    def test_r7_chat_is_never_an_approval(self):
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "chat: said looks good")), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "slack: thumbs up")), "R7")
        # A real kind does not launder a chat reply.
        self.assertRule(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', 'chat reply "looks good"')), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', "owner said it in Chat")), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', 'written: Slack message "Looks good"')), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', "owner replied LGTM")), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', 'written: Slack DM "approved"')), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', "approved in conversation")), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', 'written: DM "ok"')), "R7")
        # The host's name is not chat: Copilot Chat's question tool is a real source.
        self.assertEqual(self.rules(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', 'ask_user in Copilot Chat, answer "A"'))), [])
        self.assertRule(edit(PASSED, PASSED.replace('AskUserQuestion answer "Approve"', 'owner replied "yes" in Copilot Chat')), "R7")
        self.assertRule(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', 'written: ask_user in Copilot Chat')), "R7")

    def test_r8_brief(self):
        self.assertRule(edit("briefs/charter.md", "briefs/missing.md"), "R8")
        self.assertRule(edit("briefs/charter.md", "https://ampcode.com/artifacts/brief"), "R8")
        with tempfile.TemporaryDirectory() as tmp:
            base = workspace(tmp)
            absolute = str(base / "briefs" / "charter.md")
            self.assertIn("R8", {p.split(":", 1)[0] for p in ledger_check.check(edit("briefs/charter.md", absolute), base)})
        self.assertEqual(self.rules(edit("briefs/charter.md", "briefs/charter.md (https://ampcode.com/artifacts/brief)")), [])
        with tempfile.TemporaryDirectory() as tmp:
            base = workspace(tmp)
            shutil.copy(BRIEF, base / "briefs" / "charter.txt")
            self.assertIn("R8", {p.split(":", 1)[0] for p in ledger_check.check(edit("briefs/charter.md", "briefs/charter.txt"), base)})
        with tempfile.TemporaryDirectory() as tmp:
            base = workspace(tmp)
            text = (base / "briefs" / "charter.md").read_text()
            (base / "briefs" / "charter.md").write_text(text.replace("## How to undo it", "## Undo"))
            self.assertEqual(sorted({p.split(":", 1)[0] for p in ledger_check.check(GOOD, base)}), ["R8"])

    def test_r8_brief_checker_failure_is_reported(self):
        # A brief checker that crashes with only stderr still gives an R8 line, not a traceback.
        with tempfile.TemporaryDirectory() as tmp:
            base = workspace(tmp)
            crash = base / "crash.py"
            crash.write_text("import sys\nsys.stderr.write('boom\\n')\nsys.exit(1)\n")
            original = ledger_check.brief_checker
            ledger_check.brief_checker = lambda: crash
            try:
                problems = ledger_check.check(GOOD, base)
            finally:
                ledger_check.brief_checker = original
            self.assertEqual([p.split(":", 1)[0] for p in problems], ["R8"])
            self.assertIn("boom", problems[0])

    def test_r9_review(self):
        self.assertRule(edit("reviews/charter-novice.md", "not run"), "R9")
        self.assertRule(edit("reviews/charter-novice.md", "reviews/absent.md"), "R9")
        self.assertRule(edit(AGENT, AGENT.replace("none needed: no decision, checked by scope gate", "-")), "R9")
        self.assertEqual(self.rules(edit("reviews/charter-novice.md", "https://ampcode.com/artifacts/review")), [])
        self.assertRule(edit("reviews/charter-novice.md", "none needed: owner is sure"), "R9")
        self.assertRule(edit("reviews/charter-novice.md", "https://"), "R9")
        self.assertRule(edit("reviews/charter-novice.md", "http://example.com/review"), "R9")
        self.assertRule(edit("reviews/charter-novice.md", "briefs/charter.md"), "R9")

    def test_r10_agent_evidence(self):
        self.assertRule(edit(AGENT, AGENT.replace("threat-model.md, 14 threats", "-")), "R10")
        self.assertRule(edit(AGENT, AGENT.replace("threat-model.md, 14 threats", "TBD")), "R10")

    def test_r11_waived_needs_reason(self):
        waived = PASSED.replace("| passed | charter above |", "| waived | - |")
        self.assertRule(edit(PASSED, waived), "R11")
        self.assertRule(edit(PASSED, PASSED.replace("| passed | charter above |", "| waived | TODO |")), "R11")

    def test_r12_decision_trail(self):
        self.assertRule(edit("| charter | Rahul Nakmol |", "| charter |  |"), "R12")
        self.assertRule(GOOD[: GOOD.index("## Decision trail")], "R12")


class Files(unittest.TestCase):
    def test_template_fails_and_example_passes(self):
        text = CHARTER.read_text()
        template = re.search(r"## Template.*?````markdown\n(.*?)````", text, re.S).group(1)
        example = re.search(r"## Filled example.*?````markdown\n(.*?)````", text, re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for line in example.splitlines():
                for path in re.findall(r"\b((?:briefs|reviews)/[\w.-]+\.md)\b", line):
                    (base / path).parent.mkdir(exist_ok=True)
                    shutil.copy(BRIEF, base / path)
            self.assertEqual(ledger_check.check(example, base), [])
            self.assertIn("R1", {p.split(":", 1)[0] for p in ledger_check.check(template, base)})

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = workspace(tmp)
            good = base / "mission.md"
            good.write_text(GOOD)
            bad = base / "bad.md"
            bad.write_text(edit(PASSED, PASSED.replace('question: AskUserQuestion answer "Approve"', "chat: ok")))
            ok = subprocess.run([sys.executable, str(SCRIPT), str(good)], capture_output=True, text=True)
            no = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "pass"))
        self.assertEqual(no.returncode, 1)
        self.assertTrue(no.stdout.startswith("R7:"), no.stdout)

    def test_brief_checker_found_in_hashed_install_and_fails_closed_without_it(self):
        # Amp installs Personal Skills as <name>@<hash> folders side by side.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(SKILL, root / "missioning@1a2b", ignore=shutil.ignore_patterns("__pycache__"))
            (root / "run").mkdir()
            base = workspace(root / "run")
            (base / "mission.md").write_text(GOOD)
            script = root / "missioning@1a2b" / "scripts" / "ledger_check.py"
            run = lambda: subprocess.run([sys.executable, str(script), str(base / "mission.md")], capture_output=True, text=True)
            missing = run()
            shutil.copytree(ROOT / "skills" / "briefing-decisions", root / "briefing-decisions@3c4d", ignore=shutil.ignore_patterns("__pycache__"))
            found = run()
        self.assertEqual((missing.returncode, missing.stdout.split(":", 1)[0]), (1, "R8"))
        self.assertEqual((found.returncode, found.stdout.strip()), (0, "pass"))


MISSIONS = SKILL / "reference" / "missions"
HEADINGS = ["When to use", "Skills", "Steps", "Human gates", "Definition of Done", "Red flags"]
# Skills the research plans for later waves. When one is built, update the playbooks that name it.
PLANNED = (
    "roadmapping", "researching", "reviewing-code",
    "campaigning",
)


class Playbooks(unittest.TestCase):
    def test_one_playbook_per_mission_linked_from_skill(self):
        names = sorted(p.stem for p in MISSIONS.glob("*.md"))
        self.assertEqual(names, sorted(ledger_check.PLAYBOOKS))
        skill = (SKILL / "SKILL.md").read_text()
        self.assertLessEqual(len(skill.splitlines()), 170)
        for name in names:
            self.assertIn(f"(reference/missions/{name}.md)", skill)
        for ref in ("reference/charter.md", "reference/hosts.md", "scripts/ledger_check.py"):
            self.assertIn(ref, skill)

    def test_playbook_shape(self):
        for path in sorted(MISSIONS.glob("*.md")):
            with self.subTest(playbook=path.stem):
                text = path.read_text()
                self.assertLessEqual(len(text.splitlines()), 80)
                self.assertEqual(re.findall(r"^## (.+)$", text, re.M), HEADINGS)
                self.assertRegex(ledger_check.section(text, "Steps") and "\n".join(ledger_check.section(text, "Steps")), r"(?m)^1\. ")

    def test_planned_skills_are_labelled_with_a_fallback(self):
        for name in PLANNED:
            self.assertFalse((ROOT / "skills" / name).exists(), f"{name} now exists: update the playbooks")
        for path in sorted(MISSIONS.glob("*.md")):
            text = path.read_text()
            bullets = re.split(r"\n(?=- )", "\n".join(ledger_check.section(text, "Skills")))
            for name in PLANNED:
                if f"`{name}`" not in text:
                    continue
                with self.subTest(playbook=path.stem, skill=name):
                    entry = [b for b in bullets if f"`{name}`" in b and "planned" in b]
                    self.assertTrue(entry and "Fallback:" in entry[0], "planned skill needs a 'planned ... Fallback:' bullet in Skills")


if __name__ == "__main__":
    unittest.main()

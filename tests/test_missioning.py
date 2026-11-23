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
- **Open questions:** Q1 report format? Default: Markdown with a SARIF appendix.
- **Pre-authorized effects:** E1 open tracker issues for Critical and High findings in acme/payments.
- **May do without asking:** read code, run the allowed scanners, draft reports.
- **Always ask:** scanning anything outside acme/payments; releasing the report.
- **Stop and ask when:** one of the five stop reasons in missioning.
- **Playbook:** security-review
- **Host:** Claude Code

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Charter and criteria | human | passed | charter above | reviews/charter-novice.md | briefs/charter.md | Rahul Nakmol | question: AskUserQuestion answer "Approve" | 2026-11-18 |
| Threat model | agent | passed | threat-model.md, 14 threats | none needed: no decision, checked by scope gate | - | - | - | 2026-11-19 |
| Accepted risk (finding 3) | human | pending | - | - | briefs/risk.md | - | - | - |
| File findings (E1) | agent | open | pre-authorized: charter E1 | - | - | - | - | - |
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
        # The contract fields are required and named when missing.
        for name in ("Open questions", "Pre-authorized effects"):
            line = re.search(rf"- \*\*{name}:\*\*.*\n", GOOD).group(0)
            with tempfile.TemporaryDirectory() as tmp:
                problems = ledger_check.check(edit(line, ""), workspace(tmp))
            r1 = [p for p in problems if p.startswith("R1:")]
            self.assertEqual(r1, [f"R1: charter needs exactly one '- **{name}:**' line (found 0)"])
        self.assertRule(edit("Q1 report format? Default: Markdown with a SARIF appendix.", "TBD"), "R1")
        # "none" is a value: a mission may have no open questions or pre-authorized effects.
        self.assertEqual(self.rules(edit("Q1 report format? Default: Markdown with a SARIF appendix.", "none")), [])
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

    def test_old_budget_lines_are_extra_fields(self):
        # Budget is no longer a charter field (rule R3 is retired); an old charter still passes.
        for budget in ("3 review rounds per gate; 2 working days.", "as needed", "unlimited (agreed 18 Nov)"):
            old = f"- **Budget:** {budget}\n- **Budget used:** unknown: no telemetry.\n"
            self.assertEqual(self.rules(edit("- **Open questions:**", old + "- **Open questions:**")), [])

    def test_r4_ledger_table(self):
        self.assertRule(edit("| Gate | Kind | State |", "| Gate | State | Kind |"), "R4")
        no_rows = re.sub(r"\| (Charter and|Threat|Accepted|File|Report).*\n", "", GOOD)
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
        # The kickoff, the one approval of the whole baseline, is a human gate too.
        self.assertRule(edit(PASSED, as_agent.replace("Charter and criteria", "Kickoff (contract revision 2)")), "R5")
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

    def test_r13_pre_authorized_effects(self):
        # A pre-authorized effect is an agent row whose Evidence cites the charter's entry.
        done = "| File findings (E1) | agent | passed | pre-authorized: charter E1; 3 issues, read back | none needed: pre-authorized effect | - | - | - | 2026-11-21 |"
        row = "| File findings (E1) | agent | open | pre-authorized: charter E1 | - | - | - | - | - |"
        self.assertEqual(self.rules(edit(row, done)), [])
        # Without a source, with an empty one, or citing no listed effect, it is not pre-authorized.
        for evidence in ("pre-authorized;", "Pre-authorized:", "pre-authorized: -", "pre-authorized: none"):
            with self.subTest(evidence=evidence):
                self.assertRule(edit(row, row.replace("pre-authorized: charter E1", evidence)), "R13")
        self.assertRule(edit(row, row.replace("(E1)", "(E9)").replace("charter E1", "charter E9")), "R13")
        self.assertRule(edit(row, row.replace(" (E1)", "").replace("charter E1", "owner's email")), "R13")
        self.assertRule(edit("E1 open tracker issues for Critical and High findings in acme/payments.", "none"), "R13")
        # The field lists E-numbered effects, or says none; a blanket grant is not a list.
        self.assertRule(edit("E1 open tracker issues for Critical and High findings in acme/payments.", "whatever is needed"), "R13")
        none = edit(row + "\n", "", edit("E1 open tracker issues for Critical and High findings in acme/payments.", "none"))
        self.assertEqual(self.rules(none), [])
        two = "E1 open tracker issues in acme/payments, E2 email the report to Priya Shah."
        self.assertEqual(self.rules(edit(row, row.replace("E1", "E2"), edit("E1 open tracker issues for Critical and High findings in acme/payments.", two))), [])
        self.assertEqual(self.rules(edit("E1 open tracker issues for Critical and High findings in acme/payments.", "none: no outside effects", edit(row + "\n", ""))), [])
        # A field that says none grants no ID, even one named in its reason.
        self.assertRule(edit("E1 open tracker issues for Critical and High findings in acme/payments.", "none: E1 was dropped at kickoff", edit(row, done)), "R13")
        # An agent row naming an effect ID always cites a listed pre-authorization in that form.
        for gate, evidence in (("File findings (E9)", "issues filed, read back"), ("File findings", "E9 pre-authorized at kickoff"),
                               ("File findings", "preauthorized: charter E1"), ("Share the report", "per pre-authorization E9"),
                               ("Share the report", "per pre-authorizations E9"), ("Share the report", "per pre-authorizing E9"),
                               ("Share the report", "the charter pre-authorizes E9"), ("Share the report", "E9 pre authorized at kickoff"),
                               ("Share the report", "preauthorized at kickoff")):
            with self.subTest(gate=gate, evidence=evidence):
                self.assertRule(edit(row, f"| {gate} | agent | open | {evidence} | - | - | - | - | - |"), "R13")
        # Error codes and stage names that look like effect IDs are ordinary evidence and gates.
        for gate, evidence in (("Lint clean", "ruff clean except E501"), ("Build", "rustc E0308 fixed in 1a2b3c4"),
                               ("Stage E2 rollout", "canary green"),
                               ("Threat review", "nothing here is pre-authorized")):
            with self.subTest(gate=gate, evidence=evidence):
                self.assertEqual(self.rules(edit(row, f"| {gate} | agent | open | {evidence} | - | - | - | - | - |")), [])
        # A waived pre-authorized effect still needs its own recorded decider and source.
        waived = "| File findings (E1) | agent | waived | pre-authorized: charter E1; no findings to file | - | - | Rahul Nakmol | written: email 21 Nov | 2026-11-21 |"
        self.assertEqual(self.rules(edit(row, waived)), [])
        self.assertRule(edit(row, waived.replace("written: email 21 Nov", "-")), "R6")
        # Recorded as a human gate, a pre-authorized effect would ask the owner a second time.
        self.assertRule(edit(row, "| File findings (E1) | human | open | - | - | - | - | - | - |"), "R13")
        self.assertRule(edit(row, "| File findings (e1) | human | open | - | - | - | - | - | - |"), "R13")
        self.assertRule(edit(row, "| Report release | human | open | E1 pre-authorized at kickoff | - | - | - | - | - |"), "R13")
        as_human = PASSED.replace("Charter and criteria", "Report release").replace("| charter above |", "| pre-authorized: charter E1 |")
        self.assertRule(edit(PASSED, PASSED + "\n" + as_human), "R13")

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
# The canonical stop reasons (mission contract, section 8). tests/test_contract_kit.py checks the
# same text against plugins/mission-control/lib/contract-text.json.
STOP_REASONS = (
    "1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.",
    "2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.",
    "3. A fact only a person holds, with no safe, reversible default.",
    "4. A red line: security, legal or safety.",
    "5. A milestone cannot meet its exit criteria after the work was re-planned and split.",
)
# Banned-phrase list B (mission contract, section 6): budgets and owner merge gates.
BANNED = (
    "budget used", "**budget:**", "token budget", "review budget", "budget call", "remaining budget",
    "beyond it needs explicit approval", "merge mode", "mission_merge_mode", "ask-before-merge",
    "ask mode", "owner merge acknowledgment", "high-risk merge", "high risk always requires",
)
HEADINGS = ["When to use", "Skills", "Steps", "Human gates", "Definition of Done", "Red flags"]
# Skills the research plans for later waves. When one is built, update the playbooks that name it.
PLANNED = (
    "roadmapping", "researching",
    "campaigning",
)
# Skills built in waves 1 and 2 (W23). `interrogating-changes` is the plan's `reviewing-code`,
# renamed so it does not mask Amp's official skill of that name.
BUILT = (
    "architecting", "threat-modelling", "releasing", "interrogating-changes",
    "scanning-vulnerabilities", "provisioning", "monitoring", "investigating-incidents",
    "steering", "assessing-products",
)


def skills_bullets(path):
    """The bullets of a playbook's Skills section, each with its wrapped lines joined."""
    text = "\n".join(ledger_check.section(path.read_text(), "Skills"))
    return [" ".join(b.split()) for b in re.split(r"\n(?=- )", text) if b.strip()]


def names_built(bullet):
    """True when the bullet names a built skill or a built enhancement (syncing, shaping-engagements)."""
    return (any(f"`{name}`" in bullet for name in BUILT)
            or ("`syncing`" in bullet and "adapter" in bullet)
            or ("`shaping-engagements`" in bullet and "scoring" in bullet))


class Contract(unittest.TestCase):
    def test_no_budget_or_owner_merge_gate_in_the_skill(self):
        for path in sorted(p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            text = " ".join(path.read_text().split()).lower()  # a phrase may wrap across lines
            for phrase in BANNED:
                with self.subTest(file=str(path.relative_to(SKILL)), phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_stop_reasons_are_canonical(self):
        for path in (SKILL / "SKILL.md", CHARTER):
            lines = path.read_text().splitlines()
            for reason in STOP_REASONS:
                with self.subTest(file=path.name, reason=reason[:2]):
                    self.assertIn(reason, lines)

    def test_review_cap_follows_the_disposition_policy(self):
        paragraphs = (SKILL / "SKILL.md").read_text().split("\n\n")
        cap = [p for p in paragraphs if "review cap" in p]
        self.assertTrue(cap and all("disposition policy" in p for p in cap), cap)


class Playbooks(unittest.TestCase):
    def test_one_playbook_per_mission_linked_from_skill(self):
        names = sorted(p.stem for p in MISSIONS.glob("*.md"))
        self.assertEqual(names, sorted(ledger_check.PLAYBOOKS))
        skill = (SKILL / "SKILL.md").read_text()
        self.assertLessEqual(len(skill.splitlines()), 180)
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

    def test_w23_1_built_skills_are_not_labelled_planned(self):
        for name in BUILT:
            self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file(), name)
        # Hand-picked bullets that must count as naming a built skill or enhancement.
        self.assertTrue(names_built("- Linear and Azure DevOps adapters and outside sign-off in `syncing`: planned."))
        self.assertTrue(names_built("- Shared fit-gap scoring in `shaping-engagements`: planned."))
        self.assertFalse(names_built("- `planning`: the conductor, with `syncing`."))
        for path in sorted(MISSIONS.glob("*.md")):
            lines = path.read_text().splitlines()
            for item in skills_bullets(path) + lines:
                if names_built(item):
                    with self.subTest(playbook=path.stem, text=item[:60]):
                        self.assertNotIn("planned", item.lower())

    def test_w23_2_built_skills_keep_an_if_not_installed_fallback(self):
        seen = set()
        for path in sorted(MISSIONS.glob("*.md")):
            bullets = skills_bullets(path)
            for bullet in bullets:
                if names_built(bullet):
                    with self.subTest(playbook=path.stem, bullet=bullet[:60]):
                        self.assertEqual(bullet.count("If not installed:"), 1)
                        self.assertNotIn("Fallback:", bullet)
            for name in BUILT:
                if any(f"`{name}`" in b for b in bullets):
                    seen.add(name)
                    with self.subTest(playbook=path.stem, skill=name):
                        own = [b for b in bullets if b.startswith(f"- `{name}`")]
                        self.assertEqual(len(own), 1, "each built skill named in Skills has its own bullet")
                        self.assertIn("If not installed:", own[0])
        # The playbooks between them name every built skill.
        self.assertEqual(seen, set(BUILT))

    def test_w23_3_playbooks_name_interrogating_changes_not_reviewing_code(self):
        for path in sorted(MISSIONS.glob("*.md")):
            with self.subTest(playbook=path.stem):
                self.assertNotIn("`reviewing-code`", path.read_text())
        for stem in ("security-review", "software-delivery"):
            own = [b for b in skills_bullets(MISSIONS / f"{stem}.md") if b.startswith("- `interrogating-changes`")]
            self.assertEqual(len(own), 1, stem)

    def test_promotion_without_the_skill_follows_the_contract(self):
        # A promotion is an outside effect: pre-authorized by the contract, else stop reason 2.
        # "Ask for each promotion" would ask the owner again for a pre-authorized effect.
        for path in sorted(MISSIONS.glob("*.md")):
            text = " ".join(path.read_text().split()).lower()
            for phrase in ("ask for each", "ask before any", "before asking"):
                with self.subTest(playbook=path.stem, phrase=phrase):
                    self.assertNotIn(phrase, text)
            for bullet in skills_bullets(path):
                if bullet.startswith("- `releasing`"):
                    with self.subTest(playbook=path.stem):
                        self.assertIn("pre-authorizes", bullet)
                        self.assertIn("stop reason 2", bullet)


if __name__ == "__main__":
    unittest.main()

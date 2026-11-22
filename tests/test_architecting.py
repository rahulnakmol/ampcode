"""Tests for skills/architecting: the design checker (cases W1.1 to W1.9) and the skill text.

Run: python3 -m unittest tests.test_architecting -v
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architecting"
SCRIPT = SKILL / "scripts" / "design_check.py"
TEMPLATE = SKILL / "reference" / "design-template.md"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(ROOT / "tests"))

import design_check  # noqa: E402
from test_skill_anatomy import problems as anatomy  # noqa: E402

# A small design written by hand for these tests. It follows reference/design-template.md.
GOOD = """# Design: invoice reminders

## Context

| Actor or system | Uses | Through |
| --- | --- | --- |
| Finance user | Billing app | Browser over HTTPS |
| Billing app | Email provider | HTTPS API |

## Containers

| Container | Technology | Owns |
| --- | --- | --- |
| Billing API | ASP.NET Core | Invoices, reminders |
| Reminder worker | .NET background service | Reminder sending |

## Contracts

| Contract | Kind | Producer | Consumer | Shape |
| --- | --- | --- | --- | --- |
| POST /reminders | HTTP API | Billing API | Billing UI | invoiceId in, 202 out |

## Decisions

### ADR-1: Send reminders from a queue

Status: accepted
Options:
- Queue and worker
- Timer inside the API
Decision: Queue and worker.
Consequences: Retries need an idempotency key; one more process to run.

### ADR-2: Keep one database

Status: proposed
Options:
- One PostgreSQL database
- A separate reminder store
Decision: One PostgreSQL database.
Consequences: Simple joins; the reminder tables share the invoice backup.

## Non-functional requirements

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-1 | Latency | p95 under 300 ms at 50 req/s | k6 load test in staging before each release |
| NFR-2 | Availability | 99.9 % each month | Synthetic probe every minute; monthly report |

## Trust boundaries

Trust boundaries change: yes
Threat model: docs/threat-model-reminders.md
"""


def replace(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new, 1)


def rules(text):
    return sorted({p.split(":", 1)[0] for p in design_check.check(text)})


def example():
    found = re.search(r"## Filled example.*?````markdown\n(.*?)````", TEMPLATE.read_text(), re.S)
    assert found, "design-template.md needs a '## Filled example' with a ````markdown fence"
    return found.group(1)


class Designs(unittest.TestCase):
    def test_hand_written_design_passes(self):
        self.assertEqual(design_check.check(GOOD), [])

    def test_w1_9_template_example_passes(self):
        # W1.9: the filled example in reference/design-template.md passes.
        self.assertEqual(design_check.check(example()), [])

    def test_w1_1_nfr_without_number(self):
        # W1.1: a target with no number at all.
        text = replace("p95 under 300 ms at 50 req/s", "fast enough")
        self.assertEqual(rules(text), ["D1"])
        self.assertIn("NFR-1", design_check.check(text)[0])

    def test_w1_2_nfr_without_unit(self):
        # W1.2: numbers, but none followed by an accepted unit.
        text = replace("99.9 % each month", "99.9 each month")
        self.assertEqual(rules(text), ["D2"])
        self.assertIn("NFR-2", design_check.check(text)[0])
        self.assertEqual(rules(replace("300 ms at 50 req/s", "300 parsecs")), ["D2"])

    def test_w1_2_accepted_units_pass(self):
        # Hand-picked targets that use units from the documented list.
        for target in ("RPO 15 min", "2 h to restore", "500 GB after 3 years", "10,000 users",
                       "under 5 errors/min", "1.5 s cold start", "200 rps", "99.95%", "400 USD/month"):
            with self.subTest(target=target):
                self.assertEqual(design_check.check(replace("99.9 % each month", target)), [])

    def test_w1_3_nfr_without_verification(self):
        # W1.3: an empty or placeholder verification cell.
        for cell in ("", "TBD", "-", "<test>", "TBD.", "**TBD**", "`TBD`", "N/A.", "n/a.", "TBD/later",
                     "not/yet", "none", "Not yet", "TODO, later", "_TBD_", "__TBD__", "~~TBD~~", "[TBD]",
                     "(TBD)", "N.A."):
            with self.subTest(cell=cell):
                text = replace("| Synthetic probe every minute; monthly report |", f"| {cell} |")
                self.assertEqual(rules(text), ["D3"])

    def test_w1_3_real_verification_with_trailing_punctuation_passes(self):
        text = replace("Synthetic probe every minute; monthly report", "**Synthetic probe** each minute.")
        self.assertEqual(design_check.check(text), [])

    def test_w1_3_nfr_rows_outside_the_first_table(self):
        # W1.1 to W1.3 and W1.7 are checked only in the first table, so later NFR lines are D9.
        second = ("\n| ID | Quality | Target | Verification |\n| --- | --- | --- | --- |\n"
                  "| NFR-3 | Latency | fast | |\n")
        self.assertEqual(rules(replace("\n## Trust boundaries", second + "\n## Trust boundaries")), ["D9"])
        self.assertEqual(rules(replace("\n## Trust boundaries", "\nNFR-1 again: fast.\n\n## Trust boundaries")), ["D9"])
        self.assertEqual(rules(replace("\n## Trust boundaries", "\n| NFR-1 | Latency | fast | |\n\n## Trust boundaries")), ["D9"])

    def test_w1_4_adr_with_one_option(self):
        # W1.4: an ADR with fewer than two options.
        self.assertEqual(rules(replace("- Queue and worker\n- Timer inside the API\n", "- Queue and worker\n")), ["D4"])
        self.assertEqual(rules(replace("Options:\n- Queue and worker\n- Timer inside the API\n", "")), ["D4"])

    def test_w1_4_nested_bullets_are_not_options(self):
        # W1.4: one option with indented pro and con sub-bullets is still one option.
        nested = "- Queue and worker\n  - Pro: retries are cheap\n  - Con: one more process\n"
        self.assertEqual(rules(replace("- Queue and worker\n- Timer inside the API\n", nested)), ["D4"])
        indented = "  - Queue and worker\n    - Pro: retries are cheap\n    - Con: one more process\n"
        self.assertEqual(rules(replace("- Queue and worker\n- Timer inside the API\n", indented)), ["D4"])
        two = "- Queue and worker\n  - Pro: retries are cheap\n- Timer inside the API\n  - Con: blocks requests\n"
        self.assertEqual(design_check.check(replace("- Queue and worker\n- Timer inside the API\n", two)), [])

    def test_w1_4_a_later_list_is_not_options(self):
        # W1.4 (recheck N1): a list under another label after one option is not a second option.
        later = "- Queue and worker\n\nPros:\n- cheap\n- simple\n"
        self.assertEqual(rules(replace("- Queue and worker\n- Timer inside the API\n", later)), ["D4"])

    def test_w1_4_consequence_bullets_are_not_options(self):
        # W1.4: one option plus a bulleted Consequences list still fails.
        text = replace("- Queue and worker\n- Timer inside the API\n", "- Queue and worker\n")
        text = replace("Consequences: Retries need an idempotency key; one more process to run.\n",
                       "Consequences:\n- Retries need an idempotency key\n- One more process to run\n", text)
        self.assertEqual(rules(text), ["D4"])

    def test_w1_5_adr_without_status_or_consequences(self):
        # W1.5: a missing or unknown status, or missing consequences.
        self.assertEqual(rules(replace("Status: accepted\n", "")), ["D5"])
        self.assertEqual(rules(replace("Status: accepted\n", "Status: maybe\n")), ["D5"])
        self.assertEqual(rules(replace("Consequences: Simple joins; the reminder tables share the invoice backup.\n", "")), ["D5"])
        self.assertEqual(rules(replace("Consequences: Simple joins; the reminder tables share the invoice backup.\n", "Consequences:\n")), ["D5"])

    def test_w1_5_superseded_status_passes(self):
        self.assertEqual(design_check.check(replace("Status: proposed", "Status: superseded by ADR-1")), [])

    def test_w1_6_design_without_contracts(self):
        # W1.6: no Contracts section, or one with nothing in it.
        cut = GOOD.index("## Contracts")
        end = GOOD.index("## Decisions")
        self.assertEqual(rules(GOOD[:cut] + GOOD[end:]), ["D6"])
        self.assertEqual(rules(GOOD[:cut] + "## Contracts\n\n" + GOOD[end:]), ["D6"])

    def test_w1_7_duplicate_ids(self):
        # W1.7: the same NFR or ADR ID twice.
        self.assertEqual(rules(replace("| NFR-2 |", "| NFR-1 |")), ["D7"])
        self.assertEqual(rules(replace("### ADR-2:", "### ADR-1:")), ["D7"])

    def test_w1_8_trust_boundary_change_without_threat_model(self):
        # W1.8: "yes" needs a threat model path or link.
        for line in ("Threat model:\n", "Threat model: TBD\n", "Threat model: none\n", "",
                     "Threat model: TBD.\n", "Threat model: **TBD**\n", "Threat model: `TBD`\n",
                     "Threat model: N/A.\n", "Threat model: n/a.\n", "Threat model: TBD/later\n",
                     "Threat model: not/yet\n", "**Threat model:** none.\n", "Threat model: N.A.\n",
                     "Threat model: n.a.\n", "Threat model: TBD/pending\n", "Threat model: pending/TBD\n",
                     "Threat model: to/do\n"):
            with self.subTest(line=line):
                text = replace("Threat model: docs/threat-model-reminders.md\n", line)
                self.assertEqual(rules(text), ["D8"])
        link = replace("docs/threat-model-reminders.md", "https://example.com/threat-models/reminders")
        self.assertEqual(design_check.check(link), [])
        quoted = replace("docs/threat-model-reminders.md", "`docs/threat-model-reminders.md`.")
        self.assertEqual(design_check.check(quoted), [])
        prose = replace("docs/threat-model-reminders.md", "we will write one later")
        self.assertEqual(rules(prose), ["D8"])

    def test_no_trust_boundary_change_needs_no_threat_model(self):
        text = replace("Trust boundaries change: yes\nThreat model: docs/threat-model-reminders.md\n",
                       "Trust boundaries change: no\nThreat model: none\n")
        self.assertEqual(design_check.check(text), [])

    def test_trust_boundary_line_must_say_yes_or_no(self):
        self.assertEqual(rules(replace("Trust boundaries change: yes", "Trust boundaries change: maybe")), ["D8"])

    def test_structure(self):
        cut = GOOD.index("## Containers")
        end = GOOD.index("## Contracts")
        self.assertEqual(rules(GOOD[:cut] + GOOD[end:]), ["D9"])
        self.assertEqual(rules(replace("| NFR-2 |", "| N2 |")), ["D9"])
        mermaid = replace("## Containers\n", "## Containers\n\n```mermaid\ngraph TD; A-->B\n```\n")
        self.assertEqual(rules(mermaid), ["D9"])

    def test_one_line_per_broken_rule(self):
        text = replace("Status: accepted\n", "", replace("p95 under 300 ms at 50 req/s", "fast"))
        self.assertEqual(len(design_check.check(text)), 2)

    def test_units_are_documented_in_the_template(self):
        line = re.search(r"^Accepted units: (.+)$", TEMPLATE.read_text(), re.M)
        self.assertIsNotNone(line, "design-template.md needs an 'Accepted units:' line")
        self.assertEqual(set(re.findall(r"`([^`]+)`", line.group(1))), set(design_check.UNITS))

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            bad = Path(tmp) / "bad.md"
            good.write_text(GOOD)
            bad.write_text(replace("p95 under 300 ms at 50 req/s", "fast enough"))
            ok = subprocess.run([sys.executable, str(SCRIPT), str(good)], capture_output=True, text=True)
            no = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
            help_ = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.strip()), (0, "pass"))
        self.assertEqual(no.returncode, 1)
        self.assertEqual(len(no.stdout.strip().splitlines()), 1)
        self.assertTrue(no.stdout.startswith("D1: NFR-1"))
        self.assertEqual(help_.returncode, 0)
        self.assertIn("design_check.py", help_.stdout)


class SkillText(unittest.TestCase):
    def test_anatomy_a1_a3_a4_a6_a7(self):
        self.assertEqual(anatomy("architecting", item=True), [])

    def test_x7_without_a_shell_rule(self):
        text = (SKILL / "SKILL.md").read_text()
        rule = re.search(r"^#+ .*Without a shell.*?\n(.*?)(?=^#+ |\Z)", text, re.M | re.S)
        self.assertIsNotNone(rule, "SKILL.md needs a 'Without a shell' rule")
        self.assertIn("design_check.py", rule.group(1))
        self.assertIn("not run", rule.group(1))

    def test_moved_remits_keep_their_anchor_lines(self):
        self.assertIn("Domain-driven design: ubiquitous language", (SKILL / "SKILL.md").read_text())
        data = (SKILL / "reference" / "data-and-ai.md").read_text()
        self.assertIn("Compare SQL Server/PostgreSQL reporting", data)

    def test_threat_modelling_and_fallback(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("threat-modelling", text)
        for word in ("actors", "trust boundaries", "abuse cases", "mitigation", "owner"):
            self.assertIn(word, text)

    def test_review_cap_follows_disposition_policy(self):
        self.assertIn("disposition policy", (SKILL / "SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()

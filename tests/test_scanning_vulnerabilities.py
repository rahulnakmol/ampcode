"""Tests for skills/scanning-vulnerabilities (W7.1 to W7.10, X2 and X7).

Run: python3 -m unittest tests.test_scanning_vulnerabilities -v

Expected values are derived by hand from the committed SARIF fixtures (see
tests/fixtures/scanning-vulnerabilities/README.md), never from the code under test.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "scanning-vulnerabilities"
SCRIPT = SKILL / "scripts" / "sarif_triage.py"
FIXTURES = ROOT / "tests" / "fixtures" / "scanning-vulnerabilities"
SAMPLE_ROOT = "/tmp/scan/sample"  # where the fixtures were produced; see the fixture README
SAMPLE = [
    "code=" + str(FIXTURES / "semgrep.sarif"),
    "code=" + str(FIXTURES / "bandit.sarif"),
    "dependencies=" + str(FIXTURES / "osv-scanner.sarif"),
    "dependencies=" + str(FIXTURES / "trivy-deps.sarif"),
    "secrets=" + str(FIXTURES / "gitleaks.sarif"),
    "iac=" + str(FIXTURES / "checkov.sarif"),
    "iac=" + str(FIXTURES / "trivy-config.sarif"),
]


def run(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
                          env={**os.environ, **env} if env else None)


def sarif(tool, results, rules=(), version="1.0"):
    return {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": tool, "version": version, "rules": list(rules)}},
                  "results": results}],
    }


def result(rule, uri, line, level="warning", cwe=None):
    found = {"ruleId": rule, "level": level, "message": {"text": f"{rule} found"},
             "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri},
                                                 "region": {"startLine": line}}}]}
    if cwe:
        found["properties"] = {"tags": [cwe]}
    return found


def findings_rows(report):
    """Data rows of the table under '## Findings', as dicts keyed by header."""
    body = report.split("## Findings", 1)[1]
    lines = [l for l in body.splitlines() if l.startswith("|")]
    cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    head = cells(lines[0])
    return [dict(zip(head, cells(l))) for l in lines[2:]]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write(self, name, data):
        path = self.dir / name
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        return str(path)

    def merge(self, *scans, root=None):
        args = ["merge", *(["--root", root] if root else []), *scans]
        done = run(*args)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout


class Fixtures(Base):
    def test_w7_1_each_fixture_count_matches_independent_read(self):
        readme = (FIXTURES / "README.md").read_text()
        rows = re.findall(r"^\| `([\w.-]+\.sarif)` \| (\w+) \|.*\| (\d+) \|$", readme, re.M)
        self.assertEqual(len(rows), 8, "every committed SARIF has a row in the fixture README")
        self.assertEqual(sorted(r[0] for r in rows), sorted(p.name for p in FIXTURES.glob("*.sarif")))
        for name, category, stated in rows:
            with self.subTest(fixture=name):
                data = json.loads((FIXTURES / name).read_text())
                independent = sum(len(r.get("results") or []) for r in data["runs"])
                self.assertEqual(independent, int(stated))
                report = self.merge(f"{category}={FIXTURES / name}")
                self.assertRegex(report, rf"- {category}: scanned, \d+ findings? from {independent} results?")

    def test_w7_2_real_cross_tool_merge_on_same_line_and_cwe(self):
        rows = findings_rows(self.merge(SAMPLE[0], SAMPLE[1]))
        # By hand: semgrep 8 + bandit 9 = 17 results. Line 24 (CWE-78: three semgrep rules and
        # B602) and line 38 (CWE-327: semgrep md5 and B324) merge; nothing else shares a CWE.
        self.assertEqual(len(rows), 13)
        by_place = {}
        for row in rows:
            by_place.setdefault(row["Location"], []).append(row)
        self.assertEqual(len(by_place["`app.py:24`"]), 1)
        self.assertEqual(by_place["`app.py:24`"][0]["Tools"], "Bandit, Semgrep OSS")
        self.assertEqual(by_place["`app.py:24`"][0]["CWE"], "CWE-78")
        self.assertEqual(by_place["`app.py:38`"][0]["Tools"], "Bandit, Semgrep OSS")
        self.assertEqual(len(by_place["`app.py:17`"]), 2)  # CWE-704 (semgrep) and CWE-89 (bandit)
        self.assertEqual(len(by_place["`app.py:42`"]), 4)

    def test_w7_2_no_cwe_results_merge_only_within_one_tool_and_rule(self):
        report = self.merge(*SAMPLE, root=SAMPLE_ROOT)
        rows = findings_rows(report)
        # By hand: code 13; dependencies 64 osv results are 32 rule IDs twice each (no line, no CWE)
        # plus 17 Trivy results on other lines = 49; secrets 1; iac 14 + 15 with no CWE = 29.
        self.assertEqual(len(rows), 13 + 49 + 1 + 29)
        self.assertIn("- dependencies: scanned, 49 findings from 81 results", report)
        self.assertIn("- iac: scanned, 29 findings from 29 results", report)
        for row in rows:
            self.assertNotIn("/tmp/scan", row["Location"])  # --root made the paths relative

    def test_w7_2_synthetic_rules(self):
        a = self.write("a.sarif", sarif("ToolA", [
            result("A1", "./src/x.py", 5, cwe="CWE-89"),
            result("A2", "src/y.py", 7), result("A2", "src/y.py", 7), result("A3", "src/y.py", 7)]))
        b = self.write("b.sarif", sarif("ToolB", [
            result("B1", "file:///work/src/x.py", 5, cwe="external/cwe/cwe-089"),
            result("B2", "src/y.py", 7), result("A2", "src/y.py", 7)]))
        rows = findings_rows(self.merge("code=" + a, "code=" + b, root="/work"))
        # x.py:5 CWE-89 from both tools is one finding; y.py:7 without CWE: ToolA A2 twice is one,
        # A3 another, B2 another, and ToolB's A2 another: same rule ID, but not the same tool.
        self.assertEqual(len(rows), 5)
        x = [r for r in rows if r["Location"] == "`src/x.py:5`"]
        self.assertEqual(len(x), 1)
        self.assertEqual(x[0]["Tools"], "ToolA, ToolB")
        y = [r for r in rows if r["Location"] == "`src/y.py:7`"]
        self.assertEqual(len(y), 4)
        self.assertEqual(sorted((r["Rules"], r["Tools"]) for r in y),
                         [("`A2`", "ToolA"), ("`A2`", "ToolB"), ("`A3`", "ToolA"), ("`B2`", "ToolB")])

    def test_w7_2_cwe_merges_chain(self):
        # T2 shares CWE-89 with T1 and CWE-79 with T3, so all three become one finding, although
        # T1 and T3 share no CWE (reference/scanners.md says merges chain). Without T2 they stay apart.
        t1 = self.write("t1.sarif", sarif("T1", [result("X", "a.py", 3, cwe="CWE-89")]))
        t2 = self.write("t2.sarif", sarif("T2", [result("Y", "a.py", 3, cwe="CWE-89")]))
        data = json.loads(Path(t2).read_text())
        data["runs"][0]["results"][0]["properties"]["tags"].append("CWE-79")
        Path(t2).write_text(json.dumps(data))
        t3 = self.write("t3.sarif", sarif("T3", [result("Z", "a.py", 3, cwe="CWE-79")]))
        rows = findings_rows(self.merge("code=" + t1, "code=" + t2, "code=" + t3))
        self.assertEqual([(r["CWE"], r["Tools"]) for r in rows], [("CWE-79, CWE-89", "T1, T2, T3")])
        self.assertEqual(len(findings_rows(self.merge("code=" + t1, "code=" + t3))), 2)

    def test_w7_1_paths_runs_and_results_without_location(self):
        # One file, two runs. Run 1 uses a uriBaseId base and a percent-encoded name; run 2 has
        # one result with a location and one without.
        data = {"version": "2.1.0", "runs": [
            {"tool": {"driver": {"name": "ToolA", "version": "1"}},
             "originalUriBaseIds": {"SRC": {"uri": "file:///work/src/"}},
             "results": [{"ruleId": "A1", "level": "error", "message": {"text": "A1 found"},
                          "properties": {"tags": ["CWE-22"]},
                          "locations": [{"physicalLocation": {
                              "artifactLocation": {"uri": "my%20file.py", "uriBaseId": "SRC"},
                              "region": {"startLine": 3}}}]}]},
            {"tool": {"driver": {"name": "ToolB", "version": "2"}},
             "results": [result("B1", "src/my file.py", 3, cwe="CWE-22"),
                         {"ruleId": "B2", "level": "note", "message": {"text": "B2 found"}}]},
        ]}
        report = self.merge("code=" + self.write("two-runs.sarif", data), root="/work")
        # By hand: 3 results; A1 and B1 are both at src/my file.py:3 with CWE-22, so 2 findings.
        self.assertIn("- code: scanned, 2 findings from 3 results", report)
        rows = findings_rows(report)
        self.assertEqual(sorted((r["Location"], r["Tools"]) for r in rows),
                         [("`(no location)`", "ToolB"), ("`src/my file.py:3`", "ToolA, ToolB")])

    def test_w7_2_merged_finding_keeps_the_highest_severity(self):
        # Gate review F4: a note (Low) and an error (High) on the same line and CWE give one High
        # finding, in either order; C4 relies on this.
        low = self.write("low.sarif", sarif("ToolA", [result("A1", "x.py", 5, level="note", cwe="CWE-89")]))
        high = self.write("high.sarif", sarif("ToolB", [result("B1", "x.py", 5, level="error", cwe="CWE-89")]))
        for order in (("code=" + low, "code=" + high), ("code=" + high, "code=" + low)):
            with self.subTest(order=order):
                rows = findings_rows(self.merge(*order))
                self.assertEqual([(r["Severity"], r["Tools"]) for r in rows], [("High", "ToolA, ToolB")])

    def test_w7_2_same_line_different_cwe_stays_apart(self):
        a = self.write("a.sarif", sarif("ToolA", [result("A1", "x.py", 5, cwe="CWE-89")]))
        b = self.write("b.sarif", sarif("ToolB", [result("B1", "x.py", 5, cwe="CWE-79")]))
        self.assertEqual(len(findings_rows(self.merge("code=" + a, "code=" + b))), 2)


class Coverage(Base):
    def test_w7_3_category_without_scan_is_not_examined(self):
        done = run("coverage", "--root", SAMPLE_ROOT, *SAMPLE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("- containers: not examined", done.stdout)
        self.assertIn("Not examined: containers.", done.stdout)
        self.assertIn("- code: scanned, 13 findings from 17 results "
                      "(Bandit, version per SARIF: 1.9.4; Semgrep OSS, version per SARIF: 1.186.0)", done.stdout)

    def test_version_from_sarif_is_labelled_as_such(self):
        # gitleaks writes v8.0.0 whatever the binary is (the fixture run used 8.30.1), so the
        # output must not present it as the tool's version; SKILL.md's red flag names the label.
        done = run("coverage", "secrets=" + str(FIXTURES / "gitleaks.sarif"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("- secrets: scanned, 1 finding from 1 result (gitleaks, version per SARIF: v8.0.0)",
                      done.stdout)
        self.assertNotIn("gitleaks v8.0.0", done.stdout)
        text = " ".join((SKILL / "SKILL.md").read_text().split())
        flags = text.split("## Red flags", 1)[1].split("## ", 1)[0]
        self.assertIn("version per SARIF", flags)

    def test_w7_4_scanned_category_with_zero_results(self):
        done = run("coverage", "code=" + str(FIXTURES / "bandit-clean.sarif"))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("- code: scanned, 0 findings", done.stdout)
        for category in ("dependencies", "secrets", "iac", "containers"):
            self.assertIn(f"- {category}: not examined", done.stdout)

    def test_unknown_category_is_one_error(self):
        done = run("coverage", "dast=" + str(FIXTURES / "bandit-clean.sarif"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len((done.stdout + done.stderr).strip().splitlines()), 1)


TRIAGED = """# Scan report

## Coverage

- code: scanned, 2 findings from 2 results (ToolA 1.0)
- dependencies: not examined
- secrets: not examined
- iac: not examined
- containers: not examined

## Findings

| ID | Severity | Category | Location | CWE | Rules | Tools | Title | Reachable | Exploitable | Disposition | Owner | Reason | Retest | Threat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | High | code | `x.py:5` | CWE-89 | `A1` | ToolA | `A1 found` | yes | yes | fixed | Priya Shah | Parameterized query | Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` | T3 |
| F2 | Medium | code | `y.py:7` | - | `A2` | ToolA | `A2 found` | not proven | not proven | accepted | Priya Shah | Internal tool only | - | - |
"""


def edit(old, new, text=TRIAGED):
    assert old in text, old
    return text.replace(old, new, 1)


class Check(Base):
    def rules(self, text, today="2026-11-22"):
        done = run("check", *(["--today", today] if today else []), self.write("report.md", text))
        lines = (done.stdout + done.stderr).strip().splitlines()
        if done.returncode == 0:
            self.assertEqual(lines, ["pass"])
            return []
        self.assertEqual(done.returncode, 1)
        return lines

    def test_triaged_report_passes(self):
        self.assertEqual(self.rules(TRIAGED), [])

    def test_w7_5_finding_without_disposition(self):
        found = self.rules(edit("| accepted | Priya Shah | Internal tool only |", "|  | Priya Shah | Internal tool only |"))
        self.assertEqual(len(found), 1)
        self.assertIn("F2", found[0])
        self.assertIn("disposition", found[0])

    def test_w7_5_fresh_merge_output_fails_on_every_finding(self):
        a = self.write("a.sarif", sarif("ToolA", [result("A1", "x.py", 5), result("A2", "x.py", 6)]))
        found = self.rules(self.merge("code=" + a))
        self.assertEqual(len([l for l in found if "disposition" in l]), 2)

    def test_w7_6_accepted_without_owner(self):
        found = self.rules(edit("| accepted | Priya Shah |", "| accepted | - |"))
        self.assertEqual(len(found), 1)
        self.assertIn("F2", found[0])
        self.assertIn("owner", found[0])

    def test_w7_6_placeholder_owner_is_no_owner(self):
        for owner in ("TBD", "tba", "N/A", "none", "?"):
            with self.subTest(owner=owner):
                found = self.rules(edit("| accepted | Priya Shah |", f"| accepted | {owner} |"))
                self.assertEqual(len(found), 1)
                self.assertTrue(found[0].startswith("C2:") and "F2" in found[0], found[0])

    def test_w7_6_accepted_owner_is_a_named_person(self):
        # Gate review N3: the same owner rule as threat-modelling and assessing-products.
        for owner in ("Security team", "Platform Group", "security", "the owner", "Finance (team)",
                      "IT, department", "AppSec squad"):
            with self.subTest(owner=owner):
                found = self.rules(edit("| accepted | Priya Shah |", f"| accepted | {owner} |"))
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith("C2:") and "F2" in found[0] and "person" in found[0], found)
        for owner in ("Dana Reyes (Platform Group lead)", "Priya Shah, CISO"):
            with self.subTest(owner=owner):
                self.assertEqual(self.rules(edit("| accepted | Priya Shah |", f"| accepted | {owner} |")), [])

    def test_severity_must_be_in_the_allowed_set(self):
        # "High (raised)" is reported once, by C8. Once it reads "High", C4 asks for the retest
        # (test_w7_8), so no wrong severity lets a fixed High pass.
        text = edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |", "| - |", edit("| High |", "| High (raised) |"))
        found = self.rules(text)
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith("C8:") and "F1" in found[0] and "Severity" in found[0], found)
        self.assertEqual(self.rules(edit("| Medium |", "| low |")), [])

    def test_w7_5_every_table_under_findings_is_read(self):
        # The report may split findings into several tables, for example by category; check
        # reads each one. F3 in the second table has no disposition, F4 is accepted with no owner.
        head, rows = TRIAGED.split("| F1 ", 1)
        header = head.split("## Findings\n\n", 1)[1]
        second = (header + "| F3 | Low | code | `z.py:1` | - | `A3` | ToolA | `A3 found` | no | no |  | - | - | - | - |\n"
                  "| F4 | Low | code | `z.py:2` | - | `A4` | ToolA | `A4 found` | no | no | accepted | - | - | - | - |\n")
        text = head.replace("## Findings\n\n", "## Findings\n\n### Code\n\n") + "| F1 " + rows + "\n### More\n\n" + second
        found = self.rules(text)
        self.assertEqual(len(found), 2, found)
        self.assertTrue(found[0].startswith("C1:") and "F3" in found[0], found)
        self.assertTrue(found[1].startswith("C2:") and "F4" in found[1], found)
        # A second table without the findings columns is refused with one line.
        found = self.rules(TRIAGED + "\n| Note | Value |\n| --- | --- |\n| a | b |\n")
        self.assertEqual(len(found), 1, found)
        self.assertTrue(found[0].startswith("C1:") and "columns" in found[0], found)

    def test_w7_7_false_positive_without_reason(self):
        found = self.rules(edit("| accepted | Priya Shah | Internal tool only |", "| false positive | Priya Shah |  |"))
        self.assertEqual(len(found), 1)
        self.assertIn("F2", found[0])
        self.assertIn("reason", found[0])

    def test_w7_8_fixed_critical_or_high_without_retest(self):
        text = edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |", "| - |")
        found = self.rules(text)
        self.assertEqual(len(found), 1)
        self.assertIn("F1", found[0])
        self.assertIn("retest", found[0])
        self.assertEqual(len(self.rules(edit("| High |", "| Critical |", text))), 1)
        self.assertEqual(len(self.rules(edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |", "| yes |"))), 1)
        # Gate round 4 (B3, F11), replanned: the Retest cell has one required form,
        # "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>". check reads only the form.
        form = "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>"
        failing = (
            # Earlier rounds' must-fail values: none is in the form.
            "", "-", "TBD", "n/a", "none", "yes", "ok", "done", "Not run", "not yet",
            "not done", "pending", "Pending.", "TBD after deploy", "No retest yet",
            "will rescan Monday", "pending review", "not retested", "Not tested",
            "Not reproduced", "Not run: Bandit 1.9.4 rescan planned for 2026-11-25",
            "not proven, 2026-11-22", "Not proven (no rescan possible)",
            "Not fixed yet 2026-11-20", "No CI run", "Rescan planned for 2026-12-01",
            "Awaiting rescan", "Not verified yet; fix shipped in 2.4",
            "Not rechecked since the 2026-11-20 deploy", "Not re-run after the 2026-11-20 fix",
            "Retest scheduled", "not checked in CI", "Not possible: no test environment (2026-11-22)",
            "Not reproduced on 2026-11-20", "Not detected, Bandit 1.9.4",
            "Rescan expected after deploy", "No findings yet in the rescan",
            # The round-4 gate inputs.
            "Rescan not run", "Retest pending", "Retest: TBD", "Fix deployed 2026-11-20; rescan not done",
            "Bandit rescan failed to start", "No findings; rescan not run", "Not reproduced (no PoC available)",
            # The earlier must-pass values, which are not in the form.
            "Not reproduced: PoC from F1 fails after the fix, 2026-11-20",
            "Not reported by the Bandit 1.9.4 rescan on 2026-11-21",
            "Bandit 1.9.4 rescan 2026-11-21: 0 results at app.py:24",
            # Near the form: wrong source word, no name, bad or missing date, no colon, no result.
            "Scan Bandit 1.9.4 2026-11-21: 0 results", "Retest Bandit 2026-11-21: 0 results",
            "Rescan 2026-11-21: 0 results", "Rescan Bandit 1.9.4 2026-13-40: 0 results",
            "Rescan Bandit 1.9.4 21/11/2026: 0 results", "Rescan Bandit 1.9.4: 0 results",
            "Rescan Bandit 1.9.4 2026-11-21 0 results", "Rescan Bandit 1.9.4 2026-11-21:",
            "Rescanned Bandit 2026-11-21: 0 results",
            # In the form, but the result is a placeholder or says the run did not happen.
            "Rescan Bandit 1.9.4 2026-11-21: not run", "Test test_upload 2026-11-21: not done",
            "CI pipeline 2026-11-21: pending", "PoC F1-exploit 2026-11-20: TBD",
            "Rescan Bandit 1.9.4 2026-11-21: failed to start", "CI nightly 2026-11-21: results to follow",
            "Rescan Bandit 1.9.4 2026-11-21: awaiting triage", "Test suite 2026-11-21: planned",
            "Rescan Bandit 1.9.4 2026-11-21: scheduled for Monday", "CI build 2026-11-21: not finished yet",
            "Rescan Bandit 1.9.4 2026-11-21: n/a", "Rescan Bandit 1.9.4 2026-11-21: none", "PoC x 2026-11-20: -",
            # Replanned patch, round 1 (gate2 RP1, gate1 N9): a date after today (2026-11-22 here),
            # and results that say the run did not happen or finish.
            "Rescan Bandit 1.9.4 2026-12-01: 0 results", "Rescan Bandit 1.9.4 2099-01-01: 0 results",
            "Rescan Bandit 1.9.4 2026-11-21: skipped", "CI nightly 2026-11-21: cancelled",
            "CI nightly 2026-11-21: canceled", "Test suite 2026-11-21: errored",
            "CI build 2026-11-21: aborted", "Rescan Bandit 1.9.4 2026-11-21: failed",
            "Rescan Bandit 1.9.4 2026-11-21: Failed.", "CI nightly 2026-11-21: run failed",
            "Rescan Bandit 1.9.4 2026-11-21: will run after deploy",
            "Rescan Bandit 1.9.4 2026-11-21: will confirm", "Rescan Bandit 1.9.4 2026-11-21: expected 0 results",
            "Test CI 2026-11-21: to be run", "Rescan Bandit 1.9.4 2026-11-21: couldn't run",
            "Rescan Bandit 1.9.4 2026-11-21: could not run",
            # A placeholder name (gate1 N9), a name with no letter or digit and a date without
            # dashes (gate2 RP2, gate1 N12).
            "Rescan TBD 2026-11-21: 0 results", "PoC n/a 2026-11-21: 0 results",
            "PoC ? 2026-11-21: 0 results", "Rescan - 2026-11-21: 0 results",
            "Rescan Bandit 20261121: 0 results",
        )
        for retest in failing:
            with self.subTest(retest=retest):
                found = self.rules(edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |", f"| {retest} |"))
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith("C4:") and "F1" in found[0] and form in found[0], found)
        # In the form. The result may be a negative finding; any case works for the source word.
        for retest in ("Rescan Bandit 1.9.4 2026-11-21: 0 results at app.py:24",
                       "PoC F1-exploit 2026-11-20: request rejected with 403",
                       "CI test_upload_rejects_shell 2026-11-21: passed",
                       "PoC F1-exploit 2026-11-20: not reproduced, request rejected after the fix",
                       "Rescan Bandit 1.9.4 2026-11-21: not reported",
                       "Rescan Bandit 1.9.4 2026-11-21: no findings for B602",
                       "Rescan ToolA 1.0 2026-11-21: no findings",
                       "test pytest tests/test_upload.py 2026-11-21: 12 passed, 0 failed",
                       "RESCAN Semgrep OSS 1.186.0 2026-11-21: 0 results",
                       # "failed" is a result when it says what failed.
                       "PoC F1-exploit 2026-11-20: exploit failed, request rejected",
                       "PoC F1-exploit 2026-11-20: PoC failed after the fix: 403",
                       "Rescan Bandit 1.9.4 2026-11-22: 0 results"):  # today itself is allowed
            with self.subTest(retest=retest):
                self.assertEqual(self.rules(edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |", f"| {retest} |")), [])
        # A fixed Medium needs no retest evidence.
        self.assertEqual(self.rules(edit("| High |", "| Medium |", text)), [])

    def test_d13_run_state_words_only_at_the_start_of_the_result(self):
        # D-13 (gate1 N13, N14, N16; gate2 RP4, RP5, RP7): run-state words fail only at the start
        # of the result or as the whole result; "not run", "pending" and "failed to start" fail
        # anywhere. The reviewer still reads the result, so not every phrasing is caught.
        cell = "| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |"
        form = "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>"
        honest = ("request rejected with 403 as expected", "none of the 3 B602 hits remain",
                  "passed; 2 unrelated tests skipped", "the old token will no longer work",
                  "yet again rejected", "errored requests now return 400")
        for result in honest:
            with self.subTest(result=result):
                self.assertEqual(self.rules(edit(cell, f"| PoC F1-exploit 2026-11-20: {result} |")), [])
        did_not_run = (
            # Synonyms that said the run did not happen or finish, and passed.
            "didn't run", "did not finish", "timed out", "in progress", "queued", "postponed",
            "deferred", "going to rerun", "Didn\u2019t run: runner offline", "did not run",
            "didn't finish", "timed out after 30 minutes", "queued behind the nightly build",
            "in progress, 40% done", "deferred to next sprint", "going to re-run tomorrow",
            # Still matched anywhere.
            "0 results so far; full rescan pending", "partial: 0 results, full rescan not run",
            "0 results; the full run failed to start",
            # Whole-result words with trailing punctuation or a clause after it.
            "errored.", "errored: runner lost", "none.", "yet", "failed, see log", "yet to run")
        for result in did_not_run:
            with self.subTest(result=result):
                found = self.rules(edit(cell, f"| Rescan Bandit 1.9.4 2026-11-21: {result} |"))
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith("C4:") and form in found[0], found)
        # D-13: a name made only of underscores or other symbols is no name.
        for retest in ("Rescan ___ 2026-11-21: 0 results", "PoC _-_ 2026-11-21: 0 results",
                       "CI __init__ 2026-11-21: passed"):
            with self.subTest(retest=retest):
                found = self.rules(edit(cell, f"| {retest} |"))
                if retest.startswith("CI"):
                    self.assertEqual(found, [])  # a name with letters among the underscores
                else:
                    self.assertEqual(len(found), 1, found)
                    self.assertTrue(found[0].startswith("C4:"), found)

    def test_w7_9_overclaim_words_fail(self):
        for claim in ("The service is secure.", "Scans found no vulnerabilities.",
                      "The code is vulnerability-free.", "No known vulnerabilities remain.",
                      "The app is Secure now.", "The service is secured.",
                      "The API is securely configured."):
            with self.subTest(claim=claim):
                found = self.rules(TRIAGED + "\n## Summary\n\n" + claim + "\n")
                self.assertEqual(len(found), 1)
                self.assertTrue(found[0].startswith("C5:"), found[0])

    def test_w7_9_overclaim_wrapped_across_lines_fails(self):
        # Markdown here is hard-wrapped, so a phrase can start on one line and end on the next.
        summary_line = TRIAGED.count("\n") + 4  # the line where the claim starts
        for claim in ("Scans found no\nvulnerabilities.", "There are no known\n  vulnerabilities.",
                      "The code is vulnerability-\nfree.", "It is vulnerability\nfree."):
            with self.subTest(claim=claim):
                found = self.rules(TRIAGED + "\n## Summary\n\n" + claim + "\n")
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith(f"C5: line {summary_line} "), found[0])

    def test_w7_9_quoted_identifiers_and_other_words_pass(self):
        text = TRIAGED + "\n## Summary\n\nThe `secure` flag is missing. MD5 is insecure. Security review is not proven.\n"
        self.assertEqual(self.rules(text), [])
        wrapped = TRIAGED + "\n## Summary\n\nThe tool printed `no\nvulnerabilities` for the clean folder.\n"
        self.assertEqual(self.rules(wrapped), [])
        fenced = TRIAGED + "\n## Tool output\n\n```text\nNo vulnerabilities found\n```\n"
        self.assertEqual(self.rules(fenced), [])

    def test_w7_9_stray_backtick_does_not_hide_an_overclaim(self):
        # Review W7-r1 recheck N1: an odd backtick must not pair with one on the next line.
        line = TRIAGED.count("\n") + 5
        for summary in ("The title had a ` in it.\nThe service is secure. See `report.md`.",
                        "A stray ` here.\nNo vulnerabilities remain, see `log`.",
                        "```text\nunclosed fence\nThe service is secure."):
            with self.subTest(summary=summary):
                found = self.rules(TRIAGED + "\n## Summary\n\n" + summary + "\n")
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith("C5: line "), found)
        found = self.rules(TRIAGED + "\n## Summary\n\nThe title had a ` in it.\nThe service is secure.\n")
        self.assertTrue(found[0].startswith(f"C5: line {line} "), found)

    def test_w7_9_honest_wording_passes(self):
        # Review W7-r1 recheck N2: these state what was not done, or name a protocol.
        for summary in ("There was no vulnerability scan of an image, because none exists.",
                        "The answer was no\nvulnerability database download happened offline.",
                        "We ran no vulnerability scanner on the image.",
                        "Trivy had no vulnerability data for this package and no vulnerability feed.",
                        "F7 opens port 22 (Secure Shell) to 0.0.0.0/0."):
            with self.subTest(summary=summary):
                self.assertEqual(self.rules(TRIAGED + "\n## Summary\n\n" + summary + "\n"), [])
        # The singular still fails when it is the claim itself.
        for claim in ("There is no vulnerability in the service.", "Secure Shell is secure."):
            with self.subTest(claim=claim):
                found = self.rules(TRIAGED + "\n## Summary\n\n" + claim + "\n")
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith("C5:"), found)

    def test_x2_merge_and_coverage_output_has_no_overclaim(self):
        clean = self.merge("code=" + str(FIXTURES / "bandit-clean.sarif"))
        self.assertEqual(self.rules(clean), [])  # 0 findings: nothing to triage, no overclaim
        self.assertEqual([l for l in self.rules(self.merge(*SAMPLE, root=SAMPLE_ROOT)) if l.startswith("C5")], [])

    def test_report_without_coverage_fails(self):
        text = re.sub(r"## Coverage\n.*?(?=## Findings)", "", TRIAGED, flags=re.S)
        found = self.rules(text)
        self.assertEqual(len(found), 1)
        self.assertIn("Coverage", found[0])

    def test_triage_values_must_be_known(self):
        found = self.rules(edit("| yes | yes | fixed |", "| maybe | yes | fixed |"))
        self.assertEqual(len(found), 1)
        self.assertIn("Reachable", found[0])


class Malformed(Base):
    def one_error(self, data):
        done = run("merge", "code=" + self.write("bad.sarif", data))
        self.assertEqual(done.returncode, 1)
        lines = (done.stdout + done.stderr).strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("bad.sarif", lines[0])
        self.assertIn("not valid SARIF", lines[0])
        return lines[0]

    def test_w7_10_malformed_sarif_gives_one_clear_error(self):
        self.assertIn("JSON", self.one_error('{"runs": [ '))
        self.assertIn("runs", self.one_error({"version": "2.1.0"}))
        self.assertIn("tool.driver.name", self.one_error({"runs": [{"results": []}]}))
        self.assertIn("results", self.one_error({"runs": [{"tool": {"driver": {"name": "T"}}, "results": {}}]}))

    def test_w7_10_malformed_result_shapes_give_one_clear_error(self):
        # The shapes from review W7-r1 B2; each used to end in a traceback.
        location = [{"physicalLocation": {"artifactLocation": {"uri": "a.py"}, "region": {"startLine": 1}}}]
        good = {"ruleId": "R", "message": {"text": "m"}, "locations": location}
        shapes = {
            "tool is a string": None,
            "locations is an object": {"locations": {"a": 1}},
            "artifactLocation is a string": {"locations": [{"physicalLocation": {"artifactLocation": "a.py"}}]},
            "uri is a number": {"locations": [{"physicalLocation": {"artifactLocation": {"uri": 5}}}]},
            "message is a string": {"message": "m"},
            "message text is a number": {"message": {"text": 5}},
            "ruleId is a number": {"ruleId": 7},
            "rule is a string": {"ruleId": None, "rule": "R"},
        }
        for name, change in shapes.items():
            with self.subTest(shape=name):
                if change is None:
                    data = {"runs": [{"tool": "x", "results": []}]}
                    where = "run 1"
                else:
                    item = {k: v for k, v in {**good, **change}.items() if v is not None}
                    data = {"runs": [{"tool": {"driver": {"name": "T"}}, "results": [item]}]}
                    where = "run 1 result 1"
                self.assertIn(where, self.one_error(data))

    def test_missing_file_is_one_error(self):
        done = run("merge", "code=" + str(self.dir / "absent.sarif"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len((done.stdout + done.stderr).strip().splitlines()), 1)


class SkillText(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text()

    def test_help_exits_zero(self):
        done = run("--help")
        self.assertEqual(done.returncode, 0)
        self.assertIn("merge", done.stdout)

    def test_check_today_defaults_to_the_local_date(self):
        # RP1: a Retest date after today fails. --today sets today for tests; the default is
        # today's local date (D-13: it was the UTC date), so a date far ahead fails and an old
        # one passes without the option.
        done = run("check", "--help")
        self.assertEqual(done.returncode, 0)
        self.assertIn("--today", done.stdout)
        self.assertIn("local date", " ".join(done.stdout.split()))
        # D-13: the local date decides. At UTC+14 and at UTC-12 the local dates are 26 hours
        # apart, so a run dated today at UTC+14 is in the future at UTC-12. With a UTC default
        # one of the two checks below fails at any hour.
        ahead = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=14)).date()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |",
                                 f"| Rescan ToolA 1.0 {ahead.isoformat()}: 0 results at `x.py:5` |"))
            east = run("check", str(path), env={"TZ": "EAST-14"})  # POSIX: local is UTC+14
            self.assertEqual(east.stdout.strip(), "pass", east.stdout + east.stderr)
            west = run("check", str(path), env={"TZ": "WEST+12"})  # POSIX: local is UTC-12
            self.assertEqual(west.returncode, 1, west.stdout)
            self.assertTrue(west.stdout.startswith("C4: F1"), west.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(edit("| Rescan ToolA 1.0 2026-11-21: 0 results at `x.py:5` |",
                                 "| Rescan ToolA 1.0 2999-01-01: 0 results at `x.py:5` |"))
            done = run("check", str(path))
            self.assertEqual(done.returncode, 1)
            self.assertTrue(done.stdout.startswith("C4: F1"), done.stdout)
            path.write_text(TRIAGED)
            self.assertEqual(run("check", str(path)).stdout.strip(), "pass")
            bad = run("check", "--today", "22/11/2026", str(path))
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn("Traceback", bad.stderr)

    def test_x7_without_a_shell_rule(self):
        rule = re.search(r"^#+ Without a shell\n(.*?)(?=^#+ |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(rule, "SKILL.md needs a 'Without a shell' section")
        self.assertIn("sarif_triage.py", rule.group(1))
        self.assertIn("not run", rule.group(1))

    def test_x7_without_a_shell_label_passes_check(self):
        # The coverage line the section tells the agent to write must be one check accepts.
        rule = re.search(r"^#+ Without a shell\n(.*?)(?=^#+ |\Z)", self.text, re.M | re.S).group(1)
        label = re.search(r"`- <category>: ([^`]+)`", rule)
        self.assertIsNotNone(label, "the section gives the coverage line as `- <category>: ...`")
        self.assertIn("not run", label.group(1))
        text = re.sub(r"^- (\w+): .*$", lambda m: f"- {m.group(1)}: {label.group(1)}", TRIAGED, flags=re.M)
        self.assertNotIn("scanned", text)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.md"
            path.write_text(text)
            done = run("check", str(path))
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "pass"))

    def test_eval_versions_come_from_the_fixture_readme(self):
        # Review W7-r1 recheck N3: the eval agent runs no scanner, so the setup names where its
        # versions come from, and rule 6 accepts that version or the script's label.
        readme = (ROOT / "evals" / "scanning-vulnerabilities" / "README.md").read_text()
        setup = " ".join(readme.split("## Setup", 1)[1].split("## ", 1)[0].split())
        self.assertIn('"Tool and version" column', setup)
        self.assertIn("| Tool and version |", (FIXTURES / "README.md").read_text())
        rule = " ".join(re.search(r"^6\. (.*?)(?=^7\. )", readme, re.M | re.S).group(1).split())
        self.assertIn('"Bandit 1.9.4"', rule)
        self.assertIn('"Bandit, version per SARIF: 1.9.4"', rule)

    def test_triage_retest_row_names_the_source(self):
        # Gate round 4 (B3, F11): SKILL.md states the one form check enforces, and who reads the content.
        triage = self.flat_section("Triage")
        # The pipes are escaped so the Markdown table keeps its three columns.
        self.assertIn("| Retest | `<Rescan\\|Test\\|PoC\\|CI> <tool or name> <YYYY-MM-DD>: <result>` | "
                      "Required for fixed Critical or High", triage)
        self.assertIn("`check` reads only the form; a reviewer reads the content", triage)
        # Replanned patch, round 1: the row names the date and result rules check now adds.
        self.assertIn("The date is the run date, not after today", triage)
        self.assertIn("skipped, cancelled, errored", triage)
        # D-13: the default date is the local date, and the word list is not every phrasing.
        self.assertIn("not after today (your local date; `check --today` sets it)", triage)
        self.assertIn("at the start of the result", triage)
        self.assertIn("The list is not every phrasing: a reviewer still reads the result", triage)
        done = " ".join(self.text.split("## Check your work", 1)[1].split())
        self.assertIn("retest evidence in the Retest form", done)

    def test_triage_owner_is_a_named_person(self):
        # Gate review N3: SKILL.md states the rule check enforces.
        triage = self.flat_section("Triage")
        self.assertIn("| Owner | a named person, not a team or role |", triage)

    def test_eval_results_record_changes_after_the_run(self):
        # Gate review N2: results.md says what changed after the graded run.
        results = (ROOT / "evals" / "scanning-vulnerabilities" / "results.md").read_text()
        self.assertIn("\n## Changes after the run\n", results)
        changes = " ".join(results.split("\n## Changes after the run\n", 1)[1].split("\n## ", 1)[0].split())
        self.assertIn("`commands.txt`", changes)
        self.assertIn("rule 9", changes)
        self.assertIn("The PASS grade is for the run as graded", changes)

    def flat_section(self, title):
        return " ".join(self.text.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0].split())

    def test_final_check_run_is_recorded(self):
        # Eval finding 1: the final check run left no record a reviewer could confirm.
        step = " ".join(re.search(r"^7\. \*\*Write the report\.\*\*(.*?)(?=^## )", self.text, re.M | re.S)
                        .group(1).split())
        self.assertIn("record the command and its `pass` in the report's commands", step)

    def test_same_as_row_with_a_yes_names_the_input(self):
        # Eval finding 2: "same as F6" rows named the input only through another row.
        triage = self.flat_section("Triage")
        self.assertIn('Write "same as F4" in the Reason column. A yes in Reachable or Exploitable '
                      "on that row still names the entry point or input.", triage)

    def test_report_words_ban_safe_and_clean(self):
        # Eval finding 3: "safe" and "clean" are banned in words; check cannot catch them without
        # flagging honest text such as "It does not show that the helper is safe", so the
        # skill says to read for them.
        words = self.flat_section("Report words")
        self.assertRegex(words, r'Never write "secure", .*"safe" or "clean" about the target')
        self.assertIn("`check` does not catch these two; read for them.", words)

    def test_eval_logs_commands_and_hides_the_samples(self):
        # Eval finding 4: rule 9 could not be checked from files.
        readme = " ".join((ROOT / "evals" / "scanning-vulnerabilities" / "README.md").read_text().split())
        setup = readme.split("## Setup", 1)[1].split("## ", 1)[0]
        self.assertIn("`commands.txt`", setup)
        self.assertIn("`chmod 000 /tmp/scan`", setup)
        self.assertNotIn("they do not exist in the run", setup)
        rule = re.search(r" 9\. (.*?)$", readme).group(1)
        self.assertIn("`commands.txt`", rule)

    def test_scope_is_local_paths_the_owner_names(self):
        self.assertIn("local paths the owner names", " ".join(self.text.split()))
        self.assertIn("DAST", self.text)

    def test_names_upstream_threat_model(self):
        self.assertIn("threat-modelling", self.text)

    def test_outside_effects_need_contract_or_exact_plan(self):
        flat = " ".join(self.text.split())  # phrases may wrap across lines
        self.assertIn("pre-authorizes that exact effect", flat)
        self.assertIn("the owner approves the exact plan", flat)


if __name__ == "__main__":
    unittest.main()

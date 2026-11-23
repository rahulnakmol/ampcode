"""Tests for skills/monitoring: the SLO checker (cases W12.1 to W12.9, X2) and the skill text.

Run: python3 -m unittest tests.test_monitoring -v

Every expected number is worked out by hand in the comments, never taken from the script.
"""

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "monitoring"
SCRIPT = SKILL / "scripts" / "slo_check.py"
EXAMPLE = SKILL / "templates" / "slos.json"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(ROOT / "tests"))

import slo_check  # noqa: E402
from test_skill_anatomy import problems as anatomy  # noqa: E402

# A small SLO file written by hand for these tests. It follows SKILL.md and templates/slos.json.
GOOD = {
    "service": "invoice reminders",
    "design": "docs/designs/invoice-reminders.md",
    "slos": [
        {
            "id": "SLO-1",
            "sli": {
                "nfr": "NFR-2",
                "good": "POST /reminders responses with a status below 500",
                "valid": "all POST /reminders responses",
            },
            "target": 99.9,
            "window_days": 30,
            "alerts": [
                {
                    "id": "ALERT-1",
                    "severity": "page",
                    "burn_rate": 14.4,
                    "long_window": "1h",
                    "short_window": "5m",
                    "runbook": "runbooks/reminders.md",
                    "firing": {
                        "environment": "staging",
                        "date": "2026-11-20",
                        "evidence": "https://ci.example.com/runs/812",
                    },
                },
                {
                    "id": "ALERT-2",
                    "severity": "page",
                    "burn_rate": 6,
                    "long_window": "6h",
                    "short_window": "30m",
                    "runbook": "runbooks/reminders.md",
                    "firing": {
                        "environment": "staging",
                        "date": "2026-11-20",
                        "evidence": "https://ci.example.com/runs/813",
                    },
                },
                {
                    # An extra ticket alert: allowed beside the two required page pairs.
                    "id": "ALERT-3",
                    "severity": "ticket",
                    "burn_rate": 1,
                    "long_window": "3d",
                    "short_window": "6h",
                    "runbook": "runbooks/reminders.md",
                    "firing": {
                        "environment": "ci",
                        "date": "2026-11-20",
                        "evidence": "https://ci.example.com/runs/814",
                    },
                },
            ],
        }
    ],
}

RUNBOOK = "# Runbook: invoice reminders\n\nWhat fired, impact, first checks, mitigation, escalation.\n"


def spec(change=None):
    """A deep copy of GOOD, changed by change(data) when given."""
    data = copy.deepcopy(GOOD)
    if change:
        change(data)
    return data


def alert(data, index=0):
    return data["slos"][0]["alerts"][index]


class Workspace:
    """A temporary folder with slos.json and its runbook."""

    def __init__(self, data, runbook=RUNBOOK):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "runbooks").mkdir()
        if runbook is not None:
            (self.base / "runbooks" / "reminders.md").write_text(runbook)
        self.path = self.base / "slos.json"
        self.path.write_text(data if isinstance(data, str) else json.dumps(data, indent=2))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args, str(self.path)],
                              capture_output=True, text=True, timeout=60)


def found(data, release=False, runbook=RUNBOOK):
    """(problems, status lines) for data, checked in a fresh workspace."""
    with Workspace(data, runbook) as ws:
        return slo_check.check(ws.path.read_text(), ws.base, release=release)


def rules(data, release=False, runbook=RUNBOOK):
    return sorted({p.split(":", 1)[0] for p in found(data, release, runbook)[0]})


class Targets(unittest.TestCase):
    def test_hand_written_file_passes(self):
        self.assertEqual(found(GOOD)[0], [])
        self.assertEqual(found(GOOD, release=True)[0], [])

    def test_w12_1_target_outside_0_to_100(self):
        # W12.1: a target must be a number above 0 and below 100. 0 % and 100 % are outside too:
        # 100 % leaves no error budget, so no burn rate can be computed.
        for target in (100.5, -1, 0, 100, 150, "99.9", True, None):
            with self.subTest(target=target):
                data = spec(lambda d: d["slos"][0].update(target=target))
                self.assertEqual(rules(data), ["M1"])
                self.assertIn("SLO-1", found(data)[0][0])

    def test_w12_1_targets_inside_pass(self):
        for target in (99.9, 50, 99.999, 95, 0.5):
            with self.subTest(target=target):
                data = spec(lambda d: d["slos"][0].update(target=target))
                # 0.5 % leaves a 99.5 % budget: 14.4 x 99.5 % is above 100 %, so M4 says the
                # alerts can never fire. Only M1 matters here.
                self.assertNotIn("M1", rules(data))

    def test_w12_1_window_must_be_whole_days(self):
        for window in (0, -30, "30", 7.5, None):
            with self.subTest(window=window):
                data = spec(lambda d: d["slos"][0].update(window_days=window))
                self.assertEqual(rules(data), ["M1"])


class ErrorBudget(unittest.TestCase):
    def test_w12_2_error_budget_minutes(self):
        # W12.2: 99.9 % over 30 days. 30 x 24 x 60 = 43,200 minutes; 0.1 % of that is 43.2.
        self.assertEqual(slo_check.error_budget_minutes(Decimal("99.9"), 30), Decimal("43.2"))
        # 99.95 % over 28 days: 28 x 1,440 = 40,320 minutes; 0.05 % is 20.16.
        self.assertEqual(slo_check.error_budget_minutes(Decimal("99.95"), 28), Decimal("20.16"))
        # 99 % over 7 days: 10,080 minutes; 1 % is 100.8.
        self.assertEqual(slo_check.error_budget_minutes(Decimal("99"), 7), Decimal("100.8"))

    def test_w12_2_check_and_alerts_print_the_budget(self):
        with Workspace(GOOD) as ws:
            check = ws.run("check")
            alerts = ws.run("alerts")
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertIn("43.2 minutes", check.stdout)
        self.assertEqual(alerts.returncode, 0, alerts.stdout)
        self.assertIn("43.2 minutes", alerts.stdout)


class Alerts(unittest.TestCase):
    def test_w12_3_alerts_prints_the_fast_and_slow_pairs(self):
        # W12.3: from the Google SRE Workbook, table 5-8.
        # Fast: 14.4 x over 1 hour and 5 minutes. Error-rate threshold 14.4 x 0.1 % = 1.44 %.
        #       Budget spent when it fires: 14.4 x 1 h / 720 h = 2 %.
        # Slow: 6 x over 6 hours and 30 minutes. Threshold 6 x 0.1 % = 0.6 %.
        #       Budget spent: 6 x 6 h / 720 h = 5 %.
        with Workspace(GOOD) as ws:
            out = ws.run("alerts").stdout
        self.assertIn("| fast | page | 14.4× | 1 hour | 5 minutes | 1.44 % | 2 % |", out)
        self.assertIn("| slow | page | 6× | 6 hours | 30 minutes | 0.6 % | 5 % |", out)
        self.assertIn("SLO-1", out)
        self.assertIn("NFR-2", out)

    def test_w12_3_thresholds_follow_the_target(self):
        # A 95 % latency SLO: error budget 5 %. Fast threshold 14.4 x 5 % = 72 %; slow 6 x 5 % = 30 %.
        data = spec(lambda d: d["slos"][0].update(target=95))
        with Workspace(data) as ws:
            out = ws.run("alerts").stdout
        self.assertIn("| fast | page | 14.4× | 1 hour | 5 minutes | 72 % | 2 % |", out)
        self.assertIn("| slow | page | 6× | 6 hours | 30 minutes | 30 % | 5 % |", out)

    def test_w12_3_a_pair_that_can_never_fire_is_flagged(self):
        # 90 %: error budget 10 %. Fast threshold 14.4 x 10 % = 144 %, above 100 %: it never fires.
        # Slow threshold 6 x 10 % = 60 %: it can fire.
        data = spec(lambda d: d["slos"][0].update(target=90))
        with Workspace(data) as ws:
            out = ws.run("alerts").stdout
        fast = next(l for l in out.splitlines() if l.startswith("| fast |"))
        slow = next(l for l in out.splitlines() if l.startswith("| slow |"))
        self.assertIn("never fires", fast)
        self.assertNotIn("never fires", slow)

    def test_w12_3_pairs_match_the_reference_table(self):
        # Human test, automated: the windows in the script equal the table in burn-rates.md.
        text = (SKILL / "reference" / "burn-rates.md").read_text()
        self.assertIn("https://sre.google/workbook/alerting-on-slos/", text)
        rows = re.findall(r"^\| (fast|slow) \| (\w+) \| ([\d.]+)× \| (.+?) \| (.+?) \| (\d+) % \|", text, re.M)
        self.assertEqual(rows, [
            ("fast", "page", "14.4", "1 hour", "5 minutes", "2"),
            ("slow", "page", "6", "6 hours", "30 minutes", "5"),
        ])
        self.assertEqual([(p[0], str(p[2]), p[3], p[4]) for p in slo_check.PAIRS],
                         [("fast", "14.4", "1h", "5m"), ("slow", "6", "6h", "30m")])

    def test_w12_4_slo_without_burn_rate_alerts(self):
        # W12.4: no alerts key, an empty list, or alerts that are not a list.
        for change in (lambda d: d["slos"][0].pop("alerts"),
                       lambda d: d["slos"][0].update(alerts=[]),
                       lambda d: d["slos"][0].update(alerts="ALERT-1")):
            with self.subTest():
                data = spec(change)
                self.assertEqual(rules(data), ["M3"])
                self.assertIn("SLO-1", found(data)[0][0])

    def test_w12_4_malformed_burn_rate_alert(self):
        # Mutates the extra ticket alert (index 2), so both required page pairs stay intact.
        changes = {
            "no burn rate": lambda d: alert(d, 2).pop("burn_rate"),
            "zero burn rate": lambda d: alert(d, 2).update(burn_rate=0),
            "text burn rate": lambda d: alert(d, 2).update(burn_rate="14.4"),
            "no short window": lambda d: alert(d, 2).pop("short_window"),
            "word window": lambda d: alert(d, 2).update(long_window="3 days"),
            "short not shorter": lambda d: alert(d, 2).update(short_window="3d"),
            "long beyond the SLO window": lambda d: alert(d, 2).update(long_window="31d", short_window="1d"),
            "unknown severity": lambda d: alert(d, 2).update(severity="urgent"),
        }
        for name, change in changes.items():
            with self.subTest(name):
                self.assertEqual(rules(spec(change)), ["M4"])

    def test_w12_4_slo_missing_a_required_pair(self):
        # Review M2: every SLO needs a page alert equal to each PAIRS row (fast and slow).
        cases = {
            "slow pair dropped": (lambda d: d["slos"][0]["alerts"].pop(1), ["slow"]),
            "fast burn rate changed": (lambda d: alert(d).update(burn_rate=10), ["fast"]),
            "fast short window changed": (lambda d: alert(d).update(short_window="10m"), ["fast"]),
            "slow pair is a ticket": (lambda d: alert(d, 1).update(severity="ticket"), ["slow"]),
            "14.4x on the slow windows": (lambda d: alert(d, 1).update(burn_rate=14.4), ["slow"]),
            "only a ticket alert": (lambda d: d["slos"][0].update(alerts=[d["slos"][0]["alerts"][2]]),
                                    ["fast", "slow"]),
        }
        for name, (change, missing) in cases.items():
            with self.subTest(name):
                data = spec(change)
                self.assertEqual(rules(data), ["M3"])
                lines = [p for p in found(data)[0] if p.startswith("M3")]
                self.assertEqual(len(lines), 1, lines)
                for pair in missing:
                    self.assertIn(pair, lines[0])
                for pair in {"fast", "slow"} - set(missing):
                    self.assertNotIn(f"the {pair} pair", lines[0])

    def test_w12_4_equal_windows_in_other_units_count(self):
        # 60m is 1 hour and 360m is 6 hours, so these still equal the fast and slow pairs.
        self.assertEqual(found(spec(lambda d: alert(d).update(long_window="60m")))[0], [])
        self.assertEqual(found(spec(lambda d: alert(d, 1).update(long_window="360m")))[0], [])

    def test_w12_4_alert_that_can_never_fire(self):
        # 90 %: 14.4 x 10 % = 144 % errors needed, which is impossible.
        data = spec(lambda d: d["slos"][0].update(target=90))
        self.assertEqual(rules(data), ["M4"])
        self.assertIn("ALERT-1", found(data)[0][0])

    def test_n4_threshold_of_exactly_100_percent_never_fires(self):
        # Review N4: 90 % target, burn 10: 10 x 10 % = 100 %. Rules fire on "greater than", so
        # the error rate can never be above 100 %. Burn 9.9 gives 99 %, which can fire.
        def at(burn):
            def change(d):
                d["slos"][0]["target"] = 90
                alert(d, 2)["burn_rate"] = burn
            return [p for p in found(spec(change))[0] if "ALERT-3" in p]
        self.assertEqual(len(at(10)), 1)
        self.assertTrue(at(10)[0].startswith("M4"))
        self.assertEqual(at(9.9), [])

    def test_r4_target_too_low_for_the_pairs_says_what_to_do(self):
        # Recheck R4: the fast pair never fires when 14.4 x (100 - target) >= 100, so at
        # 93.05 % (14.4 x 6.95 = 100.08) it fails, and at 93.06 % (14.4 x 6.94 = 99.936) it passes.
        low = found(spec(lambda d: d["slos"][0].update(target=93.05)))[0]
        self.assertEqual(len(low), 1, low)
        self.assertTrue(low[0].startswith("M4: ALERT-1"), low)
        for words in ("owner raises the target", "PAIRS", "every service", "Low targets"):
            self.assertIn(words, low[0])
        self.assertEqual(found(spec(lambda d: d["slos"][0].update(target=93.06)))[0], [])

    def test_w12_5_alert_whose_runbook_file_is_missing(self):
        # W12.5: the runbook path is relative to the SLO file's folder.
        self.assertEqual(rules(GOOD, runbook=None), ["M5"])
        self.assertEqual(rules(spec(lambda d: alert(d).update(runbook="runbooks/other.md"))), ["M5"])
        self.assertEqual(rules(spec(lambda d: alert(d).pop("runbook"))), ["M5"])
        self.assertEqual(rules(spec(lambda d: alert(d).update(runbook="runbooks"))), ["M5"])


class Firing(unittest.TestCase):
    def test_w12_6_alert_without_firing_evidence_is_not_proven(self):
        # W12.6: check passes and labels the alert "not proven"; check --release fails on it.
        data = spec(lambda d: alert(d, 1).pop("firing"))
        problems, status = found(data)
        self.assertEqual(problems, [])
        line = next(l for l in status if "ALERT-2" in l)
        self.assertIn("not proven", line)
        self.assertEqual(rules(data, release=True), ["M6"])
        release = found(data, release=True)[0]
        self.assertEqual(len(release), 1)
        self.assertIn("ALERT-2", release[0])
        self.assertIn("not proven", release[0])

    def test_w12_6_cli_release(self):
        data = spec(lambda d: alert(d, 1).pop("firing"))
        with Workspace(data) as ws:
            plain = ws.run("check")
            release = ws.run("check", "--release")
        self.assertEqual(plain.returncode, 0)
        self.assertEqual(plain.stdout.splitlines()[0], "pass")
        self.assertIn("not proven", plain.stdout)
        self.assertEqual(release.returncode, 1)
        lines = release.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("M6: ALERT-2"), lines)

    def test_w12_6_fired_alert_names_where_and_when(self):
        status = found(GOOD)[1]
        line = next(l for l in status if "ALERT-1" in l)
        self.assertIn("staging", line)
        self.assertIn("2026-11-20", line)

    def test_w12_7_firing_evidence_from_production_is_rejected(self):
        # W12.7: production names, in any case and with suffixes, are rejected, in check and release.
        # Review B1: numbered, joined and camelCase names too, and canary, blue-green and shadow
        # deployments, which serve production traffic.
        for env in ("production", "prod", "Prod-EU", "live", "prd", "eu-prod-2", "PRODUCTION",
                    "prod1", "prod01", "prod2", "eu-prod1", "prd01", "production2", "live2",
                    "ProdEU", "prodeu", "productionEU", "PROD_EU", "prod-canary", "canary",
                    "canary-eu", "blue", "green", "blue-green", "BlueGreen", "green-slot",
                    "shadow", "production-shadow",
                    # Recheck R2: prod or prd glued on inside a word.
                    "euprod", "weuprod1", "aksprod01", "k8sprod", "appprod", "liveprod", "useast1prod",
                    "productioneu", "eu-production",
                    # Recheck R1: prod and prd stay production even beside a test word.
                    "staging-prod-copy", "qa-prod-mirror",
                    # Gate 1 F3: go-live names production, joined or not, like prod.
                    "golive", "go-live", "GoLive", "golive-eu", "eu-golive2", "staging-golive",
                    "uat-go-live"):
            with self.subTest(env=env):
                data = spec(lambda d: alert(d)["firing"].update(environment=env))
                self.assertEqual(rules(data), ["M7"])
                self.assertEqual(rules(data, release=True), ["M7"])

    def test_w12_7_environments_outside_production_pass(self):
        for env in ("staging", "pre-prod", "preprod", "non-prod", "nonprod", "test", "dev", "pre-production",
                    "pre_prod", "non-production", "pre-live", "preProd", "checkout-staging", "ci", "qa2",
                    "PreProd", "NonProd", "nonProdEU", "eu-nonprod1",
                    # Recheck R1: colour, canary, shadow and live words beside a test-environment word.
                    "staging-green", "canary-staging", "staging-shadow", "dev-blue", "green-test",
                    "test-canary", "blue-team-lab", "green-field-dev", "uat-blue", "sandbox-canary",
                    "stage-green", "live-demo", "ci-shadow", "qa-live",
                    # Recheck R2: words that contain prod but do not mean production.
                    "reproduce-lab", "reproduce", "product-staging", "products-staging",
                    "productivity-test", "prodigy-qa", "blueprint-test", "liveness-ci",
                    # Gate 1 F3: a pre-go-live environment is not production, like pre-prod.
                    "pre-go-live", "pregolive", "pre-golive"):
            with self.subTest(env=env):
                self.assertEqual(found(spec(lambda d: alert(d)["firing"].update(environment=env)))[0], [])

    def test_f6_unknown_names_count_as_outside_production_and_are_documented(self):
        # Gate 2 F6: the rule is a deny-list. A name that says nothing counts as outside
        # production, so the docstring must not claim "when in doubt it says production", and
        # SKILL.md must tell the agent to name each environment so it says what it is.
        for env in ("eu-west-1", "primary", "main"):
            with self.subTest(env=env):
                self.assertFalse(slo_check.production(env))
        self.assertNotIn("When in doubt", slo_check.production.__doc__)
        self.assertIn("eu-west-1", slo_check.production.__doc__)
        section = re.search(r"^## 6\. Prove each alert fires\n(.*?)(?=^## )",
                            (SKILL / "SKILL.md").read_text(), re.M | re.S)
        flat = re.sub(r"\s+", " ", section.group(1))
        self.assertIn("`eu-west-1`", flat)
        self.assertIn("counts as outside production", flat)
        self.assertIn("says what it is", flat)

    def test_w12_7_incomplete_or_future_firing_evidence(self):
        changes = {
            "no environment": lambda d: alert(d)["firing"].pop("environment"),
            "no date": lambda d: alert(d)["firing"].pop("date"),
            "bad date": lambda d: alert(d)["firing"].update(date="20 Nov 2026"),
            # Review N1: Python 3.11+ fromisoformat also accepts these; the rule says YYYY-MM-DD.
            "basic date": lambda d: alert(d)["firing"].update(date="20261118"),
            "week date": lambda d: alert(d)["firing"].update(date="2026-W47-1"),
            "future date": lambda d: alert(d)["firing"].update(date="2999-01-01"),
            "no evidence": lambda d: alert(d)["firing"].pop("evidence"),
            "empty evidence": lambda d: alert(d)["firing"].update(evidence=" "),
            "not an object": lambda d: alert(d).update(firing="yes"),
        }
        for name, change in changes.items():
            with self.subTest(name):
                self.assertEqual(rules(spec(change)), ["M7"])


class Indicators(unittest.TestCase):
    def test_w12_8_sli_without_nfr_id(self):
        # W12.8: every SLI cites the NFR ID it measures, in the form NFR-n.
        for change in (lambda d: d["slos"][0]["sli"].pop("nfr"),
                       lambda d: d["slos"][0]["sli"].update(nfr="3"),
                       lambda d: d["slos"][0]["sli"].update(nfr="NFR3"),
                       lambda d: d["slos"][0]["sli"].update(nfr=""),
                       # Review N2: architecting issues NFR-1, NFR-2 ...; never NFR-0 or NFR-03.
                       lambda d: d["slos"][0]["sli"].update(nfr="NFR-0"),
                       lambda d: d["slos"][0]["sli"].update(nfr="NFR-03"),
                       lambda d: d["slos"][0].pop("sli")):
            with self.subTest():
                data = spec(change)
                self.assertEqual(rules(data), ["M2"])
                self.assertIn("SLO-1", found(data)[0][0])

    def test_sli_needs_good_and_valid_events(self):
        self.assertEqual(rules(spec(lambda d: d["slos"][0]["sli"].pop("good"))), ["M2"])
        self.assertEqual(rules(spec(lambda d: d["slos"][0]["sli"].update(valid=""))), ["M2"])


class Example(unittest.TestCase):
    def test_w12_9_example_passes(self):
        # W12.9: the example passes check. It keeps one alert without firing evidence on purpose,
        # so check --release fails on that alert alone.
        problems, status = slo_check.check(EXAMPLE.read_text(), EXAMPLE.parent)
        self.assertEqual(problems, [])
        self.assertTrue(any("not proven" in l for l in status))
        release = slo_check.check(EXAMPLE.read_text(), EXAMPLE.parent, release=True)[0]
        self.assertTrue(release)
        self.assertTrue(all(p.startswith("M6:") for p in release), release)

    def test_w12_9_example_cli_and_alerts(self):
        check = subprocess.run([sys.executable, str(SCRIPT), "check", str(EXAMPLE)], capture_output=True, text=True)
        alerts = subprocess.run([sys.executable, str(SCRIPT), "alerts", str(EXAMPLE)], capture_output=True, text=True)
        self.assertEqual((check.returncode, check.stdout.splitlines()[0]), (0, "pass"))
        self.assertEqual(alerts.returncode, 0)
        self.assertIn("| fast | page | 14.4× | 1 hour | 5 minutes |", alerts.stdout)
        self.assertIn("| slow | page | 6× | 6 hours | 30 minutes |", alerts.stdout)

    def test_w12_9_example_cites_the_architecting_example(self):
        # The example's SLIs cite NFR IDs from architecting's filled design example.
        data = json.loads(EXAMPLE.read_text())
        design = (ROOT / "skills" / "architecting" / "reference" / "design-template.md").read_text()
        for slo in data["slos"]:
            self.assertIn(f"| {slo['sli']['nfr']} |", design)

    def test_n3_example_uses_only_production_measurable_nfrs(self):
        # Review N3: architecting's "From NFR to monitoring" says the Verification cell names the
        # kind. Only an NFR whose cell names production measurement becomes an SLO. In the filled
        # example that is NFR-3 ("Synthetic probe every minute in production"); NFR-1's cell names
        # only a staging load test, so it keeps its test and gets no SLO.
        data = json.loads(EXAMPLE.read_text())
        design = (ROOT / "skills" / "architecting" / "reference" / "design-template.md").read_text()
        example = design[design.index("## Filled example"):]
        self.assertEqual(sorted({slo["sli"]["nfr"] for slo in data["slos"]}), ["NFR-3"])
        for slo in data["slos"]:
            row = re.search(rf"^\| {slo['sli']['nfr']} \|(.*)$", example, re.M).group(1)
            self.assertIn("in production", row.split("|")[-2])


class Overclaims(unittest.TestCase):
    def test_x2_alert_works_in_a_runbook_or_the_file_is_rejected(self):
        self.assertEqual(rules(GOOD, runbook=RUNBOOK + "\nThe alert works.\n"), ["M8"])
        self.assertEqual(rules(spec(lambda d: d.update(service="checkout, alerts work"))), ["M8"])
        # Review M1: the skill's own IDs, other verbs, and "verified" as a claim.
        self.assertEqual(rules(GOOD, runbook=RUNBOOK + "\nALERT-1 works: confirmed in prod.\n"), ["M8"])

    def test_x2_claims_the_checker_rejects(self):
        for phrase in ("The alert works.", "ALERT-1 works", "ALERT-1 works in staging", "alerting works",
                       "the alert now works", "the alert is verified", "alert verified in staging",
                       "alerts tested and working", "Alerts: working", "ALERT-2 has been verified",
                       "We verified the alert in staging", "verified that the alerts fire",
                       "alarms are working", "Alerts all work",
                       # Recheck R3 options: a "Verified:" label and "confirmed working".
                       "Verified: ALERT-1", "alert confirmed working",
                       # Gate 1 F2: a hedge word earlier in the sentence does not hide a flat claim.
                       "No regressions: the alert works.", "Once deployed, the alert works.",
                       "The alert was tested and is working.",
                       # Gate round 2: "nobody doubts that" affirms the claim; it does not negate it.
                       "Nobody on the team doubts that the alert works.",
                       "No one questions that the alert works.",
                       # A condition covers only its own comma clause; a negation stops at : and ;.
                       "When we deployed, the alert works.",
                       "We have not seen errors; the alert works."):
            with self.subTest(phrase=phrase):
                self.assertTrue(slo_check.overclaims(phrase), phrase)

    def test_x2_honest_negations_pass(self):
        for phrase in ("ALERT-1: not verified", "ALERT-2 is not proven", "the alert is not verified",
                       "alerts are not working yet", "we have not verified the alert",
                       "never verified the alert", "unverified alert", "Verify the alert fires in staging",
                       "Alert rules: see the dashboard", "the alert fired in staging on 2026-11-18",
                       # Recheck R3: questions, conditionals, hedges and working hours.
                       "If the alert is working as designed, it stops 5 minutes after the errors stop.",
                       "Is the alert working? Check the dashboard.",
                       "If no alert worked during the drill, file a bug.",
                       "Check whether the alert works in staging before release.",
                       "Routing rules: working hours go to the team queue.",
                       "Escalation rules: working days only.",
                       "When the monitor is working again, close the incident.",
                       "We have not yet verified the alert in staging.",
                       "Nobody has verified the alert yet.",
                       "Until someone has verified the alert in staging, it is not proven.",
                       "Do not assume the alert works.",
                       # Gate round 2 (R2-N1, F9): a negation covers the rest of its sentence part,
                       # across commas and at any distance.
                       "We have not, as of today, verified the alert.",
                       "Do not assume, without a drill, that the alert works.",
                       "We have not yet shown that the alert works.",
                       "Nobody has shown that the alert works.",
                       "No one has confirmed that the alert works.",
                       "We cannot say that the alert works.",
                       "The team hasn't shown that the alert works.",
                       "We have not, despite three separate attempts over the last two weeks in staging, "
                       "verified the alert."):
            with self.subTest(phrase=phrase):
                self.assertEqual(slo_check.overclaims(phrase), [], phrase)

    def test_d12_a_negation_stops_at_and_but_so_yet(self):
        # D-12: a negation covers only its own clause. "and", "but", "so" or "yet" after it,
        # with or without a comma, start a new clause, so a claim after them is a claim.
        # "not only", "not just" and "not merely" are not negations.
        for phrase in ("We did not change the threshold and the alert works.",
                       "We did not change the threshold, and the alert works.",
                       "The deploy didn't break anything, and the alert works.",
                       "It isn't pretty, but the alert works.",
                       "We never touched the route, so the alert works.",
                       "We could not reproduce the bug, so the alert works.",
                       "Nobody paged us yet the alert works.",
                       "Not only the route but also the alert works.",
                       "Not only does the alert work, it pages in 2 minutes.",
                       "Not just the alert works, the route too.",
                       "Not merely the alert works.",
                       "The deploy did not fail and ALERT-1 is verified."):
            with self.subTest(phrase=phrase):
                self.assertTrue(slo_check.overclaims(phrase), phrase)

    def test_d12_honest_negations_still_pass(self):
        # D-12: "not yet" is an adverb, not the joining "yet"; commas alone do not end a negation;
        # "no proof" and "no evidence" negate what follows (chosen: the sentence below is honest;
        # its "and" comes after the claim, so it does not end the negation's reach).
        for phrase in ("We have not yet shown that the alert works.",
                       "We haven't yet verified the alert.",
                       "Nobody has shown that the alert works.",
                       "We have not, as of today, verified the alert.",
                       "Do not assume, without a drill, that the alert works.",
                       "There is no proof yet that the alert works and pages on time.",
                       "We have no evidence that the alert works."):
            with self.subTest(phrase=phrase):
                self.assertEqual(slo_check.overclaims(phrase), [], phrase)

    def test_d12_gate2_f1_no_proof_covers_only_its_that_clause(self):
        # D-12, M5 gate 2 F1: "no proof" or "no evidence" negates only a claim it introduces with
        # "that". A later clause after it is still a claim.
        for phrase in ("No proof needed, the alert works.",
                       "No evidence required: the alert works.",
                       "We need no proof; the alert works.",
                       "No proof needed and the alert works.",
                       "There is no proof that the deploy finished, but the alert works."):
            with self.subTest(phrase=phrase):
                self.assertTrue(slo_check.overclaims(phrase), phrase)
        for phrase in ("There is no proof yet that the alert works and pages on time.",
                       "We have no evidence that the alert works.",
                       "There is no evidence so far that ALERT-1 is verified."):
            with self.subTest(phrase=phrase):
                self.assertEqual(slo_check.overclaims(phrase), [], phrase)

    def test_d12_round2_dash_ends_a_negation(self):
        # D-12, gate 2 F15: " - ", " – " and " — " end a negation's reach, like ":" and ";".
        for phrase in ("No evidence that it broke - the alert works.",
                       "No evidence that it broke \u2013 the alert works.",
                       "No evidence that it broke \u2014 the alert works.",
                       "We did not change the route - the alert works."):
            with self.subTest(phrase=phrase):
                self.assertTrue(slo_check.overclaims(phrase), phrase)
        # A hyphen inside a word is not a dash: the negation still reaches past "pre-release".
        self.assertEqual(slo_check.overclaims("We have not verified ALERT-1 in pre-release."), [])
        self.assertEqual(slo_check.overclaims("We have not, in pre-release, verified the alert."), [])

    def test_d12_round2_no_proof_shape(self):
        # D-12, gate 2 F20 and gate 1 N4. "no proof" or "no evidence" covers a claim only:
        # - after "that", with no comma between "that" and the claim;
        # - after one comma-bounded aside that ends right before "that";
        # - with no "that", when only the claim's subject (an optional "the") comes between.
        claims = (
            "No proof needed, the alert works.",                                    # gate 2 F1
            "No evidence required: the alert works.",
            "We need no proof; the alert works.",
            "No proof needed and the alert works.",
            "There is no proof that the deploy finished, but the alert works.",
            "There is no proof that, the alert works.",                             # F20: comma after that
            "No evidence that the deploy finished, the alert works.",               # F20: comma guard
            "No proof needed, really, the alert works.",                            # aside must end at "that"
            "No proof, really, the alert works.",                                   # aside without "that"
            "There is no proof needed now the alert works.",                        # no-that: subject only
            "There is no proof that the deploy finished and the alert works.",      # join inside the clause
        )
        honest = (
            "We have no evidence the alert works.",                                 # N4: no "that"
            "There is no proof, as of today, that the alert works.",                # N4: one aside
            "There is no proof yet that the alert works and pages on time.",
            "We have no evidence that the alert works.",
            "There is no evidence so far that ALERT-1 is verified.",
            "There is no proof yet, as of today, that the alert works.",
        )
        for phrase in claims:
            with self.subTest(claim=phrase):
                self.assertTrue(slo_check.overclaims(phrase), phrase)
        for phrase in honest:
            with self.subTest(honest=phrase):
                self.assertEqual(slo_check.overclaims(phrase), [], phrase)

    def test_d12_skill_text_documents_the_negation_scope(self):
        text = re.sub(r"\s+", " ", (SKILL / "SKILL.md").read_text())
        for words in ('"and", "but", "so" or "yet"', '"not only"', '"no proof"', "a dash"):
            self.assertIn(words, text)
        doc = re.sub(r"\s+", " ", slo_check.__doc__)
        self.assertIn("and, but, so or yet", doc)
        self.assertIn("not only", doc)

    def test_x2_checker_output_never_overclaims(self):
        data = spec(lambda d: alert(d, 1).pop("firing"))
        with Workspace(data) as ws:
            outputs = [ws.run("check").stdout, ws.run("check", "--release").stdout, ws.run("alerts").stdout]
        for out in outputs:
            for word in ("works", "working", "verified", "secure"):
                self.assertNotIn(word, out.lower())

    def test_r3_honest_runbook_passes_check(self):
        honest = RUNBOOK + ("\n## Escalate\n\nRouting rules: working hours go to the team queue.\n"
                            "Is the alert working? Check the dashboard.\nDo not assume the alert works.\n")
        self.assertEqual(found(GOOD, runbook=honest)[0], [])
        # A claim after an honest line in the same runbook is still caught.
        self.assertEqual(rules(GOOD, runbook=honest + "ALERT-1 works.\n"), ["M8"])

    def test_x2_runbook_template_and_skill_do_not_overclaim(self):
        for path in (SKILL / "templates" / "runbook.md", SKILL / "templates" / "slos.json"):
            self.assertEqual(slo_check.overclaims(path.read_text()), [], path.name)


class Structure(unittest.TestCase):
    def test_invalid_json_and_missing_slos(self):
        with Workspace("{not json") as ws:
            self.assertEqual(sorted({p.split(":")[0] for p in slo_check.check(ws.path.read_text(), ws.base)[0]}), ["M9"])
        self.assertEqual(rules({"service": "x"}), ["M9"])
        self.assertEqual(rules({"service": "x", "slos": []}), ["M9"])

    def test_duplicate_or_missing_ids(self):
        self.assertEqual(rules(spec(lambda d: alert(d, 1).update(id="ALERT-1"))), ["M9"])
        self.assertEqual(rules(spec(lambda d: d["slos"][0].pop("id"))), ["M9"])
        self.assertEqual(rules(spec(lambda d: d["slos"].append(copy.deepcopy(d["slos"][0])))), ["M9"])

    def test_one_line_per_broken_rule(self):
        def two(d):
            d["slos"][0]["target"] = 100.5
            d["slos"][0]["sli"].pop("nfr")
        self.assertEqual(len(found(spec(two))[0]), 2)

    def test_command_line(self):
        with Workspace(GOOD) as ws:
            ok = ws.run("check")
            bad_data = spec(lambda d: d["slos"][0].update(target=101))
            ws.path.write_text(json.dumps(bad_data))
            no = ws.run("check")
        help_ = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        missing = subprocess.run([sys.executable, str(SCRIPT), "check", "/nonexistent/slos.json"],
                                 capture_output=True, text=True)
        self.assertEqual((ok.returncode, ok.stdout.splitlines()[0]), (0, "pass"))
        self.assertEqual(no.returncode, 1)
        self.assertEqual(len(no.stdout.strip().splitlines()), 1)
        self.assertTrue(no.stdout.startswith("M1: SLO-1"))
        self.assertEqual(help_.returncode, 0)
        self.assertIn("slo_check.py", help_.stdout)
        self.assertEqual(missing.returncode, 2)


class SkillText(unittest.TestCase):
    def text(self):
        return (SKILL / "SKILL.md").read_text()

    def test_anatomy_a1_a3_a4_a6_a7(self):
        self.assertEqual(anatomy("monitoring", item=True), [])

    def test_x7_without_a_shell_rule(self):
        rule = re.search(r"^#+ .*Without a shell.*?\n(.*?)(?=^#+ |\Z)", self.text(), re.M | re.S)
        self.assertIsNotNone(rule, "SKILL.md needs a 'Without a shell' rule")
        self.assertIn("slo_check.py", rule.group(1))
        self.assertIn("not run", rule.group(1))

    def test_nfr_ids_and_provisioning_links(self):
        text = self.text()
        self.assertIn("architecting", text)
        self.assertIn("NFR-", text)
        self.assertIn("provisioning", text)
        self.assertIn("not proven", text)

    def test_outside_effects_need_contract_or_exact_plan(self):
        text = re.sub(r"\s+", " ", self.text())
        self.assertIn("pre-authorizes that exact effect", text)
        self.assertIn("owner approves the exact plan", text)

    def test_b1_canary_blue_green_and_shadow_are_production(self):
        text = re.sub(r"\s+", " ", self.text())
        for word in ("canary", "blue-green", "shadow"):
            self.assertIn(word, text)
        self.assertIn("are production", text)

    def test_n3_how_an_slo_relates_to_its_nfr(self):
        text = re.sub(r"\s+", " ", self.text())
        self.assertIn("cites its NFR ID", text)
        self.assertIn("Verification cell", text)
        self.assertNotIn("keyed by its ID", text)

    def test_report_states_a_fire_drills_approval_condition(self):
        # Eval finding 2: the Report section states the drill's approval condition in full.
        report = re.search(r"^## 8\. Report\n(.*?)(?=^## )", self.text(), re.M | re.S)
        self.assertIsNotNone(report, "SKILL.md needs '## 8. Report'")
        flat = re.sub(r"\s+", " ", report.group(1))
        self.assertIn("fire drill", flat)
        self.assertIn("pre-authorizes that exact drill", flat)
        self.assertIn("owner approves its exact plan", flat)

    def test_r4_skill_says_what_to_do_when_the_target_is_too_low(self):
        text = re.sub(r"\s+", " ", self.text())
        self.assertIn("93.05 %", text)
        self.assertIn("owner raises the target", text)
        self.assertIn("changes `PAIRS` for every service", text)

    def test_r5_skill_lines_fit_100_characters(self):
        # Only the frontmatter description and table rows may be longer.
        for number, line in enumerate(self.text().splitlines(), 1):
            if len(line) > 100:
                self.assertTrue(line.startswith(("description:", "|")), f"line {number}: {line[:60]}")

    def test_r1_test_slots_are_not_production_text(self):
        text = re.sub(r"\s+", " ", self.text())
        self.assertIn("staging-green", text)

    def test_m2_check_requires_both_pairs(self):
        text = re.sub(r"\s+", " ", self.text())
        self.assertIn("page alert equal to each pair", text)

    def test_cloud_monitoring_24_hour_lookback(self):
        text = (SKILL / "reference" / "platforms.md").read_text()
        section = re.search(r"^## Cloud Monitoring.*?\n(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
        flat = re.sub(r"\s+", " ", section)
        self.assertIn("24 hours", flat)
        self.assertIn("3 days", flat)

    def test_platforms_reference_cites_docs(self):
        text = (SKILL / "reference" / "platforms.md").read_text()
        for name in ("Azure Monitor", "CloudWatch", "Cloud Monitoring", "Prometheus", "Grafana"):
            with self.subTest(platform=name):
                section = re.search(rf"^## {name}.*?\n(.*?)(?=^## |\Z)", text, re.M | re.S)
                self.assertIsNotNone(section, f"platforms.md needs a '## {name}' section")
                self.assertRegex(section.group(1), r"https://\S+")


if __name__ == "__main__":
    unittest.main()

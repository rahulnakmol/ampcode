"""Tests for skills/steering: flow.py (work item W15) and raid_check.py (work item W16).

Run: python3 -m unittest tests.test_steering -v

Expected values are counted by hand from the fixtures in tests/fixtures/steering/, never taken
from the scripts. flow.json and gh-issues.json encode the same twelve items:

  item  started     finished    cycle time (calendar days, both ends counted)
  #1    2026-10-26  2026-10-28   3
  #2    2026-10-26  2026-11-03   9
  #3    2026-10-27  2026-11-02   7
  #4    2026-10-29  2026-11-04   7
  #5    2026-11-02  2026-11-12  11
  #6    2026-11-10  2026-11-11   2
  #7    2026-11-09  2026-11-20  12
  #8    2026-11-10  2026-11-16   7
  #9    2026-11-16  2026-11-24   9   (this week: not a complete week on 2026-11-25)
  #10   2026-11-01  open            age 25 on 2026-11-25
  #11   2026-11-14  open            age 12
  #12   2026-11-15  open            age 11

Weeks start on Monday. With today 2026-11-25 (a Wednesday) the complete weeks are 2026-10-26,
11-02, 11-09 and 11-16, with 1, 3 (#2, #3, #4), 2 (#5, #6) and 2 (#7, #8) items finished.
"""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "steering"
FLOW = SKILL / "scripts" / "flow.py"
RAID = SKILL / "scripts" / "raid_check.py"
FIXTURES = ROOT / "tests" / "fixtures" / "steering"
TODAY = "2026-11-25"


def run(script, *args, tz=None):
    env = {**os.environ, "TZ": tz} if tz else None
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def utc_today(days=0):
    return (dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=days)).isoformat()


# Etc/GMT+12 is UTC-12 and Etc/GMT-14 is UTC+14. At any hour, one of them has a local date that
# differs from the UTC date, so a script that used the local date would fail one of the N4 tests.
ZONES = ("Etc/GMT+12", "Etc/GMT-14")


def flow_json(tmp, items, name="flow.json"):
    path = Path(tmp) / name
    path.write_text(json.dumps({"contract": "flow/v1", "items": items}))
    return str(path)


class FlowMetrics(unittest.TestCase):
    def metrics(self, path, today=TODAY):
        code, out = run(FLOW, "metrics", path, "--today", today, "--json")
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def test_w15_1_weekly_throughput_equals_hand_counts(self):
        found = self.metrics(str(FIXTURES / "flow.json"))
        self.assertEqual(found["throughput"], [
            {"week": "2026-10-26", "finished": 1},
            {"week": "2026-11-02", "finished": 3},
            {"week": "2026-11-09", "finished": 2},
            {"week": "2026-11-16", "finished": 2},
        ])
        self.assertEqual(found["this_week"], {"week": "2026-11-23", "finished": 1})
        self.assertEqual((found["items"], found["finished"], found["wip"]), (12, 9, 3))

    def test_w15_1_a_week_with_no_finish_counts_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [
                {"id": "a", "started": "2026-11-02", "finished": "2026-11-03"},
                {"id": "b", "started": "2026-11-03", "finished": "2026-11-18"},
            ])
            found = self.metrics(path)
        self.assertEqual([w["finished"] for w in found["throughput"]], [1, 0, 1])

    def test_w15_2_cycle_time_percentiles_nearest_rank(self):
        # Sorted: 2 3 7 7 7 9 9 11 12 (n = 9). 50th: rank ceil(4.5) = 5 -> 7. 85th: rank ceil(7.65) = 8 -> 11.
        found = self.metrics(str(FIXTURES / "flow.json"))
        self.assertEqual(found["cycle_time"], {"count": 9, "p50": 7, "p85": 11})

    def test_w15_2_nearest_rank_on_an_even_count(self):
        # Cycle times 1 2 3 4 (n = 4). 50th: rank 2 -> 2. 85th: rank ceil(3.4) = 4 -> 4.
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [
                {"id": str(days), "started": "2026-11-02", "finished": f"2026-11-0{1 + days}"}
                for days in (1, 2, 3, 4)
            ])
            found = self.metrics(path)
        self.assertEqual(found["cycle_time"], {"count": 4, "p50": 2, "p85": 4})

    def test_w15_3_open_items_older_than_p85_are_aging(self):
        # 85th percentile is 11. #10 (25) and #11 (12) are older; #12 (11) is not.
        found = self.metrics(str(FIXTURES / "flow.json"))
        self.assertEqual(found["aging"], [{"id": "#10", "age": 25}, {"id": "#11", "age": 12}])

    def test_w15_3_text_report_lists_aging_items(self):
        code, out = run(FLOW, "metrics", str(FIXTURES / "flow.json"), "--today", TODAY)
        self.assertEqual(code, 0, out)
        self.assertIn("#10", out)
        self.assertIn("#11", out)
        self.assertNotIn("#12 ", out)

    def test_w15_6_gh_issue_list_gives_the_same_metrics(self):
        neutral = self.metrics(str(FIXTURES / "flow.json"))
        github = self.metrics(str(FIXTURES / "gh-issues.json"))
        self.assertEqual(github, neutral)

    def test_w15_6_gh_issue_list_gives_the_same_forecast(self):
        args = ("--today", TODAY, "--remaining", "10", "--seed", "3", "--json")
        neutral = run(FLOW, "forecast", str(FIXTURES / "flow.json"), *args)
        github = run(FLOW, "forecast", str(FIXTURES / "gh-issues.json"), *args)
        self.assertEqual(neutral[0], 0, neutral[1])
        self.assertEqual(github, neutral)

    def test_w15_7_finish_before_start_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [
                {"id": "ok", "started": "2026-11-02", "finished": "2026-11-03"},
                {"id": "S-4", "started": "2026-11-10", "finished": "2026-11-09"},
            ])
            code, out = run(FLOW, "metrics", path, "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("S-4", out)
        self.assertIn("before", out)

    def test_w15_7_gh_closed_before_created_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gh.json"
            path.write_text(json.dumps([
                {"number": 7, "createdAt": "2026-11-10T09:00:00Z", "closedAt": "2026-11-09T09:00:00Z"}]))
            code, out = run(FLOW, "metrics", str(path), "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("#7", out)

    def test_bad_input_fails_one_line_per_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [
                {"id": "a", "started": "2026-13-01"},
                {"id": "b", "finshed": "2026-11-01", "started": "2026-11-01"},
                {"id": "a", "started": "2026-11-01"},
                {"id": "c", "started": "2026-11-30"},
            ])
            code, out = run(FLOW, "metrics", path, "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertEqual(len(out.strip().splitlines()), 4, out)

    def test_n1_history_starts_at_the_first_start_not_the_first_finish(self):
        # First start in week 2026-10-26, first finish in week 2026-11-09: weeks 10-26 to 11-16.
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [
                {"id": "a", "started": "2026-10-26"},
                {"id": "b", "started": "2026-11-09", "finished": "2026-11-10"},
            ])
            found = self.metrics(path)
        self.assertEqual([w["finished"] for w in found["throughput"]], [0, 0, 1, 0])
        self.assertEqual(found["throughput"][0]["week"], "2026-10-26")

    def gh_with_reasons(self, tmp):
        """The gh fixture with stateReason, plus four closures that are not finished work."""
        issues = json.loads((FIXTURES / "gh-issues.json").read_text())
        for issue in issues:
            issue["stateReason"] = "COMPLETED" if issue["closedAt"] else ""
        issues[0]["stateReason"] = "REOPENED"  # #12: reopened and open again
        issues += [
            {"number": 20 + n, "createdAt": "2026-11-17T09:00:00Z", "closedAt": "2026-11-17T10:00:00Z",
             "stateReason": reason}
            for n, reason in enumerate(("NOT_PLANNED", "NOT_PLANNED", "DUPLICATE", ""))
        ]
        path = Path(tmp) / "gh.json"
        path.write_text(json.dumps(issues))
        return str(path)

    def test_m3_closures_that_are_not_completed_are_removed(self):
        # The four extra issues are neither finished nor open; every other figure stays as before.
        expected = self.metrics(str(FIXTURES / "flow.json"))
        self.assertEqual(expected["removed"], 0)
        expected["removed"] = 4
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.metrics(self.gh_with_reasons(tmp)), expected)

    def test_m3_removed_closures_do_not_change_the_forecast(self):
        args = ("--today", TODAY, "--remaining", "24", "--seed", "42", "--json")
        plain = json.loads(run(FLOW, "forecast", str(FIXTURES / "flow.json"), *args)[1])
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run(FLOW, "forecast", self.gh_with_reasons(tmp), *args)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out), plain)

    def test_m3_help_and_hint_give_the_full_export_command(self):
        code, out = run(FLOW, "--help")
        self.assertEqual(code, 0)
        for text in ("--limit 1000", 'label:"type:story","type:bug"', "stateReason", "COMPLETED"):
            self.assertIn(text, out)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gh.json"
            path.write_text(json.dumps([{"createdAt": "2026-11-10T09:00:00Z"}]))
            code, out = run(FLOW, "metrics", str(path), "--today", TODAY)
        self.assertEqual(code, 1)
        self.assertIn("--limit 1000", out)

    def test_r4_an_export_of_exactly_1000_issues_warns(self):
        # gh's search returns at most 1000 issues, so exactly 1000 may be a cut-short export.
        def issues(n):
            return [{"number": i, "createdAt": "2026-11-02T09:00:00Z", "closedAt": "2026-11-03T09:00:00Z"}
                    for i in range(1, n + 1)]
        with tempfile.TemporaryDirectory() as tmp:
            for n, warns in ((1000, True), (999, False)):
                with self.subTest(rows=n):
                    path = Path(tmp) / f"gh{n}.json"
                    path.write_text(json.dumps(issues(n)))
                    proc = subprocess.run([sys.executable, str(FLOW), "metrics", str(path), "--today", TODAY,
                                           "--json"], capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(json.loads(proc.stdout)["finished"], n)  # JSON stays clean on stdout
                    self.assertEqual("1000" in proc.stderr and "cut short" in proc.stderr, warns, proc.stderr)

    def test_n4_default_today_is_the_utc_date(self):
        # An item finished on today's UTC date is not "after --today" in any local time zone.
        with tempfile.TemporaryDirectory() as tmp:
            path = flow_json(tmp, [{"id": "a", "started": utc_today(-3), "finished": utc_today()}])
            for zone in ZONES:
                with self.subTest(zone=zone):
                    code, out = run(FLOW, "metrics", path, "--json", tz=zone)
                    self.assertEqual(code, 0, out)
                    self.assertEqual(json.loads(out)["today"], utc_today())

    def test_help_exits_zero(self):
        self.assertEqual(run(FLOW, "--help")[0], 0)


class FlowForecast(unittest.TestCase):
    def constant(self, tmp):
        """Four complete weeks, five items finished on each Tuesday; today is Wednesday 2026-11-25."""
        items = []
        for week, tuesday in enumerate(("2026-10-27", "2026-11-03", "2026-11-10", "2026-11-17")):
            items += [{"id": f"w{week}-{n}", "started": tuesday, "finished": tuesday} for n in range(5)]
        return flow_json(tmp, items)

    def forecast(self, path, *extra):
        code, out = run(FLOW, "forecast", path, "--today", TODAY, "--json", *extra)
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def test_w15_4_constant_history_gives_four_weeks_at_every_percentile(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = self.forecast(self.constant(tmp), "--remaining", "20", "--seed", "1")
        self.assertEqual(found["weeks"], {"p50": 4, "p85": 4, "p95": 4})
        # 2026-11-25 plus 4 weeks.
        self.assertEqual(found["dates"], {"p50": "2026-12-23", "p85": "2026-12-23", "p95": "2026-12-23"})
        self.assertEqual((found["remaining"], found["history_weeks"]), (20, 4))

    def test_w15_4_a_seed_repeats_the_result(self):
        path = str(FIXTURES / "flow.json")
        first = run(FLOW, "forecast", path, "--today", TODAY, "--remaining", "15", "--seed", "42")
        second = run(FLOW, "forecast", path, "--today", TODAY, "--remaining", "15", "--seed", "42")
        self.assertEqual(first[0], 0, first[1])
        self.assertEqual(first, second)
        self.assertIn("42", first[1])

    def test_w15_4_forecast_stays_within_the_history_bounds(self):
        # Weekly throughput is 1 to 3, so 12 items take 4 to 12 weeks in every run.
        found = self.forecast(str(FIXTURES / "flow.json"), "--remaining", "12", "--seed", "5")
        weeks = found["weeks"]
        self.assertTrue(4 <= weeks["p50"] <= weeks["p85"] <= weeks["p95"] <= 12, weeks)

    def test_w15_4_due_date_gives_the_chance_and_the_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.constant(tmp)
            on_time = self.forecast(path, "--remaining", "20", "--seed", "1", "--due", "2026-12-23")
            late = self.forecast(path, "--remaining", "20", "--seed", "1", "--due", "2026-12-22")
        self.assertEqual((on_time["chance_by_due"], on_time["p85_by_due"]), (100, True))
        self.assertEqual((late["chance_by_due"], late["p85_by_due"]), (0, False))

    def spread(self, tmp):
        """Ten items start 2026-11-09 and finish 2026-11-17: weekly history [0, 10]."""
        return flow_json(tmp, [{"id": str(n), "started": "2026-11-09", "finished": "2026-11-17"}
                               for n in range(10)])

    def test_b1_asymmetric_history_gives_the_hand_derived_spread(self):
        # Each run ends at the first week that draws 10, so P(weeks <= k) = 1 - 0.5**k:
        # 0.75, 0.875, 0.9375, 0.96875 for k = 2..5. Nearest rank: 85th -> 3, 95th -> 5.
        # A forecast from the mean (5 per week) would give 2 at every percentile.
        # The 50th sits exactly on the 0.5 boundary, so it is not asserted.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.spread(tmp)
            for seed in ("1", "2", "3", "42"):
                with self.subTest(seed=seed):
                    found = self.forecast(path, "--remaining", "10", "--seed", seed)
                    self.assertEqual((found["weeks"]["p85"], found["weeks"]["p95"]), (3, 5))
                    self.assertEqual(found["history_weeks"], 2)

    def test_b1_the_seed_decides_the_draws(self):
        # With one run, the result is one geometric draw (1 week with chance 0.5, 2 with 0.25, ...).
        # The same seed repeats it; twenty seeds give more than one value unless the seed is ignored.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.spread(tmp)
            seen = set()
            for seed in range(1, 21):
                args = ("--remaining", "10", "--runs", "1", "--seed", str(seed))
                first, second = self.forecast(path, *args), self.forecast(path, *args)
                self.assertEqual(first, second)
                seen.add(first["weeks"]["p50"])
        self.assertGreater(len(seen), 1)

    def test_n1_weeks_uses_only_the_last_weeks(self):
        # Weekly history 1, 1, 1, 5. --weeks 1 draws only the 5: 20 items take 4 weeks in every run.
        # Without it, 4 weeks needs four draws of 5 (chance 1/256), so the 50th percentile is above 4.
        with tempfile.TemporaryDirectory() as tmp:
            items = [{"id": f"x{n}", "started": day, "finished": day}
                     for n, day in enumerate(("2026-10-27", "2026-11-03", "2026-11-10"))]
            items += [{"id": f"y{n}", "started": "2026-11-17", "finished": "2026-11-17"} for n in range(5)]
            path = flow_json(tmp, items)
            last = self.forecast(path, "--remaining", "20", "--seed", "1", "--weeks", "1")
            whole = self.forecast(path, "--remaining", "20", "--seed", "1")
        self.assertEqual((last["weeks"], last["history_weeks"]), ({"p50": 4, "p85": 4, "p95": 4}, 1))
        self.assertEqual(whole["history_weeks"], 4)
        self.assertGreater(whole["weeks"]["p50"], 4)

    def test_n1_an_unseeded_run_prints_a_seed_that_repeats_it(self):
        path = str(FIXTURES / "flow.json")
        first = self.forecast(path, "--remaining", "15")
        self.assertIsInstance(first["seed"], int)
        self.assertEqual(self.forecast(path, "--remaining", "15", "--seed", str(first["seed"])), first)

    def test_remaining_defaults_to_open_items(self):
        found = self.forecast(str(FIXTURES / "flow.json"), "--seed", "1")
        self.assertEqual(found["remaining"], 3)

    def test_w15_5_empty_history_refuses_to_forecast(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = flow_json(tmp, [], "empty.json")
            only_open = flow_json(tmp, [{"id": "x", "started": "2026-11-02"}], "open.json")
            this_week = flow_json(tmp, [{"id": "y", "started": "2026-11-23", "finished": "2026-11-24"}], "week.json")
            gh = Path(tmp) / "gh.json"
            gh.write_text("[]")
            for path in (empty, only_open, this_week, str(gh)):
                with self.subTest(path=Path(path).name):
                    code, out = run(FLOW, "forecast", path, "--today", TODAY, "--remaining", "5", "--seed", "1")
                    self.assertEqual(code, 1, out)
                    self.assertIn("forecast", out.lower())
                    self.assertNotIn("p85", out.lower())

    def test_w15_5_empty_history_still_reports_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run(FLOW, "metrics", flow_json(tmp, []), "--today", TODAY, "--json")
        self.assertEqual(code, 0, out)
        found = json.loads(out)
        self.assertEqual((found["items"], found["wip"], found["cycle_time"]["count"]), (0, 0, 0))


GOOD_RAID = """# Risks, issues and decisions: pilot UK01

Week of: 2026-11-23

## Risks

| ID | Risk | Owner | Date | Response | State |
| --- | --- | --- | --- | --- | --- |
| R1 | The bank's test window may close before the pilot is ready | Elena Petrova | 2026-12-04 | Ask the bank for a second window | open |

## Issues

| ID | Issue | Owner | Date | Action | State |
| --- | --- | --- | --- | --- | --- |
| I1 | The payment file fails the bank's format check | Sam Okafor | 2026-11-27 | Fix the header record | open |

## Decisions

| ID | Decision needed | Decider | Deadline | Default | Outcome |
| --- | --- | --- | --- | --- | --- |
| D1 | Move the pilot from 4 December to 18 December? | Priya Raman | 2026-11-20 | Keep 4 December and the full scope; escalate to Rahul | default applied: kept 4 December and the scope; escalated to Rahul (2026-11-21) |
| D2 | Add a second tester? | Rahul | 2026-11-30 | No second tester | open |

## Guardrails

| ID | Guardrail | Limit | Value | State | Action taken |
| --- | --- | --- | --- | --- | --- |
| G1 | Work in progress | at most 4 | 5 | breached | No new starts until work in progress is 4; told Rahul on 2026-11-24 |
| G2 | Escaped defects per week | at most 2 | 0 | ok | - |
"""

GOOD_STATUS = """# Status: pilot UK01, week of 2026-11-23

## Status

Overall: amber. The pilot date holds; work in progress is above its limit.
Flow: 2 items finished last week; cycle time 7 days (50th) and 11 days (85th).
Forecast: 85% chance to finish the 6 remaining items by 2026-12-18 (seed 42).
Risks and issues: 1 open risk, 1 open issue; 1 guardrail breached, action taken.
Decision needed: D2, a second tester, by 2026-11-30; default no second tester.
"""


class RaidCheck(unittest.TestCase):
    def check(self, text, name="raid.md", today="2026-11-25"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_text(text)
            return run(RAID, str(path), "--today", today)

    def fails(self, text, *words, name="raid.md"):
        code, out = self.check(text, name)
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        for word in words:
            self.assertIn(word, out)
        return out

    def test_good_log_and_status_pass(self):
        self.assertEqual(self.check(GOOD_RAID), (0, "pass\n"))
        self.assertEqual(self.check(GOOD_STATUS, "status.md"), (0, "pass\n"))

    def test_w16_1_risk_without_owner(self):
        self.fails(GOOD_RAID.replace("| Elena Petrova |", "|  |"), "R1", "owner")

    def test_w16_1_risk_without_date(self):
        self.fails(GOOD_RAID.replace("| 2026-12-04 |", "| soon |"), "R1", "date")

    def test_w16_1_issue_without_owner_or_date(self):
        self.fails(GOOD_RAID.replace("| Sam Okafor |", "| TBD |"), "I1", "owner")
        self.fails(GOOD_RAID.replace("| 2026-11-27 |", "| - |"), "I1", "date")

    def test_w16_2_decision_without_deadline(self):
        self.fails(GOOD_RAID.replace("| 2026-11-30 |", "|  |"), "D2", "deadline")

    def test_w16_2_decision_without_default(self):
        self.fails(GOOD_RAID.replace("| No second tester |", "| - |"), "D2", "default")

    def test_w16_3_passed_deadline_without_default_applied_or_decision(self):
        for outcome in ("| open |", "| open: waiting for Rahul |"):  # gate N2: "open: ..." is still open
            with self.subTest(outcome=outcome):
                text = GOOD_RAID.replace(
                    "| default applied: kept 4 December and the scope; escalated to Rahul (2026-11-21) |", outcome)
                self.fails(text, "D1", "default applied")

    def test_w16_3_passed_deadline_with_a_decision_passes(self):
        text = GOOD_RAID.replace(
            "| default applied: kept 4 December and the scope; escalated to Rahul (2026-11-21) |",
            "| decided: move to 18 December (Rahul, 2026-11-19) |")
        self.assertEqual(self.check(text), (0, "pass\n"))

    def test_w16_3_deadline_today_is_not_passed(self):
        self.assertEqual(self.check(GOOD_RAID, today="2026-11-30"), (0, "pass\n"))
        code, out = self.check(GOOD_RAID, today="2026-12-01")
        self.assertEqual(code, 1, out)
        self.assertIn("D2", out)

    def test_w16_4_breached_guardrail_without_action(self):
        text = GOOD_RAID.replace(
            "| No new starts until work in progress is 4; told Rahul on 2026-11-24 |", "| - |")
        self.fails(text, "G1", "action")

    def test_w16_5_status_longer_than_five_lines(self):
        self.fails(GOOD_STATUS + "Next week: start the bank tests.\n", "status", "5", name="status.md")

    def test_w16_5_blank_lines_do_not_count(self):
        text = GOOD_STATUS.replace("Flow:", "\nFlow:")
        self.assertEqual(self.check(text, "status.md"), (0, "pass\n"))

    def test_w16_6_the_templates_pass(self):
        for name in ("raid.md", "status.md"):
            with self.subTest(template=name):
                code, out = run(RAID, str(SKILL / "templates" / name), "--today", "2026-11-25")
                self.assertEqual((code, out), (0, "pass\n"))

    def test_one_line_per_broken_rule(self):
        text = GOOD_RAID.replace("| Elena Petrova |", "|  |").replace("| No second tester |", "|  |")
        code, out = self.check(text)
        self.assertEqual(code, 1)
        self.assertEqual(len(out.strip().splitlines()), 2, out)

    def test_a_file_with_nothing_to_check_fails(self):
        self.fails("# Notes\n\nNothing here.\n", "nothing to check")

    def test_help_exits_zero(self):
        self.assertEqual(run(RAID, "--help")[0], 0)

    # M1: rows the checker would not read must fail, not pass unread.
    BROKEN_D2 = GOOD_RAID.replace("| No second tester | open |", "|  | open |")

    def test_m1_unknown_section_heading_fails(self):
        out = self.fails(GOOD_RAID.replace("## Decisions", "## Decision requests"), "format")
        self.assertIn("Decision requests", out)

    def test_m1_table_under_a_lower_heading_fails(self):
        code, out = self.check(self.BROKEN_D2.replace("## Decisions", "### Decisions"))
        self.assertEqual(code, 1, out)
        self.assertIn("format", out)

    def test_m1_repeated_section_fails(self):
        extra = ("\n## Decisions\n\n| ID | Decision needed | Decider | Deadline | Default | Outcome |\n"
                 "| --- | --- | --- | --- | --- | --- |\n| D3 | Hire a contractor? |  | 2026-11-01 |  | open |\n")
        code, out = self.check(GOOD_RAID + extra)
        self.assertEqual(code, 1, out)
        self.assertIn("more than once", out)

    def test_m1_table_line_after_a_blank_line_fails(self):
        row = "| R1 | The bank's test window may close before the pilot is ready | Elena Petrova | 2026-12-04 | Ask the bank for a second window | open |\n"
        text = GOOD_RAID.replace(row, row + "\n| R2 | Supplier may go bust | | soon | - | open |\n")
        out = self.fails(text, "format")
        self.assertIn("outside", out)

    # N2: outcomes other than "open", and deadlines that are not dates.
    def test_n2_outcome_must_be_open_default_applied_or_decided(self):
        text = GOOD_RAID.replace("| No second tester | open |", "| No second tester | waiting for Rahul |")
        self.fails(text, "D2", "format")

    def test_n2_bare_decided_or_default_applied_fails(self):
        current = "| default applied: kept 4 December and the scope; escalated to Rahul (2026-11-21) |"
        for bare in ("| decided |", "| default applied: |", "| decided:  |"):
            with self.subTest(outcome=bare):
                self.fails(GOOD_RAID.replace(current, bare), "D1")

    def test_n2_deadline_must_be_a_date(self):
        self.fails(GOOD_RAID.replace("| 2026-11-30 |", "| next Friday |"), "D2", "deadline")

    def test_eval_proposed_owner_date_and_deadline_pass(self):
        # Eval finding 3: a value the agent chose carries "(proposed)" and still passes.
        text = (GOOD_RAID.replace("| Elena Petrova | 2026-12-04 |", "| Rahul (proposed) | 2026-12-04 (proposed) |")
                .replace("| 2026-11-30 |", "| 2026-11-30 (proposed) |"))
        self.assertEqual(self.check(text), (0, "pass\n"))
        code, out = self.check(text, today="2026-12-01")  # a proposed deadline still passes by date
        self.assertEqual(code, 1, out)
        self.assertIn("D2", out)
        self.fails(GOOD_RAID.replace("| 2026-11-30 |", "| 2026-11-30 (maybe) |"), "D2", "deadline")

    # N3: closed rows keep their owner and date.
    def test_n3_closed_risk_without_owner_fails(self):
        text = GOOD_RAID.replace("| Elena Petrova |", "|  |").replace(
            "| Ask the bank for a second window | open |", "| Ask the bank for a second window | closed |")
        self.fails(text, "R1", "owner")

    # N4: the default --today is the UTC date in every time zone.
    def test_n4_default_today_is_the_utc_date(self):
        log = ("## Decisions\n\n| ID | Decision needed | Decider | Deadline | Default | Outcome |\n"
               "| --- | --- | --- | --- | --- | --- |\n| D1 | Add a tester? | Rahul | {deadline} | No | open |\n")
        with tempfile.TemporaryDirectory() as tmp:
            due_today, passed = Path(tmp) / "today.md", Path(tmp) / "passed.md"
            due_today.write_text(log.format(deadline=utc_today()))
            passed.write_text(log.format(deadline=utc_today(-1)))
            for zone in ZONES:
                with self.subTest(zone=zone):
                    self.assertEqual(run(RAID, str(due_today), tz=zone), (0, "pass\n"))
                    code, out = run(RAID, str(passed), tz=zone)
                    self.assertEqual(code, 1, out)
                    self.assertIn("deadline", out)

    # N5: no "on track", "verified" or "signed off" in the status without evidence on the line.
    def test_n5_overclaims_without_evidence_fail(self):
        for line in ("Overall: green, on track.", "Flow: verified.", "Sign-off: F2 signed off.",
                     "Sign-off: F2 signed.",
                     "Overall: green, on-track.",                                  # R2: hyphen
                     "Overall: not blocked, on track.",                            # negation elsewhere on the line
                     "Sign-off: F2 signed by the bank by email on 2026-11-25.",    # R2: a date is not a source
                     "Sign-off: Priya approved F1 and the pilot plan.",            # gate N1: "approved"
                     "Sign-off: F2 signed off by the bank; Elena will /approve later."):  # gate N1: bare /approve
            with self.subTest(line=line):
                text = GOOD_STATUS.replace(
                    "Overall: amber. The pilot date holds; work in progress is above its limit.", line)
                self.fails(text, "overclaim", name="status.md")

    def test_n5_evidence_or_a_negation_passes(self):
        for line in ("Overall: on track; 85th percentile date 2026-12-16 is before the 2026-12-18 due date.",
                     "Sign-off: F2 signed off by Elena Petrova on 2026-11-24 (tracker /approve).",
                     "Sign-off: F2 signed off, https://github.com/acme/pilot/issues/12#issuecomment-123.",
                     "Sign-off: Priya approved F1 with /approve on 2026-11-24.",
                     "Sign-off: F1 not approved yet.",
                     "Sign-off: F2 signed off by Elena Petrova, written: ledger row of 2026-11-24.",
                     "Sign-off: F2 signed by the bank by email on 2026-11-25; claimed, not in the tracker.",
                     "Overall: not on-track; the forecast misses M1.",
                     "Sign-off: F2 not signed off yet; the bank's email is claimed, not in the tracker.",
                     "Overall: not on track; the forecast misses M1.",
                     "Flow: figures not verified against the tracker."):
            with self.subTest(line=line):
                text = GOOD_STATUS.replace(
                    "Overall: amber. The pilot date holds; work in progress is above its limit.", line)
                self.assertEqual(self.check(text, "status.md"), (0, "pass\n"))

    def test_gate_n3_full_pack_is_checked_for_overclaims(self):
        pack = "\n## Full pack\n\n### Flow\n\nOverall we are on track and verified.\n"
        self.fails(GOOD_STATUS + pack, "overclaim", "Full pack", name="status.md")
        honest = ("\n## Full pack\n\n### Flow\n\n" + "Not on track: the 85th percentile date is 2027-03-03.\n" * 8)
        self.assertEqual(self.check(GOOD_STATUS + honest, "status.md"), (0, "pass\n"))  # no line limit

    # D-15: the full-pack overclaim check reads clauses, the date of a /approve comment, and prose only.
    def pack(self, *lines):
        return GOOD_STATUS + "\n## Full pack\n\n" + "\n".join(lines) + "\n"

    def pack_passes(self, *lines):
        self.assertEqual(self.check(self.pack(*lines), "status.md"), (0, "pass\n"))

    def pack_fails(self, *lines):
        return self.fails(self.pack(*lines), "overclaim", "Full pack", name="status.md")

    def test_d15_honest_refusals_pass(self):
        for line in ("Do not mark F2 as approved.",
                     "Never mark F2 as signed off without its /approve comment.",
                     "Rule: do not report F2 as on track until the forecast says so.",
                     "You asked me to mark F2 as signed off in GitHub. I did not.",
                     "Rahul asked me to mark F2 as signed off in GitHub. I did not, for these reasons:",
                     "You asked me to record F2 as approved; I have not.",
                     "Rahul wants me to mark F2 as approved. I will not, because the charter says always ask."):
            with self.subTest(line=line):
                self.pack_passes(line)

    def test_d15_requests_without_a_refusal_and_other_clauses_still_fail(self):
        for line in ("You asked me to mark F2 as signed off in GitHub. I did.",
                     "Rahul asked me to mark F2 as approved.",
                     "I did not wait: F2 is signed off.",                  # the refusal comes first
                     "I did not object. Rahul asked me to mark F2 as signed off.",  # a refusal must follow the request
                     "Do not worry. F2 is approved.",                      # the negation covers its own clause only
                     "Overall: not blocked, on track."):                   # a plain "not" does not cover the clause
            with self.subTest(line=line):
                self.pack_fails(line)

    def test_d15_a_date_counts_only_as_the_date_of_the_approve_comment(self):
        for line in ("F2 signed off: Elena will /approve by 2026-12-01.",
                     "By 2026-12-01 Elena will /approve F2; it is signed off.",
                     "F2 approved; Elena will /approve later, see the plan of 2026-11-20."):
            with self.subTest(line=line):
                self.pack_fails(line)
        for line in ("F2 signed off by Elena Petrova, /approve on 2026-11-24.",
                     "F2 signed off by Elena Petrova, /approve 2026-11-24.",
                     "F2 signed off by Elena Petrova on 2026-11-24 (tracker /approve).",
                     "F2 approved by Elena Petrova: https://github.com/acme/pilot/issues/12#issuecomment-99 (2026-12-01)."):
            with self.subTest(line=line):
                self.pack_passes(line)

    def test_d15_structure_is_not_read_as_prose(self):
        self.pack_passes(
            "### Are we on track?",
            "",
            "| Feature | Approved by | Signed off on | Source |",
            "| --- | --- | --- | --- |",
            "| F1 | Priya Raman | 2026-11-24 | /approve on 2026-11-24 |",
            "",
            "```",
            "F1  approved  [priya-r current]  signed off",
            "verified: on track",
            "```",
        )

    def test_d15_a_table_body_row_without_a_source_still_fails(self):
        self.pack_fails(
            "| Feature | Approved by | Source |",
            "| --- | --- | --- |",
            "| F2 | signed off by Elena Petrova | email |",
        )

    def test_d15_approved_with_a_date_but_no_source_fails(self):
        for line in ("F1 Approved by Priya on 2026-11-24 (email).", "Priya approved F1 on 2026-11-24."):
            with self.subTest(line=line):
                self.pack_fails(line)
                status = GOOD_STATUS.replace(
                    "Overall: amber. The pilot date holds; work in progress is above its limit.", line)
                self.fails(status, "overclaim", "Status", name="status.md")

    DECISIONS = ("\n## {title}\n\n| ID | Decision needed | Decider | Deadline | Default | Outcome |\n"
                 "| --- | --- | --- | --- | --- | --- |\n| D3 | Hire a contractor? |  | 2026-11-01 |  | open |\n")

    def test_r1_status_file_with_a_renamed_decisions_section_fails(self):
        out = self.fails(GOOD_STATUS + self.DECISIONS.format(title="Decision requests"), "format",
                         name="status.md")
        self.assertIn("Decision requests", out)

    def test_r1_status_and_log_sections_in_one_file_fail(self):
        code, out = self.check(GOOD_STATUS + self.DECISIONS.format(title="Decisions"), "status.md")
        self.assertEqual(code, 1, out)
        self.assertIn("separate files", out)

    def test_r1_status_file_keeps_its_full_pack(self):
        text = GOOD_STATUS + "\n## Full pack\n\n| Milestone | Due |\n| --- | --- |\n| M1 | 2026-12-18 |\n"
        self.assertEqual(self.check(text, "status.md"), (0, "pass\n"))

    def test_repeated_status_section_fails(self):
        self.fails(GOOD_STATUS + "\n## Status\n\nOverall: green.\n", "more than once", name="status.md")

    def test_r5_guardrails_as_a_list_above_the_risks_pass_and_as_a_table_fail(self):
        listed = GOOD_RAID.replace("Week of: 2026-11-23\n", "Week of: 2026-11-23\n\n"
                                   "Guardrails set by the owner:\n\n- Work in progress at most 4.\n")
        self.assertEqual(self.check(listed), (0, "pass\n"))
        tabled = GOOD_RAID.replace("Week of: 2026-11-23\n", "Week of: 2026-11-23\n\n"
                                   "| Guardrail | Limit |\n| --- | --- |\n| Work in progress | at most 4 |\n")
        self.fails(tabled, "format", "outside")


class SkillText(unittest.TestCase):
    def text(self):
        return (SKILL / "SKILL.md").read_text()

    def test_outside_effects_follow_the_contract(self):
        for phrase in ("pre-authorizes", "exact plan", "syncing", "grooming", "missioning",
                       "flow.py", "raid_check.py", "templates/raid.md", "templates/status.md"):
            self.assertIn(phrase, self.text())

    def test_m1_skill_names_the_checked_headings(self):
        for heading in ("## Risks", "## Issues", "## Decisions", "## Guardrails", "## Status"):
            self.assertIn(f"`{heading}`", self.text())

    def test_m2_outside_sign_off_takes_a_real_route(self):
        text = self.text()
        for phrase in ("`/approve`", "`pull`", "record-signoff", "written:",
                       "Never post `/approve` for someone else"):
            self.assertIn(phrase, text)
        readme = (ROOT / "evals" / "steering" / "README.md").read_text()
        self.assertIn("/approve", readme)
        self.assertNotIn("through `syncing`'s plan", text + readme)

    def test_m3_export_is_stories_and_bugs_with_state_reason(self):
        text = self.text()
        for phrase in ('label:"type:story","type:bug"', "stateReason", "--limit 1000", "COMPLETED"):
            self.assertIn(phrase, text)

    def test_m4_defaults_are_safe_and_not_approvals(self):
        text = self.text()
        for phrase in ("lets the agent do alone", "keep the date and the scope",
                       "decision trail", "not the gate's approval", "Silence is never an approval"):
            self.assertIn(phrase, text)
        raid = (SKILL / "templates" / "raid.md").read_text()
        self.assertNotIn("cut", raid.lower().split("## decisions")[1].split("## guardrails")[0])

    def test_r3_record_signoff_needs_approval_of_the_exact_command(self):
        text = self.text()
        self.assertIn("the exact command", text)
        self.assertIn("item, approver and source", text)

    def test_r5_applied_default_trail_row_names_the_agent(self):
        text = self.text()
        self.assertIn('"Agent (default applied)"', text)
        self.assertIn("as a list above `## Risks`", text)
        readme = (ROOT / "evals" / "steering" / "README.md").read_text()
        self.assertIn("proposes the decision trail row", readme)
        self.assertNotIn("names the decision trail entry", readme)

    def test_eval_trail_row_without_a_ledger_is_a_proposal(self):
        # Eval finding 2: with no mission.md, the row goes into the pack as a proposal.
        text = self.text()
        for phrase in ("no `mission.md`", "as a proposal in the pack", '"I propose"', 'never "I recorded"'):
            self.assertIn(phrase, text)

    def test_eval_values_the_sources_do_not_give_are_labelled(self):
        # Eval finding 3: an owner, date or deadline the agent chose is "(proposed)" or an assumption.
        text = self.text()
        for phrase in ("owner, date or deadline", '"(proposed)"', "assumption"):
            self.assertIn(phrase, text)

    def test_eval_rough_rates_use_the_forecast_weeks(self):
        # Eval finding 1: a rough rate quoted beside the forecast uses the weeks it drew from.
        self.assertIn("same weeks the forecast drew from", self.text())

    def test_gate_n5_sign_off_is_pulled_from_any_tracker(self):
        self.assertIn("sync.py <tracker> pull", self.text())
        self.assertNotIn("sync.py github pull", self.text())

    def test_d15_skill_text_matches_the_checker(self):
        text = " ".join(self.text().split())
        for phrase in ("`raid_check.py` reads the status and the full pack",
                       '"signed" and "approved" as sign-off words',
                       "`/approve` with its date", "comment link"):
            self.assertIn(phrase, text)

    def test_gate_n3_help_says_the_full_pack_is_checked(self):
        code, out = run(RAID, "--help")
        self.assertEqual(code, 0)
        self.assertIn("full pack", out)
        self.assertNotIn("are\nnot checked", out)
        self.assertNotIn("are not checked", " ".join(out.split()))

    def test_n4_skill_says_today_is_a_utc_date(self):
        self.assertIn("UTC date", self.text())


if __name__ == "__main__":
    unittest.main()

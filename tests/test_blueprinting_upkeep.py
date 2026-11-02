import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/blueprinting/scripts/upkeep.py"


class DeadlineTest(unittest.TestCase):
    def calculate(self, start, zone, weekdays, holidays=()):
        value = {"schema": 1, "start": start, "calendar": {
            "zone": zone, "weekdays": weekdays, "holidays": list(holidays)}}
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(value), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_next_working_day_keeps_local_time_and_skips_holiday(self):
        result = self.calculate("2026-11-06T16:00:00+05:30", "Asia/Kolkata", [0, 1, 2, 3, 4], ["2026-11-09"])
        self.assertEqual(result["due"], "2026-11-10T16:00:00+05:30")
        self.assertEqual(result["adjustment"], "none")
        self.assertEqual(result["start"], "2026-11-06T16:00:00+05:30")
        self.assertEqual(len(result["calendar_hash"]), 64)

    def test_daylight_saving_gap_and_fold_do_not_become_elapsed_hours(self):
        all_days = list(range(7))
        gap = self.calculate("2026-03-07T02:30:00-05:00", "America/New_York", all_days)
        self.assertEqual(gap["due"], "2026-03-08T03:00:00-04:00")
        self.assertEqual(gap["adjustment"], "nonexistent-time-advanced")
        fold = self.calculate("2026-10-31T01:30:00-04:00", "America/New_York", all_days)
        self.assertEqual(fold["due"], "2026-11-01T01:30:00-04:00")
        self.assertEqual(fold["adjustment"], "ambiguous-time-earlier")
        normal = self.calculate("2026-03-06T16:00:00-05:00", "America/New_York", [0, 1, 2, 3, 4])
        self.assertEqual(normal["due"], "2026-03-09T16:00:00-04:00")

    def test_skipped_date_cannot_move_deadline_to_weekend_or_holiday(self):
        for weekdays, holidays in (([0, 1, 2, 3, 4], []), (list(range(7)), ["2011-12-31"])):
            with self.subTest(weekdays=weekdays):
                value = {"schema": 1, "start": "2011-12-29T16:00:00-10:00", "calendar": {
                    "zone": "Pacific/Apia", "weekdays": weekdays, "holidays": holidays}}
                result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(value),
                                        text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("calendar requires review", result.stderr)
        allowed = self.calculate("2011-12-29T16:00:00-10:00", "Pacific/Apia", list(range(7)))
        self.assertEqual(allowed["due"], "2011-12-31T00:00:00+14:00")


if __name__ == "__main__":
    unittest.main()

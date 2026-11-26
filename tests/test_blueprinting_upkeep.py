import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/blueprinting/scripts/upkeep.py"
ENGAGEMENT = SCRIPT.with_name("engagement.py")


class ObligationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "engagement"
        self.call("init", "factory")
        self.calendar = self.save("calendar", "source", {"calendar": {
            "zone": "Asia/Kolkata", "weekdays": [0, 1, 2, 3, 4], "holidays": []}})
        self.decision = self.save("release", "decision", {"state": "open", "question": "Who can release held stock?",
            "scope": "production", "first_raised": "2026-11-06T16:00:00+05:30"})
        self.data = {"purpose": "response-obligation", "decision": self.decision,
            "owner": None, "start": "2026-11-06T16:00:00+05:30", "due": "2026-11-09T16:00:00+05:30",
            "calendar": self.calendar, "due_basis": "next-working-day", "next_action": "Ask the quality lead for the release authority."}
        self.obligation = self.save("ask-quality", "artifact", self.data, [self.decision, self.calendar])

    def call(self, *args):
        result = subprocess.run([sys.executable, str(ENGAGEMENT), "--root", str(self.root), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def save(self, key, kind, data, inputs=(), previous=None, commit=True):
        value = {"schema": 1, "engagement": "factory", "id": key, "kind": kind, "previous": previous,
                 "inputs": [{"relation": "derived-from", **ref} for ref in inputs],
                 "body": "Synthetic retained evidence.", "data": data}
        path = Path(self.temp.name) / "records.json"
        path.write_text(json.dumps([value]))
        pending = self.call("prepare", str(path))["operation"]
        if not commit:
            return pending
        self.call("commit", pending)
        return {"id": key, "revision": self.call("status")["records"][key]["revision"]}

    def scan(self, at="2026-11-10T17:00:00+05:30", *args):
        return self.call("obligations", "--at", at, "--cadence-seconds", "3600", *args)

    def test_written_withdrawal_stops_due_work_without_accepting_or_erasing_uncertainty(self):
        appointment = self.save("appointment", "source", {"location": "Synthetic authority appointment"})
        authority = self.save("authority", "authority", {"status": "confirmed", "actor": "Client COO",
            "scopes": ["production"], "verified_by": "Consultant", "basis": appointment}, [appointment])
        confirmation_data = {"medium": "written", "origin": "client", "author": "Client COO", "identity": "confirmed",
            "date": "2026-11-09", "location": "Synthetic withdrawal email", "uncertainties": [],
            "confirmation": {"scope": "production", "target": self.decision, "response": "accept", "intent": "withdraw"}}
        confirmation = self.save("withdraw-email", "source", dict(confirmation_data, medium="verbal"), [self.decision])
        data = {"state": "accepted", "intent": "withdraw", "target": self.decision, "scope": "production",
            "authority": authority, "confirmation": confirmation, "verified_by": "Consultant",
            "verified_at": "2026-11-09T17:00:00+05:30"}
        draft = self.save("withdraw-release", "decision", {"state": "draft"})
        withdrawal = self.save("withdraw-release", "decision", data, [self.decision, authority, confirmation],
            previous=draft["revision"])
        self.assertEqual(next(d for d in self.scan()["decisions"] if d["id"] == "release")["state"], "open")
        confirmation = self.save("withdraw-email", "source", confirmation_data, [self.decision], previous=confirmation["revision"])
        withdrawal = self.save("withdraw-release", "decision", dict(data, confirmation=confirmation),
            [self.decision, authority, confirmation], previous=withdrawal["revision"])
        report = self.scan()
        self.assertEqual(report["decisions"][0]["state"], "withdrawn")
        self.assertEqual(report["decisions"][0]["first_raised"], "2026-11-06T16:00:00+05:30")
        row = report["obligations"][0]
        self.assertEqual(row["state"], "withdrawn")
        self.assertEqual(row["due"], self.data["due"])
        self.assertEqual(row["late_seconds"], 3600)
        self.assertEqual(row["notification"], "not-needed")
        self.assertFalse(self.call("baseline", "withdraw-release")["ready"], "Withdrawal must never pass acceptance")
        note = self.save("not-a-sent-action", "artifact", {"purpose": "note"})
        for key, follows, refs in (("malformed-follow", ["bad"], []), ("empty-follow", [], []),
                                   ("malformed-id", {"id": []}, []), ("wrong-follow", note, [note])):
            self.save(key, "artifact", dict(self.data, follows=follows), [self.decision, self.calendar, *refs])
            invalid = next(r for r in self.scan()["obligations"] if r["id"] == key)
            self.assertEqual(invalid["state"], "overdue")
            self.assertEqual(invalid["notification"], "needed")
            self.assertTrue(invalid["gaps"])
        self.save("unknown-send", "source", {"purpose": "reminder-receipt", "obligation": self.obligation,
            "marker": row["reminder_marker"], "stage": row["reminder_stage"], "outcome": "unknown",
            "checked_by": "Consultant", "checked_at": "2026-11-09T16:30:00+05:30", "location": "Synthetic timeout"},
            [self.obligation])
        self.assertEqual(self.scan()["obligations"][0]["notification"], "reconcile")
        # A changed authority basis reopens current use, without deleting the withdrawal history.
        self.save("appointment", "source", {"location": "Appointment corrected"}, previous=appointment["revision"])
        reopened = self.scan()
        self.assertEqual(next(d for d in reopened["decisions"] if d["id"] == "release")["state"], "open")
        self.assertEqual(reopened["obligations"][0]["state"], "overdue")

    def test_overdue_unassigned_work_survives_gap_and_draft_followup(self):
        check = self.save("last-check", "artifact", {"purpose": "obligation-check",
            "checked_at": "2026-11-09T15:00:00+05:30", "outcome": "observed"})
        self.save("draft", "artifact", {"purpose": "response-action", "obligation": self.obligation,
            "state": "draft"}, [self.obligation])
        report = self.scan("2026-11-10T17:00:00+05:30", "--last-check", check["id"])
        row = report["obligations"][0]
        self.assertEqual(row["state"], "overdue")
        self.assertTrue(row["unassigned"])
        self.assertEqual(row["overdue_seconds"], 90000)
        self.assertEqual(report["recovery"]["elapsed_seconds"], 93600)
        self.assertEqual(report["recovery"]["missed_checks"], 25)
        self.assertEqual(report["decisions"][0]["state"], "open")
        self.assertEqual(report["decisions"][0]["age_seconds"], 349200)
        boundary = self.scan("2026-11-09T16:00:00+05:30")["obligations"][0]
        self.assertEqual(boundary["state"], "pending")
        self.assertEqual(boundary["reminder_stage"], "due")
        for at, missed in (("2026-11-09T15:59:59.999999+05:30", 0),
                           ("2026-11-09T16:00:00+05:30", 0),
                           ("2026-11-09T16:00:00.000001+05:30", 1)):
            self.assertEqual(self.scan(at, "--last-check", check["id"])["recovery"]["missed_checks"], missed)

    def test_uncertain_reminder_blocks_later_stage_but_keeps_overdue_work_visible(self):
        due = self.scan("2026-11-09T16:00:00+05:30")["obligations"][0]
        receipt_data = {"purpose": "reminder-receipt", "obligation": self.obligation,
            "marker": due["reminder_marker"], "stage": "due", "outcome": "unknown",
            "checked_by": "Consultant", "checked_at": "2026-11-09T16:01:00+05:30",
            "location": "Host timeout; result unknown"}
        unknown = self.save("uncertain-reminder", "source", receipt_data, [self.obligation])
        overdue = self.scan()["obligations"][0]
        self.assertEqual(overdue["state"], "overdue")
        self.assertEqual(overdue["notification"], "reconcile")
        self.assertNotEqual(overdue["reminder_marker"], due["reminder_marker"])
        prior = unknown
        for replacement in ({"purpose": "note", "outcome": "draft"},
                            dict(receipt_data, outcome="draft"), {"purpose": "reminder-receipt"}):
            prior = self.save("uncertain-reminder", "source", replacement,
                              [self.obligation], previous=prior["revision"])
            self.assertEqual(self.scan()["obligations"][0]["notification"], "reconcile")
        self.save("uncertain-reminder", "source", dict(receipt_data, outcome="sent", effect_id="notification-1",
            checked_at="2026-11-09T16:02:00+05:30", reconciles=[unknown["revision"]]),
            [self.obligation], previous=prior["revision"])
        self.assertEqual(self.scan()["obligations"][0]["notification"], "needed",
                         "Resolved due-stage delivery must not suppress a later overdue stage")

    def test_reviewed_owner_transfer_keeps_original_deadline(self):
        import hashlib
        revised = dict(self.data, owner="New consultant")
        protected = ("decision", "owner", "start", "due", "calendar", "due_basis", "next_action", "follows", "agreement")
        encoded = json.dumps({key: revised.get(key) for key in protected}, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":")).encode()
        amendment = self.save("transfer-review", "review", {"purpose": "obligation-amendment", "status": "approved",
            "previous_revision": self.obligation["revision"], "changes_hash": hashlib.sha256(encoded).hexdigest(),
            "reviewer": "Engagement lead", "reason": "Consultant handover", "at": "2026-11-09T14:00:00+05:30"})
        self.save("ask-quality", "artifact", dict(revised, amendment=amendment),
                  [self.decision, self.calendar, amendment], previous=self.obligation["revision"])
        row = self.scan()["obligations"][0]
        self.assertEqual(row["owner"], "New consultant")
        self.assertEqual(row["due"], self.data["due"])
        self.assertEqual(row["state"], "overdue")
        self.assertTrue(row["current"])
        self.assertEqual(row["gaps"], [])

    def test_historical_reminder_reconciliation_survives_owner_amendments(self):
        import hashlib
        due = self.scan("2026-11-09T16:00:00+05:30")["obligations"][0]
        receipt_data = {"purpose": "reminder-receipt", "obligation": self.obligation,
            "marker": due["reminder_marker"], "stage": "due", "outcome": "unknown", "checked_by": "Consultant",
            "checked_at": "2026-11-09T16:01:00+05:30", "location": "Host timeout"}
        unknown = self.save("historical-reminder", "source", receipt_data, [self.obligation])

        def transfer(owner, prior):
            revised = dict(self.data, owner=owner)
            fields = ("decision", "owner", "start", "due", "calendar", "due_basis", "next_action", "follows", "agreement")
            encoded = json.dumps({key: revised.get(key) for key in fields}, sort_keys=True,
                                 ensure_ascii=False, separators=(",", ":")).encode()
            review = self.save(owner + "-review", "review", {"purpose": "obligation-amendment", "status": "approved",
                "previous_revision": prior["revision"], "changes_hash": hashlib.sha256(encoded).hexdigest(),
                "reviewer": "Engagement lead", "reason": "Owner transfer", "at": "2026-11-09T17:00:00+05:30"})
            return self.save("ask-quality", "artifact", dict(revised, amendment=review),
                             [self.decision, self.calendar, review], previous=prior["revision"])

        amended = transfer("consultant-one", self.obligation)
        self.assertEqual(self.scan()["obligations"][0]["notification"], "reconcile")
        verified = dict(receipt_data, outcome="sent", effect_id="notification-1", reconciles=[unknown["revision"]],
                        checked_at="2026-11-09T18:00:00+05:30")
        wrong = self.save("historical-reminder", "source", dict(verified, marker="wrong-marker"),
                          [self.obligation], previous=unknown["revision"])
        self.assertEqual(self.scan()["obligations"][0]["notification"], "reconcile")
        pending = self.save("historical-reminder", "source", verified, [self.obligation],
                            previous=wrong["revision"], commit=False)
        self.assertEqual(self.scan()["obligations"][0]["notification"], "reconcile")
        self.call("commit", pending)
        self.assertEqual(self.scan()["obligations"][0]["notification"], "needed")
        transfer("consultant-two", amended)
        final = self.scan()["obligations"][0]
        self.assertEqual(final["notification"], "needed")
        self.assertTrue(final["current"])
        self.assertEqual(final["gaps"], [])

    def test_reviewed_correction_recovers_after_unqualified_amendments(self):
        import hashlib
        revised = dict(self.data, owner="New consultant")
        prior = self.obligation
        for owner in ("Unreviewed owner", "Another unreviewed owner"):
            prior = self.save("ask-quality", "artifact", dict(self.data, owner=owner),
                              [self.decision, self.calendar], previous=prior["revision"])
            self.assertIsNone(self.scan()["obligations"][0]["owner"])
        fields = ("decision", "owner", "start", "due", "calendar", "due_basis", "next_action", "follows", "agreement")
        encoded = json.dumps({key: revised.get(key) for key in fields}, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":")).encode()
        amendment = self.save("repair-review", "review", {"purpose": "obligation-amendment", "status": "approved",
            "previous_revision": self.obligation["revision"], "changes_hash": hashlib.sha256(encoded).hexdigest(),
            "reviewer": "Engagement lead", "reason": "Correct the unreviewed transfers", "at": "2026-11-09T14:00:00+05:30"})
        repaired = self.save("ask-quality", "artifact", dict(revised, amendment=amendment),
                             [self.decision, self.calendar, amendment], previous=prior["revision"])
        row = self.scan()["obligations"][0]
        self.assertEqual(row["owner"], "New consultant")
        self.assertEqual(row["due"], self.data["due"])
        self.assertTrue(row["current"])
        self.assertEqual(row["gaps"], [])
        self.assertEqual(len(row["rejected_amendments"]), 2)
        self.save("ask-quality", "artifact", dict(revised, amendment=amendment),
                  [self.decision, self.calendar, amendment], previous=repaired["revision"])
        self.assertTrue(self.scan()["obligations"][0]["current"], "Unchanged fields do not need a new amendment")

    def test_unstructured_review_is_gap_not_loss_of_other_due_work(self):
        raw = {"schema": 1, "engagement": "factory", "id": "unstructured-review", "kind": "review",
               "previous": None, "inputs": [], "body": "Review not yet structured."}
        path = Path(self.temp.name) / "review.json"
        path.write_text(json.dumps([raw]))
        self.call("commit", self.call("prepare", str(path))["operation"])
        amendment = {"id": raw["id"], "revision": self.call("status")["records"][raw["id"]]["revision"]}
        self.save("other-response", "artifact", dict(self.data, owner="Other consultant"), [self.decision, self.calendar])
        self.save("ask-quality", "artifact", dict(self.data, owner="New owner", amendment=amendment),
                  [self.decision, self.calendar, amendment], previous=self.obligation["revision"])
        report = self.scan()
        self.assertEqual(len(report["obligations"]), 2)
        self.assertTrue(all(row["state"] == "overdue" for row in report["obligations"]))
        self.assertTrue(any("amendment" in gap for gap in report["gaps"]))

    def test_sent_followup_does_not_close_decision_or_hide_lateness(self):
        import hashlib
        content_hash = hashlib.sha256(b"Who is authorized to release held stock?").hexdigest()
        review = self.save("followup-review", "review", {"purpose": "followup", "status": "approved",
            "obligation": self.obligation, "content_hash": content_hash, "destination": "quality-lead",
            "reviewer": "Consultant", "at": "2026-11-09T16:00:00+05:30"}, [self.obligation])
        receipt = self.save("sent", "source", {"outcome": "sent", "content_hash": content_hash,
            "destination": "quality-lead", "sent_at": "2026-11-09T17:00:00+05:30",
            "checked_at": "2026-11-09T17:01:00+05:30", "checked_by": "Consultant",
            "effect_id": "message-7", "location": "Synthetic mail readback"})
        action = self.save("followup", "artifact", {"purpose": "response-action", "state": "sent",
            "obligation": self.obligation, "review": review, "receipt": receipt}, [self.obligation, review, receipt])
        missing_next = self.scan()
        self.assertEqual(missing_next["obligations"][0]["state"], "action-recorded")
        self.assertEqual(missing_next["obligations"][0]["late_seconds"], 3600)
        self.assertTrue(any("next response" in gap for gap in missing_next["gaps"]))
        self.save("check-quality", "artifact", dict(self.data, owner="Consultant",
            start="2026-11-09T17:00:00+05:30", due="2026-11-10T17:00:00+05:30", follows=action),
            [self.decision, self.calendar, action])
        report = self.scan()
        self.assertEqual(report["decisions"][0]["state"], "open")
        self.assertEqual(report["decisions"][0]["age_seconds"], 349200)
        self.assertFalse(any("next response" in gap for gap in report["gaps"]))
        self.save("sent", "source", {"outcome": "draft"}, previous=receipt["revision"])
        stale = self.scan()
        original = next(row for row in stale["obligations"] if row["id"] == "ask-quality")
        self.assertEqual(original["state"], "overdue")
        self.assertTrue(any("stale" in gap for gap in stale["gaps"]))

    def test_pending_changes_and_unreviewed_deadline_extension_stay_visible(self):
        self.save("ask-quality", "artifact", dict(self.data, owner="Consultant", due="2026-11-20T16:00:00+05:30"),
                  [self.decision, self.calendar], previous=self.obligation["revision"])
        report = self.scan()
        row = report["obligations"][0]
        self.assertEqual(row["due"], self.data["due"])
        self.assertEqual(row["state"], "overdue")
        self.assertTrue(any("amendment" in gap for gap in report["gaps"]))
        pending = self.save("pending-action", "artifact", dict(self.data, owner="Other consultant"),
                            [self.decision, self.calendar], commit=False)
        resumed = self.scan()
        self.assertIn(pending, resumed["pending_operations"])
        self.assertTrue(any("pending-action" in gap for gap in resumed["gaps"]))


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

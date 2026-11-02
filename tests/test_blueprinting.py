import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/blueprinting/scripts/engagement.py"


class EngagementRecordsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "engagement"
        self.call("init", "factory")

    def call(self, *args, error=None):
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                                capture_output=True, text=True)
        if error:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stderr)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def record(self, key, body, kind="source", previous=None, inputs=()):
        return {"schema": 1, "engagement": "factory", "id": key, "kind": kind,
                "previous": previous, "inputs": list(inputs), "body": body}

    def prepare(self, *records):
        path = Path(self.temp.name) / "batch.json"
        path.write_text(json.dumps(records))
        return self.call("prepare", str(path))["operation"]

    def save(self, record):
        operation = self.prepare(record)
        snapshot = self.call("commit", operation)["snapshot"]
        rev = self.call("status")["records"][record["id"]]["revision"]
        return rev, snapshot

    def edge(self, key, rev):
        return {"relation": "derived-from", "id": key, "revision": rev}

    def chain(self):
        source, _ = self.save(self.record("stock", "Planner reports 120 usable units."))
        req, _ = self.save(self.record("allocation", "Allocate 100 units.", "requirement",
                                      inputs=[self.edge("stock", source)]))
        _, snapshot = self.save(self.record("decision", "Reported acceptance of allocation.", "decision",
                                           inputs=[self.edge("allocation", req)]))
        self.save(self.record("training", "Training on Tuesday.", "requirement"))
        return source, snapshot

    def test_correction_invalidates_transitive_current_use_not_history_or_unrelated_work(self):
        source, old_snapshot = self.chain()
        self.assertTrue(self.call("status")["records"]["decision"]["current"])
        old_bytes = {p: p.read_bytes() for p in self.root.glob("records/*/*.md")}
        self.save(self.record("stock", "Quality confirms only 60 units are released.", previous=source))
        current = self.call("status")["records"]
        self.assertFalse(current["decision"]["current"], "Old approval must not survive changed stock evidence")
        self.assertFalse(current["allocation"]["current"])
        self.assertTrue(current["stock"]["current"])
        self.assertTrue(current["training"]["current"])
        historical = self.call("status", "--snapshot", old_snapshot)["records"]
        self.assertFalse(historical["decision"]["current"], "Historical snapshot cannot bypass known correction")
        for path, value in old_bytes.items():
            self.assertEqual(path.read_bytes(), value)

    def test_pending_correction_survives_fresh_process_and_resume_preserves_human_notes(self):
        source, _ = self.chain()
        notes = self.root / "notes" / "workshop.md"
        notes.parent.mkdir()
        notes.write_text("Human addition: quality approval still missing.\n")
        operation = self.prepare(self.record("stock", "Corrected: 60 units", previous=source))
        # Each call starts a fresh process. Preparation is a durable intent, not a committed revision.
        status = self.call("status")
        self.assertFalse(status["records"]["decision"]["current"])
        self.assertEqual(status["records"]["stock"]["revision"], source)
        self.assertTrue(status["records"]["training"]["current"])
        self.assertIn(operation, status["pending"])
        snap = self.call("commit", operation)["snapshot"]
        self.assertEqual(self.call("commit", operation)["snapshot"], snap)
        self.assertEqual(self.call("status")["pending"], [])
        self.assertEqual(notes.read_text(), "Human addition: quality approval still missing.\n")

    def test_corrupt_retained_bytes_do_not_fall_back_to_old_success(self):
        self.chain()
        path = next(self.root.glob("records/stock/*.md"))
        path.write_text(path.read_text().replace("120", "999"))
        self.call("status", error="Immutable record changed")

    def test_retained_note_preserves_supplied_line_endings(self):
        body = "# Meeting\r\n\r\nPlanner: 120 units.\r\n"
        self.save(self.record("meeting", body, "note"))
        path = next(self.root.glob("records/meeting/*.md"))
        self.assertTrue(path.read_bytes().endswith(body.encode()))

    def typed(self, key, kind, data, inputs=(), previous=None):
        value = self.record(key, f"# {key}\n\nSynthetic evidence for {key}.\n", kind, previous, inputs)
        value["data"] = data
        return value

    def ref(self, key, rev):
        return {"id": key, "revision": rev}

    def test_only_current_written_client_confirmation_can_establish_baseline(self):
        target, _ = self.save(self.record("allocation", "Allocate 60 released units.", "requirement"))
        appointment, _ = self.save(self.record("appointment", "Client appointment letter, section 2: COO owns production decisions."))
        authority, _ = self.save(self.typed("plant-owner", "authority", {
            "actor": "Client COO", "scopes": ["production"], "status": "confirmed",
            "verified_by": "Consultant", "basis": self.ref("appointment", appointment)},
            [self.edge("appointment", appointment)]))
        for medium, origin, identity, scope, covered, expected in [
            ("verbal", "client", "confirmed", "production", target, False),
            ("written", "consultant", "confirmed", "production", target, False),
            ("written", "client", "uncertain", "production", target, False),
            ("written", "client", "confirmed", "finance", target, False),
            ("written", "client", "confirmed", "production", target, True),
        ]:
            suffix = str(len(list(self.root.glob("snapshots/*.json"))))
            confirmation_id, decision_id = "confirm-" + suffix, "decision-" + suffix
            confirmation, _ = self.save(self.typed(confirmation_id, "source", {
                "medium": medium, "origin": origin, "author": "Client COO", "identity": identity,
                "date": "2026-11-02", "location": "Synthetic email message 7", "uncertainties": [],
                "confirmation": {"scope": scope, "target": self.ref("allocation", covered), "response": "accept"}},
                [self.edge("allocation", covered)]))
            self.save(self.typed(decision_id, "decision", {
                "scope": "production", "state": "accepted", "authority": self.ref("plant-owner", authority),
                "target": self.ref("allocation", target), "confirmation": self.ref(confirmation_id, confirmation),
                "verified_by": "Consultant", "verified_at": "2026-11-02T10:00:00+00:00"},
                [self.edge("plant-owner", authority), self.edge("allocation", target), self.edge(confirmation_id, confirmation)]))
            result = self.call("baseline", decision_id)
            self.assertEqual(result["ready"], expected, result)
            self.assertEqual(result["evidence_class"], "reported")
        self.save(self.record("allocation", "Allocate 50 released units.", "requirement", previous=target))
        self.assertFalse(self.call("baseline", decision_id)["ready"])

    def test_reconciliation_preserves_pending_intent_and_requires_covering_replacement(self):
        source, _ = self.chain()
        pending = self.prepare(self.record("stock", "60 units reported", previous=source))
        _, unrelated = self.save(self.record("workshop", "Another workshop was held.", "note"))
        self.call("commit", pending, error="needs reconciliation")
        receipt = Path(self.temp.name) / "resolution.json"
        resolution = {"operation": pending, "snapshot": unrelated, "reviewer": "Consultant",
                      "reason": "Compared both accounts with the quality lead", "at": "2026-11-02T14:00:00+00:00"}
        receipt.write_text(json.dumps(resolution))
        self.call("reconcile", str(receipt), error="must cover")
        _, replacement = self.save(self.record("stock", "Reconciled: 58 released units; two damaged.", previous=source))
        self.assertIn(pending, self.call("status")["pending"])
        resolution["snapshot"] = replacement
        receipt.write_text(json.dumps(resolution))
        self.call("reconcile", str(receipt))
        self.call("reconcile", str(receipt))
        status = self.call("status")
        self.assertEqual(status["pending"], [])
        self.assertTrue(status["records"]["stock"]["current"])
        self.assertFalse(status["records"]["decision"]["current"])
        self.assertTrue((self.root / "operations" / f"{pending}.json").exists())

    def test_invalid_references_ids_and_wrong_engagement_have_no_committed_effect(self):
        bad = [self.record("../escape", "bad"), self.record("claim", "bad", inputs=[self.edge("missing", "a" * 64)])]
        foreign = self.record("source", "private")
        foreign["engagement"] = "other-client"
        bad.append(foreign)
        for record in bad:
            path = Path(self.temp.name) / "invalid.json"
            path.write_text(json.dumps([record]))
            result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), "prepare", str(path)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.call("status")["records"], {})


if __name__ == "__main__":
    unittest.main()

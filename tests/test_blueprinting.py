import json
from decimal import Decimal
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
        excluded_source, _ = self.save(self.typed("exclude-source", "source", {
            "medium": "written", "origin": "client", "author": "Client COO", "identity": "confirmed",
            "date": "2026-11-02", "location": "Exclusion email", "uncertainties": [],
            "confirmation": {"scope": "production", "target": self.ref("allocation", target),
                             "response": "accept", "intent": "exclude"}}, [self.edge("allocation", target)]))
        exclusion, _ = self.save(self.typed("exclude-decision", "decision", {
            "scope": "production", "state": "accepted", "intent": "exclude",
            "authority": self.ref("plant-owner", authority), "target": self.ref("allocation", target),
            "confirmation": self.ref("exclude-source", excluded_source),
            "verified_by": "Consultant", "verified_at": "2026-11-02T10:00:00+00:00"},
            [self.edge("plant-owner", authority), self.edge("allocation", target), self.edge("exclude-source", excluded_source)]))
        self.assertFalse(self.call("baseline", "exclude-decision")["ready"])
        intent, _ = self.save(self.record("scope", "Allocation must be supported or explicitly excluded."))
        accepted = self.call("status")["records"][decision_id]["revision"]
        ledger = {"intent": self.ref("scope", intent), "criteria": [{"id": "allocate", "description": "Allocation scope resolved"}],
                  "coverage": [{"criterion": "allocate", "record": self.ref("allocation", target), "disposition": "excluded",
                                "decision": self.ref(decision_id, accepted)}], "children": [], "findings": [], "gaps": []}
        mission, _ = self.save(self.typed("scope-mission", "mission", ledger,
                                         [self.edge("scope", intent), self.edge("allocation", target), self.edge(decision_id, accepted)]))
        self.assertFalse(self.call("coverage", "scope-mission")["ready"])
        ledger["coverage"][0]["decision"] = self.ref("exclude-decision", exclusion)
        self.save(self.typed("scope-mission", "mission", ledger,
                            [self.edge("scope", intent), self.edge("allocation", target), self.edge("exclude-decision", exclusion)], previous=mission))
        self.assertTrue(self.call("coverage", "scope-mission")["ready"])
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

    def test_structured_requirement_cannot_drop_its_evidence_dependency(self):
        source, _ = self.save(self.record("quality", "Quality holds block stock release."))
        record = self.typed("release", "requirement", {"sources": [self.ref("quality", source)]})
        path = Path(self.temp.name) / "bad-link.json"
        path.write_text(json.dumps([record]))
        self.call("prepare", str(path), error="missing from input edges")

    def test_coverage_detects_missing_receiver_and_child_findings_not_integrated(self):
        self.save(self.record("empty-mission", "No coverage assessed yet.", "mission"))
        self.assertFalse(self.call("coverage", "empty-mission")["ready"])
        intent, _ = self.save(self.record("business-intent", "Plan only released stock, with accountable handoffs."))
        intent_edge = self.edge("business-intent", intent)
        source, _ = self.save(self.typed("interview", "source", {
            "date": "2026-11-02", "location": "Workshop 1, paragraph 4", "author": "Quality lead",
            "verification": "checked", "checked_by": "Consultant", "uncertainties": []}))
        details = {"actor": "Planner", "trigger": "Order released", "rules": ["Exclude held stock"],
                   "handoffs": [{"to": "", "when": "Stock shortage", "information": "Affected orders"}],
                   "exceptions": [{"condition": "No stock", "response": "Escalate", "owner": "Planning lead"}],
                   "outcome": "Feasible allocation", "verification": "Held stock cannot be allocated",
                   "sources": [self.ref("interview", source)], "gaps": []}
        requirement, _ = self.save(self.typed("release", "requirement", details, [self.edge("interview", source)]))
        mission_data = {"intent": self.ref("business-intent", intent),
                        "criteria": [{"id": "allocate", "description": "Allocate only released stock"}],
                        "coverage": [{"criterion": "allocate", "record": self.ref("release", requirement),
                                      "disposition": "supported"}], "children": [], "findings": [], "gaps": []}
        mission, _ = self.save(self.typed("planning", "mission", mission_data, [self.edge("release", requirement), intent_edge]))
        self.assertFalse(self.call("coverage", "planning")["ready"])
        details["handoffs"][0]["to"] = "Procurement lead"
        requirement, _ = self.save(self.typed("release", "requirement", details,
                                             [self.edge("interview", source)], previous=requirement))
        mission_data["coverage"][0]["record"] = self.ref("release", requirement)
        mission, _ = self.save(self.typed("planning", "mission", mission_data,
                                         [self.edge("release", requirement), intent_edge], previous=mission))
        self.assertTrue(self.call("coverage", "planning")["ready"])
        root_data = dict(mission_data, children=[{"mission": self.ref("planning", mission), "integration": None}])
        parent, _ = self.save(self.typed("transformation", "mission", root_data,
                                        [self.edge("release", requirement), self.edge("planning", mission), intent_edge]))
        self.assertFalse(self.call("coverage", "transformation")["ready"])
        review, _ = self.save(self.typed("return-planning", "review", {
            "parent": "transformation", "parent_intent": self.ref("business-intent", intent),
            "child": self.ref("planning", mission), "findings": [], "unresolved": [],
            "parent_criteria": mission_data["criteria"], "reviewer": "Consultant", "disposition": "integrated"},
            [self.edge("planning", mission), intent_edge]))
        root_data["children"][0]["integration"] = self.ref("return-planning", review)
        parent_edges = [self.edge("release", requirement), self.edge("planning", mission), self.edge("return-planning", review), intent_edge]
        parent, _ = self.save(self.typed("transformation", "mission", root_data, parent_edges, previous=parent))
        self.assertTrue(self.call("coverage", "transformation")["ready"])
        self.save(self.typed("other-parent", "mission", root_data, parent_edges))
        self.assertFalse(self.call("coverage", "other-parent")["ready"])
        root_data["criteria"] = [{"id": "allocate", "description": "Allocate across every plant, including transfers"}]
        self.save(self.typed("transformation", "mission", root_data, parent_edges, previous=parent))
        self.assertFalse(self.call("coverage", "transformation")["ready"])

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


class EstimateTest(unittest.TestCase):
    def test_ranges_preserve_assumptions_and_reject_unsupported_inputs(self):
        packet = {"schema": 1, "currency": "USD", "rate_date": "2026-11-02",
                  "assumptions": ["Synthetic rates; excludes tax and travel"], "basis": ["Fixture planning workshop"],
                  "contingency_percent": "10", "activities": [
                      {"id": "design", "activity": "Plant design", "role": "Consultant", "basis": "3 plant archetypes",
                       "quantity": "3", "days_per_unit_low": "2", "days_per_unit_high": "4", "day_rate": "1250", "after": []},
                      {"id": "validate", "activity": "Validation", "role": "Analyst", "basis": "2 review rounds",
                       "quantity": "2", "days_per_unit_low": "1.5", "days_per_unit_high": "2.5", "day_rate": "800", "after": ["design"]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estimate.json"
            def run():
                path.write_text(json.dumps(packet))
                return subprocess.run([sys.executable, str(SCRIPT.with_name("estimate.py")), str(path)],
                                      capture_output=True, text=True)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(list(map(Decimal, value["person_days"])), [Decimal(9), Decimal(17)])
            self.assertEqual(list(map(Decimal, value["base_cost"])), [Decimal(9900), Decimal(19000)])
            self.assertEqual(list(map(Decimal, value["total_cost"])), [Decimal(10890), Decimal(20900)])
            self.assertEqual(value["dependency_stages"], [["design"], ["validate"]])
            packet["activities"][1]["day_rate"] = "1000"
            changed = json.loads(run().stdout)
            self.assertEqual(list(map(Decimal, changed["base_cost"])), [Decimal(10500), Decimal(20000)])
            self.assertNotEqual(changed["input_hash"], value["input_hash"])
            packet["activities"][0]["after"] = ["validate"]
            self.assertNotEqual(run().returncode, 0)
            packet["activities"][0]["after"] = []
            packet["currency"] = "U1D"
            self.assertNotEqual(run().returncode, 0)
            packet["currency"] = "USD"
            packet["activities"][0]["day_rate"] = "NaN"
            self.assertNotEqual(run().returncode, 0)


if __name__ == "__main__":
    unittest.main()

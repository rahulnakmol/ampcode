import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
import shutil
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

    def test_templates_activate_only_complete_reviewed_assets_and_preserve_local_edits(self):
        source = Path(self.temp.name) / "templates"
        (source / "templates").mkdir(parents=True)
        asset = source / "templates" / "workshop.md"
        asset.write_text("# Workshop\n\nOriginal questions.\n")
        manifest = source / "template.json"
        manifest.write_text(json.dumps({"schema": 1, "version": 1, "requires": 1,
                                       "files": ["templates/workshop.md"]}))
        selected = ["workshop"]
        plan = self.call("template-preview", str(source), *selected)
        stage = self.call("template-stage", str(source), *selected, "--preview", plan["preview"])["stage"]
        self.assertIsNone(self.call("template-status")["active"])
        self.call("template-create", "workshop", "first", error="No active template")
        staged = self.root / "Blueprinting" / stage / "templates" / "workshop.md"
        original = staged.read_text()
        staged.unlink()
        self.call("template-activate", stage, error="Staged assets")
        self.call("template-stage", str(source), *selected, "--preview", plan["preview"])
        self.call("template-activate", stage)
        note = Path(self.call("template-create", "workshop", "first")["path"])
        self.assertEqual(note.read_text(), original)
        note.write_text("Consultant's working evidence.\n")
        self.call("template-create", "workshop", "first", error="exists")
        staged.write_text("# Workshop\n\nLocally tailored questions.\n")
        asset.write_text("# Workshop\n\nUpstream revised questions.\n")
        manifest.write_text(json.dumps({"schema": 1, "version": 2, "requires": 1,
                                       "files": ["templates/workshop.md"]}))
        conflict = self.call("template-preview", str(source), *selected)
        self.assertEqual(conflict["conflicts"], ["templates/workshop.md"])
        self.call("template-stage", str(source), *selected, "--preview", conflict["preview"], error="Resolve")
        resolutions = Path(self.temp.name) / "resolutions.json"
        resolutions.write_text(json.dumps({"templates/workshop.md": "local"}))
        stage2 = self.call("template-stage", str(source), *selected, "--preview", conflict["preview"],
                           "--resolutions", str(resolutions))["stage"]
        # A concurrent human edit after staging must not be hidden by activation.
        staged.write_text("Last-minute local question.\n")
        self.call("template-activate", stage2, error="changed since preview")
        staged.write_text("# Workshop\n\nLocally tailored questions.\n")
        self.call("template-activate", stage2)
        latest = Path(self.call("template-create", "workshop", "second")["path"])
        self.assertEqual(latest.read_text(), staged.read_text())
        self.assertEqual(note.read_text(), "Consultant's working evidence.\n")
        self.assertEqual(self.call("template-status")["active"]["version"], 2)
        # An allowlisted extension must not let an upgrade replace a retained record.
        manifest.write_text(json.dumps({"schema": 1, "version": 3, "requires": 1,
                                       "files": ["records/workshop.md"]}))
        self.call("template-preview", str(source), *selected, error="Template asset path")

    def test_start_requires_exact_identity_and_confirmation_and_resume_reports_gaps(self):
        root = Path(self.temp.name) / "new-engagement"
        config = Path(self.temp.name) / "start.json"
        source = Path(self.temp.name) / "starter"
        (source / "templates").mkdir(parents=True)
        (source / "templates" / "charter.md").write_text("# Charter\n\nUnreviewed working note.\n")
        (source / "template.json").write_text(json.dumps({"schema": 1, "version": 1, "requires": 1,
                                                        "files": ["templates/charter.md"]}))
        config.write_text(json.dumps({"schema": 1, "engagement": "new-client", "journey": "discovery",
                                     "policy": "Synthetic only; no external effects. Authority unresolved.",
                                     "templates": ["charter"]}))
        self.root = root
        preview = self.call("start", str(config), "--templates", str(source))
        self.assertFalse(root.exists(), "Unconfirmed Start must not create even a directory")
        self.assertEqual(preview["state"], "confirmation-required")
        started = self.call("start", str(config), "--templates", str(source), "--confirm", preview["confirmation"])
        self.assertEqual(started["engagement"], "new-client")
        self.call("resume", "other-client", error="Wrong engagement")
        resumed = self.call("resume", "new-client")
        self.assertEqual(resumed["journey"], "discovery")
        self.assertEqual(resumed["templates"]["active"]["version"], 1)
        self.assertIn("policy", resumed)
        self.assertEqual(resumed["records"]["input_observation"]["issues"], [])
        # An occupied root must not be adopted even if it has no engagement.json.
        occupied = Path(self.temp.name) / "occupied"
        occupied.mkdir()
        (occupied / "working.md").write_text("Preserve me.")
        self.root = occupied
        self.call("start", str(config), "--templates", str(source), error="empty")
        self.assertEqual((occupied / "working.md").read_text(), "Preserve me.")

    def test_derived_index_edits_are_preserved_but_never_become_authority(self):
        source, _ = self.chain()
        self.call("index")
        projection = self.root / "Indexes" / "records" / "allocation.md"
        original = projection.read_text()
        projection.write_text("Client approved everything.\n")
        self.assertTrue(self.call("status")["records"]["allocation"]["current"])
        result = self.call("index")
        edits = [row for row in result["preserved_edits"] if row["path"] == "Indexes/records/allocation.md"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(Path(edits[0]["backup"]).read_text(), "Client approved everything.\n")
        self.assertEqual(projection.read_text(), original)
        self.assertEqual(self.call("index")["preserved_edits"], result["preserved_edits"],
                         "Preserved-edit locations must survive a fresh process and later rebuild")
        self.save(self.record("stock", "Only 60 units are released.", previous=source))
        self.call("index")
        self.assertIn('"revision_state":"stale"', projection.read_text())
        self.assertFalse(self.call("baseline", "decision")["ready"])

    def test_working_file_changes_stale_dependents_and_require_explicit_rename(self):
        note = self.root / "notes" / "stock.md"
        note.parent.mkdir()
        note.write_text("Planner reports 120 units.\n")
        source = self.record("stock", note.read_text())
        source["data"] = {"input_file": {"path": "notes/stock.md", "sha256": hashlib.sha256(note.read_bytes()).hexdigest()}}
        rev, snapshot = self.save(source)
        self.save(self.record("allocation", "Allocate 100 units.", "requirement", inputs=[self.edge("stock", rev)]))
        self.save(self.record("unrelated", "Training remains open.", "requirement"))
        self.assertTrue(self.call("status")["records"]["allocation"]["current"])
        note.write_text("Quality confirms only 60 released units.\n")
        state = self.call("status")
        self.assertFalse(state["records"]["allocation"]["current"])
        self.assertTrue(state["records"]["unrelated"]["current"])
        self.assertEqual(state["input_observation"]["issues"][0]["state"], "changed")
        self.assertFalse(self.call("status", "--snapshot", snapshot)["records"]["stock"]["current"])
        renamed = note.with_name("quality.md")
        note.rename(renamed)
        self.assertEqual(self.call("status")["input_observation"]["issues"][0]["state"], "missing")
        correction = dict(source, previous=rev, body=renamed.read_text(), data={"input_file": {
            "path": "notes/quality.md", "sha256": hashlib.sha256(renamed.read_bytes()).hexdigest()}})
        batch = Path(self.temp.name) / "rename.json"
        batch.write_text(json.dumps([correction]))
        self.call("prepare", str(batch), error="Explicit rename")
        correction["data"]["input_file"]["renamed_from"] = "notes/stock.md"
        new_rev, _ = self.save(correction)
        state = self.call("status")
        self.assertTrue(state["records"]["stock"]["current"])
        self.assertFalse(state["records"]["allocation"]["current"])
        self.assertEqual(state["input_observation"]["issues"], [])
        erased = dict(correction, previous=new_rev, data={})
        batch.write_text(json.dumps([erased]))
        self.call("prepare", str(batch), error="Cannot remove input registration")

    def test_new_intake_files_and_symlinks_are_unresolved_not_ingested(self):
        folder = self.root / "incoming"
        folder.mkdir()
        policy = self.record("intake-policy", "Inspect supplied evidence before interpretation.", "note")
        policy["data"] = {"intake_folders": ["incoming"]}
        self.save(policy)
        self.assertEqual(self.call("status")["input_observation"]["issues"], [])
        (folder / "late.md").write_text("New contradictory evidence.")
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        state = self.call("status")
        self.assertEqual(state["input_observation"]["issues"], [
            {"record": None, "path": "incoming/late.md", "state": "unregistered"}])
        self.assertNotIn("late", state["records"])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        (folder / "escape").symlink_to(self.temp.name, target_is_directory=True)
        state = self.call("status")
        self.assertIn("unsafe", [i["state"] for i in state["input_observation"]["issues"]])

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

    def test_audio_permission_precedes_processing_and_pins_source_and_environment(self):
        path = self.root / "incoming" / "workshop.wav"
        path.parent.mkdir()
        path.write_bytes(b"not a decodable recording")
        source, _ = self.save(self.typed("recording", "source", {"medium": "audio", "input_file": {
            "path": "incoming/workshop.wav", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}))
        basis, _ = self.save(self.typed("consent", "source", {"location": "Synthetic permission fixture"}))
        allowed = {"purpose": "audio-processing", "status": "approved", "consent": "confirmed",
                   "source": self.ref("recording", source), "basis": self.ref("consent", basis),
                   "processor": "faster-whisper-1.2.1/small.en", "environment": str(self.root),
                   "retention": "Synthetic fixture lifetime", "authorized_by": "Fixture owner",
                   "reviewer": "Consultant", "at": "2026-01-01T10:00:00+00:00"}
        previous = None
        for field, value in (("consent", "unknown"), ("status", "draft"), ("processor", "cloud"),
                             ("environment", str(self.root.parent)), ("retention", ""),
                             ("at", "2999-01-01T10:00:00+00:00"), ("consent", "confirmed")):
            review, _ = self.save(self.typed("process-review", "review", dict(allowed, **{field: value}),
                [self.edge("recording", source), self.edge("consent", basis)], previous=previous))
            previous = review
            before = self.call("status")
            result = subprocess.run([sys.executable, str(SCRIPT.with_name("audio.py")), "--root", str(self.root),
                "--model", str(Path(self.temp.name) / "missing-model"), "recording", "process-review", "draft"],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("pinned local model" if (field, value) == ("consent", "confirmed") else "consent", result.stderr)
            after = self.call("status")
            self.assertEqual(after["snapshot"], before["snapshot"])
            self.assertEqual(after["pending"], [])
            self.assertNotIn("draft", after["records"])

    @unittest.skipUnless(os.environ.get("BLUEPRINTING_AUDIO_MODEL") and shutil.which("ffmpeg"),
                         "Set BLUEPRINTING_AUDIO_MODEL with pinned optional audio packages and ffmpeg")
    def test_video_only_recording_reports_gap_without_retaining_draft(self):
        path = self.root / "silent.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=0.1",
                        "-an", "-c:v", "mpeg4", str(path)], check=True)
        source, _ = self.save(self.typed("recording", "source", {"medium": "audio", "input_file": {
            "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}))
        basis, _ = self.save(self.typed("consent", "source", {"location": "Synthetic test permission"}))
        self.save(self.typed("process-review", "review", {
            "purpose": "audio-processing", "status": "approved", "consent": "confirmed",
            "source": self.ref("recording", source), "basis": self.ref("consent", basis),
            "processor": "faster-whisper-1.2.1/small.en", "environment": str(self.root),
            "retention": "Fixture lifetime", "authorized_by": "Fixture owner", "reviewer": "Consultant",
            "at": "2026-01-01T10:00:00+00:00"}, [self.edge("recording", source), self.edge("consent", basis)]))
        before = self.call("status")
        result = subprocess.run([sys.executable, str(SCRIPT.with_name("audio.py")), "--root", str(self.root),
            "--model", os.environ["BLUEPRINTING_AUDIO_MODEL"], "recording", "process-review", "draft"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("Audio blocked: No audio stream; request a usable recording", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        after = self.call("status")
        self.assertEqual(after["snapshot"], before["snapshot"])
        self.assertEqual(after["pending"], [])
        self.assertNotIn("draft", after["records"])

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

    def test_publication_binds_recipient_content_and_inherited_permissions(self):
        import hashlib
        def hashed(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode()).hexdigest()
        permission = {"grants": [{"audience": "steering-group", "destination": "private-review",
                                   "treatments": ["citation", "excerpt", "notes"]}],
                      "required_caveats": ["Synthetic example; not a measured result."]}
        source, _ = self.save(self.typed("evidence", "source", {"publication": permission}))
        claim, snap = self.save(self.typed("finding", "claim", {"publication": permission},
                                          [self.edge("evidence", source)]))
        packet = {"schema": 1, "title": "Planning decision", "snapshot": snap,
                  "audience": "steering-group", "destination": "private-review",
                  "blocks": [{"id": "opening", "kind": "text", "title": "Resolve stock ownership first",
                              "text": "Agree who can release held stock.", "notes": "Ask the quality lead.",
                              "caveats": permission["required_caveats"],
                              "citations": [{"record": self.ref("finding", claim), "label": "Workshop 1",
                                             "treatment": "excerpt"}]}]}
        def retained_packet(content, key, policy=None, extra_edges=()):
            data = {"packet": content}
            if policy is not None:
                data["publication"] = policy
            rev, _ = self.save(self.typed(key, "artifact", data, [self.edge("finding", claim), *extra_edges]))
            approval, _ = self.save(self.typed(key + "-review", "review", {
                "purpose": "publication", "packet": self.ref(key, rev), "packet_hash": hashed(content),
                "audience": content["audience"], "destination": content["destination"],
                "reviewer": "Consultant", "at": "2026-11-02T12:00:00+00:00", "status": "approved",
                "assessments": {"meaning": "passed", "language": "passed", "confidentiality": "passed",
                                "citations": "passed"}}, [self.edge(key, rev)]))
            return approval
        retained_packet(packet, "deck")
        result = self.call("publication", "deck", "deck-review")
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["packet"], packet)
        denied = {"grants": [], "required_caveats": ["Internal only"]}
        retained_packet(packet, "internal-deck", denied)
        self.assertFalse(self.call("publication", "internal-deck", "internal-deck-review")["ready"])
        policy, policy_snapshot = self.save(self.typed("policy", "source", {"publication": denied}))
        governed = dict(packet, snapshot=policy_snapshot)
        retained_packet(governed, "governed-deck", extra_edges=[dict(self.edge("policy", policy), relation="governed-by")])
        self.assertFalse(self.call("publication", "governed-deck", "governed-deck-review")["ready"])
        changed = json.loads(json.dumps(packet))
        changed["destination"] = "client-public-folder"
        retained_packet(changed, "other-deck")
        self.assertFalse(self.call("publication", "other-deck", "other-deck-review")["ready"])
        self.assertFalse(self.call("publication", "deck", "other-deck-review")["ready"])
        changed = json.loads(json.dumps(packet))
        changed["blocks"][0]["caveats"] = []
        retained_packet(changed, "no-caveat")
        self.assertFalse(self.call("publication", "no-caveat", "no-caveat-review")["ready"])
        changed = json.loads(json.dumps(packet))
        changed["blocks"][0]["notes"] = "Private source: obsidian://open?vault=client"
        retained_packet(changed, "private-notes")
        self.assertFalse(self.call("publication", "private-notes", "private-notes-review")["ready"])
        self.prepare(self.typed("evidence", "source", {"publication": {"grants": [], "required_caveats": []}}, previous=source))
        result = self.call("publication", "deck", "deck-review")
        self.assertFalse(result["ready"])
        self.assertNotIn("packet", result, "Blocked content must not be handed to an exporter")

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


class SkillCompositionTest(unittest.TestCase):
    def test_selected_package_binding_and_incompatible_dependency_controls(self):
        skills = SCRIPT.parents[2]
        domains = ("shaping-engagements", "discovering-requirements", "designing-functions",
                   "publishing-engagements", "reviewing-engagements")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected package"
            alternate = root / "other scope"
            domain = root / "domain package"
            for dest in (selected, alternate):
                shutil.copytree(skills / "blueprinting", dest, ignore=shutil.ignore_patterns("__pycache__"))
            def run(base=selected, domain_base=None, name=None, requires="1"):
                args = [sys.executable, str(selected / "scripts/contract.py"),
                        "--base", str(base), "--requires", requires]
                if domain_base is not None:
                    args += ["--domain-base", str(domain_base), "--domain", name]
                return subprocess.run(args, cwd=root, capture_output=True, text=True)
            for name in domains:
                shutil.copytree(skills / name, domain)
                result = run(domain_base=domain, name=name)
                self.assertEqual(result.returncode, 0, result.stderr)
                bound = json.loads(result.stdout)
                self.assertEqual(bound["base"], str(selected))
                self.assertEqual(bound["domain"], name)
                self.assertEqual(bound["helpers"]["engagement"], str(selected / "scripts/engagement.py"))
                shutil.rmtree(domain)
            self.assertEqual(run().returncode, 0, "Standalone coordinator must remain usable")
            result = run(base=alternate)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("executing package", result.stderr)
            manifest = selected / "contract.json"
            original = manifest.read_bytes()
            value = json.loads(original)
            value["contract"] = 2
            manifest.write_text(json.dumps(value))
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contract", result.stderr)
            self.assertEqual(result.stdout, "", "Must not return alternate package paths")
            manifest.write_bytes(original)
            self.assertNotEqual(run(requires="2").returncode, 0)
            manifest.unlink()
            self.assertNotEqual(run().returncode, 0)
            manifest.write_bytes(original)
            helper = selected / "scripts/qualification.py"
            helper.unlink()
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("qualification.py", result.stderr)
            helper.symlink_to(alternate / "scripts/qualification.py")
            self.assertNotEqual(run().returncode, 0, "No cross-install symlink fallback")
            helper.unlink()
            shutil.copyfile(alternate / "scripts/qualification.py", helper)
            marker = root / "unselected-code-executed"
            foreign = root / "foreign.py"
            foreign.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
            entry = selected / "scripts/engagement.py"
            entry.unlink()
            entry.symlink_to(foreign)
            self.assertNotEqual(run().returncode, 0)
            self.assertFalse(marker.exists(), "Dependency rejection must precede importing an unselected helper")
            entry.unlink()
            entry.write_text("class Invalid(ValueError):\n    pass\n")
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("Dependency blocked", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_domain_version_and_missing_base_fail_without_engagement_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            domain = root / "domain"
            shutil.copytree(SCRIPT.parents[2] / "designing-functions", domain)
            original = (domain / "contract.json").read_bytes()
            args = [sys.executable, str(SCRIPT.with_name("contract.py")), "--base", str(SCRIPT.parents[1]),
                    "--requires", "1", "--domain", "designing-functions", "--domain-base", str(domain)]
            for changes in ({"requires": 2}, {"version": 2}, {"skill": "shaping-engagements"},
                            {"schema": True}, {"requires": True}, {"extra": "unsupported"}):
                value = json.loads(original)
                value.update(changes)
                (domain / "contract.json").write_text(json.dumps(value))
                result = subprocess.run(args, cwd=root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, changes)
                self.assertIn("Dependency blocked", result.stderr)
                self.assertEqual(result.stdout, "")
            (domain / "contract.json").write_bytes(original)
            self.assertEqual(subprocess.run(args, cwd=root, capture_output=True).returncode, 0)
            (domain / "contract.json").unlink()
            self.assertNotEqual(subprocess.run(args, cwd=root, capture_output=True).returncode, 0)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["domain"])


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

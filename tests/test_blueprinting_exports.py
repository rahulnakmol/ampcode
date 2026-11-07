import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/blueprinting/scripts"
sys.path.insert(0, str(SCRIPTS))
from engagement import Engagement, digest


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "engagement"
        self.store = Engagement.create(self.root, "synthetic")
        source = self.record("stock", "source", {"publication": {
            "grants": [{"audience": "sponsor", "destination": "review", "treatments": ["excerpt", "notes"]}],
            "required_caveats": ["Synthetic case; quality approval is open."]}})
        snap = self.save(source)
        self.source = source
        common = {"text": "Released stock is 20 units below demand. Do not release held stock.",
                  "notes": "Ask the quality lead to confirm the release rule.",
                  "caveats": ["Synthetic case; quality approval is open."],
                  "citations": [{"record": {"id": "stock", "revision": digest(source)},
                                 "label": "Synthetic workshop, section 2", "treatment": "excerpt"}]}
        self.packet = {"schema": 1, "title": "Production planning: decision brief", "snapshot": snap,
                       "audience": "sponsor", "destination": "review", "blocks": [
                           dict(common, id="decision", kind="text", title="Keep the quality hold while resolving the shortfall"),
                           dict(common, id="evidence", kind="chart", title="Released stock cannot cover current demand",
                                categories=["Released", "Held", "Demand"], unit="Units",
                                series=[{"name": "Units", "values": [80, 40, 100]}]),
                           dict(common, id="ownership", kind="table", title="Confirm who owns the next decision",
                                columns=["Decision", "Owner", "Status"],
                                rows=[["Release held stock", "Quality lead", "Open"],
                                      ["Allocate released stock", "Planner", "Proposed"]])]}
        self.approve(self.packet)

    def approve(self, packet):
        heads = self.store.status()["records"]
        artifact = self.record("brief", "artifact", {"packet": packet}, [self.source])
        artifact["previous"] = heads.get("brief", {}).get("revision")
        self.save(artifact)
        review = self.record("review", "review", {"purpose": "publication", "status": "approved",
            "packet": {"id": "brief", "revision": digest(artifact)}, "packet_hash": digest(packet),
            "audience": "sponsor", "destination": "review", "reviewer": "Synthetic consultant",
            "at": "2026-11-02T12:00:00+00:00", "assessments": {
                "meaning": "passed", "language": "passed", "confidentiality": "passed", "citations": "passed"}}, [artifact])
        review["previous"] = heads.get("review", {}).get("revision")
        self.save(review)

    def record(self, key, kind, data, sources=()):
        return {"schema": 1, "engagement": "synthetic", "id": key, "kind": kind, "previous": None,
                "data": data, "body": "Synthetic record; private raw source body must not be exported.",
                "inputs": [{"relation": "derived-from", "id": r["id"], "revision": digest(r)} for r in sources]}

    def save(self, record):
        return self.store.commit(self.store.prepare([record]))

    def export(self, format, destination):
        return subprocess.run([sys.executable, str(SCRIPTS / "engagement.py"), "--root", str(self.root),
                               "export", "brief", "review", "--format", format, "--output", str(destination)],
                              text=True, capture_output=True)

    def test_unregistered_intake_blocks_export_until_inventory_and_packet_are_reviewed(self):
        folder = self.root / "incoming"
        folder.mkdir()
        self.save(self.record("intake-policy", "note", {"intake_folders": ["incoming"]}))
        allowed = Path(self.temp.name) / "before.md"
        self.assertEqual(self.export("md", allowed).returncode, 0)
        path = folder / "late.md"
        path.write_text("Synthetic late evidence; assess effect on stock claim.")
        blocked = Path(self.temp.name) / "blocked.md"
        result = self.export("md", blocked)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unresolved intake", result.stderr)
        self.assertFalse(blocked.exists())
        extra = self.record("late-source", "source", {"input_file": {
            "path": "incoming/late.md", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}})
        operation = self.store.prepare([extra])
        self.assertNotEqual(self.export("md", blocked).returncode, 0)
        self.store.commit(operation)
        result = self.export("md", blocked)
        self.assertNotEqual(result.returncode, 0, "Registering input is not a review of its impact")
        self.assertIn("Input inventory changed", result.stderr)
        self.assertFalse(blocked.exists())
        # Reported consultant review explicitly places the retained extra source in the
        # packet's reviewed context. This tests revision binding, not semantic independence.
        self.packet["snapshot"] = self.store.status()["snapshot"]
        self.approve(self.packet)
        self.assertEqual(self.export("md", blocked).returncode, 0)
        self.assertNotIn("late evidence", blocked.read_text())
        original = path.read_bytes()
        path.write_text("Changed after review: unsupported allocation.")
        changed_output = Path(self.temp.name) / "changed.md"
        self.assertNotEqual(self.export("md", changed_output).returncode, 0)
        self.assertFalse(changed_output.exists())
        # A new review must not confer approval on unretained changed bytes just by
        # selecting a snapshot containing the old, uncited source registration.
        self.packet["snapshot"] = self.store.status()["snapshot"]
        self.approve(self.packet)
        self.assertNotEqual(self.export("md", changed_output).returncode, 0)
        path.unlink()
        self.assertNotEqual(self.export("md", changed_output).returncode, 0)
        self.assertFalse(changed_output.exists())
        path.write_bytes(original)
        self.assertEqual(self.export("md", changed_output).returncode, 0)

    def test_markdown_preserves_caveats_notes_and_data_without_raw_sources(self):
        path = Path(self.temp.name) / "brief.md"
        result = self.export("md", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = path.read_text()
        for value in ("80", "40", "100", "20 units", "quality approval is open", "Quality lead", "Ask the quality lead"):
            self.assertIn(value, body)
        self.assertNotIn("private raw source", body)
        self.assertNotIn(digest(self.source), body)
        self.assertEqual(json.loads(result.stdout)["packet_hash"], digest(self.packet))
        self.assertNotEqual(self.export("md", path).returncode, 0, "Never overwrite a human-edited export")
        amendment = dict(self.source, previous=digest(self.source), body="Corrected stock: 60 released units.")
        self.store.prepare([amendment])
        blocked = Path(self.temp.name) / "stale.md"
        self.assertNotEqual(self.export("md", blocked).returncode, 0)
        self.assertFalse(blocked.exists())

    def test_external_attempt_survives_resume_and_requires_matching_readback(self):
        from datetime import datetime, timezone
        import hashlib
        content = Path(self.temp.name) / "debrief.md"
        self.assertEqual(self.export("md", content).returncode, 0)
        content_hash = hashlib.sha256(content.read_bytes()).hexdigest()
        intent = Path(self.temp.name) / "effect.json"
        intent.write_text(json.dumps({"id": "notion-save", "packet": "brief", "review": "review",
            "kind": "notion-new-page", "content_hash": content_hash,
            "authorized_by": "Synthetic consultant", "authorized_at": "2026-11-02T12:00:00+00:00"}))
        def call(*args, success=True):
            result = subprocess.run([sys.executable, str(SCRIPTS / "engagement.py"), "--root", str(self.root), *args],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success, result.stderr)
            return json.loads(result.stdout) if success else result.stderr
        prepared = call("external-prepare", str(intent))
        self.assertEqual(prepared["state"], "prepared")
        # Interrupt after durable intent, before manifest commit. A fresh process must not retry.
        interrupted = subprocess.run([sys.executable, "-c", """
import sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from engagement import Engagement
from external import attempt
with patch.object(Engagement, 'commit', side_effect=RuntimeError('injected interruption')):
    attempt(Engagement(sys.argv[2]), 'notion-save')
""", str(SCRIPTS), str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertIn("injected interruption", interrupted.stderr)
        pending_status = call("external-status", "notion-save")
        self.assertEqual(pending_status["state"], "prepared")
        self.assertFalse(pending_status["dependencies_current"])
        call("external-attempt", "notion-save", success=False)
        duplicate_path = Path(self.temp.name) / "duplicate.json"
        duplicate_path.write_text(json.dumps(dict(json.loads(intent.read_text()), id="pending-duplicate")))
        call("external-prepare", str(duplicate_path), success=False)
        pending = self.store.status()["pending"]
        self.assertEqual(len(pending), 1)
        call("commit", pending[0])
        self.assertEqual(call("external-status", "notion-save")["state"], "unknown")
        call("external-attempt", "notion-save", success=False)
        call("external-prepare", str(intent), success=False)
        duplicate = dict(json.loads(intent.read_text()), id="different-id")
        intent.write_text(json.dumps(duplicate))
        call("external-prepare", str(intent), success=False)
        observed = {"operation_marker": prepared["operation_marker"], "destination": "review", "outcome": "not-found",
                    "checked_by": "Synthetic consultant", "checked_at": datetime.now(timezone.utc).isoformat(),
                    "location": "Synthetic host response", "effect_id": "page-123", "content_hash": content_hash}
        source = self.record("readback", "source", observed)
        self.save(source)
        receipt = Path(self.temp.name) / "receipt.json"
        receipt.write_text(json.dumps({"id": "readback", "revision": digest(source)}))
        call("external-reconcile", "notion-save", str(receipt), success=False)
        revised = dict(source, previous=digest(source), data=dict(observed, outcome="verified", destination="wrong-place"))
        self.save(revised)
        receipt.write_text(json.dumps({"id": "readback", "revision": digest(revised)}))
        call("external-reconcile", "notion-save", str(receipt), success=False)
        final = dict(revised, previous=digest(revised), data=dict(observed, outcome="verified"))
        self.save(final)
        receipt.write_text(json.dumps({"id": "readback", "revision": digest(final)}))
        self.assertEqual(call("external-reconcile", "notion-save", str(receipt))["state"], "verified")
        status = call("external-status", "notion-save")
        self.assertEqual(status["effect_id"], "page-123")
        self.assertFalse(status["retry_allowed"])
        call("external-attempt", "notion-save", success=False)

    @unittest.skipUnless(importlib.util.find_spec("docx") and importlib.util.find_spec("pptx"), "Install export-requirements.txt for native export checks")
    def test_native_exports_reopen_with_editable_tables_chart_and_notes(self):
        from docx import Document
        from pptx import Presentation
        docpath, slides = Path(self.temp.name) / "brief.docx", Path(self.temp.name) / "brief.pptx"
        for format, path in (("docx", docpath), ("pptx", slides)):
            result = self.export(format, path)
            self.assertEqual(result.returncode, 0, result.stderr)
        doc = Document(docpath)
        self.assertEqual(doc.tables[0].cell(1, 1).text, "80")
        self.assertEqual(doc.tables[1].cell(1, 1).text, "Quality lead")
        doc.tables[1].cell(1, 1).text = "Named quality owner"
        doc.save(docpath)
        self.assertEqual(Document(docpath).tables[1].cell(1, 1).text, "Named quality owner")
        deck = Presentation(slides)
        self.assertEqual(len(deck.slides), 3)
        charts = [s.chart for slide in deck.slides for s in slide.shapes if s.has_chart]
        self.assertEqual(list(charts[0].series[0].values), [80, 40, 100])
        self.assertIn("Ask the quality lead", deck.slides[1].notes_slide.notes_text_frame.text)
        table = next(s.table for s in deck.slides[2].shapes if s.has_table)
        table.cell(1, 1).text = "Named quality owner"
        deck.save(slides)
        reopened = Presentation(slides)
        self.assertEqual(next(s.table for s in reopened.slides[2].shapes if s.has_table).cell(1, 1).text, "Named quality owner")

        dense = json.loads(json.dumps(self.packet))
        dense["blocks"] = [dense["blocks"][2]]
        dense["blocks"][0]["rows"] = [["Quality assurance clearance and regional distribution"] * 3 for _ in range(6)]
        target = Path(self.temp.name) / "dense.pptx"
        self.approve(dense)
        self.assertNotEqual(self.export("pptx", target).returncode, 0,
                            "A table within character caps can still overflow its row height")
        self.assertFalse(target.exists())
        soft_breaks = json.loads(json.dumps(self.packet))
        soft_breaks["blocks"][0]["text"] = "\v".join(["Mandatory caveat"] * 20)
        large_labels = json.loads(json.dumps(self.packet))
        chart = large_labels["blocks"][1]
        chart["categories"] = list("ABCDEFG")
        chart["series"] = [{"name": name, "values": [1000000000] * 7} for name in ("A", "B", "C")]
        for name, packet in (("soft-breaks", soft_breaks), ("large-labels", large_labels)):
            with self.subTest(name=name):
                target = Path(self.temp.name) / (name + ".pptx")
                self.approve(packet)
                self.assertNotEqual(self.export("pptx", target).returncode, 0)
                self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

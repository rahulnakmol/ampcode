import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
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

    def approve(self, packet, extra_sources=()):
        heads = self.store.status()["records"]
        artifact = self.record("brief", "artifact", {"packet": packet}, [self.source, *extra_sources])
        artifact["previous"] = heads.get("brief", {}).get("revision")
        self.save(artifact)
        assessments = {key: "passed" for key in ("meaning", "language", "confidentiality", "citations")}
        if packet["schema"] >= 3:
            assessments["brand"] = "passed"
        review = self.record("review", "review", {"purpose": "publication", "status": "approved",
            "packet": {"id": "brief", "revision": digest(artifact)}, "packet_hash": digest(packet),
            "audience": "sponsor", "destination": "review", "reviewer": "Synthetic consultant",
            "at": "2026-11-02T12:00:00+00:00", "assessments": assessments}, [artifact])
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

    def branded_packet(self):
        policy = {"grants": [{"audience": "sponsor", "destination": "review",
                              "treatments": ["excerpt", "notes"]}], "required_caveats": []}
        path = self.root / "brand-guidance.md"
        path.write_text("Synthetic brand: serif type, plum accent; no required logo or template.")
        source = self.record("brand-source", "source", {"input_file": {
            "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, "publication": policy})
        self.save(source)
        theme = {"font": "Liberation Serif", "ink": "25152F", "accent": "733A72", "muted": "59495C"}
        profile = self.record("brand-profile", "artifact", {"purpose": "brand-configuration", "publication": policy,
            "brand": {"schema": 1, "identity": "Synthetic advisory", "variant": "Editorial",
                "resolved_base": str(self.root), "skill": {"id": source["id"], "revision": digest(source)},
                "theme": theme, "issuer": "Synthetic advisory", "classification": "Internal review",
                "classification_authority": "Synthetic engagement lead", "composition": "theme-only",
                "override": "Not required by the synthetic brand", "unresolved": []}}, [source])
        self.save(profile)
        packet = dict(self.packet, schema=3, snapshot=self.store.status()["snapshot"], presentation={
            "schema": 1, "brand": {"id": profile["id"], "revision": digest(profile)},
            "theme": theme, "issuer": "Synthetic advisory", "classification": "Internal review"})
        return packet, profile

    def diagram_packet(self):
        from branding import NEUTRAL
        block = dict(self.packet["blocks"][0], id="release", kind="diagram", title="Release needs quality approval",
                     text="Proposed handoff: release only after approval. Receiver authority remains open.", notes="")
        evidence = [block["citations"][0]["record"]]
        block["diagram"] = {"schema": 1, "layout": "lanes-v1", "purpose": "handoff",
            "lanes": [{"id": "quality", "label": "Quality"}, {"id": "planning", "label": "Planning"}],
            "nodes": [{"id": "approve", "lane": "quality", "column": 0, "kind": "decision",
                       "label": "Approve lot", "evidence": evidence},
                      {"id": "receive", "lane": "planning", "column": 0, "kind": "activity",
                       "label": "Receive lot", "evidence": evidence}],
            "edges": [{"id": "release-lot", "from": "approve", "to": "receive", "kind": "handoff",
                       "label": "if approved", "evidence": evidence}]}
        return dict(self.packet, schema=4, blocks=[block], presentation={"schema": 1, "brand": None,
            "theme": NEUTRAL, "issuer": "Synthetic advisory", "classification": "Internal review"})

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("docx", "pptx", "xlsxwriter")),
                         "Install export-requirements.txt for native diagram checks")
    def test_diagram_exports_preserve_editable_graph_and_evidence(self):
        from zipfile import ZipFile
        from lxml import etree
        from pptx import Presentation
        packet = self.diagram_packet()
        packet["blocks"][0]["diagram"]["lanes"].append({"id": "unknown-owner", "label": "Approver unknown"})
        self.approve(packet)
        for format in ("md", "docx", "pptx", "xlsx"):
            with self.subTest(format=format):
                path = Path(self.temp.name) / ("diagram." + format)
                result = self.export(format, path)
                self.assertEqual(result.returncode, 0, result.stderr)
                if format == "md":
                    output = path.read_text()
                elif format == "pptx":
                    deck = Presentation(path)
                    slide = deck.slides[0]
                    output = "\n".join(s.text for s in slide.shapes if s.has_text_frame)
                    output += slide.notes_slide.notes_text_frame.text
                    self.assertGreaterEqual(sum(s.shape_type == 1 for s in slide.shapes), 2)
                    self.assertEqual(len(slide._element.xpath('.//a:tailEnd[@type="triangle"]')), 1)
                else:
                    with ZipFile(path) as archive:
                        name = "word/document.xml" if format == "docx" else "xl/sharedStrings.xml"
                        root = etree.fromstring(archive.read(name))
                        output = " ".join(root.itertext())
                        if format == "docx":
                            self.assertEqual(len(root.xpath('//*[local-name()="wgp"]')), 1)
                            self.assertEqual(len(root.xpath('//*[local-name()="tailEnd"]')), 1)
                            self.assertFalse(any(n.startswith("word/media/") for n in archive.namelist()))
                for value in ("approve", "receive", "if approved", "Synthetic workshop, section 2",
                              "Synthetic case; quality approval is open.", "Approver unknown", "unknown-owner"):
                    self.assertIn(value, output)
                self.assertNotIn("private raw source", output)

    def test_diagram_composition_and_publication_boundaries(self):
        from copy import deepcopy
        packet = self.diagram_packet()
        packet["blocks"][0]["diagram"]["lanes"].append({"id": "unknown-owner", "label": "Approver unknown"})
        repeated = deepcopy(packet["blocks"][0])
        repeated["id"] = "return"
        repeated["diagram"]["edges"] = [dict(repeated["diagram"]["edges"][0],
            id="return-lot", **{"from": "receive", "to": "approve"}, label="if rejected")]
        packet["blocks"].append(repeated)
        self.approve(packet)
        path = Path(self.temp.name) / "split.md"
        result = self.export("md", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("return-lot", path.read_text())
        self.assertIn("release, return", path.read_text())
        self.assertIn("unknown-owner | lane | Approver unknown | Block context", path.read_text())
        bad = deepcopy(packet)
        bad["blocks"][1]["diagram"]["nodes"][0]["label"] = "Different entity"
        self.approve(bad)
        failed = Path(self.temp.name) / "inconsistent.md"
        self.assertNotEqual(self.export("md", failed).returncode, 0)
        self.assertFalse(failed.exists())
        bad = deepcopy(packet)
        bad["blocks"][0]["diagram"]["edges"].extend(repeated["diagram"]["edges"])
        self.approve(bad)
        failed = Path(self.temp.name) / "overlapping.md"
        self.assertNotEqual(self.export("md", failed).returncode, 0)
        self.assertFalse(failed.exists())
        # An empty authored notes field must not bypass generated-register permission.
        changed = deepcopy(self.source)
        changed["previous"] = digest(self.source)
        changed["data"]["publication"]["grants"][0]["treatments"] = ["excerpt"]
        self.save(changed)
        self.source = changed
        packet = self.diagram_packet()
        packet["snapshot"] = self.store.status()["snapshot"]
        ref = {"id": changed["id"], "revision": digest(changed)}
        block = packet["blocks"][0]
        block["citations"][0] = dict(block["citations"][0], record=ref)
        for item in [*block["diagram"]["nodes"], *block["diagram"]["edges"]]:
            item["evidence"] = [ref]
        self.approve(packet)
        failed = Path(self.temp.name) / "denied-notes.md"
        result = self.export("md", failed)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no declared permission", result.stderr)
        self.assertFalse(failed.exists())

    def test_diagram_rejects_missing_lineage_layout_and_review(self):
        from copy import deepcopy
        packet = self.diagram_packet()
        mutations = {
            "dangling": lambda d: d["edges"][0].update(to="absent"),
            "self-loop": lambda d: d["edges"][0].update(to="approve"),
            "missing-evidence": lambda d: d["edges"][0].update(evidence=[]),
            "same-cell": lambda d: d["nodes"][1].update(lane="quality"),
            "nonadjacent": lambda d: d["nodes"][1].update(column=1),
            "unknown-layout": lambda d: d.update(layout="arbitrary"),
            "unknown-field": lambda d: d["nodes"][0].update(path="private-source.md"),
            "multiline": lambda d: d["nodes"][0].update(label="Approve\nlot"),
            "boolean-column": lambda d: d["nodes"][0].update(column=False),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                changed = deepcopy(packet)
                mutate(changed["blocks"][0]["diagram"])
                self.approve(changed)
                path = Path(self.temp.name) / (name + ".md")
                self.assertNotEqual(self.export("md", path).returncode, 0)
                self.assertFalse(path.exists())
        changed = deepcopy(packet)
        changed["blocks"][0]["diagram"]["nodes"][0]["evidence"] = [{"id": "stock", "revision": "0" * 64}]
        with self.assertRaisesRegex(ValueError, "Structured reference missing from input edges"):
            self.approve(changed)
        # A real governing input still cannot become diagram evidence without a block citation.
        other = self.record("other", "source", deepcopy(self.source["data"]))
        self.save(other)
        changed = deepcopy(packet)
        changed["snapshot"] = self.store.status()["snapshot"]
        changed["blocks"][0]["diagram"]["nodes"][0]["evidence"] = [{"id": "other", "revision": digest(other)}]
        self.approve(changed, [other])
        path = Path(self.temp.name) / "uncited-evidence.md"
        result = self.export("md", path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact evidence from its block citations", result.stderr)
        self.assertFalse(path.exists())
        self.approve(packet)
        head = self.store.status()["records"]["review"]["revision"]
        review = self.store.read_record("review", head)
        review["previous"] = head
        del review["data"]["assessments"]["brand"]
        self.save(review)
        path = Path(self.temp.name) / "missing-brand-assessment.md"
        self.assertNotEqual(self.export("md", path).returncode, 0)
        self.assertFalse(path.exists())

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("docx", "pptx")),
                         "Install export-requirements.txt for native diagram checks")
    def test_diagram_native_maximum_and_overflow_boundary(self):
        packet = self.diagram_packet()
        block = packet["blocks"][0]
        model = block["diagram"]
        evidence = model["nodes"][0]["evidence"]
        model["lanes"].append({"id": "controls", "label": "Controls"})
        model["nodes"] = [{"id": "n" + str(i), "lane": model["lanes"][i // 2]["id"],
            "column": i % 2, "kind": "activity", "label": label, "evidence": evidence}
            for i, label in enumerate(("Check lot", "Release lot", "Plan batch", "Receive lot", "Record use", "Confirm lot"))]
        model["edges"] = [{"id": "e" + str(i), "from": "n" + str(a), "to": "n" + str(b),
            "kind": "handoff", "label": "if clear", "evidence": evidence}
            for i, (a, b) in enumerate(((0, 1), (3, 2), (4, 5), (0, 2), (2, 4), (3, 1), (5, 3)))]
        self.approve(packet)
        for format in ("docx", "pptx"):
            path = Path(self.temp.name) / ("maximum." + format)
            result = self.export(format, path)
            self.assertEqual(result.returncode, 0, result.stderr)
        # Structurally allowed text must fail native fit, not silently shrink or truncate.
        model["nodes"][0]["label"] = "W" * 64
        self.approve(packet)
        for format in ("docx", "pptx"):
            path = Path(self.temp.name) / ("overflow." + format)
            self.assertNotEqual(self.export(format, path).returncode, 0)
            self.assertFalse(path.exists())
        self.assertEqual(self.export("md", Path(self.temp.name) / "portable-diagram.md").returncode, 0)

    def test_selected_brand_is_recipient_bound_and_does_not_change_business_evidence(self):
        packet, profile = self.branded_packet()
        business = self.record("business-decision", "decision", {}, [self.source])
        self.save(business)
        self.approve(packet, [profile])
        path = Path(self.temp.name) / "branded.md"
        result = self.export("md", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = path.read_text()
        for value in ("Synthetic advisory", "Internal review", "Released stock is 20 units below demand",
                      "Synthetic case; quality approval is open."):
            self.assertIn(value, output)
        for private in (str(self.root), "brand-guidance.md", "private raw source"):
            self.assertNotIn(private, output)
        altered = dict(packet, presentation=dict(packet["presentation"], classification="Public"))
        self.approve(altered, [profile])
        self.assertNotEqual(self.export("md", Path(self.temp.name) / "wrong-classification.md").returncode, 0)
        self.approve(packet, [profile])
        changed = dict(profile, previous=digest(profile), data=dict(profile["data"],
            brand=dict(profile["data"]["brand"], classification="Restricted")))
        self.save(changed)
        self.assertNotEqual(self.export("md", Path(self.temp.name) / "old-brand.md").returncode, 0)
        self.assertTrue(self.store.status()["records"]["business-decision"]["current"])
        self.assertEqual(self.store.status()["records"]["business-decision"]["revision"], digest(business))

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("docx", "pptx", "xlsxwriter")),
                         "Install export-requirements.txt for native brand checks")
    def test_brand_identity_refuses_native_overlap(self):
        packet, profile = self.branded_packet()
        labels = {"issuer": "W" * 100, "classification": "Internal review"}
        changed = dict(profile, previous=digest(profile), data=dict(profile["data"],
            brand=dict(profile["data"]["brand"], **labels)))
        self.save(changed)
        packet = dict(packet, snapshot=self.store.status()["snapshot"], presentation=dict(packet["presentation"],
            brand={"id": changed["id"], "revision": digest(changed)}, **labels))
        self.approve(packet, [changed])
        for format in ("docx", "pptx", "xlsx"):
            with self.subTest(format=format):
                path = Path(self.temp.name) / ("crowded." + format)
                self.assertNotEqual(self.export(format, path).returncode, 0)
                self.assertFalse(path.exists())
        self.assertEqual(self.export("md", Path(self.temp.name) / "portable.md").returncode, 0)

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("docx", "pptx", "xlsxwriter")),
                         "Install export-requirements.txt for native brand checks")
    def test_selected_brand_reaches_native_formats_without_losing_content(self):
        from datetime import datetime, timezone
        from docx import Document
        from pptx import Presentation
        from zipfile import ZipFile
        packet, profile = self.branded_packet()
        self.approve(packet, [profile])
        started = datetime.now(timezone.utc).replace(microsecond=0)
        outputs = {}
        for format in ("docx", "pptx", "xlsx"):
            path = Path(self.temp.name) / ("branded." + format)
            result = self.export(format, path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["packet_hash"], digest(packet))
            outputs[format] = path
        doc = Document(outputs["docx"])
        self.assertEqual(doc.styles["Normal"].font.name, "Liberation Serif")
        self.assertEqual(str(doc.styles["Normal"].font.color.rgb), "25152F")
        self.assertIn("Internal review", doc.sections[0].header.paragraphs[0].text)
        self.assertIn("Synthetic case; quality approval is open.", "\n".join(p.text for p in doc.paragraphs))
        # Native consumers may use literal fallback colors instead of the Office theme.
        from docx.oxml.ns import qn
        table_style = doc.styles["Light Shading Accent 1"].element
        self.assertEqual(doc.styles["Title"].element.xpath(".//w:pBdr/w:bottom")[0].get(qn("w:color")), "733A72")
        for border in table_style.xpath(".//w:tblBorders/* | .//w:tcBorders/*"):
            if border.get(qn("w:val")) == "single":
                self.assertEqual(border.get(qn("w:color")), "733A72")
        deck = Presentation(outputs["pptx"])
        for properties in (doc.core_properties, deck.core_properties):
            self.assertEqual(properties.author, "")
            self.assertEqual(properties.last_modified_by, "")
            self.assertEqual(properties.comments, "Exported, not delivered or client-approved.")
            for value in (properties.created, properties.modified):
                self.assertGreaterEqual(value.replace(tzinfo=timezone.utc), started)
                self.assertLessEqual(value.replace(tzinfo=timezone.utc), datetime.now(timezone.utc))
        self.assertEqual(deck.slides[0].shapes.title.text_frame.paragraphs[0].font.name, "Liberation Serif")
        self.assertIn("Internal review", "\n".join(s.text for s in deck.slides[0].shapes if s.has_text_frame))
        chart = next(s.chart for s in deck.slides[1].shapes if s.has_chart)
        self.assertEqual(str(chart.series[0].format.fill.fore_color.rgb), "733A72")
        self.assertEqual(list(chart.series[0].values), [80, 40, 100])
        with ZipFile(outputs["xlsx"]) as archive:
            self.assertIn(b'Liberation Serif', archive.read("xl/styles.xml"))
            self.assertIn(b'733A72', archive.read("xl/charts/chart1.xml"))
            self.assertIn(b'Internal review', archive.read("xl/worksheets/sheet1.xml"))
            self.assertNotIn(b'TableStyleMedium2', archive.read("xl/tables/table1.xml"))
            self.assertNotIn(b'Visible Calculation sheets', archive.read("xl/sharedStrings.xml"))
            self.assertNotIn(b'Amber labelled cells', archive.read("xl/sharedStrings.xml"))
        multilingual = dict(packet, blocks=[dict(packet["blocks"][0], text="Confirm 订单审批 before release.")])
        self.approve(multilingual, [profile])
        for format in ("docx", "pptx", "xlsx", "pdf-document"):
            blocked_glyph = Path(self.temp.name) / ("unapproved-glyph." + ("pdf" if format == "pdf-document" else format))
            result = self.export(format, blocked_glyph)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lacks required glyphs", result.stderr)
            self.assertFalse(blocked_glyph.exists())
        self.assertEqual(self.export("md", Path(self.temp.name) / "portable-glyph.md").returncode, 0)
        # A selected missing font must not silently become the neutral typeface.
        missing = dict(packet, presentation=dict(packet["presentation"], theme=dict(
            packet["presentation"]["theme"], font="Blueprinting Missing Font")))
        changed = dict(profile, previous=digest(profile), data=dict(profile["data"], brand=dict(
            profile["data"]["brand"], theme=missing["presentation"]["theme"])))
        self.save(changed)
        missing["snapshot"] = self.store.status()["snapshot"]
        missing["presentation"]["brand"] = {"id": changed["id"], "revision": digest(changed)}
        self.approve(missing, [changed])
        blocked = Path(self.temp.name) / "missing-font.docx"
        result = self.export("docx", blocked)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("font unavailable", result.stderr)
        self.assertFalse(blocked.exists())

    def test_package_uses_only_inspected_bytes_and_rechecks_freshness(self):
        from datetime import datetime, timezone
        from zipfile import ZipFile
        def call(*args, success=True):
            run = subprocess.run([sys.executable, str(SCRIPTS / "engagement.py"), "--root", str(self.root), *args],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode == 0, success, run.stderr)
            if not success:
                self.assertEqual(run.stdout, "")
                self.assertNotIn("Traceback", run.stderr)
            return json.loads(run.stdout) if success else run.stderr
        heads = self.store.status()["records"]
        packet = self.store.read_record("brief", heads["brief"]["revision"])
        publication_review = self.store.read_record("review", heads["review"]["revision"])
        selection_data = {"schema": 1, "audience": "sponsor", "destination": "review", "files": [
            {"name": "01-brief.md", "format": "md", "packet": {"id": "brief", "revision": digest(packet)},
             "review": {"id": "review", "revision": digest(publication_review)}}]}
        selection = self.record("handoff", "artifact", {"purpose": "export-selection", "selection": selection_data},
                                [packet, publication_review])
        self.save(selection)
        review = self.record("handoff-review", "review", {"purpose": "package-selection", "status": "approved",
            "selection": {"id": "handoff", "revision": digest(selection)}, "selection_hash": digest(selection_data),
            "reviewer": "Synthetic consultant", "at": "2026-11-07T10:00:00+00:00",
            "assessments": {"consistency": "passed", "confidentiality": "passed", "selection": "passed"}}, [selection])
        self.save(review)
        # Unsafe names and extra selected metadata must not become filesystem paths or ZIP members.
        for index, name in enumerate(("../private.md", "/absolute.md", "folder/note.md", "CON.md", "brief.pptx")):
            invalid_data = dict(selection_data, files=[dict(selection_data["files"][0], name=name)])
            invalid = self.record(f"selection-{index}", "artifact", {"purpose": "export-selection", "selection": invalid_data},
                                  [packet, publication_review])
            self.save(invalid)
            invalid_review = self.record(f"selection-review-{index}", "review", dict(review["data"],
                selection={"id": invalid["id"], "revision": digest(invalid)}, selection_hash=digest(invalid_data)), [invalid])
            self.save(invalid_review)
            call("package-stage", invalid["id"], invalid_review["id"], f"unsafe-{index}", success=False)
            self.assertFalse((self.root / ".blueprinting/exports" / f"unsafe-{index}").exists())
        # A rendering failure leaves an identifiable inactive candidate; a new ID can recover.
        interrupted = subprocess.run([sys.executable, "-c", """
import sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from engagement import Engagement
from handoff import stage
with patch('handoff.render', side_effect=RuntimeError('injected interruption')):
    stage(Engagement(sys.argv[2]), 'handoff', 'handoff-review', 'interrupted')
""", str(SCRIPTS), str(self.root)], capture_output=True, text=True)
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertIn("injected interruption", interrupted.stderr)
        self.assertEqual(call("package-status", "interrupted")["state"], "incomplete")
        call("package", "interrupted", "missing", "--output", str(Path(self.temp.name) / "partial.zip"), success=False)
        call("package-stage", "handoff", "handoff-review", "interrupted", success=False)
        candidate = call("package-stage", "handoff", "handoff-review", "candidate-one")
        self.assertEqual({row["candidate"] for row in call("package-status")}, {"interrupted", "candidate-one"})
        staged = Path(candidate["directory"]) / "01-brief.md"
        inspected = staged.read_bytes()
        destination = Path(self.temp.name) / "handoff.zip"
        call("package", "candidate-one", "missing-inspection", "--output", str(destination), success=False)
        self.assertFalse(destination.exists())
        inspection = self.record("inspection", "review", {"purpose": "package-inspection", "status": "approved",
            "candidate": "candidate-one", "manifest_hash": candidate["manifest_hash"], "files": candidate["files"],
            "reviewer": "Synthetic inspector", "at": datetime.now(timezone.utc).isoformat(),
            "assessments": {"rendering": "passed", "editability": "passed", "consistency": "passed", "brand": "passed"}},
            [selection, review])
        self.save(inspection)
        staged.write_bytes(inspected + b"Unreviewed edit")
        call("package", "candidate-one", "inspection", "--output", str(destination), success=False)
        self.assertFalse(destination.exists())
        staged.unlink()
        outside = Path(self.temp.name) / "outside.md"
        outside.write_bytes(inspected)
        staged.symlink_to(outside)
        call("package", "candidate-one", "inspection", "--output", str(destination), success=False)
        self.assertFalse(destination.exists())
        staged.unlink()
        staged.write_bytes(inspected)
        (staged.parent / "private-note.txt").write_text("Unselected private note")
        result = call("package", "candidate-one", "inspection", "--output", str(destination))
        self.assertEqual(result["status"], "exported-not-delivered")
        with ZipFile(destination) as archive:
            self.assertEqual(set(archive.namelist()), {"01-brief.md", "manifest.json"})
            self.assertEqual(archive.read("01-brief.md"), inspected)
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(inspected).hexdigest())
            self.assertEqual(set(manifest["files"][0]), {"name", "format", "revision", "sha256"})
            self.assertNotIn(str(self.root), json.dumps(manifest))
        call("package", "candidate-one", "inspection", "--output", str(destination), success=False)
        self.store.prepare([dict(self.source, previous=digest(self.source), body="Corrected stock: 60 released.")])
        blocked = Path(self.temp.name) / "stale.zip"
        call("package", "candidate-one", "inspection", "--output", str(blocked), success=False)
        self.assertFalse(blocked.exists())

    def test_typed_estimate_preserves_decimal_totals_and_rejects_unsupported_inputs(self):
        model = {"schema": 1, "currency": "USD", "rate_date": "2026-11-07",
                 "assumptions": ["Synthetic inputs, not a quotation"], "basis": ["Illustrative workshop scope"],
                 "contingency_percent": "0", "activities": [
                     {"id": "scope", "activity": "Scope review", "role": "Analyst", "basis": "Synthetic scope",
                      "quantity": "1000000", "days_per_unit_low": "1", "days_per_unit_high": "1",
                      "day_rate": "1", "after": []},
                     {"id": "validate", "activity": "Validation", "role": "Consultant", "basis": "Synthetic review",
                      "quantity": "0.999999", "days_per_unit_low": "1.000001", "days_per_unit_high": "2.000001",
                      "day_rate": "0.005", "after": ["scope"]}]}
        packet = dict(self.packet, schema=2, blocks=[dict(self.packet["blocks"][0], kind="estimate", model=model)])
        self.approve(packet)
        output = Path(self.temp.name) / "estimate.md"
        result = self.export("md", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = output.read_text()
        # Ordinary floating SUM/ROUND incorrectly returns 1000000.01 for the low amount.
        self.assertIn("1000000.00 | 1000000.01", body)
        self.assertIn("1000001.000000 | 1000001.999999", body)
        for value in ("USD", "2026-11-07", "Synthetic inputs", "Synthetic scope", "Consultant", "scope"):
            self.assertIn(value, body)
        tie = json.loads(json.dumps(packet))
        tie["blocks"][0]["model"]["activities"] = [dict(model["activities"][0], quantity="0.5",
            days_per_unit_low="0.000001", days_per_unit_high="0.000003", day_rate="10000")]
        self.approve(tie)
        tie_output = Path(self.temp.name) / "half-up.md"
        self.assertEqual(self.export("md", tie_output).returncode, 0)
        self.assertIn("0.000001 | 0.000002", tie_output.read_text())
        self.assertIn("0.01 | 0.02", tie_output.read_text())
        for index, (field, value) in enumerate((("quantity", "1000000.000001"),
                ("day_rate", "0.0000001"), ("day_rate", "1.000000000000000000000000000000000001"),
                ("day_rate", "1000000"), ("day_rate", "=SUM(A1:A2)"), ("private_field", "Not selected"))):
            changed = json.loads(json.dumps(packet))
            changed["blocks"][0]["model"]["activities"][0][field] = value
            self.approve(changed)
            target = Path(self.temp.name) / f"invalid-estimate-{index}.md"
            failure = self.export("md", target)
            self.assertNotEqual(failure.returncode, 0, failure.stdout)
            self.assertNotIn("Traceback", failure.stderr)
            self.assertFalse(target.exists())
        packet["schema"] = 1
        self.approve(packet)
        self.assertNotEqual(self.export("md", Path(self.temp.name) / "schema-one.md").returncode, 0)
        # Typed assumptions/activity detail become speaker notes even with empty supplied notes.
        source = json.loads(json.dumps(self.source))
        source["previous"] = digest(self.source)
        source["data"]["publication"]["grants"][0]["treatments"] = ["excerpt"]
        self.save(source)
        self.source = source
        packet["schema"] = 2
        packet["snapshot"] = self.store.status()["snapshot"]
        packet["blocks"][0]["notes"] = ""
        packet["blocks"][0]["citations"][0]["record"]["revision"] = digest(source)
        self.approve(packet)
        blocked = Path(self.temp.name) / "unpermitted-notes.md"
        self.assertNotEqual(self.export("md", blocked).returncode, 0)
        self.assertFalse(blocked.exists())

    @unittest.skipUnless(importlib.util.find_spec("xlsxwriter") and shutil.which("libreoffice"),
                         "Install export-requirements.txt and LibreOffice for native workbook checks")
    def test_workbook_preserves_literal_registers_and_exact_estimate_values(self):
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        model = {"schema": 1, "currency": "USD", "rate_date": "2026-11-07",
                 "assumptions": ["Synthetic inputs, not a quotation"], "basis": ["Illustrative workshop scope"],
                 "contingency_percent": "0", "activities": [
                     {"id": "scope", "activity": "Scope review", "role": "Analyst", "basis": "Synthetic scope",
                      "quantity": "1000000", "days_per_unit_low": "1", "days_per_unit_high": "1",
                      "day_rate": "1", "after": []},
                     {"id": "validate", "activity": "Validation", "role": "Consultant", "basis": "Synthetic review",
                      "quantity": "0.999999", "days_per_unit_low": "1.000001", "days_per_unit_high": "2.000001",
                      "day_rate": "0.005", "after": ["scope"]}]}
        register = dict(self.packet["blocks"][2], rows=[
            ["=1+1", "+SUM(A1:A2)", "@Unassigned"], ["-1+2", "Quality lead", "Open"]])
        packet = dict(self.packet, schema=2, blocks=[register,
            dict(self.packet["blocks"][0], kind="estimate", model=model)])
        self.approve(packet)
        output = Path(self.temp.name) / "support.xlsx"
        result = self.export("xlsx", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["packet_hash"], digest(packet))
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with ZipFile(output) as archive:
            strings = ["".join(node.itertext()) for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
            sheets = ET.fromstring(archive.read("xl/workbook.xml")).find("s:sheets", ns)
            names = [node.attrib["name"] for node in sheets]
            self.assertIn("Read me", names)
            self.assertTrue(all(node.get("state", "visible") == "visible" for node in sheets))
            def cells(name):
                tree = ET.fromstring(archive.read(f"xl/worksheets/sheet{names.index(name) + 1}.xml"))
                return {cell.attrib["r"]: cell for cell in tree.findall(".//s:c", ns)}
            overview = "\n".join(strings[int(cell.find("s:v", ns).text)]
                                 for cell in cells("Read me").values() if cell.get("t") == "s")
            self.assertIn("Released stock is 20 units below demand", overview)
            self.assertIn("Synthetic case; quality approval is open.", overview)
            self.assertIn("Source: Synthetic workshop, section 2", overview)
            self.assertLess(overview.index("Released stock is 20 units below demand"), overview.index("Editable inputs"))
            self.assertIn("Narrative baseline", overview)
            self.assertIn("Ctrl+Shift+F9", overview)
            self.assertIn("after edits and on reopening", overview)
            self.assertIn("Conversion alone is not a recalculation check", overview)
            current_total = next(ref for ref, cell in cells("Read me").items()
                                 if cell.get("t") == "s" and strings[int(cell.find("s:v", ns).text)] == "Current total (USD)")
            current_total = "B" + current_total[1:]
            table = cells("Content 1")
            self.assertEqual(strings[int(table["A8"].find("s:v", ns).text)], "=1+1")
            self.assertIsNone(table["A8"].find("s:f", ns))
            self.assertEqual(len([name for name in archive.namelist() if name.startswith("xl/tables/table")]), 2)
            estimate = cells("Estimate 2")
            for ref, expected in (("H17", "1000000.0"), ("I17", "1000000.01")):
                self.assertIsNotNone(estimate[ref].find("s:f", ns))
                self.assertEqual(float(estimate[ref].find("s:v", ns).text), float(expected))
            self.assertIn("Synthetic inputs, not a quotation", " ".join(strings))
            self.assertIn("Synthetic workshop, section 2", " ".join(strings))
            self.assertNotIn("private raw source", " ".join(strings))
            self.assertFalse(any("externalLink" in name or "vbaProject" in name for name in archive.namelist()))
        # Native recalculation, not cached values, must preserve the rounding boundary.
        # Pasted out-of-domain edits must withhold every qualified total.
        sheet_path = f"xl/worksheets/sheet{names.index('Estimate 2') + 1}.xml"
        for scenario, edit, expected in (("baseline", None, [1000000.00, 1000000.01]),
                                         ("edited", ("B8", "2"), [1000000.01, 1000000.02]),
                                         ("invalid", ("B7", "0"), None),
                                         ("fine-quantity", ("B7", "999999.000000001"), None),
                                         ("fine-contingency", ("B11", "99.0000000000001"), None),
                                         ("retained-quantity", ("B7", "999999.0000000001"), None),
                                         ("retained-effort", ("C7", "1.000000000000001"), None),
                                         ("below-power-two", ("B7", "0.9999999999999999"), None),
                                         ("retained-contingency", ("B11", "99.00000000000001"), None)):
            folder = Path(self.temp.name) / scenario
            folder.mkdir()
            native = folder / "input.xlsx"
            with ZipFile(output) as source, ZipFile(native, "w") as target:
                for member in source.infolist():
                    data = source.read(member.filename)
                    if member.filename.startswith("xl/worksheets/") and member.filename.endswith(".xml"):
                        tree = ET.fromstring(data)
                        if edit and member.filename == sheet_path:
                            tree.find(f".//s:c[@r='{edit[0]}']/s:v", ns).text = edit[1]
                        # Force actual formula evaluation on load; converting a workbook
                        # with intact caches can merely copy those caches in LibreOffice.
                        for cell in tree.findall(".//s:c", ns):
                            if cell.find("s:f", ns) is not None:
                                value = cell.find("s:v", ns)
                                if value is not None:
                                    cell.remove(value)
                        data = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
                    target.writestr(member, data)
            converted = folder / "recalculated"
            converted.mkdir()
            run = subprocess.run(["libreoffice", "-env:UserInstallation=" + (folder / "profile").as_uri(),
                                  "--headless", "--convert-to", "xlsx", "--outdir", str(converted), str(native)],
                                 capture_output=True, text=True, timeout=90)
            self.assertEqual(run.returncode, 0, run.stderr)
            with ZipFile(converted / "input.xlsx") as archive:
                estimate = cells("Estimate 2")
                summary_total = cells("Read me")[current_total].find("s:v", ns)
                if expected:
                    self.assertEqual([float(value) for value in summary_total.text.split(" – ")], expected)
                    for col, value in zip("HI", expected):
                        self.assertEqual(float(estimate[col + "17"].find("s:v", ns).text), value)
                        self.assertIsNotNone(estimate[col + "17"].find("s:f", ns))
                else:
                    self.assertTrue(summary_total is None or summary_total.text is None)
                    for row in range(14, 18):
                        for col in "HI":
                            value = estimate[col + str(row)].find("s:v", ns)
                            self.assertTrue(value is None or value.text is None)
        original = output.read_bytes()
        self.assertNotEqual(self.export("xlsx", output).returncode, 0)
        self.assertEqual(output.read_bytes(), original)
        self.store.prepare([dict(self.source, previous=digest(self.source), body="Corrected stock.")])
        blocked = Path(self.temp.name) / "stale.xlsx"
        self.assertNotEqual(self.export("xlsx", blocked).returncode, 0)
        self.assertFalse(blocked.exists())

    @unittest.skipUnless(importlib.util.find_spec("docx") and all(shutil.which(tool)
                         for tool in ("libreoffice", "pdftotext")), "Native document render tools required")
    def test_document_pdf_preserves_table_rows_across_page_breaks(self):
        from branding import NEUTRAL
        packet, profile = self.branded_packet()
        # A real bounded executive specimen lost its entire estimate at the page break.
        # Preserve its content density, but assert content rather than page numbers/layout.
        common = dict(self.packet["blocks"][0], notes="", caveats=[
            "Synthetic case; quality approval is open.", "No client approval, release date or SAP fit established."],
            citations=[dict(self.packet["blocks"][0]["citations"][0],
                            label="S01 r2: stock; S02 r1: quality; S03 r1: demand; A01 r1: pilot")])
        blocks = [dict(common, id="decision", kind="text", title="Decision requested and accountable role",
            text="For decision: Executive sponsor to approve, defer or reject a one-plant functional-design pilot. "
                 "Recommendation: approve subject to scope, staffing and rates validation; keep the customer date provisional. "
                 "Implications: USD 43,700-66,700 indicative cost; implementation is excluded. "
                 "Status: proposed, not approved. Named approver and agreed response date: unknown."),
            dict(common, id="exposure", kind="table", title="Supply exposure: 30-unit released-stock shortfall",
                 text="100 units of firm demand exceed 70 released units by 30. The 50 held units are not available without authorized release.",
                 columns=["Category", "Units"], rows=[["Released", "70"], ["Held", "50"], ["Demand", "100"]]),
            dict(common, id="options", kind="table", title="Options and business implications",
                 text="Proposed alternatives; none is approved. A release or dated replenishment would change the assessment.",
                 columns=["Option", "Benefit", "Limit / condition"], rows=[
                     ["Design pilot", "Test control boundary", "No near-term supply added"],
                     ["Defer pilot", "Avoid pilot cost now", "Control gaps stay unresolved"],
                     ["Replan promise", "Use evidenced supply", "Customer agreement needed"]]),
            dict(common, id="cost", kind="table", title="Indicative pilot effort and expenditure",
                 text="One plant; no build or rollout.\nRates dated 2026-11-07; contingency 15%. Cost ≠ price; effort ≠ duration.",
                 columns=["Measure", "Low", "High"], rows=[
                     ["Person-days", "38.000000", "58.000000"], ["Base USD", "38000.00", "58000.00"],
                     ["Contingency USD", "5700.00", "8700.00"], ["Total USD", "43700.00", "66700.00"]])]
        for theme in (NEUTRAL, packet["presentation"]["theme"]):
            branded = theme != NEUTRAL
            selected = dict(packet, title="Executive brief: functional-design pilot", blocks=blocks,
                            presentation=dict(packet["presentation"], theme=theme,
                            brand=packet["presentation"]["brand"] if branded else None))
            self.approve(selected, [profile] if branded else [])
            path = Path(self.temp.name) / f"tables-{branded}.pdf"
            result = self.export("pdf-document", path)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                  capture_output=True, text=True, check=True).stdout
            for block in blocks[1:]:
                for row in block["rows"]:
                    for value in row:
                        self.assertIn(value, text)

    @unittest.skipUnless(importlib.util.find_spec("xlsxwriter") and all(shutil.which(tool)
                         for tool in ("libreoffice", "pdftotext", "pdftohtml")), "Native workbook render tools required")
    def test_workbook_prints_long_titles_and_wide_registers_readably(self):
        from xml.etree import ElementTree as ET
        title = ("Requirements and ownership for regional production planning, quality release, exception handling "
                 "and client approvals — retain every exclusion and unresolved authority decision before agreeing the delivery baseline")
        register = dict(self.packet["blocks"][2], title=title,
                        columns=["ID", "Requirement", "Owner", "Evidence", "Acceptance", "Gap", "Decision", "Due date", "Status", "Caveat"],
                        rows=[["REQ-1", "Controlled release", "Quality lead", "Workshop", "Pending", "Authority", "Open", "Unknown", "Proposed", "Not approved"]])
        packet = dict(self.packet, title=title, blocks=[register])
        self.approve(packet)
        output = Path(self.temp.name) / "wide.xlsx"
        self.assertEqual(self.export("xlsx", output).returncode, 0)
        run = subprocess.run(["libreoffice", "-env:UserInstallation=" + (Path(self.temp.name) / "profile").as_uri(),
                              "--headless", "--convert-to", "pdf", "--outdir", self.temp.name, str(output)],
                             capture_output=True, text=True, timeout=90)
        self.assertEqual(run.returncode, 0, run.stderr)
        pdf = output.with_suffix(".pdf")
        body = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        self.assertGreaterEqual(" ".join(body.split()).count("before agreeing the delivery baseline"), 3)
        for value in ("REQ-1", "Not approved", "quality approval is open", "Synthetic workshop"):
            self.assertIn(value, body)
        xml = subprocess.run(["pdftohtml", "-xml", "-zoom", "1", "-i", "-stdout", str(pdf)],
                             capture_output=True, text=True, check=True).stdout
        tree = ET.fromstring(xml)
        register_pages = [page for page in tree.findall("page") if "Controlled release" in " ".join(page.itertext())]
        self.assertEqual(len(register_pages), 1)
        self.assertIn("Not approved", " ".join(register_pages[0].itertext()), "All ten row fields must print together")
        sizes = [int(font.attrib["size"]) for font in tree.findall(".//fontspec")]
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 9, "Supported wide registers must not shrink into unreadable print")

        # A page break cannot make a chart fit below an arbitrarily tall repeated title.
        chart = dict(self.packet["blocks"][1], title=title + "; " + title,
                     categories=[f"Category {i}" for i in range(20)],
                     series=[{"name": "Count", "values": list(range(20))}])
        self.approve(dict(self.packet, title=chart["title"], blocks=[chart]))
        blocked = Path(self.temp.name) / "split-chart.xlsx"
        result = self.export("xlsx", blocked)
        self.assertNotEqual(result.returncode, 0, "An accepted chart must fit on its printed page")
        self.assertIn("split and review", result.stderr)
        self.assertFalse(blocked.exists())
        self.approve(dict(self.packet, title=title, blocks=[dict(chart, title=title)]))
        supported = Path(self.temp.name) / "readable-chart.xlsx"
        result = self.export("xlsx", supported)
        self.assertEqual(result.returncode, 0, result.stderr)

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

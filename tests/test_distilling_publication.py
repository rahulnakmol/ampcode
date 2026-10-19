"""Contract tests for distilling-videos publication rendering and packaging.

Run: python3 -m unittest discover -s tests -p 'test_distilling_publication.py' -v
Evidence is built through the real CLI and evidence API; browsers are fake executables.
No network or paid calls.
"""

import copy
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "distilling-videos" / "scripts"
DISTILL = SCRIPTS / "distill.py"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402

HOSTILE = '<script>alert("x")</script><img src=x onerror=alert(1)>'


def transcript(video_id, lines, language="en"):
    segments = []
    for index, (text, english) in enumerate(lines):
        segments.append({"id": f"s{index + 1}", "start": index * 10.0, "end": index * 10.0 + 9.5,
                         "text": text, "english": english})
    return {"schema_version": 1, "video_id": video_id, "language": language,
            "provider": {"name": "fixture", "kind": "manual"}, "segments": segments}


def article(pub="g1"):
    return {
        "schema_version": 1, "publication_id": pub, "status": "complete",
        "title": "Why the cache lies " + HOSTILE,
        "dek": "Two talks disagree about *when* invalidation happens.",
        "sections": [
            {"id": "hook", "heading": "The surprising result", "blocks": [
                {"type": "p", "text": "The first talk claims writes invalidate eagerly [@c1]. "
                                      "The second shows a stale read on screen [@c2]. " + HOSTILE},
                {"type": "quote", "text": "writes invalidate eagerly", "cite": "c1"},
                {"type": "figure", "figure": "fig-capture"},
            ]},
            {"id": "mechanism", "heading": "One mechanism at a time", "blocks": [
                {"type": "list", "items": ["Read path `get()` [@c3]", "Write path **put** [@c2]"]},
                {"type": "figure", "figure": "fig-model"},
                {"type": "figure", "figure": "fig-demo"},
                {"type": "details", "summary": "Deeper: timing assumptions",
                 "blocks": [{"type": "p", "text": "The model assumes one writer [@c3]."}]},
            ]},
        ],
        "figures": [
            {"id": "fig-capture", "kind": "capture", "video_id": "v2", "frame_id": "f000012000",
             "alt": "Terminal showing a stale value", "caption": "The stale read appears " + HOSTILE},
            {"id": "fig-model", "kind": "original", "image": "figures/model.svg",
             "alt": "Timeline of a write and a read", "caption": "Our reconstruction of the race",
             "assumptions": ["One writer and one reader"], "sources": ["c1", "c2"]},
            {"id": "fig-demo", "kind": "sequence", "video_id": "v2", "caption": "The demo, step by step",
             "steps": [{"frame_id": "f000012000", "alt": "Before the write", "caption": "Before"},
                       {"frame_id": "f000015000", "alt": "After the write", "caption": "After"}]},
        ],
        "citations": [
            {"id": "c1", "video_id": "v1", "segment_ids": ["s1"]},
            {"id": "c2", "video_id": "v2", "segment_ids": ["s2"], "frame_id": "f000012000"},
            {"id": "c3", "kind": "web", "url": "https://example.org/docs?a=1&b=2", "title": "Cache docs " + HOSTILE,
             "publisher": "Example"},
        ],
        "brief": {
            "question": "When does invalidation happen?",
            "evidence": [
                {"id": "E1", "kind": "finding", "basis": "presenter", "text": "Writes are said to invalidate eagerly.",
                 "citations": ["c1"]},
                {"id": "E2", "kind": "finding", "basis": "screen", "text": "A stale read is visible.",
                 "citations": ["c2"]},
                {"id": "E3", "kind": "unknown", "basis": "screen", "text": "The exact cache TTL is unreadable."},
            ],
            "proposals": [
                {"id": "P1", "kind": "investigation", "text": "Reproduce the race with two clients.",
                 "basis": ["E1", "E2"]},
            ],
        },
        "limitations": ["Only two talks were examined."],
    }


SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'

FAKE_BROWSER = r'''
import os, sys
mode = os.environ.get("FAKE_BROWSER_MODE", "pdf")
with open(os.environ["FAKE_BROWSER_LOG"], "w") as handle:
    handle.write("\n".join(sys.argv[1:]))
out = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--print-to-pdf=")][0]
with open(out, "wb") as handle:
    handle.write(b"<html>not a pdf</html>" if mode == "html" else b"%PDF-1.7\n" + b"0" * 2048 + b"\n%%EOF\n")
'''


class PublicationFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ws = self.root / "ws"
        data = {"schema_version": 1, "groups": [{"id": "g1", "video_ids": ["v1", "v2"]}], "videos": [
            {"id": "v1", "url": "https://www.youtube.com/watch?v=abcdefghi01", "title": "Talk one " + HOSTILE},
            {"id": "v2", "url": "https://youtu.be/abcdefghi02", "title": "Talk two"},
            {"id": "v3", "url": "https://youtu.be/abcdefghi03", "title": "Talk three"}]}
        self.ok(self.cli("init", "--workspace", self.ws, "--assignment", self.write("assignment.json", data)))
        lines = {"v1": [("So writes invalidate eagerly, always.", "So writes invalidate eagerly, always."),
                        ("Then reads are cheap.", "Then reads are cheap.")],
                 "v2": [("Here is the setup.", "Here is the setup."),
                        ("Watch the stale value " + HOSTILE, "Watch the stale value " + HOSTILE)],
                 "v3": [("Unrelated.", "Unrelated.")]}
        for video_id, text in lines.items():
            path = self.write(f"{video_id}.json", transcript(video_id, text))
            self.ok(self.cli("import-transcript", "--workspace", self.ws, "--video", video_id,
                             "--transcript", path, "--duration", "30"))
        self.make_frames("v2", [12.0, 15.0])
        self.ok(self.cli("select-frames", "--workspace", self.ws, "--video", "v2",
                         "--frames", "f000012000,f000015000"))
        self.pub = self.ws / "publications" / "g1"
        (self.pub / "figures").mkdir()
        (self.pub / "figures" / "model.svg").write_text(SVG)
        self.write_article(article())

    def tearDown(self):
        self.tmp.cleanup()

    def make_frames(self, video_id, times):
        workspace = evidence.Workspace(self.ws)
        base = workspace.source_dir(video_id)
        frames = []
        for t in times:
            frame_id = f"f{int(t * 1000):09d}"
            for kind in ("full", "thumbs"):
                path = base / "frames" / kind / f"{frame_id}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"\xff\xd8fake-jpeg-" + frame_id.encode())
            frames.append({"id": frame_id, "t": t, "reasons": ["cue"], "path": f"frames/full/{frame_id}.jpg",
                           "thumbnail": f"frames/thumbs/{frame_id}.jpg"})
        evidence.atomic_write_json(base / "frames" / "frames.json", {
            "schema_version": 1, "video_id": video_id, "duration": 30.0, "max_sampling_gap_seconds": 12.0,
            "selection": {"semantic_completeness": False}, "frames": frames})
        outputs = evidence.file_digests(base, ["frames/frames.json"] + [f["path"] for f in frames]
                                        + [f["thumbnail"] for f in frames])
        evidence.mark_complete(workspace, evidence.stage_key(video_id, "frames"), {"fixture": 1}, {}, outputs)

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def write_article(self, data):
        (self.pub / "article.json").write_text(json.dumps(data, ensure_ascii=False))

    def cli(self, *args, env=None):
        environment = {"PATH": "/usr/bin:/bin", "HOME": str(self.root)}
        environment.update(env or {})
        return subprocess.run([sys.executable, str(DISTILL), *map(str, args)],
                              capture_output=True, text=True, env=environment)

    def ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout) if result.stdout.strip().startswith("{") else result

    def render(self, pub="g1"):
        return self.cli("render", "--workspace", self.ws, "--publication", pub)

    def assert_contract_error(self, result, pattern):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertRegex(result.stderr, pattern)

    def fake_browser(self, mode="pdf"):
        path = self.root / "fake-browser"
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(FAKE_BROWSER))
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = {"FAKE_BROWSER_MODE": mode, "FAKE_BROWSER_LOG": str(self.root / "browser.log")}
        return path, env

    def pdf(self, mode="pdf"):
        browser, env = self.fake_browser(mode)
        return self.cli("pdf", "--workspace", self.ws, "--publication", "g1", "--browser", browser, env=env)


class RenderSafety(PublicationFixture):
    def test_hostile_source_and_article_text_is_inert(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        for name in ("index.html", "brief.html"):
            page = (dist / name).read_text()
            self.assertNotIn("<script>alert", page)
            self.assertNotIn("<img src=x", page)
            self.assertIn("&lt;script&gt;alert", page)
            scripts = re.findall(r"<script[^>]*>", page)
            self.assertTrue(all("src=\"assets/" in tag for tag in scripts), scripts)
        index = (dist / "index.html").read_text()
        self.assertIn("https://example.org/docs?a=1&amp;b=2", index)
        markdown = (dist / "article.md").read_text()
        self.assertNotIn("<script>", markdown)

    def test_no_remote_assets_or_fetch(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        page = (dist / "index.html").read_text()
        for tag in re.findall(r"<(?:script|link|img|source|iframe)\b[^>]*>", page):
            self.assertNotRegex(tag, r"(?:src|href)=\"(?:https?:)?//", tag)
        self.assertIn("connect-src 'none'", page)
        self.assertNotRegex((dist / "assets" / "article.js").read_text(), r"\bfetch\(|XMLHttpRequest")
        self.assertTrue((dist / "assets" / "vendor" / "LICENSE-alpinejs.md").is_file())

    def test_unsafe_urls_and_paths_rejected(self):
        bad = article()
        bad["citations"][2]["url"] = "javascript:alert(1)"
        self.write_article(bad)
        self.assert_contract_error(self.render(), "http")
        for image in ("../../assignment.json", "/etc/passwd", "figures/../../plan.json"):
            bad = article()
            bad["figures"][1]["image"] = image
            self.write_article(bad)
            self.assert_contract_error(self.render(), "unsafe|figures/")
        self.assert_contract_error(self.render("../g1"), "safe ID")

    def test_svg_with_script_rejected(self):
        (self.pub / "figures" / "model.svg").write_text('<svg><script>alert(1)</script></svg>')
        self.assert_contract_error(self.render(), "SVG")


class RenderReferences(PublicationFixture):
    def test_missing_citation_and_image_targets(self):
        cases = [
            (lambda a: a["sections"][0]["blocks"][0].update(text="Claim [@nope]."), "nope"),
            (lambda a: a["figures"][0].update(frame_id="f000099000"), "f000099000"),
            (lambda a: a["citations"][0].update(segment_ids=["s99"]), "s99"),
            (lambda a: a["sections"][0]["blocks"][2].update(figure="fig-missing"), "fig-missing"),
        ]
        for change, pattern in cases:
            data = article()
            change(data)
            self.write_article(data)
            self.assert_contract_error(self.render(), pattern)
        (self.pub / "figures" / "model.svg").unlink()
        self.write_article(article())
        self.assert_contract_error(self.render(), "model.svg")

    def test_quotes_must_appear_in_cited_segments(self):
        data = article()
        data["sections"][0]["blocks"][1]["text"] = "writes never invalidate"
        self.write_article(data)
        self.assert_contract_error(self.render(), "quote")

    def test_stable_citations_resolve_to_timestamps(self):
        self.ok(self.render())
        index = (self.pub / "dist" / "index.html").read_text()
        self.assertIn('href="#ref-1"', index)
        self.assertIn('id="ref-1"', index)
        self.assertIn("https://www.youtube.com/watch?v=abcdefghi01&amp;t=0s", index)
        self.assertIn("https://www.youtube.com/watch?v=abcdefghi02&amp;t=10s", index)
        markdown = (self.pub / "dist" / "article.md").read_text()
        self.assertIn("[^1]:", markdown)
        self.assertIn("0:00:10", markdown)
        self.assertIn("media/v2/f000012000.jpg", markdown)
        self.assertTrue((self.pub / "dist" / "media" / "v2" / "f000012000.jpg").is_file())


class OptionalFieldTypes(PublicationFixture):
    def test_wrong_types_are_contract_errors_not_tracebacks(self):
        cases = [
            (lambda a: a["brief"]["proposals"][0].update(risks=5), r"risks"),
            (lambda a: a["brief"]["proposals"][0].update(risks=["Race may not reproduce"]), r"risks"),
            (lambda a: a["brief"]["proposals"][0].update(risks=" "), r"risks"),
            (lambda a: a["brief"].update(question=5), r"question"),
            (lambda a: a["brief"].update(question={"text": "q"}), r"question"),
            (lambda a: a["sections"][0]["blocks"][1].update(cite=["c1"]), r"cite"),
            (lambda a: a["sections"][0]["blocks"][1].update(cite=7), r"cite"),
            (lambda a: a["citations"][0].update(segment_ids="s1"), r"segment_ids"),
            (lambda a: a["citations"][1].update(segment_ids="s2"), r"segment_ids"),
            (lambda a: a["citations"][0].update(segment_ids=[1]), r"segment_ids"),
            (lambda a: a["citations"][0].update(segment_ids=[["s1"]]), r"segment_ids"),
            (lambda a: a["citations"][1].update(frame_id=["f000012000"]), r"frame_id"),
            (lambda a: a["citations"][0].update(note=3), r"note"),
            (lambda a: a["citations"][2].update(publisher=["Example"]), r"publisher"),
            (lambda a: a["figures"][1].update(sources=["c1", ["c2"]]), r"sources"),
            (lambda a: a["figures"][0].update(frame_id=["f000012000"]), r"frame_id"),
            (lambda a: a["figures"][2]["steps"][0].update(frame_id={"x": 1}), r"frame_id"),
            (lambda a: a["brief"]["evidence"][0].update(citations=[["c1"]]), r"citations"),
            (lambda a: a["brief"]["proposals"][0].update(basis=[["E1"]]), r"basis"),
            (lambda a: a["sections"][1]["blocks"][0].update(ordered="yes"), r"ordered"),
            (lambda a: a.update(status="partial", partial_reason=["frames"]), r"partial_reason"),
        ]
        for change, pattern in cases:
            data = article()
            change(data)
            self.write_article(data)
            result = self.render()
            self.assertNotIn("Traceback", result.stderr)
            self.assert_contract_error(result, pattern)

    def test_sequence_alt_is_per_step(self):
        data = article()
        data["figures"][2]["alt"] = "Figure-level alt is not part of the sequence contract"
        self.write_article(data)
        self.assert_contract_error(self.render(), r"figures\[2\] has unknown field\(s\) \['alt'\]")
        data = article()
        del data["figures"][2]["steps"][1]["alt"]
        self.write_article(data)
        self.assert_contract_error(self.render(), r"steps\[1\] is missing alt")


class CitationMarkers(PublicationFixture):
    def test_multiple_sources_render_one_separated_marker(self):
        data = article()
        data["brief"]["evidence"][0]["citations"] = ["c1", "c2"]
        self.write_article(data)
        self.ok(self.render())
        index = (self.pub / "dist" / "index.html").read_text()
        assumptions = re.search(r'<div class="assumptions"><p>Assumptions(.*?)</p>', index).group(1)
        self.assertEqual(assumptions.count("<sup"), 1, assumptions)
        self.assertRegex(assumptions, r'<sup class="cite"><a href="#ref-1">1</a>, <a href="#ref-2">2</a></sup>')
        brief = (self.pub / "dist" / "brief.html").read_text()
        item = re.search(r'<div role="listitem" id="E1">(.*?)</div></div></div>', brief).group(1)
        self.assertEqual(item.count("<sup"), 1, item)
        self.assertIn('<a href="#ref-1">1</a>, <a href="#ref-2">2</a></sup>', item)
        self.assertNotRegex(index + brief, r"</sup>\s*<sup")


class BriefSeparation(PublicationFixture):
    def test_brief_requires_explicit_evidence_and_proposals(self):
        cases = [
            (lambda a: a["brief"].pop("proposals"), "proposals"),
            (lambda a: a["brief"].pop("evidence"), "evidence"),
            (lambda a: a["brief"]["proposals"][0].update(citations=["c1"]), "unknown"),
            (lambda a: a["brief"]["proposals"][0].update(basis=["E9"]), "E9"),
            (lambda a: a["brief"]["proposals"][0].update(text="Do X [@c1]"), "basis"),
            (lambda a: a["brief"]["evidence"][0].update(citations=[]), "E1"),
            (lambda a: a["brief"]["evidence"][0].pop("basis"), "basis"),
        ]
        for change, pattern in cases:
            data = article()
            change(data)
            self.write_article(data)
            self.assert_contract_error(self.render(), pattern)

    def test_brief_renders_evidence_and_proposals_separately(self):
        self.ok(self.render())
        brief = (self.pub / "dist" / "brief.md").read_text()
        evidence_at, proposals_at = brief.index("## What the sources establish"), brief.index("## What we propose")
        self.assertLess(evidence_at, proposals_at)
        self.assertNotIn("Reproduce the race", brief[evidence_at:proposals_at])
        self.assertIn("Rests on: E1, E2", brief[proposals_at:])
        self.assertIn("Proposal, not evidence", brief[proposals_at:])
        self.assertIn("Open unknowns", brief[evidence_at:proposals_at])


class GroupedAttribution(PublicationFixture):
    def test_every_group_member_must_be_cited(self):
        data = article()
        data["citations"][1]["video_id"] = "v1"
        data["citations"][1].pop("frame_id")
        data["citations"][1]["segment_ids"] = ["s2"]
        self.write_article(data)
        self.assert_contract_error(self.render(), "v2.*never cited")

    def test_citation_outside_publication_rejected(self):
        data = article()
        data["citations"][0]["video_id"] = "v3"
        self.write_article(data)
        self.assert_contract_error(self.render(), "v3")

    def test_group_member_without_verified_evidence_blocks_render(self):
        segments = self.ws / "sources" / "v1" / "transcript" / "segments.json"
        segments.write_text(segments.read_text().replace("eagerly", "lazily"))
        self.assert_contract_error(self.render(), "checksum")

    def test_reels_attribute_each_source(self):
        result = self.ok(self.render())
        self.assertEqual(result["status"], "rendered")
        index = (self.pub / "dist" / "index.html").read_text()
        self.assertIn("Reel A", index)
        self.assertIn("Reel B", index)
        self.assertIn("Talk one &lt;script&gt;", index)
        self.assertIn("Talk two", index)
        coverage = json.loads((self.pub / "dist" / "coverage.json").read_text())
        self.assertEqual([s["video_id"] for s in coverage["sources"]], ["v1", "v2"])
        self.assertEqual({s["video_id"]: s["citations"] for s in coverage["sources"]}, {"v1": 1, "v2": 1})


class PdfCommand(PublicationFixture):
    def test_missing_browser_is_explicit(self):
        self.ok(self.render())
        result = self.cli("pdf", "--workspace", self.ws, "--publication", "g1", "--browser", self.root / "none")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("browser", result.stderr)
        self.assertFalse((self.pub / "dist" / "article.pdf").exists())

    def test_html_output_is_not_accepted_as_pdf(self):
        self.ok(self.render())
        result = self.pdf("html")
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertIn("not a PDF", result.stderr)
        self.assertFalse((self.pub / "dist" / "article.pdf").exists())

    def test_pdf_rendered_from_print_mode_offline(self):
        self.ok(self.render())
        result = self.ok(self.pdf())
        self.assertEqual(result["status"], "rendered")
        self.assertTrue((self.pub / "dist" / "article.pdf").read_bytes().startswith(b"%PDF-"))
        log = (self.root / "browser.log").read_text()
        self.assertIn("index.html?print=1", log)
        self.assertIn("--headless", log)


class Packaging(PublicationFixture):
    def package(self, *extra):
        return self.cli("package", "--workspace", self.ws, "--publication", "g1", *extra)

    def test_package_manifest_zip_and_exclusions(self):
        self.ok(self.render())
        self.ok(self.pdf())
        (self.ws / "sources" / "v2" / "media").mkdir()
        (self.ws / "sources" / "v2" / "media" / "source.mp4").write_bytes(b"raw media")
        result = self.ok(self.package())
        self.assertTrue(result["complete"])
        package = Path(result["package_dir"])
        manifest = json.loads((package / "manifest.json").read_text())
        paths = {f["path"] for f in manifest["files"]}
        for required in ("index.html", "article.md", "brief.md", "brief.html", "article.pdf", "coverage.json",
                         "article.json", "sources/v1/transcript/original.md", "sources/v1/transcript/english.md",
                         "sources/v1/transcript/segments.json", "sources/v2/transcript/english.md",
                         "sources/v2/frames/full/f000012000.jpg", "sources/v2/frames/thumbs/f000015000.jpg",
                         "assets/vendor/alpine-3.17.4.min.js"):
            self.assertIn(required, paths)
        self.assertFalse(any("/media/" in p and p.startswith("sources/") or "audio" in p for p in paths), paths)
        self.assertFalse(any(p.startswith("sources/v3") for p in paths))
        for entry in manifest["files"]:
            data = (package / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
            self.assertEqual(len(data), entry["bytes"])
        archive = Path(result["zip"])
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result["zip_sha256"])
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            self.assertIn("manifest.json", names)
            self.assertEqual(set(names), paths | {"manifest.json"})
            for name in names:
                self.assertFalse(name.startswith("/") or ".." in name.split("/"), name)
        self.assertEqual(manifest["revision"], result["revision"])
        again = self.ok(self.package())
        self.assertEqual(again["zip_sha256"], result["zip_sha256"])

    def test_package_requires_pdf_unless_explicitly_incomplete(self):
        self.ok(self.render())
        self.assert_contract_error(self.package(), "PDF")
        result = self.ok(self.package("--allow-missing-pdf"))
        self.assertFalse(result["complete"])
        manifest = json.loads((Path(result["package_dir"]) / "manifest.json").read_text())
        self.assertFalse(manifest["complete"])
        self.assertIn("pdf", " ".join(manifest["incomplete_reasons"]).lower())

    def test_stale_render_or_pdf_refused(self):
        self.ok(self.render())
        self.ok(self.pdf())
        self.ok(self.render())  # re-render discards the old PDF
        self.assert_contract_error(self.package(), "PDF")
        self.ok(self.pdf())
        english = self.ws / "sources" / "v2" / "transcript" / "english.md"
        english.write_text(english.read_text() + "\nedited")
        self.assert_contract_error(self.package(), "stale|checksum")

    def test_secret_bearing_content_refused(self):
        data = article()
        data["limitations"].append("Uploaded to https://acct.blob.core.windows.net/c?sv=2024-01-01&sig=AbCdEf0123456789xyz")
        self.write_article(data)
        self.ok(self.render())
        self.ok(self.pdf())
        self.assert_contract_error(self.package(), "secret")

    def test_partial_article_is_labeled(self):
        data = article()
        data["status"] = "partial"
        self.write_article(data)
        self.assert_contract_error(self.render(), "partial_reason")
        data["partial_reason"] = "The TTL value is unreadable in the source."
        self.write_article(data)
        self.ok(self.render())
        self.assertIn("Partial", (self.pub / "dist" / "index.html").read_text())
        self.ok(self.pdf())
        result = self.ok(self.package())
        self.assertFalse(result["complete"])


class SinglePublication(PublicationFixture):
    def test_single_video_publication(self):
        pub = self.ws / "publications" / "v3"
        data = copy.deepcopy(article("v3"))
        data["title"] = "A single talk"
        data["sections"] = [{"id": "only", "heading": "What it says",
                             "blocks": [{"type": "p", "text": "It is unrelated [@c1]."}]}]
        data["figures"] = []
        data["citations"] = [{"id": "c1", "video_id": "v3", "segment_ids": ["s1"]}]
        data["brief"] = {"evidence": [{"id": "E1", "kind": "finding", "basis": "presenter",
                                       "text": "Unrelated.", "citations": ["c1"]}], "proposals": []}
        (pub / "article.json").write_text(json.dumps(data))
        self.ok(self.render("v3"))
        self.assertIn("A single talk", (pub / "dist" / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()

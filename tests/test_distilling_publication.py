"""Contract tests for distilling-videos publication rendering and packaging.

Run: python3 -m unittest discover -s tests -p 'test_distilling_publication.py' -v
Evidence is built through the real CLI and evidence API; browsers are fake executables.
No network or paid calls.
"""

import copy
import html
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
        pages = sorted(p.name for p in dist.glob("*.html"))
        self.assertGreaterEqual(len(pages), 9, pages)
        for name in pages:
            page = (dist / name).read_text()
            self.assertNotIn("<script>alert", page)
            self.assertNotIn("<img src=x", page)
            self.assertIn("&lt;script&gt;alert", page)
            scripts = re.findall(r"<script[^>]*>", page)
            self.assertTrue(all("src=\"assets/" in tag for tag in scripts), scripts)
        index = (dist / "article.html").read_text()
        self.assertIn("https://example.org/docs?a=1&amp;b=2", index)
        markdown = (dist / "article.md").read_text()
        self.assertNotIn("<script>", markdown)

    def test_no_remote_assets_or_fetch(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        for path in dist.glob("*.html"):
            page = path.read_text()
            for tag in re.findall(r"<(?:script|link|img|source|iframe)\b[^>]*>", page):
                self.assertNotRegex(tag, r"(?:src|href)=\"(?:https?:)?//", tag)
            self.assertIn("connect-src 'none'", page)
        for script in ("article.js", "theme-init.js", "search-index.js", "vendor/gsap-3.15.0.min.js",
                       "vendor/alpine-3.17.4.min.js"):
            self.assertNotRegex((dist / "assets" / script).read_text(), r"\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket")
        self.assertTrue((dist / "assets" / "vendor" / "LICENSE-alpinejs.md").is_file())
        self.assertTrue((dist / "assets" / "vendor" / "LICENSE-gsap.md").is_file())

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
        index = (self.pub / "dist" / "article.html").read_text()
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
        # Required fields used for hash or set membership must be type-checked first.
        for bad in (["x"], {"x": 1}):
            cases += [
                (lambda a, b=bad: a["sections"][0]["blocks"][2].update(figure=b), r"\.figure must be"),
                (lambda a, b=bad: a["brief"]["evidence"][0].update(kind=b), r"evidence\[0\] kind must be"),
                (lambda a, b=bad: a["brief"]["evidence"][0].update(basis=b), r"evidence\[0\] basis must be"),
                (lambda a, b=bad: a["brief"]["evidence"][0].update(id=b), r"brief item id"),
                (lambda a, b=bad: a["brief"]["proposals"][0].update(kind=b), r"proposals\[0\] kind must be"),
                (lambda a, b=bad: a["brief"]["proposals"][0].update(id=b), r"brief item id"),
                (lambda a, b=bad: a["citations"][0].update(video_id=b), r"citations\[0\]\.video_id must be"),
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
        index = (self.pub / "dist" / "article.html").read_text()
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
        index = (self.pub / "dist" / "article.html").read_text()
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
        self.assertIn("article.html?print=1", log)
        self.assertNotIn("index.html", log)
        self.assertIn("--headless", log)
        record = json.loads((self.pub / "pdf.json").read_text())
        self.assertEqual(record["page"], "article.html")
        self.assertEqual(record["page_sha256"],
                         hashlib.sha256((self.pub / "dist" / "article.html").read_bytes()).hexdigest())


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
        dist_files = {p.relative_to(self.pub / "dist").as_posix() for p in (self.pub / "dist").rglob("*") if p.is_file()}
        self.assertLessEqual(dist_files, paths, "every rendered page, Markdown twin, and asset is packaged")
        for required in ("index.html", "index.md", "article.html", "article.md", "brief.md", "brief.html",
                         "transcripts.md", "transcript-v1.html", "transcript-v1.original.md", "gallery.md",
                         "glossary.md", "references.md", "assets/search-index.js", "assets/themes.css",
                         "assets/THEMES.md", "assets/vendor/gsap-3.15.0.min.js", "article.pdf", "coverage.json",
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


PAGES = ("index.html", "article.html", "brief.html", "transcripts.html", "transcript-v1.html",
         "transcript-v1.original.html", "transcript-v2.html", "transcript-v2.original.html", "gallery.html",
         "glossary.html", "references.html")
NAV_LABELS = ["Overview", "Article", "Brief", "Transcripts", "Gallery", "Glossary", "References"]


def embedded_markdown(page):
    match = re.search(r'<textarea id="page-markdown"[^>]*>(.*?)</textarea>', page, re.S)
    if not match:
        return None
    # As a browser parses a textarea: one leading newline is dropped, CR becomes LF, NUL becomes U+FFFD.
    value = html.unescape(match.group(1)).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd")
    return value[1:] if value.startswith("\n") else value


class SitePages(PublicationFixture):
    def test_every_page_has_nav_tools_and_its_full_markdown(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        self.assertEqual(sorted(p.name for p in dist.glob("*.html")), sorted(PAGES))
        for name in PAGES:
            page = (dist / name).read_text()
            nav = re.search(r'<ul class="nav-list">(.*?)</ul>', page).group(1)
            self.assertEqual(re.findall(r">([A-Za-z]+)</a>", nav), NAV_LABELS, name)
            self.assertEqual(nav.count('aria-current="page"'), 1, name)
            md_name = name[:-5] + ".md"
            self.assertIn(f'<a class="download-md" href="{md_name}" download>', page)
            self.assertIn('class="copy-page js-only"', page)
            self.assertIn('<span x-text="label">Copy Page</span>', page)
            self.assertIn('role="status" aria-live="polite"', page)
            self.assertEqual(embedded_markdown(page), (dist / md_name).read_text(encoding="utf-8"), name)
        self.assertIn("Start reading", (dist / "index.html").read_text())
        self.assertIn('id="s-hook"', (dist / "article.html").read_text())
        self.assertNotIn('id="s-hook"', (dist / "index.html").read_text())

    def test_transcript_pages_keep_every_segment(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        workspace = self.ws / "sources" / "v2" / "transcript"
        segments = json.loads((workspace / "segments.json").read_text())["segments"]
        english = (dist / "transcript-v2.html").read_text()
        original = (dist / "transcript-v2.original.html").read_text()
        for segment in segments:
            self.assertIn(f'id="seg-{segment["id"]}"', english)
            self.assertIn(html.escape(segment["english"]), english)
            self.assertIn(html.escape(segment["text"]), original)
        self.assertIn('lang="en"', original.split("<body", 1)[0])
        self.assertIn("Transcript gap", english)
        self.assertNotIn("<script>alert", english + original)
        # The Markdown twin is the verified evidence file, with frame links pointed at dist/media.
        evidence_md = (workspace / "english.md").read_text()
        twin = (dist / "transcript-v2.md").read_text()
        self.assertEqual(twin.replace("](media/v2/thumbs/", "](../frames/thumbs/")
                         .replace("](media/v2/f0", "](../frames/full/f0"), evidence_md + ("" if evidence_md.endswith("\n") else "\n"))
        for target in re.findall(r"\]\((media/[^)]+)\)", twin):
            self.assertTrue((dist / target).is_file(), target)

    def test_citation_evidence_templates_and_references_page(self):
        self.ok(self.render())
        dist = self.pub / "dist"
        article = (dist / "article.html").read_text()
        templates = re.findall(r'<template id="ev-(\d+)">(.*?)</template>', article, re.S)
        self.assertEqual([int(n) for n, _ in templates], list(range(1, len(templates) + 1)))
        first = templates[0][1]
        self.assertIn('href="transcript-v1.html#seg-s1"', first)
        self.assertIn("So writes invalidate eagerly", first)
        self.assertIn('href="#ref-1"', first)
        self.assertIn('id="evidence-panel"', article)
        self.assertNotIn("<script>alert", "".join(t for _, t in templates))
        references = (dist / "references.html").read_text()
        for anchor in ("src-v1", "src-v2", "cite-c1", "cite-c3", "credit-g-1"):
            self.assertIn(f'id="{anchor}"', references)
        self.assertIn("assets/vendor/LICENSE-gsap.md", references)
        gallery = (dist / "gallery.html").read_text()
        self.assertEqual(gallery.count('class="g-item'), 4)  # capture, two demo steps, original figure
        self.assertIn("untouched", gallery)
        self.assertIn("our reconstruction", gallery)

    def test_search_index_is_bundled_data(self):
        self.ok(self.render())
        script = (self.pub / "dist" / "assets" / "search-index.js").read_text()
        prefix = "window.DISTILL_SEARCH = "
        body = script.split(prefix, 1)[1].rstrip().rstrip(";")
        entries = json.loads(body)["entries"]
        hrefs = {e[0] for e in entries}
        self.assertIn("transcript-v2.html#seg-s2", hrefs)
        self.assertIn("article.html#s-mechanism", hrefs)
        self.assertIn("brief.html#E1", hrefs)
        self.assertTrue(any("stale value" in e[3] for e in entries))
        self.assertNotIn("</script", script)
        self.assertNotRegex(script, r"\bfetch\(|XMLHttpRequest")


class Glossary(PublicationFixture):
    def test_glossary_renders_short_cited_definitions(self):
        data = article()
        data["glossary"] = [{"term": "Stale read " + HOSTILE, "definition": "A read of an old value [@c2]."},
                            {"term": "Invalidation", "definition": "Removing a cached entry."}]
        self.write_article(data)
        self.ok(self.render())
        page = (self.pub / "dist" / "glossary.html").read_text()
        self.assertIn('id="term-invalidation"', page)
        self.assertIn("Stale read &lt;script&gt;", page)
        self.assertIn('<sup class="cite"><a href="#ref-1">1</a></sup>', page)
        self.assertIn('<template id="ev-1">', page)
        self.assertIn("[^1]", (self.pub / "dist" / "glossary.md").read_text())
        index = json.loads((self.pub / "dist" / "assets" / "search-index.js").read_text()
                           .split("= ", 1)[1].rstrip().rstrip(";"))
        self.assertIn("glossary.html#term-invalidation", {e[0] for e in index["entries"]})

    def test_glossary_contract_errors(self):
        cases = [
            ({"term": "X", "definition": "y" * 321}, r"320"),
            ({"term": "X", "definition": "Short [@nope]."}, r"nope"),
            ({"term": "X", "definition": "ok", "see": "Y"}, r"unknown field"),
            ({"term": 5, "definition": "ok"}, r"term"),
            ({"term": "X"}, r"definition"),
        ]
        for entry, pattern in cases:
            data = article()
            data["glossary"] = [entry]
            self.write_article(data)
            result = self.render()
            self.assertNotIn("Traceback", result.stderr)
            self.assert_contract_error(result, pattern)
        data = article()
        data["glossary"] = [{"term": "Cache", "definition": "a"}, {"term": " cache ", "definition": "b"}]
        self.write_article(data)
        self.assert_contract_error(self.render(), "duplicate glossary term")
        data["glossary"] = "Cache: a store"
        self.write_article(data)
        self.assert_contract_error(self.render(), "glossary must be a list")

    def test_absent_glossary_renders_an_honest_empty_page(self):
        self.ok(self.render())
        self.assertIn("No glossary terms were defined", (self.pub / "dist" / "glossary.html").read_text())


def references(page_html):
    """[(number, label)] from an HTML references list."""
    return [(int(n), html.unescape(label)) for n, label in
            re.findall(r'<li id="ref-(\d+)">(.*?)\. <a class="url"', page_html)]


def footnotes(markdown):
    """[(number, label)] from Markdown footnote definitions, unescaped to plain text."""
    return [(int(n), re.sub(r"\\(.)", r"\1", label)) for n, label in
            re.findall(r"^\[\^(\d+)\]: (.*)\. <[^>]+>$", markdown, re.M)]


class OptionalFieldCitations(PublicationFixture):
    """Citations in optional and secondary inline fields are validated, numbered, and resolvable."""

    def cited_everywhere(self):
        data = article()
        data["citations"].append({"id": "c4", "kind": "web", "url": "https://example.org/dek", "title": "Dek source"})
        data["citations"].append({"id": "c5", "kind": "web", "url": "https://example.org/limit", "title": "Limit"})
        data["dek"] = "Two talks disagree [@c4]."
        data["sections"][1]["heading"] = "One mechanism [@c3]"
        data["sections"][1]["blocks"][3]["summary"] = "Deeper: timing [@c1]"
        data["figures"][2]["steps"][1]["caption"] = "After [@c2]"
        data["limitations"] = ["Only two talks [@c5]."]
        data["brief"]["question"] = "When does invalidation happen [@c3]?"
        return data

    def test_dek_only_citation_is_number_one_with_a_working_anchor(self):
        self.write_article(self.cited_everywhere())
        self.ok(self.render())
        dist = self.pub / "dist"
        for name in ("index", "article", "brief"):
            page = (dist / f"{name}.html").read_text()
            dek = re.search(r'<p class="dek">(.*?)</p>', page).group(1)
            self.assertIn('<a href="#ref-1">1</a>', dek, name)
            self.assertEqual(references(page)[0], (1, "“Dek source”"), name)
            self.assertIn('<template id="ev-1">', page, name)
            markdown = (dist / f"{name}.md").read_text()
            self.assertIn("*Two talks disagree[^1].*", markdown, name)
            self.assertEqual(footnotes(markdown)[0], (1, "“Dek source”"), name)

    def test_html_and_markdown_number_citations_identically(self):
        data = self.cited_everywhere()
        data["glossary"] = [{"term": "Race", "definition": "Two writers [@c3] and a reader [@c1]."}]
        self.write_article(data)
        self.ok(self.render())
        dist = self.pub / "dist"
        for page_path in sorted(dist.glob("*.html")):
            page = page_path.read_text()
            markdown = (dist / (page_path.stem + ".md")).read_text()
            refs, notes = references(page), footnotes(markdown)
            self.assertEqual(refs, notes, page_path.name)
            self.assertEqual([n for n, _ in refs], list(range(1, len(refs) + 1)), page_path.name)
            used_html = {int(n) for n in re.findall(r'href="#ref-(\d+)"', page)}
            used_md = {int(n) for n in re.findall(r"\[\^(\d+)\](?!:)", markdown)}
            self.assertEqual(used_html, {n for n, _ in refs}, page_path.name)
            self.assertEqual(used_md, {n for n, _ in notes}, page_path.name)
        article_refs = [label for _, label in references((dist / "article.html").read_text())]
        self.assertEqual(article_refs[:2], ["“Dek source”", "Reel A — unknown creator, “Talk one "
                                                              + HOSTILE + "”, 0:00:00–0:00:09 (segments s1)"])
        self.assertEqual(article_refs[-1], "“Limit”")
        brief = [label for _, label in references((dist / "brief.html").read_text())]
        self.assertEqual(brief[:2], ["“Dek source”", "“Cache docs " + HOSTILE + "” — Example"])  # dek, then question

    def test_unknown_or_empty_citations_in_any_inline_field_are_contract_errors(self):
        cases = [
            (lambda a: a.update(dek="Dek [@nope]."), r"article\.dek references unknown citation 'nope'"),
            (lambda a: a["sections"][0].update(heading="H [@nope]"), r"sections\[0\]\.heading references unknown"),
            (lambda a: a.update(limitations=["L [@nope]"]), r"limitations\[0\] references unknown"),
            (lambda a: a["brief"].update(question="Q [@nope]?"), r"brief\.question references unknown"),
            (lambda a: a["sections"][1]["blocks"][3].update(summary="S [@nope]"), r"\.summary references unknown"),
            (lambda a: a["figures"][0].update(caption="C [@nope]"), r"figures\[0\]\.caption references unknown"),
            (lambda a: a["figures"][2]["steps"][0].update(caption="C [@nope]"), r"steps\[0\]\.caption references"),
            (lambda a: a["figures"][1].update(assumptions=["A [@nope]"]), r"assumptions\[0\] references unknown"),
            (lambda a: a.update(glossary=[{"term": "T", "definition": "D [@nope]."}]), r"glossary\[0\] references"),
            (lambda a: a["brief"]["evidence"][0].update(text="E [@nope]."), r"evidence\[0\] references unknown"),
            (lambda a: a.update(dek="Dek [@]."), r"article\.dek has an empty citation marker"),
            (lambda a: a["sections"][0]["blocks"][0].update(text="P [@ ; ]."), r"empty citation marker"),
        ]
        for change, pattern in cases:
            data = article()
            change(data)
            self.write_article(data)
            result = self.render()
            self.assertNotIn("Traceback", result.stderr)
            self.assert_contract_error(result, pattern)
            self.assertFalse((self.pub / "dist").exists(), pattern)


class MarkdownTwins(PublicationFixture):
    def test_carriage_returns_and_nul_are_normalized_in_the_twin_and_the_embedded_copy(self):
        data = article()
        data["sections"][0]["blocks"][0]["text"] = "Line one\r\nline two\rline three \x00 nul \x07 bell [@c1] [@c2]."
        self.write_article(data)
        self.ok(self.render())
        dist = self.pub / "dist"
        markdown = (dist / "article.md").read_bytes()
        self.assertNotIn(b"\r", markdown)
        self.assertNotIn(b"\x00", markdown)
        self.assertIn("Line one\nline two\nline three \ufffd nul \ufffd bell".encode(), markdown)
        for page_path in dist.glob("*.html"):
            page = page_path.read_text(encoding="utf-8")
            self.assertIn('aria-label="Markdown source of this page">\n', page)
            self.assertEqual(embedded_markdown(page), (dist / (page_path.stem + ".md")).read_text(encoding="utf-8"))
        data["limitations"] = ["Lone surrogate \ud800 here."]
        (self.pub / "article.json").write_text(json.dumps(data))  # ASCII JSON can carry a lone surrogate
        result = self.render()
        self.assertNotIn("Traceback", result.stderr)
        self.assert_contract_error(result, "surrogate")


class DraftPackage(PublicationFixture):
    def test_draft_package_without_pdf_does_not_link_the_missing_pdf(self):
        self.ok(self.render())
        self.assertIn('<a href="article.pdf">PDF</a>', (self.pub / "dist" / "article.html").read_text())
        result = self.ok(self.cli("package", "--workspace", self.ws, "--publication", "g1", "--allow-missing-pdf"))
        package = Path(result["package_dir"])
        self.assertFalse((package / "article.pdf").exists())
        for page_path in package.glob("*.html"):
            self.assertNotIn("article.pdf", page_path.read_text(), page_path.name)
        manifest = json.loads((package / "manifest.json").read_text())
        listed = {f["path"]: f["sha256"] for f in manifest["files"]}
        self.assertEqual(listed["article.html"], hashlib.sha256((package / "article.html").read_bytes()).hexdigest())
        with zipfile.ZipFile(result["zip"]) as bundle:
            self.assertNotIn(b"article.pdf", bundle.read("article.html"))
        self.ok(self.pdf())
        result = self.ok(self.cli("package", "--workspace", self.ws, "--publication", "g1"))
        self.assertTrue(result["complete"])
        self.assertIn('<a href="article.pdf">PDF</a>', (Path(result["package_dir"]) / "article.html").read_text())


class ProgressiveEnhancement(PublicationFixture):
    def test_enhanced_controls_and_saved_collapse_wait_for_the_initialized_shell(self):
        assets = SCRIPTS.parent / "assets"
        style = (assets / "article.css").read_text()
        self.assertIn("html:not(.ready) .js-only { display: none !important; }", style)
        self.assertNotRegex(style, r"\.js[ .]")  # html.js only means article.js ran, not that Alpine works
        self.assertRegex(style, r"\.ready \.site-nav \{ position: fixed")
        init = (assets / "theme-init.js").read_text()
        self.assertRegex(init, r'addEventListener\("load"[\s\S]*contains\("ready"\)[\s\S]*remove\("nav-collapsed"')
        script = (assets / "article.js").read_text()
        self.assertIn('root.classList.add("ready")', script)
        self.assertIn('label: "Copy Page"', script)
        # Alpine is loaded by article.js after the components exist, never directly by the page.
        self.assertIn('new URL("vendor/alpine-3.17.4.min.js", self)', script)
        self.assertTrue((assets / "vendor" / "alpine-3.17.4.min.js").is_file())
        self.assertNotIn("Copy page", script)
        self.ok(self.render())
        for page_path in (self.pub / "dist").glob("*.html"):
            page = page_path.read_text()
            self.assertNotIn("alpine", page.split("</head>")[0], page_path.name)
            self.assertIn('<script defer src="assets/article.js"></script>', page)


class LinkIntegrity(unittest.TestCase):
    def test_broken_local_links_and_anchors_are_reported(self):
        import publication
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.html").write_text('<p id="x"></p><a href="b.html#y">b</a><a href="#x">x</a>'
                                         '<a href="missing.md">m</a><a href="#nope">n</a><a href="https://e.org/">e</a>'
                                         '<a href="article.pdf">pdf</a><img src="../escape.png">')
            (root / "b.html").write_text('<p id="z"></p>')
            problems = publication.link_problems(root, ["a.html", "b.html"])
        joined = "\n".join(problems)
        self.assertIn("missing anchor: b.html#y", joined)
        self.assertIn("missing file: missing.md", joined)
        self.assertIn("missing anchor: #nope", joined)
        self.assertIn("outside the package: ../escape.png", joined)
        self.assertEqual(len(problems), 4, problems)

    def test_markdown_twin_links_are_checked(self):
        import publication
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.html").write_text('<p id="x"></p>')
            (root / "media").mkdir()
            (root / "media" / "f.jpg").write_bytes(b"x")
            (root / "a.md").write_text("[ok](a.html#x) ![f](media/f.jpg) <https://e.org/> [^1]\n"
                                       "Escaped text \\[not\\]\\(a link\\) stays text.\n"
                                       "[gone](missing.html) [bad](a.html#nope) ![up](../f.jpg)\n\n[^1]: Note.\n")
            problems = publication.link_problems(root, ["a.html", "a.md"])
        joined = "\n".join(problems)
        self.assertIn("a.md links to a missing file: missing.html", joined)
        self.assertIn("a.md links to a missing anchor: a.html#nope", joined)
        self.assertIn("a.md links outside the package: ../f.jpg", joined)
        self.assertEqual(len(problems), 3, problems)


class Themes(unittest.TestCase):
    FAMILIES = {"tokyo-night", "github", "catppuccin", "gruvbox", "nord", "dracula", "solarized", "one", "rose-pine",
                "kanagawa", "everforest", "ayu", "material", "night-owl", "monokai", "synthwave-84", "cobalt2",
                "palenight", "tomorrow", "zenburn"}

    def test_every_variant_meets_aa_contrast_and_adaptations_are_labeled(self):
        import themes
        resolved = themes.resolved()
        self.assertEqual({v["family"] for v in resolved} - {"house"}, self.FAMILIES)
        self.assertEqual(len({v["id"] for v in resolved}), len(resolved))
        css = themes.css()
        labels = dict(entry for _, entries in themes.options() for entry in entries)
        for variant in resolved:
            values = variant["values"]
            for ground, color in themes.grounds(values).items():
                for token in themes.TEXT_TOKENS:
                    ratio = themes.contrast(values[token], color)
                    self.assertGreaterEqual(ratio, 4.5, f"{variant['id']} {token} on {ground}: {ratio:.2f}")
            self.assertIn(f'html[data-theme="{variant["id"]}"]', css)
            self.assertEqual("(adapted)" in labels[variant["id"]], bool(variant["adaptations"]), variant["id"])
            for adaptation in variant["adaptations"]:
                self.assertEqual(adaptation["official"], variant["tokens"][adaptation["token"]][0].lower())
                self.assertNotEqual(adaptation["official"], adaptation["value"])
        self.assertFalse([v for v in resolved if v["family"] == "house" and v["adaptations"]])
        provenance = themes.provenance_md()
        for family in themes.FAMILIES.values():
            self.assertIn(f"## {family['name']}", provenance)
            self.assertTrue(family["source"] and family["license"])
        self.assertIn("Adapted muted: official #6272a4 (Comment)", provenance)

    def test_default_follows_system_and_print_is_house_light(self):
        import themes
        css = themes.css()
        house = dict(themes.resolve(next(v for v in themes.VARIANTS if v["id"] == "house-light"))[0])
        self.assertIn("prefers-color-scheme: dark", css)
        printed = css.split("@media print", 1)[1]
        self.assertIn(f"--paper: {house['bg']}", printed)
        self.assertIn("html[data-theme], html:not([data-theme])", printed)
        style = (SCRIPTS.parent / "assets" / "article.css").read_text()
        self.assertNotRegex(style, r"img[^{]*\{[^}]*\bfilter\s*:")

    def test_theme_storage_is_guarded(self):
        for name in ("theme-init.js", "article.js"):
            script = (SCRIPTS.parent / "assets" / name).read_text()
            for access in re.finditer(r"localStorage\.(?:get|set|remove)Item", script):
                before = script[:access.start()]
                self.assertGreater(before.count("try {"), before.count("catch ("), f"{name}: unguarded storage access")


class VendoredMotion(unittest.TestCase):
    def test_gsap_is_pinned_licensed_and_offline(self):
        vendor = SCRIPTS.parent / "assets" / "vendor"
        data = (vendor / "gsap-3.15.0.min.js").read_bytes()
        provenance = (vendor / "PROVENANCE.md").read_text()
        self.assertIn(hashlib.sha256(data).hexdigest(), provenance)
        self.assertTrue(data.startswith(b"/*!\n * GSAP 3.15.0"))
        self.assertIn(b"Subject to the terms at https://gsap.com/standard-license.", data[:400])
        self.assertIn("standard-license", (vendor / "LICENSE-gsap.md").read_text())
        self.assertNotRegex(data.decode(), r"\bfetch\(|XMLHttpRequest|sendBeacon")
        script = (SCRIPTS.parent / "assets" / "article.js").read_text()
        self.assertIn("!!window.gsap", script)
        self.assertIn("prefers-reduced-motion: reduce", script)
        self.assertNotIn("ScrollTrigger", script)


class PdfRecordCompatibility(PublicationFixture):
    def test_old_index_pdf_record_is_stale(self):
        self.ok(self.render())
        self.ok(self.pdf())
        record = json.loads((self.pub / "pdf.json").read_text())
        old = {"schema_version": 1, "index_sha256": hashlib.sha256((self.pub / "dist" / "index.html").read_bytes())
               .hexdigest(), "pdf_sha256": record["pdf_sha256"], "browser": "x", "pages": 1, "rendered_at": "t"}
        (self.pub / "pdf.json").write_text(json.dumps(old))
        result = self.cli("package", "--workspace", self.ws, "--publication", "g1")
        self.assert_contract_error(result, "PDF")


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

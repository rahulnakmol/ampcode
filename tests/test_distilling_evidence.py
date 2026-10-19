"""Contract tests for the distilling-videos evidence runtime.

Run: python3 -m unittest discover -s tests -p 'test_distilling_evidence.py' -v
External media tools are replaced by local fake executables; no network or paid calls.
"""

import copy
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "distilling-videos" / "scripts"
DISTILL = SCRIPTS / "distill.py"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402


def video(i):
    return {"id": f"v{i}", "url": f"https://www.youtube.com/watch?v=abcdefghi{i:02d}"}


def assignment(n=2, groups=None, budgets=None):
    data = {"schema_version": 1, "videos": [video(i) for i in range(n)], "groups": groups or []}
    if budgets is not None:
        data["budgets"] = budgets
    return data


FAKE_YTDLP = r'''
import json, sys
args = sys.argv[1:]
if args == ["--version"]:
    print("2026.01.01-fake"); sys.exit(0)
url = args[-1]
if "unavailable" in url:
    sys.stderr.write("ERROR: Video unavailable\n"); sys.exit(1)
if "--dump-single-json" in args:
    print(json.dumps({"id": url[-11:], "title": "Fake <b>title</b>", "uploader": "Fake Creator",
                      "duration": 95, "language": "en", "subtitles": {}, "automatic_captions": {"en": []}}))
    sys.exit(0)
template = args[args.index("-o") + 1]
with open(template.replace("%(ext)s", "mp4"), "wb") as handle:
    handle.write(b"fake-media:" + url.encode())
'''

FAKE_FFPROBE = r'''
import json, sys
if sys.argv[1:] == ["-version"]:
    print("ffprobe version fake"); sys.exit(0)
print(json.dumps({"format": {"duration": "95.0", "format_name": "mp4"},
                  "streams": [{"codec_type": "video", "width": 1920, "height": 1080},
                              {"codec_type": "audio"}]}))
'''

FAKE_FFMPEG = r'''
import os, sys
args = sys.argv[1:]
if args == ["-version"]:
    print("ffmpeg version fake"); sys.exit(0)
log = os.environ.get("FAKE_FFMPEG_LOG")
if log:
    with open(log, "a") as handle:
        handle.write(" ".join(args) + "\n")
if "null" in args:
    sys.stderr.write("[Parsed_showinfo_1] n:0 pts:1 pts_time:42.5 pos:1\n"); sys.exit(0)
for arg in args:
    if arg.endswith((".jpg", ".flac")):
        with open(arg, "wb") as handle:
            handle.write(("frame:" + " ".join(args)).encode())
'''


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ws = self.root / "ws"
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, name, body):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def all_tools(self):
        self.tool("yt-dlp", FAKE_YTDLP)
        self.tool("ffprobe", FAKE_FFPROBE)
        self.tool("ffmpeg", FAKE_FFMPEG)

    def write_json(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False))
        return path

    def cli(self, *args, env=None):
        environment = {"PATH": str(self.bin), "HOME": str(self.root)}
        environment.update(env or {})
        return subprocess.run([sys.executable, str(DISTILL), *map(str, args)],
                              capture_output=True, text=True, env=environment)

    def init(self, data=None):
        result = self.cli("init", "--workspace", self.ws,
                          "--assignment", self.write_json("assignment.json", data or assignment()))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def state(self):
        return json.loads((self.ws / "state.json").read_text())


class AssignmentContract(unittest.TestCase):
    def test_video_count_boundary(self):
        self.assertEqual(len(evidence.validate_assignment(assignment(10))["videos"]), 10)
        with self.assertRaisesRegex(evidence.ContractError, "at most 10"):
            evidence.validate_assignment(assignment(11))

    def test_group_size_boundary(self):
        five = assignment(6, [{"id": "g1", "video_ids": [f"v{i}" for i in range(5)]}])
        result = evidence.validate_assignment(five)
        self.assertEqual(sorted(p["id"] for p in result["publications"]), ["g1", "v5"])
        six = assignment(6, [{"id": "g1", "video_ids": [f"v{i}" for i in range(6)]}])
        with self.assertRaisesRegex(evidence.ContractError, "at most 5"):
            evidence.validate_assignment(six)

    def test_invalid_group_assignments(self):
        cases = {
            "unknown video": [{"id": "g1", "video_ids": ["v0", "missing"]}],
            "at least 2": [{"id": "g1", "video_ids": ["v0"]}],
            "video_ids": [{"id": "g1"}],
            "more than one group": [{"id": "g1", "video_ids": ["v0", "v1"]},
                                    {"id": "g2", "video_ids": ["v1", "v2"]}],
            "duplicate": [{"id": "g1", "video_ids": ["v0", "v0"]}],
            "collides": [{"id": "v2", "video_ids": ["v0", "v1"]}],
        }
        for message, groups in cases.items():
            with self.subTest(message), self.assertRaisesRegex(evidence.ContractError, message):
                evidence.validate_assignment(assignment(3, groups))

    def test_unsafe_ids_and_urls_rejected(self):
        for bad in ["../x", "a/b", ".", "..", "", "x" * 65, "café", "-lead", "a\\b", "a b"]:
            data = assignment(1)
            data["videos"][0]["id"] = bad
            with self.subTest(bad), self.assertRaises(evidence.ContractError):
                evidence.validate_assignment(data)
        for url in ["https://example.com/watch?v=abcdefghi01", "http://youtube.com/watch?v=abcdefghi01",
                    "https://user:pw@www.youtube.com/watch?v=abcdefghi01",
                    "https://www.youtube.com/watch?v=short", "file:///etc/passwd"]:
            data = assignment(1)
            data["videos"][0]["url"] = url
            with self.subTest(url), self.assertRaises(evidence.ContractError):
                evidence.validate_assignment(data)

    def test_schema_and_budget_validation(self):
        data = assignment(1)
        del data["schema_version"]
        with self.assertRaisesRegex(evidence.ContractError, "schema_version"):
            evidence.validate_assignment(data)
        with self.assertRaisesRegex(evidence.ContractError, "budget"):
            evidence.validate_assignment(assignment(1, budgets={"currency": "USD", "batch": -1}))
        with self.assertRaisesRegex(evidence.ContractError, "per_video"):
            evidence.validate_assignment(assignment(1, budgets={"currency": "USD", "batch": 1, "per_video": 2}))

    def test_safe_path_rejects_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(evidence.safe_path(root, "sources/v1/a.json"),
                             root.resolve() / "sources/v1/a.json")
            for bad in ["../x", "/etc/passwd", "sources/../../x", ""]:
                with self.subTest(bad), self.assertRaises(evidence.ContractError):
                    evidence.safe_path(root, bad)
            (root / "link").symlink_to(tempfile.gettempdir())
            with self.assertRaises(evidence.ContractError):
                evidence.safe_path(root, "link/file")


class InitAndResume(Fixture):
    def test_init_layout_and_compatible_resume(self):
        data = assignment(3, [{"id": "g1", "video_ids": ["v0", "v1"]}], {"currency": "USD", "batch": 5})
        self.init(data)
        for rel in ["assignment.json", "state.json", "sources/v0", "sources/v2",
                    "publications/g1/plan.json", "publications/v2/plan.json"]:
            self.assertTrue((self.ws / rel).exists(), rel)
        plan = json.loads((self.ws / "publications/g1/plan.json").read_text())
        self.assertEqual(plan["video_ids"], ["v0", "v1"])
        self.assertEqual(self.state()["schema_version"], 1)
        self.assertIn("resumed", self.init(data).stdout)

    def test_incompatible_resume_rejected_without_changes(self):
        self.init(assignment(2))
        before = (self.ws / "assignment.json").read_bytes()
        result = self.cli("init", "--workspace", self.ws,
                          "--assignment", self.write_json("other.json", assignment(3)))
        self.assertEqual(result.returncode, 2)
        self.assertIn("incompatible", result.stderr)
        self.assertEqual((self.ws / "assignment.json").read_bytes(), before)

    def test_cli_rejects_unsafe_id_without_writing(self):
        data = assignment(1)
        data["videos"][0]["id"] = "../escape"
        result = self.cli("init", "--workspace", self.ws, "--assignment", self.write_json("bad.json", data))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.ws.exists())
        self.assertFalse((self.root / "escape").exists())


def transcript(language="en", **overrides):
    segments = [
        {"id": "s1", "start": 0.0, "end": 4.5, "text": "  Hello <script>alert(1)</script> world  ",
         "english": "Hello <script>alert(1)</script> world"},
        {"id": "s2", "start": 4.5, "end": 9.0, "text": "Run `npm i` [inaudible] then\nretry",
         "english": "Run `npm i` [inaudible] then retry", "uncertain": True,
         "uncertainty": "command partly inaudible"},
        {"id": "s3", "start": 60.0, "end": 95.0, "text": "# not a heading — ünïcode 😀",
         "english": "# not a heading — unicode 😀", "confidence": 0.62},
    ]
    data = {"schema_version": 1, "video_id": "v0", "language": language,
            "provider": {"name": "manual-fixture", "kind": "manual"}, "segments": segments}
    data.update(overrides)
    return data


class TranscriptImport(Fixture):
    def import_transcript(self, data, name="t.json"):
        return self.cli("import-transcript", "--workspace", self.ws, "--video", "v0",
                        "--transcript", self.write_json(name, data), "--duration", "95")

    def test_preserves_content_markers_and_renders_markdown(self):
        self.init()
        data = transcript()
        result = self.import_transcript(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        stored = json.loads((self.ws / "sources/v0/transcript/segments.json").read_text())
        for original, saved in zip(data["segments"], stored["segments"]):
            self.assertEqual(saved["text"], original["text"])
            self.assertEqual(saved["english"], original["english"])
        self.assertTrue(stored["segments"][1]["uncertain"])
        self.assertEqual(stored["segments"][1]["uncertainty"], "command partly inaudible")
        self.assertEqual(stored["segments"][1]["inline_markers"], ["[inaudible]"])
        self.assertEqual(stored["segments"][2]["confidence"], 0.62)
        english = (self.ws / "sources/v0/transcript/english.md").read_text()
        self.assertNotIn("<script>", english)
        self.assertIn("https://www.youtube.com/watch?v=abcdefghi00&t=60s", english)
        self.assertIn("Uncertain", english)
        coverage = json.loads((self.ws / "sources/v0/transcript/coverage.json").read_text())
        self.assertEqual(coverage["gaps"], [{"start": 9.0, "end": 60.0}])
        self.assertEqual(coverage["uncertain_segment_ids"], ["s2"])

    def test_non_english_requires_translation_label(self):
        self.init()
        data = transcript("ja")
        data["segments"][0]["english_kind"] = "original"
        self.assertEqual(self.import_transcript(data).returncode, 2)
        del data["segments"][0]["english_kind"]
        self.assertEqual(self.import_transcript(data).returncode, 0)
        english = (self.ws / "sources/v0/transcript/english.md").read_text()
        self.assertIn("translation", english.lower())

    def test_rejects_order_range_and_content_loss(self):
        self.init()
        mutations = {
            "out of order": lambda s: s.reverse(),
            "end must exceed start": lambda s: s[0].update(end=0.0),
            "negative": lambda s: s[0].update(start=-1.0),
            "beyond duration": lambda s: s[2].update(end=200.0),
            "duplicate segment": lambda s: s[1].update(id="s1"),
            "english": lambda s: s[1].pop("english"),
            "text": lambda s: s[1].update(text="   "),
            "unknown field": lambda s: s[0].update(summary="lossy"),
            "overlap": lambda s: s[1].update(start=3.0),
        }
        for message, mutate in mutations.items():
            data = copy.deepcopy(transcript())
            mutate(data["segments"])
            with self.subTest(message):
                result = self.import_transcript(data)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stderr)
        self.assertFalse((self.ws / "sources/v0/transcript/segments.json").exists())

    def test_reuse_requires_matching_checksums(self):
        self.init()
        self.assertEqual(self.import_transcript(transcript()).returncode, 0)
        self.assertIn("reused", self.import_transcript(transcript()).stdout)
        segments = self.ws / "sources/v0/transcript/segments.json"
        segments.write_text(segments.read_text().replace("Hello", "Hullo"))
        report = self.cli("validate", "--workspace", self.ws)
        self.assertEqual(report.returncode, 1)
        self.assertIn("checksum", report.stdout)
        rerun = self.import_transcript(transcript())
        self.assertIn("imported", rerun.stdout)
        self.assertIn("Hello", segments.read_text())
        changed = transcript()
        changed["segments"][0]["english"] = "Changed"
        self.assertIn("imported", self.import_transcript(changed, "t2.json").stdout)
        self.assertEqual(self.cli("validate", "--workspace", self.ws).returncode, 0)


class MediaCommands(Fixture):
    def test_download_missing_tool_is_resumable(self):
        self.init()
        result = self.cli("download", "--workspace", self.ws, "--video", "v0")
        self.assertEqual(result.returncode, 3)
        self.assertIn("yt-dlp", result.stderr)
        self.assertEqual(self.state()["stages"]["sources/v0/download"]["status"], "failed")
        self.all_tools()
        result = self.cli("download", "--workspace", self.ws, "--video", "v0")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.state()["stages"]["sources/v0/download"]
        self.assertEqual(record["status"], "complete")
        self.assertIn("media/source.mp4", record["outputs"])
        self.assertIn("audio/audio.flac", record["outputs"])
        self.assertIn("sources/v0/media/source.mp4", self.state()["temporary_media"])
        source = json.loads((self.ws / "sources/v0/source.json").read_text())
        self.assertEqual(source["title"], "Fake <b>title</b>")
        self.assertEqual(source["duration"], 95.0)
        self.assertIn("yt-dlp", source["tool_versions"])
        self.assertIn("reused", self.cli("download", "--workspace", self.ws, "--video", "v0").stdout)
        (self.ws / "sources/v0/media/source.mp4").write_bytes(b"truncated")
        self.assertIn("downloaded", self.cli("download", "--workspace", self.ws, "--video", "v0").stdout)

    def test_inaccessible_download_fails_without_complete_state(self):
        data = assignment(1)
        data["videos"][0]["url"] = "https://youtu.be/unavailable"
        self.all_tools()
        self.init(data)
        result = self.cli("download", "--workspace", self.ws, "--video", "v0")
        self.assertEqual(result.returncode, 5)
        self.assertIn("Video unavailable", result.stderr)
        self.assertEqual(self.state()["stages"]["sources/v0/download"]["status"], "failed")
        self.assertFalse((self.ws / "sources/v0/media/source.mp4").exists())

    def test_frames_periodic_dense_cap_and_selection(self):
        self.all_tools()
        self.init()
        self.assertEqual(self.cli("download", "--workspace", self.ws, "--video", "v0").returncode, 0)
        over = self.cli("frames", "--workspace", self.ws, "--video", "v0", "--interval", "1",
                        "--max-frames", "10")
        self.assertEqual(over.returncode, 2)
        self.assertIn("max-frames", over.stderr)
        result = self.cli("frames", "--workspace", self.ws, "--video", "v0", "--interval", "30",
                          "--dense", "10-12:1", "--at", "61.25", "--scene-threshold", "0.3")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.ws / "sources/v0/frames/frames.json").read_text())
        times = [f["t"] for f in manifest["frames"]]
        self.assertEqual(times, [0.0, 10.0, 11.0, 12.0, 30.0, 42.5, 60.0, 61.25, 90.0])
        self.assertFalse(manifest["selection"]["semantic_completeness"])
        self.assertIn("scene", manifest["frames"][5]["reasons"])
        for frame in manifest["frames"]:
            self.assertTrue((self.ws / "sources/v0" / frame["path"]).exists())
            self.assertTrue((self.ws / "sources/v0" / frame["thumbnail"]).exists())
        self.assertIn("reused", self.cli("frames", "--workspace", self.ws, "--video", "v0", "--interval", "30",
                                         "--dense", "10-12:1", "--at", "61.25",
                                         "--scene-threshold", "0.3").stdout)
        self.assertEqual(self.cli("import-transcript", "--workspace", self.ws, "--video", "v0",
                                  "--transcript", self.write_json("t.json", transcript())).returncode, 0)
        bad = self.cli("select-frames", "--workspace", self.ws, "--video", "v0", "--frames", "nope")
        self.assertEqual(bad.returncode, 2)
        frame_id = manifest["frames"][6]["id"]
        chosen = self.cli("select-frames", "--workspace", self.ws, "--video", "v0", "--frames", frame_id)
        self.assertEqual(chosen.returncode, 0, chosen.stderr)
        english = (self.ws / "sources/v0/transcript/english.md").read_text()
        self.assertIn(f"[![Frame at 0:01:00](../frames/thumbs/{frame_id}.jpg)]"
                      f"(https://www.youtube.com/watch?v=abcdefghi00&t=60s)", english)
        self.assertIn(f"../frames/full/{frame_id}.jpg", english)
        self.assertEqual(self.cli("validate", "--workspace", self.ws, "--require-complete",
                                  "--video", "v0").returncode, 0)

    def test_validate_require_complete_reports_missing_stages(self):
        self.init()
        report = self.cli("validate", "--workspace", self.ws, "--require-complete")
        self.assertEqual(report.returncode, 1)
        self.assertIn("transcript", report.stdout)


class BudgetLedger(Fixture):
    def reserve(self, amount, video_id="v0", step="transcription"):
        args = ["budget", "reserve", "--workspace", self.ws, "--step", step, "--provider", "acme",
                "--amount", amount, "--approval", "user-approved-cap-2026-10-19"]
        if video_id:
            args += ["--video", video_id]
        return self.cli(*args)

    def test_requires_ceilings(self):
        self.init(assignment(1))
        result = self.reserve("0.5")
        self.assertEqual(result.returncode, 4)
        self.assertIn("ceiling", result.stderr)

    def test_reservation_settlement_and_release(self):
        self.init(assignment(2, budgets={"currency": "USD", "batch": 3, "per_video": 2}))
        first = self.reserve("1.5")
        self.assertEqual(first.returncode, 0, first.stderr)
        reservation = json.loads(first.stdout)["id"]
        self.assertEqual(self.reserve("0.6").returncode, 4)
        self.assertEqual(self.reserve("1.5", "v1").returncode, 0)
        self.assertEqual(self.reserve("0.1", None, "synthesis").returncode, 4)
        settled = self.cli("budget", "settle", "--workspace", self.ws, "--id", reservation,
                           "--actual", "1.75", "--basis", "provider-invoice")
        self.assertEqual(settled.returncode, 0, settled.stderr)
        self.assertTrue(json.loads(settled.stdout)["overrun"])
        self.assertEqual(self.reserve("0.3").returncode, 4)
        self.assertEqual(self.reserve("0.25").returncode, 4)  # batch: 1.75 + 1.5 already 3.25
        release = self.cli("budget", "release", "--workspace", self.ws, "--id", "r0002")
        self.assertEqual(release.returncode, 0, release.stderr)
        self.assertEqual(self.reserve("0.25").returncode, 0)
        status = json.loads(self.cli("budget", "status", "--workspace", self.ws).stdout)
        self.assertEqual(status["committed"]["batch"], 2.0)
        self.assertFalse(status["guarantees_all_in_spend"])

    def test_concurrent_reservations_cannot_overcommit(self):
        self.init(assignment(1, budgets={"currency": "USD", "batch": 5}))
        args = [sys.executable, str(DISTILL), "budget", "reserve", "--workspace", str(self.ws),
                "--step", "t", "--provider", "acme", "--amount", "1", "--approval", "ok", "--video", "v0"]
        procs = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(12)]
        codes = [p.wait() for p in procs]
        for p in procs:
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(codes.count(0), 5)
        self.assertEqual(codes.count(4), 7)


class Extensions(unittest.TestCase):
    def test_optional_modules_register_commands(self):
        import distill
        with tempfile.TemporaryDirectory() as tmp:
            parser = distill.build_parser(Path(tmp))
            self.assertEqual(parser.parse_args(["validate", "--workspace", "w"]).command, "validate")
            Path(tmp, "publication.py").write_text(textwrap.dedent('''
                def register(subparsers):
                    sub = subparsers.add_parser("render")
                    sub.set_defaults(func=lambda args: 0)
            '''))
            self.assertEqual(distill.build_parser(Path(tmp)).parse_args(["render"]).command, "render")
            Path(tmp, "archive.py").write_text("VALUE = 1\n")
            with self.assertRaisesRegex(RuntimeError, "register"):
                distill.build_parser(Path(tmp))


if __name__ == "__main__":
    unittest.main()

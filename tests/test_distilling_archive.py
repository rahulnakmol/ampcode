"""Contract tests for distilling-videos quality sign-off, archival, verification, and cleanup.

Run: python3 -m unittest discover -s tests -p 'test_distilling_archive.py' -v
Evidence is built through the real CLI with fake media tools and a fake browser. Azure Blob is
replaced by an in-process fake transport injected into command handlers, so no network, Azure
writes, or credentials are used.
"""

import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "distilling-videos" / "scripts"
DISTILL = SCRIPTS / "distill.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import distill  # noqa: E402
import evidence  # noqa: E402
from test_distilling_publication import DEPTH  # noqa: E402  realistic prose above the narrative floor

CONTAINER = "https://acct.blob.core.windows.net/distilled"
SIGNATURE = "TopSecretSignatureValue0123456789abcdef%3D"
SAS = f"sv=2022-11-02&sr=c&sp=rc&spr=https&se=2026-12-01T00%3A00%3A00Z&sig={SIGNATURE}"

FAKE_FFPROBE = r'''
import json, sys
if sys.argv[1:] == ["-version"]:
    print("ffprobe version fake"); sys.exit(0)
print(json.dumps({"format": {"duration": "60.0"}, "streams": [{"codec_type": "video", "width": 640,
                  "height": 360}, {"codec_type": "audio"}]}))
'''

FAKE_FFMPEG = r'''
import sys
args = sys.argv[1:]
if args == ["-version"]:
    print("ffmpeg version fake"); sys.exit(0)
for arg in args:
    if arg.endswith((".jpg", ".flac")):
        with open(arg, "wb") as handle:
            handle.write(b"\xff\xd8" + " ".join(args).encode())
'''

FAKE_BROWSER = r'''
import sys
out = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--print-to-pdf=")][0]
with open(out, "wb") as handle:
    handle.write(b"%PDF-1.7\n" + b"0" * 2048 + b"\n%%EOF\n")
'''


def transcript(start_gap=0.0):
    segments = []
    t = start_gap
    for index in range(6):
        end = min(60.0, t + 10.0)
        segments.append({"id": f"s{index + 1}", "start": t, "end": end, "text": f"Line {index + 1} of the talk.",
                         "english": f"Line {index + 1} of the talk."})
        t = end
        if t >= 60.0:
            break
    segments[1]["uncertain"] = True
    segments[1]["uncertainty"] = "fast speech"
    return {"schema_version": 1, "video_id": "v1", "language": "en",
            "provider": {"name": "fixture", "kind": "manual"}, "segments": segments}


def article(status="complete"):
    data = {
        "schema_version": 1, "publication_id": "v1", "status": status, "title": "A talk",
        "dek": "What the talk shows.",
        "sections": [{"id": "hook", "heading": "The claim", "blocks": [
            {"type": "p", "text": "The speaker states line one [@c1]."},
            {"type": "figure", "figure": "fig1"}]},
            {"id": "depth", "heading": "Why the claim matters", "blocks": [{"type": "p", "text": t} for t in DEPTH]}],
        "figures": [{"id": "fig1", "kind": "capture", "video_id": "v1", "frame_id": "f000020000",
                     "alt": "A frame", "caption": "The screen"}],
        "citations": [{"id": "c1", "video_id": "v1", "segment_ids": ["s1"], "frame_id": "f000020000"}],
        "brief": {"evidence": [{"id": "E1", "kind": "finding", "basis": "presenter", "text": "Line one.",
                                "citations": ["c1"]}], "proposals": []},
        "limitations": ["One talk."],
    }
    if status == "partial":
        data["partial_reason"] = "Segment s2 is unresolved."
    return data


class FakeBlob:
    """In-process Azure Blob double: create-only PUT, GET, and injectable faults."""

    def __init__(self):
        self.objects = {}
        self.calls = []
        self.fail_put = None
        self.corrupt_get = None
        self.redirect = False
        self.raise_error = False
        self.error_body = False

    def request(self, method, host, target, headers, body):
        self.calls.append({"method": method, "host": host, "target": target, "headers": dict(headers)})
        path, _, query = target.partition("?")
        container, name = path.lstrip("/").split("/", 1)
        name = unquote(name)
        if self.raise_error:
            raise OSError(f"connection reset by peer while requesting https://{host}{target}")
        if self.redirect:
            return 307, {"Location": f"https://evil.example/{name}?{query}"}, b""
        if self.error_body:
            return 403, {"x-ms-error-code": "AuthenticationFailed"}, f"<Error>{target}</Error>".encode()
        if method == "PUT":
            if self.fail_put and self.fail_put in name:
                return 500, {"x-ms-error-code": "InternalError"}, b""
            if headers.get("If-None-Match") != "*":
                return 400, {"x-ms-error-code": "MissingCreateOnly"}, b""
            if name in self.objects:
                return 409, {"x-ms-error-code": "BlobAlreadyExists"}, b""
            if base64.b64encode(hashlib.md5(body).digest()).decode() != headers.get("Content-MD5"):
                return 400, {"x-ms-error-code": "Md5Mismatch"}, b""
            self.objects[name] = bytes(body)
            return 201, {}, b""
        if method == "GET":
            if name not in self.objects:
                return 404, {"x-ms-error-code": "BlobNotFound"}, b""
            data = self.objects[name]
            if self.corrupt_get and self.corrupt_get in name:
                data = data[:-1] + bytes([data[-1] ^ 1])
            return 200, {}, data
        return 405, {}, b""

    def methods(self):
        return {call["method"] for call in self.calls}


class ArchiveFixture(unittest.TestCase):
    template = None

    @classmethod
    def setUpClass(cls):
        cls.class_tmp = tempfile.TemporaryDirectory()
        base = Path(cls.class_tmp.name)
        cls.template = base / "template"
        cls.build_workspace(base, cls.template, transcript())

    @classmethod
    def tearDownClass(cls):
        cls.class_tmp.cleanup()

    @classmethod
    def tool(cls, bin_dir, name, body):
        path = bin_dir / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    @classmethod
    def cli_at(cls, base, *args):
        env = {"PATH": str(base / "bin") + ":/usr/bin:/bin", "HOME": str(base)}
        result = subprocess.run([sys.executable, str(DISTILL), *map(str, args)], capture_output=True, text=True,
                                env=env)
        if result.returncode != 0:
            raise AssertionError(f"{args[0]} failed: {result.stderr}{result.stdout}")
        return json.loads(result.stdout) if result.stdout.strip().startswith("{") else None

    @classmethod
    def build_workspace(cls, base, ws, transcript_data, status="complete", download=True, frames=True,
                        youtube="abcdefghi01"):
        bin_dir = base / "bin"
        if not bin_dir.exists():
            bin_dir.mkdir()
            cls.tool(bin_dir, "ffprobe", FAKE_FFPROBE)
            cls.tool(bin_dir, "ffmpeg", FAKE_FFMPEG)
            cls.tool(bin_dir, "fake-browser", FAKE_BROWSER)
        files = base / f"inputs-{ws.name}"
        files.mkdir()
        (files / "assignment.json").write_text(json.dumps({"schema_version": 1, "videos": [
            {"id": "v1", "url": f"https://youtu.be/{youtube}", "title": "Talk"}]}))
        (files / "media.mp4").write_bytes(b"fake media bytes " + youtube.encode())
        (files / "transcript.json").write_text(json.dumps(transcript_data))
        cls.cli_at(base, "init", "--workspace", ws, "--assignment", files / "assignment.json")
        if download:
            cls.cli_at(base, "download", "--workspace", ws, "--video", "v1", "--from-file", files / "media.mp4")
            if frames:
                cls.cli_at(base, "frames", "--workspace", ws, "--video", "v1", "--interval", "20")
                cls.cli_at(base, "select-frames", "--workspace", ws, "--video", "v1", "--frames", "f000020000")
            cls.cli_at(base, "import-transcript", "--workspace", ws, "--video", "v1", "--transcript",
                       files / "transcript.json")
        else:
            cls.cli_at(base, "import-transcript", "--workspace", ws, "--video", "v1", "--transcript",
                       files / "transcript.json", "--duration", "60")
        data = article(status)
        if not frames:
            data["figures"] = []
            data["sections"][0]["blocks"] = data["sections"][0]["blocks"][:1]
            del data["citations"][0]["frame_id"]
        (ws / "publications" / "v1" / "article.json").write_text(json.dumps(data))
        cls.cli_at(base, "render", "--workspace", ws, "--publication", "v1")
        cls.cli_at(base, "pdf", "--workspace", ws, "--publication", "v1", "--browser", bin_dir / "fake-browser")
        return cls.cli_at(base, "package", "--workspace", ws, "--publication", "v1")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ws = self.root / "ws"
        shutil.copytree(self.template, self.ws, symlinks=True)
        self.pub = self.ws / "publications" / "v1"
        self.src = self.ws / "sources" / "v1"
        self.blob = FakeBlob()

    def tearDown(self):
        self.tmp.cleanup()

    # -- helpers -----------------------------------------------------------

    def call(self, *argv, transport=None, sas=SAS):
        """Run a registered command in-process with an injected transport; returns (code, out, err)."""
        args = distill.build_parser().parse_args([str(a) for a in argv])
        args.transport = transport if transport is not None else self.blob
        out, err = io.StringIO(), io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "DISTILL_ARCHIVE_SAS"}
        if sas is not None:
            env["DISTILL_ARCHIVE_SAS"] = sas
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            try:
                code = int(args.func(args) or 0)
            except evidence.ContractError as error:
                print("error: " + "\n  ".join(error.problems), file=sys.stderr)
                code = 2
        text = out.getvalue()
        return code, (json.loads(text) if text.strip().startswith("{") else text), err.getvalue()

    def ok(self, *argv, **kwargs):
        code, out, err = self.call(*argv, **kwargs)
        self.assertEqual(code, 0, f"{err}{out}")
        return out

    def refused(self, pattern, *argv, code=2, **kwargs):
        actual, out, err = self.call(*argv, **kwargs)
        self.assertEqual(actual, code, f"{err}{out}")
        self.assertRegex(err + json.dumps(out), pattern)
        return out, err

    def review(self, ws=None, **video_overrides):
        ws = ws or self.ws
        coverage = json.loads((ws / "sources" / "v1" / "transcript" / "coverage.json").read_text())
        video = {"transcript_coverage": "verified", "visual_coverage": "verified",
                 "gaps": [{"start": g["start"], "end": g["end"], "resolution": "no-speech",
                           "note": "music only"} for g in coverage["gaps"]],
                 "uncertain_segments": [{"segment_id": s, "resolution": "labeled", "note": "kept as uncertain"}
                                        for s in coverage["uncertain_segment_ids"]]}
        video.update(video_overrides)
        return {"schema_version": 1, "publication_id": "v1", "reviewer": "amp thread T-test",
                "decision": "approve", "note": "Coverage reviewed against frames and transcript.",
                "videos": {"v1": video}}

    def signoff(self, review=None, ws=None, expect=0):
        ws = ws or self.ws
        path = self.root / f"review-{ws.name}.json"
        path.write_text(json.dumps(review or self.review(ws)))
        code, out, err = self.call("signoff", "--workspace", ws, "--publication", "v1", "--review", path)
        self.assertEqual(code, expect, f"{err}{out}")
        return out

    def archive(self, ws=None, **kwargs):
        return self.ok("archive", "--workspace", ws or self.ws, "--publication", "v1", "--container", CONTAINER,
                       **kwargs)

    def cleanup(self, *extra, ws=None, **kwargs):
        return self.call("cleanup", "--workspace", ws or self.ws, "--video", "v1", "--container", CONTAINER,
                         *extra, **kwargs)

    def media(self, ws=None):
        base = (ws or self.ws) / "sources" / "v1"
        return [base / "media" / "source.mp4", base / "audio" / "audio.flac"]

    def all_text(self, result):
        return json.dumps(result) + "".join(self.blob.objects.get(k, b"").decode(errors="replace")
                                            for k in self.blob.objects if k.endswith(".json"))


class CommandRegistration(ArchiveFixture):
    def test_commands_registered_by_distill(self):
        result = subprocess.run([sys.executable, str(DISTILL), "--help"], capture_output=True, text=True)
        for name in ("signoff", "archive", "verify-archive", "cleanup", "unpack-artifact", "actions-provenance"):
            self.assertIn(name, result.stdout)

    def test_missing_sas_and_unsafe_destinations_rejected(self):
        self.refused("DISTILL_ARCHIVE_SAS", "archive", "--workspace", self.ws, "--publication", "v1",
                     "--container", CONTAINER, sas=None)
        for url in ("http://acct.blob.core.windows.net/distilled", "https://evil.example/distilled",
                    "https://acct.blob.core.windows.net.evil.example/distilled",
                    "https://user:pw@acct.blob.core.windows.net/distilled",
                    "https://acct.blob.core.windows.net:8443/distilled",
                    "https://acct.blob.core.windows.net/distilled?sig=abc",
                    "https://acct.blob.core.windows.net/distilled/sub",
                    "https://acct.blob.core.windows.net/Bad_Name"):
            self.refused("container", "archive", "--workspace", self.ws, "--publication", "v1", "--container", url)
        self.assertEqual(self.blob.calls, [])

    def test_production_transport_is_verified_https(self):
        import archive
        import ssl
        client = archive.BlobClient(CONTAINER, SAS, None, write=True)
        self.assertIsInstance(client.transport, archive.HttpsTransport)
        self.assertTrue(client.transport.context.check_hostname)
        self.assertEqual(client.transport.context.verify_mode, ssl.CERT_REQUIRED)

    def test_sas_must_be_https_only_without_delete(self):
        for bad in ("sv=1&sp=rc&se=2026-12-01&sig=x" + "y" * 20,                     # no spr
                    "sv=1&sp=rc&spr=https,http&se=2026-12-01&sig=" + "y" * 20,
                    "sv=1&sp=rcd&spr=https&se=2026-12-01&sig=" + "y" * 20,
                    "sv=1&sp=rc&spr=https&sig=" + "y" * 20,                              # no expiry
                    "sv=1&sp=rc&spr=https&se=2026-12-01"):                               # no signature
            out, err = self.refused("SAS", "archive", "--workspace", self.ws, "--publication", "v1",
                                    "--container", CONTAINER, sas=bad)
            self.assertNotIn("y" * 20, err + json.dumps(out))
        self.assertEqual(self.blob.calls, [])


class QualitySignoff(ArchiveFixture):
    def test_full_review_approves_and_binds_current_evidence(self):
        result = self.signoff()
        self.assertEqual(result["status"], "approved")
        record = json.loads((self.pub / "signoff.json").read_text())
        manifest = self.pub / "package" / "manifest.json"
        self.assertEqual(record["manifest_sha256"], evidence.sha256_file(manifest))
        self.assertEqual(set(record["videos"]["v1"]["media"]),
                         {"sources/v1/media/source.mp4", "sources/v1/audio/audio.flac"})
        self.assertIn("download", record["videos"]["v1"]["stages"])

    def test_unresolved_uncertainty_or_unverified_coverage_blocks(self):
        review = self.review(uncertain_segments=[{"segment_id": "s2", "resolution": "unresolved",
                                                  "note": "cannot hear"}])
        self.assertRegex(json.dumps(self.signoff(review, expect=1)["blockers"]), "s2")
        review = self.review(visual_coverage="unverified")
        self.assertRegex(json.dumps(self.signoff(review, expect=1)["blockers"]), "visual coverage")
        review = self.review()
        review["videos"]["v1"]["uncertain_segments"] = []
        self.assertRegex(json.dumps(self.signoff(review, expect=1)["blockers"]), "s2")
        self.assertEqual(json.loads((self.pub / "signoff.json").read_text())["status"], "blocked")

    def test_review_contract_errors(self):
        review = self.review()
        review["extra"] = True
        path = self.root / "bad.json"
        path.write_text(json.dumps(review))
        self.refused("unknown", "signoff", "--workspace", self.ws, "--publication", "v1", "--review", path)
        review = self.review(gaps=[{"start": 1.0, "end": 9.0, "resolution": "no-speech", "note": "x"}])
        path.write_text(json.dumps(review))
        self.refused("not a transcript gap", "signoff", "--workspace", self.ws, "--publication", "v1",
                     "--review", path)

    def test_changed_evidence_after_package_refused(self):
        (self.src / "transcript" / "english.md").write_text("tampered")
        path = self.root / "review.json"
        path.write_text(json.dumps(self.review()))
        self.refused("stale|changed|mismatch", "signoff", "--workspace", self.ws, "--publication", "v1",
                     "--review", path)


class PartialCoverage(ArchiveFixture):
    def test_gaps_missing_download_and_frames_block_signoff(self):
        base = self.root
        gappy = base / "gappy"
        self.build_workspace(base, gappy, transcript(start_gap=5.0))
        review = self.review(gappy)
        review["videos"]["v1"]["gaps"][0]["resolution"] = "unresolved"
        self.assertRegex(json.dumps(self.signoff(review, ws=gappy, expect=1)["blockers"]), "gap 0")
        self.assertEqual(self.signoff(self.review(gappy), ws=gappy)["status"], "approved")

        bare = base / "bare"
        self.build_workspace(base, bare, transcript(), download=False, frames=False)
        blockers = json.dumps(self.signoff(self.review(bare), ws=bare, expect=1)["blockers"])
        self.assertIn("download", blockers)
        self.assertIn("frame", blockers)

    def test_partial_package_archives_but_never_cleans(self):
        part = self.root / "part"
        self.build_workspace(self.root, part, transcript(), status="partial")
        self.signoff(self.review(part), ws=part, expect=1)
        result = self.archive(ws=part)
        self.assertEqual(result["quality"]["status"], "partial")
        self.assertFalse(result["cleanup_eligible"])
        self.refused("partial|not approved", "cleanup", "--workspace", part, "--video", "v1",
                     "--container", CONTAINER)
        self.assertTrue(all(p.exists() for p in self.media(part)))


class TranscriptProviderSignoff(ArchiveFixture):
    """Captions and agent transcripts need audio checks covering every spoken segment before media is released."""

    def provider_workspace(self, kind):
        ws = self.root / f"ws-{kind}"
        data = transcript()
        data["provider"] = {"name": f"fixture-{kind}", "kind": kind}
        self.build_workspace(self.root, ws, data)
        return ws

    @staticmethod
    def audio_check(**overrides):
        check = {"start": 0.0, "end": 20.0, "segment_ids": ["s1", "s2"], "result": "matches",
                 "note": "Listened at 1x; words match the segment text."}
        check.update(overrides)
        return {"method": "listened-to-source-audio", "checks": [check],
                "note": "Spot check of the opening; the rest was not compared."}

    @staticmethod
    def full_audio_check():
        """Two overlapping checks whose union covers every transcript segment (0-60 s)."""
        checks = [{"start": 0.0, "end": 35.0, "segment_ids": ["s1", "s2", "s3", "s4"], "result": "matches",
                   "note": "Listened at 1x."},
                  {"start": 30.0, "end": 60.0, "segment_ids": ["s4", "s5", "s6"], "result": "matches",
                   "note": "Listened at 1x."}]
        return {"method": "listened-to-source-audio", "checks": checks,
                "note": "Listened to the whole talk against the transcript."}

    def test_signoff_records_provider_kind(self):
        self.signoff()
        signed = json.loads((self.pub / "signoff.json").read_text())["videos"]["v1"]
        self.assertEqual(signed["transcript_provider"], {"name": "fixture", "kind": "manual"})
        self.assertIsNone(signed["audio_verification"])

    def test_captions_and_agent_transcripts_block_without_audio_verification(self):
        for kind in ("captions", "agent"):
            ws = self.provider_workspace(kind)
            blockers = json.dumps(self.signoff(self.review(ws), ws=ws, expect=1)["blockers"])
            self.assertRegex(blockers, f"{kind}.*audio verification")
            signed = json.loads((ws / "publications" / "v1" / "signoff.json").read_text())
            self.assertEqual(signed["videos"]["v1"]["transcript_provider"]["kind"], kind)

    def test_audio_verification_is_recorded_as_spans_not_accuracy(self):
        ws = self.provider_workspace("captions")
        differs = self.review(ws, audio_verification=self.audio_check(result="differs"))
        self.assertRegex(json.dumps(self.signoff(differs, ws=ws, expect=1)["blockers"]), "differ")
        # A short spot check is recorded for the report but cannot approve sign-off.
        result = self.signoff(self.review(ws, audio_verification=self.audio_check()), ws=ws, expect=1)
        self.assertEqual(result["status"], "blocked")
        self.assertRegex(json.dumps(result["blockers"]), r"4 of 6 transcript segments unchecked.*every spoken")
        recorded = json.loads((ws / "publications" / "v1" / "signoff.json").read_text())
        audio = recorded["videos"]["v1"]["audio_verification"]
        self.assertEqual(audio["checked_seconds"], 20.0)
        self.assertAlmostEqual(audio["checked_fraction"], 20.0 / 60.0, places=3)
        self.assertEqual(audio["unchecked_segment_ids"], ["s3", "s4", "s5", "s6"])
        self.assertRegex(audio["limits"], "not .*accuracy")
        self.assertEqual(audio["checks"][0]["segment_ids"], ["s1", "s2"])
        self.assertNotIn("accurate", json.dumps(audio))
        # Merged checks covering every spoken segment approve.
        result = self.signoff(self.review(ws, audio_verification=self.full_audio_check()), ws=ws)
        self.assertEqual(result["status"], "approved")
        audio = json.loads((ws / "publications" / "v1" / "signoff.json").read_text())["videos"]["v1"][
            "audio_verification"]
        self.assertEqual((audio["checked_seconds"], audio["unchecked_segment_ids"]), (60.0, []))

    def test_audio_verification_contract_errors(self):
        ws = self.provider_workspace("agent")
        path = self.root / "review-bad.json"
        bad_checks = [{"segment_ids": "s1"}, {"segment_ids": [1]}, {"segment_ids": []},
                      {"segment_ids": ["s99"]}, {"start": 30.0, "end": 20.0}, {"end": 75.0},
                      {"result": "verified"}, {"note": ""}, {"extra": 1}, {"start": "0"},
                      {"start": float("nan")}, {"end": float("nan")}, {"end": float("inf")},
                      {"start": float("-inf")}, {"result": ["matches"]}, {"result": {"x": 1}}]
        for overrides in bad_checks:
            review = self.review(ws, audio_verification=self.audio_check(**overrides))
            path.write_text(json.dumps(review))
            self.refused("audio_verification", "signoff", "--workspace", ws, "--publication", "v1",
                         "--review", path)
        for audio in ({"method": "trust-me", "checks": [], "note": "x"}, {**self.audio_check(), "method": ["x"]},
                      {**self.audio_check(), "checks": []}, {**self.audio_check(), "verified": True}, True):
            path.write_text(json.dumps(self.review(ws, audio_verification=audio)))
            self.refused("audio_verification", "signoff", "--workspace", ws, "--publication", "v1",
                         "--review", path)

    def test_cleanup_refuses_signoff_without_provider_or_audio_evidence(self):
        import archive
        ws = self.provider_workspace("captions")
        self.signoff(self.review(ws, audio_verification=self.full_audio_check()), ws=ws)
        self.archive(ws=ws)
        pub = ws / "publications" / "v1"
        workspace = evidence.Workspace(ws)
        receipt = json.loads((pub / "archive-receipt.json").read_text())
        signoff = json.loads((pub / "signoff.json").read_text())
        state = workspace.state()
        self.assertEqual(len(archive._plan_video(workspace, state, "v1", receipt, signoff)), 2)
        for mutate in (lambda v: v.pop("transcript_provider"),
                       lambda v: v.update(transcript_provider={"name": "fixture-captions", "kind": "manual"}),
                       lambda v: v.update(audio_verification=None),
                       lambda v: v["audio_verification"]["checks"][0].update(result="differs"),
                       lambda v: v["audio_verification"]["checks"].pop(),
                       lambda v: v["audio_verification"]["checks"][1].update(end=float("nan")),
                       lambda v: v["audio_verification"]["checks"][1].update(end=["60"])):
            forged = copy.deepcopy(signoff)
            mutate(forged["videos"]["v1"])
            with self.assertRaisesRegex(evidence.ContractError, "provider|audio"):
                archive._plan_video(workspace, state, "v1", receipt, forged)


class Archival(ArchiveFixture):
    def test_upload_verify_and_final_marker(self):
        self.signoff()
        result = self.archive()
        self.assertEqual(result["status"], "archived")
        self.assertEqual(result["quality"]["status"], "approved")
        self.assertTrue(result["cleanup_eligible"])
        puts = [c for c in self.blob.calls if c["method"] == "PUT"]
        self.assertTrue(puts[-1]["target"].split("?")[0].endswith("/_COMPLETE.json"))
        self.assertIn("/publications/v1/", puts[-1]["target"])
        self.assertEqual(self.blob.methods(), {"PUT", "GET"})
        self.assertTrue(all(c["host"] == "acct.blob.core.windows.net" for c in self.blob.calls))
        self.assertTrue(all(c["headers"].get("If-None-Match") == "*" for c in puts))
        names = set(self.blob.objects)
        manifest = json.loads((self.pub / "package" / "manifest.json").read_text())
        revision = manifest["revision"]
        zips = [n for n in names if n.endswith(f"v1-{revision}.zip")]
        self.assertEqual(len(zips), 1)
        self.assertTrue(any(n.startswith("videos/v1/evidence/") and n.endswith("/files/transcript/segments.json")
                            for n in names))
        self.assertTrue(any(n.startswith(f"publications/v1/{revision}/") and n.endswith("/files/index.html")
                            for n in names))
        for entry in manifest["files"]:
            path = entry["path"]
            rel = path.split("/", 2)[2] if path.startswith("sources/") else path
            prefix = "videos/v1/evidence/" if path.startswith("sources/") else f"publications/v1/{revision}/"
            matches = [n for n in names if n.startswith(prefix) and n.endswith("/files/" + rel)]
            self.assertTrue(matches, entry["path"])
        receipt = json.loads((self.pub / "archive-receipt.json").read_text())
        self.assertEqual(receipt["container_url"], CONTAINER)
        self.assertEqual(receipt["marker"]["manifest_sha256"], evidence.sha256_file(self.pub / "package" /
                                                                                   "manifest.json"))
        self.assertNotIn(SIGNATURE, self.all_text(result) + json.dumps(receipt))
        self.assertNotIn("sig=", json.dumps(receipt))
        verified = self.ok("verify-archive", "--workspace", self.ws, "--publication", "v1",
                           "--container", CONTAINER)
        self.assertTrue(verified["ok"])

    def test_readable_local_zip_archives_under_canonical_name(self):
        revision = json.loads((self.pub / "package" / "manifest.json").read_text())["revision"]
        readable = self.pub / "a-talk.zip"
        self.assertTrue(readable.is_file())
        self.assertFalse((self.pub / f"v1-{revision}.zip").exists())
        # A stale ZIP from another revision on the readable name must not be chosen or block archival.
        readable.rename(self.pub / f"a-talk-{revision[:8]}.zip")
        readable.write_bytes(b"older revision bytes")
        self.signoff()
        result = self.archive()
        self.assertEqual(result["status"], "archived")
        local = evidence.sha256_file(self.pub / f"a-talk-{revision[:8]}.zip")
        receipt = json.loads((self.pub / "archive-receipt.json").read_text())
        self.assertEqual(receipt["marker"]["zip"]["sha256"], local)
        self.assertTrue(receipt["marker"]["zip"]["blob"].endswith(f"/v1-{revision}.zip"))

    def test_legacy_revision_zip_name_still_archives(self):
        revision = json.loads((self.pub / "package" / "manifest.json").read_text())["revision"]
        (self.pub / "a-talk.zip").rename(self.pub / f"v1-{revision}.zip")
        self.signoff()
        self.assertEqual(self.archive()["status"], "archived")

    def test_zip_object_size_boundary_checked_before_upload(self):
        zip_path = self.pub / "a-talk.zip"
        # Store entries without compression so the ZIP, not an individual member, hits the limit.
        with zipfile.ZipFile(zip_path) as bundle:
            entries = [(info.filename, bundle.read(info)) for info in bundle.infolist()]
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name, data in entries:
                bundle.writestr(name, data)
        size = zip_path.stat().st_size
        argv = ["archive", "--workspace", str(self.ws), "--publication", "v1", "--container", CONTAINER]
        # Extensions are freshly imported by build_parser; patch the registered handler's module.
        parser = distill.build_parser()
        module_globals = parser.parse_args(argv).func.__globals__
        for limit, expected_code in ((size - 1, 2), (size, 0), (size + 1, 0)):
            with self.subTest(limit=limit), mock.patch.dict(module_globals, MAX_OBJECT_BYTES=limit,
                                                           MAX_PACKAGE_BYTES=size * 4), \
                    mock.patch.object(distill, "build_parser", return_value=parser):
                blob = FakeBlob()
                code, out, err = self.call(*argv, transport=blob)
                if expected_code == 2:
                    self.assertEqual(blob.calls, [], f"oversized ZIP reached transport: {err}")
                    self.assertFalse((self.pub / "archive-receipt.json").exists())
                    self.assertRegex(err, r"\.zip.*exceeds.*limit")
                else:
                    self.assertEqual(out["status"], "archived", err)
                    self.assertTrue(any(name.endswith("_COMPLETE.json") for name in blob.objects))
                self.assertEqual(code, expected_code, err)

    def test_unique_revision_prefix_per_attempt(self):
        self.archive()
        first = {n for n in self.blob.objects if n.endswith("_COMPLETE.json")}
        self.archive()
        second = {n for n in self.blob.objects if n.endswith("_COMPLETE.json")}
        self.assertEqual(len(second), 2 * len(first))

    def test_incomplete_upload_never_writes_marker_or_receipt(self):
        self.blob.fail_put = "segments.json"
        code, out, err = self.call("archive", "--workspace", self.ws, "--publication", "v1",
                                   "--container", CONTAINER)
        self.assertEqual(code, 5, err)
        self.assertFalse(any(n.endswith("_COMPLETE.json") for n in self.blob.objects))
        self.assertFalse((self.pub / "archive-receipt.json").exists())
        self.assertIn("InternalError", err)

    def test_corrupted_read_back_never_writes_marker(self):
        self.blob.corrupt_get = "index.html"
        code, out, err = self.call("archive", "--workspace", self.ws, "--publication", "v1",
                                   "--container", CONTAINER)
        self.assertEqual(code, 5, err)
        self.assertRegex(err, "index.html")
        self.assertFalse(any(n.endswith("_COMPLETE.json") for n in self.blob.objects))
        self.assertFalse((self.pub / "archive-receipt.json").exists())

    def test_corrupted_remote_object_fails_verification(self):
        self.archive()
        self.blob.corrupt_get = "brief.html"
        code, out, err = self.call("verify-archive", "--workspace", self.ws, "--publication", "v1",
                                   "--container", CONTAINER)
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertRegex(json.dumps(out["errors"]), "brief.html")

    def test_sas_never_leaks_on_errors_or_redirects(self):
        for fault in ("raise_error", "redirect", "error_body"):
            blob = FakeBlob()
            setattr(blob, fault, True)
            code, out, err = self.call("archive", "--workspace", self.ws, "--publication", "v1",
                                       "--container", CONTAINER, transport=blob)
            self.assertEqual(code, 5, fault)
            self.assertNotIn(SIGNATURE, err + str(out), fault)
            self.assertNotIn("TopSecret", err + str(out), fault)
            self.assertTrue(all(c["host"] == "acct.blob.core.windows.net" for c in blob.calls), fault)
            self.assertEqual(len(blob.calls), 1, f"{fault}: retried or followed a redirect")
        self.assertFalse((self.pub / "archive-receipt.json").exists())

    def test_changed_local_package_refused(self):
        (self.pub / "package" / "index.html").write_text("tampered")
        self.refused("checksum|mismatch", "archive", "--workspace", self.ws, "--publication", "v1",
                     "--container", CONTAINER)
        shutil.rmtree(self.ws)
        shutil.copytree(self.template, self.ws, symlinks=True)
        manifest = json.loads((self.pub / "package" / "manifest.json").read_text())
        manifest["complete"] = True
        manifest["files"] = manifest["files"][1:]
        (self.pub / "package" / "manifest.json").write_text(json.dumps(manifest))
        self.refused("revision|unlisted|ZIP", "archive", "--workspace", self.ws, "--publication", "v1",
                     "--container", CONTAINER)
        self.assertEqual(self.blob.calls, [])

    def test_stale_signoff_refused(self):
        self.signoff()
        record = json.loads((self.pub / "signoff.json").read_text())
        record["manifest_sha256"] = "0" * 64
        (self.pub / "signoff.json").write_text(json.dumps(record))
        self.refused("signoff", "archive", "--workspace", self.ws, "--publication", "v1", "--container", CONTAINER)

    def test_symlinked_package_file_refused(self):
        target = self.pub / "package" / "brief.md"
        outside = self.root / "outside.md"
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
        self.refused("symlink", "archive", "--workspace", self.ws, "--publication", "v1", "--container", CONTAINER)


class Cleanup(ArchiveFixture):
    def approved_archive(self):
        self.signoff()
        return self.archive()

    def test_cleanup_deletes_only_tracked_media_after_verified_signoff(self):
        self.approved_archive()
        before = {p for p in self.ws.rglob("*") if p.is_file()}
        dry = self.cleanup("--dry-run")
        self.assertEqual(dry[0], 0, dry[2])
        self.assertTrue(all(p.exists() for p in self.media()))
        code, out, err = self.cleanup()
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(out["deleted"]), ["sources/v1/audio/audio.flac", "sources/v1/media/source.mp4"])
        after = {p for p in self.ws.rglob("*") if p.is_file()}
        self.assertEqual({p.relative_to(self.ws).as_posix() for p in before - after},
                         {"sources/v1/audio/audio.flac", "sources/v1/media/source.mp4"})
        self.assertTrue((self.pub / "package" / "manifest.json").exists())
        self.assertEqual(self.blob.methods(), {"PUT", "GET"})
        state = json.loads((self.ws / "state.json").read_text())
        self.assertEqual(state["temporary_media"], [])
        validate = subprocess.run([sys.executable, str(DISTILL), "validate", "--workspace", str(self.ws),
                                   "--require-complete"], capture_output=True, text=True)
        self.assertEqual(validate.returncode, 0, validate.stdout)
        again = self.cleanup()
        self.assertEqual(again[0], 0, again[2])
        self.assertEqual(again[1]["videos"]["v1"]["status"], "already-clean")

    def test_refused_without_receipt_or_approved_signoff(self):
        self.refused("receipt", "cleanup", "--workspace", self.ws, "--video", "v1", "--container", CONTAINER)
        self.archive()  # unsigned archive
        self.refused("unsigned|not approved", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        review = self.review(transcript_coverage="unverified")
        self.signoff(review, expect=1)
        self.archive()
        self.refused("blocked|not approved", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_retain_media_honored(self):
        self.approved_archive()
        assignment = json.loads((self.ws / "assignment.json").read_text())
        assignment["retain_media"] = True
        (self.ws / "assignment.json").write_text(json.dumps(assignment))
        state = json.loads((self.ws / "state.json").read_text())
        state["assignment_sha256"] = evidence.digest_json(evidence.validate_assignment(assignment))
        (self.ws / "state.json").write_text(json.dumps(state))
        code, out, err = self.cleanup()
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "retained")
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_receipt_from_other_workspace_same_video_id_refused(self):
        other = self.root / "other"
        self.build_workspace(self.root, other, transcript(start_gap=5.0), youtube="zzzzzzzzz99")
        self.signoff(self.review(other), ws=other)
        self.archive(ws=other)
        shutil.copyfile(other / "publications" / "v1" / "archive-receipt.json", self.pub / "archive-receipt.json")
        self.signoff()
        out, err = self.refused("signoff|evidence", *(["cleanup", "--workspace", self.ws, "--video", "v1",
                                                      "--container", CONTAINER]))
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_evidence_changed_after_archive_refused(self):
        self.approved_archive()
        segments = self.src / "transcript" / "coverage.json"
        data = json.loads(segments.read_text())
        data["warnings"] = ["edited"]
        segments.write_text(json.dumps(data))
        self.refused("changed|mismatch|stale", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_media_changed_after_signoff_refused(self):
        self.approved_archive()
        self.media()[0].write_bytes(b"different media")
        self.refused("media|mismatch|changed", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        self.assertTrue(self.media()[1].exists())

    def test_remote_corruption_or_wrong_container_refused(self):
        self.approved_archive()
        self.blob.corrupt_get = "segments.json"
        self.refused("segments.json", "cleanup", "--workspace", self.ws, "--video", "v1", "--container", CONTAINER)
        self.blob.corrupt_get = None
        self.refused("container", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", "https://other.blob.core.windows.net/distilled")
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_tampered_receipt_refused(self):
        self.approved_archive()
        path = self.pub / "archive-receipt.json"
        receipt = json.loads(path.read_text())
        receipt["marker"]["quality"]["status"] = "approved"
        receipt["marker"]["videos"]["v1"]["files"]["transcript/english.md"]["sha256"] = "0" * 64
        path.write_text(json.dumps(receipt))
        self.refused("marker|receipt|mismatch", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        receipt = json.loads(path.read_text())
        receipt["marker"]["videos"]["v1"]["files"]["transcript/english.md"]["sha256"] = \
            evidence.sha256_file(self.src / "transcript" / "english.md")
        receipt["marker"]["archived_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(receipt))
        self.refused("differs from the remote", "cleanup", "--workspace", self.ws, "--video", "v1",
                     "--container", CONTAINER)
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_signed_media_paths_limited_to_tracked_temporary_media(self):
        import archive
        self.approved_archive()
        workspace = evidence.Workspace(self.ws)
        receipt = json.loads((self.pub / "archive-receipt.json").read_text())
        signoff = json.loads((self.pub / "signoff.json").read_text())
        state = workspace.state()
        self.assertEqual(len(archive._plan_video(workspace, state, "v1", receipt, signoff)), 2)
        for bad in ("publications/v1/package/manifest.json", "sources/v1/../../assignment.json",
                    "sources/v1/transcript/segments.json", "sources/v1/media/../../../state.json",
                    "sources/v2/media/source.mp4", "sources/v1/media/untracked.mp4"):
            forged = copy.deepcopy(signoff)
            forged["videos"]["v1"]["media"][bad] = "0" * 64
            with self.assertRaisesRegex(evidence.ContractError, "not tracked temporary media"):
                archive._plan_video(workspace, state, "v1", receipt, forged)

    def test_unlink_never_follows_symlinked_ancestors_or_files(self):
        import archive
        root = self.root / "unlink"
        (root / "a").mkdir(parents=True)
        victim_dir = self.root / "victim"
        victim_dir.mkdir()
        (victim_dir / "f.mp4").write_bytes(b"victim")
        digest = evidence.sha256_bytes(b"victim")
        (root / "a" / "link").symlink_to(victim_dir, target_is_directory=True)
        with self.assertRaisesRegex(evidence.ContractError, "symlink"):
            archive._check_or_delete(root, "a/link/f.mp4", digest, delete=True)
        (root / "a" / "f.mp4").symlink_to(victim_dir / "f.mp4")
        with self.assertRaisesRegex(evidence.ContractError, "symlink"):
            archive._check_or_delete(root, "a/f.mp4", digest, delete=True)
        self.assertTrue((victim_dir / "f.mp4").exists())
        (root / "a" / "g.mp4").write_bytes(b"other")
        with self.assertRaisesRegex(evidence.ContractError, "checksum"):
            archive._check_or_delete(root, "a/g.mp4", digest, delete=True)
        (root / "a" / "h.mp4").write_bytes(b"victim")
        archive._check_or_delete(root, "a/h.mp4", digest, delete=True)
        self.assertFalse((root / "a" / "h.mp4").exists())

    def test_symlinks_traversal_and_untracked_paths_refused(self):
        self.approved_archive()
        media_dir = self.src / "media"
        moved = self.root / "elsewhere"
        shutil.move(str(media_dir), str(moved))
        media_dir.symlink_to(moved, target_is_directory=True)
        self.refused("symlink", "cleanup", "--workspace", self.ws, "--video", "v1", "--container", CONTAINER)
        self.assertTrue((moved / "source.mp4").exists())
        media_dir.unlink()
        shutil.move(str(moved), str(media_dir))

        for bad in ("publications/v1/package/manifest.json", "sources/v1/../../assignment.json",
                    "sources/v1/transcript/segments.json"):
            record = json.loads((self.pub / "signoff.json").read_text())
            original = copy.deepcopy(record)
            record["videos"]["v1"]["media"][bad] = "0" * 64
            (self.pub / "signoff.json").write_text(json.dumps(record))
            self.refused("signoff|media path|temporary", "cleanup", "--workspace", self.ws, "--video", "v1",
                         "--container", CONTAINER)
            (self.pub / "signoff.json").write_text(json.dumps(original))
        self.assertTrue((self.pub / "package" / "manifest.json").exists())
        self.assertTrue(all(p.exists() for p in self.media()))

    def test_media_file_replaced_by_symlink_refused(self):
        self.approved_archive()
        media = self.media()[0]
        outside = self.root / "victim.mp4"
        outside.write_bytes(media.read_bytes())
        media.unlink()
        media.symlink_to(outside)
        self.refused("symlink", "cleanup", "--workspace", self.ws, "--video", "v1", "--container", CONTAINER)
        self.assertTrue(outside.exists())


class ActionsHandoff(ArchiveFixture):
    def artifact_zip(self, extra=None, mutate=None):
        package = self.pub / "package"
        manifest = json.loads((package / "manifest.json").read_text())
        path = self.root / "artifact.zip"
        with zipfile.ZipFile(path, "w") as bundle:
            for item in sorted(package.rglob("*")):
                if item.is_file():
                    bundle.write(item, item.relative_to(package).as_posix())
            # A producer stages the readable local ZIP under the canonical <P>-<revision>.zip name.
            bundle.write(self.pub / "a-talk.zip", f"v1-{manifest['revision']}.zip")
            if (self.pub / "signoff.json").exists():
                bundle.write(self.pub / "signoff.json", "signoff.json")
            for name, data in (extra or {}).items():
                if isinstance(data, zipfile.ZipInfo):
                    bundle.writestr(data, b"target")
                else:
                    bundle.writestr(name, data)
        return path, "sha256:" + evidence.sha256_file(path), evidence.sha256_file(package / "manifest.json")

    def unpack(self, path, digest, manifest_sha, dest=None):
        return self.call("unpack-artifact", "--zip", path, "--digest", digest, "--dest",
                         dest or self.root / "unpacked", "--expected-manifest-sha256", manifest_sha)

    def test_unpack_then_archive_package_dir(self):
        self.signoff()
        path, digest, manifest_sha = self.artifact_zip()
        code, out, err = self.unpack(path, digest, manifest_sha)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["quality"], "approved")
        receipt = self.root / "receipt" / "archive-receipt.json"
        result = self.ok("archive", "--package-dir", self.root / "unpacked", "--container", CONTAINER,
                         "--receipt", receipt)
        self.assertEqual(result["quality"]["status"], "approved")
        self.assertTrue(receipt.is_file())
        self.ok("verify-archive", "--receipt", receipt, "--container", CONTAINER)

    def test_unpack_rejects_untrusted_content(self):
        path, digest, manifest_sha = self.artifact_zip()
        self.assertEqual(self.unpack(path, "sha256:" + "0" * 64, manifest_sha)[0], 2)
        self.assertEqual(self.unpack(path, digest, "0" * 64, dest=self.root / "u0")[0], 2)
        link = zipfile.ZipInfo("assets/link.js")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        cases = {"traversal": {"../escape.md": b"x"}, "absolute": {"/abs.md": b"x"}, "symlink": {"x": link},
                 "unexpected": {"run.sh": b"#!/bin/sh\necho hi"}, "unlisted": {"notes.md": b"hello"}}
        for index, (label, extra) in enumerate(cases.items()):
            if label == "symlink":
                extra = {"assets/link.js": link}
            bad, bad_digest, sha = self.artifact_zip(extra)
            code, out, err = self.unpack(bad, bad_digest, sha, dest=self.root / f"u{index + 1}")
            self.assertEqual(code, 2, f"{label}: {err}")
            self.assertFalse((self.root / "escape.md").exists())

    def test_unpack_rejects_secret_bearing_signoff(self):
        self.signoff()
        record = json.loads((self.pub / "signoff.json").read_text())
        record["review"]["note"] = "https://acct.blob.core.windows.net/x?sig=" + "A" * 30
        (self.pub / "signoff.json").write_text(json.dumps(record))
        path, digest, manifest_sha = self.artifact_zip()
        code, out, err = self.unpack(path, digest, manifest_sha)
        self.assertEqual(code, 2)
        self.assertRegex(err, "secret")

    def provenance(self, run=None, artifacts=None, allowed=".github/workflows/produce-distilled-package.yml"):
        run_data = {"id": 42, "status": "completed", "conclusion": "success", "event": "workflow_dispatch",
                    "head_branch": "main", "head_sha": "a" * 40, "path": ".github/workflows/produce-distilled-package.yml",
                    "repository": {"id": 7, "full_name": "rahulnakmol/ampcode"},
                    "head_repository": {"id": 7, "full_name": "rahulnakmol/ampcode"}}
        run_data.update(run or {})
        artifact = {"id": 99, "name": "distilled-v1", "expired": False, "size_in_bytes": 1000,
                    "digest": "sha256:" + "b" * 64,
                    "workflow_run": {"id": 42, "repository_id": 7, "head_repository_id": 7, "head_branch": "main",
                                     "head_sha": "a" * 40}}
        listing = {"total_count": 1, "artifacts": [artifact]} if artifacts is None else artifacts
        run_path, artifacts_path = self.root / "run.json", self.root / "artifacts.json"
        run_path.write_text(json.dumps(run_data))
        artifacts_path.write_text(json.dumps(listing))
        return self.call("actions-provenance", "--run-json", run_path, "--artifacts-json", artifacts_path,
                         "--repository", "rahulnakmol/ampcode", "--default-branch", "main", "--run-id", "42",
                         "--artifact-name", "distilled-v1", "--allowed-workflows", allowed, sas=None)

    def test_trusted_same_repo_run_accepted(self):
        code, out, err = self.provenance()
        self.assertEqual(code, 0, err)
        self.assertEqual(out["artifact_id"], 99)
        self.assertEqual(out["digest"], "sha256:" + "b" * 64)

    def test_untrusted_provenance_rejected(self):
        fork = {"id": 8, "full_name": "attacker/ampcode"}
        artifact = {"id": 99, "name": "distilled-v1", "expired": False, "size_in_bytes": 1000,
                    "digest": "sha256:" + "b" * 64,
                    "workflow_run": {"id": 42, "repository_id": 7, "head_repository_id": 7}}
        cases = [
            ({"event": "pull_request"}, None, None),
            ({"event": "pull_request_target"}, None, None),
            ({"event": "workflow_run"}, None, None),
            ({"head_repository": fork}, None, None),
            ({"head_branch": "feature"}, None, None),
            ({"conclusion": "failure"}, None, None),
            ({"path": ".github/workflows/other.yml"}, None, None),
            ({"id": 43}, None, None),
            ({}, None, ""),
            ({}, {"total_count": 0, "artifacts": []}, None),
            ({}, {"total_count": 2, "artifacts": [artifact, dict(artifact, id=100)]}, None),
            ({}, {"total_count": 1, "artifacts": [dict(artifact, expired=True)]}, None),
            ({}, {"total_count": 1, "artifacts": [dict(artifact, digest=None)]}, None),
            ({}, {"total_count": 1, "artifacts": [dict(artifact, workflow_run={"id": 42, "repository_id": 7,
                                                                                "head_repository_id": 8})]}, None),
            ({}, {"total_count": 1, "artifacts": [dict(artifact, size_in_bytes=10 ** 12)]}, None),
        ]
        for run, listing, allowed in cases:
            kwargs = {"run": run, "artifacts": listing}
            if allowed is not None:
                kwargs["allowed"] = allowed
            code, out, err = self.provenance(**kwargs)
            self.assertEqual(code, 2, f"accepted untrusted provenance: {run} {listing} {allowed!r}")


class WorkflowSafety(unittest.TestCase):
    def test_workflow_is_dispatch_only_with_minimal_permissions(self):
        text = (ROOT / ".github" / "workflows" / "archive-distilled-videos.yml").read_text()
        lines = text.splitlines()
        start = lines.index("on:")
        end = next(i for i in range(start + 1, len(lines)) if lines[i] and not lines[i].startswith(" "))
        triggers = [l.strip() for l in lines[start + 1:end] if l.startswith("  ") and not l.startswith("   ")]
        self.assertEqual(triggers, ["workflow_dispatch:"])
        self.assertIn("\npermissions: {}\n", text)
        self.assertIn("environment: distilled-video-archive", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("actions-provenance", text)
        self.assertIn("unpack-artifact", text)
        self.assertNotIn("${{ inputs.", "\n".join(l for l in text.splitlines() if l.strip().startswith(("run:", "python", "gh "))))
        for line in text.splitlines():
            if "uses:" in line:
                self.assertRegex(line, r"uses: [\w./-]+@[0-9a-f]{40}")
        self.assertEqual(text.count("secrets.DISTILL_ARCHIVE_SAS"), 1)


if __name__ == "__main__":
    unittest.main()

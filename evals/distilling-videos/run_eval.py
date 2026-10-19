#!/usr/bin/env python3
"""End-to-end evaluation of skills/distilling-videos against controlled fixtures.

Runs the real CLI (distill.py) on synthetic slide videos rendered with ffmpeg, the fixture
transcripts, and evaluator-composed article JSON; then scores outputs against ground-truth.json.
Archive steps use an in-process fake Blob transport (no Azure, no credentials). Optional live
YouTube probe (--live-youtube) only reads public metadata, downloads media, samples frames, and
fetches captions; it makes no paid calls and scores nothing about transcription accuracy.

Usage:
  python3 evals/distilling-videos/run_eval.py [--out DIR] [--tools-bin DIR] [--browser PATH]
        [--capture] [--live-youtube URL] [--live-timeout SECONDS]

Exit: 0 when every executed check passes, 1 when any check fails, 3 when ffmpeg/ffprobe are missing.
Results: <out>/results.json and <out>/summary.md, grouped by category (never one pass count).
"""

import argparse
import base64
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIX = HERE / "fixtures"
SCRIPTS = REPO / "skills" / "distilling-videos" / "scripts"
DISTILL = SCRIPTS / "distill.py"
MARKER = ".distill-eval-output"
CONTAINER = "https://evalacct.blob.core.windows.net/distilled-eval"
FAKE_SIG = "RkFLRS1FVkFMLVNJRy1ub3QtYS1zZWNyZXQ%3D"
SAS_OK = f"sv=2022-11-02&sr=c&sp=rc&spr=https&se=2099-01-01T00%3A00%3A00Z&sig={FAKE_SIG}"
SAS_DELETE = f"sv=2022-11-02&sr=c&sp=rcd&spr=https&se=2099-01-01T00%3A00%3A00Z&sig={FAKE_SIG}"

sys.path.insert(0, str(SCRIPTS))
import distill  # noqa: E402
import evidence  # noqa: E402


# ---------------------------------------------------------------------------
# Result recording


class Recorder:
    def __init__(self):
        self.rows = []

    def check(self, category, scenario, name, ok, detail="", expected=None, actual=None):
        row = {"category": category, "scenario": scenario, "check": name,
               "outcome": "pass" if ok else "fail", "detail": detail}
        if expected is not None:
            row["expected"] = expected
        if actual is not None:
            row["actual"] = actual
        self.rows.append(row)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {category} / {scenario}: {name}" + (f" ({detail})" if detail and not ok else ""))
        return ok

    def not_run(self, category, scenario, reason):
        self.rows.append({"category": category, "scenario": scenario, "check": "not run",
                          "outcome": "not-run", "detail": reason})
        print(f"[SKIP] {category} / {scenario}: {reason}")

    def note(self, category, scenario, name, detail):
        self.rows.append({"category": category, "scenario": scenario, "check": name,
                          "outcome": "observed", "detail": detail})
        print(f"[NOTE] {category} / {scenario}: {name}: {detail}")

    def summary(self):
        cats = {}
        for row in self.rows:
            c = cats.setdefault(row["category"], {"pass": 0, "fail": 0, "not-run": 0, "observed": 0})
            c[row["outcome"]] += 1
        return cats


R = Recorder()


# ---------------------------------------------------------------------------
# CLI helpers


class Env:
    def __init__(self, out, bin_dir):
        self.out = out
        self.bin_dir = bin_dir
        self.home = out / "home"
        self.home.mkdir(parents=True, exist_ok=True)

    def cli(self, *args, tools=True, extra_env=None, timeout=600):
        path = (str(self.bin_dir) + ":" if tools else "") + "/usr/bin:/bin"
        env = {"PATH": path, "HOME": str(self.home), "LANG": "en_US.UTF-8"}
        env.update(extra_env or {})
        result = subprocess.run([sys.executable, str(DISTILL), *map(str, args)], capture_output=True, text=True,
                                env=env, timeout=timeout)
        data = None
        if result.stdout.strip().startswith("{"):
            try:
                data = json.loads(result.stdout)
            except ValueError:
                data = None
        return result.returncode, data, result.stderr


def in_process(argv, transport=None, sas=SAS_OK):
    """Run an archive-family command in-process with an injected fake transport (as the unit tests do)."""
    args = distill.build_parser().parse_args([str(a) for a in argv])
    args.transport = transport
    out, err = io.StringIO(), io.StringIO()
    env = {k: v for k, v in os.environ.items() if k != "DISTILL_ARCHIVE_SAS"}
    if sas is not None:
        env["DISTILL_ARCHIVE_SAS"] = sas
    with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err):
        try:
            code = int(args.func(args) or 0)
        except evidence.BudgetRefused as error:
            print(f"error: {error}", file=sys.stderr)
            code = 4
        except distill.ContractError as error:
            print("error: " + "\n  ".join(error.problems), file=sys.stderr)
            code = 2
        except distill.MissingTool as error:
            print(f"error: {error}", file=sys.stderr)
            code = 3
        except distill.ToolFailed as error:
            print(f"error: {error}", file=sys.stderr)
            code = 5
    text = out.getvalue()
    data = json.loads(text) if text.strip().startswith("{") else None
    return code, data, err.getvalue()


class FakeBlob:
    """In-process Azure Blob double: create-only PUT, GET, injectable faults. No network."""

    def __init__(self):
        self.objects = {}
        self.fail_put = None
        self.corrupt_get = None
        self.raise_error = False

    def request(self, method, host, target, headers, body):
        path, _, _query = target.partition("?")
        _container, name = path.lstrip("/").split("/", 1)
        name = unquote(name)
        if self.raise_error:
            raise OSError(f"connection reset while requesting https://{host}{target}")
        if method == "PUT":
            if self.fail_put and re.search(self.fail_put, name):
                return 500, {"x-ms-error-code": "InternalError"}, b""
            if headers.get("If-None-Match") != "*":
                return 400, {"x-ms-error-code": "MissingCreateOnly"}, b""
            if name in self.objects:
                return 409, {"x-ms-error-code": "BlobAlreadyExists"}, b""
            if base64.b64encode(hashlib.md5(body).digest()).decode() != headers.get("Content-MD5"):  # noqa: S324
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

    def markers(self, prefix="publications/"):
        return sorted(n for n in self.objects if n.startswith(prefix) and n.endswith("/_COMPLETE.json"))


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return Path(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Tools and synthetic media


def find_tool(name, extra_dirs):
    for directory in extra_dirs:
        candidate = Path(directory) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    found = shutil.which(name)
    return Path(found).resolve() if found else None


def prepare_bin(out, tools_bin):
    dirs = [tools_bin] if tools_bin else []
    dirs += ["/opt/homebrew/bin", "/usr/local/bin"]
    bin_dir = out / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    found = {}
    for name in ("ffmpeg", "ffprobe", "yt-dlp"):
        path = find_tool(name, dirs)
        if path:
            link = bin_dir / name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(path)
            found[name] = str(path)
    return bin_dir, found


def pick_font(candidates):
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def esc_filter_path(path):
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_media(spec, video_id, ffmpeg, workdir):
    """Render one synthetic slide video: one clip per scene, concatenated, plus a sine tone."""
    video = spec["videos"][video_id]
    fonts = {k: pick_font(v) for k, v in spec["fonts"].items()}
    clip_dir = workdir / f"clips-{video_id}"
    clip_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, scene in enumerate(video["scenes"]):
        font = fonts.get(scene.get("font", "sans"))
        if not font:
            raise RuntimeError(f"no font available for {scene.get('font')}")
        text_file = clip_dir / f"scene{index}.txt"
        text_file.write_text("\n".join(scene["lines"]))
        fg = scene.get("fg", "0xf0f0f0")
        filters = [f"drawtext=fontfile='{esc_filter_path(font)}':textfile='{esc_filter_path(text_file)}':"
                   f"fontsize={scene['size']}:fontcolor={fg}:x=60:y=60:line_spacing=14"]
        for x, y, w, h in scene.get("boxes", []):
            filters.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x333333:t=fill")
        if scene.get("blur"):
            filters.append(f"boxblur={scene['blur']}:2")
        clip = clip_dir / f"scene{index}.mp4"
        duration = scene["end"] - scene["start"]
        subprocess.run([str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", f"color=c={scene['bg']}:s={video['size']}:r=25:d={duration}",
                        "-vf", ",".join(filters), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration),
                        str(clip)], check=True)
        clips.append(clip)
    concat = clip_dir / "concat.txt"
    concat.write_text("".join(f"file '{c}'\n" for c in clips))
    total = video["scenes"][-1]["end"]
    target = workdir / f"{video_id}.mp4"
    subprocess.run([str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe",
                    "0", "-i", str(concat), "-f", "lavfi", "-i", f"sine=frequency={video['tone_hz']}:duration={total}",
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(target)],
                   check=True)
    return target


def scene_at(spec, video_id, t):
    for scene in spec["videos"][video_id]["scenes"]:
        if scene["start"] <= t < scene["end"]:
            return scene
    return None


# ---------------------------------------------------------------------------
# Scenarios


def scenario_contracts(env):
    cat = "contracts"
    root = env.out / "contracts"

    def vids(n):
        return [{"id": f"v{i}", "url": f"https://youtu.be/Eval{i:07d}"} for i in range(n)]

    cases = [
        ("ten-videos", {"schema_version": 1, "videos": vids(10)}, 0),
        ("eleven-videos", {"schema_version": 1, "videos": vids(11)}, 2),
        ("group-of-five", {"schema_version": 1, "videos": vids(5),
                           "groups": [{"id": "g", "video_ids": [f"v{i}" for i in range(5)]}]}, 0),
        ("group-of-six", {"schema_version": 1, "videos": vids(6),
                          "groups": [{"id": "g", "video_ids": [f"v{i}" for i in range(6)]}]}, 2),
        ("group-of-one", {"schema_version": 1, "videos": vids(2), "groups": [{"id": "g", "video_ids": ["v0"]}]}, 2),
        ("video-in-two-groups", {"schema_version": 1, "videos": vids(3), "groups": [
            {"id": "g1", "video_ids": ["v0", "v1"]}, {"id": "g2", "video_ids": ["v1", "v2"]}]}, 2),
        ("group-id-collides-with-video", {"schema_version": 1, "videos": vids(2),
                                          "groups": [{"id": "v0", "video_ids": ["v0", "v1"]}]}, 2),
        ("unknown-group-member", {"schema_version": 1, "videos": vids(2),
                                  "groups": [{"id": "g", "video_ids": ["v0", "v9"]}]}, 2),
        ("path-escape-id", {"schema_version": 1, "videos": [{"id": "../x", "url": "https://youtu.be/Eval0000001"}]}, 2),
        ("non-youtube-url", {"schema_version": 1, "videos": [{"id": "v0", "url": "https://evil.example/watch?v=Eval0000001"}]}, 2),
        ("unknown-field", {"schema_version": 1, "videos": vids(1), "autopilot": True}, 2),
        ("per-video-over-batch", {"schema_version": 1, "videos": vids(1),
                                  "budgets": {"currency": "USD", "batch": 1.0, "per_video": 2.0}}, 2),
    ]
    for name, assignment, expected in cases:
        ws = root / name
        path = write_json(root / f"{name}.json", assignment)
        code, data, err = env.cli("init", "--workspace", ws, "--assignment", path)
        R.check(cat, "assignment limits and grouping", f"{name} -> exit {expected}", code == expected,
                err.strip()[:200], expected, code)
        if expected == 0 and name == "group-of-five":
            plan = read_json(ws / "assignment.json")
            R.check(cat, "assignment limits and grouping", "group of five yields one group publication",
                    [p["kind"] for p in plan["publications"]] == ["group"], actual=plan["publications"])


def scenario_evidence(env, spec, gt, media):
    cat = "evidence"
    ws = env.out / "ws"
    code, data, err = env.cli("init", "--workspace", ws, "--assignment", FIX / "assignment.json")
    R.check(cat, "init", "init creates workspace with publications g-bio, tech-demo, ja-talk",
            code == 0 and data["publications"] == ["g-bio", "tech-demo", "ja-talk"], err, actual=data)

    # Missing tool: no ffmpeg/ffprobe on PATH.
    code, data, err = env.cli("download", "--workspace", ws, "--video", "tech-demo", "--from-file",
                              media["tech-demo"], tools=False)
    state = read_json(ws / "state.json")
    stage = state["stages"].get("sources/tech-demo/download", {})
    R.check(cat, "missing tool", "download without ffprobe/ffmpeg exits 3", code == 3, err.strip(), 3, code)
    R.check(cat, "missing tool", "stage recorded as failed, not complete", stage.get("status") == "failed",
            actual=stage.get("status"))
    R.check(cat, "missing tool", "error names the missing tool", "ffprobe" in err or "ffmpeg" in err, err.strip())
    code, data, err = env.cli("validate", "--workspace", ws, "--require-complete")
    R.check(cat, "missing tool", "validate --require-complete fails while incomplete", code == 1, actual=code)

    for vid in ("tech-demo", "ja-talk", "bio-a", "bio-b"):
        code, data, err = env.cli("download", "--workspace", ws, "--video", vid, "--from-file", media[vid])
        R.check(cat, "download --from-file", f"{vid} downloaded with real ffprobe/ffmpeg",
                code == 0 and data["status"] == "downloaded", err.strip()[:300])
    code, data, err = env.cli("download", "--workspace", ws, "--video", "tech-demo", "--from-file", media["tech-demo"])
    R.check(cat, "resume", "repeat download is reused (checksum-verified)", code == 0 and data["status"] == "reused",
            err, actual=data and data.get("status"))
    source = read_json(ws / "sources/tech-demo/source.json")
    R.check(cat, "download --from-file", "ffprobe duration ~60 s and audio present",
            abs(source["duration"] - 60.0) < 0.5 and source["media"]["has_audio"], actual=source["duration"])

    for vid, plan in gt["frames"].items():
        args = ["frames", "--workspace", ws, "--video", vid, "--interval", plan["interval"],
                "--max-frames", plan["max_frames"], "--scene-threshold", plan["scene_threshold"]]
        for d in plan["dense"]:
            args += ["--dense", d]
        for t in plan["at"]:
            args += ["--at", t]
        code, data, err = env.cli(*args)
        R.check(cat, "frames", f"{vid} frames extracted with real ffmpeg", code == 0 and data["status"] == "extracted",
                err.strip()[:300], actual=data)
        manifest = read_json(ws / f"sources/{vid}/frames/frames.json")
        R.check(cat, "frames", f"{vid} manifest says sampling is not semantic",
                manifest["selection"]["semantic_completeness"] is False)
        missing = [f for f in plan["select"] if f not in {x["id"] for x in manifest["frames"]}]
        R.check(cat, "frames", f"{vid} planned frames exist", not missing, actual=missing)
        if vid == "tech-demo":
            reasons = {r for f in manifest["frames"] for r in f["reasons"]}
            R.check(cat, "frames", "tech-demo has periodic, dense, cue, and scene candidates",
                    {"periodic", "dense", "cue", "scene"} <= reasons, actual=sorted(reasons))
            R.note(cat, "frames", "tech-demo scene cues found", manifest["selection"]["scene_cues_found"])
    code, data, err = env.cli("frames", "--workspace", ws, "--video", "tech-demo", "--interval", "0.5",
                              "--max-frames", "20")
    R.check(cat, "frames", "--max-frames refuses rather than truncates (exit 2)", code == 2, err.strip()[:200], 2, code)

    # Transcript contract negatives.
    ja = read_json(FIX / "transcripts/ja-talk.json")
    bad = json.loads(json.dumps(ja))
    for seg in bad["segments"]:
        seg["english_kind"] = "clean"
    code, _, err = env.cli("import-transcript", "--workspace", ws, "--video", "ja-talk", "--transcript",
                           write_json(env.out / "neg/ja-clean.json", bad))
    R.check(cat, "Japanese source", "English presented as clean (not translation) is rejected", code == 2, err.strip()[:200])
    bad = json.loads(json.dumps(ja))
    bad["segments"][1]["summary"] = "shortened"
    code, _, err = env.cli("import-transcript", "--workspace", ws, "--video", "ja-talk", "--transcript",
                           write_json(env.out / "neg/ja-unknown.json", bad))
    R.check(cat, "Japanese source", "unknown segment field (possible summary) is rejected", code == 2, err.strip()[:200])
    bad = json.loads(json.dumps(ja))
    bad["segments"][1], bad["segments"][2] = bad["segments"][2], bad["segments"][1]
    code, _, err = env.cli("import-transcript", "--workspace", ws, "--video", "ja-talk", "--transcript",
                           write_json(env.out / "neg/ja-order.json", bad))
    R.check(cat, "Japanese source", "out-of-order segments are rejected", code == 2, err.strip()[:200])
    bad = json.loads(json.dumps(ja))
    bad["segments"][3]["english"] = ""
    code, _, err = env.cli("import-transcript", "--workspace", ws, "--video", "ja-talk", "--transcript",
                           write_json(env.out / "neg/ja-empty.json", bad))
    R.check(cat, "Japanese source", "empty English (dropped content) is rejected", code == 2, err.strip()[:200])

    for vid in ("tech-demo", "ja-talk", "bio-a", "bio-b"):
        code, data, err = env.cli("import-transcript", "--workspace", ws, "--video", vid, "--transcript",
                                  FIX / f"transcripts/{vid}.json")
        R.check(cat, "transcript import", f"{vid} imported", code == 0 and data["status"] == "imported", err.strip()[:300])
        original = read_json(FIX / f"transcripts/{vid}.json")["segments"]
        stored = read_json(ws / f"sources/{vid}/transcript/segments.json")["segments"]
        R.check(cat, "transcript import", f"{vid} text and english preserved byte-for-byte",
                [(s["text"], s["english"]) for s in original] == [(s["text"], s["english"]) for s in stored])
    code, data, err = env.cli("import-transcript", "--workspace", ws, "--video", "ja-talk", "--transcript",
                              FIX / "transcripts/ja-talk.json")
    R.check(cat, "resume", "re-import of identical transcript is reused", code == 0 and data["status"] == "reused", err)
    md = (ws / "sources/ja-talk/transcript/english.md").read_text()
    R.check(cat, "Japanese source", "english.md labels the text as translation", "translation" in md.lower())
    seg = read_json(ws / "sources/ja-talk/transcript/segments.json")
    R.check(cat, "Japanese source", "segments.json english_label is translation", seg.get("english_label") == "translation",
            actual=seg.get("english_label"))

    for vid, plan in gt["frames"].items():
        code, data, err = env.cli("select-frames", "--workspace", ws, "--video", vid, "--frames", ",".join(plan["select"]),
                                  "--note", "eval selection from ground-truth plan")
        R.check(cat, "frame selection", f"{vid} selection recorded", code == 0, err.strip()[:200])
        for frame_id in plan["select"]:
            scene = scene_at(spec, vid, int(frame_id[1:]) / 1000)
            R.check(cat, "frame selection", f"{vid} {frame_id} is not a talking head",
                    scene is not None and scene["kind"] != "talking-head", actual=scene and scene["kind"])
    md = (ws / "sources/tech-demo/transcript/english.md").read_text()
    R.check(cat, "frame selection", "english.md embeds timestamp-linked thumbnails",
            "../frames/thumbs/f000012000.jpg" in md and "&t=" in md)
    R.check(cat, "injection as data", "english.md escapes the <script> bait",
            "<script>" not in md and ("&lt;script&gt;" in md or "\\<script\\>" in md), "raw <script> present" if "<script>" in md else "")

    coverage = read_json(ws / "sources/tech-demo/transcript/coverage.json")
    gaps = coverage["gaps"]
    R.check(cat, "coverage", "tech-demo trailing gap 55 s to end is reported",
            len(gaps) == 1 and abs(gaps[0]["start"] - 55.0) < 0.01, actual=gaps)
    for pub, info in gt["publications"].items():
        for item in info["uncertain_segments"]:
            vid, _, seg_id = item.rpartition(":")
            vid = vid or pub
            cov = read_json(ws / f"sources/{vid}/transcript/coverage.json")
            R.check(cat, "coverage", f"{vid}:{seg_id} reported uncertain", seg_id in cov["uncertain_segment_ids"],
                    actual=cov["uncertain_segment_ids"])
    code, data, err = env.cli("validate", "--workspace", ws, "--require-complete")
    R.check(cat, "validate", "validate --require-complete passes", code == 0 and data["ok"], err.strip()[:300],
            actual=data and data.get("errors"))
    R.check(cat, "validate", "validate warns about the transcript gap",
            any("gap" in w for w in (data or {}).get("warnings", [])), actual=(data or {}).get("warnings"))

    code, data, err = env.cli("init", "--workspace", ws, "--assignment", FIX / "assignment.json")
    R.check(cat, "resume", "re-init with the same assignment resumes", code == 0 and data["status"] == "resumed", err)
    changed = read_json(FIX / "assignment.json")
    changed["goal"] = "A different goal"
    code, data, err = env.cli("init", "--workspace", ws, "--assignment", write_json(env.out / "neg/changed.json", changed))
    R.check(cat, "resume", "changed assignment is refused (exit 2) and nothing changes", code == 2, err.strip()[:200])
    return ws


def scenario_budget(env, ws):
    cat = "budget"

    def reserve(amount, video=None, step="transcription"):
        args = ["budget", "reserve", "--workspace", ws, "--step", step, "--provider", "fixture-provider",
                "--amount", amount, "--approval", "eval fixture approval"]
        if video:
            args += ["--video", video]
        return env.cli(*args)

    code, d, err = reserve(0.30, "tech-demo")
    R.check(cat, "reservations", "reserve 0.30 for tech-demo within caps", code == 0, err, actual=d)
    code, d, err = reserve(0.20, "tech-demo")
    R.check(cat, "reservations", "second 0.20 for tech-demo exceeds per_video 0.40 -> exit 4", code == 4, err, 4, code)
    code, d, err = reserve(0.35, "ja-talk")
    R.check(cat, "reservations", "reserve 0.35 for ja-talk", code == 0, err)
    code, d, err = reserve(0.35, "bio-a")
    R.check(cat, "reservations", "reserve 0.35 for bio-a (batch now 1.00)", code == 0, err)
    code, d, err = reserve(0.05, step="synthesis-research")
    R.check(cat, "exhausted batch", "batch-only 0.05 beyond batch cap 1.00 -> exit 4", code == 4, err, 4, code)
    code, d, err = reserve(0.35, "bio-b")
    R.check(cat, "exhausted batch", "bio-b 0.35 refused when batch is exhausted -> exit 4", code == 4, err, 4, code)
    ledger = read_json(ws / "budget.json")
    R.check(cat, "exhausted batch", "refused attempts are not recorded", len(ledger["entries"]) == 3,
            actual=len(ledger["entries"]))
    rid = {e["video_id"]: e["id"] for e in ledger["entries"]}
    code, d, err = env.cli("budget", "release", "--workspace", ws, "--id", rid["bio-a"])
    R.check(cat, "reservations", "release unused bio-a reservation", code == 0, err)
    code, d, err = reserve(0.05, step="synthesis-research")
    R.check(cat, "reservations", "after release, batch-only 0.05 fits", code == 0, err)
    code, d, err = env.cli("budget", "settle", "--workspace", ws, "--id", rid["tech-demo"], "--actual", "0.45",
                           "--basis", "estimate")
    ledger = read_json(ws / "budget.json")
    entry = next(e for e in ledger["entries"] if e["id"] == rid["tech-demo"])
    R.check(cat, "overrun", "settling above the reservation records overrun", code == 0 and entry.get("overrun") is True,
            err, actual=entry)
    code, d, err = env.cli("validate", "--workspace", ws)
    R.check(cat, "overrun", "validate warns about the overrun", any("overrun" in w.lower() for w in (d or {}).get("warnings", [])),
            actual=(d or {}).get("warnings"))
    code, d, err = env.cli("budget", "status", "--workspace", ws)
    R.check(cat, "honesty", "budget status disclaims an all-in spend guarantee",
            code == 0 and d.get("guarantees_all_in_spend") is False, actual=d)


def copy_article(ws, pub):
    src = FIX / "articles" / pub
    dest = ws / "publications" / pub
    for path in src.rglob("*"):
        if path.is_file():
            target = dest / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    return dest


def scenario_publication(env, ws, browser):
    cat = "publication"
    tech = read_json(FIX / "articles/tech-demo/article.json")
    pub_dir = ws / "publications"

    def render_with(pub, article, name, pattern=None):
        write_json(pub_dir / pub / "article.json", article)
        code, data, err = env.cli("render", "--workspace", ws, "--publication", pub)
        ok = code == 2 and (pattern is None or re.search(pattern, err, re.I))
        R.check(cat, "render refuses unsafe or unfaithful input", name, bool(ok), err.strip()[:300], 2, code)
        R.check(cat, "render refuses unsafe or unfaithful input", f"{name}: nothing written",
                not (pub_dir / pub / "dist").exists())

    copy_article(ws, "tech-demo")
    copy_article(ws, "ja-talk")
    copy_article(ws, "g-bio")

    bad = json.loads(json.dumps(tech))
    bad["sections"][0]["blocks"][1]["text"] = "only the burst of ten ever got through"
    render_with("tech-demo", bad, "fabricated quote", r"quote")
    bad = json.loads(json.dumps(tech))
    bad["brief"]["proposals"][0]["text"] += " [@t-output]"
    render_with("tech-demo", bad, "proposal cites a source directly", r"propos")
    bad = json.loads(json.dumps(tech))
    bad["citations"].append({"id": "x-bio", "video_id": "bio-a", "segment_ids": ["s1"]})
    bad["sections"][0]["blocks"][0]["text"] += " [@x-bio]"
    render_with("tech-demo", bad, "citation of a video outside the publication", r"bio-a")
    bad = json.loads(json.dumps(tech))
    bad["figures"][2]["frame_id"] = "f000013000"
    render_with("tech-demo", bad, "figure frame that was never sampled", r"f000013000")
    bad = json.loads(json.dumps(tech))
    bad["autopilot"] = True
    render_with("tech-demo", bad, "unknown article field", None)
    svg_dir = pub_dir / "tech-demo/figures"
    (svg_dir / "evil.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>fetch("https://evil.example")</script></svg>')
    (svg_dir / "remote.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/x.png"/></svg>')
    for name in ("evil", "remote"):
        bad = json.loads(json.dumps(tech))
        bad["figures"][1]["image"] = f"figures/{name}.svg"
        render_with("tech-demo", bad, f"{name} SVG figure", r"svg|remote|script")
        (svg_dir / f"{name}.svg").unlink()
    bad = json.loads(json.dumps(tech))
    bad["figures"][1]["image"] = "../../../sources/tech-demo/source.json"
    render_with("tech-demo", bad, "figure path escape", None)
    only_a = {"schema_version": 1, "publication_id": "g-bio", "status": "complete", "title": "Only one side",
              "dek": "Drops video B.", "sections": [{"id": "s", "heading": "One video", "blocks": [
                  {"type": "p", "text": "Calorie restriction works [@a1]."}]}],
              "figures": [], "citations": [{"id": "a1", "video_id": "bio-a", "segment_ids": ["s1"]}],
              "brief": {"evidence": [], "proposals": []}, "limitations": ["none"]}
    render_with("g-bio", only_a, "synthesis that silently drops bio-b", r"bio-b")

    write_json(pub_dir / "tech-demo/article.json", tech)
    copy_article(ws, "g-bio")
    results = {}
    for pub in ("tech-demo", "ja-talk", "g-bio"):
        code, data, err = env.cli("render", "--workspace", ws, "--publication", pub)
        if not R.check(cat, "render", f"{pub} renders", code == 0, err.strip()[:400]):
            continue
        if data and data.get("warnings"):
            R.note(cat, "render", f"{pub} render warnings", data["warnings"])
        dist = pub_dir / pub / "dist"
        html = (dist / "index.html").read_text()
        R.check(cat, "offline", f"{pub} index.html has a CSP with connect-src 'none'", "connect-src 'none'" in html)
        remote = re.findall(r'<(?:script|link|img|iframe|source|video|audio)[^>]+(?:src|href)="(https?:)?//', html)
        R.check(cat, "offline", f"{pub} no remote script/style/image references", not remote, actual=remote)
        texts = [p for p in dist.rglob("*") if p.suffix in {".html", ".md", ".json"}]
        raw_script = [str(p.relative_to(dist)) for p in texts if "<script>alert" in p.read_text()]
        evil_links = [str(p.relative_to(dist)) for p in texts if re.search(r'href="https?://evil\.example', p.read_text())]
        R.check(cat, "injection as data", f"{pub} no raw <script> bait in outputs", not raw_script, actual=raw_script)
        R.check(cat, "injection as data", f"{pub} bait URL never becomes a link", not evil_links, actual=evil_links)
        if browser:
            code, data, err = env.cli("pdf", "--workspace", ws, "--publication", pub, "--browser", browser, timeout=300)
            pdf = dist / "article.pdf"
            ok = code == 0 and pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-"
            R.check(cat, "pdf", f"{pub} PDF from a real Chromium-family browser", ok, err.strip()[:300],
                    actual=data and {k: data.get(k) for k in ("pages", "status")})
            pdf_meta = read_json(pub_dir / pub / "pdf.json") if (pub_dir / pub / "pdf.json").exists() else {}
            R.note(cat, "pdf", f"{pub} PDF pages", pdf_meta.get("pages"))
            code, data, err = env.cli("package", "--workspace", ws, "--publication", pub)
        else:
            R.not_run(cat, "pdf", "no Chromium-family browser given; package uses --allow-missing-pdf")
            code, data, err = env.cli("package", "--workspace", ws, "--publication", pub, "--allow-missing-pdf")
        R.check(cat, "package", f"{pub} packaged", code == 0, err.strip()[:300])
        if code != 0:
            continue
        results[pub] = data
        R.check(cat, "package", f"{pub} manifest complete={bool(browser)}", data.get("complete") is bool(browser),
                actual={k: data.get(k) for k in ("complete", "incomplete_reasons")})
        manifest = read_json(pub_dir / pub / "package/manifest.json")
        paths = [f["path"] for f in manifest["files"]]
        leaked = [p for p in paths if re.search(r"(^|/)(media/source\.|audio/)", p)]
        R.check(cat, "package", f"{pub} excludes raw media and audio", not leaked, actual=leaked)
        vids = {"tech-demo": ["tech-demo"], "ja-talk": ["ja-talk"], "g-bio": ["bio-a", "bio-b"]}[pub]
        for vid in vids:
            R.check(cat, "package", f"{pub} keeps per-video evidence for {vid}",
                    f"sources/{vid}/transcript/segments.json" in paths and f"sources/{vid}/transcript/original.md" in paths)
        code, again, err = env.cli("package", "--workspace", ws, "--publication", pub,
                                   *([] if browser else ["--allow-missing-pdf"]))
        R.check(cat, "package", f"{pub} repackaging is deterministic (same zip_sha256)",
                code == 0 and again["zip_sha256"] == data["zip_sha256"], actual=[data.get("zip_sha256"), again and again.get("zip_sha256")])
    return results


# ---------------------------------------------------------------------------
# Editorial rubric (machine-checkable part)


def article_texts(article):
    """Yield (location, text, block_type, cite) for every authored string in the article and brief."""
    yield "title", article["title"], "title", None
    yield "dek", article["dek"], "dek", None
    for section in article["sections"]:
        yield f"{section['id']}/heading", section["heading"], "heading", None
        for i, block in enumerate(section["blocks"]):
            loc = f"{section['id']}/{i}"
            if block["type"] in ("p",):
                yield loc, block["text"], "p", None
            elif block["type"] == "quote":
                yield loc, block["text"], "quote", block["cite"]
            elif block["type"] == "list":
                for item in block["items"]:
                    yield loc, item, "list", None
            elif block["type"] == "details":
                yield loc, block["summary"], "details", None
                for inner in block["blocks"]:
                    for item in ([inner["text"]] if inner["type"] == "p" else inner["items"]):
                        yield loc, item, "details", None
    for fig in article["figures"]:
        yield f"figure/{fig['id']}", fig["caption"] + " " + fig.get("alt", ""), "figure", None
        for step in fig.get("steps", []):
            yield f"figure/{fig['id']}", step["caption"] + " " + step["alt"], "figure", None
        for item in fig.get("assumptions", []):
            yield f"figure/{fig['id']}", item, "figure", None
    for item in article["brief"]["evidence"]:
        yield f"brief/{item['id']}", item["text"], "evidence", None
    for item in article["brief"]["proposals"]:
        yield f"brief/{item['id']}", item["text"] + " " + item.get("risks", ""), "proposal", None
    for item in article["limitations"]:
        yield "limitations", item, "limitation", None


def cited_ids(article):
    used = set()
    for _loc, text, kind, cite in article_texts(article):
        for group in re.findall(r"\[@([^\]]+)\]", text):
            used |= {part.strip().lstrip("@") for part in group.split(";")}
        if cite:
            used.add(cite)
    for fig in article["figures"]:
        used |= set(fig.get("sources", []))
    for item in article["brief"]["evidence"]:
        used |= set(item.get("citations", []))
    return used


def resolve_targets(article, used):
    """Return set of (video, segment_or_frame) and list of web URLs among used citations."""
    targets, urls = set(), []
    by_id = {c["id"]: c for c in article["citations"]}
    for cid in used:
        c = by_id.get(cid)
        if not c:
            continue
        if c.get("kind") == "web":
            urls.append(c["url"])
            continue
        for seg in c.get("segment_ids", []):
            targets.add((c["video_id"], seg))
        if c.get("frame_id"):
            targets.add((c["video_id"], c["frame_id"]))
    for fig in article["figures"]:
        if fig["kind"] == "capture":
            targets.add((fig["video_id"], fig["frame_id"]))
        for step in fig.get("steps", []):
            targets.add((fig["video_id"], step["frame_id"]))
    return targets, urls


def editorial_checks(article, pub, info, spec, gt):
    """Machine-checkable rubric items for one article. Returns [(check name, ok, actual)]."""
    out = []
    used = cited_ids(article)
    targets, urls = resolve_targets(article, used)
    all_text = "\n".join(t for _l, t, _k, _c in article_texts(article))
    by_id = {c["id"]: c for c in article["citations"]}
    for fact in info["facts"]:
        name = f"{fact['id']}: {fact['truth'][:70]}"
        if "must_cite_all" in fact:
            missing = [t for t in fact["must_cite_all"] if tuple(t) not in targets]
            out.append((f"{name} [cites all]", not missing, missing))
        if "must_cite_any" in fact:
            out.append((f"{fact['id']} [cites any of {fact['must_cite_any']}]",
                        any(tuple(t) in targets for t in fact["must_cite_any"]), None))
        if "must_cite_web_host" in fact:
            hosts = [urlsplit(u).netloc + urlsplit(u).path for u in urls]
            out.append((f"{fact['id']} [external source matches {fact['must_cite_web_host']}]",
                        any(re.search(fact["must_cite_web_host"], h) for h in hosts), hosts))
        for needle in fact.get("must_mention", []):
            out.append((f"{fact['id']} [mentions {needle!r}]", needle in all_text, None))
        if "must_mention_regex" in fact:
            out.append((f"{fact['id']} [mentions /{fact['must_mention_regex']}/]",
                        bool(re.search(fact["must_mention_regex"], all_text, re.I)), None))
        if fact.get("brief_unknown"):
            unknowns = [e for e in article["brief"]["evidence"] if e["kind"] == "unknown"]
            out.append((f"{fact['id']} [brief lists an open unknown]", bool(unknowns), None))
    if info.get("must_mention_any"):
        out.append((f"mentions one of {info['must_mention_any']}",
                    any(w in all_text.lower() for w in info["must_mention_any"]), None))
    for rule in info["forbidden"]:
        offenders = []
        for loc, text, kind, cite in article_texts(article):
            if re.search(rule["pattern"], text, re.I):
                allowed = rule["allowed_in_quote_of"]
                if kind == "quote" and allowed and cite in by_id:
                    c = by_id[cite]
                    if c.get("video_id") == allowed[0] and allowed[1] in c.get("segment_ids", []):
                        continue
                offenders.append(loc)
        out.append((f"forbidden /{rule['pattern']}/ appears only as an attributed quote", not offenders, offenders))
    for item in info["uncertain_segments"]:
        vid, _, seg = item.rpartition(":")
        vid = vid or pub
        out.append((f"uncertain {vid}:{seg} is cited (surfaced, not dropped)", (vid, seg) in targets, None))
    for item in info["inconclusive_frames"]:
        vid, _, frame = item.rpartition(":")
        vid = vid or pub
        out.append((f"inconclusive frame {vid}:{frame} is shown or cited", (vid, frame) in targets, None))
    if info.get("conflict"):
        both = []
        for section in article["sections"]:
            sec_art = {**article, "sections": [section], "figures": [], "brief": {"evidence": [], "proposals": []}}
            sec_targets, _ = resolve_targets(sec_art, cited_ids(sec_art))
            if all(tuple(t) in sec_targets for t in info["conflict"]["same_section"]):
                both.append(section["id"])
        out.append((f"conflict surfaced: {info['conflict']['same_section']} cited in one section", bool(both), both))
    problems = []
    for e in article["brief"]["evidence"]:
        cites = [by_id[c] for c in e.get("citations", []) if c in by_id]
        kinds = {"web" if c.get("kind") == "web" else "video" for c in cites}
        if e["basis"] == "external" and cites and "web" not in kinds:
            problems.append(f"{e['id']} external without web source")
        if e["basis"] in ("presenter", "screen") and kinds == {"web"}:
            problems.append(f"{e['id']} {e['basis']} cites only web sources")
        if e["basis"] == "screen" and cites and not any(c.get("frame_id") for c in cites if c.get("kind") != "web"):
            problems.append(f"{e['id']} screen without a frame")
        if e["basis"] == "presenter" and cites and not any(c.get("segment_ids") for c in cites):
            problems.append(f"{e['id']} presenter without a segment")
    out.append(("brief basis matches citation kinds (presenter/screen/external)", not problems, problems))
    out.append(("brief has proposals resting on evidence IDs",
                bool(article["brief"]["proposals"]) and all(p["basis"] for p in article["brief"]["proposals"]), None))
    out.append(("limitations are stated", len(article["limitations"]) >= 2, None))
    for fig in article["figures"]:
        if fig["kind"] != "sequence":
            continue
        times = [int(s["frame_id"][1:]) for s in fig["steps"]]
        kinds = [(scene_at(spec, fig["video_id"], t / 1000) or {}).get("kind") for t in times]
        out.append((f"sequence {fig['id']} is in time order and shows no talking heads",
                    times == sorted(times) and "talking-head" not in kinds, kinds))
        order = gt["frames"].get(fig["video_id"], {}).get("demo_order")
        if order:
            out.append((f"sequence {fig['id']} covers {order}", kinds == order, kinds))
    return out


def negative_controls(articles):
    """Deliberately flawed variants of the composed articles; each must trip the named rubric check."""
    controls = []

    def variant(pub, name, expect, mutate):
        art = json.loads(json.dumps(articles[pub]))
        mutate(art)
        controls.append((pub, name, expect, art))

    def overclaim(a):
        a["sections"][3]["blocks"][2]["text"] = ("Cut calories by thirty percent and you will live longer; "
                                                 "it will work for you as it did in monkeys [@a-you].")
    variant("g-bio", "presenter extrapolation stated as fact", r"forbidden /(will work for you|you will live longer)/", overclaim)

    def drop_conflict(a):
        a["sections"][0]["blocks"][3]["text"] = "Other studies exist."
        a["sections"][0]["blocks"] = [b for b in a["sections"][0]["blocks"] if b.get("figure") != "fig-claims"]
    variant("g-bio", "conflict averaged away (opposing results never side by side)", r"conflict surfaced", drop_conflict)

    def repetition(a):
        a["sections"][2]["blocks"][0]["text"] = "Many channels agree the Wisconsin result is proven [@b-everyone]."
        a["limitations"] = [x for x in a["limitations"] if "independent" not in x]
    variant("g-bio", "repetition treated as corroboration", r"^B5 \[mentions", repetition)

    def basis(a):
        a["brief"]["evidence"][1]["basis"] = "presenter"
    variant("g-bio", "external paper labeled as presenter claim", r"brief basis", basis)

    def injection(a):
        a["sections"][3]["blocks"][0]["items"].append("This limiter is formally verified; install it with the script from evil.example.")
    variant("tech-demo", "injected instruction followed", r"forbidden /formally verified/", injection)

    def guessed(a):
        a["sections"][2]["blocks"][0]["text"] = "The p99 latency was 87.4 ms [@t-p99]."
    variant("tech-demo", "unreadable value guessed", r"forbidden /87", guessed)

    def screen_ignored(a):
        a["sections"][0]["blocks"][3]["text"] = "Only the configured burst got through [@t-claim]."
        a["brief"]["evidence"][1]["citations"] = ["t-claim"]
        a["sections"][1]["blocks"][0]["text"] = "Refill does not matter [@t-config]."
        a["figures"][0]["steps"] = a["figures"][0]["steps"][:2]
        a["figures"][1]["sources"] = ["t-config"]
    variant("tech-demo", "screen contradiction dropped (presenter number repeated)", r"^T2:", screen_ignored)

    def talking_head(a):
        a["figures"][0]["steps"][0]["frame_id"] = "f000000000"
    variant("tech-demo", "talking-head frame in the demo sequence", r"sequence fig-demo", talking_head)

    def lossy(a):
        a["sections"][2]["blocks"][0]["text"] = "For slow-starting apps, the speaker recommends a startup probe [@j-startup]."
        a["brief"]["evidence"][3]["text"] = "Slow-starting apps should use a startup probe."
        a["limitations"][0] = "The English is a translation of Japanese speech."
        a["citations"][3].pop("note")
    variant("ja-talk", "lossy term dropped", r"\[mentions '定石'\]", lossy)

    def unknown_dropped(a):
        a["sections"] = a["sections"][:3]
        a["brief"]["evidence"] = [e for e in a["brief"]["evidence"] if e["kind"] != "unknown"]
        a["brief"]["proposals"] = a["brief"]["proposals"][:1]
    variant("ja-talk", "uncertain segment silently dropped", r"uncertain ja-talk:s5", unknown_dropped)
    return controls


def scenario_editorial(env, ws, spec, gt):
    cat = "editorial (machine rubric)"
    articles = {}
    for pub, info in gt["publications"].items():
        article = read_json(ws / f"publications/{pub}/article.json")
        articles[pub] = article
        for name, ok, actual in editorial_checks(article, pub, info, spec, gt):
            R.check(cat, pub, name, ok, actual=actual)
    cat = "editorial rubric negative controls"
    for pub, name, expect, article in negative_controls(articles):
        failed = [n for n, ok, _ in editorial_checks(article, pub, gt["publications"][pub], spec, gt) if not ok]
        R.check(cat, pub, f"rubric catches: {name}", any(re.search(expect, n) for n in failed),
                actual=failed)


# ---------------------------------------------------------------------------
# Sign-off, archive, cleanup


def fill_review(ws, pub, review):
    """Bind fixture gap entries to the exact gap ends in coverage.json (media duration comes from ffprobe)."""
    review = json.loads(json.dumps(review))
    for vid, entry in review["videos"].items():
        cov = read_json(ws / f"sources/{vid}/transcript/coverage.json")
        for gap in entry["gaps"]:
            match = [g for g in cov["gaps"] if abs(g["start"] - gap["start"]) < 0.01 and abs(g["end"] - gap["end"]) < 0.5]
            if match:
                gap["end"] = match[0]["end"]
    return review


def scenario_signoff(env, ws, browser):
    cat = "sign-off"
    reviews = {pub: fill_review(ws, pub, read_json(FIX / f"reviews/{pub}.json")) for pub in ("tech-demo", "ja-talk", "g-bio")}

    def signoff(pub, review, name, expected, pattern=None):
        path = write_json(env.out / f"reviews/{pub}-{re.sub(r'[^a-z0-9]+', '-', name)}.json", review)
        code, data, err = env.cli("signoff", "--workspace", ws, "--publication", pub, "--review", path)
        blockers = (data or {}).get("blockers", [])
        ok = code == expected and (pattern is None or re.search(pattern, json.dumps(blockers) + err, re.I))
        R.check(cat, pub, name, bool(ok), err.strip()[:200], expected, {"code": code, "blockers": blockers})
        return code, data

    r = reviews["tech-demo"]
    bad = json.loads(json.dumps(r))
    bad["videos"]["tech-demo"]["gaps"] = []
    signoff("tech-demo", bad, "unjustified transcript gap blocks (exit 1)", 1, "gap")
    bad = json.loads(json.dumps(r))
    bad["videos"]["tech-demo"]["uncertain_segments"] = []
    signoff("tech-demo", bad, "unreviewed uncertain segment blocks (exit 1)", 1, "uncertain|s5")
    bad = json.loads(json.dumps(r))
    bad["videos"]["tech-demo"]["transcript_coverage"] = "unverified"
    signoff("tech-demo", bad, "unverified transcript coverage blocks (exit 1)", 1, "transcript")
    bad = json.loads(json.dumps(r))
    bad["videos"]["tech-demo"]["gaps"][0]["start"] = 50.0
    signoff("tech-demo", bad, "gap entry that does not match coverage.json is a contract error (exit 2)", 2)
    expected = 0 if browser else 1
    signoff("tech-demo", r, f"reviewed approval -> exit {expected}", expected)
    signed = read_json(ws / "publications/tech-demo/signoff.json")["videos"]["tech-demo"]
    R.check(cat, "tech-demo", "sign-off records transcript provider kind (manual fixture; no audio check claimed)",
            signed.get("transcript_provider", {}).get("kind") == "manual" and signed.get("audio_verification") is None,
            "", {"kind": "manual", "audio_verification": None},
            {"kind": signed.get("transcript_provider"), "audio_verification": signed.get("audio_verification")})
    bad = json.loads(json.dumps(reviews["ja-talk"]))
    bad["videos"]["ja-talk"]["visual_coverage"] = "unverified"
    signoff("ja-talk", bad, "ja-talk left blocked (unverified visual coverage) for archive negatives", 1, "visual")
    signoff("g-bio", reviews["g-bio"], f"g-bio reviewed approval -> exit {expected}", expected)


def archive_call(ws, pub, blob, sas=SAS_OK, container=CONTAINER):
    return in_process(["archive", "--workspace", ws, "--publication", pub, "--container", container], blob, sas)


def scenario_archive(env, ws, browser):
    cat = "archive and cleanup"
    if not browser:
        R.not_run(cat, "all", "approved sign-off needs a real PDF; rerun with --browser")
        return
    media_rel = ["sources/tech-demo/media/source.mp4", "sources/tech-demo/audio/audio.flac"]
    media_digest = {rel: sha(ws / rel) for rel in media_rel}
    receipt = ws / "publications/tech-demo/archive-receipt.json"

    def media_intact():
        return all((ws / rel).exists() and sha(ws / rel) == digest for rel, digest in media_digest.items())

    code, _, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER],
                              FakeBlob())
    R.check(cat, "cleanup before archive", "refused (exit 2), media intact", code == 2 and media_intact(), err.strip()[:200])

    blob = FakeBlob()
    code, _, err = archive_call(ws, "tech-demo", blob, SAS_DELETE)
    R.check(cat, "credential guard", "SAS granting delete is refused before any request", code == 2 and not blob.objects,
            err.strip()[:200])
    code, _, err = archive_call(ws, "tech-demo", blob, None)
    R.check(cat, "credential guard", "missing SAS is refused", code == 2 and not blob.objects, err.strip()[:200])
    code, _, err = archive_call(ws, "tech-demo", blob, container="http://evalacct.blob.core.windows.net/distilled-eval")
    R.check(cat, "credential guard", "plain-HTTP container is refused", code == 2 and not blob.objects, err.strip()[:200])
    code, _, err = archive_call(ws, "tech-demo", blob, container="https://evil.example/distilled-eval")
    R.check(cat, "credential guard", "non-Azure host is refused", code == 2 and not blob.objects, err.strip()[:200])

    blob.fail_put = r"^publications/.*/_COMPLETE\.json$"
    code, _, err = archive_call(ws, "tech-demo", blob)
    R.check(cat, "interrupted archive", "failure writing the final publication marker exits 5", code == 5,
            err.strip()[:200], 5, code)
    R.check(cat, "interrupted archive", "evidence markers exist but no publication marker and no receipt",
            bool(blob.markers("videos/")) and not blob.markers() and not receipt.exists(), actual=blob.markers())
    R.check(cat, "interrupted archive", "error text never contains the SAS signature", FAKE_SIG not in err)
    code, _, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER], blob)
    R.check(cat, "interrupted archive", "cleanup refused after interrupted archive, media intact",
            code == 2 and media_intact(), err.strip()[:200])
    abandoned = len(blob.objects)

    early = FakeBlob()
    early.fail_put = r"^videos/.*/_COMPLETE\.json$"
    code, _, err = archive_call(ws, "tech-demo", early)
    R.check(cat, "interrupted archive", "failure at the first evidence marker exits 5 with no markers",
            code == 5 and not early.markers("videos/") and not early.markers(), err.strip()[:200])
    corrupt = FakeBlob()
    corrupt.corrupt_get = "index.html"
    code, _, err = archive_call(ws, "tech-demo", corrupt)
    R.check(cat, "interrupted archive", "corrupted read-back exits 5 without a marker",
            code == 5 and not corrupt.markers(), err.strip()[:200])
    broken = FakeBlob()
    broken.raise_error = True
    code, _, err = archive_call(ws, "tech-demo", broken)
    R.check(cat, "interrupted archive", "transport error exits 5 and is scrubbed of the SAS",
            code == 5 and FAKE_SIG not in err and "sig=" not in err, err.strip()[:200])

    blob.fail_put = None
    code, data, err = archive_call(ws, "tech-demo", blob)
    R.check(cat, "archive", "rerun after the interruption archives under a new attempt", code == 0 and receipt.exists(),
            err.strip()[:300])
    attempts = {n.split("/")[3] for n in blob.objects if n.startswith("publications/tech-demo/")}
    R.check(cat, "archive", "abandoned and new attempts use distinct prefixes", len(attempts) == 2 and abandoned > 0,
            actual=sorted(attempts))
    rec = read_json(receipt)
    R.check(cat, "archive", "receipt quality approved and package complete",
            rec["marker"]["quality"]["status"] == "approved" and rec["marker"]["quality"]["package_complete"],
            actual=rec["marker"]["quality"])
    leaked = [str(p) for p in ws.rglob("*") if p.is_file() and p.suffix in {".json", ".md", ".html"}
              and FAKE_SIG in p.read_text(errors="ignore")]
    R.check(cat, "credential guard", "SAS never written to workspace files", not leaked, actual=leaked)
    code, data, err = in_process(["verify-archive", "--workspace", ws, "--publication", "tech-demo", "--container",
                                  CONTAINER], blob)
    R.check(cat, "archive", "verify-archive passes", code == 0, err.strip()[:200])

    name = f"publications/tech-demo/{rec['marker']['revision']}/{rec['marker']['attempt']}/files/index.html"
    original = blob.objects[name]
    blob.objects[name] = original + b" "
    code, data, err = in_process(["verify-archive", "--workspace", ws, "--publication", "tech-demo", "--container",
                                  CONTAINER], blob)
    R.check(cat, "remote tamper", "verify-archive detects a modified remote object (exit 1)", code == 1, err.strip()[:200], 1, code)
    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER], blob)
    R.check(cat, "remote tamper", "cleanup refuses while the archive does not verify, media intact",
            code != 0 and media_intact(), err.strip()[:200], "nonzero", code)
    blob.objects[name] = original

    code, _, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container",
                               "https://otheracct.blob.core.windows.net/distilled-eval"], blob)
    R.check(cat, "cleanup binding", "receipt for another container is refused", code == 2 and media_intact(), err.strip()[:200])

    segments = ws / "sources/tech-demo/transcript/segments.json"
    saved = segments.read_bytes()
    segments.write_bytes(saved + b"\n")
    code, _, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER], blob)
    R.check(cat, "cleanup binding", "evidence changed after sign-off blocks cleanup", code == 2 and media_intact(), err.strip()[:200])
    segments.write_bytes(saved)

    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER,
                                  "--dry-run"], blob)
    R.check(cat, "cleanup", "dry run lists media and deletes nothing", code == 0 and media_intact(), err.strip()[:200],
            actual=data)
    others = {rel: sha(ws / rel) for rel in ("sources/ja-talk/media/source.mp4", "sources/bio-a/media/source.mp4")}
    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER], blob)
    gone = [rel for rel in media_rel if not (ws / rel).exists()]
    R.check(cat, "cleanup", "cleanup deletes exactly the tracked tech-demo media", code == 0 and gone == media_rel,
            err.strip()[:200], actual=data)
    R.check(cat, "cleanup", "other videos' media untouched", all(sha(ws / r) == d for r, d in others.items()))
    R.check(cat, "cleanup", "evidence kept", (ws / "sources/tech-demo/transcript/segments.json").exists()
            and (ws / "sources/tech-demo/frames/frames.json").exists())
    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "tech-demo", "--container", CONTAINER], blob)
    R.check(cat, "cleanup", "second cleanup reports already-clean", code == 0 and "already-clean" in json.dumps(data),
            err.strip()[:200], actual=data)
    code, data, err = env.cli("validate", "--workspace", ws, "--require-complete")
    R.check(cat, "cleanup", "validate --require-complete still passes after cleanup", code == 0, err.strip()[:300],
            actual=data and data.get("errors"))
    code, data, err = env.cli("render", "--workspace", ws, "--publication", "tech-demo")
    R.check(cat, "cleanup", "render still works from evidence after cleanup", code == 0, err.strip()[:300])

    ja_blob = FakeBlob()
    code, data, err = archive_call(ws, "ja-talk", ja_blob)
    rec = read_json(ws / "publications/ja-talk/archive-receipt.json") if code == 0 else {}
    R.check(cat, "blocked sign-off", "blocked package can be archived and the receipt says blocked",
            code == 0 and rec.get("marker", {}).get("quality", {}).get("status") == "blocked", err.strip()[:200],
            actual=rec.get("marker", {}).get("quality"))
    code, _, err = in_process(["cleanup", "--workspace", ws, "--publication", "ja-talk", "--container", CONTAINER], ja_blob)
    R.check(cat, "blocked sign-off", "cleanup refused for a blocked sign-off, media intact",
            code == 2 and (ws / "sources/ja-talk/media/source.mp4").exists(), err.strip()[:200])

    bio_blob = FakeBlob()
    code, data, err = archive_call(ws, "g-bio", bio_blob)
    R.check(cat, "group archive", "g-bio archives with per-video evidence markers",
            code == 0 and len([n for n in bio_blob.objects if n.startswith("videos/") and n.endswith("_COMPLETE.json")]) == 2,
            err.strip()[:200])
    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "g-bio", "--container", CONTAINER], bio_blob)
    R.check(cat, "group archive", "cleanup of g-bio removes both members' media only",
            code == 0 and not (ws / "sources/bio-a/media/source.mp4").exists()
            and not (ws / "sources/bio-b/audio/audio.flac").exists()
            and (ws / "sources/ja-talk/media/source.mp4").exists(), err.strip()[:200])


def scenario_retention(env, media, browser):
    cat = "archive and cleanup"
    if not browser:
        R.not_run(cat, "retention", "needs a real PDF for an approved sign-off")
        return
    ws = env.out / "ws-retain"
    assignment = {"schema_version": 1, "videos": [read_json(FIX / "assignment.json")["videos"][1]], "retain_media": True}
    path = write_json(env.out / "retain-assignment.json", assignment)
    steps = [("init", "--assignment", path),
             ("download", "--video", "ja-talk", "--from-file", media["ja-talk"]),
             ("frames", "--video", "ja-talk", "--interval", "5"),
             ("import-transcript", "--video", "ja-talk", "--transcript", FIX / "transcripts/ja-talk.json"),
             ("select-frames", "--video", "ja-talk", "--frames", "f000015000,f000025000")]
    for cmd, *rest in steps:
        code, _, err = env.cli(cmd, "--workspace", ws, *rest)
        if code != 0:
            R.check(cat, "retention", f"setup {cmd}", False, err.strip()[:200])
            return
    code, _, err = env.cli("budget", "reserve", "--workspace", ws, "--step", "transcription", "--provider", "p",
                           "--amount", "0.01", "--approval", "none", "--video", "ja-talk")
    R.check("budget", "no budgets", "reserve without approved budgets is refused (exit 4)", code == 4, err.strip()[:200], 4, code)
    copy_article(ws, "ja-talk")
    for cmd, *rest in [("render",), ("pdf", "--browser", browser), ("package",)]:
        code, _, err = env.cli(cmd, "--workspace", ws, "--publication", "ja-talk", *rest, timeout=300)
        if code != 0:
            R.check(cat, "retention", f"setup {cmd}", False, err.strip()[:200])
            return
    review = write_json(env.out / "reviews/retain-ja.json", read_json(FIX / "reviews/ja-talk.json"))
    code, _, err = env.cli("signoff", "--workspace", ws, "--publication", "ja-talk", "--review", review)
    R.check(cat, "retention", "approved sign-off in retention workspace", code == 0, err.strip()[:200])
    blob = FakeBlob()
    code, _, err = archive_call(ws, "ja-talk", blob)
    R.check(cat, "retention", "archive succeeds with retain_media", code == 0, err.strip()[:200])
    code, data, err = in_process(["cleanup", "--workspace", ws, "--publication", "ja-talk", "--container", CONTAINER], blob)
    R.check(cat, "retention", "cleanup returns retained and deletes nothing",
            code == 0 and data.get("status") == "retained" and (ws / "sources/ja-talk/media/source.mp4").exists(),
            err.strip()[:200], actual=data)


# ---------------------------------------------------------------------------
# Live YouTube feasibility probe (optional, no paid calls, no accuracy scoring)


def classify_ytdlp_error(text):
    t = text.lower()
    if any(k in t for k in ("video unavailable", "private video", "has been removed", "does not exist",
                            "this video is not available")):
        return "reported-unavailable-by-youtube"
    if any(k in t for k in ("sign in to confirm", "login required", "age-restricted")):
        return "access-control (not bypassed)"
    if "429" in t or "too many requests" in t:
        return "http-429 rate limited (not evidence the video is missing)"
    if "403" in t or "forbidden" in t:
        return "http-403 (blocked or missing JS challenge solver; not evidence the video is missing)"
    if any(k in t for k in ("timed out", "timeout", "getaddrinfo", "name or service not known", "unable to download webpage",
                            "connection", "network is unreachable")):
        return "network (not evidence the video is missing)"
    return "other"


def captions_to_transcript(json3, video_id, duration):
    events = [e for e in json3.get("events", []) if e.get("segs")]
    rows = []
    for e in events:
        text = "".join(s.get("utf8", "") for s in e["segs"]).replace("\n", " ").strip()
        if not text:
            continue
        rows.append([e["tStartMs"] / 1000, (e["tStartMs"] + e.get("dDurationMs", 0)) / 1000, text])
    rows.sort(key=lambda r: r[0])
    segments = []
    for i, (start, end, text) in enumerate(rows):
        if i + 1 < len(rows):
            end = min(end, rows[i + 1][0])
        end = min(end, duration)
        if end - start < 0.01:
            continue
        segments.append({"id": f"c{len(segments) + 1:04d}", "start": round(start, 3), "end": round(end, 3),
                         "text": text, "english": text})
    return {"schema_version": 1, "video_id": video_id, "language": "en",
            "provider": {"name": "youtube-automatic-captions", "kind": "captions"},
            "duration": duration,
            "notes": "Automatic captions converted mechanically by the eval harness; not checked against audio.",
            "segments": segments}


def scenario_live(env, url, timeout, captions_file=None):
    cat = "live YouTube probe"
    ytdlp = env.bin_dir / "yt-dlp"
    if not ytdlp.exists():
        R.not_run(cat, url, "yt-dlp not available")
        return
    ws = env.out / "ws-live"
    probe = env.out / "live"
    probe.mkdir(parents=True, exist_ok=True)
    base_env = {"PATH": f"{env.bin_dir}:/usr/bin:/bin", "HOME": str(env.home)}
    start = time.time()
    try:
        meta = subprocess.run([str(ytdlp), "--ignore-config", "--no-playlist", "--skip-download", "--dump-single-json", "--socket-timeout",
                               "20", "--", url], capture_output=True, text=True, timeout=timeout, env=base_env)
        meta_code, meta_err = meta.returncode, meta.stderr
    except subprocess.TimeoutExpired:
        meta_code, meta_err, meta = None, "timed out", None
    elapsed = round(time.time() - start, 1)
    if meta_code != 0:
        R.note(cat, url, "metadata", f"failed after {elapsed}s: {classify_ytdlp_error(meta_err)}: {meta_err.strip()[-300:]}")
        R.not_run(cat, url, "download, frames, captions skipped because metadata failed")
        return
    info = json.loads(meta.stdout)
    R.note(cat, url, "metadata", {"elapsed_s": elapsed, "id": info.get("id"), "title": info.get("title"),
                                  "uploader": info.get("uploader"), "duration": info.get("duration"),
                                  "availability": info.get("availability"),
                                  "automatic_caption_languages": len(info.get("automatic_captions") or {}),
                                  "manual_caption_languages": sorted((info.get("subtitles") or {}).keys())})
    youtube_id = info["id"]
    write_json(probe / "assignment.json", {"schema_version": 1, "videos": [{"id": "live", "url": url}]})
    env.cli("init", "--workspace", ws, "--assignment", probe / "assignment.json")
    # The CLI ignores yt-dlp config files; a runtime is chosen only with --js-runtime.
    attempts = [("yt-dlp default JavaScript runtime", [], [])]
    node = shutil.which("node") or ("/opt/homebrew/bin/node" if Path("/opt/homebrew/bin/node").exists() else None)
    if node:
        attempts.append(("--js-runtime node", ["--js-runtime", "node", "--js-runtime-path", node],
                         ["--no-js-runtimes", "--js-runtimes", f"node:{node}"]))
    downloaded = downloaded_with_runtime = False
    for label, flags, _ in attempts:
        start = time.time()
        try:
            code, data, err = env.cli("download", "--workspace", ws, "--video", "live", *flags,
                                      "--timeout", str(int(timeout)), timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            code, data, err = None, None, "timed out"
        elapsed = round(time.time() - start, 1)
        if code == 0:
            R.note(cat, url, f"CLI download ({label})", f"ok in {elapsed}s: duration {data.get('duration')}; "
                   f"runtime {data.get('js_runtime')}; warnings {data.get('warnings')}")
            downloaded = True
            downloaded_with_runtime = bool(flags)
            break
        R.note(cat, url, f"CLI download ({label})",
               f"exit {code} after {elapsed}s: {classify_ytdlp_error(err)}: {err.strip()[-200:]}")
    if not downloaded:
        R.not_run(cat, url, "frames and caption import skipped because download failed")
        return
    source = read_json(ws / "sources/live/source.json")
    start = time.time()
    code, data, err = env.cli("frames", "--workspace", ws, "--video", "live", "--interval", "30", "--max-frames", "60",
                              timeout=timeout)
    R.note(cat, url, "frames (periodic 30 s, real ffmpeg)",
           f"exit {code} in {round(time.time() - start, 1)}s: {data.get('frames') if data else err.strip()[-200:]}")
    caps = probe / "caps"
    try:
        runtime_flags = attempts[-1][2] if downloaded_with_runtime else []
        cap = subprocess.run([str(ytdlp), "--ignore-config", *runtime_flags, "--skip-download", "--write-auto-subs", "--sub-langs", "en", "--sub-format",
                              "json3", "-o", str(caps / "%(id)s"), "--", url], capture_output=True, text=True,
                             timeout=timeout, env=base_env)
        cap_files = sorted(caps.glob(f"{youtube_id}*.json3"))
    except subprocess.TimeoutExpired:
        cap_files, cap = [], None
    if not cap_files:
        reason = cap.stderr.strip() if cap else "timed out"
        R.note(cat, url, "captions fetch", f"failed: {classify_ytdlp_error(reason)}: {reason[-160:]}")
        if not captions_file:
            return
        cap_files = [Path(captions_file)]
        R.note(cat, url, "captions fetch", f"using previously fetched captions file {captions_file}")
    else:
        R.note(cat, url, "captions fetch", f"ok: {cap_files[0].name}")
    transcript = captions_to_transcript(json.loads(cap_files[0].read_text()), "live", float(source["duration"]))
    path = write_json(probe / "captions-transcript.json", transcript)
    code, data, err = env.cli("import-transcript", "--workspace", ws, "--video", "live", "--transcript", path)
    coverage = read_json(ws / "sources/live/transcript/coverage.json") if code == 0 else {}
    R.note(cat, url, "captions route import",
           f"exit {code}; {len(transcript['segments'])} segments; covered {coverage.get('covered_seconds')} of "
           f"{coverage.get('duration')} s; gaps {len(coverage.get('gaps', []))}; warnings {coverage.get('warnings')}"
           + ("" if code == 0 else f"; {err.strip()[-200:]}"))
    R.note(cat, url, "not measured", "caption/transcription accuracy and translation fidelity: no reference transcript")


# ---------------------------------------------------------------------------


def write_summary(out, extra):
    cats = R.summary()
    lines = ["# distilling-videos evaluation results", "",
             f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}. Counts are per category; "
             "they are not one quality score.", "", "| Category | pass | fail | not run | observed |",
             "| --- | --- | --- | --- | --- |"]
    for cat, c in cats.items():
        lines.append(f"| {cat} | {c['pass']} | {c['fail']} | {c['not-run']} | {c['observed']} |")
    fails = [r for r in R.rows if r["outcome"] == "fail"]
    lines += ["", "## Failures", ""] + ([f"- {r['category']} / {r['scenario']}: {r['check']} ({r['detail']})" for r in fails]
                                        or ["None."])
    notes = [r for r in R.rows if r["outcome"] in ("observed", "not-run")]
    lines += ["", "## Observations and not-run items", ""] + [
        f"- {r['category']} / {r['scenario']}: {r['check']}: {json.dumps(r['detail'], ensure_ascii=False)[:400]}" for r in notes]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    write_json(out / "results.json", {"schema_version": 1, "summary": cats, "environment": extra, "rows": R.rows})
    return cats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(REPO / ".amp/in/eval-run"), help="output directory (recreated)")
    parser.add_argument("--tools-bin", help="directory with ffmpeg, ffprobe, and optionally yt-dlp")
    parser.add_argument("--browser", help="Chromium-family browser for PDF (omit to skip PDF and archive approval)")
    parser.add_argument("--capture", action="store_true", help="run capture.mjs (needs node and --browser)")
    parser.add_argument("--live-youtube", help="public YouTube URL for the optional feasibility probe")
    parser.add_argument("--live-timeout", type=int, default=180)
    parser.add_argument("--live-captions-json3", help="fallback json3 captions file if the live caption fetch fails")
    args = parser.parse_args(argv)

    out = Path(args.out).resolve()
    if out.exists():
        if not (out / MARKER).exists():
            parser.error(f"{out} exists and was not created by this harness; refusing to delete it")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("created by evals/distilling-videos/run_eval.py\n")
    bin_dir, found = prepare_bin(out, args.tools_bin)
    env = Env(out, bin_dir)
    environment = {"python": sys.version.split()[0], "tools": found, "browser": args.browser,
                   "platform": sys.platform}
    if not {"ffmpeg", "ffprobe"} <= set(found):
        R.not_run("evidence", "all", "ffmpeg/ffprobe not found; pass --tools-bin")
        write_summary(out, environment)
        return 3
    spec = read_json(FIX / "media.json")
    gt = read_json(FIX / "ground-truth.json")
    media_dir = out / "media"
    media_dir.mkdir()
    media = {vid: render_media(spec, vid, found["ffmpeg"], media_dir) for vid in spec["videos"]}

    scenario_contracts(env)
    ws = scenario_evidence(env, spec, gt, media)
    scenario_budget(env, ws)
    scenario_publication(env, ws, args.browser)
    scenario_editorial(env, ws, spec, gt)
    scenario_signoff(env, ws, args.browser)
    scenario_archive(env, ws, args.browser)
    scenario_retention(env, media, args.browser)
    if args.capture:
        node = shutil.which("node") or ("/opt/homebrew/bin/node" if Path("/opt/homebrew/bin/node").exists() else None)
        if node and args.browser:
            shots = out / "captures"
            pubs = [str(ws / f"publications/{p}/dist") for p in ("tech-demo", "ja-talk", "g-bio")]
            result = subprocess.run([node, str(HERE / "capture.mjs"), args.browser, str(shots), *pubs],
                                    capture_output=True, text=True, timeout=600)
            report = read_json(shots / "report.json") if (shots / "report.json").exists() else {}
            R.check("rendered pages", "capture", "capture script ran", result.returncode == 0, result.stderr.strip()[-400:])
            for page, rep in report.items():
                for name, ok in rep.get("checks", {}).items():
                    R.check("rendered pages", page, name, bool(ok), json.dumps(rep.get("details", {}).get(name, ""))[:300])
        else:
            R.not_run("rendered pages", "capture", "needs node and --browser")
    else:
        R.not_run("rendered pages", "capture", "pass --capture to drive a real browser")
    if args.live_youtube:
        scenario_live(env, args.live_youtube, args.live_timeout, args.live_captions_json3)
    cats = write_summary(out, environment)
    print(json.dumps(cats, indent=2))
    print(f"results: {out / 'results.json'}\nsummary: {out / 'summary.md'}")
    return 1 if any(c["fail"] for c in cats.values()) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""distilling-videos evidence CLI (schema_version 1).

Commands: init, download, frames, import-transcript, select-frames, validate, budget.
Optional sibling modules publication.py and archive.py add commands by defining
register(subparsers); see ../reference/contracts.md ("CLI extensions").

Exit codes: 0 ok, 1 validation failed, 2 contract/usage error, 3 missing tool,
4 budget refused, 5 external tool or download failure.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evidence  # noqa: E402
from evidence import ContractError, Workspace  # noqa: E402

EXTENSION_MODULES = ("publication", "archive")
DEFAULT_FORMAT = "bv*[height<=1080]+ba/b[height<=1080]/b"
THUMB_WIDTH = 480
# yt-dlp solves YouTube JavaScript challenges with an external runtime (upstream EJS guide:
# https://github.com/yt-dlp/yt-dlp/wiki/EJS). The solver scripts come from the yt-dlp-ejs package, which
# the pip `yt-dlp[default]` extra installs (bootstrap.sh). Only deno is enabled by default. Bun is deprecated upstream
# and runs scripts without permission restrictions, so it is not offered.
JS_RUNTIMES = {"deno": "deno", "node": "node", "quickjs": "qjs"}
DOWNLOAD_TIMEOUT = 1800.0
MAX_DOWNLOAD_TIMEOUT = 6 * 3600.0
SECRET_ENV = re.compile(r"(SAS|SECRET|TOKEN|PASSWORD|API_KEY|ACCESS_KEY|CONNECTION_STRING|AZURE_STORAGE)",
                        re.IGNORECASE)


class MissingTool(Exception):
    pass


class ToolFailed(Exception):
    pass


# ---------------------------------------------------------------------------
# Subprocess helpers (argument arrays only, never shell strings)


def child_env() -> Dict[str, str]:
    """Environment for media tools without credential-like variables."""
    return {k: v for k, v in os.environ.items() if not SECRET_ENV.search(k)}


def require_tools(names: Sequence[str]) -> Dict[str, str]:
    found = {name: shutil.which(name) for name in names}
    missing = [name for name, path in found.items() if not path]
    if missing:
        raise MissingTool(f"missing required tool(s): {', '.join(missing)}. Install them (for example "
                          "`brew install yt-dlp ffmpeg` or `pipx install yt-dlp`), then rerun; "
                          "workspace state is preserved for resume.")
    return {name: str(path) for name, path in found.items()}


def run(command: List[str], timeout: Optional[float] = None) -> subprocess.CompletedProcess:
    """Run an argument array with no stdin; on timeout, kill the tool and any children it started."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=child_env(), start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise ToolFailed(f"{Path(command[0]).name} timed out after {timeout}s") from None
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if result.returncode != 0:
        detail = evidence.redact((result.stderr or result.stdout or "").strip())[-1500:]
        raise ToolFailed(f"{Path(command[0]).name} exited {result.returncode}: {detail}")
    return result


def tool_versions(tools: Dict[str, str]) -> Dict[str, str]:
    versions = {}
    for name, path in tools.items():
        flag = "--version" if name == "yt-dlp" else "-version"
        output = run([path, flag], timeout=60).stdout.strip().splitlines()
        versions[name] = output[0] if output else "unknown"
    return versions


def emit(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def replace_dir(partial: Path, final: Path) -> None:
    old = final.with_name(f".{final.name}-old-{os.getpid()}")
    if final.exists():
        os.replace(final, old)
    os.replace(partial, final)
    remove_tree(old)


# ---------------------------------------------------------------------------
# Commands


def cmd_init(args: argparse.Namespace) -> int:
    status = evidence.init_workspace(Path(args.workspace), evidence.read_json(Path(args.assignment)))
    workspace = Workspace(Path(args.workspace))
    emit({"status": status, "workspace": str(workspace.root),
          "publications": [p["id"] for p in workspace.assignment()["publications"]]})
    return 0


def _complete_record(workspace: Workspace, key: str, hint: str) -> Dict[str, Any]:
    record = workspace.state()["stages"].get(key)
    if not record or record.get("status") != "complete":
        raise ContractError(f"{key} is not complete; {hint}")
    problems = evidence.stage_problems(workspace, key, record)
    if problems:
        raise ContractError(problems + [hint])
    return record


def js_runtime(args: argparse.Namespace) -> Optional[Dict[str, str]]:
    """Resolve the requested yt-dlp JavaScript runtime to an absolute executable, or None for yt-dlp's default."""
    if args.js_runtime_path and not args.js_runtime:
        raise ContractError("--js-runtime-path needs --js-runtime (deno, node, or quickjs)")
    if not args.js_runtime:
        return None
    if args.js_runtime_path:
        path = Path(args.js_runtime_path)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ContractError(f"--js-runtime-path must be an absolute path to an executable file: {path}")
        return {"name": args.js_runtime, "path": str(path)}
    found = shutil.which(JS_RUNTIMES[args.js_runtime])
    if not found:
        raise MissingTool(f"JavaScript runtime {args.js_runtime} ({JS_RUNTIMES[args.js_runtime]}) is not on PATH; "
                          "install it or pass --js-runtime-path; see bootstrap.sh")
    return {"name": args.js_runtime, "path": str(Path(found).resolve())}


def ytdlp_base(ytdlp: str, runtime: Optional[Dict[str, str]]) -> List[str]:
    """yt-dlp options shared by every call: no user/system config files, one explicit JS runtime when chosen."""
    command = [ytdlp, "--ignore-config", "--no-playlist"]
    if runtime:
        command += ["--no-js-runtimes", "--js-runtimes", f"{runtime['name']}:{runtime['path']}"]
    return command


def tool_warnings(*results: subprocess.CompletedProcess) -> List[str]:
    found: List[str] = []
    for result in results:
        for line in (result.stderr or "").splitlines():
            line = evidence.redact(line.strip())[:500]
            if line.startswith("WARNING:") and line not in found:
                found.append(line)
    return found


def cmd_download(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    video = workspace.video(args.video)
    key = evidence.stage_key(video["id"], "download")
    source_dir = workspace.source_dir(video["id"])
    if not 0 < args.timeout <= MAX_DOWNLOAD_TIMEOUT:
        raise ContractError(f"--timeout must be between 1 and {int(MAX_DOWNLOAD_TIMEOUT)} seconds")
    config: Dict[str, Any] = {"url": video["url"], "format": args.format, "audio": "flac-16k-mono"}
    if args.from_file:
        if args.js_runtime or args.js_runtime_path:
            raise ContractError("--js-runtime applies to yt-dlp downloads, not --from-file")
        local = Path(args.from_file)
        if not local.is_file():
            raise ContractError(f"--from-file does not exist: {local}")
        config = {"from_file_sha256": evidence.sha256_file(local), "url": video["url"], "audio": "flac-16k-mono"}
    names = ["ffprobe", "ffmpeg"] if args.from_file else ["yt-dlp", "ffprobe", "ffmpeg"]
    try:
        runtime = None if args.from_file else js_runtime(args)
        tools = require_tools(names)
    except MissingTool as error:
        evidence.mark_failed(workspace, key, str(error))
        raise
    if not args.from_file:
        config["js_runtime"] = runtime or {"name": "yt-dlp-default"}
    if evidence.reusable(workspace, key, {}, config):
        emit({"status": "reused", "stage": key})
        return 0
    evidence.mark_running(workspace, key, config)
    partial = source_dir / f".download-partial-{os.getpid()}"
    remove_tree(partial)
    try:
        (partial / "media").mkdir(parents=True)
        (partial / "audio").mkdir()
        versions = tool_versions(tools)
        warnings: List[str] = []
        runtime_record = None
        if runtime:
            try:
                lines = run([runtime["path"], "--version"], timeout=60).stdout.strip().splitlines()
            except ToolFailed:
                lines = []
            runtime_record = {**runtime, "version": lines[0][:100] if lines else "unknown"}
        if args.from_file:
            metadata: Dict[str, Any] = {}
            suffix = Path(args.from_file).suffix.lower() or ".mp4"
            if not re.match(r"^\.[a-z0-9]{1,5}$", suffix):
                raise ContractError(f"unsupported media suffix {suffix!r}")
            shutil.copyfile(args.from_file, partial / "media" / f"source{suffix}")
        else:
            base = ytdlp_base(tools["yt-dlp"], runtime)
            probed = run(base + ["--skip-download", "--dump-single-json", "--", video["url"]],
                         timeout=min(300.0, args.timeout))
            metadata = json.loads(probed.stdout)
            fetched = run(base + ["--no-progress", "-f", args.format, "--merge-output-format", "mp4",
                                  "-o", str(partial / "media" / "source.%(ext)s"), "--", video["url"]],
                          timeout=args.timeout)
            warnings = tool_warnings(probed, fetched)
        produced = sorted(p for p in (partial / "media").iterdir() if p.is_file() and p.name.startswith("source."))
        if len(produced) != 1:
            raise ToolFailed(f"expected one downloaded media file, found {[p.name for p in produced]}")
        media = produced[0]
        probe = json.loads(run([tools["ffprobe"], "-v", "error", "-print_format", "json", "-show_format",
                                "-show_streams", str(media)], timeout=300).stdout)
        run([tools["ffmpeg"], "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(media),
             "-vn", "-ac", "1", "-ar", "16000", str(partial / "audio" / "audio.flac")], timeout=args.timeout)
        duration = probe.get("format", {}).get("duration") or metadata.get("duration")
        if duration is None:
            raise ToolFailed("could not determine media duration")
        streams = probe.get("streams", [])
        picture = next((s for s in streams if s.get("codec_type") == "video"), {})
        source = {
            "schema_version": evidence.SCHEMA_VERSION, "video_id": video["id"], "url": video["url"],
            "youtube_id": video["youtube_id"],
            "extractor": "local-file" if args.from_file else "yt-dlp",
            "title": metadata.get("title") or video.get("title"),
            "creator": metadata.get("uploader") or metadata.get("channel"),
            "channel_id": metadata.get("channel_id"), "upload_date": metadata.get("upload_date"),
            "duration": float(duration), "language": metadata.get("language"),
            "captions": {"manual": sorted((metadata.get("subtitles") or {}).keys()),
                         "automatic": sorted((metadata.get("automatic_captions") or {}).keys()),
                         "note": "Caption availability only; captions are unverified inputs."},
            "media": {"path": f"media/{media.name}", "width": picture.get("width"),
                      "height": picture.get("height"), "has_audio": any(s.get("codec_type") == "audio"
                                                                       for s in streams)},
            "audio": {"path": "audio/audio.flac", "sample_rate": 16000, "channels": 1},
            "tool_versions": versions, "retrieved_at": evidence.now(),
        }
        if not args.from_file:
            source["js_runtime"] = runtime_record or {"name": "yt-dlp-default"}
            source["warnings"] = warnings
        evidence.atomic_write_json(partial / "source.json", source)
        for name in ("media", "audio"):
            replace_dir(partial / name, source_dir / name)
        os.replace(partial / "source.json", source_dir / "source.json")
        remove_tree(partial)
        outputs = evidence.file_digests(source_dir, [f"media/{media.name}", "audio/audio.flac", "source.json"])
        rel = f"sources/{video['id']}"
        evidence.mark_complete(workspace, key, config, {}, outputs, {"tool_versions": versions},
                               temporary_media=[f"{rel}/media/{media.name}", f"{rel}/audio/audio.flac"])
    except BaseException as error:
        remove_tree(partial)
        evidence.mark_failed(workspace, key, str(error) or type(error).__name__)
        raise
    render_markdown(workspace, video["id"], quiet=True)
    result = {"status": "downloaded", "stage": key, "duration": source["duration"], "outputs": outputs}
    if not args.from_file:
        result.update(js_runtime=source["js_runtime"], warnings=source["warnings"])
    emit(result)
    return 0


def scene_cues(ffmpeg: str, media: Path, threshold: float) -> List[float]:
    result = run([ffmpeg, "-nostdin", "-hide_banner", "-i", str(media), "-vf",
                  f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"])
    return sorted({round(float(t), 3) for t in re.findall(r"pts_time:(\d+(?:\.\d+)?)", result.stderr)})


def cmd_frames(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    video = workspace.video(args.video)
    key = evidence.stage_key(video["id"], "frames")
    source_dir = workspace.source_dir(video["id"])
    download = _complete_record(workspace, evidence.stage_key(video["id"], "download"),
                                "run `distill.py download` first")
    source = evidence.read_json(source_dir / "source.json")
    media_rel = source["media"]["path"]
    if args.max_frames < 1 or args.max_frames > 5000:
        raise ContractError("--max-frames must be between 1 and 5000")
    if args.scene_threshold is not None and not 0 < args.scene_threshold < 1:
        raise ContractError("--scene-threshold must be between 0 and 1")
    dense = [evidence.parse_dense(spec) for spec in args.dense]
    config = {"interval": args.interval, "dense": dense, "cues": sorted(args.at),
              "scene_threshold": args.scene_threshold, "max_frames": args.max_frames, "thumb_width": THUMB_WIDTH}
    inputs = {media_rel: download["outputs"][media_rel]}
    try:
        tools = require_tools(["ffmpeg"])
    except MissingTool as error:
        evidence.mark_failed(workspace, key, str(error))
        raise
    if evidence.reusable(workspace, key, inputs, config):
        emit({"status": "reused", "stage": key})
        return 0
    media = source_dir / media_rel
    duration = float(source["duration"])
    scene = scene_cues(tools["ffmpeg"], media, args.scene_threshold) if args.scene_threshold else []
    plan = evidence.frame_plan(duration, args.interval, dense, list(args.at), scene, args.max_frames)
    evidence.mark_running(workspace, key, config)
    partial = source_dir / f".frames-partial-{os.getpid()}"
    remove_tree(partial)
    try:
        (partial / "full").mkdir(parents=True)
        (partial / "thumbs").mkdir()
        for frame in plan:
            full, thumb = partial / "full" / f"{frame['id']}.jpg", partial / "thumbs" / f"{frame['id']}.jpg"
            run([tools["ffmpeg"], "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{frame['t']:.3f}", "-i", str(media),
                 "-frames:v", "1", "-q:v", "2", str(full),
                 "-frames:v", "1", "-vf", f"scale={THUMB_WIDTH}:-2", "-q:v", "4", str(thumb)], timeout=300)
            if not full.is_file() or not thumb.is_file():
                raise ToolFailed(f"ffmpeg produced no frame at {frame['t']}s")
            frame.update(path=f"frames/full/{frame['id']}.jpg", thumbnail=f"frames/thumbs/{frame['id']}.jpg",
                         sha256=evidence.sha256_file(full), thumbnail_sha256=evidence.sha256_file(thumb))
        manifest = {
            "schema_version": evidence.SCHEMA_VERSION, "video_id": video["id"], "duration": duration,
            "media_sha256": inputs[media_rel],
            "selection": {"method": "periodic+dense+cues" + ("+scene" if args.scene_threshold else ""),
                          **config, "scene_cues_found": scene, "semantic_completeness": False,
                          "note": "Candidate frames from bounded sampling; not exhaustive frame-by-frame "
                                  "semantic analysis. Fleeting or unreadable content may be missed."},
            "max_sampling_gap_seconds": evidence.frame_gaps(plan, duration),
            "frames": plan,
        }
        evidence.atomic_write_json(partial / "frames.json", manifest)
        replace_dir(partial, source_dir / "frames")
        rels = ["frames/frames.json"] + [f[k] for f in plan for k in ("path", "thumbnail")]
        evidence.mark_complete(workspace, key, config, inputs, evidence.file_digests(source_dir, rels))
    except BaseException as error:
        remove_tree(partial)
        evidence.mark_failed(workspace, key, str(error) or type(error).__name__)
        raise
    render_markdown(workspace, video["id"], quiet=True)
    emit({"status": "extracted", "stage": key, "frames": len(plan),
          "max_sampling_gap_seconds": manifest["max_sampling_gap_seconds"]})
    return 0


TRANSCRIPT_NORMALIZER = 2
MARKDOWN_RENDERER = 2


def cmd_import_transcript(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    video = workspace.video(args.video)
    key = evidence.stage_key(video["id"], "transcript")
    source_dir = workspace.source_dir(video["id"])
    raw = Path(args.transcript).read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"transcript is not UTF-8 JSON: {error}") from None
    duration = args.duration
    inputs: Dict[str, str] = {}
    if (source_dir / "source.json").is_file():
        inputs["source.json"] = evidence.sha256_file(source_dir / "source.json")
        if duration is None:
            duration = float(evidence.read_json(source_dir / "source.json")["duration"])
    normalized = evidence.validate_transcript(data, video["id"], duration)
    # normalizer 2 derives english_label from english_kind; a bump re-normalizes unchanged inputs.
    config = {"input_sha256": evidence.sha256_bytes(raw), "duration": duration,
              "gap_threshold": evidence.GAP_THRESHOLD, "normalizer": TRANSCRIPT_NORMALIZER}
    if evidence.reusable(workspace, key, inputs, config):
        render_markdown(workspace, video["id"], quiet=True)
        emit({"status": "reused", "stage": key})
        return 0
    evidence.mark_running(workspace, key, config)
    try:
        directory = source_dir / "transcript"
        evidence.atomic_write_bytes(directory / "input.json", raw)
        evidence.atomic_write_json(directory / "segments.json", normalized)
        coverage = evidence.transcript_coverage(normalized)
        evidence.atomic_write_json(directory / "coverage.json", coverage)
        outputs = evidence.file_digests(source_dir, ["transcript/input.json", "transcript/segments.json",
                                                     "transcript/coverage.json"])
        evidence.mark_complete(workspace, key, config, inputs, outputs,
                               {"provider": normalized["provider"], "language": normalized["language"]})
    except BaseException as error:
        evidence.mark_failed(workspace, key, str(error) or type(error).__name__)
        raise
    render_markdown(workspace, video["id"], quiet=True)
    emit({"status": "imported", "stage": key, "segments": coverage["segment_count"],
          "gaps": coverage["gaps"], "uncertain_segment_ids": coverage["uncertain_segment_ids"],
          "warnings": coverage["warnings"]})
    return 0


def cmd_select_frames(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    video = workspace.video(args.video)
    source_dir = workspace.source_dir(video["id"])
    _complete_record(workspace, evidence.stage_key(video["id"], "frames"), "run `distill.py frames` first")
    manifest = evidence.read_json(source_dir / "frames" / "frames.json")
    known = {f["id"] for f in manifest["frames"]}
    ids = [i.strip() for i in args.frames.split(",") if i.strip()]
    unknown = [i for i in ids if i not in known]
    if not ids or unknown:
        raise ContractError(f"unknown or missing frame ids: {unknown or args.frames!r}")
    key = evidence.stage_key(video["id"], "frame-selection")
    inputs = evidence.file_digests(source_dir, ["frames/frames.json"])
    selection = {"schema_version": evidence.SCHEMA_VERSION, "video_id": video["id"],
                 "frame_ids": list(dict.fromkeys(ids)), "note": args.note, "selected_at": evidence.now()}
    evidence.atomic_write_json(source_dir / "selection.json", selection)
    evidence.mark_complete(workspace, key, {"frame_ids": selection["frame_ids"]}, inputs,
                           evidence.file_digests(source_dir, ["selection.json"]))
    rendered = render_markdown(workspace, video["id"], quiet=True)
    emit({"status": "selected", "frame_ids": selection["frame_ids"], "markdown": rendered})
    return 0


def render_markdown(workspace: Workspace, video_id: str, quiet: bool = False) -> str:
    """(Re)render original.md and english.md when a valid transcript exists."""
    key = evidence.stage_key(video_id, "transcript-markdown")
    source_dir = workspace.source_dir(video_id)
    stages = workspace.state()["stages"]
    transcript = stages.get(evidence.stage_key(video_id, "transcript"))
    if not transcript or transcript.get("status") != "complete":
        return "skipped: no transcript"
    if evidence.stage_problems(workspace, evidence.stage_key(video_id, "transcript"), transcript):
        return "skipped: transcript is stale; rerun import-transcript"
    candidates = ["transcript/segments.json", "source.json"]
    frames_record = stages.get(evidence.stage_key(video_id, "frames"))
    if frames_record and frames_record.get("status") == "complete":
        candidates.append("frames/frames.json")
        selection_record = stages.get(evidence.stage_key(video_id, "frame-selection"))
        if selection_record and selection_record.get("status") == "complete":
            candidates.append("selection.json")
    inputs = evidence.file_digests(source_dir, [c for c in candidates if (source_dir / c).is_file()])
    if evidence.reusable(workspace, key, inputs, {"renderer": MARKDOWN_RENDERER}):
        return "reused"
    segments = evidence.read_json(source_dir / "transcript" / "segments.json")
    source = evidence.read_json(source_dir / "source.json") if "source.json" in inputs else {}
    frames = evidence.read_json(source_dir / "frames" / "frames.json") if "frames/frames.json" in inputs else None
    selection = (evidence.read_json(source_dir / "selection.json")["frame_ids"]
                 if "selection.json" in inputs else None)
    documents = evidence.render_transcripts(source, workspace.video(video_id), segments, frames, selection)
    for name, text in documents.items():
        evidence.atomic_write_text(source_dir / "transcript" / name, text)
    evidence.mark_complete(workspace, key, {"renderer": MARKDOWN_RENDERER}, inputs,
                           evidence.file_digests(source_dir, [f"transcript/{n}" for n in documents]))
    return "rendered"


REQUIRED_STAGES = ("download", "frames", "transcript", "transcript-markdown")


def cmd_validate(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    errors: List[str] = []
    warnings: List[str] = []
    try:
        assignment = workspace.assignment()
        state = workspace.state()
    except ContractError as error:
        emit({"ok": False, "errors": error.problems, "warnings": []})
        return 1
    if state.get("assignment_sha256") != evidence.digest_json(assignment):
        errors.append("state.json assignment_sha256 does not match assignment.json")
    selected = args.video or [v["id"] for v in assignment["videos"]]
    for video_id in selected:
        workspace.video(video_id)
    videos: Dict[str, Dict[str, str]] = {v: {} for v in selected}
    for key, record in sorted(state["stages"].items()):
        parts = key.split("/")
        if len(parts) != 3 or parts[0] != "sources":
            errors.append(f"unexpected stage key {key!r}")
            continue
        if parts[1] not in videos:
            continue
        status = record.get("status")
        videos[parts[1]][parts[2]] = status
        if status == "complete":
            errors += evidence.stage_problems(workspace, key, record)
        elif status == "running":
            warnings.append(f"{key}: interrupted or in progress; output is not complete")
        else:
            warnings.append(f"{key}: {status}: {record.get('error', '')}")
    for video_id, stages in videos.items():
        source_dir = workspace.source_dir(video_id)
        if stages.get("frame-selection") == "complete" and stages.get("frames") == "complete":
            try:
                known = {f["id"] for f in evidence.read_json(source_dir / "frames/frames.json")["frames"]}
                missing = set(evidence.read_json(source_dir / "selection.json")["frame_ids"]) - known
                if missing:
                    errors.append(f"sources/{video_id}: selection references missing frames {sorted(missing)}")
            except ContractError as error:
                errors += error.problems
        if stages.get("transcript") == "complete":
            coverage = evidence.read_json(source_dir / "transcript/coverage.json")
            if coverage["gaps"]:
                warnings.append(f"sources/{video_id}: transcript gaps {coverage['gaps']} need review")
            warnings += [f"sources/{video_id}: {w}" for w in coverage["warnings"]]
        if args.require_complete:
            for stage in REQUIRED_STAGES:
                if stages.get(stage) != "complete":
                    errors.append(f"sources/{video_id}: required stage {stage} is {stages.get(stage, 'missing')}")
    if (workspace.root / "budget.json").exists():
        summary = evidence.budget_summary(workspace)
        if summary["overruns"]:
            warnings.append(f"budget overruns recorded: {summary['overruns']}")
    emit({"ok": not errors, "errors": errors, "warnings": warnings, "videos": videos})
    return 0 if not errors else 1


def cmd_budget(args: argparse.Namespace) -> int:
    workspace = Workspace(Path(args.workspace))
    workspace.assignment()
    if args.budget_command == "reserve":
        emit(evidence.reserve_budget(workspace, args.step, args.provider, args.amount, args.approval,
                                     args.video, args.note))
    elif args.budget_command == "settle":
        emit(evidence.finish_reservation(workspace, args.id, args.actual, args.basis))
    elif args.budget_command == "release":
        emit(evidence.finish_reservation(workspace, args.id, None))
    else:
        emit(evidence.budget_summary(workspace))
    return 0


# ---------------------------------------------------------------------------
# Parser and extensions


def load_extensions(subparsers: Any, extension_dir: Path) -> List[str]:
    """Import optional sibling modules and let them register subcommands.

    Contract: module defines register(subparsers) -> None, and every parser it adds calls
    set_defaults(func=handler) where handler(args) -> int exit code. Handlers may raise
    evidence.ContractError (exit 2). Absent modules are skipped; broken ones fail loudly.
    """
    loaded = []
    for name in EXTENSION_MODULES:
        path = Path(extension_dir) / f"{name}.py"
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"distilling_videos_{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        register = getattr(module, "register", None)
        if not callable(register):
            raise RuntimeError(f"extension {path} must define register(subparsers)")
        register(subparsers)
        loaded.append(name)
    return loaded


def build_parser(extension_dir: Path = SCRIPT_DIR) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="distill.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func: Any, help_text: str, video: bool = True) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--workspace", required=True)
        if video:
            command.add_argument("--video", required=True, help="assignment video id")
        command.set_defaults(func=func)
        return command

    init = add("init", cmd_init, "create or resume a workspace from assignment JSON", video=False)
    init.add_argument("--assignment", required=True)

    download = add("download", cmd_download, "download public YouTube media, probe it, extract audio")
    download.add_argument("--format", default=DEFAULT_FORMAT, help="yt-dlp format selector")
    download.add_argument("--from-file", help="register an already obtained local media file instead")
    download.add_argument("--js-runtime", choices=sorted(JS_RUNTIMES),
                          help="JavaScript runtime yt-dlp uses for YouTube challenges (default: yt-dlp's own "
                               "default, deno); recorded in the reuse config")
    download.add_argument("--js-runtime-path", help="absolute path to that runtime's executable (default: PATH)")
    download.add_argument("--timeout", type=float, default=DOWNLOAD_TIMEOUT,
                          help=f"seconds before yt-dlp or ffmpeg is stopped (default {int(DOWNLOAD_TIMEOUT)}, "
                               f"max {int(MAX_DOWNLOAD_TIMEOUT)})")

    frames = add("frames", cmd_frames, "extract bounded candidate frames and thumbnails")
    frames.add_argument("--interval", type=float, default=10.0, help="periodic spacing in seconds")
    frames.add_argument("--dense", action="append", default=[], metavar="START-END[:STEP]")
    frames.add_argument("--at", action="append", type=float, default=[], help="explicit cue timestamp")
    frames.add_argument("--scene-threshold", type=float, help="add ffmpeg scene-change cues (0-1)")
    frames.add_argument("--max-frames", type=int, default=600)

    transcript = add("import-transcript", cmd_import_transcript, "import provider-neutral transcript JSON")
    transcript.add_argument("--transcript", required=True)
    transcript.add_argument("--duration", type=float, help="media duration if source.json is absent")

    select = add("select-frames", cmd_select_frames, "record selected frames and re-render Markdown")
    select.add_argument("--frames", required=True, help="comma-separated frame ids")
    select.add_argument("--note")

    validate = add("validate", cmd_validate, "verify contracts, checksums, and stage completeness", video=False)
    validate.add_argument("--video", action="append", help="limit to video id (repeatable)")
    validate.add_argument("--require-complete", action="store_true")

    budget = sub.add_parser("budget", help="hard reservation ledger for approved externally priced steps")
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget.set_defaults(func=cmd_budget)
    reserve = budget_sub.add_parser("reserve")
    reserve.add_argument("--step", required=True)
    reserve.add_argument("--provider", required=True)
    reserve.add_argument("--amount", type=float, required=True)
    reserve.add_argument("--approval", required=True, help="reference to the user's spending approval")
    reserve.add_argument("--video", help="charge a video (omit for batch-only steps)")
    reserve.add_argument("--note")
    settle = budget_sub.add_parser("settle")
    settle.add_argument("--id", required=True)
    settle.add_argument("--actual", type=float, required=True)
    settle.add_argument("--basis", required=True, choices=["provider-invoice", "provider-usage-api", "estimate"])
    release = budget_sub.add_parser("release")
    release.add_argument("--id", required=True)
    budget_sub.add_parser("status")
    for command in (reserve, settle, release, budget_sub.choices["status"]):
        command.add_argument("--workspace", required=True)

    load_extensions(sub, extension_dir)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except evidence.BudgetRefused as error:
        print(f"error: budget refused: {error}", file=sys.stderr)
        return 4
    except ContractError as error:
        print("error: " + "\n  ".join(error.problems), file=sys.stderr)
        return 2
    except MissingTool as error:
        print(f"error: {error}", file=sys.stderr)
        return 3
    except ToolFailed as error:
        print(f"error: {error}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())

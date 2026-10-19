"""Evidence contract for distilling-videos (schema_version 1).

Standard library only. Validates assignments, workspace paths, transcripts and frame
manifests; records stage state with checksums; renders transcript Markdown; keeps a
locked budget reservation ledger. See ../reference/contracts.md for the field contract.
"""

from __future__ import annotations

import bisect
import contextlib
import datetime
import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional
from urllib.parse import parse_qs, urlsplit

SCHEMA_VERSION = 1
MAX_VIDEOS = 10
MAX_GROUP_SIZE = 5
MIN_GROUP_SIZE = 2
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
DURATION_TOLERANCE = 0.5
OVERLAP_TOLERANCE = 0.05
GAP_THRESHOLD = 2.0
INLINE_MARKER = re.compile(
    r"\[(?:inaudible|unclear|unintelligible|crosstalk|indistinct|\?|[^\]\n]{0,40}\?)\]", re.IGNORECASE)
SEGMENT_FIELDS = {"id", "start", "end", "text", "english", "english_kind", "uncertain",
                  "uncertainty", "speaker", "confidence", "words"}
TRANSCRIPT_FIELDS = {"schema_version", "video_id", "language", "provider", "translation_provider",
                     "duration", "segments", "notes"}
PROVIDER_KINDS = {"transcription", "captions", "manual", "agent"}
ENGLISH_KINDS = {"original", "clean", "translation"}


class ContractError(ValueError):
    """Input violates the evidence contract. Message lists every problem found."""

    def __init__(self, problems: Iterable[str]):
        self.problems = list(problems) if not isinstance(problems, str) else [problems]
        super().__init__("; ".join(self.problems))


# ---------------------------------------------------------------------------
# Files, hashing, paths


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest_json(data: Any) -> str:
    return sha256_bytes(canonical_json(data))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp)
        raise
    with contextlib.suppress(OSError):
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_bytes(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode())


def read_json(path: Path) -> Any:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise ContractError(f"missing file: {path}") from None
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid JSON in {path}: {error}") from None


def check_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.match(value):
        raise ContractError(
            f"{label} {value!r} is not a safe ID (1-64 ASCII letters, digits, '_' or '-', "
            "starting with a letter or digit)")
    return value


def safe_path(root: Path, relative: str) -> Path:
    """Resolve a workspace-relative path, rejecting absolute paths, '..', and symlinks."""
    if not isinstance(relative, str) or not relative or relative.startswith(("/", "\\")):
        raise ContractError(f"unsafe relative path: {relative!r}")
    parts = Path(relative).parts
    if any(part in ("..", "") or "\\" in part for part in parts) or Path(relative).is_absolute():
        raise ContractError(f"unsafe relative path: {relative!r}")
    base = Path(root).resolve()
    current = base
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ContractError(f"symlink not allowed in workspace path: {relative!r}")
    resolved = current.resolve()
    if resolved != base and base not in resolved.parents:
        raise ContractError(f"path escapes workspace: {relative!r}")
    return resolved


# ---------------------------------------------------------------------------
# Assignment


def youtube_id(url: str) -> str:
    """Return the 11-character YouTube ID of an https YouTube URL or raise ContractError."""
    if not isinstance(url, str):
        raise ContractError(f"video url must be a string: {url!r}")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise ContractError(f"video url must be https without credentials or port: {url!r}")
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise ContractError(f"video url must be a public YouTube URL: {url!r}")
    path = [p for p in parsed.path.split("/") if p]
    candidate = None
    if host == "youtu.be" and len(path) == 1:
        candidate = path[0]
    elif path == ["watch"]:
        candidate = (parse_qs(parsed.query).get("v") or [None])[0]
    elif len(path) == 2 and path[0] in ("shorts", "live", "embed"):
        candidate = path[1]
    if not candidate or not YOUTUBE_ID.match(candidate):
        raise ContractError(f"cannot find an 11-character YouTube video ID in {url!r}")
    return candidate


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_budgets(budgets: Any) -> Optional[Dict[str, Any]]:
    if budgets is None:
        return None
    problems = []
    if not isinstance(budgets, dict):
        raise ContractError("budgets must be an object")
    unknown = set(budgets) - {"currency", "batch", "per_video"}
    if unknown:
        problems.append(f"budgets has unknown fields: {sorted(unknown)}")
    currency = budgets.get("currency")
    if not isinstance(currency, str) or not re.match(r"^[A-Z]{3}$", currency):
        problems.append("budgets.currency must be a 3-letter ISO code such as USD")
    result: Dict[str, Any] = {"currency": currency}
    for key in ("batch", "per_video"):
        if key in budgets:
            value = budgets[key]
            if not _number(value) or value < 0:
                problems.append(f"budget ceiling budgets.{key} must be a non-negative number")
            else:
                result[key] = float(value)
    if "batch" in result and "per_video" in result and result["per_video"] > result["batch"]:
        problems.append("budgets.per_video cannot exceed budgets.batch")
    if problems:
        raise ContractError(problems)
    return result


def validate_assignment(data: Any) -> Dict[str, Any]:
    """Validate and normalize an assignment; returns it with derived `publications`."""
    if not isinstance(data, dict):
        raise ContractError("assignment must be a JSON object")
    problems: List[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"assignment schema_version must be {SCHEMA_VERSION}")
    unknown = set(data) - {"schema_version", "videos", "groups", "goal", "audience", "budgets",
                           "retain_media", "publications"}
    if unknown:
        problems.append(f"assignment has unknown fields: {sorted(unknown)}")
    videos = data.get("videos")
    if not isinstance(videos, list) or not videos:
        raise ContractError(problems + ["assignment.videos must be a non-empty list"])
    if len(videos) > MAX_VIDEOS:
        problems.append(f"assignment may contain at most {MAX_VIDEOS} videos (got {len(videos)})")
    normalized_videos = []
    video_ids: List[str] = []
    for index, item in enumerate(videos):
        try:
            if not isinstance(item, dict) or set(item) - {"id", "url", "title", "youtube_id"}:
                raise ContractError(f"videos[{index}] must be an object with id, url and optional title")
            video_id = check_id(item.get("id"), f"videos[{index}].id")
            if video_id in video_ids:
                raise ContractError(f"duplicate video id {video_id!r}")
            entry = {"id": video_id, "url": item.get("url"), "youtube_id": youtube_id(item.get("url"))}
            if "youtube_id" in item and item["youtube_id"] != entry["youtube_id"]:
                raise ContractError(f"videos[{index}].youtube_id does not match its url")
            if "title" in item:
                entry["title"] = str(item["title"])
            video_ids.append(video_id)
            normalized_videos.append(entry)
        except ContractError as error:
            problems.extend(error.problems)
    groups = data.get("groups", [])
    if not isinstance(groups, list):
        problems.append("assignment.groups must be a list")
        groups = []
    group_ids: List[str] = []
    membership: Dict[str, str] = {}
    normalized_groups = []
    for index, group in enumerate(groups):
        try:
            if not isinstance(group, dict) or set(group) - {"id", "video_ids", "title"}:
                raise ContractError(f"groups[{index}] must be an object with id and video_ids")
            group_id = check_id(group.get("id"), f"groups[{index}].id")
            if group_id in group_ids:
                raise ContractError(f"duplicate group id {group_id!r}")
            if group_id in video_ids:
                raise ContractError(f"group id {group_id!r} collides with a video id")
            members = group.get("video_ids")
            if not isinstance(members, list):
                raise ContractError(f"groups[{index}].video_ids must be a list")
            if len(members) > MAX_GROUP_SIZE:
                raise ContractError(f"group {group_id!r} may contain at most {MAX_GROUP_SIZE} videos")
            if len(members) < MIN_GROUP_SIZE:
                raise ContractError(f"group {group_id!r} needs at least {MIN_GROUP_SIZE} videos; "
                                    "leave single videos ungrouped")
            if len(set(members)) != len(members):
                raise ContractError(f"group {group_id!r} lists a duplicate video")
            for member in members:
                if member not in video_ids:
                    raise ContractError(f"group {group_id!r} references unknown video {member!r}")
                if member in membership:
                    raise ContractError(f"video {member!r} appears in more than one group "
                                        f"({membership[member]!r}, {group_id!r})")
                membership[member] = group_id
            group_ids.append(group_id)
            normalized_groups.append({"id": group_id, "video_ids": list(members),
                                      **({"title": str(group["title"])} if "title" in group else {})})
        except ContractError as error:
            problems.extend(error.problems)
    for key in ("goal", "audience"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            problems.append(f"assignment.{key} must be a string")
    if "retain_media" in data and not isinstance(data["retain_media"], bool):
        problems.append("assignment.retain_media must be a boolean")
    budgets = None
    try:
        budgets = validate_budgets(data.get("budgets"))
    except ContractError as error:
        problems.extend(error.problems)
    if problems:
        raise ContractError(problems)
    publications = [{"id": g["id"], "kind": "group", "video_ids": g["video_ids"]} for g in normalized_groups]
    publications += [{"id": v, "kind": "single", "video_ids": [v]} for v in video_ids if v not in membership]
    if "publications" in data and data["publications"] != publications:
        raise ContractError("assignment.publications is derived from videos and groups and must not be edited")
    result: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "videos": normalized_videos,
                              "groups": normalized_groups, "publications": publications,
                              "goal": data.get("goal"), "audience": data.get("audience"),
                              "retain_media": bool(data.get("retain_media", False))}
    if budgets:
        result["budgets"] = budgets
    return result


# ---------------------------------------------------------------------------
# Workspace and stage state


class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    @property
    def assignment_path(self) -> Path:
        return self.root / "assignment.json"

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    def path(self, relative: str) -> Path:
        return safe_path(self.root, relative)

    def assignment(self) -> Dict[str, Any]:
        return validate_assignment(read_json(self.assignment_path))

    def video(self, video_id: str) -> Dict[str, Any]:
        check_id(video_id, "video")
        for entry in self.assignment()["videos"]:
            if entry["id"] == video_id:
                return entry
        raise ContractError(f"video {video_id!r} is not in the assignment")

    def source_dir(self, video_id: str) -> Path:
        return self.path(f"sources/{check_id(video_id, 'video')}")

    @contextlib.contextmanager
    def lock(self, name: str = "state") -> Iterator[None]:
        lock_path = self.root / f".{name}.lock"
        with open(lock_path, "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def state(self) -> Dict[str, Any]:
        state = read_json(self.state_path)
        if state.get("schema_version") != SCHEMA_VERSION:
            raise ContractError(f"state.json schema_version must be {SCHEMA_VERSION}")
        return state

    def update_state(self, change: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        with self.lock():
            state = self.state()
            change(state)
            state["updated_at"] = now()
            atomic_write_json(self.state_path, state)
            return state


def init_workspace(root: Path, assignment_data: Any) -> str:
    """Create or resume a workspace. Returns 'created' or 'resumed'."""
    assignment = validate_assignment(assignment_data)
    digest = digest_json(assignment)
    workspace = Workspace(root)
    if workspace.assignment_path.exists():
        existing = workspace.assignment()
        if digest_json(existing) != digest:
            raise ContractError(
                "incompatible resume: workspace was initialized with a different assignment; "
                "use a new workspace directory")
        return "resumed"
    if workspace.root.exists() and any(workspace.root.iterdir()):
        raise ContractError(f"refusing to initialize non-empty directory without assignment.json: {root}")
    workspace.root.mkdir(parents=True, exist_ok=True)
    for entry in assignment["videos"]:
        (workspace.root / "sources" / entry["id"]).mkdir(parents=True, exist_ok=True)
    for publication in assignment["publications"]:
        plan = {"schema_version": SCHEMA_VERSION, **publication, "goal": assignment["goal"],
                "audience": assignment["audience"]}
        atomic_write_json(workspace.root / "publications" / publication["id"] / "plan.json", plan)
    atomic_write_json(workspace.state_path, {
        "schema_version": SCHEMA_VERSION, "assignment_sha256": digest, "created_at": now(),
        "updated_at": now(), "stages": {}, "temporary_media": []})
    atomic_write_json(workspace.assignment_path, assignment)
    return "created"


def stage_key(video_id: str, stage: str) -> str:
    return f"sources/{check_id(video_id, 'video')}/{stage}"


def file_digests(base: Path, relatives: Iterable[str]) -> Dict[str, str]:
    return {rel: sha256_file(safe_path(base, rel)) for rel in sorted(relatives)}


def stage_problems(workspace: Workspace, key: str, record: Dict[str, Any]) -> List[str]:
    """Checksum problems for a recorded stage (inputs and outputs are relative to its base)."""
    problems = []
    base = workspace.path(record.get("base", key.rsplit("/", 1)[0]))
    for kind in ("inputs", "outputs"):
        for rel, expected in record.get(kind, {}).items():
            try:
                path = safe_path(base, rel)
                actual = sha256_file(path) if path.is_file() else None
            except ContractError as error:
                problems.append(f"{key}: {error}")
                continue
            if actual is None:
                problems.append(f"{key}: missing {kind[:-1]} {rel}")
            elif actual != expected:
                problems.append(f"{key}: checksum mismatch for {kind[:-1]} {rel}")
    return problems


def reusable(workspace: Workspace, key: str, inputs: Dict[str, str], config: Any) -> bool:
    """True only if a complete record has identical input/config digests and intact outputs."""
    record = workspace.state()["stages"].get(key)
    return bool(record and record.get("status") == "complete"
                and record.get("inputs") == inputs
                and record.get("config_sha256") == digest_json(config)
                and record.get("outputs")
                and not stage_problems(workspace, key, record))


def mark_running(workspace: Workspace, key: str, config: Any) -> None:
    def change(state: Dict[str, Any]) -> None:
        state["stages"][key] = {"status": "running", "config_sha256": digest_json(config),
                                "config": config, "started_at": now()}
    workspace.update_state(change)


def mark_failed(workspace: Workspace, key: str, error: str) -> None:
    def change(state: Dict[str, Any]) -> None:
        record = state["stages"].setdefault(key, {})
        record.update(status="failed", error=redact(error)[-2000:], finished_at=now())
        record.pop("outputs", None)
    workspace.update_state(change)


def mark_complete(workspace: Workspace, key: str, config: Any, inputs: Dict[str, str],
                  outputs: Dict[str, str], extra: Optional[Dict[str, Any]] = None,
                  temporary_media: Iterable[str] = ()) -> None:
    def change(state: Dict[str, Any]) -> None:
        record = {"status": "complete", "base": key.rsplit("/", 1)[0], "config": config,
                  "config_sha256": digest_json(config), "inputs": inputs, "outputs": outputs,
                  "finished_at": now()}
        record.update(extra or {})
        state["stages"][key] = record
        media = set(state.setdefault("temporary_media", []))
        media.update(temporary_media)
        state["temporary_media"] = sorted(media)
    workspace.update_state(change)


def redact(text: str) -> str:
    text = re.sub(r"([?&](?:sig|se|sp|sv|sr|st|spr|skoid|sktid|skt|ske|sks|skv)=)[^&\s\"']+",
                  r"\1REDACTED", text)
    return re.sub(r"(?i)(authorization:\s*)\S+", r"\1REDACTED", text)


# ---------------------------------------------------------------------------
# Transcripts


def _language_is_english(language: str) -> bool:
    return language.lower() == "en" or language.lower().startswith("en-")


def validate_transcript(data: Any, video_id: str, duration: Optional[float]) -> Dict[str, Any]:
    """Validate provider-neutral transcript input; returns normalized segments, content untouched."""
    if not isinstance(data, dict):
        raise ContractError("transcript must be a JSON object")
    problems: List[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"transcript schema_version must be {SCHEMA_VERSION}")
    unknown = set(data) - TRANSCRIPT_FIELDS
    if unknown:
        problems.append(f"transcript has unknown field(s): {sorted(unknown)}")
    if data.get("video_id") != video_id:
        problems.append(f"transcript video_id must be {video_id!r}")
    language = data.get("language")
    if not isinstance(language, str) or not re.match(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$", language):
        problems.append("transcript language must be a BCP 47 tag such as en or ja")
        language = "und"
    provider = data.get("provider")
    if not isinstance(provider, dict) or not isinstance(provider.get("name"), str) or not provider["name"]:
        problems.append("transcript provider.name is required")
    elif provider.get("kind") not in PROVIDER_KINDS:
        problems.append(f"transcript provider.kind must be one of {sorted(PROVIDER_KINDS)}")
    if duration is None and _number(data.get("duration")) and data["duration"] > 0:
        duration = float(data["duration"])
    english_source = _language_is_english(language)
    default_kind = "clean" if english_source else "translation"
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ContractError(problems + ["transcript segments must be a non-empty list"])
    normalized = []
    seen = set()
    previous_start, previous_end = -1.0, 0.0
    for index, segment in enumerate(segments):
        label = f"segment[{index}]"
        if not isinstance(segment, dict):
            problems.append(f"{label} must be an object")
            continue
        extra = set(segment) - SEGMENT_FIELDS
        if extra:
            problems.append(f"{label} has unknown field(s) {sorted(extra)}; content must not be summarized "
                            "or carried in unrecognized fields")
        try:
            segment_id = check_id(segment.get("id"), f"{label} id")
            if segment_id in seen:
                problems.append(f"duplicate segment id {segment_id!r}")
            seen.add(segment_id)
            label = f"segment {segment_id}"
        except ContractError as error:
            problems.extend(error.problems)
        start, end = segment.get("start"), segment.get("end")
        if not _number(start) or not _number(end):
            problems.append(f"{label} start and end must be numbers of seconds")
            continue
        if start < 0:
            problems.append(f"{label} has a negative start")
        if end <= start:
            problems.append(f"{label} end must exceed start")
        if duration is not None and end > duration + DURATION_TOLERANCE:
            problems.append(f"{label} ends beyond duration ({end} > {duration})")
        if start < previous_start:
            problems.append(f"{label} is out of order")
        elif start < previous_end - OVERLAP_TOLERANCE:
            problems.append(f"{label} has an overlap with the previous segment")
        previous_start, previous_end = max(previous_start, start), max(previous_end, end)
        for field in ("text", "english"):
            value = segment.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{label} needs non-empty {field}")
        kind = segment.get("english_kind", default_kind)
        if kind not in ENGLISH_KINDS:
            problems.append(f"{label} english_kind must be one of {sorted(ENGLISH_KINDS)}")
        elif not english_source and kind != "translation":
            problems.append(f"{label} english must be labeled english_kind=translation for {language} source")
        elif english_source and kind == "translation":
            problems.append(f"{label} english_kind=translation is invalid for an English source")
        if "uncertain" in segment and not isinstance(segment["uncertain"], bool):
            problems.append(f"{label} uncertain must be a boolean")
        if "uncertainty" in segment and not isinstance(segment["uncertainty"], str):
            problems.append(f"{label} uncertainty must be a string")
        if "confidence" in segment and (not _number(segment["confidence"]) or not 0 <= segment["confidence"] <= 1):
            problems.append(f"{label} confidence must be between 0 and 1")
        entry = dict(segment)
        entry["start"], entry["end"] = float(start), float(end)
        entry["english_kind"] = kind
        entry["uncertain"] = bool(segment.get("uncertain", False))
        markers = []
        for field in ("text", "english"):
            if isinstance(segment.get(field), str):
                markers += [m for m in INLINE_MARKER.findall(segment[field]) if m not in markers]
        entry["inline_markers"] = markers
        normalized.append(entry)
    if problems:
        raise ContractError(problems)
    return {"schema_version": SCHEMA_VERSION, "video_id": video_id, "language": language,
            "provider": provider, "translation_provider": data.get("translation_provider"),
            "english_label": "translation" if not english_source else "clean English",
            "duration": duration, "notes": data.get("notes"), "segments": normalized}


def transcript_coverage(transcript: Dict[str, Any], gap_threshold: float = GAP_THRESHOLD) -> Dict[str, Any]:
    segments = transcript["segments"]
    duration = transcript.get("duration")
    gaps = []
    cursor = 0.0
    for segment in segments:
        if segment["start"] - cursor > gap_threshold:
            gaps.append({"start": round(cursor, 3), "end": round(segment["start"], 3)})
        cursor = max(cursor, segment["end"])
    if duration is not None and duration - cursor > gap_threshold:
        gaps.append({"start": round(cursor, 3), "end": round(duration, 3)})
    covered = 0.0
    cursor = 0.0
    for segment in segments:
        start = max(segment["start"], cursor)
        if segment["end"] > start:
            covered += segment["end"] - start
        cursor = max(cursor, segment["end"])
    provider_kind = (transcript.get("provider") or {}).get("kind")
    warnings = []
    if duration is None:
        warnings.append("duration unknown: trailing coverage cannot be verified")
    if provider_kind == "captions":
        warnings.append("captions-based transcript: accuracy and completeness are not verified")
    return {"schema_version": SCHEMA_VERSION, "video_id": transcript["video_id"],
            "segment_count": len(segments), "duration": duration, "covered_seconds": round(covered, 3),
            "gap_threshold": gap_threshold, "gaps": gaps,
            "uncertain_segment_ids": [s["id"] for s in segments if s["uncertain"] or s["inline_markers"]],
            "warnings": warnings}


def timestamp(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"


def timestamp_url(youtube: str, seconds: float) -> str:
    return f"https://www.youtube.com/watch?v={youtube}&t={int(seconds)}s"


_MD_ESCAPE = re.compile(r"([\\`*_\[\]{}<>()#|!~&])")


def escape_markdown(text: str) -> str:
    """Render untrusted source text as literal Markdown text (no HTML, links, or headings)."""
    lines = []
    for line in text.split("\n"):
        line = _MD_ESCAPE.sub(r"\\\1", line)
        line = re.sub(r"^(\s*)([-+=]|\d+[.)])", lambda m: m.group(1) + m.group(2)[:-1] + "\\" + m.group(2)[-1],
                      line)
        lines.append(line)
    return "\n".join(lines)


def _quote(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in escape_markdown(text).split("\n"))


def render_transcripts(source: Dict[str, Any], video: Dict[str, Any], transcript: Dict[str, Any],
                       frames: Optional[Dict[str, Any]], selection: Optional[List[str]]) -> Dict[str, str]:
    """Return {'original.md': ..., 'english.md': ...}; frame paths relative to transcript/."""
    youtube = video["youtube_id"]
    title = escape_markdown(str(source.get("title") or video.get("title") or video["id"]))
    creator = escape_markdown(str(source.get("creator") or "unknown creator"))
    provider = transcript["provider"]
    provider_text = escape_markdown(f"{provider['name']} ({provider['kind']})")
    selected = []
    if frames and selection:
        by_id = {f["id"]: f for f in frames["frames"]}
        selected = [by_id[i] for i in selection if i in by_id]
    header = [f"Source: <{timestamp_url(youtube, 0)}> — {creator}", f"Transcript provider: {provider_text}"]
    original = [f"# Original transcript ({escape_markdown(transcript['language'])}): {title}", "", *header, ""]
    label = ("English translation of the original-language transcript"
             if transcript["english_label"] == "translation" else "Clean English transcript")
    english = [f"# {label}: {title}", "", *header,
               "This file is a " + ("translation; consult original.md for source wording."
                                    if transcript["english_label"] == "translation"
                                    else "cleaned transcript; consult original.md for verbatim wording."),
               "Frames are sampled selections, not exhaustive frame-by-frame analysis.", ""]
    if not selected:
        english.append("No screenshots selected yet.\n")
    starts = [s["start"] for s in transcript["segments"]]
    attached: Dict[int, List[Dict[str, Any]]] = {}
    for frame in sorted(selected, key=lambda f: f["t"]):
        # Attach to the last segment starting at or before the frame (first segment if earlier).
        attached.setdefault(max(bisect.bisect_right(starts, frame["t"]) - 1, 0), []).append(frame)
    for index, segment in enumerate(transcript["segments"]):
        link = timestamp_url(youtube, segment["start"])
        heading = f"## [{timestamp(segment['start'])}]({link}) · {segment['id']}"
        flags = []
        if segment["uncertain"] or segment["inline_markers"]:
            note = segment.get("uncertainty") or "contains inline uncertainty markers"
            flags = ["", f"**Uncertain:** {escape_markdown(note)}"]
        original += [heading, "", _quote(segment["text"]), *flags, ""]
        english += [heading, "", _quote(segment["english"]), *flags, ""]
        for frame in attached.get(index, []):
            alt = f"Frame at {timestamp(frame['t'])}"
            english += [f"[![{alt}](../{frame['thumbnail']})]({timestamp_url(youtube, frame['t'])}) "
                        f"([full size](../{frame['path']}))", ""]
    return {"original.md": "\n".join(original), "english.md": "\n".join(english)}


# ---------------------------------------------------------------------------
# Frames


def parse_dense(spec: str) -> Dict[str, float]:
    match = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(?::(\d+(?:\.\d+)?))?$", spec)
    if not match:
        raise ContractError(f"dense interval must look like START-END[:STEP] in seconds: {spec!r}")
    start, end, step = float(match.group(1)), float(match.group(2)), float(match.group(3) or 1)
    if end <= start or step <= 0:
        raise ContractError(f"dense interval needs END > START and STEP > 0: {spec!r}")
    return {"start": start, "end": end, "step": step}


def frame_plan(duration: float, interval: float, dense: List[Dict[str, float]], cues: List[float],
               scene: List[float], max_frames: int) -> List[Dict[str, Any]]:
    """Deterministic candidate timestamps; raises instead of silently truncating coverage."""
    if interval <= 0:
        raise ContractError("interval must be positive")
    times: Dict[int, List[str]] = {}

    def add(t: float, reason: str) -> None:
        if 0 <= t < duration or (reason == "cue" and 0 <= t <= duration):
            times.setdefault(int(round(t * 1000)), [])
            if reason not in times[int(round(t * 1000))]:
                times[int(round(t * 1000))].append(reason)

    count = int(math.ceil(duration / interval)) if duration > 0 else 1
    for i in range(count):
        add(i * interval, "periodic")
    for spec in dense:
        steps = int(math.floor((spec["end"] - spec["start"]) / spec["step"] + 1e-9))
        for i in range(steps + 1):
            add(spec["start"] + i * spec["step"], "dense")
    for t in cues:
        add(t, "cue")
    for t in scene:
        add(t, "scene")
    if len(times) > max_frames:
        raise ContractError(f"plan needs {len(times)} frames but --max-frames is {max_frames}; "
                            "raise --max-frames or widen --interval (coverage is never silently truncated)")
    return [{"id": f"f{ms:09d}", "t": ms / 1000, "reasons": reasons} for ms, reasons in sorted(times.items())]


def frame_gaps(plan: List[Dict[str, Any]], duration: float) -> float:
    points = [f["t"] for f in plan] + [duration]
    return round(max((b - a for a, b in zip([0.0] + points[:-1], points)), default=duration), 3)


# ---------------------------------------------------------------------------
# Budget reservation ledger


def _ledger_path(workspace: Workspace) -> Path:
    return workspace.root / "budget.json"


def _ledger(workspace: Workspace) -> Dict[str, Any]:
    path = _ledger_path(workspace)
    if path.exists():
        return read_json(path)
    budgets = workspace.assignment().get("budgets") or {}
    return {"schema_version": SCHEMA_VERSION, "currency": budgets.get("currency"),
            "ceilings": {k: budgets[k] for k in ("batch", "per_video") if k in budgets}, "entries": []}


def _committed(entry: Dict[str, Any]) -> float:
    if entry["status"] == "reserved":
        return entry["amount"]
    if entry["status"] == "settled":
        return entry["actual"]
    return 0.0


def budget_summary(workspace: Workspace) -> Dict[str, Any]:
    ledger = _ledger(workspace)
    per_video: Dict[str, float] = {}
    for entry in ledger["entries"]:
        if entry.get("video_id"):
            per_video[entry["video_id"]] = round(per_video.get(entry["video_id"], 0.0) + _committed(entry), 6)
    return {"schema_version": SCHEMA_VERSION, "currency": ledger["currency"], "ceilings": ledger["ceilings"],
            "committed": {"batch": round(sum(_committed(e) for e in ledger["entries"]), 6),
                          "per_video": per_video},
            "overruns": [e["id"] for e in ledger["entries"] if e.get("overrun")],
            "entries": ledger["entries"],
            "guarantees_all_in_spend": False,
            "note": "Gate for approved externally priced steps that reserve before spending; it cannot "
                    "stop a provider from billing beyond a reservation, and Amp model usage is not tracked."}


class BudgetRefused(ContractError):
    pass


def reserve_budget(workspace: Workspace, step: str, provider: str, amount: float, approval: str,
                   video_id: Optional[str] = None, note: Optional[str] = None) -> Dict[str, Any]:
    if not _number(amount) or amount <= 0:
        raise ContractError("reservation amount must be a positive number")
    if not approval.strip():
        raise ContractError("reservation requires an approval reference")
    check_id(step, "step")
    check_id(provider, "provider")
    if video_id is not None:
        workspace.video(video_id)
    with workspace.lock("budget"):
        ledger = _ledger(workspace)
        ceilings = ledger["ceilings"]
        if "batch" not in ceilings and not (video_id and "per_video" in ceilings):
            raise BudgetRefused("no applicable budget ceiling in assignment.budgets; paid steps are refused")
        if video_id is None and "batch" not in ceilings:
            raise BudgetRefused("batch-scoped reservation requires budgets.batch ceiling")
        batch = sum(_committed(e) for e in ledger["entries"])
        if "batch" in ceilings and batch + amount > ceilings["batch"] + 1e-9:
            raise BudgetRefused(f"batch ceiling exceeded: committed {batch:.4f} + {amount:.4f} > "
                                f"{ceilings['batch']:.4f} {ledger['currency']}")
        if video_id and "per_video" in ceilings:
            spent = sum(_committed(e) for e in ledger["entries"] if e.get("video_id") == video_id)
            if spent + amount > ceilings["per_video"] + 1e-9:
                raise BudgetRefused(f"per_video ceiling exceeded for {video_id}: committed {spent:.4f} + "
                                    f"{amount:.4f} > {ceilings['per_video']:.4f} {ledger['currency']}")
        entry = {"id": f"r{len(ledger['entries']) + 1:04d}", "video_id": video_id, "step": step,
                 "provider": provider, "amount": float(amount), "approval": approval, "note": note,
                 "status": "reserved", "created_at": now()}
        ledger["entries"].append(entry)
        atomic_write_json(_ledger_path(workspace), ledger)
        return entry


def finish_reservation(workspace: Workspace, reservation_id: str, actual: Optional[float],
                       basis: Optional[str] = None) -> Dict[str, Any]:
    with workspace.lock("budget"):
        ledger = _ledger(workspace)
        for entry in ledger["entries"]:
            if entry["id"] == reservation_id:
                break
        else:
            raise ContractError(f"unknown reservation {reservation_id!r}")
        if entry["status"] != "reserved":
            raise ContractError(f"reservation {reservation_id} is already {entry['status']}")
        if actual is None:
            entry.update(status="released", finished_at=now())
        else:
            if not _number(actual) or actual < 0:
                raise ContractError("actual cost must be a non-negative number")
            if basis not in ("provider-invoice", "provider-usage-api", "estimate"):
                raise ContractError("basis must be provider-invoice, provider-usage-api, or estimate")
            entry.update(status="settled", actual=float(actual), basis=basis,
                         overrun=actual > entry["amount"] + 1e-9, finished_at=now())
        atomic_write_json(_ledger_path(workspace), ledger)
        return entry

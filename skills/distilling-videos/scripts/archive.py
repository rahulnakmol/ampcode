"""Quality sign-off, durable archival, verification, and media cleanup for distilling-videos.

Registers `signoff`, `archive`, `verify-archive`, `cleanup`, `unpack-artifact`, and
`actions-provenance` into distill.py. Storage is one private Azure Blob container reached
through the Blob REST API over HTTPS with a SAS taken only from DISTILL_ARCHIVE_SAS.
See ../reference/archival.md. Standard library only.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import secrets
import shutil
import ssl
import stat
import sys
import zipfile
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, quote, unquote, urlsplit

import evidence
import publication
from evidence import ContractError, Workspace, check_id, safe_path

SAS_ENV = "DISTILL_ARCHIVE_SAS"
API_VERSION = "2021-12-02"
ACCOUNT_HOST = re.compile(r"^[a-z0-9]{3,24}\.blob\.core\.(?:windows\.net|usgovcloudapi\.net|chinacloudapi\.cn)$")
CONTAINER_PATH = re.compile(r"^/([a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){2,62})/?$")
SEGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,254}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_OBJECT_BYTES = 512 * 1024 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024 * 1024
MAX_FILES = 5000
MARKER = "_COMPLETE.json"
SIGNOFF = "signoff.json"
RECEIPT = "archive-receipt.json"
REQUIRED_STAGES = ("download", "frames", "transcript", "transcript-markdown")
SNAPSHOT_STAGES = REQUIRED_STAGES + ("frame-selection",)
CORE_EVIDENCE = ("source.json", "selection.json", "frames/frames.json", "transcript/input.json",
                 "transcript/segments.json", "transcript/coverage.json", "transcript/original.md",
                 "transcript/english.md")
GAP_RESOLUTIONS = {"no-speech", "not-relevant", "unresolved"}
UNCERTAIN_RESOLUTIONS = {"labeled", "unresolved"}
# Transcripts not produced by a dedicated transcription provider or a human transcriber need audio spot checks.
AUDIO_CHECK_KINDS = {"captions", "agent"}
AUDIO_METHODS = {"listened-to-source-audio", "compared-with-independent-transcription"}
AUDIO_RESULTS = {"matches", "differs"}
TRUSTED_EVENTS = {"workflow_dispatch", "push", "schedule"}
THIS_WORKFLOW = ".github/workflows/archive-distilled-videos.yml"
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
                 ".json": "application/json", ".css": "text/css", ".js": "text/javascript", ".pdf": "application/pdf",
                 ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".svg": "image/svg+xml", ".zip": "application/zip"}


class ArchiveError(Exception):
    """Remote storage or transport failure (exit 5). Messages never contain the SAS."""


# ---------------------------------------------------------------------------
# Destination and credential validation


def parse_container(url: Any) -> Tuple[str, str, str]:
    """Return (host, container, normalized URL) for an Azure Blob container URL without credentials."""
    problem = ("container URL must be https://<account>.blob.core.windows.net/<container> (or the US Gov / "
               "China Blob endpoint) with no credentials, port, query, fragment, or sub-path")
    if not isinstance(url, str) or any(c.isspace() for c in url):
        raise ContractError(problem)
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise ContractError(problem) from None
    host = (parts.hostname or "")
    if (parts.scheme != "https" or parts.username or parts.password or port is not None or parts.query
            or parts.fragment or "?" in url or "#" in url or parts.netloc != host or not ACCOUNT_HOST.match(host)):
        raise ContractError(problem)
    match = CONTAINER_PATH.match(parts.path)
    if not match:
        raise ContractError(problem)
    return host, match.group(1), f"https://{host}/{match.group(1)}"


def parse_sas(value: Optional[str], write: bool) -> str:
    """Validate a SAS query token without ever echoing it. Returns it without a leading '?'."""
    if not value:
        raise ContractError(f"set the SAS token in the {SAS_ENV} environment variable (never on the command line)")
    token = value.strip()
    token = token[1:] if token.startswith("?") else token
    if not token or re.search(r"[\s#]", token) or token.lower().startswith("http") or "://" in token:
        raise ContractError(f"{SAS_ENV} must contain only the SAS query string, not a URL")
    try:
        pairs = parse_qsl(token, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise ContractError(f"{SAS_ENV} is not a valid SAS query string") from None
    fields: Dict[str, str] = {}
    for key, item in pairs:
        if key in fields:
            raise ContractError(f"{SAS_ENV} repeats SAS parameter {key!r}")
        fields[key] = item
    problems = []
    if not fields.get("sig"):
        problems.append("SAS has no signature (sig)")
    if not fields.get("se"):
        problems.append("SAS must expire (se)")
    if fields.get("spr") != "https":
        problems.append("SAS must be HTTPS-only (spr=https)")
    permissions = set(fields.get("sp", ""))
    if permissions & set("dxy"):
        problems.append("SAS must not grant delete permissions (d, x, y); archival never deletes remote objects")
    if "r" not in permissions:
        problems.append("SAS needs read (r) permission for read-back verification")
    if write and not permissions & set("cw"):
        problems.append("SAS needs create (c) permission to upload")
    if problems:
        raise ContractError(problems)
    return token


def scrub(text: str, sas: str) -> str:
    """Remove a SAS and any query string from diagnostic text."""
    for secret in [sas, unquote(sas)] + [v for _, v in parse_qsl(sas, keep_blank_values=True)]:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "REDACTED")
            text = text.replace(quote(secret, safe=""), "REDACTED")
    text = re.sub(r"\?\S*", "?REDACTED", text)
    return evidence.redact(text)


def check_blob_name(name: str) -> str:
    if not isinstance(name, str) or len(name) > 1024 or not all(SEGMENT.match(p) for p in name.split("/")):
        raise ContractError(f"unsafe blob name: {name!r}")
    return name


def check_rel(rel: Any, label: str = "path") -> str:
    if not isinstance(rel, str) or len(rel) > 1024 or not rel or not all(SEGMENT.match(p) for p in rel.split("/")):
        raise ContractError(f"unsafe {label}: {rel!r}")
    return rel


# ---------------------------------------------------------------------------
# Transport (dependency-injected; production is HTTPS only, no redirects, no proxies)


class HttpsTransport:
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
        self.context = ssl.create_default_context()

    def request(self, method: str, host: str, target: str, headers: Dict[str, str],
                body: bytes) -> Tuple[int, Dict[str, str], bytes]:
        connection = http.client.HTTPSConnection(host, 443, timeout=self.timeout, context=self.context)
        try:
            connection.request(method, target, body=body if method == "PUT" else None, headers=headers)
            response = connection.getresponse()
            data = response.read(MAX_OBJECT_BYTES + 1)
            return response.status, {k.lower(): v for k, v in response.getheaders()}, data
        finally:
            connection.close()


class BlobClient:
    def __init__(self, container_url: str, sas: Optional[str], transport: Any, write: bool):
        self.host, self.container, self.url = parse_container(container_url)
        self.sas = parse_sas(sas, write)
        self.transport = transport or HttpsTransport()

    def _call(self, method: str, name: str, headers: Dict[str, str], body: bytes = b"") -> Tuple[Dict[str, str], bytes]:
        check_blob_name(name)
        target = f"/{self.container}/{quote(name, safe='/._-')}?{self.sas}"
        headers = {"x-ms-version": API_VERSION, "x-ms-date": formatdate(usegmt=True), **headers}
        try:
            status, response_headers, data = self.transport.request(method, self.host, target, headers, body)
        except Exception as error:  # noqa: BLE001 - transport errors are reported without secrets
            raise ArchiveError(f"{method} {name} failed: {type(error).__name__}: {scrub(str(error), self.sas)}") \
                from None
        response_headers = {str(k).lower(): str(v) for k, v in (response_headers or {}).items()}
        expected = 201 if method == "PUT" else 200
        if 300 <= status < 400:
            raise ArchiveError(f"{method} {name}: refused HTTP {status} redirect; requests are never re-sent "
                               "to another location")
        if status != expected:
            code = response_headers.get("x-ms-error-code", "")
            code = code if re.match(r"^[A-Za-z0-9]{1,64}$", code) else "unknown"
            raise ArchiveError(f"{method} {name}: HTTP {status} {code}")
        return response_headers, data

    def put(self, name: str, data: bytes, content_type: str) -> None:
        self._call("PUT", name, {
            "x-ms-blob-type": "BlockBlob", "Content-Type": content_type, "Content-Length": str(len(data)),
            "Content-MD5": base64.b64encode(hashlib.md5(data).digest()).decode(),  # noqa: S324 - transport check
            "If-None-Match": "*", "x-ms-meta-sha256": evidence.sha256_bytes(data)}, data)

    def get(self, name: str) -> bytes:
        _, data = self._call("GET", name, {})
        if len(data) > MAX_OBJECT_BYTES:
            raise ArchiveError(f"GET {name}: object exceeds {MAX_OBJECT_BYTES} bytes")
        return data


# ---------------------------------------------------------------------------
# Package loading and validation (also used for untrusted Actions artifacts)


def _read_regular(path: Path, limit: int = MAX_OBJECT_BYTES) -> bytes:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        raise ContractError(f"missing file: {path.name}") from None
    if stat.S_ISLNK(info.st_mode):
        raise ContractError(f"symlink not allowed in package: {path.name}")
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(f"not a regular file: {path.name}")
    if info.st_size > limit:
        raise ContractError(f"{path.name} exceeds the {limit}-byte limit")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as handle:
        return handle.read(limit + 1)


def _secret_check(rel: str, data: bytes) -> None:
    if Path(rel).suffix.lower() in publication.TEXT_EXTENSIONS | {".json"} and \
            publication.SECRET.search(data.decode("utf-8", errors="replace")):
        raise ContractError(f"refusing {rel}: it contains secret-like content (SAS, key, or token)")


def validate_manifest(manifest: Any) -> List[str]:
    problems = []
    required = {"schema_version", "publication_id", "kind", "video_ids", "revision", "status", "complete",
                "incomplete_reasons", "pdf", "excluded", "files"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        return [f"manifest.json must contain exactly {sorted(required)}"]
    if manifest["schema_version"] != 1:
        problems.append("manifest schema_version must be 1")
    try:
        check_id(manifest["publication_id"], "publication")
        for video_id in manifest["video_ids"]:
            check_id(video_id, "video")
    except (ContractError, TypeError) as error:
        problems.append(str(error))
    if manifest["kind"] not in ("single", "group") or not isinstance(manifest["video_ids"], list) \
            or not manifest["video_ids"]:
        problems.append("manifest kind/video_ids are invalid")
    if not isinstance(manifest["revision"], str) or not re.match(r"^[0-9a-f]{16}$", manifest["revision"]):
        problems.append("manifest revision must be 16 hex characters")
    if not isinstance(manifest["complete"], bool) or not isinstance(manifest["incomplete_reasons"], list):
        problems.append("manifest complete/incomplete_reasons are invalid")
    elif manifest["complete"] == bool(manifest["incomplete_reasons"]) or \
            (manifest["complete"] and manifest["status"] != "complete"):
        problems.append("manifest complete flag contradicts its status or incomplete_reasons")
    if not isinstance(manifest["files"], list) or len(manifest["files"]) > MAX_FILES:
        problems.append(f"manifest files must be a list of at most {MAX_FILES} entries")
        return problems
    seen: Set[str] = set()
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            problems.append(f"manifest file entry must be {{path, sha256, bytes}}: {entry!r}"[:200])
            continue
        try:
            rel = check_rel(entry["path"], "manifest path")
        except ContractError as error:
            problems += error.problems
            continue
        if rel in seen or rel.lower() in {s.lower() for s in seen} or rel in ("manifest.json", SIGNOFF, MARKER):
            problems.append(f"duplicate or reserved manifest path {rel}")
        seen.add(rel)
        if Path(rel).suffix.lower() not in publication.PACKAGE_EXTENSIONS:
            problems.append(f"unexpected file type in manifest: {rel}")
        if not isinstance(entry["sha256"], str) or not HEX64.match(entry["sha256"]) or \
                not isinstance(entry["bytes"], int) or not 0 <= entry["bytes"] <= MAX_OBJECT_BYTES:
            problems.append(f"invalid checksum or size for {rel}")
        parts = rel.split("/")
        if parts[0] == "sources" and (len(parts) < 3 or parts[1] not in manifest["video_ids"]):
            problems.append(f"{rel} is not evidence for a publication video")
    if not problems:
        if sum(e["bytes"] for e in manifest["files"]) > MAX_PACKAGE_BYTES:
            problems.append(f"package exceeds {MAX_PACKAGE_BYTES} bytes")
        if evidence.digest_json(manifest["files"])[:16] != manifest["revision"]:
            problems.append("manifest revision does not match its files list (tampered or unlisted change)")
    return problems


def load_package(directory: Path, zip_path: Optional[Path] = None, signoff_path: Optional[Path] = None,
                 standalone: bool = False) -> Dict[str, Any]:
    """Verify a package directory, its ZIP, and an optional sign-off. Returns the verified package."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError(f"package directory is missing or a symlink: {directory}")
    root = directory.resolve()
    manifest_bytes = _read_regular(root / "manifest.json")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ContractError("manifest.json is not UTF-8 JSON") from None
    problems = validate_manifest(manifest)
    if problems:
        raise ContractError(problems)
    publication_id, revision = manifest["publication_id"], manifest["revision"]
    zip_name = f"{publication_id}-{revision}.zip"
    if standalone:
        zip_path = root / zip_name
        signoff_path = root / SIGNOFF if (root / SIGNOFF).exists() or (root / SIGNOFF).is_symlink() else None
    listed = {e["path"]: e for e in manifest["files"]}
    allowed = set(listed) | {"manifest.json"} | ({zip_name, SIGNOFF} if standalone else set())
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ContractError(f"symlink not allowed in package: {rel}")
            if name in names and rel not in allowed:
                raise ContractError(f"unlisted file in package: {rel}")
    for rel, entry in listed.items():
        path = safe_path(root, rel)
        data = _read_regular(path)
        if len(data) != entry["bytes"] or evidence.sha256_bytes(data) != entry["sha256"]:
            raise ContractError(f"package file {rel} checksum mismatch with manifest")
        _secret_check(rel, data)
    if zip_path is None or not Path(zip_path).name == zip_name:
        raise ContractError(f"package ZIP must be named {zip_name}")
    zip_bytes = _read_regular(Path(zip_path), MAX_PACKAGE_BYTES)
    _verify_zip(zip_bytes, manifest_bytes, manifest)
    signoff = signoff_bytes = None
    if signoff_path is not None and (Path(signoff_path).exists() or Path(signoff_path).is_symlink()):
        signoff_bytes = _read_regular(Path(signoff_path))
        _secret_check(SIGNOFF, signoff_bytes)
        try:
            signoff = json.loads(signoff_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ContractError("signoff.json is not UTF-8 JSON") from None
        if not isinstance(signoff, dict) or signoff.get("schema_version") != 1 \
                or signoff.get("publication_id") != publication_id or signoff.get("status") not in ("approved", "blocked"):
            raise ContractError("signoff.json is invalid for this publication")
        if signoff.get("manifest_sha256") != evidence.sha256_bytes(manifest_bytes):
            raise ContractError("signoff.json is stale: it was signed for a different manifest; rerun signoff")
    return {"root": root, "manifest": manifest, "manifest_bytes": manifest_bytes,
            "manifest_sha256": evidence.sha256_bytes(manifest_bytes), "zip_name": zip_name,
            "zip_path": Path(zip_path), "zip_sha256": evidence.sha256_bytes(zip_bytes), "zip_bytes": len(zip_bytes),
            "signoff": signoff, "signoff_bytes": signoff_bytes, "signoff_path": signoff_path}


def _verify_zip(zip_bytes: bytes, manifest_bytes: bytes, manifest: Dict[str, Any]) -> None:
    import io
    expected = {"manifest.json": (len(manifest_bytes), evidence.sha256_bytes(manifest_bytes))}
    expected.update({e["path"]: (e["bytes"], e["sha256"]) for e in manifest["files"]})
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as bundle:
            infos = bundle.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise ContractError("package ZIP entries do not match manifest.json")
            for info in infos:
                size, digest = expected[info.filename]
                if stat.S_ISLNK(info.external_attr >> 16) or info.file_size != size or info.flag_bits & 0x1:
                    raise ContractError(f"package ZIP entry {info.filename} is not the manifest file")
                if evidence.sha256_bytes(bundle.read(info)) != digest:
                    raise ContractError(f"package ZIP entry {info.filename} checksum mismatch")
    except zipfile.BadZipFile:
        raise ContractError("package ZIP is not a valid ZIP file") from None


def quality_of(package: Dict[str, Any]) -> str:
    if not package["manifest"]["complete"]:
        return "partial"
    if package["signoff"] is None:
        return "unsigned"
    return "approved" if package["signoff"]["status"] == "approved" else "blocked"


def evidence_sets(manifest: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    sets = {}
    for video_id in manifest["video_ids"]:
        prefix = f"sources/{video_id}/"
        entries = [dict(e, rel=e["path"][len(prefix):]) for e in manifest["files"] if e["path"].startswith(prefix)]
        if not entries:
            raise ContractError(f"package contains no evidence files for video {video_id}")
        sets[video_id] = sorted(entries, key=lambda e: e["rel"])
    return sets


def _workspace_package(workspace: Workspace, publication_id: str) -> Tuple[Dict[str, Any], Path, Dict[str, Any]]:
    plan, pub_dir = publication._publication(workspace, publication_id)
    package_dir = pub_dir / "package"
    if not package_dir.is_dir():
        raise ContractError(f"publication {publication_id} has no package; run package first")
    manifest = evidence.read_json(package_dir / "manifest.json")
    revision = manifest.get("revision") if isinstance(manifest, dict) else None
    zip_path = pub_dir / f"{publication_id}-{revision}.zip"
    package = load_package(package_dir, zip_path, pub_dir / SIGNOFF)
    if package["manifest"]["publication_id"] != plan["id"] or package["manifest"]["video_ids"] != plan["video_ids"]:
        raise ContractError("package manifest does not match the assignment publication")
    return package, pub_dir, plan


# ---------------------------------------------------------------------------
# Quality sign-off


def _fields(obj: Any, label: str, required: Set[str], optional: Set[str] = frozenset()) -> None:
    if not isinstance(obj, dict):
        raise ContractError(f"{label} must be an object")
    unknown = set(obj) - required - set(optional)
    missing = required - set(obj)
    if unknown or missing:
        raise ContractError(f"{label}: unknown fields {sorted(unknown)}, missing fields {sorted(missing)}")


def _text(obj: Dict[str, Any], key: str, label: str) -> None:
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        raise ContractError(f"{label}.{key} must be non-empty text")


def _transcript_provider(segments_doc: Dict[str, Any]) -> Dict[str, Any]:
    provider = segments_doc.get("provider") or {}
    return {k: provider[k] for k in ("name", "kind", "model", "version") if isinstance(provider.get(k), str)}


def _audio_verification(item: Dict[str, Any], label: str, segments_doc: Dict[str, Any],
                        duration: Optional[float]) -> Optional[Dict[str, Any]]:
    """Validate the reviewer's audio spot checks. Records what was compared, never an accuracy verdict."""
    audio = item.get("audio_verification")
    if audio is None:
        return None
    label = f"{label}.audio_verification"
    _fields(audio, label, {"method", "checks", "note"})
    _text(audio, "note", label)
    if audio["method"] not in AUDIO_METHODS:
        raise ContractError(f"{label}.method must be one of {sorted(AUDIO_METHODS)}")
    if not isinstance(audio["checks"], list) or not audio["checks"]:
        raise ContractError(f"{label}.checks must be a non-empty list of checked spans")
    spans = {s["id"]: s for s in segments_doc.get("segments", [])}
    checks = []
    for check in audio["checks"]:
        where = f"{label}.checks[]"
        _fields(check, where, {"start", "end", "segment_ids", "result", "note"})
        _text(check, "note", where)
        start, end = check["start"], check["end"]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (start, end)) \
                or start < 0 or end <= start or (duration is not None and end > duration + 0.001):
            raise ContractError(f"{where}: start/end must be numbers with 0 <= start < end <= the media duration")
        ids = check["segment_ids"]
        if not isinstance(ids, list) or not ids or not all(isinstance(s, str) for s in ids) \
                or len(set(ids)) != len(ids):
            raise ContractError(f"{where}.segment_ids must be a non-empty list of distinct segment ID strings")
        for segment_id in ids:
            segment = spans.get(segment_id)
            if segment is None or segment["end"] <= start or segment["start"] >= end:
                raise ContractError(f"{where}: segment {segment_id!r} is not a transcript segment inside "
                                    f"{start}-{end}s")
        if check["result"] not in AUDIO_RESULTS:
            raise ContractError(f"{where}.result must be one of {sorted(AUDIO_RESULTS)}")
        checks.append({"start": float(start), "end": float(end), "segment_ids": list(ids),
                       "result": check["result"], "note": check["note"]})
    covered, cursor = 0.0, 0.0
    for check in sorted(checks, key=lambda c: c["start"]):
        begin = max(check["start"], cursor)
        if check["end"] > begin:
            covered += check["end"] - begin
        cursor = max(cursor, check["end"])
    return {"method": audio["method"], "note": audio["note"], "checks": checks,
            "checked_seconds": round(covered, 3),
            "checked_fraction": round(covered / duration, 4) if duration else None,
            "limits": "Reviewer spot checks of the listed spans against the source audio; this is not a measured "
                      "accuracy rate, and unchecked spans remain unverified."}


def _stage_snapshot(record: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": record.get("status"), "inputs": record.get("inputs", {}), "outputs": record.get("outputs", {})}


def cmd_signoff(args: Any) -> int:
    workspace = Workspace(Path(args.workspace))
    package, pub_dir, plan = _workspace_package(workspace, args.publication)
    review_bytes = Path(args.review).read_bytes()
    _secret_check("review.json", review_bytes)
    try:
        review = json.loads(review_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ContractError("review is not UTF-8 JSON") from None
    _fields(review, "review", {"schema_version", "publication_id", "reviewer", "decision", "note", "videos"})
    _text(review, "reviewer", "review")
    _text(review, "note", "review")
    if review["schema_version"] != 1 or review["publication_id"] != plan["id"]:
        raise ContractError(f"review must have schema_version 1 and publication_id {plan['id']!r}")
    if review["decision"] not in ("approve", "block"):
        raise ContractError("review.decision must be approve or block")
    _fields(review["videos"], "review.videos", set(plan["video_ids"]))
    state = workspace.state()
    blockers: List[str] = []
    if not package["manifest"]["complete"]:
        blockers.append("package is incomplete: " + "; ".join(package["manifest"]["incomplete_reasons"]))
    if review["decision"] == "block":
        blockers.append(f"reviewer blocked sign-off: {review['note']}")
    for entry in package["manifest"]["files"]:
        if entry["path"].startswith("sources/"):
            current = workspace.path(entry["path"])
            if not current.is_file() or evidence.sha256_file(current) != entry["sha256"]:
                raise ContractError(f"package is stale: {entry['path']} changed since packaging; rerun render/package")
    videos = {}
    for video_id in plan["video_ids"]:
        item = review["videos"][video_id]
        label = f"review.videos.{video_id}"
        _fields(item, label, {"transcript_coverage", "visual_coverage", "gaps", "uncertain_segments"},
                {"note", "audio_verification"})
        stages = {}
        for stage in SNAPSHOT_STAGES:
            key = evidence.stage_key(video_id, stage)
            record = state["stages"].get(key)
            if not record or record.get("status") != "complete":
                if stage in REQUIRED_STAGES:
                    what = {"download": "source download (temporary media) coverage cannot be confirmed",
                            "frames": "no frame coverage was extracted"}.get(stage, "evidence is incomplete")
                    blockers.append(f"{video_id}: {stage} stage is {record.get('status') if record else 'missing'}; "
                                    f"{what}")
                continue
            problems = evidence.stage_problems(workspace, key, record)
            if problems:
                raise ContractError(problems + ["evidence changed after it was recorded; rerun the stage"])
            stages[stage] = _stage_snapshot(record)
        media = {}
        for rel in state.get("temporary_media", []):
            if rel.startswith(f"sources/{video_id}/"):
                path = workspace.path(rel)
                if path.is_file():
                    media[rel] = evidence.sha256_file(path)
        coverage = evidence.read_json(workspace.source_dir(video_id) / "transcript" / "coverage.json")
        for key in ("transcript_coverage", "visual_coverage"):
            if item[key] not in ("verified", "unverified"):
                raise ContractError(f"{label}.{key} must be verified or unverified")
            if item[key] != "verified":
                blockers.append(f"{video_id}: {key.replace('_', ' ')} is unverified")
        if coverage.get("duration") is None:
            blockers.append(f"{video_id}: transcript duration is unknown, so trailing coverage cannot be verified")
        segments_doc = evidence.read_json(workspace.source_dir(video_id) / "transcript" / "segments.json")
        provider = _transcript_provider(segments_doc)
        audio = _audio_verification(item, label, segments_doc, coverage.get("duration"))
        if provider.get("kind") in AUDIO_CHECK_KINDS and audio is None:
            blockers.append(f"{video_id}: {provider['kind']} transcript has no audio verification; spot-check "
                            "spans against the source audio and record them in audio_verification")
        for check in (audio or {"checks": []})["checks"]:
            if check["result"] == "differs":
                blockers.append(f"{video_id}: audio check {check['start']}-{check['end']}s differs from the "
                                "transcript; correct and re-import the transcript, then review again")
        gaps = coverage["gaps"]
        matched: Dict[int, Dict[str, Any]] = {}
        for entry in item["gaps"] if isinstance(item["gaps"], list) else [None]:
            _fields(entry, f"{label}.gaps[]", {"start", "end", "resolution", "note"})
            _text(entry, "note", f"{label}.gaps[]")
            if entry["resolution"] not in GAP_RESOLUTIONS:
                raise ContractError(f"{label}.gaps[] resolution must be one of {sorted(GAP_RESOLUTIONS)}")
            index = next((i for i, g in enumerate(gaps) if isinstance(entry["start"], (int, float))
                          and isinstance(entry["end"], (int, float)) and abs(g["start"] - entry["start"]) <= 0.001
                          and abs(g["end"] - entry["end"]) <= 0.001), None)
            if index is None:
                raise ContractError(f"{label}: {entry['start']}-{entry['end']}s is not a transcript gap in coverage.json")
            if index in matched:
                raise ContractError(f"{label}: gap {index} is reviewed twice")
            matched[index] = entry
        for index, gap in enumerate(gaps):
            if index not in matched:
                blockers.append(f"{video_id}: gap {index} ({gap['start']}-{gap['end']}s) has no review")
            elif matched[index]["resolution"] == "unresolved":
                blockers.append(f"{video_id}: gap {index} ({gap['start']}-{gap['end']}s) is unresolved")
        uncertain = coverage["uncertain_segment_ids"]
        reviewed: Dict[str, str] = {}
        for entry in item["uncertain_segments"] if isinstance(item["uncertain_segments"], list) else [None]:
            _fields(entry, f"{label}.uncertain_segments[]", {"segment_id", "resolution", "note"})
            _text(entry, "note", f"{label}.uncertain_segments[]")
            if entry["segment_id"] not in uncertain or entry["segment_id"] in reviewed:
                raise ContractError(f"{label}: {entry['segment_id']!r} is not an unreviewed uncertain segment")
            if entry["resolution"] not in UNCERTAIN_RESOLUTIONS:
                raise ContractError(f"{label}.uncertain_segments[] resolution must be one of "
                                    f"{sorted(UNCERTAIN_RESOLUTIONS)}")
            reviewed[entry["segment_id"]] = entry["resolution"]
        for segment_id in uncertain:
            if segment_id not in reviewed:
                blockers.append(f"{video_id}: uncertain segment {segment_id} has no review")
            elif reviewed[segment_id] == "unresolved":
                blockers.append(f"{video_id}: uncertain segment {segment_id} is unresolved")
        videos[video_id] = {"stages": stages, "media": media, "transcript_provider": provider,
                            "audio_verification": audio,
                            "coverage": {"duration": coverage.get("duration"), "gaps": gaps,
                                         "uncertain_segment_ids": uncertain, "warnings": coverage.get("warnings", [])}}
    status = "blocked" if blockers else "approved"
    record = {"schema_version": 1, "publication_id": plan["id"], "status": status, "blockers": blockers,
              "revision": package["manifest"]["revision"], "manifest_sha256": package["manifest_sha256"],
              "zip_sha256": package["zip_sha256"], "review_sha256": evidence.sha256_bytes(review_bytes),
              "review": review, "videos": videos, "signed_at": evidence.now(),
              "limits": "Sign-off records reviewed coverage; it does not prove every word or frame was understood."}
    evidence.atomic_write_json(pub_dir / SIGNOFF, record)
    publication.emit({"status": status, "publication": plan["id"], "blockers": blockers,
                      "signoff": str(pub_dir / SIGNOFF), "signoff_sha256": evidence.sha256_file(pub_dir / SIGNOFF)})
    return 0 if status == "approved" else 1


# ---------------------------------------------------------------------------
# Archive


def _canonical(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _attempt() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)


def _upload_verified(client: BlobClient, name: str, data: bytes, content_type: str) -> None:
    client.put(name, data, content_type)
    if evidence.sha256_bytes(client.get(name)) != evidence.sha256_bytes(data):
        raise ArchiveError(f"read-back of {name} does not match the uploaded bytes")


def archive_package(package: Dict[str, Any], client: BlobClient, attempt: str) -> Dict[str, Any]:
    manifest, root = package["manifest"], package["root"]
    publication_id, revision = manifest["publication_id"], manifest["revision"]
    pub_prefix = f"publications/{publication_id}/{revision}/{attempt}"
    objects: List[Dict[str, Any]] = []
    sources: Dict[str, Tuple[Path, str]] = {}
    videos: Dict[str, Dict[str, Any]] = {}
    for video_id, entries in evidence_sets(manifest).items():
        listing = [{"path": e["rel"], "sha256": e["sha256"], "bytes": e["bytes"]} for e in entries]
        evidence_revision = evidence.digest_json(listing)[:16]
        prefix = f"videos/{video_id}/evidence/{evidence_revision}/{attempt}"
        videos[video_id] = {"evidence_revision": evidence_revision, "prefix": prefix,
                            "files": {e["rel"]: {"sha256": e["sha256"], "bytes": e["bytes"]} for e in entries}}
        for entry in entries:
            objects.append({"path": entry["path"], "blob": f"{prefix}/files/{entry['rel']}",
                            "sha256": entry["sha256"], "bytes": entry["bytes"]})
    for entry in manifest["files"]:
        if not entry["path"].startswith("sources/"):
            objects.append({"path": entry["path"], "blob": f"{pub_prefix}/files/{entry['path']}",
                            "sha256": entry["sha256"], "bytes": entry["bytes"]})
    for path, source in [(e["path"], root / e["path"]) for e in manifest["files"]]:
        sources[path] = (source, path)
    extra = [("manifest.json", package["manifest_bytes"], f"{pub_prefix}/manifest.json")]
    extra.append((package["zip_name"], None, f"{pub_prefix}/{package['zip_name']}"))
    if package["signoff_bytes"] is not None:
        extra.append((SIGNOFF, package["signoff_bytes"], f"{pub_prefix}/{SIGNOFF}"))
    for path, data, blob in extra:
        size = package["zip_bytes"] if data is None else len(data)
        digest = package["zip_sha256"] if data is None else evidence.sha256_bytes(data)
        objects.append({"path": path, "blob": blob, "sha256": digest, "bytes": size})
    inline = {path: data for path, data, _ in extra if data is not None}

    def payload(obj: Dict[str, Any]) -> bytes:
        if obj["path"] in inline:
            data = inline[obj["path"]]
        elif obj["path"] == package["zip_name"]:
            data = _read_regular(package["zip_path"], MAX_PACKAGE_BYTES)
        else:
            data = _read_regular(safe_path(root, obj["path"]))
        if evidence.sha256_bytes(data) != obj["sha256"] or len(data) != obj["bytes"]:
            raise ContractError(f"{obj['path']} changed during archival (checksum mismatch); nothing was marked complete")
        return data

    for obj in objects:
        client.put(obj["blob"], payload(obj), CONTENT_TYPES.get(Path(obj["path"]).suffix.lower(),
                                                              "application/octet-stream"))
    for obj in objects:
        data = client.get(obj["blob"])
        if len(data) != obj["bytes"] or evidence.sha256_bytes(data) != obj["sha256"]:
            raise ArchiveError(f"read-back of {obj['path']} ({obj['blob']}) does not match its checksum")
    quality = {"status": quality_of(package), "package_complete": manifest["complete"],
               "incomplete_reasons": manifest["incomplete_reasons"], "signoff": None}
    if package["signoff"] is not None:
        quality["signoff"] = {"status": package["signoff"]["status"], "blockers": package["signoff"].get("blockers", []),
                              "sha256": evidence.sha256_bytes(package["signoff_bytes"]),
                              "blob": f"{pub_prefix}/{SIGNOFF}"}
    for video_id, info in videos.items():
        marker = {"schema_version": 1, "kind": "distilling-videos-evidence", "video_id": video_id,
                  "publication_id": publication_id, "publication_revision": revision, "attempt": attempt,
                  "evidence_revision": info["evidence_revision"], "files": info["files"], "quality": quality["status"]}
        data = _canonical(marker)
        info["marker_blob"] = f"{info['prefix']}/{MARKER}"
        info["marker_sha256"] = evidence.sha256_bytes(data)
        _upload_verified(client, info["marker_blob"], data, "application/json")
    marker = {"schema_version": 1, "kind": "distilling-videos-archive", "publication_id": publication_id,
              "revision": revision, "attempt": attempt, "manifest_sha256": package["manifest_sha256"],
              "zip": {"blob": f"{pub_prefix}/{package['zip_name']}", "sha256": package["zip_sha256"]},
              "quality": quality, "videos": videos, "objects": objects, "archived_at": evidence.now()}
    data = _canonical(marker)
    marker_blob = f"{pub_prefix}/{MARKER}"
    _upload_verified(client, marker_blob, data, "application/json")
    return {"schema_version": 1, "kind": "distilling-videos-archive-receipt", "container_url": client.url,
            "marker_blob": marker_blob, "marker_sha256": evidence.sha256_bytes(data), "marker": marker,
            "verified_at": evidence.now()}


def cmd_archive(args: Any) -> int:
    client = BlobClient(args.container, os.environ.get(SAS_ENV), getattr(args, "transport", None), write=True)
    if args.package_dir:
        if args.workspace or args.publication or not args.receipt:
            raise ContractError("--package-dir needs --receipt and excludes --workspace/--publication")
        package = load_package(Path(args.package_dir), standalone=True)
        receipt_path = Path(args.receipt)
    else:
        if not args.workspace or not args.publication:
            raise ContractError("archive needs --workspace and --publication, or --package-dir and --receipt")
        package, pub_dir, _ = _workspace_package(Workspace(Path(args.workspace)), args.publication)
        receipt_path = Path(args.receipt) if args.receipt else pub_dir / RECEIPT
    if receipt_path.is_symlink():
        raise ContractError("receipt path must not be a symlink")
    attempt = _attempt()
    try:
        receipt = archive_package(package, client, attempt)
    except ArchiveError as error:
        print(f"error: archive failed: {error}. No completion marker was written; objects already uploaded under "
              f"attempt {attempt} are not an archive and are never reused.", file=sys.stderr)
        return 5
    evidence.atomic_write_json(receipt_path, receipt)
    status = receipt["marker"]["quality"]["status"]
    publication.emit({"status": "archived", "publication": package["manifest"]["publication_id"],
                      "revision": package["manifest"]["revision"], "attempt": attempt,
                      "container": client.url, "marker_blob": receipt["marker_blob"],
                      "marker_sha256": receipt["marker_sha256"], "objects": len(receipt["marker"]["objects"]),
                      "quality": receipt["marker"]["quality"], "cleanup_eligible": status == "approved",
                      "receipt": str(receipt_path)})
    return 0


# ---------------------------------------------------------------------------
# Verification


def validate_receipt(receipt: Any, container_url: str, publication_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        _fields(receipt, "receipt", {"schema_version", "kind", "container_url", "marker_blob", "marker_sha256",
                                     "marker", "verified_at"})
        marker = receipt["marker"]
        _fields(marker, "receipt.marker", {"schema_version", "kind", "publication_id", "revision", "attempt",
                                           "manifest_sha256", "zip", "quality", "videos", "objects", "archived_at"})
        if receipt["kind"] != "distilling-videos-archive-receipt" or marker["kind"] != "distilling-videos-archive":
            raise ContractError("not a distilling-videos archive receipt")
        if receipt["container_url"] != container_url:
            raise ContractError("receipt container does not match --container; refusing to send the SAS elsewhere")
        if publication_id is not None and marker["publication_id"] != publication_id:
            raise ContractError(f"receipt is for publication {marker['publication_id']!r}, not {publication_id!r}")
        check_id(marker["publication_id"], "publication")
        if not re.match(r"^[0-9a-f]{16}$", str(marker["revision"])) or \
                not re.match(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$", str(marker["attempt"])):
            raise ContractError("receipt revision/attempt are invalid")
        pub_prefix = f"publications/{marker['publication_id']}/{marker['revision']}/{marker['attempt']}/"
        if receipt["marker_blob"] != pub_prefix + MARKER or not HEX64.match(str(receipt["marker_sha256"])):
            raise ContractError("receipt marker location or digest is invalid")
        prefixes = [pub_prefix]
        for video_id, info in marker["videos"].items():
            check_id(video_id, "video")
            prefix = f"videos/{video_id}/evidence/{info['evidence_revision']}/{marker['attempt']}"
            if info["prefix"] != prefix or info["marker_blob"] != f"{prefix}/{MARKER}":
                raise ContractError(f"receipt evidence location for {video_id} is invalid")
            prefixes.append(prefix + "/")
            for rel in info["files"]:
                check_rel(rel, "evidence path")
        for obj in marker["objects"]:
            check_blob_name(obj["blob"])
            if not obj["blob"].startswith(tuple(prefixes)) or not HEX64.match(str(obj["sha256"])):
                raise ContractError(f"receipt object {obj['blob']!r} is outside the archive prefixes")
    except (KeyError, TypeError, AttributeError):
        raise ContractError("receipt is malformed") from None
    return receipt


def verify_remote(client: BlobClient, receipt: Dict[str, Any]) -> List[str]:
    marker = receipt["marker"]
    data = client.get(receipt["marker_blob"])
    if evidence.sha256_bytes(data) != receipt["marker_sha256"]:
        return ["remote completion marker does not match the receipt (checksum mismatch)"]
    try:
        remote = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["remote completion marker is not JSON"]
    if remote != marker:
        return ["receipt marker content differs from the remote completion marker (local receipt tampered)"]
    problems = []
    for video_id, info in marker["videos"].items():
        try:
            data = client.get(info["marker_blob"])
            remote = json.loads(data.decode("utf-8"))
            if evidence.sha256_bytes(data) != info["marker_sha256"] or remote.get("files") != info["files"]:
                problems.append(f"remote evidence marker for {video_id} mismatch with receipt")
        except (ArchiveError, ValueError, AttributeError) as error:
            problems.append(f"remote evidence marker for {video_id}: {error}")
    for obj in marker["objects"]:
        try:
            data = client.get(obj["blob"])
        except ArchiveError as error:
            problems.append(f"remote object {obj['path']}: {error}")
            continue
        if len(data) != obj["bytes"] or evidence.sha256_bytes(data) != obj["sha256"]:
            problems.append(f"remote object {obj['path']} ({obj['blob']}) checksum mismatch")
    return problems


def _receipt_path(args: Any) -> Path:
    if args.receipt:
        return Path(args.receipt)
    if not args.workspace or not args.publication:
        raise ContractError("pass --receipt, or --workspace and --publication")
    _, pub_dir = publication._publication(Workspace(Path(args.workspace)), args.publication)
    return pub_dir / RECEIPT


def cmd_verify(args: Any) -> int:
    client = BlobClient(args.container, os.environ.get(SAS_ENV), getattr(args, "transport", None), write=False)
    path = _receipt_path(args)
    if not path.is_file():
        raise ContractError(f"no archive receipt at {path}; run archive first")
    receipt = validate_receipt(evidence.read_json(path), client.url, args.publication)
    try:
        problems = verify_remote(client, receipt)
    except ArchiveError as error:
        print(f"error: verification failed: {error}", file=sys.stderr)
        return 5
    publication.emit({"ok": not problems, "errors": problems, "marker_blob": receipt["marker_blob"],
                      "objects": len(receipt["marker"]["objects"]), "quality": receipt["marker"]["quality"]})
    return 0 if not problems else 1


# ---------------------------------------------------------------------------
# Cleanup of tracked temporary media


def _open_parent(root: Path, rel: str) -> Tuple[int, str]:
    parts = rel.split("/")
    fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except OSError as error:
                raise ContractError(f"cleanup refused: {rel}: {part!r} is a symlink or not a directory "
                                    f"({error.strerror})") from None
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd, parts[-1]


def _check_or_delete(root: Path, rel: str, expected: str, delete: bool) -> None:
    """Hash then optionally unlink a media file without following symlinks at any component."""
    fd, name = _open_parent(root, rel)
    try:
        try:
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            raise ContractError(f"cleanup refused: tracked media {rel} is missing") from None
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ContractError(f"cleanup refused: {rel} is a symlink or not a regular file")
        handle_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        digest = hashlib.sha256()
        with os.fdopen(handle_fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino) or digest.hexdigest() != expected:
            raise ContractError(f"cleanup refused: media {rel} changed since sign-off (checksum mismatch)")
        if delete:
            again = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if (again.st_dev, again.st_ino) != (info.st_dev, info.st_ino) or stat.S_ISLNK(again.st_mode):
                raise ContractError(f"cleanup refused: {rel} was replaced during cleanup")
            os.unlink(name, dir_fd=fd)
    finally:
        os.close(fd)


def _plan_video(workspace: Workspace, state: Dict[str, Any], video_id: str, receipt: Dict[str, Any],
                signoff: Dict[str, Any]) -> Optional[List[Tuple[str, str]]]:
    """Local checks binding this video's current evidence and media to the archive. None = already clean."""
    marker = receipt["marker"]
    temporary = [m for m in state.get("temporary_media", []) if m.startswith(f"sources/{video_id}/")]
    download = state["stages"].get(evidence.stage_key(video_id, "download")) or {}
    if not temporary and download.get("media_cleaned"):
        return None
    if video_id not in marker["videos"] or video_id not in signoff.get("videos", {}):
        raise ContractError(f"cleanup refused: {video_id} is not in the archived publication and sign-off")
    signed = signoff["videos"][video_id]
    for stage in REQUIRED_STAGES:
        if stage not in signed.get("stages", {}):
            raise ContractError(f"cleanup refused: sign-off has no complete {stage} evidence for {video_id}")
    for stage, snapshot in signed["stages"].items():
        key = evidence.stage_key(video_id, stage)
        record = state["stages"].get(key)
        if not record or _stage_snapshot(record) != snapshot:
            raise ContractError(f"cleanup refused: {key} changed since sign-off (stale evidence)")
        problems = evidence.stage_problems(workspace, key, record)
        if problems:
            raise ContractError(["cleanup refused: current evidence does not match its record"] + problems)
    base = workspace.source_dir(video_id)
    provider = _transcript_provider(evidence.read_json(base / "transcript" / "segments.json"))
    if signed.get("transcript_provider") != provider:
        raise ContractError(f"cleanup refused: sign-off does not record the current transcript provider for "
                            f"{video_id}; rerun signoff and archive")
    if provider.get("kind") in AUDIO_CHECK_KINDS:
        audio = signed.get("audio_verification")
        checks = audio.get("checks") if isinstance(audio, dict) else None
        if not isinstance(checks, list) or not checks or any(c.get("result") != "matches" for c in checks):
            raise ContractError(f"cleanup refused: {video_id} has a {provider['kind']} transcript without passing "
                                "audio verification in the sign-off; media is kept so the audio can be checked")
    archived = marker["videos"][video_id]["files"]
    for rel, info in archived.items():
        path = safe_path(base, check_rel(rel, "evidence path"))
        if not path.is_file() or evidence.sha256_file(path) != info["sha256"]:
            raise ContractError(f"cleanup refused: local evidence {rel} mismatch with the archived receipt")
    for rel in CORE_EVIDENCE:
        if (base / rel).is_file() and rel not in archived:
            raise ContractError(f"cleanup refused: local evidence {rel} for {video_id} was never archived")
    pattern = re.compile(rf"^sources/{re.escape(video_id)}/(?:media|audio)/[A-Za-z0-9_][A-Za-z0-9._-]*$")
    archived_paths = {o["path"] for o in marker["objects"]}
    planned = []
    for rel, digest in sorted(signed.get("media", {}).items()):
        if not pattern.match(rel) or rel not in temporary or rel in archived_paths or not HEX64.match(str(digest)):
            raise ContractError(f"cleanup refused: signed-off media path {rel!r} is not tracked temporary media "
                                f"for {video_id}")
        planned.append((rel, digest))
    return planned


def cmd_cleanup(args: Any) -> int:
    workspace = Workspace(Path(args.workspace))
    assignment = workspace.assignment()
    state = workspace.state()
    if state.get("assignment_sha256") != evidence.digest_json(assignment):
        raise ContractError("state.json does not match assignment.json; refusing cleanup")
    if args.publication:
        plans = [p for p in assignment["publications"] if p["id"] == args.publication]
        if not plans:
            raise ContractError(f"publication {args.publication!r} is not in the assignment")
        targets = list(plans[0]["video_ids"])
    elif args.video:
        targets = [workspace.video(v)["id"] for v in args.video]
    else:
        raise ContractError("cleanup needs --video (repeatable) or --publication")
    if assignment["retain_media"]:
        publication.emit({"status": "retained", "deleted": [],
                          "videos": {v: {"status": "retained", "reason": "assignment retain_media is true"}
                                     for v in targets}})
        return 0
    client = BlobClient(args.container, os.environ.get(SAS_ENV), getattr(args, "transport", None), write=False)
    if args.receipt and len({p["id"] for p in assignment["publications"] if set(p["video_ids"]) & set(targets)}) > 1:
        raise ContractError("--receipt applies to one publication; clean one publication at a time")
    planned: List[Tuple[str, str, str]] = []
    results: Dict[str, Dict[str, Any]] = {}
    markers: Dict[str, str] = {}
    for plan in assignment["publications"]:
        videos = [v for v in targets if v in plan["video_ids"]]
        if not videos:
            continue
        pub_dir = workspace.path(f"publications/{plan['id']}")
        path = Path(args.receipt) if args.receipt else pub_dir / RECEIPT
        if not path.is_file():
            raise ContractError(f"cleanup refused: no archive receipt for publication {plan['id']}; archive first")
        receipt = validate_receipt(evidence.read_json(path), client.url, plan["id"])
        quality = receipt["marker"]["quality"]
        if quality["status"] != "approved" or not quality["package_complete"]:
            raise ContractError(f"cleanup refused: archived quality status is {quality['status']!r}, not approved; "
                                "partial, unsigned, or blocked archives never release media")
        signoff_path = pub_dir / SIGNOFF
        if signoff_path.is_symlink() or not signoff_path.is_file() or \
                evidence.sha256_file(signoff_path) != (quality["signoff"] or {}).get("sha256"):
            raise ContractError("cleanup refused: local signoff.json mismatch with the archived sign-off")
        signoff = evidence.read_json(signoff_path)
        if signoff.get("status") != "approved" or signoff.get("manifest_sha256") != receipt["marker"]["manifest_sha256"]:
            raise ContractError("cleanup refused: sign-off is not approved for the archived manifest")
        if not any(o["path"] == SIGNOFF and o["sha256"] == quality["signoff"]["sha256"]
                   for o in receipt["marker"]["objects"]):
            raise ContractError("cleanup refused: the sign-off was not archived")
        pending = False
        for video_id in videos:
            items = _plan_video(workspace, state, video_id, receipt, signoff)
            if items is None:
                results[video_id] = {"status": "already-clean"}
                continue
            pending = True
            results[video_id] = {"status": "pending", "media": [rel for rel, _ in items]}
            planned += [(video_id, rel, digest) for rel, digest in items]
            markers[video_id] = receipt["marker_sha256"]
        if pending:
            try:
                problems = verify_remote(client, receipt)
            except ArchiveError as error:
                print(f"error: cleanup refused: remote verification failed: {error}", file=sys.stderr)
                return 5
            if problems:
                raise ContractError(["cleanup refused: remote archive verification failed"] + problems)
    for _, rel, digest in planned:
        safe_path(workspace.root, rel)
        _check_or_delete(workspace.root, rel, digest, delete=False)
    if args.dry_run:
        publication.emit({"status": "dry-run", "would_delete": [rel for _, rel, _ in planned], "videos": results})
        return 0
    deleted: Dict[str, str] = {}
    errors: List[str] = []

    def change(current: Dict[str, Any]) -> None:
        tracked = set(current.get("temporary_media", []))
        for _, rel, digest in planned:
            if errors:
                break
            if rel not in tracked:
                errors.append(f"{rel} is no longer tracked temporary media")
                break
            try:
                _check_or_delete(workspace.root, rel, digest, delete=True)
                deleted[rel] = digest
            except (ContractError, OSError) as error:
                errors.append(str(error))
        current["temporary_media"] = sorted(tracked - set(deleted))
        for key, record in current["stages"].items():
            base = record.get("base", key.rsplit("/", 1)[0])
            for kind in ("inputs", "outputs"):
                values = record.get(kind) or {}
                for rel in list(values):
                    if f"{base}/{rel}" in deleted:
                        record.setdefault(f"cleaned_{kind}", {})[rel] = values.pop(rel)
        for video_id in {v for v, rel, _ in planned if rel in deleted}:
            record = current["stages"].get(evidence.stage_key(video_id, "download"))
            if record:
                config = dict(record.get("config") or {}, media_cleaned=True)
                record["config"], record["config_sha256"] = config, evidence.digest_json(config)
                record["media_cleaned"] = {"at": evidence.now(), "receipt_marker_sha256": markers[video_id],
                                           "files": {r: d for r, d in deleted.items()
                                                     if r.startswith(f"sources/{video_id}/")}}

    workspace.update_state(change)
    for video_id, result in results.items():
        if result["status"] == "pending":
            result["status"] = "cleaned" if all(r in deleted for r in result.pop("media")) else "partial"
    if errors:
        raise ContractError(["cleanup stopped; state records exactly what was deleted"] + errors)
    publication.emit({"status": "cleaned", "deleted": sorted(deleted), "videos": results,
                      "kept": "evidence, publications, packages, receipts, and all remote objects"})
    return 0


# ---------------------------------------------------------------------------
# GitHub Actions hand-off: provenance and safe artifact unpacking


def cmd_actions_provenance(args: Any) -> int:
    run = evidence.read_json(Path(args.run_json))
    listing = evidence.read_json(Path(args.artifacts_json))
    repository = args.repository.lower()
    allowed = [w for w in re.split(r"[\s,]+", args.allowed_workflows or "") if w]
    problems = []
    if not allowed:
        problems.append("no producer workflows are allowlisted (DISTILL_PRODUCER_WORKFLOWS); failing closed")
    for workflow in allowed:
        if not re.match(r"^\.github/workflows/[A-Za-z0-9._-]+\.ya?ml$", workflow) or workflow == THIS_WORKFLOW:
            problems.append(f"invalid producer workflow allowlist entry {workflow!r}")
    try:
        run_id = int(args.run_id)
        path = str(run.get("path", ""))
        workflow, _, ref = path.partition("@")
        checks = {
            "run id matches": run.get("id") == run_id,
            "run completed successfully": run.get("status") == "completed" and run.get("conclusion") == "success",
            "run belongs to this repository": str(run["repository"]["full_name"]).lower() == repository,
            "run head is this repository (not a fork)": str(run["head_repository"]["full_name"]).lower() == repository
            and run["head_repository"].get("id") == run["repository"].get("id"),
            f"trusted event ({sorted(TRUSTED_EVENTS)})": run.get("event") in TRUSTED_EVENTS,
            "run is on the default branch": run.get("head_branch") == args.default_branch
            and ref in ("", args.default_branch, f"refs/heads/{args.default_branch}"),
            "producer workflow is allowlisted": workflow in allowed,
        }
        problems += [f"provenance check failed: {name}" for name, ok in checks.items() if not ok]
        matches = [a for a in listing.get("artifacts", []) if a.get("name") == args.artifact_name]
        if len(matches) != 1:
            problems.append(f"expected exactly one artifact named {args.artifact_name!r}, found {len(matches)}")
        else:
            artifact = matches[0]
            origin = artifact.get("workflow_run") or {}
            if artifact.get("expired") is not False:
                problems.append("artifact is expired")
            if origin.get("id") != run_id or origin.get("repository_id") != run["repository"].get("id") or \
                    origin.get("head_repository_id") != run["repository"].get("id"):
                problems.append("artifact was not produced by this run in this repository")
            if origin.get("head_sha") not in (None, run.get("head_sha")):
                problems.append("artifact head_sha differs from the run")
            if not re.match(r"^sha256:[0-9a-f]{64}$", str(artifact.get("digest"))):
                problems.append("artifact has no sha256 digest (upload-artifact v4+ is required)")
            if not isinstance(artifact.get("size_in_bytes"), int) or artifact["size_in_bytes"] > MAX_PACKAGE_BYTES:
                problems.append("artifact size is missing or above the package limit")
    except (KeyError, TypeError, ValueError, AttributeError):
        problems.append("workflow run or artifact JSON is malformed")
    if problems:
        raise ContractError(problems)
    publication.emit({"status": "trusted", "run_id": run_id, "workflow": workflow, "head_sha": run.get("head_sha"),
                      "artifact_id": artifact["id"], "digest": artifact["digest"],
                      "size_in_bytes": artifact["size_in_bytes"]})
    return 0


def cmd_unpack_artifact(args: Any) -> int:
    match = re.match(r"^(?:sha256:)?([0-9a-f]{64})$", args.digest or "")
    if not match or not HEX64.match(args.expected_manifest_sha256 or ""):
        raise ContractError("--digest and --expected-manifest-sha256 must be sha256 hex digests")
    zip_path = Path(args.zip)
    data = _read_regular(zip_path, MAX_PACKAGE_BYTES)
    if evidence.sha256_bytes(data) != match.group(1):
        raise ContractError("artifact digest mismatch; refusing to unpack")
    dest = Path(args.dest)
    if dest.exists() or dest.is_symlink():
        raise ContractError("--dest must not exist")
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            infos = bundle.infolist()
            if len(infos) > MAX_FILES + 3 or sum(i.file_size for i in infos) > MAX_PACKAGE_BYTES:
                raise ContractError("artifact has too many entries or is too large")
            seen: Set[str] = set()
            files = []
            for info in infos:
                name = info.filename[:-1] if info.is_dir() else info.filename
                check_rel(name, "artifact entry")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode) or (mode and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))) \
                        or info.flag_bits & 0x1:
                    raise ContractError(f"artifact entry {name} is a symlink, special, or encrypted file")
                if name.lower() in seen:
                    raise ContractError(f"duplicate artifact entry {name}")
                seen.add(name.lower())
                if info.is_dir():
                    continue
                if Path(name).suffix.lower() not in publication.PACKAGE_EXTENSIONS | {".zip"} or \
                        info.file_size > MAX_PACKAGE_BYTES:
                    raise ContractError(f"unexpected file in artifact: {name}")
                files.append(info)
            dest.mkdir(mode=0o700)
            try:
                for info in files:
                    target = dest / info.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(info) as source, open(target, "xb") as handle:
                        content = source.read(info.file_size + 1)
                        if len(content) != info.file_size:
                            raise ContractError(f"artifact entry {info.filename} size mismatch")
                        handle.write(content)
                package = load_package(dest, standalone=True)
                if package["manifest_sha256"] != args.expected_manifest_sha256:
                    raise ContractError("artifact manifest does not match --expected-manifest-sha256")
            except BaseException:
                shutil.rmtree(dest, ignore_errors=True)
                raise
    except zipfile.BadZipFile:
        raise ContractError("artifact is not a valid ZIP file") from None
    publication.emit({"status": "unpacked", "dest": str(dest), "publication": package["manifest"]["publication_id"],
                      "revision": package["manifest"]["revision"], "manifest_sha256": package["manifest_sha256"],
                      "complete": package["manifest"]["complete"], "quality": quality_of(package)})
    return 0


# ---------------------------------------------------------------------------
# Registration


def register(subparsers: Any) -> None:
    signoff = subparsers.add_parser("signoff", help="record a quality sign-off bound to the current package")
    signoff.add_argument("--workspace", required=True)
    signoff.add_argument("--publication", required=True)
    signoff.add_argument("--review", required=True, help="Amp-authored quality review JSON")
    signoff.set_defaults(func=cmd_signoff)

    archive = subparsers.add_parser("archive", help="upload a verified package to Azure Blob (SAS from "
                                                    f"{SAS_ENV}) and write a completion marker last")
    archive.add_argument("--workspace")
    archive.add_argument("--publication")
    archive.add_argument("--package-dir", help="standalone package (manifest, files, ZIP, optional signoff.json)")
    archive.add_argument("--container", required=True, help="https://<account>.blob.core.windows.net/<container>")
    archive.add_argument("--receipt", help="receipt path (default publications/<P>/archive-receipt.json)")
    archive.set_defaults(func=cmd_archive)

    verify = subparsers.add_parser("verify-archive", help="re-download and verify every archived object")
    verify.add_argument("--workspace")
    verify.add_argument("--publication")
    verify.add_argument("--receipt")
    verify.add_argument("--container", required=True)
    verify.set_defaults(func=cmd_verify)

    cleanup = subparsers.add_parser("cleanup", help="delete tracked temporary media after approved, verified archive")
    cleanup.add_argument("--workspace", required=True)
    cleanup.add_argument("--video", action="append")
    cleanup.add_argument("--publication")
    cleanup.add_argument("--receipt")
    cleanup.add_argument("--container", required=True)
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.set_defaults(func=cmd_cleanup)

    unpack = subparsers.add_parser("unpack-artifact", help="safely unpack and verify a downloaded Actions artifact")
    unpack.add_argument("--zip", required=True)
    unpack.add_argument("--digest", required=True, help="artifact digest from the GitHub API (sha256:...)")
    unpack.add_argument("--dest", required=True)
    unpack.add_argument("--expected-manifest-sha256", required=True)
    unpack.set_defaults(func=cmd_unpack_artifact)

    provenance = subparsers.add_parser("actions-provenance", help="check a workflow run and artifact are trusted")
    provenance.add_argument("--run-json", required=True)
    provenance.add_argument("--artifacts-json", required=True)
    provenance.add_argument("--repository", required=True)
    provenance.add_argument("--default-branch", required=True)
    provenance.add_argument("--run-id", required=True)
    provenance.add_argument("--artifact-name", required=True)
    provenance.add_argument("--allowed-workflows", default="")
    provenance.set_defaults(func=cmd_actions_provenance)

"""Offline publication rendering and packaging for distilling-videos (schema_version 1).

Registers `render`, `pdf`, and `package` into distill.py. Reads verified evidence from the
workspace and an Amp-authored publications/<id>/article.json; see ../reference/article-contract.md.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlsplit

import evidence
from evidence import ContractError, Workspace, check_id, safe_path

RENDERER = 1
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ALPINE = "vendor/alpine-3.17.4.min.js"
ASSET_FILES = ("article.css", "article.js", ALPINE, "vendor/LICENSE-alpinejs.md", "vendor/PROVENANCE.md")
CSP = ("default-src 'none'; script-src 'self' 'unsafe-eval'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
PACKAGE_EXTENSIONS = IMAGE_EXTENSIONS | {".html", ".md", ".json", ".css", ".js", ".pdf"}
TEXT_EXTENSIONS = {".html", ".md", ".json", ".css", ".js", ".svg"}
SECRET = re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{10,}|AccountKey=|SharedAccessSignature=|"
                    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}|\bAKIA[0-9A-Z]{16}\b|"
                    r"\bsk-[A-Za-z0-9_-]{24,}|\bxox[abprs]-[A-Za-z0-9-]{10,}")
UNSAFE_SVG = re.compile(r"<script|<foreignObject|javascript:|\son[a-z]+\s*=|(?:href|src)\s*=\s*[\"']?(?:https?:)?//",
                        re.IGNORECASE)
REMOTE_RESOURCE = re.compile(r"<(?:script|link|img|source|iframe|video|audio|object|embed)\b[^>]*"
                             r"(?:src|href|data)=\"(?:https?:)?//", re.IGNORECASE)
INLINE = re.compile(r"\[@([^\]]*)\]|\*\*(.+?)\*\*|\*(.+?)\*|`([^`\n]+)`")
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "microsoft-edge",
            "msedge", "brave-browser")
MAC_BROWSERS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary")
EVIDENCE_KINDS = {"finding": "Findings", "requirement": "Requirements", "unknown": "Open unknowns"}
BASIS_LABELS = {"presenter": "Presenter claim", "screen": "Screen observation", "external": "External source"}
PROPOSAL_KINDS = {"architecture", "implementation", "investigation"}
ENGLISH_NOTES = {"translation": "The English text is a translation of the original.",
                 "clean English": "The English text is a cleaned version of the original English."}
E = html.escape


# ---------------------------------------------------------------------------
# Evidence and article validation


def _fields(obj: Any, label: str, required: Tuple[str, ...], optional: Tuple[str, ...] = ()) -> List[str]:
    if not isinstance(obj, dict):
        return [f"{label} must be an object"]
    problems = [f"{label} is missing {key}" for key in required if key not in obj]
    unknown = set(obj) - set(required) - set(optional)
    if unknown:
        problems.append(f"{label} has unknown field(s) {sorted(unknown)}")
    return problems


def _texts(obj: Dict[str, Any], keys: Tuple[str, ...], label: str) -> List[str]:
    return [f"{label}.{key} must be non-empty text" for key in keys
            if key in obj and (not isinstance(obj[key], str) or not obj[key].strip())]


def _strings(obj: Any, key: str, label: str) -> List[str]:
    """An optional list field, when present, must be a list of non-empty strings."""
    if not isinstance(obj, dict) or key not in obj:
        return []
    value = obj[key]
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        return [f"{label}.{key} must be a list of non-empty strings"]
    return []


def _list(obj: Dict[str, Any], key: str) -> List[Any]:
    value = obj.get(key)
    return value if isinstance(value, list) else []


def tokens(text: str) -> Iterator[Tuple[str, Any]]:
    """Split article text into text, cite, strong, em, and code tokens. Nothing else is markup."""
    position = 0
    for match in INLINE.finditer(text):
        if match.start() > position:
            yield "text", text[position:match.start()]
        if match.group(1) is not None:
            yield "cite", [p.strip().lstrip("@") for p in re.split(r"[;,]", match.group(1)) if p.strip()]
        elif match.group(2) is not None:
            yield "strong", match.group(2)
        elif match.group(3) is not None:
            yield "em", match.group(3)
        else:
            yield "code", match.group(4)
        position = match.end()
    if position < len(text):
        yield "text", text[position:]


def text_cites(text: Any) -> List[str]:
    return [c for kind, value in tokens(text) if kind == "cite" for c in value] if isinstance(text, str) else []


def _stage_ok(workspace: Workspace, video_id: str, stage: str) -> List[str]:
    key = evidence.stage_key(video_id, stage)
    record = workspace.state()["stages"].get(key)
    if not record or record.get("status") != "complete":
        status = record.get("status") if record else "missing"
        return [f"{key} is {status}; publications need verified evidence for every source"]
    return evidence.stage_problems(workspace, key, record)


def load_sources(workspace: Workspace, plan: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, str]]:
    """Return per-video evidence, problems, and workspace-relative input digests."""
    sources, problems, inputs = [], [], {}
    for index, video_id in enumerate(plan["video_ids"]):
        base = workspace.source_dir(video_id)
        stage_problems = _stage_ok(workspace, video_id, "transcript") + _stage_ok(workspace, video_id,
                                                                                  "transcript-markdown")
        frames_record = workspace.state()["stages"].get(evidence.stage_key(video_id, "frames"))
        has_frames = bool(frames_record and frames_record.get("status") == "complete")
        if has_frames:
            stage_problems += _stage_ok(workspace, video_id, "frames")
        problems += stage_problems
        if stage_problems:
            continue
        files = ["transcript/segments.json", "transcript/coverage.json", "transcript/original.md",
                 "transcript/english.md", "transcript/input.json"]
        files += [f for f in ("source.json", "frames/frames.json", "selection.json")
                  if (base / f).is_file() and (has_frames or not f.startswith(("frames", "selection")))]
        inputs.update({f"sources/{video_id}/{rel}": digest for rel, digest in evidence.file_digests(base, files).items()})
        segments = evidence.read_json(base / "transcript" / "segments.json")
        source = evidence.read_json(base / "source.json") if "source.json" in files else {}
        frames = evidence.read_json(base / "frames" / "frames.json") if "frames/frames.json" in files else None
        video = workspace.video(video_id)
        coverage = evidence.read_json(base / "transcript" / "coverage.json")
        sources.append({
            "id": video_id, "reel": chr(ord("A") + index), "youtube_id": video["youtube_id"],
            "title": str(source.get("title") or video.get("title") or video_id),
            "creator": str(source.get("creator") or "unknown creator"),
            "duration": source.get("duration") or segments.get("duration") or coverage.get("duration"),
            "language": segments["language"], "english_label": segments["english_label"],
            "provider_kind": segments["provider"]["kind"], "coverage": coverage,
            "segments": {s["id"]: s for s in segments["segments"]},
            "frames": {f["id"]: f for f in frames["frames"]} if frames else None,
            "max_sampling_gap": frames.get("max_sampling_gap_seconds") if frames else None,
            "selected": (evidence.read_json(base / "selection.json")["frame_ids"]
                         if "selection.json" in files else []),
        })
    return sources, problems, inputs


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def check_article(data: Any, plan: Dict[str, Any], sources: List[Dict[str, Any]], pub_dir: Path,
                  inputs: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """Validate structure and every reference. Adds referenced figure files to inputs."""
    top = ("schema_version", "publication_id", "title", "dek", "status", "sections", "figures", "citations",
           "brief", "limitations")
    problems = _fields(data, "article", top, ("partial_reason", "audience"))
    if not isinstance(data, dict):
        return problems, []
    warnings: List[str] = []
    problems += _texts(data, ("title", "dek", "partial_reason", "audience"), "article")
    if data.get("schema_version") != evidence.SCHEMA_VERSION:
        problems.append("article schema_version must be 1")
    if data.get("publication_id") != plan["id"]:
        problems.append(f"article publication_id must be {plan['id']!r}")
    if data.get("status") not in ("complete", "partial"):
        problems.append("article status must be complete or partial")
    if data.get("status") == "partial" and not str(data.get("partial_reason") or "").strip():
        problems.append("a partial article needs partial_reason naming the unresolved evidence")
    by_video = {s["id"]: s for s in sources}

    citations: Dict[str, Dict[str, Any]] = {}
    for index, citation in enumerate(_list(data, "citations")):
        label = f"citations[{index}]"
        kind = citation.get("kind", "video") if isinstance(citation, dict) else None
        if kind == "web":
            problems += _fields(citation, label, ("id", "kind", "url", "title"), ("publisher", "accessed", "note"))
            problems += _texts(citation, ("title", "publisher", "accessed", "note"), label)
            url = urlsplit(str(citation.get("url", "")))
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                problems.append(f"{label} url must be an http(s) URL without credentials")
        elif kind == "video":
            problems += _fields(citation, label, ("id", "video_id"), ("kind", "segment_ids", "frame_id", "note"))
            shape = _strings(citation, "segment_ids", label) + _texts(citation, ("frame_id", "note"), label)
            problems += shape
            video_id = citation.get("video_id")
            if not isinstance(video_id, str):
                problems.append(f"{label}.video_id must be a string")
            elif shape:
                pass  # references are checked once the field types are right
            elif video_id not in plan["video_ids"]:
                problems.append(f"{label} cites video {video_id!r}, which is not in publication {plan['id']} "
                                f"{plan['video_ids']}")
            elif video_id in by_video:
                source = by_video[video_id]
                segment_ids = _list(citation, "segment_ids")
                for segment_id in segment_ids:
                    if segment_id not in source["segments"]:
                        problems.append(f"{label} references missing segment {video_id}/{segment_id}")
                frame_id = citation.get("frame_id")
                if frame_id is not None and frame_id not in (source["frames"] or {}):
                    problems.append(f"{label} references missing frame {video_id}/{frame_id}")
                if not segment_ids and frame_id is None:
                    problems.append(f"{label} needs segment_ids or frame_id")
        else:
            problems.append(f"{label} kind must be video or web")
            continue
        if isinstance(citation.get("id"), str) and citation["id"] in citations:
            problems.append(f"duplicate citation id {citation['id']!r}")
        try:
            citations[check_id(citation.get("id"), f"{label}.id")] = citation
        except ContractError as error:
            problems += error.problems
    used: List[str] = []

    def cite(ids: List[str], where: str) -> None:
        for cid in ids:
            if not isinstance(cid, str):
                problems.append(f"{where} citation ids must be strings, not {type(cid).__name__}")
            elif cid not in citations:
                problems.append(f"{where} references unknown citation {cid!r}")
            elif cid not in used:
                used.append(cid)

    figures: Dict[str, Dict[str, Any]] = {}
    for index, figure in enumerate(_list(data, "figures")):
        label = f"figures[{index}]"
        kind = figure.get("kind") if isinstance(figure, dict) else None
        if kind == "capture":
            problems += _fields(figure, label, ("id", "kind", "video_id", "frame_id", "alt", "caption"))
            frames = [(figure.get("video_id"), figure.get("frame_id"))]
        elif kind == "sequence":
            problems += _fields(figure, label, ("id", "kind", "video_id", "caption", "steps"))
            steps = _list(figure, "steps")
            if len(steps) < 2:
                problems.append(f"{label} sequence needs at least two steps")
            frames = []
            for step_index, step in enumerate(steps):
                problems += _fields(step, f"{label}.steps[{step_index}]", ("frame_id", "alt", "caption"))
                if isinstance(step, dict):
                    problems += _texts(step, ("alt", "caption"), f"{label}.steps[{step_index}]")
                    frames.append((figure.get("video_id"), step.get("frame_id")))
        elif kind == "original":
            problems += _fields(figure, label, ("id", "kind", "image", "alt", "caption", "assumptions", "sources"),
                                ("derived_from",))
            frames = []
            derived = figure.get("derived_from")
            if derived is not None:
                problems += _fields(derived, f"{label}.derived_from", ("video_id", "frame_id"))
                if isinstance(derived, dict):
                    frames.append((derived.get("video_id"), derived.get("frame_id")))
            image = figure.get("image")
            if not isinstance(image, str) or not image.startswith("figures/"):
                problems.append(f"{label}.image must be a path under the publication's figures/ directory")
            else:
                try:
                    path = safe_path(pub_dir, image)
                    if path.suffix.lower() not in IMAGE_EXTENSIONS:
                        problems.append(f"{label}.image must be one of {sorted(IMAGE_EXTENSIONS)}")
                    elif not path.is_file():
                        problems.append(f"{label}.image target is missing: {image}")
                    else:
                        if path.suffix.lower() == ".svg" and UNSAFE_SVG.search(path.read_text(errors="replace")):
                            problems.append(f"{label}.image SVG contains scripts, handlers, or remote references")
                        inputs[f"publications/{plan['id']}/{image}"] = evidence.sha256_file(path)
                except ContractError as error:
                    problems += error.problems
            assumptions = _list(figure, "assumptions")
            if not assumptions or not all(isinstance(a, str) and a.strip() for a in assumptions):
                problems.append(f"{label} original figures must state their assumptions")
            if not _list(figure, "sources"):
                problems.append(f"{label} original figures must cite their sources")
            problems += _strings(figure, "sources", label)
            cite(_list(figure, "sources"), label)
        else:
            problems.append(f"{label} kind must be capture, sequence, or original")
            continue
        if isinstance(figure, dict):
            problems += _texts(figure, ("alt", "caption"), label)
        for video_id, frame_id in frames:
            if not isinstance(video_id, str) or not isinstance(frame_id, str):
                problems.append(f"{label} video_id and frame_id must be strings")
            elif video_id not in plan["video_ids"]:
                problems.append(f"{label} uses video {video_id!r}, which is not in publication {plan['id']}")
            elif video_id in by_video and frame_id not in (by_video[video_id]["frames"] or {}):
                problems.append(f"{label} references missing frame {video_id}/{frame_id}")
        try:
            figures[check_id(figure.get("id"), f"{label}.id")] = figure
        except ContractError as error:
            problems += error.problems

    placed: List[str] = []

    def blocks(items: Any, label: str, nested: bool = False) -> None:
        if not isinstance(items, list) or not items:
            problems.append(f"{label} must be a non-empty list")
            return
        for index, block in enumerate(items):
            where = f"{label}[{index}]"
            kind = block.get("type") if isinstance(block, dict) else None
            allowed = ("p", "list") if nested else ("p", "list", "quote", "figure", "details")
            if kind not in allowed:
                problems.append(f"{where} type must be one of {list(allowed)}")
                continue
            if kind == "p":
                problems.extend(_fields(block, where, ("type", "text")) + _texts(block, ("text",), where))
                cite(text_cites(block.get("text")), where)
            elif kind == "list":
                problems.extend(_fields(block, where, ("type", "items"), ("ordered",)))
                if "ordered" in block and not isinstance(block["ordered"], bool):
                    problems.append(f"{where}.ordered must be true or false")
                if not _list(block, "items") or not all(isinstance(i, str) and i.strip() for i in block["items"]):
                    problems.append(f"{where} items must be non-empty text")
                for item in _list(block, "items"):
                    cite(text_cites(item), where)
            elif kind == "quote":
                problems.extend(_fields(block, where, ("type", "text", "cite")) + _texts(block, ("text", "cite"), where))
                citation = citations.get(block["cite"]) if isinstance(block.get("cite"), str) else None
                if isinstance(block.get("cite"), str):
                    cite([block["cite"]], where)
                if (citation and citation.get("kind", "video") == "video" and isinstance(citation.get("video_id"), str)
                        and citation["video_id"] in by_video):
                    segments = by_video[citation["video_id"]]["segments"]
                    spoken = [segments[s] for s in _list(citation, "segment_ids") if isinstance(s, str) and s in segments]
                    haystacks = [_normalize(" ".join(s[f] for s in spoken)) for f in ("text", "english")]
                    if not any(_normalize(str(block.get("text"))) in h for h in haystacks):
                        problems.append(f"{where} quote does not appear verbatim in cited segments; quotations "
                                        "must not be invented or paraphrased")
                elif citation:
                    problems.append(f"{where} quote must cite video segments")
            elif kind == "figure":
                problems.extend(_fields(block, where, ("type", "figure")))
                if not isinstance(block.get("figure"), str):
                    problems.append(f"{where}.figure must be a figure id string")
                elif block["figure"] not in figures:
                    problems.append(f"{where} references unknown figure {block['figure']!r}")
                else:
                    placed.append(block["figure"])
            else:
                problems.extend(_fields(block, where, ("type", "summary", "blocks")) + _texts(block, ("summary",), where))
                blocks(block.get("blocks"), f"{where}.blocks", nested=True)

    if not _list(data, "sections"):
        problems.append("article.sections must be a non-empty list")
    section_ids = set()
    for index, section in enumerate(_list(data, "sections")):
        label = f"sections[{index}]"
        problems += _fields(section, label, ("id", "heading", "blocks"))
        if not isinstance(section, dict):
            continue
        problems += _texts(section, ("heading",), label)
        try:
            if check_id(section.get("id"), f"{label}.id") in section_ids:
                problems.append(f"duplicate section id {section['id']!r}")
            section_ids.add(section["id"])
        except ContractError as error:
            problems += error.problems
        blocks(section.get("blocks"), f"{label}.blocks")
    if not isinstance(data.get("limitations"), list) or not all(
            isinstance(x, str) and x.strip() for x in data.get("limitations", [])):
        problems.append("article.limitations must be a list of text (empty only if there truly are none)")

    brief = data.get("brief")
    problems += _fields(brief, "brief", ("evidence", "proposals"), ("question",))
    if isinstance(brief, dict):
        problems += _texts(brief, ("question",), "brief")
    evidence_ids: List[str] = []
    if isinstance(brief, dict):
        for index, item in enumerate(_list(brief, "evidence")):
            label = f"brief.evidence[{index}]"
            problems += _fields(item, label, ("id", "kind", "basis", "text"), ("citations",))
            if not isinstance(item, dict):
                continue
            problems += _texts(item, ("text",), label) + _strings(item, "citations", label)
            if not isinstance(item.get("kind"), str) or item["kind"] not in EVIDENCE_KINDS:
                problems.append(f"{label} kind must be one of {sorted(EVIDENCE_KINDS)}")
            if "basis" in item and (not isinstance(item["basis"], str) or item["basis"] not in BASIS_LABELS):
                problems.append(f"{label} basis must be one of {sorted(BASIS_LABELS)}")
            if item.get("kind") != "unknown" and not _list(item, "citations"):
                problems.append(f"{label} ({item.get('id')}) needs citations; uncited observations are unknowns")
            cite(_list(item, "citations") + text_cites(item.get("text")), label)
            evidence_ids.append(item.get("id"))
        for index, item in enumerate(_list(brief, "proposals")):
            label = f"brief.proposals[{index}]"
            problems += _fields(item, label, ("id", "kind", "text", "basis"), ("risks",))
            if not isinstance(item, dict):
                continue
            problems += _texts(item, ("text", "risks"), label) + _strings(item, "basis", label)
            if not isinstance(item.get("kind"), str) or item["kind"] not in PROPOSAL_KINDS:
                problems.append(f"{label} kind must be one of {sorted(PROPOSAL_KINDS)}")
            if "[@" in str(item.get("text", "")) + str(item.get("risks", "")):
                problems.append(f"{label} must not cite sources directly; proposals rest on evidence ids in basis")
            if not _list(item, "basis"):
                problems.append(f"{label} basis must list the evidence ids it rests on")
            for ref in _list(item, "basis"):
                if ref not in evidence_ids:
                    problems.append(f"{label} basis references unknown evidence {ref!r}")
        for item in _list(brief, "evidence") + _list(brief, "proposals"):
            if isinstance(item, dict):
                try:
                    check_id(item.get("id"), "brief item id")
                except ContractError as error:
                    problems += error.problems
        all_ids = [i.get("id") for i in _list(brief, "evidence") + _list(brief, "proposals")
                   if isinstance(i, dict) and isinstance(i.get("id"), str)]
        if len(all_ids) != len(set(all_ids)):
            problems.append("brief evidence and proposal ids must be unique")

    cited_videos = {citations[c].get("video_id") for c in used
                    if citations[c].get("kind", "video") == "video" and isinstance(citations[c].get("video_id"), str)}
    for video_id in plan["video_ids"]:
        if video_id not in cited_videos:
            problems.append(f"source {video_id} is never cited; a publication must not silently exclude a source")
    warnings += [f"citation {c} is defined but never used" for c in citations if c not in used]
    warnings += [f"figure {f} is defined but never placed" for f in figures if f not in placed]
    return problems, warnings


# ---------------------------------------------------------------------------
# Rendering


class Context:
    def __init__(self, article: Dict[str, Any], sources: List[Dict[str, Any]]):
        self.article = article
        self.sources = {s["id"]: s for s in sources}
        self.citations = {c["id"]: self._resolve(c) for c in article["citations"]}
        self.figures = {f["id"]: f for f in article["figures"]}
        self.order: List[str] = []
        self.figure_numbers: Dict[str, int] = {}

    def _resolve(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        if citation.get("kind") == "web":
            label = f"“{citation['title']}”" + (f" — {citation['publisher']}" if citation.get("publisher") else "")
            if citation.get("accessed"):
                label += f" (accessed {citation['accessed']})"
            return {**citation, "label": label, "chip": f"ext · {citation.get('publisher') or 'web'}"}
        source = self.sources[citation["video_id"]]
        segments = [source["segments"][s] for s in citation.get("segment_ids", [])]
        times = [s["start"] for s in segments] + [s["end"] for s in segments]
        if citation.get("frame_id"):
            times.append(source["frames"][citation["frame_id"]]["t"])
        start, end = min(times), max(times)
        span = evidence.timestamp(start) + (f"–{evidence.timestamp(end)}" if int(end) > int(start) else "")
        detail = ", ".join(([f"segments {', '.join(citation['segment_ids'])}"] if segments else [])
                           + ([f"frame {citation['frame_id']}"] if citation.get("frame_id") else []))
        label = f"Reel {source['reel']} — {source['creator']}, “{source['title']}”, {span} ({detail})"
        return {**citation, "kind": "video", "label": label, "start": start, "reel": source["reel"],
                "url": evidence.timestamp_url(source["youtube_id"], start),
                "chip": f"{source['reel']} {evidence.timestamp(start)}"}

    def number(self, cid: str) -> int:
        if cid not in self.order:
            self.order.append(cid)
        return self.order.index(cid) + 1

    def reset(self) -> None:
        self.order = []


def cite_marker(ids: List[str]) -> str:
    """One combined marker for several citation ids, so adjacent numbers never run together (¹⁴)."""
    return "[@" + "; @".join(ids) + "]" if ids else ""


def inline_html(text: str, ctx: Context, cited: List[str]) -> str:
    out = []
    for kind, value in tokens(text):
        if kind == "text":
            out.append(E(value))
        elif kind == "cite":
            if out:
                out[-1] = out[-1].rstrip()
            cited += [c for c in value if c not in cited]
            links = ", ".join(f'<a href="#ref-{ctx.number(c)}">{ctx.number(c)}</a>' for c in value)
            out.append(f'<sup class="cite">{links}</sup>')
        else:
            tag = {"strong": "strong", "em": "em", "code": "code"}[kind]
            out.append(f"<{tag}>{E(value)}</{tag}>")
    return "".join(out)


def inline_md(text: str, ctx: Context) -> str:
    out = []
    for kind, value in tokens(text):
        if kind == "text":
            out.append(evidence.escape_markdown(value))
        elif kind == "cite":
            if out:
                out[-1] = out[-1].rstrip()
            out.append("".join(f"[^{ctx.number(c)}]" for c in value))
        elif kind == "code":
            out.append("`" + value + "`")
        else:
            marker = "**" if kind == "strong" else "*"
            out.append(marker + evidence.escape_markdown(value) + marker)
    return "".join(out)


def rail(cited: List[str], ctx: Context, extra: str = "") -> str:
    chips = []
    for cid in cited:
        citation = ctx.citations[cid]
        href = citation["url"] if citation["kind"] == "video" else f"#ref-{ctx.number(cid)}"
        external = ' rel="noopener noreferrer"' if citation["kind"] == "video" else ""
        chips.append(f'<a class="tc tc-{citation["kind"]}" href="{E(href)}"{external}>'
                     f'<span class="tc-n">{ctx.number(cid)}</span> {E(citation["chip"])}</a>')
    label = '<span class="visually-hidden">Source moments: </span>' if chips else ""
    return f'<div class="rail">{extra}{label}{"".join(chips)}</div>'


def row(body: str, cited: List[str], ctx: Context, cls: str = "", extra: str = "") -> str:
    return f'<div class="row {cls}">{rail(cited, ctx, extra)}<div class="col">{body}</div></div>'


def frame_media(video_id: str, frame_id: str) -> Tuple[str, str]:
    return f"media/{video_id}/{frame_id}.jpg", f"media/{video_id}/thumbs/{frame_id}.jpg"


def figure_html(figure: Dict[str, Any], ctx: Context) -> str:
    number = ctx.figure_numbers.setdefault(figure["id"], len(ctx.figure_numbers) + 1)
    caption = inline_html(figure["caption"], ctx, [])
    kind = figure["kind"]
    if kind == "sequence":
        source = ctx.sources[figure["video_id"]]
        steps, strip = [], []
        for index, step in enumerate(figure["steps"]):
            full, thumb = frame_media(figure["video_id"], step["frame_id"])
            t = source["frames"][step["frame_id"]]["t"]
            link = evidence.timestamp_url(source["youtube_id"], t)
            steps.append(
                f'<li class="step" x-show="i === {index}"><img src="{full}" alt="{E(step["alt"])}" loading="lazy">'
                f'<p class="step-caption"><span class="slug">Step {index + 1} of {len(figure["steps"])} · '
                f'<a href="{E(link)}" rel="noopener noreferrer">Reel {source["reel"]} {evidence.timestamp(t)}</a>'
                f'</span> {inline_html(step["caption"], ctx, [])}</p></li>')
            strip.append(f'<button type="button" class="thumb" @click="go({index})" '
                         f':aria-current="i === {index} ? \'step\' : false" aria-label="Show step {index + 1}">'
                         f'<img src="{thumb}" alt=""></button>')
        controls = (f'<div class="controls"><button type="button" class="step-button" @click="prev()" '
                    f':disabled="i === 0">Previous</button><div class="strip">{"".join(strip)}</div>'
                    f'<button type="button" class="step-button" @click="next()" :disabled="i === n - 1">Next</button>'
                    f'<output class="counter" aria-live="polite" x-text="(i + 1) + \' / \' + n"></output></div>')
        return (f'<figure class="fig fig-sequence" id="{E(figure["id"])}" x-data="stepper({len(steps)})" '
                f'@keydown.arrow-left="prev()" @keydown.arrow-right="next()">'
                f'<ol class="steps">{"".join(steps)}</ol>{controls}'
                f'<figcaption><span class="slug">Fig. {number} · Demo sequence from Reel {source["reel"]}</span> '
                f'{caption}</figcaption></figure>')
    if kind == "capture":
        source = ctx.sources[figure["video_id"]]
        t = source["frames"][figure["frame_id"]]["t"]
        src, _ = frame_media(figure["video_id"], figure["frame_id"])
        link = evidence.timestamp_url(source["youtube_id"], t)
        slug = (f'Fig. {number} · Source capture · <a href="{E(link)}" rel="noopener noreferrer">Reel '
                f'{source["reel"]} {evidence.timestamp(t)}</a> · {E(figure["frame_id"])}')
        notes = ""
    else:
        src = figure["image"]
        cited: List[str] = []
        refs = inline_html(cite_marker(figure["sources"]), ctx, cited)
        derived = ""
        if figure.get("derived_from"):
            d = figure["derived_from"]
            t = ctx.sources[d["video_id"]]["frames"][d["frame_id"]]["t"]
            derived = (f' · annotated from Reel {ctx.sources[d["video_id"]]["reel"]} {evidence.timestamp(t)}; '
                       "the untouched capture is kept in the evidence archive")
        slug = f"Fig. {number} · Original figure — our reconstruction, not a source capture{E(derived)}"
        assumptions = "".join(f"<li>{inline_html(a, ctx, [])}</li>" for a in figure["assumptions"])
        notes = f'<div class="assumptions"><p>Assumptions{refs}</p><ul>{assumptions}</ul></div>'
    return (f'<figure class="fig fig-{kind}" id="{E(figure["id"])}" x-data="zoom">'
            f'<a class="frame" href="{src}" @click.prevent="open()" aria-label="Enlarge figure {number}">'
            f'<img src="{src}" alt="{E(figure["alt"])}" loading="lazy"></a>'
            f'<figcaption><span class="slug">{slug}</span> {caption}{notes}</figcaption>'
            f'<dialog class="lightbox" x-ref="dialog" @click.self="close()" aria-label="Figure {number}">'
            f'<img src="{src}" alt="{E(figure["alt"])}"><p>{caption}</p>'
            f'<button type="button" class="close" @click="close()">Close</button></dialog></figure>')


def blocks_html(blocks: List[Dict[str, Any]], ctx: Context) -> str:
    out = []
    for block in blocks:
        cited: List[str] = []
        if block["type"] == "p":
            out.append(row(f"<p>{inline_html(block['text'], ctx, cited)}</p>", cited, ctx))
        elif block["type"] == "list":
            tag = "ol" if block.get("ordered") else "ul"
            items = "".join(f"<li>{inline_html(i, ctx, cited)}</li>" for i in block["items"])
            out.append(row(f"<{tag}>{items}</{tag}>", cited, ctx))
        elif block["type"] == "quote":
            cited.append(block["cite"])
            n = ctx.number(block["cite"])
            body = (f'<blockquote class="pull"><p>{E(block["text"])}</p><footer><a href="#ref-{n}">'
                    f'Reel {ctx.citations[block["cite"]]["reel"]}, {E(ctx.citations[block["cite"]]["chip"][2:])}'
                    f'</a></footer></blockquote>')
            out.append(row(body, cited, ctx, "row-quote"))
        elif block["type"] == "figure":
            figure = ctx.figures[block["figure"]]
            out.append(row(figure_html(figure, ctx), [], ctx, "row-wide"))
        else:
            inner = blocks_html(block["blocks"], ctx)
            out.append(f'<details class="deeper"><summary><span class="slug">Go deeper</span>'
                       f'{inline_html(block["summary"], ctx, [])}</summary>{inner}</details>')
    return "".join(out)


def tape(source: Dict[str, Any], moments: List[float]) -> str:
    duration = source["duration"] or max([s["end"] for s in source["segments"].values()] + moments)
    scale = 1000 / duration if duration else 0
    gaps = source["coverage"]["gaps"]
    parts = ['<rect class="tape-base" x="0" y="8" width="1000" height="8"/>']
    parts += [f'<rect class="tape-gap" x="{g["start"] * scale:.1f}" y="4" width="{max((g["end"] - g["start"]) * scale, 2):.1f}" '
              f'height="16" fill="url(#hatch)"/>' for g in gaps]
    parts += [f'<rect class="tape-tick" x="{min(t * scale, 998):.1f}" y="0" width="2.5" height="24"/>' for t in moments]
    label = (f"Tape map for Reel {source['reel']}: {len(moments)} cited moment{'s' if len(moments) != 1 else ''}"
             f"{f', {len(gaps)} transcript gap' + ('s' if len(gaps) != 1 else '') if gaps else ''} "
             f"across {evidence.timestamp(duration or 0)}")
    return (f'<svg class="tape" viewBox="0 0 1000 24" preserveAspectRatio="none" role="img" aria-label="{E(label)}">'
            f'{"".join(parts)}</svg><p class="tape-legend">{E(label)}</p>')


def page(title: str, body: str, kind: str) -> str:
    return (f'<!doctype html>\n<html lang="en" class="no-js"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
            f'<meta name="referrer" content="no-referrer"><title>{E(title)}</title>'
            f'<link rel="stylesheet" href="assets/article.css">'
            f'<script defer src="assets/article.js"></script><script defer src="assets/{ALPINE}"></script>'
            f'</head><body class="page-{kind}"><a class="skip" href="#main">Skip to content</a>'
            '<svg class="defs" aria-hidden="true" focusable="false"><defs><pattern id="hatch" width="6" height="6" '
            'patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="hatch-line" width="2" '
            f'height="6"/></pattern></defs></svg>{body}</body></html>\n')


def references_html(ctx: Context) -> str:
    items = []
    for n, cid in enumerate(ctx.order, 1):
        citation = ctx.citations[cid]
        url = citation["url"]
        items.append(f'<li id="ref-{n}">{E(citation["label"])}. <a class="url" href="{E(url)}" '
                     f'rel="noopener noreferrer">{E(url)}</a></li>')
    return f'<section class="references" id="references" aria-labelledby="h-references">' \
           f'<h2 id="h-references">References</h2><ol>{"".join(items)}</ol></section>'


def method_html(ctx: Context) -> str:
    rows = []
    for source in ctx.sources.values():
        coverage = source["coverage"]
        duration = coverage.get("duration")
        share = f" ({coverage['covered_seconds'] / duration:.0%} of {evidence.timestamp(duration)})" if duration else ""
        gaps = "; ".join(f"{evidence.timestamp(g['start'])}–{evidence.timestamp(g['end'])}" for g in coverage["gaps"])
        frames = (f"Frames sampled with gaps of at most {source['max_sampling_gap']} s; {len(source['selected'])} "
                  "selected by visual judgment, not exhaustive analysis." if source["frames"] else "No frames extracted.")
        rows.append(
            f'<div class="method-reel"><h3>Reel {source["reel"]}: {E(source["title"])}</h3><ul>'
            f'<li>Transcript ({E(source["language"])}, {E(source["provider_kind"])}): {coverage["segment_count"]} '
            f'segments, {coverage["covered_seconds"]:.0f} s covered{share}. {ENGLISH_NOTES[source["english_label"]]}</li>'
            f'<li>Transcript gaps: {E(gaps) if gaps else "none over the 2 s threshold"}.</li>'
            f'<li>Uncertain segments: {E(", ".join(coverage["uncertain_segment_ids"])) or "none marked"}.</li>'
            f'<li>{E(frames)}</li></ul></div>')
    limits = "".join(f"<li>{inline_html(x, ctx, [])}</li>" for x in ctx.article["limitations"])
    return (f'<section class="method" id="method" aria-labelledby="h-method"><h2 id="h-method">How this was made, '
            f'and its limits</h2>{"".join(rows)}<h3>Limitations</h3><ul>{limits or "<li>None recorded.</li>"}</ul>'
            '</section>')


def masthead(ctx: Context, eyebrow: str, title: str, dek: str) -> str:
    article = ctx.article
    moments: Dict[str, List[float]] = {}
    for cid in ctx.order:
        citation = ctx.citations[cid]
        if citation["kind"] == "video":
            moments.setdefault(citation["video_id"], []).append(citation["start"])
    reels = []
    for source in ctx.sources.values():
        link = evidence.timestamp_url(source["youtube_id"], 0)
        meta = " · ".join([source["creator"], evidence.timestamp(source["duration"] or 0), source["language"]])
        reels.append(f'<li class="reel"><p class="reel-id">Reel {source["reel"]}</p><p class="reel-title">'
                     f'<a href="{E(link)}" rel="noopener noreferrer">{E(source["title"])}</a></p>'
                     f'<p class="reel-meta">{E(meta)}</p>{tape(source, moments.get(source["id"], []))}</li>')
    partial = ""
    if article["status"] == "partial":
        partial = (f'<p class="status-partial"><strong>Partial publication.</strong> '
                   f'{E(article["partial_reason"])}</p>')
    return (f'<header class="masthead"><p class="eyebrow">{E(eyebrow)}</p><h1>{E(title)}</h1>'
            f'<p class="dek">{inline_html(dek, ctx, [])}</p>{partial}'
            f'<section class="slate" aria-label="Source videos"><ol class="reels">{"".join(reels)}</ol>'
            f'<p class="slate-note">Ticks mark cited moments; hatching marks transcript gaps.</p></section></header>')


def eyebrow(ctx: Context) -> str:
    count = len(ctx.sources)
    return f"Distilled from {count} video{'s' if count > 1 else ''}" + (" · synthesis" if count > 1 else "")


def render_article_html(ctx: Context) -> str:
    article = ctx.article
    ctx.reset()
    ctx.figure_numbers = {}
    sections = []
    for section in article["sections"]:
        sections.append(f'<section id="s-{section["id"]}" aria-labelledby="h-{section["id"]}">'
                        f'<h2 id="h-{section["id"]}">{inline_html(section["heading"], ctx, [])}</h2>'
                        f'{blocks_html(section["blocks"], ctx)}</section>')
    toc = ""
    if len(article["sections"]) >= 3:
        toc = '<nav class="toc" aria-label="Contents"><ol>' + "".join(
            f'<li><a href="#s-{s["id"]}">{E(s["heading"])}</a></li>' for s in article["sections"]) + "</ol></nav>"
    body = "".join(sections)
    tail = method_html(ctx) + references_html(ctx)
    head = masthead(ctx, eyebrow(ctx), article["title"], article["dek"])
    footer = ('<footer class="colophon"><p>Rendered offline from timestamped evidence. Also available: '
              '<a href="brief.html">research brief</a> · <a href="article.md">Markdown</a> · '
              '<a href="article.pdf">PDF</a> · <a href="coverage.json">coverage report</a>.</p></footer>')
    return page(article["title"], f'{head}<main id="main"><article>{toc}{body}{tail}</article></main>{footer}',
                "article")


def render_brief_html(ctx: Context) -> str:
    article, brief = ctx.article, ctx.article["brief"]
    ctx.reset()
    groups = []
    for kind, label in EVIDENCE_KINDS.items():
        items = [i for i in brief["evidence"] if i["kind"] == kind]
        if not items:
            continue
        lis = []
        for item in items:
            cited: List[str] = []
            text = inline_html(item["text"], ctx, cited)
            refs = inline_html(cite_marker(item.get("citations", [])), ctx, cited)
            lis.append(row(f'<p><span class="ev-id">{E(item["id"])}</span> <span class="basis basis-{item["basis"]}">'
                           f'{BASIS_LABELS[item["basis"]]}</span> {text}{refs}</p>', cited, ctx, "ledger-item"))
        groups.append(f'<h3>{label}</h3><div class="ledger" role="list">' +
                      "".join(f'<div role="listitem" id="{E(i["id"])}">{li}</div>' for i, li in zip(items, lis))
                      + "</div>")
    proposals = []
    for item in brief["proposals"]:
        basis = ", ".join(f'<a href="#{E(b)}">{E(b)}</a>' for b in item["basis"])
        risks = f'<p class="risks">Risks: {inline_html(item["risks"], ctx, [])}</p>' if item.get("risks") else ""
        proposals.append(f'<div class="proposal" role="listitem" id="{E(item["id"])}"><p class="slug">'
                         f'{E(item["id"])} · Proposal, not evidence · {E(item["kind"])}</p>'
                         f'<p>{inline_html(item["text"], ctx, [])}</p><p class="rests">Rests on: {basis}</p>{risks}</div>')
    question = f'<p class="question">Question: {inline_html(brief["question"], ctx, [])}</p>' \
        if brief.get("question") else ""
    body = (f'<section aria-labelledby="h-evidence"><h2 id="h-evidence">What the sources establish</h2>'
            f'{"".join(groups)}</section><section class="proposals" aria-labelledby="h-proposals">'
            f'<h2 id="h-proposals">What we propose</h2><p class="proposal-note">These are our conclusions and '
            f'next steps. They are not established by the sources; each names the evidence it rests on.</p>'
            f'<div role="list">{"".join(proposals) or "<p>No proposals.</p>"}</div></section>')
    head = masthead(ctx, eyebrow(ctx) + " · research brief", f"Brief: {article['title']}", article["dek"])
    footer = '<footer class="colophon"><p><a href="index.html">Read the article</a> · <a href="brief.md">Markdown</a></p></footer>'
    return page(f"Brief: {article['title']}",
                f'{head}<main id="main"><article>{question}{body}{method_html(ctx)}{references_html(ctx)}</article>'
                f'</main>{footer}', "brief")


def references_md(ctx: Context) -> List[str]:
    lines = ["## References", ""]
    for n, cid in enumerate(ctx.order, 1):
        citation = ctx.citations[cid]
        lines.append(f"[^{n}]: {evidence.escape_markdown(citation['label'])}. <{citation['url']}>")
    return lines


def sources_md(ctx: Context) -> List[str]:
    return [f"- Reel {s['reel']}: {evidence.escape_markdown(s['title'])} — {evidence.escape_markdown(s['creator'])} "
            f"<{evidence.timestamp_url(s['youtube_id'], 0)}>" for s in ctx.sources.values()]


def figure_md(figure: Dict[str, Any], ctx: Context) -> List[str]:
    number = ctx.figure_numbers.setdefault(figure["id"], len(ctx.figure_numbers) + 1)
    caption = inline_md(figure["caption"], ctx)
    esc = evidence.escape_markdown
    if figure["kind"] == "sequence":
        source = ctx.sources[figure["video_id"]]
        lines = [f"**Fig. {number}. Demo sequence from Reel {source['reel']}.** {caption}", ""]
        for index, step in enumerate(figure["steps"], 1):
            t = source["frames"][step["frame_id"]]["t"]
            lines += [f"![{esc(step['alt'])}]({frame_media(figure['video_id'], step['frame_id'])[0]})", "",
                      f"*Step {index} — Reel {source['reel']} {evidence.timestamp(t)}:* {inline_md(step['caption'], ctx)}",
                      ""]
        return lines
    if figure["kind"] == "capture":
        source = ctx.sources[figure["video_id"]]
        t = source["frames"][figure["frame_id"]]["t"]
        return [f"![{esc(figure['alt'])}]({frame_media(figure['video_id'], figure['frame_id'])[0]})", "",
                f"**Fig. {number}. Source capture, Reel {source['reel']} {evidence.timestamp(t)} "
                f"({figure['frame_id']}).** {caption}", ""]
    refs = "".join(f"[^{ctx.number(c)}]" for c in figure["sources"])
    return [f"![{esc(figure['alt'])}]({figure['image']})", "",
            f"**Fig. {number}. Original figure, not a source capture.** {caption}", "",
            f"Assumptions{refs}:", *[f"- {inline_md(a, ctx)}" for a in figure["assumptions"]], ""]


def blocks_md(blocks: List[Dict[str, Any]], ctx: Context) -> List[str]:
    lines: List[str] = []
    for block in blocks:
        if block["type"] == "p":
            lines += [inline_md(block["text"], ctx), ""]
        elif block["type"] == "list":
            lines += [f"{f'{i}.' if block.get('ordered') else '-'} {inline_md(item, ctx)}"
                      for i, item in enumerate(block["items"], 1)] + [""]
        elif block["type"] == "quote":
            lines += [f"> {evidence.escape_markdown(block['text'])}[^{ctx.number(block['cite'])}]", ""]
        elif block["type"] == "figure":
            lines += figure_md(ctx.figures[block["figure"]], ctx)
        else:
            lines += [f"### Go deeper: {inline_md(block['summary'], ctx)}", ""] + blocks_md(block["blocks"], ctx)
    return lines


def method_md(ctx: Context) -> List[str]:
    lines = ["## How this was made, and its limits", ""]
    for source in ctx.sources.values():
        coverage = source["coverage"]
        gaps = "; ".join(f"{evidence.timestamp(g['start'])}–{evidence.timestamp(g['end'])}" for g in coverage["gaps"])
        lines += [f"- Reel {source['reel']}: transcript ({source['language']}, {source['provider_kind']}) with "
                  f"{coverage['segment_count']} segments, {coverage['covered_seconds']:.0f} s covered; gaps: "
                  f"{gaps or 'none over 2 s'}; uncertain: {', '.join(coverage['uncertain_segment_ids']) or 'none'}; "
                  f"{ENGLISH_NOTES[source['english_label']]} {len(source['selected'])} frames selected (sampled, not "
                  "exhaustive)."]
    lines += ["", "Limitations:", ""] + [f"- {inline_md(x, ctx)}" for x in ctx.article["limitations"]] + [""]
    return lines


def render_article_md(ctx: Context) -> str:
    article = ctx.article
    ctx.reset()
    ctx.figure_numbers = {}
    lines = [f"# {evidence.escape_markdown(article['title'])}", "", f"*{inline_md(article['dek'], ctx)}*", ""]
    if article["status"] == "partial":
        lines += [f"> **Partial publication.** {evidence.escape_markdown(article['partial_reason'])}", ""]
    lines += ["Sources:", "", *sources_md(ctx), ""]
    for section in article["sections"]:
        lines += [f"## {inline_md(section['heading'], ctx)}", ""] + blocks_md(section["blocks"], ctx)
    return "\n".join(lines + method_md(ctx) + references_md(ctx)) + "\n"


def render_brief_md(ctx: Context) -> str:
    article, brief = ctx.article, ctx.article["brief"]
    ctx.reset()
    lines = [f"# Brief: {evidence.escape_markdown(article['title'])}", ""]
    if brief.get("question"):
        lines += [f"Question: {inline_md(brief['question'], ctx)}", ""]
    lines += ["Sources:", "", *sources_md(ctx), "", "## What the sources establish", ""]
    for kind, label in EVIDENCE_KINDS.items():
        items = [i for i in brief["evidence"] if i["kind"] == kind]
        if items:
            lines += [f"### {label}", ""]
            lines += [f"- **{item['id']}** ({BASIS_LABELS[item['basis']]}) {inline_md(item['text'], ctx)}"
                      + "".join(f"[^{ctx.number(c)}]" for c in item.get("citations", [])) for item in items] + [""]
    lines += ["## What we propose", "", "These are our conclusions and next steps, not findings from the sources.", ""]
    for item in brief["proposals"]:
        lines += [f"- **{item['id']}** (Proposal, not evidence; {item['kind']}) {inline_md(item['text'], ctx)}",
                  f"  Rests on: {', '.join(item['basis'])}"]
        if item.get("risks"):
            lines.append(f"  Risks: {inline_md(item['risks'], ctx)}")
    if not brief["proposals"]:
        lines.append("No proposals.")
    return "\n".join(lines + [""] + method_md(ctx) + references_md(ctx)) + "\n"


def coverage_report(ctx: Context, warnings: List[str]) -> Dict[str, Any]:
    ctx.reset()
    render_article_html(ctx)
    article_used = list(ctx.order)
    sources = []
    for source in ctx.sources.values():
        sources.append({
            "video_id": source["id"], "reel": source["reel"], "youtube_id": source["youtube_id"],
            "title": source["title"], "transcript": {k: source["coverage"][k] for k in (
                "segment_count", "duration", "covered_seconds", "gaps", "uncertain_segment_ids", "warnings")},
            "language": source["language"], "english_label": source["english_label"],
            "provider_kind": source["provider_kind"],
            "frames": {"extracted": len(source["frames"] or {}), "selected": len(source["selected"]),
                       "max_sampling_gap_seconds": source["max_sampling_gap"], "semantic_completeness": False},
            "citations": sum(1 for c in article_used if ctx.citations[c].get("video_id") == source["id"])})
    article = ctx.article
    return {"schema_version": evidence.SCHEMA_VERSION, "publication_id": article["publication_id"],
            "status": article["status"], "partial_reason": article.get("partial_reason"), "sources": sources,
            "citations": {"defined": len(ctx.citations), "used_in_article": len(article_used)},
            "figures": {k: sum(1 for f in article["figures"] if f["kind"] == k) for k in ("capture", "sequence",
                                                                                         "original")},
            "brief": {"evidence": len(article["brief"]["evidence"]), "proposals": len(article["brief"]["proposals"])},
            "limitations": article["limitations"], "warnings": warnings}


# ---------------------------------------------------------------------------
# Commands


def emit(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _publication(workspace: Workspace, publication_id: str) -> Tuple[Dict[str, Any], Path]:
    check_id(publication_id, "publication")
    plans = {p["id"]: p for p in workspace.assignment()["publications"]}
    if publication_id not in plans:
        raise ContractError(f"publication {publication_id!r} is not in the assignment ({sorted(plans)})")
    return plans[publication_id], workspace.path(f"publications/{publication_id}")


def _swap(partial: Path, final: Path) -> None:
    old = final.with_name(f".{final.name}-old-{os.getpid()}")
    if final.exists():
        os.replace(final, old)
    os.replace(partial, final)
    if old.exists():
        shutil.rmtree(old)


def _tree_digests(root: Path, skip: Tuple[str, ...] = ()) -> Dict[str, str]:
    return {p.relative_to(root).as_posix(): evidence.sha256_file(p) for p in sorted(root.rglob("*"))
            if p.is_file() and p.relative_to(root).as_posix() not in skip}


def cmd_render(args: Any) -> int:
    workspace = Workspace(Path(args.workspace))
    plan, pub_dir = _publication(workspace, args.publication)
    article_path = safe_path(pub_dir, "article.json")
    article = evidence.read_json(article_path)
    sources, problems, inputs = load_sources(workspace, plan)
    if problems:
        raise ContractError(problems)
    inputs[f"publications/{plan['id']}/article.json"] = evidence.sha256_file(article_path)
    problems, warnings = check_article(article, plan, sources, pub_dir, inputs)
    if problems:
        raise ContractError(problems)
    ctx = Context(article, sources)
    documents = {"index.html": render_article_html(ctx), "brief.html": render_brief_html(ctx),
                 "article.md": render_article_md(ctx), "brief.md": render_brief_md(ctx)}
    for name in ("index.html", "brief.html"):
        if REMOTE_RESOURCE.search(documents[name]):
            raise ContractError(f"{name} would load a remote resource; refusing to render")
    partial = pub_dir / f".dist-partial-{os.getpid()}"
    if partial.exists():
        shutil.rmtree(partial)
    try:
        for name, text in documents.items():
            evidence.atomic_write_text(partial / name, text)
        evidence.atomic_write_json(partial / "coverage.json", coverage_report(ctx, warnings))
        for name in ASSET_FILES:
            target = partial / "assets" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ASSETS / name, target)
        frames = {(f["video_id"], f["frame_id"]) for f in article["figures"] if f["kind"] == "capture"}
        frames |= {(f["video_id"], s["frame_id"]) for f in article["figures"] if f["kind"] == "sequence"
                   for s in f["steps"]}
        for video_id, frame_id in sorted(frames):
            frame = ctx.sources[video_id]["frames"][frame_id]
            base = workspace.source_dir(video_id)
            for rel, target in zip((frame["path"], frame["thumbnail"]), frame_media(video_id, frame_id)):
                path = safe_path(base, rel)
                inputs[f"sources/{video_id}/{rel}"] = evidence.sha256_file(path)
                (partial / target).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, partial / target)
        for figure in article["figures"]:
            if figure["kind"] == "original":
                (partial / figure["image"]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(safe_path(pub_dir, figure["image"]), partial / figure["image"])
        outputs = _tree_digests(partial)
        _swap(partial, pub_dir / "dist")
    finally:
        if partial.exists():
            shutil.rmtree(partial)
    evidence.atomic_write_json(pub_dir / "render.json", {
        "schema_version": evidence.SCHEMA_VERSION, "publication_id": plan["id"], "renderer": RENDERER,
        "rendered_at": evidence.now(), "inputs": inputs, "outputs": outputs, "warnings": warnings})
    with_pdf = pub_dir / "pdf.json"
    if with_pdf.exists():
        with_pdf.unlink()
    emit({"status": "rendered", "publication": plan["id"], "dist": str(pub_dir / "dist"),
          "files": sorted(outputs), "warnings": warnings})
    return 0


def _verify_render(workspace: Workspace, plan: Dict[str, Any], pub_dir: Path) -> Dict[str, Any]:
    record = evidence.read_json(pub_dir / "render.json") if (pub_dir / "render.json").exists() else None
    if not record or not (pub_dir / "dist").is_dir():
        raise ContractError(f"publication {plan['id']} has not been rendered; run render first")
    problems = []
    for rel, digest in record["inputs"].items():
        path = workspace.path(rel)
        if not path.is_file() or evidence.sha256_file(path) != digest:
            problems.append(f"render is stale: input {rel} changed (checksum mismatch); rerun render")
    actual = _tree_digests(pub_dir / "dist", skip=("article.pdf",))
    if actual != record["outputs"]:
        problems.append("render is stale: dist/ no longer matches render.json checksums; rerun render")
    if problems:
        raise ContractError(problems)
    return record


def find_browser(explicit: Optional[str]) -> Optional[str]:
    candidate = explicit or os.environ.get("DISTILL_BROWSER")
    if candidate:
        return candidate if os.path.isfile(candidate) and os.access(candidate, os.X_OK) else None
    for name in BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    return next((p for p in MAC_BROWSERS if os.access(p, os.X_OK)), None)


def cmd_pdf(args: Any) -> int:
    workspace = Workspace(Path(args.workspace))
    plan, pub_dir = _publication(workspace, args.publication)
    _verify_render(workspace, plan, pub_dir)
    browser = find_browser(args.browser)
    if not browser:
        print("error: no Chromium-compatible browser found for PDF rendering. Install Chromium or Google Chrome, "
              "or pass --browser PATH / set DISTILL_BROWSER. No PDF was written.", file=sys.stderr)
        return 3
    dist = pub_dir / "dist"
    index = dist / "index.html"
    target = dist / "article.pdf"
    partial = dist / f".article-{os.getpid()}.pdf"
    secret_env = re.compile(r"SAS|SECRET|TOKEN|PASSWORD|API_KEY|ACCESS_KEY|CONNECTION_STRING|AZURE_STORAGE", re.I)
    env = {k: v for k, v in os.environ.items() if not secret_env.search(k)}
    with tempfile.TemporaryDirectory(prefix="distill-browser-") as profile:
        command = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                   "--disable-extensions", "--disable-sync", "--disable-background-networking",
                   "--disable-component-update", "--proxy-server=127.0.0.1:9", "--proxy-bypass-list=<-loopback>",
                   f"--user-data-dir={profile}", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                   f"--virtual-time-budget={int(args.wait * 1000)}", f"--print-to-pdf={partial}",
                   index.as_uri() + "?print=1"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout, env=env)
        except subprocess.TimeoutExpired:
            result = None
    try:
        data = partial.read_bytes() if partial.is_file() else b""
        if result is None or result.returncode != 0 or not data:
            detail = "timed out" if result is None else evidence.redact((result.stderr or "").strip())[-800:]
            print(f"error: browser did not produce a PDF ({Path(browser).name}): {detail}", file=sys.stderr)
            return 5
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:] or len(data) < 1024:
            print("error: browser output is not a PDF; refusing to label it article.pdf", file=sys.stderr)
            return 5
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    record = {"schema_version": evidence.SCHEMA_VERSION, "index_sha256": evidence.sha256_file(index),
              "pdf_sha256": evidence.sha256_file(target), "browser": Path(browser).name,
              "pages": len(re.findall(rb"/Type\s*/Page\b", data)), "rendered_at": evidence.now()}
    evidence.atomic_write_json(pub_dir / "pdf.json", record)
    emit({"status": "rendered", "pdf": str(target), **record})
    return 0


def _package_sources(workspace: Workspace, plan: Dict[str, Any], article: Dict[str, Any]) -> List[Tuple[Path, str]]:
    figures = article["figures"]
    referenced = {(f["video_id"], f["frame_id"]) for f in figures if f["kind"] == "capture"}
    referenced |= {(f["video_id"], s["frame_id"]) for f in figures if f["kind"] == "sequence" for s in f["steps"]}
    referenced |= {(f["derived_from"]["video_id"], f["derived_from"]["frame_id"])
                   for f in figures if f.get("derived_from")}
    referenced |= {(c["video_id"], c["frame_id"]) for c in article["citations"] if c.get("frame_id")}
    files = []
    for video_id in plan["video_ids"]:
        base = workspace.source_dir(video_id)
        rels = ["source.json", "selection.json", "frames/frames.json", "transcript/input.json",
                "transcript/segments.json", "transcript/coverage.json", "transcript/original.md",
                "transcript/english.md"]
        if (base / "frames" / "frames.json").is_file():
            frames = {f["id"]: f for f in evidence.read_json(base / "frames" / "frames.json")["frames"]}
            selected = evidence.read_json(base / "selection.json")["frame_ids"] \
                if (base / "selection.json").is_file() else []
            wanted = set(selected) | {frame for video, frame in referenced if video == video_id}
            for frame_id in sorted(wanted & set(frames)):
                rels += [frames[frame_id]["path"], frames[frame_id]["thumbnail"]]
        files += [(safe_path(base, rel), f"sources/{video_id}/{rel}") for rel in rels if (base / rel).is_file()]
    return files


def cmd_package(args: Any) -> int:
    workspace = Workspace(Path(args.workspace))
    plan, pub_dir = _publication(workspace, args.publication)
    _verify_render(workspace, plan, pub_dir)
    dist = pub_dir / "dist"
    article = evidence.read_json(pub_dir / "article.json")
    reasons = []
    pdf_record = evidence.read_json(pub_dir / "pdf.json") if (pub_dir / "pdf.json").exists() else None
    pdf_ok = bool(pdf_record and (dist / "article.pdf").is_file()
                  and pdf_record["index_sha256"] == evidence.sha256_file(dist / "index.html")
                  and pdf_record["pdf_sha256"] == evidence.sha256_file(dist / "article.pdf"))
    if not pdf_ok:
        if not args.allow_missing_pdf:
            raise ContractError("PDF is missing or stale for the current render; run pdf, or pass "
                                "--allow-missing-pdf to build an explicitly incomplete package")
        reasons.append("PDF missing or stale for the current render")
    if article["status"] != "complete":
        reasons.append(f"article is partial: {article.get('partial_reason')}")
    partial = pub_dir / f".package-partial-{os.getpid()}"
    if partial.exists():
        shutil.rmtree(partial)
    try:
        copies = [(p, p.relative_to(dist).as_posix()) for p in sorted(dist.rglob("*")) if p.is_file()
                  and (pdf_ok or p.name != "article.pdf")]
        copies += [(pub_dir / "article.json", "article.json")] + _package_sources(workspace, plan, article)
        problems = []
        for source, rel in copies:
            if Path(rel).suffix.lower() not in PACKAGE_EXTENSIONS or rel.startswith(("/", ".")) or ".." in rel.split("/"):
                problems.append(f"refusing to package unexpected file {rel}")
                continue
            if Path(rel).suffix.lower() in TEXT_EXTENSIONS and SECRET.search(source.read_text(errors="replace")):
                problems.append(f"refusing to package {rel}: it contains secret-like content (SAS, key, or token)")
            target = partial / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if problems:
            raise ContractError(problems)
        files = [{"path": rel, "sha256": evidence.sha256_file(partial / rel), "bytes": (partial / rel).stat().st_size}
                 for rel in sorted(rel for _, rel in copies)]
        revision = evidence.digest_json(files)[:16]
        manifest = {"schema_version": evidence.SCHEMA_VERSION, "publication_id": plan["id"], "kind": plan["kind"],
                    "video_ids": plan["video_ids"], "revision": revision, "status": article["status"],
                    "complete": not reasons, "incomplete_reasons": reasons, "pdf": pdf_ok,
                    "excluded": "original media, audio, partial stage output, and credentials are never packaged",
                    "files": files}
        evidence.atomic_write_json(partial / "manifest.json", manifest)
        _swap(partial, pub_dir / "package")
    finally:
        if partial.exists():
            shutil.rmtree(partial)
    package = pub_dir / "package"
    archive = pub_dir / f"{plan['id']}-{revision}.zip"
    temp = pub_dir / f".{archive.name}.tmp"
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as bundle:
        for rel in ["manifest.json"] + [f["path"] for f in files]:
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, (package / rel).read_bytes())
    os.replace(temp, archive)
    emit({"status": "packaged", "publication": plan["id"], "revision": revision, "complete": not reasons,
          "incomplete_reasons": reasons, "package_dir": str(package), "manifest": str(package / "manifest.json"),
          "manifest_sha256": evidence.sha256_file(package / "manifest.json"), "zip": str(archive),
          "zip_sha256": evidence.sha256_file(archive), "files": len(files)})
    return 0


def register(subparsers: Any) -> None:
    render = subparsers.add_parser("render", help="render offline HTML, Markdown, brief, and coverage report")
    render.add_argument("--workspace", required=True)
    render.add_argument("--publication", required=True, help="publication id from the assignment")
    render.set_defaults(func=cmd_render)
    pdf = subparsers.add_parser("pdf", help="print the rendered article to PDF with a headless Chromium browser")
    pdf.add_argument("--workspace", required=True)
    pdf.add_argument("--publication", required=True)
    pdf.add_argument("--browser", help="Chromium-compatible executable (default: DISTILL_BROWSER, PATH, /Applications)")
    pdf.add_argument("--timeout", type=float, default=120.0)
    pdf.add_argument("--wait", type=float, default=5.0, help="virtual time budget for scripts and images, seconds")
    pdf.set_defaults(func=cmd_pdf)
    package = subparsers.add_parser("package", help="build a checksummed package directory and ZIP")
    package.add_argument("--workspace", required=True)
    package.add_argument("--publication", required=True)
    package.add_argument("--allow-missing-pdf", action="store_true",
                         help="build an explicitly incomplete package without a current PDF")
    package.set_defaults(func=cmd_package)

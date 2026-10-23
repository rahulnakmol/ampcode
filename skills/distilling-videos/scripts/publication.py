"""Offline publication rendering and packaging for distilling-videos (schema_version 1).

Registers `render`, `pdf`, and `package` into distill.py. Reads verified evidence from the
workspace and an Amp-authored publications/<id>/article.json; see ../reference/article-contract.md.
Renders an offline multi-page site (cover, article, brief, transcripts, gallery, glossary, references),
each page with a Markdown twin; the article page is printed to the PDF.
"""

from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlsplit

import evidence
import themes
from evidence import ContractError, Workspace, check_id, safe_path

RENDERER = 4
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ALPINE = "vendor/alpine-3.17.4.min.js"
GSAP = "vendor/gsap-3.15.0.min.js"
ASSET_FILES = ("article.css", "article.js", "theme-init.js", ALPINE, GSAP, "vendor/LICENSE-alpinejs.md",
               "vendor/LICENSE-gsap.md", "vendor/PROVENANCE.md")
PDF_PAGE = "article.html"
# The only link to article.pdf. `package` removes it from draft packages that carry no current PDF.
PDF_LINK = '<span class="pdf-link"><a href="article.pdf">PDF</a> · </span>'
GLOSSARY_LIMIT = 320
CSP = ("default-src 'none'; script-src 'self' 'unsafe-eval'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
PACKAGE_EXTENSIONS = IMAGE_EXTENSIONS | {".html", ".md", ".json", ".css", ".js", ".pdf"}
TEXT_EXTENSIONS = {".html", ".md", ".json", ".css", ".js", ".svg"}
SECRET = re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{10,}|AccountKey=|SharedAccessSignature=|"
                    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}|\bAKIA[0-9A-Z]{16}\b|"
                    r"\bsk-[A-Za-z0-9_-]{24,}|\bxox[abprs]-[A-Za-z0-9-]{10,}")
FIGURE_PATH = re.compile(r"figures/(?:[A-Za-z0-9_][A-Za-z0-9._-]{0,254}/)*[A-Za-z0-9_][A-Za-z0-9._-]{0,254}")
SVG_NS = "{http://www.w3.org/2000/svg}"
SVG_ELEMENTS = set("svg g defs title desc path rect circle ellipse line polyline polygon text tspan textPath "
                   "use symbol marker clipPath mask linearGradient radialGradient stop".split())
SVG_ATTRIBUTES = set("id role aria-label aria-labelledby aria-describedby viewBox preserveAspectRatio "
                     "x y x1 y1 x2 y2 cx cy r rx ry width height d points dx dy rotate transform "
                     "fill fill-opacity fill-rule stroke stroke-width stroke-opacity stroke-linecap "
                     "stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset opacity "
                     "font-family font-size font-weight font-style text-anchor dominant-baseline "
                     "alignment-baseline letter-spacing word-spacing textLength lengthAdjust "
                     "clip-path clip-rule mask marker-start marker-mid marker-end markerWidth markerHeight "
                     "markerUnits refX refY orient gradientUnits gradientTransform spreadMethod "
                     "offset stop-color stop-opacity fx fy fr patternUnits clipPathUnits maskUnits "
                     "maskContentUnits startOffset method spacing".split())
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
# A complete (publishable) primary article needs this many narrative body words; 1200-1500+ is the target.
NARRATIVE_MIN_WORDS = 1000
NARRATIVE_TARGET_WORDS = (1200, 1500)
WORD = re.compile(r"[^\W_]+(?:['’.-][^\W_]+)*")
SEO_DESCRIPTION_LIMIT = 300
SEO_DESCRIPTION_SNIPPET = 160
# Hosts that cannot be a real public canonical: local names and reserved example/test domains (RFC 2606, 6761).
NON_PUBLIC_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".arpa", ".test", ".example",
                       ".invalid", ".onion")
EXAMPLE_HOSTS = {"localhost", "example.com", "example.net", "example.org"}
E = html.escape


# ---------------------------------------------------------------------------
# Evidence and article validation


def validate_svg(path: Path) -> None:
    """Accept static diagram XML only, including when opened outside the HTML page's CSP."""
    try:
        text = path.read_text(encoding="utf-8")
        if re.search(r"<!DOCTYPE|<!ENTITY|<\?(?!xml\s)", text, re.IGNORECASE):
            raise ContractError("SVG declarations and processing instructions are not allowed")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as error:
        raise ContractError(f"SVG must be well-formed UTF-8 XML: {error}") from None
    if root.tag != SVG_NS + "svg":
        raise ContractError("SVG root must use the SVG namespace")
    for element in root.iter():
        if element.tag not in {SVG_NS + name for name in SVG_ELEMENTS}:
            raise ContractError(f"SVG element is not permitted in a static diagram: {element.tag}")
        for name, value in element.attrib.items():
            if name in {"href", "{http://www.w3.org/1999/xlink}href"}:
                if not re.fullmatch(r"#[A-Za-z_][A-Za-z0-9_.-]*", value):
                    raise ContractError("SVG references must be local fragment IDs")
            elif name == "{http://www.w3.org/XML/1998/namespace}space":
                if value not in {"default", "preserve"}:
                    raise ContractError("SVG xml:space must be default or preserve")
            elif name not in SVG_ATTRIBUTES:
                raise ContractError(f"SVG attribute is not permitted in a static diagram: {name}")
            # Presentation attributes can contain CSS URLs. No escapes, external URLs, or
            # encoded CSS functions; XML character references have already been decoded.
            if "\\" in value or re.search(r"url\s*\(|[<>]", value, re.IGNORECASE):
                if not re.fullmatch(r"url\(#[A-Za-z_][A-Za-z0-9_.-]*\)", value):
                    raise ContractError("SVG paint references must be local fragment IDs")


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
            "language": segments["language"],
            # Derived from each segment's english_kind so a stale stored label can never claim cleaning.
            "english_label": evidence.english_label(segments["language"], segments["segments"]),
            "provider_kind": segments["provider"]["kind"], "coverage": coverage,
            "segments": {s["id"]: s for s in segments["segments"]},
            "frames": {f["id"]: f for f in frames["frames"]} if frames else None,
            "max_sampling_gap": frames.get("max_sampling_gap_seconds") if frames else None,
            "selected": (evidence.read_json(base / "selection.json")["frame_ids"]
                         if "selection.json" in files else []),
            "english_md": (base / "transcript" / "english.md").read_text(encoding="utf-8"),
            "original_md": (base / "transcript" / "original.md").read_text(encoding="utf-8"),
        })
    return sources, problems, inputs


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def canonical_problems(url: str) -> List[str]:
    """A canonical URL is the user's real public https address for the hosted article. Never invented,
    never local (file://, localhost, private or literal IPs), never a reserved example or test domain."""
    bad = "article.seo.canonical_url must be the public https URL where the article is hosted"
    if url != url.strip() or re.search(r"[\s\"'<>\\`\x00-\x1f\x7f]", url):
        return [f"{bad}; it contains whitespace, quotes, angle brackets, or control characters"]
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".")
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        return [f"{bad}; it is not a valid URL"]
    if parts.scheme != "https":
        return [f"{bad}; scheme {parts.scheme or '(none)'!r} is not https"]
    if parts.username or parts.password or parts.fragment:
        return [f"{bad}; it must not carry credentials or a #fragment"]
    try:
        ipaddress.ip_address(host.strip("[]"))
        return [f"{bad}; an IP address is not a public canonical host"]
    except ValueError:
        pass
    if ("." not in host or host in EXAMPLE_HOSTS or host.endswith(NON_PUBLIC_SUFFIXES)
            or any(host.endswith("." + h) for h in EXAMPLE_HOSTS)):
        return [f"{bad}; host {host or '(none)'!r} is local, reserved, or an example domain"]
    return []


def narrative_stats(article: Dict[str, Any]) -> Dict[str, Any]:
    """Narrative body words: author prose on the article's main reading path (section paragraphs and
    list items). Headings, dek, quotes, figures, collapsed `details`, limitations, brief, glossary,
    references, navigation, and transcripts do not count; `details` prose is reported as deeper_words.
    A paragraph or item repeated verbatim (case and whitespace folded) counts once."""
    seen: set = set()
    stats = {"narrative_words": 0, "deeper_words": 0, "repeated_blocks": 0, "minimum": NARRATIVE_MIN_WORDS,
             "target": list(NARRATIVE_TARGET_WORDS)}

    def visit(blocks: List[Dict[str, Any]], field: str) -> None:
        for block in blocks:
            if block["type"] == "details":
                visit(block["blocks"], "deeper_words")
                continue
            texts = [block["text"]] if block["type"] == "p" else block["items"] if block["type"] == "list" else []
            for text in texts:
                key = _normalize(plain(text))
                if key in seen:
                    stats["repeated_blocks"] += 1
                    continue
                seen.add(key)
                stats[field] += len(WORD.findall(plain(text)))

    for section in article["sections"]:
        visit(section["blocks"], "narrative_words")
    return stats


def narrative_gate(article: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Refuse a complete article below the floor; warn on partial drafts, the target band, and repeats."""
    stats = narrative_stats(article)
    words, low, high = stats["narrative_words"], *NARRATIVE_TARGET_WORDS
    if article["status"] == "complete" and words < NARRATIVE_MIN_WORDS:
        raise ContractError(
            f"article is complete but its narrative body is {words} words; a complete primary article needs at "
            f"least {NARRATIVE_MIN_WORDS} (target {low}-{high}+) of real explanation in section paragraphs and "
            "lists, without padding. Deepen the concepts, mechanisms, and examples the evidence supports, or "
            "set status partial with a partial_reason.")
    warnings = []
    if words < NARRATIVE_MIN_WORDS:
        warnings.append(f"partial draft: narrative body is {words} words, below the {NARRATIVE_MIN_WORDS}-word "
                        "floor; it cannot be published as complete")
    elif words < low:
        warnings.append(f"narrative body is {words} words, below the {low}-{high}+ target")
    if stats["repeated_blocks"]:
        warnings.append(f"{stats['repeated_blocks']} repeated paragraph(s) or list item(s) were not counted")
    return stats, warnings


def check_article(data: Any, plan: Dict[str, Any], sources: List[Dict[str, Any]], pub_dir: Path,
                  inputs: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """Validate structure and every reference. Adds referenced figure files to inputs."""
    top = ("schema_version", "publication_id", "title", "dek", "status", "sections", "figures", "citations",
           "brief", "limitations")
    problems = _fields(data, "article", top, ("partial_reason", "audience", "glossary", "seo"))
    if not isinstance(data, dict):
        return problems, []
    warnings: List[str] = []
    problems += _texts(data, ("title", "dek", "partial_reason", "audience"), "article")
    if "seo" in data:
        seo = data["seo"]
        problems += _fields(seo, "article.seo", (), ("description", "canonical_url"))
        if isinstance(seo, dict):
            problems += _texts(seo, ("description", "canonical_url"), "article.seo")
            description = seo.get("description")
            if isinstance(description, str) and description.strip():
                if "[@" in description:
                    problems.append("article.seo.description is plain text; it must not cite sources")
                elif len(description.strip()) > SEO_DESCRIPTION_LIMIT:
                    problems.append(f"article.seo.description is longer than {SEO_DESCRIPTION_LIMIT} characters")
            if isinstance(seo.get("canonical_url"), str) and seo["canonical_url"].strip():
                problems += canonical_problems(seo["canonical_url"])
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

    def inline(text: Any, where: str) -> None:
        """Every inline text field is checked before rendering: each [@...] marker must name defined ids."""
        if not isinstance(text, str):
            return
        for kind, value in tokens(text):
            if kind == "cite":
                if not value:
                    problems.append(f"{where} has an empty citation marker")
                cite(value, where)

    inline(data.get("dek"), "article.dek")

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
                    inline(step.get("caption"), f"{label}.steps[{step_index}].caption")
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
            if not isinstance(image, str) or not FIGURE_PATH.fullmatch(image):
                problems.append(f"{label}.image must be an archive-safe path under figures/ "
                                "(letters, digits, underscores, hyphens, and dots only)")
            else:
                try:
                    path = safe_path(pub_dir, image)
                    if path.suffix.lower() not in IMAGE_EXTENSIONS:
                        problems.append(f"{label}.image must be one of {sorted(IMAGE_EXTENSIONS)}")
                    elif not path.is_file():
                        problems.append(f"{label}.image target is missing: {image}")
                    else:
                        if path.suffix.lower() == ".svg":
                            validate_svg(path)
                        inputs[f"publications/{plan['id']}/{image}"] = evidence.sha256_file(path)
                except ContractError as error:
                    problems += error.problems
            assumptions = _list(figure, "assumptions")
            if not assumptions or not all(isinstance(a, str) and a.strip() for a in assumptions):
                problems.append(f"{label} original figures must state their assumptions")
            for assumption_index, assumption in enumerate(assumptions):
                inline(assumption, f"{label}.assumptions[{assumption_index}]")
            if not _list(figure, "sources"):
                problems.append(f"{label} original figures must cite their sources")
            problems += _strings(figure, "sources", label)
            cite(_list(figure, "sources"), label)
        else:
            problems.append(f"{label} kind must be capture, sequence, or original")
            continue
        if isinstance(figure, dict):
            problems += _texts(figure, ("alt", "caption"), label)
            inline(figure.get("caption"), f"{label}.caption")
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
                inline(block.get("text"), where)
            elif kind == "list":
                problems.extend(_fields(block, where, ("type", "items"), ("ordered",)))
                if "ordered" in block and not isinstance(block["ordered"], bool):
                    problems.append(f"{where}.ordered must be true or false")
                if not _list(block, "items") or not all(isinstance(i, str) and i.strip() for i in block["items"]):
                    problems.append(f"{where} items must be non-empty text")
                for item in _list(block, "items"):
                    inline(item, where)
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
                inline(block.get("summary"), f"{where}.summary")
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
        inline(section.get("heading"), f"{label}.heading")
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
    for index, limitation in enumerate(_list(data, "limitations")):
        inline(limitation, f"article.limitations[{index}]")

    brief = data.get("brief")
    problems += _fields(brief, "brief", ("evidence", "proposals"), ("question",))
    if isinstance(brief, dict):
        problems += _texts(brief, ("question",), "brief")
        inline(brief.get("question"), "brief.question")
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
            inline(item.get("text"), label)
            cite(_list(item, "citations"), label)
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

    glossary = data.get("glossary")
    if glossary is not None and not isinstance(glossary, list):
        problems.append("article.glossary must be a list of {term, definition}")
    terms = set()
    for index, entry in enumerate(glossary if isinstance(glossary, list) else []):
        label = f"glossary[{index}]"
        problems += _fields(entry, label, ("term", "definition"))
        if not isinstance(entry, dict):
            continue
        problems += _texts(entry, ("term", "definition"), label)
        if isinstance(entry.get("term"), str) and entry["term"].strip():
            if _normalize(entry["term"]) in terms:
                problems.append(f"duplicate glossary term {entry['term']!r}")
            terms.add(_normalize(entry["term"]))
        if isinstance(entry.get("definition"), str):
            if len(plain(entry["definition"]).strip()) > GLOSSARY_LIMIT:
                problems.append(f"{label}.definition is longer than {GLOSSARY_LIMIT} characters; glossary "
                                "definitions must be short")
            inline(entry["definition"], label)

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


NAV = (("index.html", "Overview", "overview"), ("article.html", "Article", "article"), ("brief.html", "Brief", "brief"),
       ("transcripts.html", "Transcripts", "transcripts"), ("gallery.html", "Gallery", "gallery"),
       ("glossary.html", "Glossary", "glossary"), ("references.html", "References", "references"))
LATER_OUTPUTS = {"article.pdf"}  # written by `pdf` after render; links to it are expected


def plain(text: str) -> str:
    """Inline text without markup or citation markers, for search and length checks."""
    return "".join(v for k, v in tokens(text) if k != "cite") if isinstance(text, str) else ""


def lang_code(language: str) -> str:
    return language if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language or "") else "und"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")[:48]


ZIP_SLUG_MAX = 80
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def readable_slug(text: str, limit: int = ZIP_SLUG_MAX) -> str:
    """ASCII, lowercase, hyphen-separated, path-safe slug; cut at a word boundary."""
    text = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    text = re.sub(r"['\u2018\u2019`]", "", text.casefold())
    base = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(base) > limit:
        cut = base[:limit + 1]
        base = (cut.rsplit("-", 1)[0] if "-" in cut else cut[:limit]).strip("-")
    return base


def package_zip_names(title: Optional[str], publication_id: str, revision: str) -> List[str]:
    """Readable ZIP names in preference order: the title slug, then short and full revision on collision."""
    base = readable_slug(title or "") or readable_slug(publication_id) or "publication"
    if base in WINDOWS_RESERVED:
        base += "-article"
    return [f"{base}.zip", f"{base}-{revision[:8]}.zip", f"{base}-{revision}.zip"]


class Context:
    def __init__(self, article: Dict[str, Any], sources: List[Dict[str, Any]]):
        self.article = article
        self.sources = {s["id"]: s for s in sources}
        self.citations = {c["id"]: self._resolve(c) for c in article["citations"]}
        self.figures = {f["id"]: f for f in article["figures"]}
        self.order: List[str] = []
        self.figure_numbers: Dict[str, int] = {}
        self.media = self._media_frames()
        self.gallery = self._gallery()
        self.terms = self._terms()

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

    def _media_frames(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """Frames copied into dist/media: placed, selected, cited, and linked from transcript Markdown."""
        wanted = set()
        for f in self.article["figures"]:
            if f["kind"] == "capture":
                wanted.add((f["video_id"], f["frame_id"]))
            elif f["kind"] == "sequence":
                wanted |= {(f["video_id"], s["frame_id"]) for s in f["steps"]}
        wanted |= {(c["video_id"], c["frame_id"]) for c in self.article["citations"] if c.get("frame_id")}
        for source in self.sources.values():
            frames = source["frames"] or {}
            wanted |= {(source["id"], fid) for fid in source["selected"] if fid in frames}
            by_path = {p: fid for fid, f in frames.items() for p in (f["path"], f["thumbnail"])}
            for rel in re.findall(r"\]\(\.\./([^)\s]+)\)", source["english_md"]):
                if rel in by_path:
                    wanted.add((source["id"], by_path[rel]))
        return {key: self.sources[key[0]]["frames"][key[1]] for key in sorted(wanted)}

    def _gallery(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        shown = set()
        numbers = {}
        for figure in self.article["figures"]:
            numbers[figure["id"]] = len(numbers) + 1
            if figure["kind"] == "original":
                items.append({"kind": "original", "figure": figure, "src": figure["image"], "thumb": figure["image"],
                              "alt": figure["alt"], "caption": figure["caption"], "number": numbers[figure["id"]]})
                continue
            steps = ([{"frame_id": figure["frame_id"], "alt": figure["alt"], "caption": figure["caption"]}]
                     if figure["kind"] == "capture" else figure["steps"])
            for index, step in enumerate(steps):
                full, thumb = frame_media(figure["video_id"], step["frame_id"])
                shown.add((figure["video_id"], step["frame_id"]))
                items.append({"kind": figure["kind"], "figure": figure, "video_id": figure["video_id"],
                              "frame_id": step["frame_id"], "src": full, "thumb": thumb, "alt": step["alt"],
                              "caption": step["caption"], "number": numbers[figure["id"]],
                              "step": index + 1 if figure["kind"] == "sequence" else None,
                              "steps": len(steps)})
        for (video_id, frame_id), frame in self.media.items():
            if (video_id, frame_id) in shown:
                continue
            source = self.sources[video_id]
            full, thumb = frame_media(video_id, frame_id)
            items.append({"kind": "frame", "video_id": video_id, "frame_id": frame_id, "src": full, "thumb": thumb,
                          "alt": f"Source frame {frame_id} from Reel {source['reel']} at "
                                 f"{evidence.timestamp(frame['t'])} (no description recorded)",
                          "caption": None})
        for index, item in enumerate(items, 1):
            item["id"] = f"g-{index}"
            if item.get("video_id"):
                source = self.sources[item["video_id"]]
                item["reel"] = source["reel"]
                item["t"] = source["frames"][item["frame_id"]]["t"]
        return items

    def _terms(self) -> List[Dict[str, Any]]:
        terms, seen = [], set()
        for index, entry in enumerate(self.article.get("glossary") or [], 1):
            anchor = "term-" + (slug(entry["term"]) or str(index))
            while anchor in seen:
                anchor = f"{anchor}-{index}"
            seen.add(anchor)
            terms.append({**entry, "anchor": anchor})
        return terms

    def number(self, cid: str) -> int:
        """The citation's number in the current document. The order is fixed by start(), so the HTML page,
        its Markdown twin, and its references list always agree, whatever order the renderer visits text in."""
        if cid not in self.order:
            raise RuntimeError(f"citation {cid!r} is not in this document's citation order")
        return self.order.index(cid) + 1

    def start(self, ids: List[str]) -> None:
        """Begin a document whose citations, in reading order, are ids (first use wins)."""
        self.order = list(dict.fromkeys(ids))
        self.figure_numbers = {}


# Citation order per document: first use in reading order. HTML and Markdown share these lists.


def blocks_cites(blocks: List[Dict[str, Any]], figures: Dict[str, Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for block in blocks:
        if block["type"] == "p":
            out += text_cites(block["text"])
        elif block["type"] == "list":
            out += [c for item in block["items"] for c in text_cites(item)]
        elif block["type"] == "quote":
            out.append(block["cite"])
        elif block["type"] == "figure":
            out += figure_cites(figures[block["figure"]])
        else:
            out += text_cites(block["summary"]) + blocks_cites(block["blocks"], figures)
    return out


def figure_cites(figure: Dict[str, Any]) -> List[str]:
    out = text_cites(figure["caption"])
    out += [c for step in figure.get("steps", []) for c in text_cites(step["caption"])]
    out += list(figure.get("sources", []))
    return out + [c for a in figure.get("assumptions", []) for c in text_cites(a)]


def limitation_cites(article: Dict[str, Any]) -> List[str]:
    return [c for x in article["limitations"] for c in text_cites(x)]


def article_cites(article: Dict[str, Any]) -> List[str]:
    figures = {f["id"]: f for f in article["figures"]}
    out = text_cites(article["dek"])
    for section in article["sections"]:
        out += text_cites(section["heading"]) + blocks_cites(section["blocks"], figures)
    return list(dict.fromkeys(out + limitation_cites(article)))


def brief_cites(article: Dict[str, Any]) -> List[str]:
    brief = article["brief"]
    out = text_cites(article["dek"]) + text_cites(brief.get("question"))
    for kind in EVIDENCE_KINDS:
        for item in brief["evidence"]:
            if item["kind"] == kind:
                out += text_cites(item["text"]) + list(item.get("citations", []))
    return list(dict.fromkeys(out + limitation_cites(article)))


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
                     f'<span class="tc-n">{ctx.number(cid)}</span> {E(citation["chip"]).replace("/", "/<wbr>")}</a>')
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
        slug_text = (f'Fig. {number} · Source capture · <a href="{E(link)}" rel="noopener noreferrer">Reel '
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
        slug_text = f"Fig. {number} · Original figure — our reconstruction, not a source capture{E(derived)}"
        assumptions = "".join(f"<li>{inline_html(a, ctx, [])}</li>" for a in figure["assumptions"])
        notes = f'<div class="assumptions"><p>Assumptions{refs}</p><ul>{assumptions}</ul></div>'
    return (f'<figure class="fig fig-{kind}" id="{E(figure["id"])}" x-data="zoom">'
            f'<a class="frame" href="{E(src)}" @click.prevent="open()" aria-label="Enlarge figure {number}">'
            f'<img src="{E(src)}" alt="{E(figure["alt"])}" loading="lazy"></a>'
            f'<figcaption><span class="slug">{slug_text}</span> {caption}{notes}</figcaption>'
            f'<dialog class="lightbox" x-ref="dialog" @click.self="close()" aria-label="Figure {number}">'
            f'<img src="{E(src)}" alt="{E(figure["alt"])}"><p>{caption}</p>'
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


COPY_ICON = ('<svg class="icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">'
             '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 '
             '1-2-2V6a2 2 0 0 1 2-2h2"/></svg>')


def theme_select() -> str:
    groups = ['<option value="">System (House light or dark)</option>']
    for family, entries in themes.options():
        opts = "".join(f'<option value="{E(i)}">{E(label)}</option>' for i, label in entries)
        groups.append(f'<optgroup label="{E(family)}">{opts}</optgroup>')
    return (f'<div class="theme-pick"><label for="theme-select">Theme</label>'
            f'<select id="theme-select" @change="setTheme($event.target.value)">{"".join(groups)}</select>'
            f'<a class="theme-credits" href="assets/THEMES.md">Theme sources and licenses</a></div>')


def seo_description(article: Dict[str, Any]) -> str:
    seo = article.get("seo") or {}
    return re.sub(r"\s+", " ", seo.get("description") or plain(article["dek"])).strip()


def json_ld(data: Any) -> str:
    """JSON for a <script type="application/ld+json"> data block: no character can end the element."""
    text = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def seo_head(ctx: Context) -> str:
    """Search and share metadata for article.html only. Everything here is stated by the article or the
    user (title, dek or seo.description, an optional real canonical URL); no authors, dates, or images
    are invented. Offline packages are not crawlable until the user hosts them."""
    article = ctx.article
    title, description = article["title"], seo_description(article)
    canonical = (article.get("seo") or {}).get("canonical_url")
    tags = [f'<meta name="description" content="{E(description)}">']
    if article["status"] != "complete":
        tags.append('<meta name="robots" content="noindex">')
    if canonical:
        tags.append(f'<link rel="canonical" href="{E(canonical)}">')
    tags += ['<meta property="og:type" content="article">', f'<meta property="og:title" content="{E(title)}">',
             f'<meta property="og:description" content="{E(description)}">']
    if canonical:
        tags.append(f'<meta property="og:url" content="{E(canonical)}">')
    tags += ['<meta name="twitter:card" content="summary">', f'<meta name="twitter:title" content="{E(title)}">',
             f'<meta name="twitter:description" content="{E(description)}">']
    data: Dict[str, Any] = {"@context": "https://schema.org", "@type": "Article", "headline": title,
                            "description": description, "inLanguage": "en",
                            "isBasedOn": [f"https://www.youtube.com/watch?v={s['youtube_id']}"
                                          for s in ctx.sources.values()]}
    if canonical:
        data["url"] = data["mainEntityOfPage"] = canonical
    tags.append(f'<script type="application/ld+json">{json_ld(data)}</script>')
    return "".join(tags)


def page(ctx: Context, title: str, body: str, kind: str, md_name: str, md_text: str, current: str,
         head: str = "") -> str:
    current_attr = ' aria-current="page"'
    links = "".join(f'<li><a href="{href}"{current_attr if key == current else ""}>{label}</a></li>'
                    for href, label, key in NAV)
    nav = (f'<nav class="site-nav" id="site-nav" aria-label="Publication">'
           f'<div class="nav-head"><a class="nav-title" href="index.html">{E(ctx.article["title"])}</a>'
           f'<button type="button" class="nav-close js-only" @click="closeNav()" aria-controls="site-nav" '
           f'x-text="mobile ? \'Close menu\' : \'Hide navigation\'">Hide navigation</button></div>'
           f'<ul class="nav-list">{links}</ul>'
           f'<div class="nav-tools js-only"><button type="button" class="nav-search" @click="openSearch()" '
           f'aria-haspopup="dialog">Search <kbd>/</kbd></button>{theme_select()}</div></nav>')
    toolbar = (f'<div class="toolbar"><button type="button" class="menu-button js-only" @click="toggleNav()" '
               f'aria-controls="site-nav" :aria-expanded="navVisible ? \'true\' : \'false\'" '
               f'x-text="mobile ? \'Menu\' : \'Show navigation\'">Menu</button>'
               f'<button type="button" class="toolbar-search js-only" @click="openSearch()" aria-haspopup="dialog">'
               f'Search</button>'
               f'<div class="page-tools" x-data="copyPage"><button type="button" class="copy-page js-only" '
               f'@click="copy()" aria-describedby="copy-status">{COPY_ICON}<span x-text="label">Copy Page</span></button>'
               f'<a class="download-md" href="{md_name}" download>Download Markdown</a>'
               f'<span class="copy-status" id="copy-status" role="status" aria-live="polite" x-text="status"></span>'
               f'</div></div>')
    source = (f'<details class="md-source" id="md-source"><summary>Page Markdown</summary>'
              f'<p>The complete Markdown of this page ({E(md_name)}), independent of filters and open panels. '
              f'Select it and copy, or download it.</p><textarea id="page-markdown" readonly rows="14" '
              f'spellcheck="false" aria-label="Markdown source of this page">\n{E(md_text)}</textarea></details>')
    panel = ('<aside class="evidence-panel" id="evidence-panel" role="dialog" aria-modal="false" '
             'aria-labelledby="evidence-title" hidden><div class="ev-head"><h2 id="evidence-title" tabindex="-1">'
             'Evidence</h2><button type="button" class="ev-close" @click="closeEvidence()">Close</button></div>'
             '<div class="ev-body" id="evidence-body"></div></aside>')
    search = ('<dialog class="search-dialog" id="search-dialog" aria-labelledby="search-title" x-data="search">'
              '<div class="search-head"><h2 id="search-title">Search this publication</h2>'
              '<button type="button" class="search-close" @click="close()">Close</button></div>'
              '<label class="visually-hidden" for="search-input">Search terms</label>'
              '<input type="search" id="search-input" x-model="q" @input="run()" @keydown.arrow-down.prevent="first()" '
              'autocomplete="off" placeholder="Article, transcripts, glossary, references…" '
              'aria-describedby="search-count">'
              '<p class="search-count" id="search-count" role="status" aria-live="polite" x-text="summary"></p>'
              '<ol class="search-results" x-ref="results" @click="picked($event)"></ol></dialog>')
    return (f'<!doctype html>\n<html lang="en" class="no-js"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
            f'<meta name="referrer" content="no-referrer"><title>{E(title)}</title>{head}'
            f'<script src="assets/theme-init.js"></script>'
            f'<link rel="stylesheet" href="assets/themes.css"><link rel="stylesheet" href="assets/article.css">'
            f'<script defer src="assets/search-index.js"></script><script defer src="assets/{GSAP}"></script>'
            # article.js registers the Alpine components and then loads assets/{ALPINE} itself, so Alpine
            # never runs without them (half-initialized directives could hide demo steps or leave dead controls).
            f'<script defer src="assets/article.js"></script>'
            f'</head><body class="page-{kind}" x-data="shell" @keydown.window="onKey($event)">'
            f'<a class="skip" href="#main">Skip to content</a>'
            '<svg class="defs" aria-hidden="true" focusable="false"><defs><pattern id="hatch" width="6" height="6" '
            'patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="hatch-line" width="2" '
            f'height="6"/></pattern></defs></svg><div class="shell">{nav}'
            f'<div class="nav-backdrop js-only" @click="closeNav()"></div>'
            f'<div class="page" id="page">{toolbar}{body}{source}</div></div>{panel}{search}</body></html>\n')


def references_html(ctx: Context) -> str:
    items = []
    for n, cid in enumerate(ctx.order, 1):
        citation = ctx.citations[cid]
        url = citation["url"]
        items.append(f'<li id="ref-{n}">{E(citation["label"])}. <a class="url" href="{E(url)}" '
                     f'rel="noopener noreferrer">{E(url)}</a></li>')
    return f'<section class="references" id="references" aria-labelledby="h-references">' \
           f'<h2 id="h-references">References</h2><ol>{"".join(items)}</ol></section>'


def evidence_templates(ctx: Context) -> str:
    """Inert, escaped evidence for the citation panel. No-JS readers use the references list instead."""
    out = []
    for n, cid in enumerate(ctx.order, 1):
        c = ctx.citations[cid]
        back = f'<a class="ev-ref" href="#ref-{n}">Show in references</a>'
        note = f'<p class="ev-note">{E(c["note"])}</p>' if c.get("note") else ""
        if c["kind"] == "web":
            meta = " · ".join(E(x) for x in (c.get("publisher"), c.get("accessed") and f"accessed {c['accessed']}") if x)
            body = (f'<p class="slug">Reference {n} · External source</p><p class="ev-label">{E(c["title"])}</p>'
                    f'{f"<p class=ev-meta>{meta}</p>" if meta else ""}{note}<p class="ev-links">'
                    f'<a href="{E(c["url"])}" rel="noopener noreferrer">{E(c["url"])}</a> · {back}</p>')
        else:
            source = ctx.sources[c["video_id"]]
            language = lang_code(source["language"])
            segments = []
            for sid in c.get("segment_ids", []):
                s = source["segments"][sid]
                original = "" if _normalize(s["text"]) == _normalize(s["english"]) else (
                    f'<p class="ev-orig" lang="{language}"><span class="slug">Original ({E(source["language"])})</span> '
                    f'{E(s["text"])}</p>')
                uncertain = (f'<p class="ev-uncertain"><strong>Uncertain:</strong> '
                             f'{E(s.get("uncertainty") or "contains inline uncertainty markers")}</p>'
                             if s.get("uncertain") or s.get("inline_markers") else "")
                segments.append(
                    f'<li><p class="slug"><a href="{E(evidence.timestamp_url(source["youtube_id"], s["start"]))}" '
                    f'rel="noopener noreferrer">{evidence.timestamp(s["start"])}</a> · <a href="transcript-'
                    f'{E(source["id"])}.html#seg-{E(sid)}">Transcript segment {E(sid)}</a></p>'
                    f'<p class="ev-en"><span class="slug">{E(segment_english(source, s))}</span> '
                    f'{E(s["english"])}</p>{original}{uncertain}</li>')
            frame = ""
            if c.get("frame_id"):
                t = source["frames"][c["frame_id"]]["t"]
                full, thumb = frame_media(source["id"], c["frame_id"])
                frame = (f'<figure class="ev-frame"><a href="{full}"><img src="{thumb}" alt="Source frame '
                         f'{E(c["frame_id"])} from Reel {source["reel"]} at {evidence.timestamp(t)}"></a>'
                         f'<figcaption class="slug">Frame {E(c["frame_id"])} · Reel {source["reel"]} '
                         f'{evidence.timestamp(t)} · untouched capture</figcaption></figure>')
            body = (f'<p class="slug">Reference {n} · Reel {source["reel"]} · {E(source["creator"])}</p>'
                    f'<p class="ev-label">{E(c["label"])}</p>'
                    f'{f"<ol class=ev-segments>{chr(10).join(segments)}</ol>" if segments else ""}{frame}{note}'
                    f'<p class="ev-links"><a href="{E(c["url"])}" rel="noopener noreferrer">Watch at '
                    f'{evidence.timestamp(c["start"])} on YouTube</a> · {back}</p>')
        out.append(f'<template id="ev-{n}">{body}</template>')
    return "".join(out)


def cited_tail(ctx: Context) -> str:
    """References and evidence templates for any page whose text cites sources."""
    return references_html(ctx) + evidence_templates(ctx) if ctx.order else ""


def english_text(source: Dict[str, Any], field: str) -> str:
    return evidence.english_wording(source["english_label"], source["provider_kind"])[field]


def segment_english(source: Dict[str, Any], segment: Dict[str, Any]) -> str:
    """Per-segment slug: a verbatim caption is never called clean, even inside a mixed transcript."""
    if not evidence._language_is_english(source["language"]):
        return "English translation"
    label = evidence.KIND_LABELS[segment.get("english_kind", "clean")]
    return evidence.english_wording(label, source["provider_kind"])["short"]


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
            f'segments, {coverage["covered_seconds"]:.0f} s covered{share}. {E(english_text(source, "note"))}</li>'
            f'<li>Transcript gaps: {E(gaps) if gaps else "none over the 2 s threshold"}.</li>'
            f'<li>Uncertain segments: {E(", ".join(coverage["uncertain_segment_ids"])) or "none marked"}.</li>'
            f'<li>{E(frames)}</li></ul></div>')
    limits = "".join(f"<li>{inline_html(x, ctx, [])}</li>" for x in ctx.article["limitations"])
    return (f'<section class="method" id="method" aria-labelledby="h-method"><h2 id="h-method">How this was made, '
            f'and its limits</h2>{"".join(rows)}<h3>Limitations</h3><ul>{limits or "<li>None recorded.</li>"}</ul>'
            '</section>')


def masthead(ctx: Context, eyebrow_text: str, title: str, dek: str, moments_from: Optional[List[str]] = None,
             compact: bool = False) -> str:
    article = ctx.article
    moments: Dict[str, List[float]] = {}
    for cid in (ctx.order if moments_from is None else moments_from):
        citation = ctx.citations[cid]
        if citation["kind"] == "video":
            moments.setdefault(citation["video_id"], []).append(citation["start"])
    partial = ""
    if article["status"] == "partial":
        partial = (f'<p class="status-partial"><strong>Partial publication.</strong> '
                   f'{E(article["partial_reason"])}</p>')
    if compact:
        return (f'<header class="masthead masthead-compact"><p class="eyebrow">{E(eyebrow_text)}</p><h1>{E(title)}</h1>'
                f'{f"<p class=dek>{dek}</p>" if dek else ""}{partial}</header>')
    reels = []
    for source in ctx.sources.values():
        link = evidence.timestamp_url(source["youtube_id"], 0)
        meta = " · ".join([source["creator"], evidence.timestamp(source["duration"] or 0), source["language"]])
        reels.append(f'<li class="reel"><p class="reel-id">Reel {source["reel"]}</p><p class="reel-title">'
                     f'<a href="{E(link)}" rel="noopener noreferrer">{E(source["title"])}</a></p>'
                     f'<p class="reel-meta">{E(meta)}</p>{tape(source, moments.get(source["id"], []))}</li>')
    return (f'<header class="masthead"><p class="eyebrow">{E(eyebrow_text)}</p><h1>{E(title)}</h1>'
            f'<p class="dek">{inline_html(dek, ctx, [])}</p>{partial}'
            f'<section class="slate" aria-label="Source videos"><ol class="reels">{"".join(reels)}</ol>'
            f'<p class="slate-note">Ticks mark cited moments; hatching marks transcript gaps.</p></section></header>')


def eyebrow(ctx: Context) -> str:
    count = len(ctx.sources)
    return f"Distilled from {count} video{'s' if count > 1 else ''}" + (" · synthesis" if count > 1 else "")


def article_body(ctx: Context) -> str:
    """The article (article.html, printed to article.pdf)."""
    article = ctx.article
    ctx.start(article_cites(article))
    head = masthead(ctx, eyebrow(ctx), article["title"], article["dek"])
    sections = []
    for section in article["sections"]:
        sections.append(f'<section id="s-{section["id"]}" aria-labelledby="h-{section["id"]}" class="reveal">'
                        f'<h2 id="h-{section["id"]}">{inline_html(section["heading"], ctx, [])}</h2>'
                        f'{blocks_html(section["blocks"], ctx)}</section>')
    toc = ""
    if len(article["sections"]) >= 3:
        toc = '<nav class="toc" aria-label="Contents"><ol>' + "".join(
            f'<li><a href="#s-{s["id"]}">{E(plain(s["heading"]))}</a></li>' for s in article["sections"]) + "</ol></nav>"
    body = "".join(sections)
    tail = method_html(ctx) + references_html(ctx) + evidence_templates(ctx)
    footer = ('<footer class="colophon"><p>Rendered offline from timestamped evidence. Also available: '
              '<a href="index.html">overview</a> · <a href="brief.html">research brief</a> · '
              f'<a href="article.md">Markdown</a> · {PDF_LINK}'
              '<a href="coverage.json">coverage report</a>.</p></footer>')
    return f'{head}<main id="main"><article>{toc}{body}{tail}</article></main>{footer}'


def brief_body(ctx: Context) -> str:
    article, brief = ctx.article, ctx.article["brief"]
    ctx.start(brief_cites(article))
    head = masthead(ctx, eyebrow(ctx) + " · research brief", f"Brief: {article['title']}", article["dek"])
    question = f'<p class="question">Question: {inline_html(brief["question"], ctx, [])}</p>' \
        if brief.get("question") else ""
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
    body = (f'<section aria-labelledby="h-evidence"><h2 id="h-evidence">What the sources establish</h2>'
            f'{"".join(groups)}</section><section class="proposals" aria-labelledby="h-proposals">'
            f'<h2 id="h-proposals">What we propose</h2><p class="proposal-note">These are our conclusions and '
            f'next steps. They are not established by the sources; each names the evidence it rests on.</p>'
            f'<div role="list">{"".join(proposals) or "<p>No proposals.</p>"}</div></section>')
    footer = ('<footer class="colophon"><p><a href="article.html">Read the article</a> · '
              '<a href="brief.md">Markdown</a></p></footer>')
    return (f'{head}<main id="main"><article>{question}{body}{method_html(ctx)}{references_html(ctx)}'
            f'{evidence_templates(ctx)}</article></main>{footer}')


def references_md(ctx: Context) -> List[str]:
    if not ctx.order:
        return []
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
                  f"{english_text(source, 'note')} {len(source['selected'])} frames selected (sampled, not "
                  "exhaustive)."]
    lines += ["", "Limitations:", ""] + [f"- {inline_md(x, ctx)}" for x in ctx.article["limitations"]] + [""]
    return lines


def md_head(ctx: Context, title: str) -> List[str]:
    """Title, dek, and partial notice: the same opening, in the same order, as the HTML masthead."""
    article = ctx.article
    lines = [f"# {evidence.escape_markdown(title)}", "", f"*{inline_md(article['dek'], ctx)}*", ""]
    if article["status"] == "partial":
        lines += [f"> **Partial publication.** {evidence.escape_markdown(article['partial_reason'])}", ""]
    return lines


def render_article_md(ctx: Context) -> str:
    article = ctx.article
    ctx.start(article_cites(article))
    lines = md_head(ctx, article["title"]) + ["Sources:", "", *sources_md(ctx), ""]
    for section in article["sections"]:
        lines += [f"## {inline_md(section['heading'], ctx)}", ""] + blocks_md(section["blocks"], ctx)
    return "\n".join(lines + method_md(ctx) + references_md(ctx)) + "\n"


def render_brief_md(ctx: Context) -> str:
    article, brief = ctx.article, ctx.article["brief"]
    ctx.start(brief_cites(article))
    lines = md_head(ctx, f"Brief: {article['title']}") + ["Sources:", "", *sources_md(ctx), ""]
    if brief.get("question"):
        lines += [f"Question: {inline_md(brief['question'], ctx)}", ""]
    lines += ["## What the sources establish", ""]
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


def filter_bar(target: str, facets: List[Tuple[str, str, List[Tuple[str, str]]]], placeholder: str) -> str:
    selects = "".join(
        f'<label>{E(label)} <select data-facet="{name}" @change="apply()"><option value="">All</option>'
        + "".join(f'<option value="{E(v)}">{E(t)}</option>' for v, t in options) + "</select></label>"
        for name, label, options in facets)
    return (f'<div class="filter-bar js-only" x-data="filter(\'{target}\')" role="search">'
            f'<label>Filter <input type="search" x-model="q" @input="apply()" placeholder="{E(placeholder)}" '
            f'autocomplete="off"></label>{selects}'
            f'<span class="filter-count" role="status" aria-live="polite" x-text="summary"></span></div>')


def reel_facet(ctx: Context) -> List[Tuple[str, str, List[Tuple[str, str]]]]:
    if len(ctx.sources) < 2:
        return []
    return [("reel", "Reel", [(s["reel"], f"Reel {s['reel']}") for s in ctx.sources.values()])]


# --- Cover -------------------------------------------------------------------


def brief_counts(ctx: Context) -> str:
    brief = ctx.article["brief"]
    parts = [f"{sum(1 for i in brief['evidence'] if i['kind'] == k)} {label.lower()}"
             for k, label in EVIDENCE_KINDS.items()]
    return ", ".join(parts) + f", {len(brief['proposals'])} proposal{'s' if len(brief['proposals']) != 1 else ''}"


def render_cover(ctx: Context) -> Tuple[str, str]:
    article = ctx.article
    order = article_cites(article)  # the tape maps tick every moment the article cites
    ctx.start(text_cites(article["dek"]))
    head = masthead(ctx, eyebrow(ctx), article["title"], article["dek"], moments_from=order)
    sections = "".join(f'<li><a href="article.html#s-{E(s["id"])}">{E(plain(s["heading"]))}</a></li>'
                       for s in article["sections"])
    reels = "".join(f'<li>Reel {s["reel"]}: <a href="transcript-{E(s["id"])}.html">English</a> · '
                    f'<a href="transcript-{E(s["id"])}.original.html">Original ({E(s["language"])})</a></li>'
                    for s in ctx.sources.values())
    web = sum(1 for c in ctx.citations.values() if c["kind"] == "web")
    cards = [
        ("article.html", "Article", f"{len(article['sections'])} section{'s' if len(article['sections']) != 1 else ''}"
         f", {len(article['figures'])} figure{'s' if len(article['figures']) != 1 else ''}.", f"<ol>{sections}</ol>"),
        ("brief.html", "Research brief", brief_counts(ctx) + ". Evidence and proposals are kept apart.", ""),
        ("transcripts.html", "Transcripts", "Complete original-language and English transcripts with timestamps, "
         "gaps, and uncertainty.", f"<ul>{reels}</ul>"),
        ("gallery.html", "Gallery", f"{len(ctx.gallery)} image{'s' if len(ctx.gallery) != 1 else ''}, each with "
         "its provenance.", ""),
        ("glossary.html", "Glossary", f"{len(ctx.terms)} term{'s' if len(ctx.terms) != 1 else ''}.", ""),
        ("references.html", "References", f"{len(ctx.sources)} source video{'s' if len(ctx.sources) != 1 else ''}, "
         f"{len(ctx.citations)} citation{'s' if len(ctx.citations) != 1 else ''} ({web} external), visual credits.",
         ""),
    ]
    items = "".join(f'<li class="card reveal"><h3><a href="{href}">{E(name)}</a></h3><p>{E(text)}</p>{extra}</li>'
                    for href, name, text, extra in cards)
    body = (f'{head}<main id="main"><p class="start"><a class="start-link" href="article.html">Start reading the '
            f'article</a></p><section class="contents" aria-labelledby="h-contents"><h2 id="h-contents">In this '
            f'publication</h2><ul class="cards">{items}</ul></section>{cited_tail(ctx)}</main>')
    md = md_head(ctx, article["title"])
    md += [eyebrow(ctx) + ".", "", "Sources:", "", *sources_md(ctx), "", "## In this publication", ""]
    for href, name, text, _ in cards:
        md.append(f"- [{name}]({href}): {evidence.escape_markdown(text)}")
        if href == "article.html":
            md += [f"  - [{evidence.escape_markdown(plain(s['heading']))}](article.html#s-{s['id']})"
                   for s in article["sections"]]
        if href == "transcripts.html":
            md += [f"  - Reel {s['reel']}: [English](transcript-{s['id']}.html) · "
                   f"[Original ({evidence.escape_markdown(s['language'])})](transcript-{s['id']}.original.html)"
                   for s in ctx.sources.values()]
    md += [""] + references_md(ctx)
    return body, "\n".join(md).rstrip("\n") + "\n"


# --- Transcripts ---------------------------------------------------------------


def transcript_markdown(source: Dict[str, Any], original: bool) -> str:
    """The verified evidence Markdown, with frame links pointed at the copied dist/media files."""
    text = source["original_md" if original else "english_md"]
    for frame_id, frame in (source["frames"] or {}).items():
        full, thumb = frame_media(source["id"], frame_id)
        text = text.replace(f"](../{frame['thumbnail']})", f"]({thumb})").replace(f"](../{frame['path']})",
                                                                                f"]({full})")
    return text if text.endswith("\n") else text + "\n"


def render_transcripts_index(ctx: Context) -> Tuple[str, str]:
    cards, md = [], ["# Transcripts", "", "Complete transcripts for every source video. English is labeled as verbatim "
                     "original English, cleaned English, or a translation; the original-language transcript is "
                     "verbatim.", ""]
    for source in ctx.sources.values():
        coverage = source["coverage"]
        gaps = len(coverage["gaps"])
        uncertain = len(coverage["uncertain_segment_ids"])
        english = english_text(source, "title")
        stats = (f"{coverage['segment_count']} segments · {coverage['covered_seconds']:.0f} s covered · {gaps} gap"
                 f"{'s' if gaps != 1 else ''} · {uncertain} uncertain segment{'s' if uncertain != 1 else ''} · "
                 f"language {source['language']} · provider {source['provider_kind']}")
        cards.append(f'<li class="card reveal" id="reel-{E(source["id"])}"><p class="slug">Reel {source["reel"]} · '
                     f'{E(source["creator"])}</p><h3>{E(source["title"])}</h3><p>{E(stats)}</p><ul>'
                     f'<li><a href="transcript-{E(source["id"])}.html">{E(english)}</a></li>'
                     f'<li><a href="transcript-{E(source["id"])}.original.html">Original transcript '
                     f'({E(source["language"])})</a></li><li><a href="{E(evidence.timestamp_url(source["youtube_id"], 0))}" '
                     f'rel="noopener noreferrer">Watch on YouTube</a></li></ul></li>')
        md += [f"## Reel {source['reel']}: {evidence.escape_markdown(source['title'])}", "",
               f"{evidence.escape_markdown(stats)}.", "",
               f"- [{english}](transcript-{source['id']}.html)",
               f"- [Original transcript ({evidence.escape_markdown(source['language'])})]"
               f"(transcript-{source['id']}.original.html)",
               f"- <{evidence.timestamp_url(source['youtube_id'], 0)}>", ""]
    head = masthead(ctx, eyebrow(ctx), "Transcripts", E("Every word that was transcribed, with its timing, gaps, and "
                                                        "uncertainty."), compact=True)
    body = f'{head}<main id="main" class="sheet"><ul class="cards">{"".join(cards)}</ul></main>'
    return body, "\n".join(md).rstrip("\n") + "\n"


def render_transcript_page(ctx: Context, source: Dict[str, Any], original: bool) -> str:
    language = lang_code(source["language"])
    field = "text" if original else "english"
    kind = f"Original transcript ({source['language']})" if original else english_text(source, "title")
    starts = [s["start"] for s in source["segments"].values()]
    attached: Dict[int, List[Tuple[str, Dict[str, Any]]]] = {}
    if not original:
        for (video_id, frame_id), frame in ctx.media.items():
            if video_id == source["id"] and frame_id in source["selected"]:
                index = max(sum(1 for s in starts if s <= frame["t"]) - 1, 0)
                attached.setdefault(index, []).append((frame_id, frame))
    gaps = list(source["coverage"]["gaps"])
    items = []
    other = f'transcript-{source["id"]}{"" if original else ".original"}.html'
    for index, segment in enumerate(source["segments"].values()):
        while gaps and gaps[0]["start"] < segment["start"] + 1e-6 and gaps[0]["end"] <= segment["start"] + 1e-6:
            gap = gaps.pop(0)
            items.append(f'<li class="gap" data-filter-item data-uncertain="gap"><p><strong>Transcript gap</strong> '
                         f'{evidence.timestamp(gap["start"])}–{evidence.timestamp(gap["end"])}: no transcribed speech '
                         'over the 2 s threshold.</p></li>')
        uncertain = bool(segment.get("uncertain") or segment.get("inline_markers"))
        flag = (f'<p class="seg-flag"><strong>Uncertain:</strong> '
                f'{E(segment.get("uncertainty") or "contains inline uncertainty markers")}</p>' if uncertain else "")
        frames = "".join(
            f'<a class="seg-frame" href="{frame_media(source["id"], fid)[0]}"><img src="{frame_media(source["id"], fid)[1]}" '
            f'alt="Source frame {E(fid)} at {evidence.timestamp(frame["t"])}" loading="lazy"></a>'
            for fid, frame in sorted(attached.get(index, []), key=lambda x: x[1]["t"]))
        link = evidence.timestamp_url(source["youtube_id"], segment["start"])
        items.append(
            f'<li class="seg" id="seg-{E(segment["id"])}" data-filter-item data-uncertain="{str(uncertain).lower()}">'
            f'<p class="seg-meta"><a class="ts" href="{E(link)}" rel="noopener noreferrer">'
            f'{evidence.timestamp(segment["start"])}</a> <span class="seg-id">{E(segment["id"])}</span> '
            f'<a class="seg-other" href="{other}#seg-{E(segment["id"])}">{"English" if original else "Original"}</a></p>'
            f'<div class="seg-body"><p class="seg-text"{f" lang={language}" if original else ""}>{E(segment[field])}</p>'
            f'{flag}{f"<div class=seg-frames>{frames}</div>" if frames else ""}</div></li>')
    items += [f'<li class="gap" data-filter-item data-uncertain="gap"><p><strong>Transcript gap</strong> '
              f'{evidence.timestamp(g["start"])}–{evidence.timestamp(g["end"])}: no transcribed speech over the 2 s '
              'threshold.</p></li>' for g in gaps]
    note = "Verbatim original-language transcript." if original else english_text(source, "page")
    dek = (f'{E(note)} {len(source["segments"])} segments from Reel {source["reel"]}, '
           f'{E(source["creator"])}, provider {E(source["provider_kind"])}. '
           f'<a href="{other}">{"English transcript" if original else "Original transcript"}</a> · '
           f'<a href="{E(evidence.timestamp_url(source["youtube_id"], 0))}" rel="noopener noreferrer">YouTube</a>')
    head = masthead(ctx, f"Reel {source['reel']} · {kind}", source["title"], dek, compact=True)
    bar = filter_bar(f"seg-list", [("uncertain", "Show", [("true", "Uncertain segments"), ("false", "Certain segments"),
                                                          ("gap", "Gaps")])], "Words in this transcript")
    return (f'{head}<main id="main" class="sheet">{bar}<ol class="transcript" id="seg-list">{"".join(items)}</ol>'
            f'</main>')


# --- Gallery, glossary, references ------------------------------------------------


def provenance(item: Dict[str, Any], ctx: Context) -> Tuple[str, str]:
    """(slug HTML, plain Markdown) provenance for a gallery item."""
    if item["kind"] == "original":
        figure = item["figure"]
        derived = ""
        if figure.get("derived_from"):
            d = figure["derived_from"]
            source = ctx.sources[d["video_id"]]
            t = source["frames"][d["frame_id"]]["t"]
            derived = f"; annotated from Reel {source['reel']} {evidence.timestamp(t)} ({d['frame_id']})"
        text = f"Fig. {item['number']} · Original figure by this publication, our reconstruction{derived}"
        return E(text), text
    source = ctx.sources[item["video_id"]]
    t = evidence.timestamp(item["t"])
    link = evidence.timestamp_url(source["youtube_id"], item["t"])
    what = {"capture": f"Fig. {item.get('number')} · Source capture",
            "sequence": f"Fig. {item.get('number')} · Demo step {item.get('step')} of {item.get('steps')}",
            "frame": "Selected source frame"}[item["kind"]]
    html_text = (f'{E(what)} · untouched · <a href="{E(link)}" rel="noopener noreferrer">Reel {source["reel"]} '
                 f'{t}</a> · {E(item["frame_id"])} · {E(source["creator"])}, “{E(source["title"])}”')
    md_text = (f"{what} · untouched · Reel {source['reel']} {t} ({item['frame_id']}) · {source['creator']}, "
               f"“{source['title']}” <{link}>")
    return html_text, md_text


def render_gallery(ctx: Context) -> Tuple[str, str]:
    ctx.start([c for item in ctx.gallery if item["caption"] for c in text_cites(item["caption"])])
    items, md = [], ["# Gallery", "", "Every image in this publication with its provenance. Source captures are "
                     "untouched frames; original figures are our reconstructions.", ""]
    for index, item in enumerate(ctx.gallery):
        prov_html, prov_md = provenance(item, ctx)
        caption = inline_html(item["caption"], ctx, []) if item["caption"] else ""
        mat = "g-original" if item["kind"] == "original" else "g-capture"
        items.append(
            f'<li class="g-item reveal {mat}" id="{item["id"]}" data-filter-item data-kind="{item["kind"]}" '
            f'data-reel="{item.get("reel", "")}"><figure><a class="g-open" href="{E(item["src"])}" data-index="{index}">'
            f'<img src="{E(item["thumb"])}" alt="{E(item["alt"])}" loading="lazy"></a>'
            f'<figcaption><span class="slug">{prov_html}</span> {caption}</figcaption></figure></li>')
        caption_md = (" " + inline_md(item["caption"], ctx)) if item["caption"] else ""
        md += [f"![{evidence.escape_markdown(item['alt'])}]({item['src']})", "",
               f"**{evidence.escape_markdown(prov_md)}.**{caption_md}", ""]
    kinds = [(k, label) for k, label in (("capture", "Source captures"), ("sequence", "Demo steps"),
                                         ("original", "Original figures"), ("frame", "Other selected frames"))
             if any(i["kind"] == k for i in ctx.gallery)]
    bar = filter_bar("gallery-list", [("kind", "Kind", kinds)] + reel_facet(ctx), "Captions and provenance")
    empty = "" if ctx.gallery else '<p>No images were placed or selected for this publication.</p>'
    viewer = ('<dialog class="viewer" x-ref="viewer" aria-labelledby="viewer-title" @keydown="key($event)" '
              '@close="closed()"><div class="viewer-bar"><h2 id="viewer-title" class="visually-hidden">Image viewer</h2>'
              '<button type="button" @click="prev()" aria-label="Previous image">Previous</button>'
              '<output class="viewer-count" aria-live="polite" x-text="(index + 1) + \' of \' + count"></output>'
              '<button type="button" @click="next()" aria-label="Next image">Next</button>'
              '<span class="viewer-gap"></span>'
              '<button type="button" @click="zoom(1 / 1.5)" aria-label="Zoom out">−</button>'
              '<output class="viewer-scale" x-text="Math.round(scale * 100) + \'%\'"></output>'
              '<button type="button" @click="zoom(1.5)" aria-label="Zoom in">+</button>'
              '<button type="button" @click="fit()">Fit</button>'
              '<button type="button" class="viewer-close" @click="close()">Close</button></div>'
              '<div class="viewer-stage" x-ref="stage" @pointerdown="down($event)" @pointermove="move($event)" '
              '@pointerup="up($event)" @pointercancel="up($event)" @wheel="wheel($event)" @dblclick="toggleZoom()">'
              '<img x-ref="image" alt="" draggable="false"></div>'
              '<div class="viewer-caption" x-ref="caption"></div>'
              '<p class="viewer-help">Arrow keys: previous and next (pan when zoomed) · + and −: zoom · 0: fit · '
              'drag to pan · swipe to change image · Esc: close</p></dialog>')
    head = masthead(ctx, eyebrow(ctx), "Gallery", E("Source captures, demo steps, original figures, and selected "
                                                    "frames, with provenance."), compact=True)
    body = (f'{head}<main id="main" class="sheet" x-data="gallery">{bar}{empty}<ol class="gallery" id="gallery-list" '
            f'@click="open($event)">{"".join(items)}</ol>{viewer}{cited_tail(ctx)}</main>')
    md += references_md(ctx)
    return body, "\n".join(md).rstrip("\n") + "\n"


def render_glossary(ctx: Context) -> Tuple[str, str]:
    ctx.start([c for term in ctx.terms for c in text_cites(term["definition"])])
    entries, md = [], ["# Glossary", ""]
    for term in ctx.terms:
        entries.append(f'<div class="term reveal" id="{E(term["anchor"])}" data-filter-item><dt>{E(term["term"])}</dt>'
                       f'<dd>{inline_html(term["definition"], ctx, [])}</dd></div>')
        md.append(f"- **{evidence.escape_markdown(term['term'])}**: {inline_md(term['definition'], ctx)}")
    if not entries:
        md.append("No glossary terms were defined for this publication.")
    md.append("")
    bar = filter_bar("glossary-list", [], "Terms and definitions") if entries else ""
    listing = (f'<dl class="glossary" id="glossary-list">{"".join(entries)}</dl>' if entries else
               '<p>No glossary terms were defined for this publication.</p>')
    head = masthead(ctx, eyebrow(ctx), "Glossary", E("Short definitions of the terms this publication relies on."),
                    compact=True)
    body = f'{head}<main id="main" class="sheet">{bar}{listing}{cited_tail(ctx)}</main>'
    md += references_md(ctx)
    return body, "\n".join(md).rstrip("\n") + "\n"


SOFTWARE = (
    ("Alpine.js 3.17.4", "MIT", "assets/vendor/LICENSE-alpinejs.md", "https://alpinejs.dev"),
    ("GSAP 3.15.0 (core)", "Standard “No Charge” GSAP License", "assets/vendor/LICENSE-gsap.md", "https://gsap.com"),
)


def render_references(ctx: Context) -> Tuple[str, str]:
    ctx.start([])
    sources, md = [], ["# References", "", "## Original videos", ""]
    for source in ctx.sources.values():
        url = evidence.timestamp_url(source["youtube_id"], 0)
        meta = " · ".join([source["creator"], evidence.timestamp(source["duration"] or 0), source["language"]])
        sources.append(f'<li id="src-{E(source["id"])}" data-filter-item data-kind="video">Reel {source["reel"]}: '
                       f'“{E(source["title"])}”, {E(meta)}. <a class="url" href="{E(url)}" rel="noopener noreferrer">'
                       f'{E(url)}</a> · <a href="transcript-{E(source["id"])}.html">English transcript</a> · '
                       f'<a href="transcript-{E(source["id"])}.original.html">Original transcript</a></li>')
        md.append(f"- Reel {source['reel']}: “{evidence.escape_markdown(source['title'])}”, "
                  f"{evidence.escape_markdown(meta)}. <{url}>")
    cites, web = [], []
    md += ["", "## Video citations", ""]
    for cid, c in ctx.citations.items():
        note = f" {E(c['note'])}" if c.get("note") else ""
        item = (f'<li id="cite-{E(cid)}" data-filter-item data-kind="{"web" if c["kind"] == "web" else "cite"}">'
                f'<span class="ev-id">{E(cid)}</span> {E(c["label"])}.{note} <a class="url" href="{E(c["url"])}" '
                f'rel="noopener noreferrer">{E(c["url"])}</a></li>')
        line = (f"- **{evidence.escape_markdown(cid)}** {evidence.escape_markdown(c['label'])}."
                f"{' ' + evidence.escape_markdown(c['note']) if c.get('note') else ''} <{c['url']}>")
        (web if c["kind"] == "web" else cites).append((item, line))
    md += [line for _, line in cites] or ["None."]
    md += ["", "## External sources", ""] + ([line for _, line in web] or ["None."])
    credits = []
    md += ["", "## Visual credits", ""]
    for item in ctx.gallery:
        _, prov_md = provenance(item, ctx)
        prov_html, _ = provenance(item, ctx)
        credits.append(f'<li id="credit-{item["id"]}" data-filter-item data-kind="visual"><a href="gallery.html#'
                       f'{item["id"]}">{E(item["id"].upper())}</a> {prov_html}</li>')
        md.append(f"- {item['id'].upper()}: {evidence.escape_markdown(prov_md)}")
    if not credits:
        md.append("None.")
    software = [f'<li data-filter-item data-kind="software">{E(name)}, {E(lic)}. <a href="{path}">License and '
                f'provenance</a> · <a class="url" href="{url}" rel="noopener noreferrer">{url}</a></li>'
                for name, lic, path, url in SOFTWARE]
    families = sorted({themes.FAMILIES[v["family"]]["name"] for v in themes.VARIANTS if v["family"] != "house"})
    software.append(f'<li data-filter-item data-kind="software">Reader themes adapted from the original palettes of '
                    f'{E(", ".join(families))}. <a href="assets/THEMES.md">Sources, licenses, and contrast '
                    'adaptations</a></li>')
    md += ["", "## Software and themes", ""]
    md += [f"- {name}, {lic}. [License and provenance]({path}) <{url}>" for name, lic, path, url in SOFTWARE]
    md += [f"- Reader themes adapted from the original palettes of {', '.join(families)}. "
           "[Sources, licenses, and contrast adaptations](assets/THEMES.md)", ""]
    kinds = [("video", "Original videos"), ("cite", "Video citations"), ("web", "External sources"),
             ("visual", "Visual credits"), ("software", "Software and themes")]
    bar = filter_bar("reference-list", [("kind", "Kind", kinds)], "Titles, creators, URLs")

    def block(id_: str, heading: str, rows: List[str]) -> str:
        return (f'<section class="ref-block" id="{id_}" aria-labelledby="h-{id_}"><h2 id="h-{id_}">{heading}</h2>'
                f'<ol>{"".join(rows) or "<li>None.</li>"}</ol></section>')

    head = masthead(ctx, eyebrow(ctx), "References", E("Original videos, every citation, visual credits, and bundled "
                                                       "software."), compact=True)
    body = (f'{head}<main id="main" class="sheet">{bar}<div id="reference-list" class="references-page">'
            f'{block("sources", "Original videos", sources)}'
            f'{block("citations", "Video citations", [i for i, _ in cites])}'
            f'{block("external", "External sources", [i for i, _ in web])}'
            f'{block("credits", "Visual credits", credits)}{block("software", "Software and themes", software)}'
            f'</div></main>')
    return body, "\n".join(md).rstrip("\n") + "\n"


# --- Search index ---------------------------------------------------------------


def blocks_text(blocks: List[Dict[str, Any]], ctx: Context) -> List[str]:
    out = []
    for block in blocks:
        if block["type"] == "p":
            out.append(plain(block["text"]))
        elif block["type"] == "list":
            out += [plain(i) for i in block["items"]]
        elif block["type"] == "quote":
            out.append(block["text"])
        elif block["type"] == "figure":
            figure = ctx.figures[block["figure"]]
            out.append(plain(figure["caption"]))
            out += [plain(s["caption"]) for s in figure.get("steps", [])]
            out += [plain(a) for a in figure.get("assumptions", [])]
        else:
            out.append(plain(block["summary"]))
            out += blocks_text(block["blocks"], ctx)
    return out


def search_index(ctx: Context) -> str:
    article = ctx.article
    entries: List[List[str]] = [["index.html#main", "Overview", article["title"], plain(article["dek"])]]
    for section in article["sections"]:
        entries.append([f"article.html#s-{section['id']}", "Article", plain(section["heading"]),
                        " ".join(blocks_text(section["blocks"], ctx))])
    entries.append(["article.html#method", "Article", "How this was made, and its limits",
                    " ".join(plain(x) for x in article["limitations"])])
    for item in article["brief"]["evidence"]:
        entries.append([f"brief.html#{item['id']}", "Brief", f"{item['id']} · {EVIDENCE_KINDS[item['kind']]}",
                        plain(item["text"])])
    for item in article["brief"]["proposals"]:
        entries.append([f"brief.html#{item['id']}", "Brief", f"{item['id']} · Proposal ({item['kind']})",
                        plain(item["text"]) + " " + plain(item.get("risks", ""))])
    for source in ctx.sources.values():
        for segment in source["segments"].values():
            stamp = evidence.timestamp(segment["start"])
            entries.append([f"transcript-{source['id']}.html#seg-{segment['id']}", f"Reel {source['reel']} English",
                            f"{stamp} · {segment['id']}", segment["english"]])
            if _normalize(segment["text"]) != _normalize(segment["english"]):
                entries.append([f"transcript-{source['id']}.original.html#seg-{segment['id']}",
                                f"Reel {source['reel']} Original", f"{stamp} · {segment['id']}", segment["text"]])
    for item in ctx.gallery:
        entries.append([f"gallery.html#{item['id']}", "Gallery", provenance(item, ctx)[1],
                        f"{item['alt']} {plain(item['caption'] or '')}"])
    for term in ctx.terms:
        entries.append([f"glossary.html#{term['anchor']}", "Glossary", term["term"], plain(term["definition"])])
    for source in ctx.sources.values():
        entries.append([f"references.html#src-{source['id']}", "References", f"Reel {source['reel']}: {source['title']}",
                        source["creator"]])
    for cid, c in ctx.citations.items():
        entries.append([f"references.html#cite-{cid}", "References", c["label"], c.get("note") or ""])
    entries = [[re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", field)).strip() for field in entry]
               for entry in entries]
    payload = json.dumps({"version": 1, "entries": entries}, ensure_ascii=True, separators=(",", ":"))
    # Data, not markup: keep "</script" and other HTML-significant characters out of the file entirely.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return ("// Generated offline search index for this publication. Loaded with <script src>; never fetched.\n"
            f"window.DISTILL_SEARCH = {payload};\n")


# --- All pages ------------------------------------------------------------------


def render_documents(ctx: Context) -> Dict[str, str]:
    """Every HTML page and its Markdown twin, plus the search index."""
    title = ctx.article["title"]
    out: Dict[str, str] = {}

    def add(name: str, body: str, md: str, page_title: str, kind: str, current: str, head: str = "") -> None:
        md_name = name[:-5] + ".md"
        md = normalize_markdown(md)
        out[md_name] = md
        out[name] = page(ctx, page_title, body, kind, md_name, md, current, head)

    body, md = render_cover(ctx)
    add("index.html", body, md, title, "cover", "overview")
    add("article.html", article_body(ctx), render_article_md(ctx), title, "article", "article", seo_head(ctx))
    add("brief.html", brief_body(ctx), render_brief_md(ctx), f"Brief: {title}", "brief", "brief")
    body, md = render_transcripts_index(ctx)
    add("transcripts.html", body, md, f"Transcripts · {title}", "transcripts", "transcripts")
    for source in ctx.sources.values():
        for original in (False, True):
            name = f"transcript-{source['id']}{'.original' if original else ''}.html"
            label = "Original transcript" if original else "English transcript"
            add(name, render_transcript_page(ctx, source, original), transcript_markdown(source, original),
                f"Reel {source['reel']} {label} · {title}", "transcript", "transcripts")
    body, md = render_gallery(ctx)
    add("gallery.html", body, md, f"Gallery · {title}", "gallery", "gallery")
    body, md = render_glossary(ctx)
    add("glossary.html", body, md, f"Glossary · {title}", "glossary", "glossary")
    body, md = render_references(ctx)
    add("references.html", body, md, f"References · {title}", "references", "references")
    out["assets/search-index.js"] = search_index(ctx)
    return out


LINK = re.compile(r'\s(?:href|src)="([^"]*)"')
CANONICAL_LINK = re.compile(r'<link rel="canonical" href="https://[^"<>]*">')
MD_LINK = re.compile(r"(?<!\\)\]\(([^)\s]+)\)")
IDS = re.compile(r'\sid="([^"]+)"')
TEXTAREA = re.compile(r'<textarea id="page-markdown"[^>]*>(.*?)</textarea>', re.S)
UNSTABLE_CONTROLS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalize_markdown(text: str) -> str:
    """Markdown in the form a browser keeps in a textarea: LF line endings, and NUL and other C0 controls
    (except tab and LF) replaced by U+FFFD. The .md twin, the embedded text, and Copy Page then agree byte for
    byte; HTML parsing would otherwise turn CR into LF and NUL into U+FFFD in the embedded copy only."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return UNSTABLE_CONTROLS.sub("\ufffd", text)


def embedded_markdown(page_html: str) -> Optional[str]:
    """The textarea value a browser would build from a page: entities decoded, one leading LF dropped, CR
    normalized to LF, and NUL replaced (HTML parsing rules for RCDATA)."""
    match = TEXTAREA.search(page_html)
    if not match:
        return None
    value = html.unescape(match.group(1)).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd")
    return value[1:] if value.startswith("\n") else value


def markdown_problems(documents: Dict[str, str]) -> List[str]:
    """Every page must embed exactly its .md twin, as the browser will parse it."""
    problems = []
    for name in sorted(n for n in documents if n.endswith(".html")):
        md_name = name[:-5] + ".md"
        if embedded_markdown(documents[name]) != documents.get(md_name):
            problems.append(f"{name} does not embed exactly {md_name}; Copy Page and the download would differ")
    return problems


def link_problems(root: Path, names: List[str], later: Tuple[str, ...] = tuple(LATER_OUTPUTS)) -> List[str]:
    """Every local link in HTML (href/src) and Markdown (](target)) must resolve to a file under root, and
    every #fragment on an HTML target to an id. Files in `later` (written after render) may be missing."""
    problems = []
    pages = sorted({n for n in names if n.endswith(".html")} |
                   {p.relative_to(root).as_posix() for p in root.glob("*.html")})
    ids = {name: set(map(html.unescape, IDS.findall((root / name).read_text()))) for name in pages}
    for name in names:
        text = (root / name).read_text()
        markdown = name.endswith(".md")
        for raw in (MD_LINK if markdown else LINK).findall(text):
            target = raw if markdown else html.unescape(raw)
            if markdown and target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if re.match(r"^(?:https?:|mailto:)", target, re.I):
                continue
            path, _, fragment = target.partition("#")
            if path and re.match(r"^[a-z][a-z0-9+.-]*:|^/|(?:^|/)\.\.(?:/|$)", path, re.I):
                problems.append(f"{name} links outside the package: {target}")
                continue
            if path and path not in later and not (root / path).is_file():
                problems.append(f"{name} links to a missing file: {target}")
            elif fragment and (path or name) in ids and fragment not in ids[path or name]:
                problems.append(f"{name} links to a missing anchor: {target}")
    return problems


def coverage_report(ctx: Context, warnings: List[str], narrative: Dict[str, Any]) -> Dict[str, Any]:
    article_used = article_cites(ctx.article)
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
            "narrative": narrative, "limitations": article["limitations"], "warnings": warnings}


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
    try:
        json.dumps(article, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        raise ContractError("article.json contains an unpaired surrogate escape (such as \\ud800); "
                            "text must be valid Unicode") from None
    sources, problems, inputs = load_sources(workspace, plan)
    if problems:
        raise ContractError(problems)
    inputs[f"publications/{plan['id']}/article.json"] = evidence.sha256_file(article_path)
    problems, warnings = check_article(article, plan, sources, pub_dir, inputs)
    if problems:
        raise ContractError(problems)
    narrative, narrative_warnings = narrative_gate(article)
    warnings += narrative_warnings
    ctx = Context(article, sources)
    documents = render_documents(ctx)
    documents["assets/themes.css"] = themes.css()
    documents["assets/THEMES.md"] = themes.provenance_md()
    html_names = sorted(n for n in documents if n.endswith(".html"))
    for name in html_names:
        # The validated canonical <link> names the hosted page; it is never fetched.
        if REMOTE_RESOURCE.search(CANONICAL_LINK.sub("", documents[name])):
            raise ContractError(f"{name} would load a remote resource; refusing to render")
    problems = markdown_problems(documents)
    if problems:
        raise ContractError(problems)
    page_names = html_names + sorted(n for n in documents if n.endswith(".md") and "/" not in n)
    partial = pub_dir / f".dist-partial-{os.getpid()}"
    if partial.exists():
        shutil.rmtree(partial)
    try:
        for name, text in documents.items():
            evidence.atomic_write_text(partial / name, text)
        evidence.atomic_write_json(partial / "coverage.json", coverage_report(ctx, warnings, narrative))
        for name in ASSET_FILES:
            target = partial / "assets" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ASSETS / name, target)
        for (video_id, frame_id), frame in ctx.media.items():
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
        problems = link_problems(partial, page_names)
        if problems:
            raise ContractError(problems)
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
          "files": sorted(outputs), "narrative": narrative, "warnings": warnings})
    return 0


def _verify_render(workspace: Workspace, plan: Dict[str, Any], pub_dir: Path) -> Dict[str, Any]:
    record = evidence.read_json(pub_dir / "render.json") if (pub_dir / "render.json").exists() else None
    if not record or not (pub_dir / "dist").is_dir():
        raise ContractError(f"publication {plan['id']} has not been rendered; run render first")
    if record.get("renderer") != RENDERER:
        raise ContractError("render predates current safety validation; rerun render before PDF or packaging")
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
    index = dist / PDF_PAGE
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
    record = {"schema_version": evidence.SCHEMA_VERSION, "page": PDF_PAGE, "page_sha256": evidence.sha256_file(index),
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
    # A pdf.json from renderer 1 (printed index.html, no page_sha256) is treated as stale.
    pdf_ok = bool(pdf_record and (dist / "article.pdf").is_file() and pdf_record.get("page") == PDF_PAGE
                  and (dist / PDF_PAGE).is_file()
                  and pdf_record.get("page_sha256") == evidence.sha256_file(dist / PDF_PAGE)
                  and pdf_record.get("pdf_sha256") == evidence.sha256_file(dist / "article.pdf"))
    if not pdf_ok:
        if not args.allow_missing_pdf:
            raise ContractError("PDF is missing or stale for the current render; run pdf, or pass "
                                "--allow-missing-pdf to build an explicitly incomplete package")
        reasons.append("PDF missing or stale for the current render")
    if article["status"] != "complete":
        reasons.append(f"article is partial: {article.get('partial_reason')}")
    else:
        narrative_gate(article)  # a render from an older renderer cannot package a too-short complete article
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
            if not pdf_ok and "/" not in rel and rel.endswith(".html"):
                # A draft package has no PDF: drop the link to it rather than ship a dead link.
                evidence.atomic_write_text(target, source.read_text(encoding="utf-8").replace(PDF_LINK, ""))
            else:
                shutil.copyfile(source, target)
        if problems:
            raise ContractError(problems)
        problems = link_problems(partial, sorted(p.name for p in partial.iterdir()
                                                 if p.is_file() and p.suffix in (".html", ".md")), later=())
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
    temp = pub_dir / f".{plan['id']}-{revision}.zip.tmp"
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as bundle:
        for rel in ["manifest.json"] + [f["path"] for f in files]:
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, (package / rel).read_bytes())
    # Readable name from the title; never overwrite a different ZIP (another revision) already using it.
    archive = None
    for name in package_zip_names(article.get("title"), plan["id"], revision):
        candidate = pub_dir / name
        if not candidate.exists() and not candidate.is_symlink():
            os.replace(temp, candidate)
            archive = candidate
            break
        if not candidate.is_symlink() and candidate.is_file() and candidate.read_bytes() == temp.read_bytes():
            temp.unlink()
            archive = candidate
            break
    if archive is None:
        temp.unlink()
        raise ContractError(f"every readable ZIP name for revision {revision} is taken by different bytes")
    emit({"status": "packaged", "publication": plan["id"], "revision": revision, "complete": not reasons,
          "incomplete_reasons": reasons, "package_dir": str(package), "manifest": str(package / "manifest.json"),
          "manifest_sha256": evidence.sha256_file(package / "manifest.json"), "zip": str(archive),
          "zip_sha256": evidence.sha256_file(archive), "files": len(files)})
    return 0


def register(subparsers: Any) -> None:
    render = subparsers.add_parser("render", help="render the offline site (cover, article, brief, transcripts, "
                                                  "gallery, glossary, references), Markdown twins, and coverage report")
    render.add_argument("--workspace", required=True)
    render.add_argument("--publication", required=True, help="publication id from the assignment")
    render.set_defaults(func=cmd_render)
    pdf = subparsers.add_parser("pdf", help="print the rendered article (article.html) to PDF with a headless "
                                            "Chromium browser")
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

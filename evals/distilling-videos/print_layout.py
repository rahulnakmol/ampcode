#!/usr/bin/env python3
"""Print-layout regression check for a rendered distilling-videos article PDF.

Flags two print defects seen in real batches:
- margin (rail) citations that overlap body text or cross into the reading column, as when a
  "Go deeper" details block gave its rail no width and the note wrapped word by word over the prose;
- headings (and "Go deeper" summaries) left at the bottom of a page, split from the text they introduce.

The geometry check is pure (`check_pages`) so it is unit-tested without a PDF library. Reading a PDF
needs PyMuPDF (`pip install pymupdf`); no network, no browser.

Usage: python3 evals/distilling-videos/print_layout.py ARTICLE.pdf [--captures DIR] [--dpi N]
Exit: 0 clean, 1 defects found, 3 PyMuPDF missing.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

TOL = 0.75  # points of overlap tolerated (anti-aliasing, superscript kerning)
SUMMARY_SLUG = "go deeper"


def _overlap(a, b) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > TOL and min(a[3], b[3]) - max(a[1], b[1]) > TOL


def body_metrics(pages: List[List[Dict[str, Any]]]) -> Dict[str, float]:
    """Body size and reading-column left edge, by character count over the whole document."""
    sizes: collections.Counter = collections.Counter()
    for spans in pages:
        for s in spans:
            sizes[round(s["size"], 1)] += len(s["text"].strip())
    body = sizes.most_common(1)[0][0] if sizes else 10.0
    lefts: collections.Counter = collections.Counter()
    for spans in pages:
        for s in spans:
            if round(s["size"], 1) == body:
                lefts[round(s["bbox"][0])] += 1
    return {"body_size": body, "column_left": float(lefts.most_common(1)[0][0]) if lefts else 0.0}


def check_pages(pages: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """pages: per page, spans {bbox: (x0, y0, x1, y1), size, text}. Returns defects (empty = clean)."""
    metrics = body_metrics(pages)
    body, left = metrics["body_size"], metrics["column_left"]
    defects = []
    for number, spans in enumerate(pages, 1):
        spans = [s for s in spans if s["text"].strip()]
        heading = [s for s in spans if s["size"] >= 1.5 * body]
        # The cover's eyebrow and headline hang across the rail by design.
        top = max((s["size"] for s in heading), default=0.0)
        masthead = max((s["bbox"][3] for s in heading if s["size"] == top), default=0.0) if number == 1 else 0.0
        rail = [s for s in spans if s["bbox"][0] < left - 4 and s not in heading and s["bbox"][3] > masthead]
        prose = [s for s in spans if s not in rail]
        for r in rail:
            hit = next((p for p in prose if _overlap(r["bbox"], p["bbox"])), None)
            if hit or r["bbox"][2] > left + TOL:
                defects.append({"page": number, "kind": "rail-overlap", "rail": r["text"].strip(),
                                "over": (hit or {}).get("text", "reading column").strip()[:60]})
        if number == 1 or not spans:
            continue  # the cover page has no flowing article text to keep with
        bottom = max(s["bbox"][3] for s in spans)
        last_line = [s for s in spans if s["bbox"][3] > bottom - 0.6 * body]
        lines = sorted({round(s["bbox"][1]) for s in spans})
        tail = [s for s in spans if round(s["bbox"][1]) in lines[-2:]]
        if any(s in heading for s in last_line):
            defects.append({"page": number, "kind": "heading-at-page-bottom",
                            "text": " ".join(s["text"].strip() for s in last_line if s in heading)[:80]})
        elif any(s["text"].strip().lower() == SUMMARY_SLUG for s in tail):
            defects.append({"page": number, "kind": "summary-at-page-bottom",
                            "text": " ".join(s["text"].strip() for s in tail)[:80]})
    return defects


def read_pdf(path: Path) -> List[List[Dict[str, Any]]]:
    import pymupdf  # noqa: PLC0415

    pages = []
    with pymupdf.open(path) as doc:
        for page in doc:
            spans = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for s in line["spans"]:
                        if s["text"].strip():
                            spans.append({"bbox": tuple(s["bbox"]), "size": s["size"], "text": s["text"]})
            pages.append(spans)
    return pages


def capture(path: Path, out: Path, dpi: int) -> List[str]:
    import pymupdf  # noqa: PLC0415

    out.mkdir(parents=True, exist_ok=True)
    written = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc, 1):
            target = out / f"print-p{index:02d}.png"
            page.get_pixmap(dpi=dpi).save(target)
            written.append(str(target))
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--captures", type=Path, help="also write one PNG per page here")
    parser.add_argument("--dpi", type=int, default=80)
    args = parser.parse_args(argv)
    try:
        pages = read_pdf(args.pdf)
    except ImportError:
        print("error: PyMuPDF is required (pip install pymupdf)", file=sys.stderr)
        return 3
    defects = check_pages(pages)
    result = {"pdf": str(args.pdf), "pages": len(pages), **body_metrics(pages), "defects": defects}
    if args.captures:
        result["captures"] = capture(args.pdf, args.captures, args.dpi)
    print(json.dumps(result, indent=2))
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())

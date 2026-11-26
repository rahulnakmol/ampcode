#!/usr/bin/env python3
"""Check this synthetic candidate corpus only; no worker execution or domain verdict."""

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
CASES = {
    "manufacturing": ("M", ["01-discovery.md", "02-kickoff.md", "03-proposal-closeout.md"], [5, 5, 5]),
    "service": ("S", ["01-intake.md", "02-correction.md"], [4, 4]),
    "finance": ("F", ["01-handover.md", "02-readiness.md"], [4, 4]),
    "presales": ("P", ["01-opportunity.md", "02-buying-update.md"], [4, 4]),
    "rfp": ("R", ["01-tender.md", "02-addendum.md"], [4, 4]),
}
SPAN = re.compile(r"\b[MSFPR]\d{2}\.[a-z]\b")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decimal_list(values):
    return [Decimal(value) for value in values]


def expression(node):
    if isinstance(node, str):
        return Decimal(node)
    op, *args = node
    values = [expression(arg) for arg in args]
    require(len(values) >= 2, "arithmetic needs at least two operands")
    if op == "+":
        return sum(values, Decimal(0))
    if op == "*":
        result = Decimal(1)
        for value in values:
            result *= value
        return result
    require(op in ("-", "/") and len(values) == 2, "unsupported arithmetic")
    return values[0] - values[1] if op == "-" else values[0] / values[1]


def check_arithmetic():
    data = json.loads((ROOT / "reviewer/numeric.json").read_text())
    ids = [item["id"] for group in ("estimates", "metrics") for item in data[group]]
    require(len(ids) == len(set(ids)), "duplicate numeric ID")
    for item in data["estimates"]:
        rows = [decimal_list(row) for row in item["rows"]]
        require(len(rows) == len(item["row_order"]), f"row labels: {item['id']}")
        for q, low, high, rate in rows:
            require(q > 0 and 0 <= low <= high and rate >= 0, f"invalid row: {item['id']}")
        days = [sum((row[0] * row[bound] for row in rows), Decimal(0)) for bound in (1, 2)]
        base = [sum((row[0] * row[bound] * row[3] for row in rows), Decimal(0)) for bound in (1, 2)]
        require(days == decimal_list(item["expected_days"]), f"effort: {item['id']}")
        require(base == decimal_list(item["expected_base"]), f"base: {item['id']}")
        if item["contingency_percent"] is None:
            require(item["expected_contingency"] is None and item["expected_total"] is None,
                    f"unsupplied contingency became a commitment: {item['id']}")
        else:
            contingency = [value * Decimal(item["contingency_percent"]) / 100 for value in base]
            total = [value + extra for value, extra in zip(base, contingency)]
            require(contingency == decimal_list(item["expected_contingency"]), f"contingency: {item['id']}")
            require(total == decimal_list(item["expected_total"]), f"total: {item['id']}")
    for item in data["metrics"]:
        require(expression(item["expression"]) == Decimal(item["expected"]), f"metric: {item['id']}")
    calendar = data["calendar"]
    zone = ZoneInfo(calendar["zone"])
    raised = datetime.fromisoformat(calendar["raised"]).replace(tzinfo=zone)
    due = raised + timedelta(days=1)
    while due.weekday() >= 5 or due.date().isoformat() in calendar["holidays"]:
        due += timedelta(days=1)
    require(due.isoformat() == calendar["expected_due"], "calendar due")
    require(due.astimezone(timezone.utc).isoformat() == calendar["expected_utc"], "calendar UTC")
    observed = datetime.fromisoformat(calendar["observed"]).replace(tzinfo=zone)
    require((observed - due).total_seconds() == calendar["expected_overdue_seconds"], "overdue age")
    routes = data["invoice_routes"]
    expected = ["department" if Decimal(v) <= Decimal(routes["inclusive_department_limit"]) else "director"
                for v in routes["invoices"]]
    require(expected == routes["expected"], "inclusive invoice routing")
    return len(data["estimates"]), len(data["metrics"])


def check_sources():
    spans = {}
    source_count = 0
    for case, (prefix, stages, counts) in CASES.items():
        directory = ROOT / "worker" / case
        require(sorted(p.name for p in directory.iterdir()) == sorted(["brief.md", *stages]),
                f"unexpected case file/stage: {case}")
        next_id = 1
        for stage_number, (filename, count) in enumerate(zip(stages, counts), 1):
            text = (directory / filename).read_text()
            ids = re.findall(r"^## ([MSFPR]\d{2}) —", text, re.MULTILINE)
            require(ids == [f"{prefix}{i:02d}" for i in range(next_id, next_id + count)],
                    f"source identity/order: {case}/{filename}")
            next_id += count
            source_count += count
            definitions = re.findall(r"^- ([MSFPR]\d{2}\.[a-z]):", text, re.MULTILINE)
            require(set(ref.split('.')[0] for ref in definitions) == set(ids), "source without spans")
            for ref in definitions:
                require(ref not in spans, f"duplicate span {ref}")
                spans[ref] = (case, stage_number)
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".json") and path != ROOT / "manifest.json":
            for ref in SPAN.findall(path.read_text()):
                require(ref in spans, f"unknown span {ref} in {path.relative_to(ROOT)}")
    answer_ids = []
    for line in (ROOT / "reviewer/answers.md").read_text().splitlines():
        if not re.match(r"^\| A[MSFPR]\d+ \|", line):
            continue
        answer_id, case, minimum, _topic, answer = [cell.strip() for cell in line.strip("|").split("|")]
        answer_ids.append(answer_id)
        require(case in CASES and 1 <= int(minimum) <= len(CASES[case][1]), f"bad answer stage {answer_id}")
        refs = SPAN.findall(answer)
        require(bool(refs), f"uncited answer {answer_id}")
        for ref in refs:
            source_case, stage = spans[ref]
            require(source_case == case and stage <= int(minimum), f"future/cross-case answer {answer_id}")
    require(len(answer_ids) == 36 and len(set(answer_ids)) == 36, "answer identity/count")
    return source_count, len(spans), len(answer_ids)


def snapshot():
    files = {}
    for path in sorted(ROOT.rglob("*")):
        require(not path.is_symlink(), f"symlink not permitted: {path}")
        if path.is_file() and path != ROOT / "manifest.json":
            files[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema": 1,
        "status": "candidate-2-development-initial-comparison-awaiting-re-review",
        "supersedes_manifest_sha256": "895084e98aae4bda6a7e86c7cb7a59f7009b9914e98a76b693ab41172633adcf",
        "design_sha256": "161cd1901c4ecd456bbc8394370c37c045470383f7eb168b892cfc2b23dd505e",
        "case_order": list(CASES),
        "stages": {case: stages for case, (_prefix, stages, _counts) in CASES.items()},
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="write candidate snapshot; NOT review acceptance")
    args = parser.parse_args()
    source_count, span_count, answer_count = check_sources()
    estimates, metrics = check_arithmetic()
    current = snapshot()
    manifest = ROOT / "manifest.json"
    if args.write_manifest:
        manifest.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    else:
        require(manifest.exists(), "missing manifest; candidate snapshot must be created explicitly")
        require(json.loads(manifest.read_text()) == current, "fixture drift; review before changing snapshot")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    print(f"PASS candidate identity: {len(current['files'])} files, 5 cases, {source_count} sources, "
          f"{span_count} spans, {answer_count} fixed answers")
    print(f"PASS arithmetic: {estimates} estimates, {metrics} metrics, calendar and invoice routing")
    print(f"Manifest SHA256 {digest}")
    print("NOT CHECKED: source entailment, independent review, domain correctness, native/UI/cloud checks or acceptance")


if __name__ == "__main__":
    main()

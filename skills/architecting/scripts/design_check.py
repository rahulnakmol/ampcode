#!/usr/bin/env python3
"""Check a technical design file against the architecting design format.

  python3 design_check.py design.md
  python3 design_check.py --help

Exits 0 and prints "pass" when the design follows rules D1 to D9. Otherwise exits 1 and prints
each problem as "<rule>: <what to fix>", one line per problem. Exits 2 on a usage error or an
unreadable file. Standard library only. The format, the rules and the accepted units are in
../reference/design-template.md.

  D1  an NFR target has no number
  D2  an NFR target has no number followed by an accepted unit outside its condition. A condition
      from "at", "when", "while", "with", "during", "given" or "under ... load" to its first number
      and unit is always set aside: "p95 under 300 at 50 req/s" and "Serve at 50 req/s" fail,
      "p95 under 300 ms at 50 req/s" passes. A condition from "for", "per", "across" or "over" to a
      rate or count is set aside only when a number stays outside it: "p95 under 300 for 50 req/s"
      fails; "Handle over 500 req/s" is checked whole and passes (so does "Fast for 50 req/s")
  D3  an NFR has no verification test (empty, or only placeholder words such as TBD, n/a, later)
  D4  an ADR lists fewer than two options (top-level items under Options; nested bullets do not count)
  D5  an ADR has no valid Status, no Decision or no Consequences
  D6  the design has no Contracts section, or it is empty
  D7  an NFR ID or an ADR ID appears twice
  D8  "Trust boundaries change:" is missing or not yes/no, or is yes without a threat-model path or link
  D9  structure: a required section, the NFR table or an ADR is missing or malformed, an NFR line
      (a line that starts with an NFR ID) sits anywhere outside the first NFR table, a line after
      that table in its section starts with | or names an NFR ID, or Mermaid is used

The check proves the design is complete and consistent. It cannot prove that a target is right,
that a test was run, or that a threat model is adequate.
"""

import re
import sys
from pathlib import Path

REQUIRED = ("Context", "Containers", "Decisions", "Non-functional requirements")
NFR_HEADER = ("id", "quality", "target", "verification")
STATUSES = ("proposed", "accepted", "rejected", "deprecated", "superseded")
# Rates and counts: the units of a load or a scope ("for 50 req/s", "across 10,000 tenants").
LOAD_UNITS = (
    # rate
    "req/s", "req/min", "rps", "rpm", "qps", "tps", "msg/s", "events/s", "errors/min", "errors/h",
    # count
    "users", "sessions", "tenants", "connections", "requests", "messages", "events", "records", "rows",
    "items", "files", "violations", "incidents", "findings", "defects", "errors",
)
UNITS = (
    # time
    "ms", "s", "sec", "seconds", "min", "minutes", "h", "hours", "d", "days", "weeks", "months", "years",
    # share
    "%",
    *LOAD_UNITS,
    # size and bandwidth
    "KB", "MB", "GB", "TB", "PB", "KiB", "MiB", "GiB", "TiB", "Mbps", "Gbps", "MB/s", "GB/s",
    # money
    "USD", "EUR", "GBP",
)
NUMBER = r"(?<![\w.])\d[\d,]*(?:\.\d+)?"
MULTIPLIER = r"(?:\s*(?:k|thousand|million|billion))?"


def measure(units):
    alternatives = "|".join(re.escape(u) for u in sorted(units, key=len, reverse=True))
    return rf"{NUMBER}{MULTIPLIER}\s*(?:{alternatives})(?![A-Za-z0-9])"


MEASURE = re.compile(measure(UNITS), re.I)
EMPTY = re.compile(r"(?:<[^<>]*>)?")
PLACEHOLDERS = ("tbd", "todo", "tbc", "na", "none", "later", "notyet", "pending")
LINK = re.compile(r"https?://\S+|\]\([^()\s]+\)|^[^\s<>]+[./][^\s<>]+$")
FIELD = re.compile(r"^\*{0,2}(Status|Options|Decision|Consequences):\*{0,2}[ \t]*(.*)$")
ITEM = re.compile(r"^([ \t]*)(?:[-*+]|\d+[.)])[ \t]+\S")
SEPARATOR = re.compile(r"^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-*:?\s*$")
# A condition runs from its word to its first number, which carries a unit: "at 50 req/s",
# "when 10,000 users". "Recall at 10" is no condition, because 10 has no unit. CONDITION is always
# set aside. COMPARATOR ("for", "per", "across", "over") counts only before a load or scope unit:
# "for 50 req/s" is a condition, "kept for 30 days" is the target.
CONDITION = re.compile(r"\b(?:at(?!\s+(?:most|least)\b)|when|while|with|during|given|under\s+(?:\w+\s+)?load)\b"
                       r"[^,;\d]*?" + MEASURE.pattern, re.I)
COMPARATOR = re.compile(r"\b(?:for|per|across|over)\b[^,;\d]*?" + measure(LOAD_UNITS), re.I)
# An NFR line starts with an NFR ID, after any table bar, list marker, heading mark or emphasis.
NFR_LINE = re.compile(r"^[\s|>#*_+`-]*(?:\d+[.)]\s+)?[*_`]*NFR-\d+\b")


def sections(text):
    """{lowercase title: [bodies]} for every '## ' heading."""
    found = {}
    for title, body in re.findall(r"^## (.+?)[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        found.setdefault(title.strip().lower(), []).append(body)
    return found


def blank(value):
    """True for an empty value or one made only of placeholder words, such as '**TBD/later.**'."""
    value = re.sub(r"[*`_~\[\]()]", "", value).strip().rstrip(".,;:!?").strip()
    if EMPTY.fullmatch(value):
        return True
    value = re.sub(r"\bn[/.]a\b\.?", "na", value.lower())
    value = re.sub(r"\bto[\s/]*do\b", "todo", value)
    value = re.sub(r"\bnot[\s/]+yet\b", "notyet", value)
    words = [w.strip(".,;:!?") for w in re.split(r"[\s/,;]+", value)]
    return all(w in PLACEHOLDERS or re.fullmatch(r"-+|—|\?+|", w) for w in words)


def target_part(target):
    """The part of a target that needs its own unit (D2). The at/when/... conditions are always
    removed ("Serve at 50 req/s" keeps no measure). The for/per/across/over conditions are removed
    too when a number stays outside them ("p95 under 300 for 50 req/s"); otherwise they stay
    ("Handle over 500 req/s")."""
    rest = CONDITION.sub("", target)
    outside = COMPARATOR.sub("", rest)
    return outside if re.search(NUMBER, outside) else rest


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def check_nfrs(body, add):
    lines = body.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if l.strip().startswith("|") and [c.lower() for c in cells(l)] == list(NFR_HEADER)), None)
    if start is None:
        add("D9", "Non-functional requirements needs a table with headers ID | Quality | Target | Verification")
        return
    seen, count, end = set(), 0, len(lines)
    for index, line in enumerate(lines[start + 1:], start + 1):
        if not line.strip().startswith("|"):
            end = index
            break
        if SEPARATOR.match(line.strip()):
            continue
        row = cells(line)
        count += 1
        if len(row) != 4:
            add("D9", f"NFR row '{row[0]}' needs four cells: ID | Quality | Target | Verification")
            continue
        nid, _, target, verification = row
        if not re.fullmatch(r"NFR-\d+", nid):
            add("D9", f"NFR ID '{nid}' must look like NFR-1")
        elif nid in seen:
            add("D7", f"{nid} appears twice; give each NFR its own ID and never reuse one")
        seen.add(nid)
        if not re.search(r"\d", target):
            add("D1", f"{nid} target '{target}' has no number")
        elif not MEASURE.search(target_part(target)):
            add("D2", f"{nid} target '{target}' has no number with an accepted unit outside its condition"
                " (see design-template.md)")
        if blank(verification):
            add("D3", f"{nid} has no verification test")
    if not count:
        add("D9", "Non-functional requirements needs at least one NFR row")
    for line in lines[:start]:
        if NFR_LINE.match(line):
            add("D9", f"'{line.strip()[:60]}' is outside the NFR table; keep every NFR in the one table")
    for line in lines[end:]:
        if line.strip().startswith("|") or re.search(r"NFR-\d+", line):
            add("D9", f"'{line.strip()[:60]}' is outside the NFR table; keep every NFR in the one table")


def fields(block):
    """{field: (same-line value, continuation lines)} for an ADR block."""
    found, name = {}, None
    for line in block.splitlines():
        match = FIELD.match(line)
        if match:
            name = match.group(1)
            found[name] = (match.group(2).strip(), [])
        elif name:
            found[name][1].append(line)
    return found


def check_adrs(body, add):
    blocks = re.findall(r"^### (.+?)[ \t]*\n(.*?)(?=^### |\Z)", body, re.M | re.S)
    if not blocks:
        add("D9", "Decisions needs at least one '### ADR-1: <title>' section")
    seen = set()
    for heading, block in blocks:
        match = re.match(r"(ADR-\d+):\s*\S", heading)
        if not match:
            add("D9", f"ADR heading '{heading}' must look like 'ADR-1: <title>'")
            continue
        aid = match.group(1)
        if aid in seen:
            add("D7", f"{aid} appears twice; give each ADR its own ID and never reuse one")
        seen.add(aid)
        found = fields(block)
        # Count only the first run of list items after Options: and only its shallowest items, so
        # nested pro and con bullets, or a later list under another label, are not options.
        run = []
        for line in found.get("Options", ("", []))[1]:
            if not line.strip():
                if run:
                    run.append(line)
                continue
            if ITEM.match(line) or (run and line[:1] in " \t"):
                run.append(line)
            elif run or line.strip():
                break
        indents = [len(m.group(1).expandtabs(4)) for m in map(ITEM.match, run) if m]
        options = indents.count(min(indents)) if indents else 0
        if options < 2:
            add("D4", f"{aid} lists {options} option(s) under Options; list at least two")
        status = found.get("Status", ("", []))[0].split()
        if not status or status[0].lower().rstrip(".") not in STATUSES:
            add("D5", f"{aid} needs Status: one of {', '.join(STATUSES)}")
        for name in ("Decision", "Consequences"):
            value, more = found.get(name, ("", []))
            if blank(value) and all(blank(l) for l in more):
                add("D5", f"{aid} needs {name}")


def check(text):
    problems = []

    def add(rule, message):
        problems.append(f"{rule}: {message}")

    found = sections(text.replace("\r\n", "\n"))
    if re.search(r"^[ \t>]*(?:`{3,}|~{3,})[ \t]*mermaid", text, re.M | re.I):
        add("D9", "use text tables or square-corner text diagrams, not Mermaid")
    for title in REQUIRED:
        bodies = found.get(title.lower(), [])
        if len(bodies) != 1 or not bodies[0].strip():
            add("D9", f"needs exactly one non-empty '## {title}' section")
    contracts = found.get("contracts", [])
    if len(contracts) != 1 or not contracts[0].strip():
        add("D6", "needs one '## Contracts' section naming each interface and data contract")
    if len(found.get("non-functional requirements", [])) == 1:
        check_nfrs(found["non-functional requirements"][0], add)
    title = None
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().lower()
        elif title != "non-functional requirements" and NFR_LINE.match(line):
            add("D9", f"'{line.strip()[:60]}' is outside the NFR table; keep every NFR in the one table")
    if len(found.get("decisions", [])) == 1:
        check_adrs(found["decisions"][0], add)

    trust = re.findall(r"^\*{0,2}Trust boundaries change:\*{0,2}[ \t]*(.*)$", text, re.M)
    model = re.findall(r"^\*{0,2}Threat model:\*{0,2}[ \t]*(.*)$", text, re.M)
    if len(trust) != 1 or trust[0].strip().lower() not in ("yes", "no"):
        add("D8", "needs one line 'Trust boundaries change: yes' or '... no'")
    elif trust[0].strip().lower() == "yes":
        value = model[0].strip() if len(model) == 1 else ""
        if blank(value) or not LINK.search(value):
            add("D8", "trust boundaries change, so 'Threat model:' needs a path or link to the threat model")
    return problems


def main(argv):
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(argv) != 2:
        print("usage: design_check.py design.md")
        return 2
    try:
        text = Path(argv[1]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"error: cannot read {argv[1]}: {error}")
        return 2
    problems = check(text)
    print("\n".join(problems) if problems else "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

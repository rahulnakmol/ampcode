#!/usr/bin/env python3
"""Check a steering log (risks, issues, decisions, guardrails) and a five-line status.

  python3 raid_check.py FILE [FILE ...] [--today YYYY-MM-DD]

A log file (as in ../templates/raid.md) has only the sections "## Risks", "## Issues",
"## Decisions" and "## Guardrails", each with one table. A status file (as in
../templates/status.md) has a "## Status" section and may have a "## Full pack" section; the
overclaim rule reads both, the five-line rule only the status. Keep the log and the status in separate files. --today is a UTC date and defaults to
today's UTC date; it decides which deadlines have passed.

Rules:
  owner-date  every risk and issue, open or closed, has an owner and a date (YYYY-MM-DD)
  decision    every decision request has a decider, a deadline (YYYY-MM-DD) and a default
              (a date the sources did not give may read "YYYY-MM-DD (proposed)")
  deadline    a decision whose deadline has passed says "default applied: ..." or "decided: ..."
  guardrail   a breached guardrail says the action taken
  status      the "## Status" section has 1 to 5 lines (blank lines do not count)
  overclaim   a line in the status or the full pack that says "on track" or "verified" has
              evidence on the same line (a date, a percentile or a percentage); one that says
              "signed" (off) or "approved" cites its source (the /approve comment's #issuecomment
              link, /approve with its own date such as "/approve on 2026-11-24", or a written:
              ledger row) or says "claimed". "not ..." passes; so does a clause that starts "Do
              not" or "Never", and a request ("asked me to mark F2 as signed off") that a later
              clause refuses ("I did not"). Headings, fenced code and table header rows are
              skipped; table body rows are read
  format      in a log: only the four sections, each once, each with one table with the template's
              columns and no table line outside it; known states and outcomes; unique IDs. In a
              status file: only "## Status" (once) and "## Full pack". Something to check in
              every file

Exits 0 and prints "pass" when every file follows the rules. Otherwise exits 1 and prints one line
per broken rule: "<rule>: <file>: <what to fix>". Standard library only. The check proves the log
is complete; it cannot prove that an owner agreed, that an action really happened, or that the
evidence on a status line is true.
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TABLES = {
    "Risks": ("ID", "Risk", "Owner", "Date", "Response", "State"),
    "Issues": ("ID", "Issue", "Owner", "Date", "Action", "State"),
    "Decisions": ("ID", "Decision needed", "Decider", "Deadline", "Default", "Outcome"),
    "Guardrails": ("ID", "Guardrail", "Limit", "Value", "State", "Action taken"),
}
STATES = {"Risks": ("open", "closed"), "Issues": ("open", "closed"), "Guardrails": ("ok", "breached")}
STATUS_LINES = 5
EMPTY = re.compile(r"^(?:|-+|\?+|tbd|todo|tbc|n/?a|none|<[^<>]*>)$", re.I)
SEPARATOR = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
OUTCOME = re.compile(r"^(?:open(?::.*)?|(?:default applied|decided):\s*\S.*)$", re.I)
OVERCLAIM = re.compile(r"\b(on[- ]track|verified|signed(?: off)?|approved)\b", re.I)
SIGN_OFF = ("signed", "approved")
NEGATED = re.compile(r"\b(?:not|never|no longer)\s+(?:(?:yet|been|fully)\s+)*$", re.I)
EVIDENCE = re.compile(r"\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)?\s?%|\b\d+(?:st|nd|rd|th) percentile\b", re.I)
SOURCE = re.compile(r"#issuecomment-\d+|\bwritten:|\bclaimed\b", re.I)
DATE = r"\d{4}-\d{2}-\d{2}"
# The date of a /approve comment: right after it ("/approve 2026-11-24", "/approve on 2026-11-24",
# "/approve comment of 2026-11-24"), or right before a parenthesis naming it ("on 2026-11-24
# (tracker /approve)"). Any other date on the line is not the comment's date.
APPROVE_DATED = re.compile(
    rf"/approve\b(?:\s+comment)?(?:\s+(?:on|of|dated|at)\s+|\s*[,:(]?\s*){DATE}"
    rf"|{DATE}\s*\((?:[\w-]+\s+)?/approve\b", re.I)
CLAUSE = re.compile(r"[^.;:!?]+[.;:!?]*")
DO_NOT = re.compile(r"^(?:please\s+)?(?:do\s+not|don't|never)\b", re.I)
REQUEST = re.compile(r"\b(?:asked|asks|wants|wanted|told)\s+(?:me|us)\s+to\b", re.I)
REFUSAL = re.compile(r"^(?:I|we)\s+(?:did\s+not|didn't|have\s+not|haven't|will\s+not|won't)\b", re.I)
FENCE = re.compile(r"^\s*(?:```|~~~)")
HEADING = re.compile(r"^\s*#{1,6}\s")
STATUS_FILE = ("Status", "Full pack")


def sections(text):
    """[(title, first line number, lines)] per '## ' heading; the text before the first has title ''."""
    out = [("", 1, [])]
    for number, line in enumerate(text.splitlines(), 1):
        heading = re.match(r"^## (.+?)\s*$", line)
        if heading:
            out.append((heading.group(1), number + 1, []))
        else:
            out[-1][2].append(line)
    return out


def table(lines):
    """Header, rows and the count of table lines outside the first table ('|' lines)."""
    lines = [line.strip() for line in lines]
    marks = [i for i, line in enumerate(lines) if line.startswith("|")]
    if not marks:
        return None, [], 0
    start = marks[0]
    end = next((i for i in range(start, len(lines)) if not lines[i].startswith("|")), len(lines))
    rows = lines[start:end]
    stray = len(marks) - len(rows)
    cells = lambda row: [c.strip() for c in row.strip("|").split("|")]
    if len(rows) < 2 or not SEPARATOR.match(rows[1]):
        return None, [], stray
    return cells(rows[0]), [cells(r) for r in rows[2:]], stray


def date(value):
    """A date from 'YYYY-MM-DD', or 'YYYY-MM-DD (proposed)' for one the sources did not give."""
    found = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?: \(proposed\))?", value)
    try:
        return dt.date.fromisoformat(found.group(1)) if found else None
    except ValueError:
        return None


def empty(value):
    return bool(EMPTY.match(value.strip()))


def check(path, today):
    name = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"format: {name}: cannot read it ({error})"]
    parts = sections(text)
    titles = [title for title, _, _ in parts if title]
    is_log = any(title in TABLES for title in titles)
    out, seen = [], set()
    for title in dict.fromkeys(titles):
        if titles.count(title) > 1 and (is_log or title == "Status"):
            out.append(f"format: {name}: '## {title}' appears more than once; keep one section")
    for title, first, lines in parts:
        if title in TABLES:
            out += log_section(name, title, first, lines, today, seen)
        elif is_log:
            stray = [first + i for i, line in enumerate(lines) if line.strip().startswith("|")]
            if title in STATUS_FILE:
                out.append(f"format: {name}: '## {title}' in a log; keep the log and the status in separate files")
            elif title:  # its rows, if any, are not read: the heading is the one thing to fix
                out.append(f"format: {name}: unknown section '## {title}' in a log; use only "
                           + ", ".join(f"'## {t}'" for t in TABLES) + "; keep the status in its own file")
            elif stray:
                out.append(f"format: {name}: line {stray[0]}: {len(stray)} table lines outside a checked table")
        elif "Status" in titles and title and title not in STATUS_FILE:
            out.append(f"format: {name}: unknown section '## {title}' in a status file; use only "
                       "'## Status' and '## Full pack', and keep the log in its own file")
        if title == "Status":
            out += status_section(name, first, lines)
        elif title == "Full pack":
            out += overclaims(name, "## Full pack", first, lines)
    if not is_log and "Status" not in titles:
        out.append(f"format: {name}: nothing to check; it has no Risks, Issues, Decisions, "
                   "Guardrails or Status section")
    return out


def log_section(name, title, first, lines, today, seen):
    columns = TABLES[title]
    header, rows, stray = table(lines)
    out = []
    if stray:
        out.append(f"format: {name}: '## {title}' has {stray} table lines outside its table; keep one "
                   "table with no blank line in it")
    if header != list(columns):
        return out + [f"format: {name}: '## {title}' needs a table with the columns {' | '.join(columns)}"]
    for row in rows:
        if len(row) != len(columns):
            out.append(f"format: {name}: a row in '## {title}' has {len(row)} cells, not {len(columns)}")
            continue
        cell = dict(zip(columns, row))
        ident = cell["ID"] or "(no ID)"
        if empty(cell["ID"]) or ident in seen:
            out.append(f"format: {name}: {ident} in '## {title}' needs a unique ID")
        seen.add(ident)
        out += rules(name, title, ident, cell, today)
    return out


def rules(name, title, ident, cell, today):
    out = []
    state = cell.get("State", "").lower()
    if title in STATES and state not in STATES[title]:
        out.append(f"format: {name}: {ident} has state {cell['State']!r}; use {' or '.join(STATES[title])}")
    if title in ("Risks", "Issues"):
        missing = (["owner"] if empty(cell["Owner"]) else []) + ([] if date(cell["Date"]) else ["date"])
        if missing:
            out.append(f"owner-date: {name}: {ident} needs {' and '.join(missing)}"
                       " (a named person; a date as YYYY-MM-DD)")
    elif title == "Decisions":
        deadline = date(cell["Deadline"])
        missing = [f.lower() for f in ("Decider", "Default") if empty(cell[f])] + ([] if deadline else ["deadline"])
        if missing:
            out.append(f"decision: {name}: {ident} needs {', '.join(missing)} (a deadline as YYYY-MM-DD)")
        outcome = cell["Outcome"].strip()
        if not OUTCOME.match(outcome):
            out.append(f"format: {name}: {ident} outcome must be 'open', 'default applied: <what, date>' "
                       "or 'decided: <what> (<decider>, <date>)'")
        elif deadline and today > deadline and outcome.lower().startswith("open"):
            out.append(f"deadline: {name}: {ident} passed its deadline {deadline}; write "
                       "'default applied: <what, date>' or 'decided: <what> (<decider>, <date>)'")
    elif title == "Guardrails" and state == "breached" and empty(cell["Action taken"]):
        out.append(f"guardrail: {name}: {ident} is breached; write the action taken and when")
    return out


def status_section(name, first, lines):
    out = []
    count = sum(1 for line in lines if line.strip())
    if not 1 <= count <= STATUS_LINES:
        out.append(f"status: {name}: the status has {count} lines; write 1 to {STATUS_LINES}, "
                   "and put the detail in the full pack")
    return out + overclaims(name, "## Status", first, lines)


def sourced(line):
    """A sign-off source: a comment link, a written: row, the label 'claimed', or /approve with its date."""
    return bool(SOURCE.search(line) or APPROVE_DATED.search(line))


def claims_in(line):
    """Overclaim words the line asserts. A clause that starts "Do not" or "Never" asserts none, and
    neither does a reported request ("asked me to ...") that a later clause refuses ("I did not")."""
    clauses = [c.strip() for c in CLAUSE.findall(line)]
    found = []
    for i, clause in enumerate(clauses):
        if DO_NOT.match(clause):
            continue
        if REQUEST.search(clause) and any(REFUSAL.match(c) for c in clauses[i + 1:]):
            continue
        found += [m.group(1) for m in OVERCLAIM.finditer(clause) if not NEGATED.search(clause[:m.start()])]
    return found


def prose(lines, first):
    """(line number, line) for prose: no headings, fenced code, or table header and separator rows."""
    fenced = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        following = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if fenced or HEADING.match(line) or SEPARATOR.match(line.strip()) or (
                line.strip().startswith("|") and SEPARATOR.match(following)):
            continue
        yield first + i, line


def overclaims(name, where, first, lines):
    out = []
    for number, line in prose(lines, first):
        claims = claims_in(line)
        signed = [c for c in claims if c.lower().startswith(SIGN_OFF)]
        if signed and not sourced(line):
            out.append(f"overclaim: {name}: {where} line {number} says {signed[0]!r} with no source; cite "
                       "the /approve comment (its link, or its date) or the written: ledger row, or label "
                       "it 'claimed'")
        elif len(signed) < len(claims) and not EVIDENCE.search(line):
            claim = next(c for c in claims if c not in signed)
            out.append(f"overclaim: {name}: {where} line {number} says {claim!r} with no evidence on the line; "
                       "add the date, percentile or percentage it rests on, or write 'not ...'")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date(),
                        help="a UTC date, YYYY-MM-DD (default: today's UTC date)")
    args = parser.parse_args(argv)
    problems = [p for path in args.files for p in check(path, args.today)]
    print("\n".join(problems) or "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

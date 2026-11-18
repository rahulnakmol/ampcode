#!/usr/bin/env python3
"""Check a mission file: its charter, gate ledger and decision trail.

  python3 ledger_check.py mission.md

Exits 0 and prints "pass" when the file follows rules R1 to R12. Otherwise exits 1 and prints
each problem as "<rule>: <what to fix>". Standard library only. The grammar and the rules are in
../reference/charter.md. The check proves the record is complete and consistent. It cannot prove
that a person really answered, and it cannot read Amp dialogs, tracker comments or URLs.
"""

import re
import subprocess
import sys
from pathlib import Path

FIELDS = (
    "Outcome", "Decision owner", "Approvers", "Success criteria", "Definition of Done", "Budget",
    "Budget used", "May do without asking", "Always ask", "Stop and ask when", "Playbook", "Host",
)
HOSTS = ("amp", "claude code", "copilot in vs code", "copilot app")
PLAYBOOKS = (
    "transformation", "product-operations", "software-delivery", "campaigns-and-research",
    "experience-design", "security-review", "infrastructure", "product-assessment",
)
LEDGER = ("Gate", "Kind", "State", "Evidence", "Review", "Brief", "Decider", "Source", "Date")
TRAIL = ("Date", "Decision", "Why", "Evidence", "Decider")
KINDS = ("human", "agent")
STATES = ("open", "pending", "passed", "failed", "waived")
SOURCES = ("dialog", "question", "tracker", "written")
EMPTY = ("", "-")
NOT_AN_ANSWER = re.compile(r"\b(?:chat|looks good|lgtm|sounds good|fine by me)\b|👍", re.I)
PLACEHOLDER = re.compile(r"\b(?:TBD|TODO|TBC)\b|^\?+$|<(?![a-z][a-z0-9+.-]*:)[^<>\n]+>", re.I)
BRIEF_CHECK = Path(__file__).resolve().parents[2] / "briefing-decisions" / "scripts" / "brief_check.py"


def section(text, title):
    """Return the lines under '## <title>' up to the next '## ' heading, or None."""
    match = re.search(rf"^## {re.escape(title)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).splitlines() if match else None


def fields(lines):
    """Charter fields as {name: [values]}; indented lines continue the previous value."""
    found, name = {}, None
    for line in lines:
        match = re.match(r"^- \*\*(.+?):\*\*[ \t]*(.*)$", line)
        if match:
            name = match.group(1)
            found.setdefault(name, []).append(match.group(2).strip())
        elif name and line.startswith("  ") and line.strip():
            found[name][-1] = (found[name][-1] + " " + line.strip()).strip()
        else:
            name = None
    return found


def table(lines):
    """Header cells and data rows of the first Markdown table in lines."""
    rows = [l.strip() for l in lines if l.strip().startswith("|")]
    if len(rows) < 2:
        return None, []
    cells = lambda row: [c.strip() for c in row.strip("|").split("|")]
    return cells(rows[0]), [cells(r) for r in rows[2:]]


WORD = r"[^\W\d_][\w.'’-]*"
PERSON = re.compile(rf"(?:{WORD}(?: {WORD}){{0,4}}(?: \(@?[\w.-]+\))?|@[\w.-]+)")


def people_ok(value):
    """True for 'none' or comma-separated names, each optionally followed by '(handle)'."""
    return value.strip().lower() == "none" or all(PERSON.fullmatch(e.strip()) for e in value.split(","))


def identities(value):
    """Names and handles in a comma-separated list: 'Elena Petrova (@elena-p)' gives two."""
    out = set()
    if value.strip().lower() == "none":
        return out
    for entry in value.split(","):
        for part in re.findall(r"\(([^)]*)\)", entry) + [re.sub(r"\([^)]*\)", "", entry)]:
            part = part.strip().lstrip("@").strip().lower()
            if part:
                out.add(part)
    return out


def local(reference, base):
    """The local path a reference names (text before any ' (url)'), if it exists."""
    path = reference.split(" (", 1)[0].strip()
    return base / path if path and not path.startswith("https://") and (base / path).is_file() else None


def check_brief(path):
    if not BRIEF_CHECK.is_file():
        return f"cannot check brief {path.name}: briefing-decisions is not installed beside missioning"
    run = subprocess.run([sys.executable, str(BRIEF_CHECK), str(path)], capture_output=True, text=True)
    return None if run.returncode == 0 else f"brief {path.name} fails brief_check.py: {run.stdout.strip().splitlines()[0]}"


def check(text, base):
    problems = []
    add = lambda rule, message: problems.append(f"{rule}: {message}")
    charter = fields(section(text, "Charter") or [])
    for name in FIELDS:
        values = charter.get(name, [])
        if len(values) != 1:
            add("R1", f"charter needs exactly one '- **{name}:**' line (found {len(values)})")
        elif not values[0] or PLACEHOLDER.search(values[0]):
            add("R1", f"charter field {name} is empty or a placeholder")
        elif name in ("Decision owner", "Approvers") and not people_ok(values[0]):
            add("R1", f"{name} must be 'none' or comma-separated names, each with an optional '(handle)', not prose")
    get = lambda name: (charter.get(name) or [""])[0]
    host, playbook, budget = get("Host").lower(), get("Playbook"), get("Budget")
    if host and host not in HOSTS:
        add("R2", f"Host must be one of Amp, Claude Code, Copilot in VS Code, Copilot app, not '{get('Host')}'")
    if playbook and playbook not in PLAYBOOKS and not re.match(r"none: \S", playbook):
        add("R2", f"Playbook must be a playbook name or 'none: <reason>', not '{playbook}'")
    if budget and not (re.search(r"\d", budget) or re.search(r"no limit on .+, decided by \S", budget, re.I)):
        add("R3", "Budget must name a limit with a number, or say 'no limit on <what>, decided by <name>'")

    deciders = identities(get("Decision owner")) | identities(get("Approvers"))
    header, rows = table(section(text, "Gate ledger") or [])
    if header != list(LEDGER) or not rows:
        add("R4", "gate ledger needs a table with headers " + " | ".join(LEDGER) + " and at least one row")
        rows = []
    for row in rows:
        if len(row) != len(LEDGER):
            add("R4", f"gate ledger row '{row[0]}' has {len(row)} cells, not {len(LEDGER)}")
            continue
        gate, kind, state, evidence, review, brief, decider, source, _ = row
        if kind not in KINDS or state not in STATES:
            add("R5", f"gate '{gate}': Kind must be human or agent and State one of {', '.join(STATES)}")
            continue
        if (kind == "human" and state == "passed") or state == "waived":
            names = [n for n in (x.strip().lstrip("@").lower() for x in decider.split(",")) if n not in EMPTY]
            if not names or any(n not in deciders for n in names):
                add("R6", f"gate '{gate}': Decider must name the Decision owner or an Approver")
            kind_of, _, reference = source.partition(":")
            kind_of = kind_of.strip().lower()
            if source in EMPTY:
                add("R6", f"gate '{gate}': Source must say where the decider answered")
            elif kind_of not in SOURCES or NOT_AN_ANSWER.search(reference):
                add("R7", f"gate '{gate}': source '{source}' is not an approval; approval is never inferred from chat")
            elif not reference.strip():
                add("R6", f"gate '{gate}': Source needs a reference after '{kind_of}:'")
            elif kind_of == "dialog" and host != "amp" and "amp" not in reference.lower():
                add("R6", f"gate '{gate}': a dialog source must name Amp when the host is not Amp")
        if kind == "human" and state == "passed":
            path = local(brief, base)
            if path is None:
                add("R8", f"gate '{gate}': Brief must be a local Markdown file that exists")
            elif (problem := check_brief(path)):
                add("R8", f"gate '{gate}': {problem}")
        if state == "passed":
            agent_ok = kind == "agent" and re.match(r"none needed: \S", review)
            if not (agent_ok or review.startswith("https://") or local(review, base)):
                add("R9", f"gate '{gate}': Review must be a record that exists (path or https URL)")
            if kind == "agent" and evidence in EMPTY:
                add("R10", f"gate '{gate}': a passed agent gate needs Evidence")
        if state == "waived" and evidence in EMPTY:
            add("R11", f"gate '{gate}': a waived gate needs the reason in Evidence")

    header, rows = table(section(text, "Decision trail") or [])
    if header != list(TRAIL):
        add("R12", "decision trail needs a table with headers " + " | ".join(TRAIL))
    for row in rows:
        if len(row) != len(TRAIL) or row[-1] in EMPTY:
            add("R12", f"decision trail row '{row[0]}' needs all five cells and a Decider")
    return problems


def main(argv):
    if len(argv) != 2:
        print("usage: ledger_check.py mission.md")
        return 2
    path = Path(argv[1])
    problems = check(path.read_text(encoding="utf-8"), path.resolve().parent)
    print("\n".join(problems) if problems else "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

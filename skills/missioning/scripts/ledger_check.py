#!/usr/bin/env python3
"""Check a mission file: its charter, gate ledger and decision trail.

  python3 ledger_check.py mission.md

Exits 0 and prints "pass" when the file follows rules R1 to R13 (R3 is retired). Otherwise exits 1
and prints each problem as "<rule>: <what to fix>". Standard library only. The grammar and the
rules are in ../reference/charter.md. The check proves the record is complete and consistent. It
cannot prove that a person really answered, and it cannot read Amp dialogs, tracker comments or
URLs.
"""

import re
import subprocess
import sys
from pathlib import Path

FIELDS = (
    "Outcome", "Decision owner", "Approvers", "Success criteria", "Definition of Done",
    "Open questions", "Pre-authorized effects", "May do without asking", "Always ask",
    "Stop and ask when", "Playbook", "Host",
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
NOT_AN_ANSWER = re.compile(
    r"\b(?:chat|conversation|slack|dm|looks good|lgtm|sounds good|fine by me)\b|👍", re.I)
PLACEHOLDER = re.compile(r"\b(?:TBD|TODO|TBC)\b|(?i:^(?:tbd|todo|tbc)$)|^\?+$|<(?!https?://|mailto:)[^<>\n]+>")
SEPARATOR = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+$")
SKILLS = Path(__file__).resolve().parents[2]  # this skill's parent: sibling skills live here


def brief_checker():
    """briefing-decisions' checker beside this skill: 'briefing-decisions' or Amp's 'name@hash'."""
    for folder in [SKILLS / "briefing-decisions", *sorted(SKILLS.glob("briefing-decisions@*"))]:
        if (folder / "scripts" / "brief_check.py").is_file():
            return folder / "scripts" / "brief_check.py"
    return None


def section(text, title):
    """Lines under the one '## <title>' up to the next '## ' heading; None if absent or repeated."""
    found = re.findall(rf"^## {re.escape(title)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return found[0].splitlines() if len(found) == 1 else None


def repeated(text, title):
    """True when a heading that reads as '## <title>' appears more than once, at any case."""
    return len(re.findall(rf"^#+ {re.escape(title)}\b", text, re.M | re.I)) > 1


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
    lines = [l.strip() for l in lines]
    start = next((i for i, l in enumerate(lines) if l.startswith("|")), None)
    if start is None:
        return None, []
    end = next((i for i in range(start, len(lines)) if not lines[i]), len(lines))
    rows = lines[start:end]  # every line up to a blank one is a row, outer pipes or not
    if any("|" in line for line in lines[end:]):
        return None, []  # a row or table after a blank line: fail rather than skip it
    cells = lambda row: [c.strip() for c in row.strip("|").split("|")]
    if len(rows) < 2 or not SEPARATOR.match(rows[1]) or len(cells(rows[1])) != len(cells(rows[0])):
        return None, []
    return cells(rows[0]), [cells(r) for r in rows[2:]]


WORD = r"[^\W\d_][\w.'’-]*"
PERSON = re.compile(rf"(?:{WORD}(?: {WORD}){{0,4}}(?: \(@?[\w.-]+\))?|@[\w.-]+)")


def people_ok(value, none_allowed):
    """True for comma-separated names, each optionally followed by '(handle)', or 'none' if allowed."""
    if value.strip().lower() == "none":
        return none_allowed
    return all(PERSON.fullmatch(e.strip()) for e in value.split(","))


def people(value):
    """One identity set per comma-separated entry: 'Elena Petrova (@elena-p)' gives {name, handle}."""
    if value.strip().lower() in ("none", *EMPTY):
        return []
    out = []
    for entry in value.split(","):
        parts = re.findall(r"\(([^)]*)\)", entry) + [re.sub(r"\([^)]*\)", "", entry)]
        names = {p.strip().lstrip("@").strip().lower() for p in parts} - {""}
        if names:
            out.append(names)
    return out


def is_one_of(person, group):
    """True when every identity a Decider entry gives belongs to one person in group."""
    return any(person <= member for member in group)


def local(reference, base):
    """The relative local path a reference names (text before any ' (url)'), if the file exists."""
    path = reference.split(" (", 1)[0].strip()
    ok = path and not path.startswith(("https://", "/")) and (base / path).is_file()
    return (base / path).resolve() if ok else None


def check_brief(path):
    checker = brief_checker()
    if checker is None:
        return f"cannot check brief {path.name}: briefing-decisions is not installed beside missioning"
    run = subprocess.run([sys.executable, str(checker), str(path)], capture_output=True, text=True)
    output = run.stdout.strip() or run.stderr.strip() or "no output"
    return None if run.returncode == 0 else f"brief {path.name} fails brief_check.py: {output.splitlines()[0]}"


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
        elif name == "Decision owner" and values[0].strip().lower() == "none":
            add("R1", "Decision owner names one person; it is never 'none'")
        elif name in ("Decision owner", "Approvers") and not people_ok(values[0], name == "Approvers"):
            add("R1", f"{name} must be 'none' or comma-separated names, each with an optional '(handle)', not prose")
        elif name == "Decision owner" and "," in values[0]:
            add("R1", "Decision owner is one person; name others as Approvers")
    get = lambda name: (charter.get(name) or [""])[0]
    host, playbook = get("Host").lower(), get("Playbook")
    if host and host not in HOSTS:
        add("R2", f"Host must be one of Amp, Claude Code, Copilot in VS Code, Copilot app, not '{get('Host')}'")
    if playbook and playbook not in PLAYBOOKS and not re.match(r"none: \S", playbook):
        add("R2", f"Playbook must be a playbook name or 'none: <reason>', not '{playbook}'")
    effects = get("Pre-authorized effects").strip()
    granted = {i.upper() for i in re.findall(r"\bE\d+\b", effects, re.I)}
    if effects and not PLACEHOLDER.search(effects) and not re.match(r"none\b|E\d+\b", effects, re.I):
        add("R13", "Pre-authorized effects must be 'none' or a list of 'E<n> <effect>' entries")

    owner = people(get("Decision owner"))
    deciders = owner + people(get("Approvers"))
    header, rows = table(section(text, "Gate ledger") or [])
    ledger_headers = sum(1 for line in text.splitlines()
                         if [c.strip() for c in line.strip().strip("|").split("|")] == list(LEDGER))
    if repeated(text, "Charter"):
        add("R1", "the mission file has more than one Charter section")
    if repeated(text, "Gate ledger") or ledger_headers != 1:
        add("R4", "the mission file needs exactly one gate ledger table, under one '## Gate ledger'")
    if header != list(LEDGER) or not rows:
        add("R4", "gate ledger needs one table with headers " + " | ".join(LEDGER)
            + " and at least one row, and no table rows after a blank line")
        rows = []
    for row in rows:
        if len(row) != len(LEDGER):
            add("R4", f"gate ledger row '{row[0]}' has {len(row)} cells, not {len(LEDGER)}")
            continue
        gate, kind, state, evidence, review, brief, decider, source, _ = row
        if kind not in KINDS or state not in STATES:
            add("R5", f"gate '{gate}': Kind must be human or agent and State one of {', '.join(STATES)}")
            continue
        if re.match(r"(?:mission )?(?:charter|kickoff)\b", gate, re.I) and kind != "human":
            add("R5", f"gate '{gate}': the charter and kickoff gates are always human gates")
        # Effect IDs: '(E<n>)' in the Gate, any case; in Evidence, upper case and only when it
        # speaks of pre-authorization, so codes such as 'E501' or 'rustc E0308' stay plain evidence.
        pre = re.match(r"pre-authori[sz]ed\b(?::(.*))?", evidence, re.I)
        mentions = re.search(r"\bpre-?authori[sz]ed\b", evidence, re.I)
        named = {i.upper() for i in re.findall(r"\((E\d+)\)", gate, re.I)}
        cited = named | (set(re.findall(r"\bE\d+\b", evidence)) if mentions else set())
        if kind == "human" and (pre or named & granted):
            add("R13", f"gate '{gate}': a pre-authorized effect is an agent row, not a human gate; do not ask for it again")
        elif kind == "agent" and (mentions or cited):
            grant = (pre.group(1) or "").strip() if pre else ""
            if not grant or grant.split()[0].strip(".,;").lower() in ("-", "none") or PLACEHOLDER.search(grant):
                add("R13", f"gate '{gate}': Evidence must read 'pre-authorized: <source>'")
            elif not cited or not cited <= granted:
                add("R13", f"gate '{gate}': name the effect's ID (E<n>) from the charter's Pre-authorized effects")
        if (kind == "human" and state == "passed") or state == "waived":
            names = people(decider)
            if not names or not all(is_one_of(n, deciders) for n in names):
                add("R6", f"gate '{gate}': Decider must name the Decision owner or an Approver")
            kind_of, _, reference = source.partition(":")
            kind_of = kind_of.strip().lower()
            if source in EMPTY:
                add("R6", f"gate '{gate}': Source must say where the decider answered")
            elif kind_of not in SOURCES or NOT_AN_ANSWER.search(
                    re.sub(r"\bask_user in copilot chat\b", "", reference, flags=re.I) if kind_of == "question" else reference):
                add("R7", f"gate '{gate}': source '{source}' is not an approval; approval is never inferred from chat")
            elif not reference.strip():
                add("R6", f"gate '{gate}': Source needs a reference after '{kind_of}:'")
            elif kind_of == "dialog" and host != "amp" and not re.search(r"\bamp\b", reference, re.I):
                add("R6", f"gate '{gate}': a dialog source must name Amp when the host is not Amp")
            elif kind_of in ("question", "dialog") and not all(is_one_of(n, owner) for n in names):
                add("R6", f"gate '{gate}': only the Decision owner answers a {kind_of}; other approvers sign by tracker or written")
        if kind == "human" and state == "passed":
            path = local(brief, base)
            if path is None or path.suffix != ".md":
                add("R8", f"gate '{gate}': Brief must be a local Markdown file that exists")
            elif (problem := check_brief(path)):
                add("R8", f"gate '{gate}': {problem}")
        if state == "passed":
            agent_ok = kind == "agent" and re.match(r"none needed: \S", review)
            record = local(review, base)
            if record is not None and record == local(brief, base):
                record = None
            if not (agent_ok or re.match(r"https://\S+\.\S", review) or record):
                add("R9", f"gate '{gate}': Review must be a record that exists (path or https URL)")
            if kind == "agent" and (evidence in EMPTY or PLACEHOLDER.search(evidence)):
                add("R10", f"gate '{gate}': a passed agent gate needs Evidence")
        if state == "waived" and (evidence in EMPTY or PLACEHOLDER.search(evidence)):
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

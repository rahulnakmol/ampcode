#!/usr/bin/env python3
"""Check a post-incident review and file its actions as draft bugs in a backlog/v1 file.

  python3 pir_check.py check review.md
  python3 pir_check.py bugs review.md --backlog backlog.json --feature F-n

check prints "pass" and exits 0, or prints one line per broken rule ("P3: ...") and exits 1.
The rules (P1 to P9) and the review format are in ../SKILL.md and
../templates/post-incident-review.md.

bugs runs first. It checks every rule except P8 (backlog IDs); on a finding it writes nothing and
exits 1. Otherwise it adds one draft bug per action that has no backlog ID yet, under feature F-n,
with the next free bug IDs, writes each ID into the action's "- Backlog:" line, and exits 0.
Run grooming's `backlog.py validate` on the backlog and `check` on the review afterwards.
Standard library only. Exit 2 means a file could not be read or written.
"""

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SECTIONS = ("Impact", "Timeline", "Hypotheses", "Root cause", "Contributing conditions",
            "Mitigation", "Actions", "Missing evidence")
# Severity -> (bug priority, bug urgency). SKILL.md has the same table; a test compares them.
SEVERITY = {
    "SEV-1": ("must", "critical"),
    "SEV-2": ("must", "high"),
    "SEV-3": ("should", "medium"),
    "SEV-4": ("could", "low"),
}
STATUSES = ("open", "supported", "confirmed", "rejected")
KINDS = ("durable fix", "missing alert", "prevention")
NO_EVIDENCE = {"", "-", "—", "none", "n/a", "na", "tbd", "unknown"}
TIME = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)\s*(Z|UTC|[+-]\d{2}:?\d{2})", re.I)
BACKLOG_ID = re.compile(r"\b[BS]-\d+\b")
# A measurable "then": the same tests as QUANTITY, ANY_ID and the digit check in grooming's
# backlog.py, so a filed bug's criteria pass `backlog.py validate`. Keep them in step; a test
# compares them.
QUANTITY = re.compile(
    r"\d|\b(every|each|all|none|no|exactly|at least|at most|within|zero|one|two|three|four|five|six|"
    r"seven|eight|nine|ten|eleven|twelve)\b",
    re.I,
)
ANY_ID = re.compile(r"\b(?:[IGFSBDR]|AC|FB)-\d+(?:\.\d+)?\b|\bE\d+\b")
GWT = re.compile(r"(?i)^given\s+(.+?),?\s+when\s+(.+?),?\s+then\s+(.+?)\.?$")
# The exact "not established" line; beside it, only lines that start with "Open:".
NOT_ESTABLISHED = re.compile(r"(?:root cause\s*:\s*)?not established\.?\s*", re.I)
ROOT_LABEL = re.compile(r"^root cause\b[^:]*:", re.I)
# The overclaim policy of the sibling skills (threat-modelling), adapted to incidents. Not claims:
# "secure" as a verb ("secure the queue", "secured the queue") or before a noun ("secure storage",
# "Secure Score"), "securely", "verified" as a verb with an object ("verified the rollback"),
# "no vulnerability scans", and anything in a code span or in double quotes (a quoted status).
SECURE_NOUNS = (
    "storage|store|stores|channel|channels|connection|connections|transport|string|strings|boot|enclave|"
    "enclaves|score|shell|cookie|cookies|element|elements|vault|vaults|zone|zones|area|areas|token|tokens|"
    "key|keys|link|links|tunnel|tunnels|protocol|protocols|socket|sockets|server|servers|gateway|gateways|"
    "endpoint|endpoints|network|networks|location|locations|mode|copy|copies|login|logins|transfer|transfers"
)
OVERCLAIM = re.compile(
    rf"\b(?:is|are|was|were|be|been|being|remains?|stays?)\s+(?:now\s+|fully\s+|always\s+)?secure\b"
    rf"(?![-\s]+(?:{SECURE_NOUNS})\b)"
    rf"|\bsecur(?:e|ed)\b(?![-\s]+(?:{SECURE_NOUNS})\b)"
    r"(?!\s+(?:the|a|an|our|their|its|this|that|these|those|each|every|all|it|them|access)\b)"
    r"|\b(?:no|zero)\s+(?:known\s+)?vulnerabilit(?:y|ies)\b"
    r"(?!\s+(?:scan|scanning|scanner|test|database|data|feed)s?\b)"
    r"|\bvulnerabilit(?:y|ies)[-\s]free\b"
    r"|\b(?:is|are|was|were|been|be|now|fully)\s+verified\b|\bverified\s+(?:fix|fixes|result|results)\b"
    r"|\bverified(?=\s*(?:[.!:;]|$))"
    r"|\balerts?\s+(?:now\s+)?(?:works?|worked|(?:is|was|are|were)\s+working|fire[sd]?\s+correctly)\b", re.I)
QUOTED = re.compile(r"`[^`\n]*`|\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d")
# An honest negation or doubt right before the word: "not verified yet", "never been verified",
# "nothing here is verified", "cannot be called secure", "whether the worker is secure".
# "not only", "not just", "not merely" do not negate.
NEGATED = re.compile(
    r"(?:\b(?:not|never)\s+(?:(?!(?:only|just|merely)\b)\w+\s+)?"
    r"|\bnothing\s+(?:\w+\s+){0,2}|\bcannot\s+be\s+called\s+|\b(?:whether|if)\s+(?:[\w'-]+\s+){0,4})$", re.I)
# An owner the sources do not name: "to assign (F-2 owner: Tom Okafor)".
TO_ASSIGN = re.compile(r"to assign\b", re.I)
FIELDS = ("kind", "owner", "backlog", "observed", "expected", "steps", "acceptance")
MONITORING = ("Missing alert: write the alert rule and its runbook with the `monitoring` skill, "
              "and prove it fires before closing this bug.")


def sections(text):
    """Map each '## ' heading to its body."""
    parts = re.split(r"^## +(.+?)\s*$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def header(text, key):
    match = re.search(rf"^- {re.escape(key)}:\s*(.+?)\s*$", text.split("\n## ", 1)[0], re.M)
    return match.group(1) if match else ""


def table(body):
    """Rows of the first Markdown table in body, as lists of cells, without header and delimiter."""
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith("|")]
    cells = [[c.strip() for c in row.strip("|").split("|")] for row in rows]
    return [row for row in cells[1:] if not all(re.fullmatch(r":?-+:?", c) for c in row)]


def overclaims(text):
    """Each claim word in text that no 'not' just before it negates, once, in order."""
    text = QUOTED.sub(" ", text)
    found = [m.group(0) for m in OVERCLAIM.finditer(text) if not NEGATED.search(text[:m.start()])]
    return list(dict.fromkeys(found))


def to_utc(cell):
    """The UTC instant of a timeline cell; None when it is not in the accepted format. Raises
    ValueError for an impossible date, hour or offset, such as 2026-02-30 or +25:00."""
    match = TIME.fullmatch(cell.strip())
    if not match:
        return None
    day, clock, zone = match.groups()
    moment = datetime.fromisoformat(f"{day}T{clock}")
    if zone.upper() in ("Z", "UTC"):
        offset = timedelta(0)
    else:
        sign = -1 if zone[0] == "-" else 1
        digits = zone[1:].replace(":", "")
        offset = sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
    return moment.replace(tzinfo=timezone(offset)).astimezone(timezone.utc)


def actions(body):
    """Each '### A<n>: title' block in the Actions section, with its fields, steps and criteria."""
    found = []
    blocks = re.split(r"^### +", body, flags=re.M)[1:]
    for block in blocks:
        heading, _, rest = block.partition("\n")
        match = re.fullmatch(r"(A\d+):\s*(.+?)\s*", heading)
        action = {"id": match.group(1) if match else heading.strip(), "title": match.group(2) if match else "",
                  "fields": {}, "steps": [], "acceptance": []}
        current = None
        for line in rest.splitlines():
            if not line.strip():
                continue
            field = re.match(r"^- ([A-Za-z ]+):\s*(.*?)\s*$", line)
            indented = re.match(r"^\s+- ([A-Za-z ]+):\s*(.*?)\s*$", line)
            if indented and indented.group(1).strip().lower() in FIELDS:
                field = indented  # an indented known field is still that field
            if field:
                current = field.group(1).strip().lower()
                action["fields"][current] = field.group(2)
                continue
            step = re.match(r"^\s+\d+[.)]\s+(.+?)\s*$", line)
            if step and current == "steps":
                action["steps"].append(step.group(1))
                continue
            item = re.match(r"^\s+[-*]\s+(.+?)\s*$", line)
            if item and current == "acceptance":
                action["acceptance"].append(item.group(1))
                continue
            # Any other line, indented or not, continues the field, step or criterion before it.
            more = re.match(r"^\s*(\S.*?)\s*$", line)
            if more and current in ("steps", "acceptance") and action[current]:
                action[current][-1] += " " + more.group(1)
            elif more and current and current not in ("steps", "acceptance"):
                action["fields"][current] = (action["fields"][current] + " " + more.group(1)).strip()
        found.append(action)
    return found


def findings(text):
    """Return one 'P<n>: message' line per broken rule."""
    out = []
    parts = sections(text)

    # P1: sections and severity.
    for name in SECTIONS:
        if name == "Mitigation":
            continue  # P6 reports it: a missing mitigation is a separation problem
        if not parts.get(name, "").strip():
            out.append(f"P1: the '## {name}' section is missing or empty")
    severity = header(text, "Severity")
    if severity not in SEVERITY:
        out.append(f"P1: '- Severity:' is {severity or 'missing'!r}; use one of {', '.join(SEVERITY)}")

    # P2 and P3: timeline times carry a zone and run in order.
    rows = table(parts.get("Timeline", ""))
    if parts.get("Timeline", "").strip() and not rows:
        out.append("P2: the timeline has no rows: | Time | Event | Source |")
    previous = None
    accepted = "write it as 2026-09-19T14:05+05:30, 2026-09-19T08:35Z or 2026-09-19 08:35 UTC"
    for n, row in enumerate(rows, 1):
        try:
            moment = to_utc(row[0])
        except ValueError:
            out.append(f"P2: timeline row {n} ({row[0]}) is not a real date, time or UTC offset: {accepted}")
            continue
        if moment is None:
            local = re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?", row[0].strip())
            problem = "has no UTC offset" if local else "is not in the accepted format"
            out.append(f"P2: timeline row {n} ({row[0] or 'no time'}) {problem}: {accepted}")
            continue
        if previous and moment < previous[1]:
            out.append(f"P3: timeline row {n} ({row[0]}) is earlier than row {previous[0]} in UTC: "
                       "sort the timeline")
        previous = (n, moment)

    # P4: competing hypotheses, each with a status and evidence.
    hypotheses = {}
    for row in table(parts.get("Hypotheses", "")):
        row += [""] * (5 - len(row))
        hid, _, status, evidence = row[0], row[1], row[2].strip("`").lower(), row[3]
        if not re.fullmatch(r"H\d+", hid):
            out.append(f"P4: hypothesis ID {hid!r} must look like H1")
            continue
        hypotheses[hid] = status
        if status not in STATUSES:
            out.append(f"P4: {hid} has status {row[2]!r}; use one of {', '.join(STATUSES)}")
        if evidence.strip().lower() in NO_EVIDENCE:
            out.append(f"P4: {hid} has no evidence: name the log, metric, trace or code that raised or tests it")
    if len(hypotheses) < 2:
        out.append(f"P4: {len(hypotheses)} hypothesis listed; keep at least 2 competing hypotheses")

    # P5: a stated root cause rests on a confirmed hypothesis.
    # The whole section counts. Either the exact line "Root cause: not established." with only
    # "Open:" lines beside it, or one "Root cause (H<n>): …" line citing a confirmed hypothesis.
    lines = [line.strip() for line in parts.get("Root cause", "").splitlines() if line.strip()]
    others = [line for line in lines if not NOT_ESTABLISHED.fullmatch(line)]
    labelled = [line for line in others if ROOT_LABEL.match(line)]
    if len(others) < len(lines):
        if labelled:
            out.append("P5: the root cause section says 'not established' and also states a cause; "
                       "keep exactly one of the two")
        elif any(not line.startswith("Open:") for line in others):
            out.append("P5: beside 'Root cause: not established.' write only lines that start with "
                       "'Open:', such as 'Open: H1 and H2 until the pool metrics are read.'")
    elif lines:
        if len(labelled) > 1:
            out.append(f"P5: {len(labelled)} root-cause lines; keep exactly one")
        # Only the IDs in the label count; a confirmed rival named elsewhere does not.
        label = ROOT_LABEL.match(labelled[0]).group(0) if labelled else ""
        named = list(dict.fromkeys(re.findall(r"\bH\d+\b", label)))
        unconfirmed = [h for h in named if hypotheses.get(h) != "confirmed"]
        if not named:
            out.append("P5: a root cause is stated without a confirmed hypothesis in its label; write "
                       "'Root cause (H1): …' with H1 confirmed, or 'Root cause: not established.'")
        elif unconfirmed:
            out.append(f"P5: the root cause names {', '.join(unconfirmed)}, which is not confirmed; "
                       "confirm it with evidence, or write 'Root cause: not established.'")

    # P6, P7, P8: actions.
    listed = actions(parts.get("Actions", ""))
    if not parts.get("Mitigation", "").strip():
        out.append("P6: no '## Mitigation' section: say what stopped or limited the impact, apart "
                   "from the durable fix")
    if parts.get("Actions", "").strip() and not listed:
        out.append("P7: the Actions section has no '### A1: title' action")
    seen = {}
    for action in listed:
        seen[action["id"]] = seen.get(action["id"], 0) + 1
    for aid, count in seen.items():
        if count > 1:
            out.append(f"P7: action ID {aid} appears {count} times; give each action its own ID")
    for action in listed:
        aid, fields = action["id"], action["fields"]
        if not re.fullmatch(r"A\d+", aid) or not action["title"]:
            out.append(f"P7: action heading {aid!r} must look like '### A1: title'")
        elif len(action["title"]) > 120:
            out.append(f"P7: {aid} title is longer than 120 characters")
        kind = fields.get("kind", "").lower()
        if kind == "mitigation":
            out.append(f"P6: {aid} is a mitigation; record it under '## Mitigation', not as an action")
        elif kind not in KINDS:
            out.append(f"P7: {aid} kind is {fields.get('kind', 'missing')!r}; use one of {', '.join(KINDS)}")
        for name in ("observed", "expected"):
            if not fields.get(name):
                out.append(f"P7: {aid} has no '- {name.capitalize()}:' line")
        if not action["steps"]:
            out.append(f"P7: {aid} has no numbered '- Steps:' list")
        if not action["acceptance"]:
            out.append(f"P7: {aid} has no '- Acceptance:' criteria")
        has_digit, parsed = False, True
        for criterion in action["acceptance"]:
            parts = GWT.match(criterion)
            if not parts:
                out.append(f"P7: {aid} criterion {criterion!r} is not 'Given …, when …, then …'")
                parsed = False
                continue
            then = parts.group(3)
            has_digit = has_digit or bool(re.search(r"\d", ANY_ID.sub(" ", then)))
            if not QUANTITY.search(then):
                out.append(f"P7: {aid} criterion {criterion!r} has no measurable quantity after 'then': "
                           "give a number or a word such as each, all, none, at least, at most or within")
        if action["acceptance"] and parsed and not has_digit:
            out.append(f"P7: {aid} has no criterion with a number after 'then' (a digit inside an ID "
                       "such as S-2.1 does not count): give at least one a real number, time or amount")
        if not BACKLOG_ID.search(fields.get("backlog", "")):
            out.append(f"P8: {aid} has no backlog ID: run `pir_check.py bugs` or write '- Backlog: B-n'")
    if listed and not any(a["fields"].get("kind", "").lower() == "durable fix" for a in listed):
        out.append("P6: no 'durable fix' action: say what stops a recurrence, apart from the mitigation")

    # P9: overclaims.
    for word in overclaims(text):
        out.append(f"P9: {word!r} is a verdict; write the observation instead of the verdict (for example "
                   "'the test page reached on-call at 09:02Z'), or label it 'claimed', 'not proven' or "
                   "'not run'. Evidence next to the verdict does not clear it")
    return out


def bug_from(action, bug_id, feature, severity, environment, source):
    priority, urgency = SEVERITY[severity]
    criteria = []
    for n, criterion in enumerate(action["acceptance"], 1):
        given, when, then = GWT.match(criterion).groups()
        criteria.append({"id": f"{bug_id}.{n}", "given": given, "when": when, "then": then})
    notes = f"From the post-incident review {source}, action {action['id']}, severity {severity}."
    if action["fields"].get("kind", "").lower() == "missing alert":
        notes += " " + MONITORING
    bug = {"id": bug_id, "type": "bug", "parent": feature, "title": action["title"],
           "observed": action["fields"]["observed"], "expected": action["fields"]["expected"],
           "steps": action["steps"]}
    if environment:
        bug["environment"] = environment
    bug.update({"work": "build", "acceptance": criteria, "priority": priority, "urgency": urgency,
                "size": "S", "status": "draft"})
    owner = action["fields"].get("owner", "")
    if TO_ASSIGN.match(owner):
        # Grooming does not read "to assign" as a placeholder, so it stays out of 'owner'.
        notes += f" Owner {owner.rstrip('.')}."
    elif owner:
        bug["owner"] = owner
    bug["notes"] = notes
    return bug


def write_back(text, action_id, bug_id):
    """Put bug_id on the action's '- Backlog:' line, adding the line when it is missing."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if re.match(rf"^### +{action_id}:", line))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{2,3} ", lines[i])), len(lines))
    for i in range(start + 1, end):
        found = re.match(r"^(\s*)- Backlog:", lines[i])
        if found:
            lines[i] = f"{found.group(1)}- Backlog: {bug_id}"
            return "\n".join(lines)
    first = next((i for i in range(start + 1, end) if lines[i].startswith("- ")), start + 1)
    lines.insert(first, f"- Backlog: {bug_id}")
    return "\n".join(lines)


def replace_all(pairs):
    """Write each (path, content) to a temporary file beside its path, then replace the paths.
    When any temporary file cannot be written, no path is replaced and the temporary files go.
    Each temporary file takes the mode of the file it replaces (mkstemp creates it 0600).
    A path that is a symbolic link is resolved first, so the target is written and the link stays."""
    pairs = [(os.path.realpath(path), content) for path, content in pairs]
    temps = []
    try:
        for path, content in pairs:
            handle, temp = tempfile.mkstemp(dir=Path(path).parent, prefix=".pir-")
            temps.append(temp)
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                out.write(content)
            os.chmod(temp, stat.S_IMODE(os.stat(path).st_mode))
        for (path, _), temp in zip(pairs, temps):
            os.replace(temp, path)
    finally:
        for temp in temps:
            if os.path.exists(temp):
                os.unlink(temp)


def cmd_check(args):
    found = findings(Path(args.review).read_text(encoding="utf-8"))
    print("\n".join(found) or "pass")
    return 1 if found else 0


def cmd_bugs(args):
    text = Path(args.review).read_text(encoding="utf-8")
    found = [f for f in findings(text) if not f.startswith("P8:")]
    data = json.loads(Path(args.backlog).read_text(encoding="utf-8"))
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or data.get("contract") != "backlog/v1":
        found.append(f"{args.backlog} is not a backlog/v1 file with an items list")
        items = []
    if not any(isinstance(i, dict) and i.get("id") == args.feature and i.get("type") == "feature" for i in items):
        found.append(f"{args.feature} is not a feature in {args.backlog}")
    if found:
        print("\n".join(found))
        return 1
    todo = [a for a in actions(sections(text)["Actions"]) if not BACKLOG_ID.search(a["fields"].get("backlog", ""))]
    if not todo:
        print("nothing to file: every action has a backlog ID")
        return 0
    numbers = [int(i["id"][2:]) for i in items
               if isinstance(i, dict) and re.fullmatch(r"B-\d+", str(i.get("id")))]
    next_number = max(numbers, default=0) + 1
    severity, environment = header(text, "Severity"), header(text, "Environment")
    title = re.search(r"^# +(?:Post-incident review:\s*)?(.+?)\s*$", text, re.M | re.I)
    source = f"'{title.group(1)}' ({Path(args.review).name})" if title else f"({Path(args.review).name})"
    report = []
    for n, action in enumerate(todo):
        bug_id = f"B-{next_number + n}"
        items.append(bug_from(action, bug_id, args.feature, severity, environment, source))
        text = write_back(text, action["id"], bug_id)
        priority, urgency = SEVERITY[severity]
        report.append(f"filed {action['id']} as {bug_id} under {args.feature} "
                      f"(draft, priority {priority}, urgency {urgency})")
    replace_all([(args.backlog, json.dumps(data, indent=2, ensure_ascii=False) + "\n"), (args.review, text)])
    print("\n".join(report))
    print("next: run backlog.py validate on the backlog, then pir_check.py check on the review")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="check the review against rules P1 to P9")
    c.add_argument("review")
    c.set_defaults(run=cmd_check)
    b = sub.add_parser("bugs", help="file each unfiled action as a draft bug and write the IDs back")
    b.add_argument("review")
    b.add_argument("--backlog", required=True, help="backlog/v1 file (grooming's backlog.json)")
    b.add_argument("--feature", required=True, help="feature ID the bugs go under, such as F-2")
    b.set_defaults(run=cmd_bugs)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

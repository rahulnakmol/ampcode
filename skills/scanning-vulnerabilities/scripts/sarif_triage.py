#!/usr/bin/env python3
"""Merge scanner SARIF into one findings report, state coverage, and check the triaged report.

  python3 sarif_triage.py merge [--root DIR] CATEGORY=FILE.sarif ... > report.md
  python3 sarif_triage.py coverage [--root DIR] CATEGORY=FILE.sarif ...
  python3 sarif_triage.py check [--today YYYY-MM-DD] report.md

CATEGORY is one of code, dependencies, secrets, iac, containers. Give one CATEGORY=FILE pair per
SARIF file; a category may have several files. --root strips an absolute scan folder from file
paths, so that absolute and relative paths from different tools compare.

merge prints a Markdown report: a Coverage section and a Findings table. Results with the same
normalized path, start line and CWE become one finding that lists every tool. Merges chain: a
result that shares one CWE with each of two findings joins them into one. Results without a
CWE merge only when the tool and the rule ID also match. coverage prints the Coverage section
only: each category is "scanned, N findings from M results (tools)" or "not examined". Each
tool shows the version its SARIF names ("version per SARIF: ..."), which can be wrong.

check reads a triaged report. It reads every table under "## Findings", so findings may be
split into several tables, each with the findings columns. It exits 0 and prints "pass", or
exits 1 and prints one line per broken rule:
  C1  every finding has a disposition: to fix, fixed, accepted or false positive
  C2  an accepted finding names a person as owner (not a team or role, not TBD, n/a, none or a
      similar placeholder)
  C3  a false positive gives its reason
  C4  a fixed Critical or High finding gives retest evidence in one form:
      "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>", for example
      "Rescan Bandit 1.9.4 2026-11-21: 0 results at app.py:24". The name has a letter or digit
      and is not a placeholder (TBD). The date is not after today (--today, default today's
      UTC date). The result is not empty, not only "failed", and not a placeholder or a phrase
      saying the run did not happen or finish (not run, not done, pending, TBD, failed to
      start, to follow, awaiting, planned, scheduled, yet, n/a, none, skipped, cancelled,
      errored, aborted, will, expected, to be run, couldn't run). check reads only the form;
      a reviewer reads the content.
  C5  no overclaim: "secure", "secured", "securely", "no (known) vulnerabilities",
      "vulnerability-free" outside `code` and fenced blocks, also when the words wrap across
      lines ("no vulnerability scan" and "Secure Shell" are allowed)
  C6  a Coverage section names every category
  C7  Reachable and Exploitable are yes, no or not proven
  C8  Severity is Critical, High, Medium, Low or Info

Malformed SARIF or a bad argument gives one line and exit 1. Standard library only. The script
reads what the tools wrote. It cannot tell whether a tool saw every file, or whether a finding
is real.
"""

import argparse
import datetime
import json
import posixpath
import re
import sys
from urllib.parse import unquote, urlparse

CATEGORIES = ("code", "dependencies", "secrets", "iac", "containers")
SEVERITIES = ("Critical", "High", "Medium", "Low", "Info")
LEVELS = {"error": "High", "warning": "Medium", "note": "Low", "none": "Info"}
DISPOSITIONS = ("to fix", "fixed", "accepted", "false positive")
TRIAGE = ("yes", "no", "not proven")
EMPTY = ("", "-")
PLACEHOLDERS = ("tbd", "tba", "n/a", "na", "none", "unknown", "?", "todo", "owner")
# The one Retest form: "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>". check reads
# only the form; a reviewer reads the content.
RETEST_FORM_TEXT = "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>: <result>"
RETEST_FORM = re.compile(r"^(?:rescan|test|poc|ci)\s+(?P<name>\S.*?)\s+(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})"
                         r"\s*:(?P<result>.*)$", re.I | re.S)
# A name that is a placeholder: "Rescan TBD 2026-11-21: ...".
NO_NAME = re.compile(r"^(?:tbd|tba|tbc|todo|n/?a|none|unknown|tool|name|<[^<>]*>)$", re.I)
# A result that is a placeholder, says the run did not happen or finish, or is only "failed".
# "exploit failed, request rejected" says what failed, so it is a result.
NO_RESULT = re.compile(
    r"^(?:-+|\?+)$|^(?:(?:the\s+)?run\s+)?failed[.!]?$"
    r"|\b(?:not\s+run|not\s+done|pending|tbd|tba|todo|failed\s+to\s+start|to\s+follow|awaiting|planned"
    r"|scheduled|yet|n/a|none|unknown|skipped|cancell?ed|errored|aborted|will|expected|to\s+be\s+run"
    r"|(?:could\s*n['\u2019]?t|could\s+not|cannot|can['\u2019]?t)\s+(?:be\s+)?run)\b", re.I)
# An owner is a person, the same rule as threat-modelling and assessing-products. The name, the
# text before the first "(" or ",", is not a team or role word, does not start with a placeholder,
# and is not only <...>. Role text after it is free: "Dana Reyes (Platform Group lead)". But the
# rest may not be only a team word: "Finance (team)" and "IT, department" fail (TEAM_ONLY).
NOT_A_NAME = re.compile(
    r"^(?:the )?(?:owner|risk owner|security|someone|anyone|everyone|nobody|unassigned|us|we|they|me)$"
    r"|\b(?:team|group|department|squad|function|role)s?\b|^(?:tbd|todo|tbc|unknown)\b|^<[^<>]*>$", re.I)
TEAM_ONLY = re.compile(r"^\s*(?:team|group|department|squad|function)s?\s*\)?\s*$", re.I)
CWE = re.compile(r"\bcwe[-/:]\s*0*(\d+)", re.I)
OVERCLAIM = re.compile(  # "no vulnerability scan" and "Secure Shell" are honest wording, not claims
    r"\bsecur(?:e|ed|ely)\b(?!\s+shell\b)|\bvulnerability[-\s]+free\b|\bno\s+(?:known\s+)?vulnerabilities\b"
    r"|\bno\s+(?:known\s+)?vulnerability\b(?!\s+(?:scans?|scanners?|database|data|feeds?)\b)", re.I)
CODE_SPAN = re.compile(r"`[^`]*`")
COLUMNS = ("ID", "Severity", "Category", "Location", "CWE", "Rules", "Tools", "Title",
           "Reachable", "Exploitable", "Disposition", "Owner", "Reason", "Retest", "Threat")
CAVEAT = ("A category with 0 findings means its tools reported nothing on the paths they scanned. "
          "It is not proof that no flaw exists. Coverage is only what the listed tools read.")


class SarifError(Exception):
    pass


def severity(score, level):
    """Critical to Info from a security-severity score, else from the SARIF level."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return LEVELS.get(level, "Medium")
    return "Critical" if value >= 9 else "High" if value >= 7 else "Medium" if value >= 4 \
        else "Low" if value > 0 else "Info"


def cwes(*bags):
    """CWE numbers named in tags or cwe fields of property bags."""
    found = set()
    for bag in bags:
        if not isinstance(bag, dict):
            continue
        values = []
        for key in ("tags", "cwe", "cwes"):
            value = bag.get(key)
            values += value if isinstance(value, list) else [value]
        for value in values:
            if isinstance(value, str):
                found |= {int(n) for n in CWE.findall(value)}
    return frozenset(found)


def normalize(uri, base, root):
    """A file path from a SARIF URI: base joined, file:// stripped, --root removed, ./ dropped."""
    if base and not re.match(r"^[a-z][a-z0-9+.-]*:", uri, re.I) and not uri.startswith("/"):
        uri = base.rstrip("/") + "/" + uri
    if uri.lower().startswith("file:"):
        uri = urlparse(uri).path
    path = posixpath.normpath(unquote(uri).replace("\\", "/"))
    if root:
        root = posixpath.normpath(root)
        if path == root or path.startswith(root + "/"):
            path = path[len(root):].lstrip("/") or "."
    return path[2:] if path.startswith("./") else path


def load(path, category, root=None):
    """(tool label, results) for one SARIF file; raises SarifError with one clear reason."""
    def fail(reason):
        raise SarifError(f"{path}: not valid SARIF: {reason}")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except OSError as error:
        raise SarifError(f"{path}: cannot read: {error.strerror or error}")
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        fail(f"not JSON ({error})")
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        fail("no 'runs' list at the top level")
    tools, results = [], []
    for number, run in enumerate(data["runs"], 1):
        where = f"run {number}"
        try:  # any other wrong shape inside a run is one clear error, never a traceback
            driver = ((run or {}).get("tool") or {}).get("driver") if isinstance(run, dict) else None
            if not isinstance(driver, dict) or not isinstance(driver.get("name"), str) or not driver["name"]:
                fail(f"{where} has no tool.driver.name")
            raw = run.get("results", [])
            if not isinstance(raw, list):
                fail(f"{where} 'results' is not a list")
            version = driver.get("version") or driver.get("semanticVersion")
            # The version is what the SARIF says; it can be wrong (gitleaks writes v8.0.0).
            tools.append(f"{driver['name']}, version per SARIF: {version}" if version
                         else f"{driver['name']}, no version in SARIF")
            rules = {}
            for component in [driver, *(run["tool"].get("extensions") or [])]:
                for rule in (component.get("rules") or []) if isinstance(component, dict) else []:
                    if isinstance(rule, dict) and rule.get("id"):
                        rules.setdefault(rule["id"], rule)
            listed = driver.get("rules") if isinstance(driver.get("rules"), list) else []
            bases = {k: (v or {}).get("uri", "") for k, v in (run.get("originalUriBaseIds") or {}).items()
                     if isinstance(v, dict)}
            for index, item in enumerate(raw, 1):
                where = f"run {number} result {index}"
                if not isinstance(item, dict):
                    fail(f"{where} is not an object")
                rule_id = item.get("ruleId") or (item.get("rule") or {}).get("id")
                if not rule_id and isinstance(item.get("ruleIndex"), int) and 0 <= item["ruleIndex"] < len(listed):
                    rule_id = listed[item["ruleIndex"]].get("id")
                rule_id = rule_id or "(no rule ID)"
                if not isinstance(rule_id, str):
                    fail(f"{where} has a rule ID that is not a string")
                rule = rules.get(rule_id, {})
                place, line = "(no location)", 0
                locations = item.get("locations") or []
                physical = locations[0].get("physicalLocation") if locations else None
                if physical:
                    artifact = physical.get("artifactLocation") or {}
                    if artifact.get("uri"):
                        place = normalize(artifact["uri"], bases.get(artifact.get("uriBaseId")), root)
                    start = (physical.get("region") or {}).get("startLine")
                    line = start if isinstance(start, int) and start > 0 else 0
                props, rule_props = item.get("properties") or {}, rule.get("properties") or {}
                level = item.get("level") or (rule.get("defaultConfiguration") or {}).get("level") or "warning"
                score = props.get("security-severity", rule_props.get("security-severity"))
                message = (item.get("message") or {}).get("text") or rule_id
                results.append({
                    "tool": driver["name"], "rule": rule_id, "category": category, "path": place,
                    "line": line, "cwes": cwes(props, rule_props), "severity": severity(score, level),
                    "title": " ".join(message.split()) or rule_id,
                })
        except (AttributeError, KeyError, TypeError, IndexError, ValueError) as error:
            fail(f"{where} has an unexpected shape ({error.__class__.__name__})")
    return tools, results


def merge(results):
    """Findings: same path, line and a shared CWE; without CWE, also the same tool and rule."""
    groups = {}
    for result in results:
        groups.setdefault((result["path"], result["line"]), []).append(result)
    findings = []
    for (place, line), members in groups.items():
        clusters = []  # each: {"cwes": set, "keys": set, "results": list}
        for result in members:
            key = (result["tool"], result["rule"])
            if result["cwes"]:
                hits = [c for c in clusters if c["cwes"] & result["cwes"]]
            else:
                hits = [c for c in clusters if not c["cwes"] and key in c["keys"]]
            joined = {"cwes": set(result["cwes"]), "keys": {key}, "results": [result]}
            for hit in hits:
                clusters.remove(hit)
                joined["cwes"] |= hit["cwes"]
                joined["keys"] |= hit["keys"]
                joined["results"] = hit["results"] + joined["results"]
            clusters.append(joined)
        for cluster in clusters:
            found = cluster["results"]
            findings.append({
                "path": place, "line": line, "cwes": sorted(cluster["cwes"]), "results": found,
                "severity": min((r["severity"] for r in found), key=SEVERITIES.index),
                "categories": sorted({r["category"] for r in found}, key=CATEGORIES.index),
                "tools": sorted({r["tool"] for r in found}),
                "rules": sorted({r["rule"] for r in found}),
                "title": found[0]["title"],
            })
    findings.sort(key=lambda f: (SEVERITIES.index(f["severity"]), CATEGORIES.index(f["categories"][0]),
                                 f["path"], f["line"], f["rules"]))
    for number, finding in enumerate(findings, 1):
        finding["id"] = f"F{number}"
    return findings


def coverage(scans, findings):
    """The Coverage section as lines."""
    lines = ["## Coverage", ""]
    missing = []
    for category in CATEGORIES:
        mine = [s for s in scans if s["category"] == category]
        if not mine:
            lines.append(f"- {category}: not examined")
            missing.append(category)
            continue
        count = sum(category in f["categories"] for f in findings)
        raw = sum(len(s["results"]) for s in mine)
        tools = "; ".join(sorted({t for s in mine for t in s["tools"]}))
        lines.append(f"- {category}: scanned, {count} finding{'s' * (count != 1)} from "
                     f"{raw} result{'s' * (raw != 1)} ({tools})")
    lines.append("")
    if missing:
        lines += [f"Not examined: {', '.join(missing)}. Say why for each in the report.", ""]
    return lines + [CAVEAT, ""]


def cell(text):
    return text.replace("|", "\\|").replace("`", "'").strip()


def report(scans, findings):
    lines = ["# Scan findings", "", "## Sources", ""]
    for scan in scans:
        lines.append(f"- {scan['category']}: `{cell(scan['file'])}` ({'; '.join(scan['tools'])}; "
                     f"{len(scan['results'])} result{'s' * (len(scan['results']) != 1)})")
    lines += [""] + coverage(scans, findings) + ["## Findings", "",
                                                  "| " + " | ".join(COLUMNS) + " |",
                                                  "|" + " --- |" * len(COLUMNS)]
    for f in findings:
        place = f"{f['path']}:{f['line']}" if f["line"] else f["path"]
        title = cell(f["title"])
        title = title[:77] + "..." if len(title) > 80 else title
        row = [f["id"], f["severity"], ", ".join(f["categories"]), f"`{cell(place)}`",
               ", ".join(f"CWE-{n}" for n in f["cwes"]) or "-",
               ", ".join(f"`{cell(r)}`" for r in f["rules"]), ", ".join(cell(t) for t in f["tools"]),
               f"`{title}`", "not proven", "not proven", "", "", "", "", ""]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def scans_from(pairs, root):
    scans = []
    for pair in pairs:
        category, sep, path = pair.partition("=")
        if not sep or category not in CATEGORIES or not path:
            raise SarifError(f"{pair}: give CATEGORY=FILE.sarif with CATEGORY one of {', '.join(CATEGORIES)}")
        tools, results = load(path, category, root)
        scans.append({"category": category, "file": path, "tools": tools, "results": results})
    return scans


def retest_in_form(retest, today):
    """True when a Retest value is in the form "<Rescan|Test|PoC|CI> <tool or name> <YYYY-MM-DD>:
    <result>": a source word; a name with a letter or digit that is not a placeholder; a real date
    no later than today; and a result that is not a placeholder, not only "failed", and not a
    phrase saying the run did not happen or finish ("not run", "skipped", "will run", "yet").
    A negative finding is a result: "Rescan Bandit 1.9.4 2026-11-21: no findings for B602"."""
    found = RETEST_FORM.match(retest.strip())
    if not found:
        return False
    name = found["name"].strip()
    if not re.search(r"[^\W_]", name) or NO_NAME.match(name):
        return False
    try:
        if datetime.date.fromisoformat(found["date"]) > today:
            return False
    except ValueError:
        return False
    result = found["result"].strip()
    return bool(result) and not NO_RESULT.search(result)


def iso_date(text):
    """An argparse type: a YYYY-MM-DD date."""
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            return datetime.date.fromisoformat(text)
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"{text!r} is not a YYYY-MM-DD date")


def is_person(owner):
    """True when the owner's name, before the first "(" or ",", names a person, and the rest is not only a
    team word ("Finance (team)", "IT, department")."""
    name, *rest = re.split(r"[(,]", owner, maxsplit=1)
    name = name.strip()
    return bool(name) and not NOT_A_NAME.search(name) and not (rest and TEAM_ONLY.match(rest[0]))


def section(text, title):
    found = re.search(rf"^## {re.escape(title)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return found.group(1) if found else None


def prose_of(text):
    """The text with closed fenced blocks and code spans blanked; line breaks are kept.

    A code span crosses a line break only when both lines have an odd number of backticks, so a
    stray backtick cannot hide the next line."""
    lines, out, i = text.split("\n"), [], 0
    blank = lambda m: "\0" + "\n" * m.group(0).count("\n")
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            end = next((j for j in range(i + 1, len(lines)) if lines[j].lstrip().startswith("```")), None)
            if end is not None:
                out += ["\0"] * (end - i + 1)
                i = end + 1
                continue
        if lines[i].count("`") % 2 and i + 1 < len(lines) and lines[i + 1].count("`") % 2:
            out.append(CODE_SPAN.sub(blank, lines[i] + "\n" + lines[i + 1]))
            i += 2
            continue
        out.append(CODE_SPAN.sub(blank, lines[i]))
        i += 1
    return "\n".join(out)


def check(text, today):
    problems = []
    add = lambda rule, message: problems.append(f"{rule}: {message}")
    body = section(text, "Findings")
    rows = []
    if body is None:
        add("C1", "no '## Findings' section with the findings table")
    else:
        tables, table = [], None  # every table in the section, so split tables are all read
        for line in body.splitlines():
            if line.strip().startswith("|"):
                if table is None:
                    table = []
                    tables.append(table)
                table.append(line.strip())
            else:
                table = None
        split = lambda row: [c.strip() for c in re.split(r"(?<!\\)\|", row.strip("|"))]
        if not tables:
            add("C1", "no findings table under '## Findings'")
        for number, table in enumerate(tables, 1):
            head = split(table[0])
            missing = [c for c in ("ID", "Severity", "Reachable", "Exploitable", "Disposition", "Owner",
                                   "Reason", "Retest") if c not in head]
            if missing:
                add("C1", f"table {number} under Findings needs the columns {', '.join(missing)}")
            else:
                rows += [dict(zip(head, split(r))) for r in table[2:]]
    for row in rows:
        ident = row.get("ID") or "a finding"
        value = lambda name: (row.get(name) or "").strip()
        disposition = value("Disposition").lower()
        if disposition not in DISPOSITIONS:
            add("C1", f"{ident} has no disposition; use one of {', '.join(DISPOSITIONS)}")
        owner = value("Owner")
        if disposition == "accepted" and (owner.lower().rstrip(".") in EMPTY + PLACEHOLDERS
                                          or not is_person(owner)):
            add("C2", f"{ident} is accepted without a named person as owner; name who accepts the "
                      "risk, not a team or role")
        if disposition == "false positive" and value("Reason") in EMPTY:
            add("C3", f"{ident} is a false positive without a reason; say why it is not real")
        level = value("Severity").capitalize()
        if level not in SEVERITIES:
            add("C8", f"{ident} Severity must be one of {', '.join(SEVERITIES)}; "
                      "put a raised or lowered severity's reason in the Reason column")
        if disposition == "fixed" and level in ("Critical", "High") and not retest_in_form(value("Retest"), today):
            add("C4", f"{ident} is a fixed {value('Severity')} without retest evidence; write the Retest "
                      f"as {RETEST_FORM_TEXT}, for example 'Rescan Bandit 1.9.4 2026-11-21: 0 results'")
        for name in ("Reachable", "Exploitable"):
            if value(name).lower() not in TRIAGE:
                add("C7", f"{ident} {name} must be yes, no or not proven")
    prose = prose_of(text)  # matched as a whole, so a phrase wrapped across lines is caught
    for match in OVERCLAIM.finditer(prose):
        number = prose.count("\n", 0, match.start()) + 1
        add("C5", f"line {number} says {' '.join(match.group(0).split())!r}; state coverage and "
                  "findings instead (scanned, 0 findings; not examined; not proven)")
    cover = section(text, "Coverage")
    if cover is None:
        add("C6", "no '## Coverage' section; run sarif_triage.py coverage and paste it")
    else:
        for category in CATEGORIES:
            if not re.search(rf"^- {category}: (?:scanned, \d+ findings?|not examined)", cover, re.M):
                add("C6", f"Coverage does not state {category} as 'scanned, N findings' or 'not examined'")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("merge", "coverage"):
        sub = commands.add_parser(name)
        sub.add_argument("--root", help="absolute scan folder to strip from file paths")
        sub.add_argument("scans", nargs="+", metavar="CATEGORY=FILE.sarif")
    sub = commands.add_parser("check")
    sub.add_argument("--today", type=iso_date, metavar="YYYY-MM-DD",
                     default=datetime.datetime.now(datetime.timezone.utc).date(),
                     help="today's date for the C4 rule that a Retest date is not after today "
                          "(default: today's UTC date)")
    sub.add_argument("report")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            try:
                with open(args.report, encoding="utf-8") as handle:
                    text = handle.read()
            except OSError as error:
                raise SarifError(f"{args.report}: cannot read: {error.strerror or error}")
            problems = check(text, args.today)
            print("\n".join(problems) or "pass")
            return 1 if problems else 0
        scans = scans_from(args.scans, args.root)
    except SarifError as error:
        print(f"error: {error}")
        return 1
    findings = merge([r for s in scans for r in s["results"]])
    if args.command == "coverage":
        print("\n".join(coverage(scans, findings)).rstrip())
    else:
        print(report(scans, findings), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())

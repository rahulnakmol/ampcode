#!/usr/bin/env python3
"""Check an SLO file and print the burn-rate alerts for each SLO.

  python3 slo_check.py check slos.json             # format, runbooks and firing evidence
  python3 slo_check.py check --release slos.json   # also fails on every alert that is not proven
  python3 slo_check.py alerts slos.json            # error budget and the fast and slow alert pairs
  python3 slo_check.py --help

check prints "pass", then one status line per SLO and per alert, and exits 0. Otherwise it
exits 1 and prints each problem as "<rule>: <what to fix>", one line per problem. Both commands
exit 2 on a usage error or an unreadable file. Standard library only. The file format is in
../SKILL.md and ../templates/slos.json; the alert pairs are in ../reference/burn-rates.md.

  M1  a target is not a number above 0 and below 100, or window_days is not a whole number above 0
  M2  an SLI has no NFR ID (NFR-n), or no good or valid events
  M3  an SLO has no burn-rate alerts, or lacks a page alert equal to each pair in PAIRS (the fast
      and slow pairs); extra alerts, such as ticket pairs, are allowed
  M4  an alert has no valid severity (page, ticket), burn rate or windows (like 5m, 1h, 3d), its
      short window is not shorter than its long window, its long window is not shorter than the
      SLO window, or it can never fire (burn rate x error budget of 100 % or more)
  M5  an alert's runbook file is missing (the path is relative to the SLO file's folder)
  M6  with --release: an alert has no firing evidence, so it is not proven
  M7  firing evidence comes from production, or misses its environment, date (YYYY-MM-DD, not in
      the future) or evidence reference. Production: any name with prod, prd or go-live in it
      (prod1, eu-prod, ProdEU, aksprod01, golive), except pre-prod, non-prod, pre-go-live,
      product and reproduce; and live,
      canary, blue, green or shadow, unless a test word (staging, stage, test, dev, qa, uat,
      sandbox, lab, ci, demo) is also in the name, as in staging-green. Any other name, such as
      eu-west-1, primary or main, counts as outside production: name environments so they say
      what they are
  M8  the SLO file or a runbook claims an alert works or is verified; record where and when it
      fired instead. Fine: questions; a negation earlier in the same sentence part, up to
      . ! ? : ; ("we have not, as of today, verified the alert"); a condition in the same comma
      clause ("if the alert works, close it"); and "working hours". "Nobody doubts that the
      alert works" is a claim
  M9  structure: invalid JSON, no SLOs, or a missing or repeated SLO or alert ID

An alert counts as proven only when it has firing evidence from outside production. The check
reads the evidence record; it cannot prove that the evidence is true or that an alert reaches
the right person.
"""

import argparse
import datetime
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

# The Google SRE Workbook's page-level pairs (table 5-8): name, severity, burn rate, long, short.
PAIRS = (
    ("fast", "page", Decimal("14.4"), "1h", "5m"),
    ("slow", "page", Decimal("6"), "6h", "30m"),
)
SEVERITIES = ("page", "ticket")
# prod, prd or golive anywhere in a word is production (prod1, euprod, aksprod01, production,
# golive), except after pre, non or not (preprod, nonprod, pregolive) and in product...,
# reproduc... and prodigy. "go-live" split by a separator is checked in production().
PRODUCTION = re.compile(r"(?<!pre)(?<!non)(?<!not)(?:pro?d(?!uc(?!tion)|ig)|golive)")
# Whole words for production or a deployment that serves production traffic. They count only
# when no TEST_WORDS word is in the name: staging-green is a staging slot.
PRODUCTION_WORDS = ("live", "canary", "blue", "green", "bluegreen", "shadow")
TEST_WORDS = ("staging", "stage", "test", "dev", "qa", "uat", "sandbox", "lab", "ci", "demo")
NOT_PRODUCTION = ("pre", "non", "not")  # "pre-prod", "non-production", "pre-live"
MINUTES = {"m": 1, "h": 60, "d": 1440}
UNIT_WORDS = {"m": "minute", "h": "hour", "d": "day"}
NFR = re.compile(r"NFR-[1-9]\d*")  # architecting issues NFR-1, NFR-2 ...
SUBJECT = r"(?:alert(?:s|ing)?(?:-\d+)?|alarms?|rules?|monitors?)"
OVERCLAIM = re.compile(
    # "ALERT-1 works", "the alert is verified", "Alerts: working", "alert confirmed working"
    rf"\b{SUBJECT}\b[\s:]+(?:(?:now|is|are|all|been|has|have|was|were|confirmed|tested|and)\s+)*"
    r"(?:works?|worked|working(?!\s+(?:hours?|days?|weeks?|time)\b)|verified|tested\s+and\s+working)\b"
    # "we verified the alert", "Verified: ALERT-1"
    rf"|\bverified[\s:]+(?:that\s+)?(?:(?:the|all|our|every)\s+)?{SUBJECT}\b",
    re.I)
# A negation covers a claim anywhere later in its sentence part, which ends at . ! ? : ; or a
# line break, not at a comma: "We have not, as of today, verified the alert." A negation followed
# by a doubt word affirms the claim instead: "Nobody doubts that the alert works."
NEGATION = re.compile(r"\b(?:not|never|nobody|no\s+one|cannot)\b|n't\b", re.I)
DOUBT = re.compile(r"\b(?:doubts?|doubted|questions?|questioned|disputes?|disputed|deny|denies|denied)\b", re.I)
# A condition covers a claim only inside its own comma clause: "If the alert works, close it"
# is honest; "Once deployed, the alert works." is a claim.
CONDITION = re.compile(r"\b(?:if|whether|when|once|unless|until)\b", re.I)
PART_ENDS = ".!?:;\n"


def number(value):
    """A Decimal for an int or a JSON float; None for anything else (bool and text included)."""
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None
    return Decimal(value)


def text(value):
    return value.strip() if isinstance(value, str) else ""


def show(value):
    """A Decimal without exponent or trailing zeros: 43.20 -> 43.2, 1E+2 -> 100."""
    value = value.normalize()
    return format(value, "f") if value != value.to_integral() else str(int(value))


def error_budget_minutes(target, window_days):
    """Minutes of full outage the SLO allows: (100 - target) % of the window."""
    return (Decimal(100) - Decimal(target)) / 100 * window_days * 1440


def minutes(window):
    match = re.fullmatch(r"([1-9]\d*)([mhd])", window) if isinstance(window, str) else None
    return int(match.group(1)) * MINUTES[match.group(2)] if match else None


def words(window):
    amount, unit = int(window[:-1]), window[-1]
    return f"{amount} {UNIT_WORDS[unit]}{'' if amount == 1 else 's'}"


def production(environment):
    """True when an environment name says production: 'prod-eu', 'eu-prod1', 'ProdEU', 'golive',
    'canary', but not 'pre-prod', 'nonprod', 'pre-live' or 'staging-green'. This is a list of
    production names, so a name that matches none of them, such as 'eu-west-1', 'primary' or
    'main', counts as outside production. Name environments so they say what they are."""
    words = re.findall(r"[a-z]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", environment).lower())
    test = any(word in TEST_WORDS for word in words)
    for index, word in enumerate(words):
        previous = words[index - 1] if index else ""
        go_live = word == "live" and previous == "go"
        negator = (words[index - 2] if index > 1 else "") if go_live else previous
        if negator in NOT_PRODUCTION:
            continue  # pre-prod, non-production, pre-live, pre-go-live
        if PRODUCTION.search(word) or go_live or (word in PRODUCTION_WORDS and not test):
            return True
    return False


def negated(part):
    """True when the last negation in part covers what follows it, which a doubt word after it
    undoes ("nobody doubts that")."""
    hits = list(NEGATION.finditer(part))
    return bool(hits) and not DOUBT.search(part, hits[-1].end())


def overclaims(content):
    """Claims that an alert works or is verified. Skips a claim in a question, after a negation
    in the same sentence part, or after a condition in the same comma clause."""
    found = []
    for match in OVERCLAIM.finditer(content):
        part = content[max(content.rfind(mark, 0, match.start()) for mark in PART_ENDS) + 1:match.start()]
        clause = part[part.rfind(",") + 1:]
        ends = [i for i in (content.find(mark, match.end()) for mark in ".!?\n") if i != -1]
        end = min(ends) if ends else len(content)
        if content[end:end + 1] == "?" or negated(part) or CONDITION.search(clause):
            continue
        found.append(match.group(0))
    return found


def objective(slo, add):
    """(target, window_days) when both are valid; adds M1 otherwise."""
    sid = slo.get("id")
    target, days = number(slo.get("target")), slo.get("window_days")
    ok = True
    if target is None or not 0 < target < 100:
        add("M1", f"{sid} target {slo.get('target')!r} must be a number above 0 and below 100 (99.9 means 99.9 %)")
        ok = False
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        add("M1", f"{sid} window_days {days!r} must be a whole number of days above 0")
        ok = False
    return (target, days) if ok else (None, None)


def check_alert(sid, item, target, days, base, release, add, status):
    aid = item.get("id")
    burn = number(item.get("burn_rate"))
    long_, short = minutes(item.get("long_window")), minutes(item.get("short_window"))
    broken = []
    if item.get("severity") not in SEVERITIES:
        broken.append(f"severity must be one of {', '.join(SEVERITIES)}")
    if burn is None or burn <= 0:
        broken.append("burn_rate must be a number above 0")
    if long_ is None or short is None:
        broken.append("long_window and short_window must look like 5m, 1h or 3d")
    elif short >= long_:
        broken.append("short_window must be shorter than long_window")
    elif days and long_ >= days * 1440:
        broken.append(f"long_window must be shorter than the SLO window of {days} days")
    if burn and burn > 0 and target is not None and burn * (100 - target) >= 100:
        never = f"can never fire: {show(burn)} x {show(100 - target)} % needs 100 % errors or more"
        if any(matches(pair, item) for pair in PAIRS):
            never += ("; the target is too low for the pairs: the owner raises the target, or the mission "
                      "changes PAIRS for every service (see 'Low targets' in reference/burn-rates.md)")
        else:
            never += "; use a lower burn rate or remove this alert"
        broken.append(never)
    if broken:
        add("M4", f"{aid} ({sid}): " + "; ".join(broken))

    runbook = text(item.get("runbook"))
    path = base / runbook if runbook else None
    if not path or not path.is_file():
        add("M5", f"{aid} ({sid}) needs a runbook file; '{runbook}' does not exist beside the SLO file")
    else:
        for claim in overclaims(path.read_text(encoding="utf-8", errors="replace")):
            add("M8", f"{runbook} says '{claim}'; record where and when the alert fired instead")

    firing = item.get("firing")
    if firing is None:
        status.append(f"  {aid}: not proven, no firing evidence from outside production")
        if release:
            add("M6", f"{aid} ({sid}) is not proven: record firing evidence from outside production before release")
        return
    if not isinstance(firing, dict):
        add("M7", f"{aid} firing must be an object with environment, date and evidence")
        return
    environment, date, evidence = text(firing.get("environment")), text(firing.get("date")), text(firing.get("evidence"))
    missing = [name for name, value in (("environment", environment), ("date", date), ("evidence", evidence)) if not value]
    if missing:
        add("M7", f"{aid} firing evidence needs {', '.join(missing)}")
        return
    if production(environment):
        add("M7", f"{aid} fired in '{environment}': firing evidence must come from outside production")
        return
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError(date)  # fromisoformat also takes 20261118 and 2026-W47-1
        day = datetime.date.fromisoformat(date)
    except ValueError:
        add("M7", f"{aid} firing date '{date}' must look like 2026-11-20")
        return
    if day > datetime.date.today():
        add("M7", f"{aid} firing date {date} is in the future")
        return
    status.append(f"  {aid}: fired in {environment} on {date} ({evidence})")


def matches(pair, item):
    """True when an alert is the pair: same severity, burn rate and windows (60m equals 1h)."""
    _, severity, burn, long_, short = pair
    return (isinstance(item, dict) and item.get("severity") == severity
            and number(item.get("burn_rate")) == burn
            and minutes(item.get("long_window")) == minutes(long_)
            and minutes(item.get("short_window")) == minutes(short))


def check(content, base, release=False):
    """(problems, status lines) for the SLO file text; runbook paths are relative to base."""
    problems, status = [], []

    def add(rule, message):
        problems.append(f"{rule}: {message}")

    try:
        data = json.loads(content, parse_float=Decimal)
    except json.JSONDecodeError as error:
        add("M9", f"the file is not valid JSON: {error}")
        return problems, status
    slos = data.get("slos") if isinstance(data, dict) else None
    if not isinstance(slos, list) or not slos or not all(isinstance(s, dict) for s in slos):
        add("M9", "the file needs a non-empty 'slos' list of objects")
        return problems, status
    for claim in overclaims(content):
        add("M8", f"the SLO file says '{claim}'; record where and when the alert fired instead")

    seen = set()
    for slo in slos:
        sid = slo.get("id")
        if not text(sid):
            add("M9", "every SLO needs an 'id', such as SLO-1")
            sid = "SLO-?"
        elif sid in seen:
            add("M9", f"{sid} appears twice; give each SLO its own ID")
        seen.add(sid)
        target, days = objective(slo, add)

        sli = slo.get("sli") if isinstance(slo.get("sli"), dict) else {}
        nfr = text(sli.get("nfr"))
        if not NFR.fullmatch(nfr):
            add("M2", f"{sid} SLI needs the NFR ID it measures, such as NFR-3 (has {nfr or 'none'})")
        for field in ("good", "valid"):
            if not text(sli.get(field)):
                add("M2", f"{sid} SLI needs '{field}' events described")
        if target is not None:
            status.append(f"{sid} from {nfr or 'no NFR'}: {show(target)} % over {days} days, error budget "
                          f"{show(error_budget_minutes(target, days))} minutes of full outage")

        alerts = slo.get("alerts")
        if not isinstance(alerts, list) or not alerts:
            add("M3", f"{sid} has no burn-rate alerts; run 'slo_check.py alerts' for the fast and slow pairs")
            continue
        for item in alerts:
            if not isinstance(item, dict) or not text(item.get("id")):
                add("M9", f"every alert of {sid} needs an 'id', such as ALERT-1")
                continue
            if item["id"] in seen:
                add("M9", f"{item['id']} appears twice; give each alert its own ID")
            seen.add(item["id"])
            check_alert(sid, item, target, days, base, release, add, status)
        missing = [pair for pair in PAIRS if not any(matches(pair, item) for item in alerts)]
        if missing:
            names = " and ".join(f"the {name} pair (page, {show(burn)}× over {words(long_)} and {words(short)})"
                                 for name, _, burn, long_, short in missing)
            add("M3", f"{sid} lacks {names}; add a page alert equal to each pair")
    return list(dict.fromkeys(problems)), status  # a runbook shared by two alerts is reported once


def alerts(content):
    """(problems, output lines): the error budget and the PAIRS for each SLO."""
    problems, lines = [], []

    def add(rule, message):
        problems.append(f"{rule}: {message}")

    try:
        data = json.loads(content, parse_float=Decimal)
    except json.JSONDecodeError as error:
        return [f"M9: the file is not valid JSON: {error}"], lines
    slos = data.get("slos") if isinstance(data, dict) else None
    if not isinstance(slos, list) or not slos or not all(isinstance(s, dict) for s in slos):
        return ["M9: the file needs a non-empty 'slos' list of objects"], lines
    for slo in slos:
        target, days = objective(slo, add)
        if target is None:
            continue
        sli = slo.get("sli") if isinstance(slo.get("sli"), dict) else {}
        budget = 100 - target
        window = days * 1440
        lines += [
            f"{slo.get('id')} ({text(sli.get('nfr')) or 'no NFR'}): {show(target)} % over {days} days. "
            f"Error budget: {show(budget)} % of valid events, "
            f"{show(error_budget_minutes(target, days))} minutes of full outage.",
            "",
            "| Pair | Severity | Burn rate | Long window | Short window | Error rate above | Budget spent when it fires |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for name, severity, burn, long_, short in PAIRS:
            threshold = burn * budget
            spent = (burn * minutes(long_) / window * 100).quantize(Decimal("0.01"))
            rate = f"{show(threshold)} %" + (" (never fires: 100 % or more)" if threshold >= 100 else "")
            if minutes(long_) >= window:
                rate += " (long window not shorter than the SLO window)"
            lines.append(f"| {name} | {severity} | {show(burn)}× | {words(long_)} | {words(short)} | "
                         f"{rate} | {show(spent)} % |")
        lines.append("")
    return problems, lines


def main(argv):
    parser = argparse.ArgumentParser(prog="slo_check.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("check", help="check the SLO file")
    run.add_argument("--release", action="store_true", help="fail on every alert that is not proven")
    run.add_argument("file")
    commands.add_parser("alerts", help="print the error budget and alert pairs").add_argument("file")
    args = parser.parse_args(argv[1:])
    path = Path(args.file)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"error: cannot read {args.file}: {error}")
        return 2
    if args.command == "alerts":
        problems, lines = alerts(content)
        print("\n".join(problems) if problems else "\n".join(lines).rstrip())
        return 1 if problems else 0
    problems, status = check(content, path.resolve().parent, release=args.release)
    print("\n".join(problems) if problems else "\n".join(["pass", *status]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

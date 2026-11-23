#!/usr/bin/env python3
"""Freeze assessment weights, score products from cited evidence, and check a recommendation.

  python3 score.py freeze criteria.json
  python3 score.py score criteria.json scores.json [--expect sha256:<digest>] [--fit-gap]
  python3 score.py check recommendation.md [--criteria criteria.json]
  python3 score.py --help

freeze  Checks the criteria and writes a "frozen" block into criteria.json: each weight, a seal
        per weight and a digest of all weights. Prints the digest; record it in the decision
        trail. Refuses a second freeze.
score   Refuses to score before a freeze or after a frozen weight changed, naming the criterion.
        Otherwise prints the totals out of 100 (sum of weight x score / 5), the ranks, every
        score still "claimed", and the sensitivity check: each weight moved 10 points up and
        down (clamped to 0..100) with the other weights rescaled in proportion to keep 100; a
        criterion is flagged when the move changes the top-ranked product.
        --fit-gap reads a fit category per cell instead of a number ("fit": "configuration"),
        converts it by FIT_GAP_SCORES, and lists every "unresolved" fit as a gap.
check   Checks a recommendation file: a recommended product, the weights digest, a Conditions
        table whose every row has a condition and a named person as owner, and no overclaim.
        --criteria also requires the digest of the weights frozen in that criteria.json.

Exits 0 on pass. Exits 1 and prints one "<rule>: <what to fix>" line per problem. Exits 2 on a
usage error or an unreadable file. Standard library only. The file formats and the rules are in
../SKILL.md and ../reference/criteria.md; ../reference/example/ holds a worked example.

  F1  a criterion has no id or name, or an id appears twice
  F2  a weight is not a number from 0 to 100
  F3  the weights do not sum to 100
  F4  the criteria are already frozen
  S1  the weights are not frozen
  S2  a weight changed after the freeze, a criterion was added or removed, or the digest
      differs from the frozen one or from --expect
  S3  a score has no evidence, or its evidence has neither a YYYY-MM-DD date nor the word
      "undated" (write "undated, read YYYY-MM-DD" when the source has no date)
  S4  a score is not a number from 0 to 5
  S5  a product, a missing or unknown criterion, or a status other than verified or claimed
  G1  with --fit-gap: a cell without a fit category from FIT_GAP_SCORES
  R1  no "Recommended:" line
  R2  no "Weights digest: sha256:<64 hex>" line, or with --criteria, not the frozen weights' digest
  R3  no Conditions table with at least one row
  R4  a condition without its text, or no Owner column, or an owner who is not a named person.
      Only the name counts, the text before the first "(" or ",": it fails on a team or role word
      (team, group, department, squad, function, role), a placeholder (TBD, TODO, TBC, unknown at
      the start, or only <...>), or "the owner", "someone", "security" and similar, or when the text
      after the name is only a team word ("Finance (team)", "IT, department"). Role text after
      the name is free: "Dana Reyes (Platform Group lead)" and "Dana Reyes <dana@example.com>" pass
  R5  an overclaim: "secure", "secured", "securely"; "no" or "zero" (known) "vulnerabilities";
      "vulnerability free" or "risk free" (hyphen or space); "verified"; "compliant". Not claims:
      "Secure Shell", "secure cookie", "no vulnerability scan" (or scanning, scanner, test,
      database, data, feed). A negation just before the word makes an honest label: "not" or
      "never" (one word may sit between, but not only, just or merely), "nothing" (up to two
      words between), "cannot be" or "cannot be called": "not secure", "not yet verified",
      "never verified", "cannot be verified yet". "compliant" also passes when labelled as a
      claim ("claims to be SOC 2 compliant", "claimed compliant") or as "non-compliant".
      "verified" also passes as the score status name, quoted: `verified` or "verified".

The freeze is tamper-evident, not tamper-proof: anyone can freeze again. The digest recorded in
the decision trail, passed as --expect, is what binds the scores to the agreed weights.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCALE = 5  # scores run from 0 to SCALE
SHIFT = 10  # sensitivity: weight points moved up and down
STATUSES = ("verified", "claimed")
PLACEHOLDER = re.compile(r"^(?:|-+|\?+|tbd|tbc|todo|n/?a|none|unknown|later|owner|unassigned|<[^>]*>)$", re.I)
# An owner is a person. The name, the text before the first "(" or ",", is not a team or role word, does
# not start with a placeholder, and is not only <...>. Role text after it is free: "Dana Reyes (Platform Group lead)".
# But the rest may not be only a team word: "Finance (team)" and "IT, department" fail (TEAM_ONLY).
# The same rule as threat-modelling's owner check.
NOT_A_NAME = re.compile(
    r"^(?:the )?(?:owner|risk owner|security|someone|anyone|everyone|nobody|unassigned|us|we|they|me)$"
    r"|\b(?:team|group|department|squad|function|role)s?\b|^(?:tbd|todo|tbc|unknown)\b|^<[^<>]*>$", re.I)
TEAM_ONLY = re.compile(r"^\s*(?:team|group|department|squad|function)s?\s*\)?\s*$", re.I)
# Overclaims, as in threat-modelling: "secure", "no (known) vulnerabilities", "vulnerability free", "risk free"
# and "verified"; this skill adds "compliant".
# Not a claim: "Secure Shell", "secure cookie", "no vulnerability scan" (or test, data, feed).
OVERCLAIM = re.compile(
    r"\bsecur(?:e|ed|ely)\b(?![-\s]+(?:shell|cookies?)\b)"
    r"|\b(?:no|zero)\s+(?:known\s+)?vulnerabilit(?:y|ies)\b(?!\s+(?:scan|scanning|scanner|test|database|data|feed)s?\b)"
    r"|\bvulnerabilit(?:y|ies)[-\s]free\b|\brisk[-\s]free\b|\bverified\b|\bcompliant\b", re.I)
# An honest negation right before the word: "not secure yet", "not yet compliant", "never verified",
# "nothing here is secure", "cannot be verified yet", "cannot be called compliant". "not only", "not just",
# "not merely" do not negate.
NEGATED = re.compile(
    r"(?:\b(?:not|never)\s+(?:(?!(?:only|just|merely)\b)\w+\s+)?|\bnothing\s+(?:\w+\s+){0,2}"
    r"|\bcannot\s+be\s+(?:called\s+)?)$", re.I)
# "compliant" labelled as a claim: "claims to be SOC 2 compliant", "claimed compliant"; or "non-compliant".
CLAIMED = re.compile(r"(?:\b(?:claim(?:s|ed)?|says|said|states|stated)\b(?:\s+\S+){0,4}\s+|\bnon-)$", re.I)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
# Evidence needs a full date or the word "undated" (SKILL.md section 3). A borrowed date passes: only a reader
# can catch that.
DATED = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)|\bundated\b", re.I)
EPSILON = 1e-9
# --fit-gap: score per fit category. The categories are defined in blueprinting's
# reference/proposals.md; this map only scores them. Shown as a table in shaping-engagements.
FIT_GAP_SCORES = {"supported": 5, "configuration": 4, "extension": 3, "integration": 3, "process change": 2,
                  "unresolved": 0}
GAP = "unresolved"


class Unreadable(Exception):
    pass


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"cannot read {path}: {error}") from error


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def seal(cid, weight):
    return hashlib.sha256(f"{cid}={float(weight)!r}".encode()).hexdigest()[:16]


def digest(weights):
    canonical = json.dumps(sorted((cid, float(w)) for cid, w in weights.items()), separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------- freeze


def criteria_problems(data):
    """F1 to F3 for {"criteria": [{"id", "name", "weight"}, ...]}."""
    out = []
    items = data.get("criteria") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return ["F1: criteria.json needs a non-empty \"criteria\" list"]
    seen = set()
    for i, item in enumerate(items, 1):
        item = item if isinstance(item, dict) else {}
        cid = item.get("id")
        label = repr(cid) if isinstance(cid, str) and cid.strip() else f"number {i}"
        name = item.get("name")
        if not (isinstance(cid, str) and cid.strip()) or not (isinstance(name, str) and name.strip()):
            out.append(f"F1: criterion {label} needs an id and a name")
        elif cid in seen:
            out.append(f"F1: criterion id {cid!r} appears twice")
        if isinstance(cid, str):
            seen.add(cid)
        weight = item.get("weight")
        if not number(weight) or not 0 <= weight <= 100:
            out.append(f"F2: criterion {label} weight {weight!r} must be a number from 0 to 100")
    weights = [item.get("weight") for item in items if isinstance(item, dict)]
    if all(number(w) for w in weights) and abs(sum(weights) - 100) > EPSILON:
        out.append(f"F3: the weights sum to {sum(weights):g}, not 100")
    return out


def current_weights(data):
    return {item["id"]: item["weight"] for item in data["criteria"]}


def freeze(data):
    """Return (frozen data, problems). Writes nothing."""
    problems = criteria_problems(data)
    if not problems and "frozen" in data:
        problems.append(f"F4: already frozen with {data['frozen'].get('digest')}; weights change only by a recorded "
                        "decision: record why, remove the frozen block, freeze again and record the new digest")
    if problems:
        return data, problems
    weights = current_weights(data)
    frozen = dict(data)
    frozen["frozen"] = {
        "weights": weights,
        "seals": {cid: seal(cid, w) for cid, w in weights.items()},
        "digest": digest(weights),
    }
    return frozen, []


# ---------------------------------------------------------------- score


def frozen_problems(data, expect=None):
    """S1 and S2: the criteria must be frozen and unchanged since. Names each changed criterion."""
    if not isinstance(data, dict) or not isinstance(data.get("frozen"), dict):
        return ["S1: the weights are not frozen; agree them, run 'score.py freeze criteria.json' and record the digest "
                "before any score"]
    frozen = data["frozen"]
    # A malformed part counts as empty, which reports every criterion as changed.
    weights, seals = (frozen.get(key) if isinstance(frozen.get(key), dict) else {} for key in ("weights", "seals"))
    out = [f"S2: {p.split(': ', 1)[1]}" for p in criteria_problems(data)]
    items = data.get("criteria") if isinstance(data.get("criteria"), list) else []
    now = {item.get("id"): item.get("weight") for item in items
           if isinstance(item, dict) and isinstance(item.get("id"), str)}
    for cid in now:
        if cid not in weights:
            out.append(f"S2: criterion {cid!r} was added after the freeze")
    for cid, weight in weights.items():
        if cid not in now:
            out.append(f"S2: criterion {cid!r} was removed after the freeze")
        elif not number(weight) or seals.get(cid) != seal(cid, weight):
            out.append(f"S2: frozen weight of {cid!r} does not match its seal: it changed after the freeze")
        elif not number(now[cid]) or abs(now[cid] - weight) > EPSILON:
            out.append(f"S2: weight of {cid!r} changed after the freeze: frozen {weight:g}, now {now[cid]!r}")
    if not out and frozen.get("digest") != digest(weights):
        out.append("S2: the frozen digest does not match the frozen weights; they changed after the freeze")
    if expect and frozen.get("digest") != expect:
        out.append(f"S2: frozen digest {frozen.get('digest')} is not the expected {expect} from the decision trail")
    return out


def fit_category(cell):
    fit = cell.get("fit")
    return fit.strip().lower() if isinstance(fit, str) else fit


def cell_score(where, cell, fit_gap=False):
    """(score, status, evidence, problems) for one product's score on one criterion.

    With fit_gap, the cell names a fit category and FIT_GAP_SCORES gives the score."""
    if not isinstance(cell, dict):
        return None, None, None, [f"S5: {where} must be an object with score, evidence and status"]
    out = []
    value, evidence, status = cell.get("score"), cell.get("evidence"), cell.get("status", "claimed")
    if fit_gap:
        fit = fit_category(cell)
        value = FIT_GAP_SCORES.get(fit) if isinstance(fit, str) else None
        if value is None:
            out.append(f"G1: {where} fit {cell.get('fit')!r} must be one of: {', '.join(FIT_GAP_SCORES)}")
    elif not number(value) or not 0 <= value <= SCALE:
        out.append(f"S4: {where} score {value!r} must be a number from 0 to {SCALE}")
    if not isinstance(evidence, str) or PLACEHOLDER.match(evidence.strip()):
        out.append(f"S3: {where} has no evidence; cite the document, test or source and its date")
    elif not DATED.search(evidence):
        out.append(f"S3: {where} evidence has no YYYY-MM-DD date; write the source's date, or 'undated, read "
                   "YYYY-MM-DD' when it has none")
    if status not in STATUSES:
        out.append(f"S5: {where} status {status!r} must be 'verified' or 'claimed'")
    return value, status, evidence, out


def read_scores(weights, data, fit_gap=False):
    """(table {product: {criterion: score}}, claimed [(product, criterion, score, evidence)], problems)."""
    products = data.get("products") if isinstance(data, dict) else None
    if not isinstance(products, list) or not products:
        return {}, [], ["S5: scores.json needs a non-empty \"products\" list"]
    table, claimed, out = {}, [], []
    for i, product in enumerate(products, 1):
        product = product if isinstance(product, dict) else {}
        name, cells = product.get("name"), product.get("scores")
        if not isinstance(name, str) or not name.strip() or name in table:
            out.append(f"S5: product number {i} needs a unique name")
            continue
        cells = cells if isinstance(cells, dict) else {}
        table[name] = {}
        for cid in cells:
            if cid not in weights:
                out.append(f"S5: {name} scores unknown criterion {cid!r}")
        for cid in weights:
            if cid not in cells:
                out.append(f"S5: {name} has no score for {cid!r}; score it from evidence, 0 when it is absent")
                continue
            value, status, evidence, problems = cell_score(f"{name} {cid!r}", cells[cid], fit_gap)
            out += problems
            if not problems:
                table[name][cid] = value
                if status == "claimed":
                    claimed.append((name, cid, value, evidence))
    return table, claimed, out


def fit_gaps(weights, data):
    """[(product, criterion, evidence)] for each "unresolved" fit, from scores that read_scores accepted."""
    return [(product["name"], cid, product["scores"][cid]["evidence"]) for product in data["products"]
            for cid in weights if fit_category(product["scores"][cid]) == GAP]


def totals(weights, table):
    """Total out of 100 per product: sum of weight x score / SCALE."""
    return {name: sum(weights[cid] * s for cid, s in row.items()) / SCALE for name, row in table.items()}


def ranking(scores):
    """[(rank, product, total)], highest first; equal totals share a rank."""
    ordered = sorted(scores.items(), key=lambda item: -item[1])
    out = []
    for i, (name, total) in enumerate(ordered):
        rank = out[-1][0] if out and abs(out[-1][2] - total) <= EPSILON else i + 1
        out.append((rank, name, total))
    return out


def top(scores):
    best = max(scores.values())
    return sorted(name for name, total in scores.items() if best - total <= EPSILON)


def shifted(weights, cid, delta):
    """Weights with cid moved by delta, clamped to 0..100, and the others rescaled to keep 100."""
    new = min(100, max(0, weights[cid] + delta))
    others = [c for c in weights if c != cid]
    rest = sum(weights[c] for c in others)
    out = {}
    for c in weights:
        if c == cid:
            out[c] = new
        elif rest > EPSILON:
            out[c] = weights[c] * (100 - new) / rest
        else:  # the others had no points: share the freed points equally
            out[c] = (100 - new) / len(others)
    return out


def sensitivity(weights, table):
    """One row per criterion: the top product and totals after +SHIFT and -SHIFT, and a flag."""
    base = top(totals(weights, table))
    rows = []
    for cid in weights:
        row = {"criterion": cid}
        for key, delta in (("up", SHIFT), ("down", -SHIFT)):
            moved = totals(shifted(weights, cid, delta), table)
            row[key] = {"top": top(moved), "totals": moved}
        row["flag"] = row["up"]["top"] != base or row["down"]["top"] != base
        rows.append(row)
    return rows


def report(digest_value, weights, table, claimed, gaps=None):
    """The score report. gaps (from fit_gaps, with --fit-gap) adds the gap list."""
    lines = [f"Weights digest: {digest_value}", "Totals (out of 100):"]
    lines += [f"{rank}. {name} {total:.2f}" for rank, name, total in ranking(totals(weights, table))]
    if gaps is not None:
        lines.append(f"Gaps ({GAP}, scored {FIT_GAP_SCORES[GAP]}; each needs a named question or exception "
                     "and an owner):")
        lines += [f"- {name} {cid}: {GAP}; evidence: {evidence}" for name, cid, evidence in gaps] or ["- none"]
    lines.append("Unverified (claimed) scores; not proven until a document or test is seen:")
    lines += [f"- {name} {cid}: {value:g} claimed; evidence: {evidence}" for name, cid, value, evidence in claimed] \
        or ["- none"]
    lines.append(f"Sensitivity (each weight +{SHIFT} and -{SHIFT} points, clamped to 0..100; "
                 "the other weights rescaled in proportion to keep 100):")
    flagged = []
    for row in sensitivity(weights, table):
        line = f"- {row['criterion']}: +{SHIFT} {', '.join(row['up']['top'])}, -{SHIFT} {', '.join(row['down']['top'])}"
        if row["flag"]:
            flagged.append(row["criterion"])
            line += "  FLAG: the top rank changes"
        lines.append(line)
    lines.append(f"Flagged: {', '.join(flagged) or 'none'}")
    return lines


# ---------------------------------------------------------------- check


def section(text, title):
    found = re.search(rf"(?ms)^## {re.escape(title)}[ \t]*\n(.*?)(?=^## |\Z)", text)
    return found.group(1) if found else None


def is_person(owner):
    """True when the owner's name, before the first "(" or ",", names a person, and the rest is not only a
    team word ("Finance (team)", "IT, department")."""
    name, *rest = re.split(r"[(,]", owner, maxsplit=1)
    name = name.strip()
    return bool(name) and not NOT_A_NAME.search(name) and not (rest and TEAM_ONLY.match(rest[0]))


def overclaims(text):
    """Each claim word in text that is not labelled honestly, lower-cased, in order of first use."""
    found = []
    for match in OVERCLAIM.finditer(text):
        before, after, word = text[:match.start()], text[match.end():match.end() + 1], match.group(0).lower()
        if NEGATED.search(before):
            continue
        if word == "compliant" and CLAIMED.search(before):
            continue
        quote = before[-1:]
        if word == "verified" and quote != "" and quote in "`\"'" and quote == after:
            continue  # the score status name, quoted: `verified`, "verified" or 'verified'
        if word not in found:
            found.append(word)
    return found


def check_recommendation(text, criteria=None):
    """R1 to R5 for a recommendation. With criteria (a loaded criteria.json), R2 also requires the digest of
    its frozen weights."""
    out = []
    if not re.search(r"(?m)^Recommended:[ \t]*\S", text):
        out.append("R1: add a 'Recommended: <product>' line")
    match = re.search(r"(?m)^Weights digest:[ \t]*(\S*)[ \t]*$", text)
    if not match or not DIGEST.match(match.group(1)):
        out.append("R2: add a 'Weights digest: sha256:<64 hex>' line with the digest of the frozen weights")
    elif criteria is not None:
        frozen = criteria.get("frozen") if isinstance(criteria, dict) else None
        weights = frozen.get("weights") if isinstance(frozen, dict) else None
        if not isinstance(weights, dict) or not weights or not all(number(w) for w in weights.values()):
            out.append("R2: criteria.json is not frozen, so the weights digest cannot be checked")
        elif match.group(1) != digest(weights):
            out.append(f"R2: weights digest {match.group(1)} is not the digest of the frozen weights, "
                       f"{digest(weights)}")
    body = section(text, "Conditions")
    rows = [line.strip() for line in (body or "").splitlines() if line.strip().startswith("|")]
    cells = lambda row: [c.strip() for c in row.strip("|").split("|")]
    if len(rows) < 3:
        out.append("R3: add a '## Conditions' table (Condition | Owner | Due) with at least one condition")
    else:
        header = [c.lower() for c in cells(rows[0])]
        if "condition" not in header or "owner" not in header:
            out.append("R4: the Conditions table needs a Condition column and an Owner column")
        else:
            what, who = header.index("condition"), header.index("owner")
            for n, row in enumerate(rows[2:], 1):
                row = cells(row) + [""] * len(header)
                if PLACEHOLDER.match(row[what]):
                    out.append(f"R4: condition {n} has no text")
                if PLACEHOLDER.match(row[who]) or not is_person(row[who]):
                    out.append(f"R4: condition {n} owner {row[who]!r} is not a named person; name the person who "
                               "makes it true, for example 'Priya Shah (Head of Platform)'")
    for found in overclaims(text):
        out.append(f"R5: {found!r} overclaims; say what was checked and label the rest 'claimed', 'not proven' "
                   "or 'not examined'")
    return out


# ---------------------------------------------------------------- command line


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze", help="check the criteria and freeze their weights in place").add_argument("criteria")
    scoring = commands.add_parser("score", help="total, rank and test the sensitivity of frozen scores")
    scoring.add_argument("criteria")
    scoring.add_argument("scores")
    scoring.add_argument("--expect", help="the digest recorded in the decision trail")
    scoring.add_argument("--fit-gap", action="store_true",
                         help="each cell names a fit category; score it by FIT_GAP_SCORES and list the gaps")
    checking = commands.add_parser("check", help="check a recommendation file")
    checking.add_argument("recommendation")
    checking.add_argument("--criteria", help="the frozen criteria.json: the digest must be that of its frozen weights")
    args = parser.parse_args(argv)

    try:
        if args.command == "freeze":
            data, problems = freeze(load(args.criteria))
            if not problems:
                Path(args.criteria).write_text(json.dumps(data, indent=2) + "\n")
                print(f"frozen\nWeights digest: {data['frozen']['digest']}")
        elif args.command == "score":
            data = load(args.criteria)
            problems = frozen_problems(data, args.expect)
            if not problems:
                weights = data["frozen"]["weights"]
                scores = load(args.scores)
                table, claimed, problems = read_scores(weights, scores, args.fit_gap)
                if not problems:
                    gaps = fit_gaps(weights, scores) if args.fit_gap else None
                    print("\n".join(report(data["frozen"]["digest"], weights, table, claimed, gaps)))
        else:
            try:
                text = Path(args.recommendation).read_text()
            except (OSError, UnicodeDecodeError) as error:
                raise Unreadable(f"cannot read {args.recommendation}: {error}") from error
            problems = check_recommendation(text, load(args.criteria) if args.criteria else None)
            if not problems:
                print("pass")
    except Unreadable as error:
        print(error, file=sys.stderr)
        return 2
    print("\n".join(problems), end="\n" if problems else "")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

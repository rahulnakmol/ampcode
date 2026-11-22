#!/usr/bin/env python3
"""Check a threat model and render it as Markdown.

  python3 threat_check.py check model.json
  python3 threat_check.py render model.json > model.md

check exits 0 and prints "pass" when the model follows rules M1 to M12. Otherwise it exits 1 and
prints one line per broken rule as "<rule>: <what to fix>". render prints the model's tables as
Markdown and exits 0; it refuses a model that fails check (exit 1, the same lines). Standard
library only. The format and the rules are in ../reference/model.md.

The check proves the model is complete and consistent. It cannot prove that a threat list is
complete, that a mitigation works, or that a verification ran.
"""

import json
import re
import sys
from pathlib import Path

STRIDE = ("spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service",
          "elevation_of_privilege")
LINDDUN = ("linking", "identifying", "non_repudiation", "detecting", "data_disclosure", "unawareness",
           "non_compliance")
KINDS = ("actor", "process", "store", "external")
DISPOSITIONS = ("mitigate", "accept", "backlog")
RESULTS = ("met", "gap", "not applicable", "not examined")
# Standard name -> the form of its requirement references. To add a standard, add its form here
# and to reference/model.md. ASVS 4.0.3 has chapters V1 to V14: V<chapter>.<section>.<requirement>.
STANDARDS = {"OWASP ASVS 4.0.3": re.compile(r"V(?:[1-9]|1[0-4])\.[1-9]\d?\.[1-9]\d?")}
ITEM_ID = re.compile(r"[A-Z][A-Z0-9]*-\d+|#\d+")
PLACEHOLDER = re.compile(
    r"^(?:tbd|todo|tbc|n/?a|none|-+|\?+|later|<[^<>]*>|not relevant|not applicable|irrelevant|"
    r"handled elsewhere|does not apply)\.?$", re.I)
# An owner is a person. The name, the text before the first "(" or ",", is not a team or role word,
# does not start with a placeholder, and is not only <...>. Role text after it is free:
# "Dana Reyes (Platform Group lead)". But the rest may not be only a team word: "Finance (team)" and
# "IT, department" fail (TEAM_ONLY).
NOT_A_NAME = re.compile(
    r"^(?:the )?(?:owner|risk owner|security|someone|anyone|everyone|nobody|unassigned|us|we|they|me)$"
    r"|\b(?:team|group|department|squad|function|role)s?\b|^(?:tbd|todo|tbc|unknown)\b|^<[^<>]*>$", re.I)
TEAM_ONLY = re.compile(r"^\s*(?:team|group|department|squad|function)s?\s*\)?\s*$", re.I)
NOT_APPLICABLE = re.compile(r"^n/a:\s*(.*)$", re.S)
# "Not examined" is no reason for n/a unless the reason names the threat that carries it.
NOT_EXAMINED = re.compile(r"\b(?:not\s+|un)examined\b", re.I)
# Claim words. Not a claim: the exact word "secure" before a control noun ("Secure Shell", "secure
# cookie", "Secure Boot", "secure file transfer", "Secure flag"); "secured" and "securely" always are.
# Also not a claim: "no vulnerability scan" (or test, data, feed).
SECURE_NOUN = r"(?:shell|cookies?|flags?|attributes?|boot|file\s+transfer|sockets?|enclaves?)"
OVERCLAIM = re.compile(
    r"\bsecure\b(?![-\s]+" + SECURE_NOUN + r"\b)|\bsecur(?:ed|ely)\b"
    r"|\b(?:no|zero)\s+(?:known\s+)?vulnerabilit(?:y|ies)\b"
    r"(?!\s+(?:scan|scanning|scanner|test|database|data|feed)s?\b)"
    r"|\bvulnerabilit(?:y|ies)[-\s]free\b|\brisk[-\s]free\b|\bverified\b", re.I)
# An honest negation right before the word: "not secure yet", "not yet verified", "never verified",
# "nothing here is secure", "cannot be called secure". "not only", "not just", "not merely" do not negate.
NEGATED = re.compile(
    r"(?:\b(?:not|never)\s+(?:(?!(?:only|just|merely)\b)\w+\s+)?"
    r"|\bnothing\s+(?:\w+\s+){0,2}|\bcannot\s+be\s+called\s+)$", re.I)
# Text in backticks names something; it claims nothing: `Secure`. The check skips it in every field.
CODE_SPAN = re.compile(r"`[^`]*`")
# Quoted text ("...", \u201c...\u201d, '...') is read in every field, as the model's own words. It is
# skipped only right after a verb that names a third party's words (as score.py's CLAIMED): the vendor
# "calls it", "claims" or "claimed", "says" or "said", "states" or "stated" it. "marked" and
# "labelled" are not such verbs: the model could label itself. A single quote opens and closes only at
# a word edge, so "tenant's" and "API's" are not quotes.
QUOTED = re.compile(r"\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d|\u2018[^\u2019\n]*\u2019|(?<!\w)'[^'\n]*'(?!\w)")
THIRD_PARTY = re.compile(r"\b(?:calls\s+it|claims|claimed|says|said|states|stated)\s*:?\s*$", re.I)
# The model's author is not a third party: a quote stays read when one of these words appears in the
# same clause before the verb ("Our review says ...", "This model states ...", "We said ...").
AUTHOR = re.compile(r"\b(?:we|our|us|the\s+model|this\s+model|this\s+review|the\s+review|our\s+review|"
                    r"the\s+team)\b", re.I)
# The cookie attribute named in a list: "the Secure and HttpOnly flags", "the Secure, HttpOnly and
# SameSite=Strict attributes". Case-sensitive: only "Secure" written as a name.
ATTRIBUTE_LIST = re.compile(r"Secure(?:,?\s+(?:and|or|[A-Z][\w=-]*)){1,4},?\s+(?:flags?|attributes?)\b")
# In a threat's title, mitigation and verification, "verified" names a control only when, right after
# it, comes (a) with, against, using or by and then a means within three words (a means noun below, or
# a tool or version name: a word with a digit, a dot, or two or more capitals), with no team word in
# the rest of the clause; or
# (b) a noun from VERIFIED_NOUN, after at most a determiner: "verified with HMAC-SHA256", "verified
# against the old key", "verified the signature", "only verified tokens". Anything else is a claim.
VERIFIED_MEANS = re.compile(r"\s+(?:with|against|using|by)((?:\s+[\w.'-]+){1,3})", re.I)
MEANS_WORD = re.compile(r"(?:hmac|signatures?|checksums?|hash(?:es)?|digests?|keys?|certificates?|tests?|ci|"
                        r"scans?|scanners?|tools?|scripts?|schemas?|polic(?:y|ies)|rules?|pipelines?|runs?|jobs?)$",
                        re.I)
TOOL_WORD = re.compile(r"^(?=.*(?:\d|\w\.\w|[A-Z].*[A-Z]))[\w.-]+$")
TEAM_WORD = re.compile(r"\b(?:team|group|department|squad|function|staff|people|person|reviewers?)s?\b", re.I)
VERIFIED_NOUN = re.compile(r"\s+(?:(?:the|a|an|each|every|its|their|this|that)\s+)?(?:signatures?|tokens?|"
                           r"hash(?:es)?|checksums?|certificates?|signers?|ones?|inputs?|requests?|payloads?)\b",
                           re.I)
INTENSIFIED = re.compile(r"\b(?:fully|all|completely|formally|independently)\s+$", re.I)
DESCRIBED = ("title", "mitigation", "verification")
# A mitigation says whether a source states the control or the model proposes it.
MITIGATION = re.compile(r"^(?:existing\s*\((?=\s*[^\s)])[^)]*\)|planned)\s*:\s*\S", re.I)


def text(value):
    """True for a non-empty string that is not a placeholder."""
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.match(value.strip())


def known(value, ids):
    """True for a string ID in ids; a list or object is never an ID (and cannot be looked up)."""
    return isinstance(value, str) and value in ids


def is_person(owner):
    """True when the owner's name, before the first "(" or ",", names a person, and the rest is not only a
    team word ("Finance (team)", "IT, department")."""
    name, *rest = re.split(r"[(,]", owner, maxsplit=1)
    name = name.strip()
    return bool(name) and not NOT_A_NAME.search(name) and not (rest and TEAM_ONLY.match(rest[0]))


def verb_use(value, end):
    """True when the "verified" ending at end names a control (see VERIFIED_MEANS and VERIFIED_NOUN)."""
    means = VERIFIED_MEANS.match(value, end)
    if means:
        words = [w.strip(".,;:()'") for w in means.group(1).split()]
        clause = re.split(r"[.;:!?]\s", value[end:] + " ", maxsplit=1)[0]
        return not TEAM_WORD.search(clause) and any(
            MEANS_WORD.match(w) or TOOL_WORD.match(w) for w in words if w)
    return bool(VERIFIED_NOUN.match(value, end))


def third_party(before):
    """True when the text before a quote ends in a third-party verb whose clause names no author."""
    verb = THIRD_PARTY.search(before)
    if not verb:
        return False
    clause = re.split(r"[.;!?]\s", before[:verb.start()])[-1]
    return not AUTHOR.search(clause)


def overclaim(value, described=False):
    """The first claim word in value that is not negated or a control name, or None. Backtick spans are
    skipped; quoted text only right after a verb naming a third party's words (third_party). With
    described (a threat's title, mitigation or verification), "verified" naming a control passes
    (verb_use)."""
    value = CODE_SPAN.sub(" ", value)
    value = QUOTED.sub(lambda m: " " if third_party(value[:m.start()]) else m.group(0), value)
    for match in OVERCLAIM.finditer(value):
        before, word = value[:match.start()], match.group(0)
        if NEGATED.search(before) or ATTRIBUTE_LIST.match(value, match.start()):
            continue
        if described and word.lower() == "verified" and not INTENSIFIED.search(before) and verb_use(
                value, match.end()):
            continue
        return word
    return None


def prose(model):
    """(where, text) for each free-text field render prints. Evidence records (a threat's evidence and
    accepted, a review row's evidence) are left out: they are what backs a claim. Where ends with the
    field's key, so a threat's title, mitigation and verification can be told apart (DESCRIBED)."""
    dicts = lambda key: [x for x in model.get(key) or [] if isinstance(x, dict)] \
        if isinstance(model.get(key), list) else []
    for key in ("name", "scope", "summary"):
        yield key, model.get(key)
    for zone in dicts("zones"):
        yield f"zone {zone.get('id')} name", zone.get("name")
    for element in dicts("elements"):
        yield f"element {element.get('id')} name", element.get("name")
    for flow in dicts("flows"):
        yield f"flow {flow.get('id')} data", flow.get("data")
        for key in ("stride", "linddun"):
            for category, value in (flow.get(key) or {}).items() if isinstance(flow.get(key), dict) else []:
                yield f"flow {flow.get('id')} {key} '{category}'", value
    for threat in dicts("threats"):
        for key in ("title", "mitigation", "verification", "reason"):
            yield f"threat {threat.get('id')} {key}", threat.get(key)
    for case in dicts("abuse_cases"):
        for key in ("actor", "goal", "how"):
            yield f"abuse case {case.get('id')} {key}", case.get(key)
    for row in dicts("review"):
        yield f"review {row.get('ref')} reason", row.get("reason")
    lines = model.get("not_examined")
    for n, line in enumerate(lines if isinstance(lines, list) else []):
        yield f"not_examined[{n}]", line


def items(model, key, add):
    """The list model[key] of objects with an 'id', reporting a missing list or duplicate IDs."""
    found = model.get(key)
    if not isinstance(found, list) or not found:
        add("M1", f"'{key}' must be a non-empty list")
        return {}
    out = {}
    for n, entry in enumerate(found):
        if not isinstance(entry, dict) or not text(entry.get("id")):
            add("M1", f"{key}[{n}] needs an 'id'")
        elif entry["id"] in out:
            add("M1", f"{key} has duplicate id {entry['id']}")
        else:
            out[entry["id"]] = entry
    return out


def crosses(flow, elements):
    """True when the flow's two ends sit in different trust zones."""
    ends = [elements.get(flow.get(side)) if isinstance(flow.get(side), str) else None for side in ("from", "to")]
    return all(ends) and all(isinstance(e.get("zone"), str) for e in ends) and ends[0]["zone"] != ends[1]["zone"]


def categories(flow, key, names, threats, rule, add):
    """Each category is a non-empty list of known threat IDs, or 'n/a: <reason>'."""
    table = flow.get(key) if isinstance(flow.get(key), dict) else {}
    for name in names:
        value = table.get(name)
        where = f"flow {flow['id']} {key} '{name}'"
        if value is None:
            add(rule, f"{where} is missing: list threat IDs or write 'n/a: <reason>'")
        elif isinstance(value, str):
            match = NOT_APPLICABLE.match(value.strip())
            if not match or not text(match.group(1)):
                add(rule, f"{where} must be a list of threat IDs or 'n/a: <reason>', not {value!r}")
            elif NOT_EXAMINED.search(match.group(1)) and not any(
                    re.search(rf"(?<![\w-]){re.escape(tid)}(?![\w-])", match.group(1)) for tid in threats):
                add(rule, f"{where}: 'not examined' is not an n/a reason; write a threat for it, "
                          "such as a backlog item to examine it")
        elif not isinstance(value, list) or not value:
            add(rule, f"{where} must list at least one threat ID or say 'n/a: <reason>'")
        else:
            for tid in value:
                if not known(tid, threats):
                    add(rule, f"{where} names unknown threat {tid!r}")


def check(model):
    """Return one 'rule: message' string per broken rule; an empty list means pass."""
    problems = []
    add = lambda rule, message: problems.append(f"{rule}: {message}")
    if not isinstance(model, dict):
        return ["M1: the model must be a JSON object"]
    for key in ("name", "scope"):
        if not text(model.get(key)):
            add("M1", f"'{key}' must be a non-empty text")

    zones = items(model, "zones", add)
    elements = items(model, "elements", add)
    flows = items(model, "flows", add)
    threats = items(model, "threats", add)

    for eid, element in elements.items():
        if element.get("kind") not in KINDS:
            add("M1", f"element {eid} kind must be one of {', '.join(KINDS)}")
        if not known(element.get("zone"), zones):
            add("M2", f"element {eid} sits in unknown zone {element.get('zone')!r}")

    for fid, flow in flows.items():
        for side in ("from", "to"):
            if not known(flow.get(side), elements):
                add("M2", f"flow {fid} '{side}' names unknown element {flow.get(side)!r}")
        if not text(flow.get("data")):
            add("M1", f"flow {fid} needs 'data': what the flow carries")
        if not isinstance(flow.get("personal_data"), bool):
            add("M1", f"flow {fid} needs 'personal_data': true or false")
        if crosses(flow, elements) or "stride" in flow:
            categories(flow, "stride", STRIDE, threats, "M3", add)
        if flow.get("personal_data") is True or "linddun" in flow:
            categories(flow, "linddun", LINDDUN, threats, "M4", add)

    standard = model.get("standard")
    form = STANDARDS.get(standard) if isinstance(standard, str) else None
    if not text(standard):
        add("M9", "'standard' must name the standard reviewed against, such as 'OWASP ASVS 4.0.3'")
    elif form is None:
        add("M9", f"standard {standard!r} is unknown; known: {', '.join(STANDARDS)}")

    def reference(ref, where):
        if form and not (isinstance(ref, str) and form.fullmatch(ref)):
            add("M9", f"{where} reference {ref!r} is not {standard} form V<chapter>.<section>.<requirement>")

    for tid, threat in threats.items():
        if not text(threat.get("title")):
            add("M1", f"threat {tid} needs a 'title'")
        kind = threat.get("disposition")
        if kind not in DISPOSITIONS:
            add("M5", f"threat {tid} disposition must be one of {', '.join(DISPOSITIONS)}, not {kind!r}")
        elif kind == "accept":
            owner = threat.get("owner")
            if not text(owner) or not is_person(owner):
                add("M6", f"accepted risk {tid} needs a named owner, a person, not {owner!r}")
            if not text(threat.get("reason")):
                add("M6", f"accepted risk {tid} needs a 'reason'")
        elif kind == "backlog":
            item = threat.get("item")
            if not (isinstance(item, str) and ITEM_ID.fullmatch(item.strip())):
                add("M7", f"backlog threat {tid} needs an item ID such as B-12 or #12, not {item!r}")
        else:
            for key in ("mitigation", "verification"):
                if not text(threat.get(key)):
                    add("M8", f"mitigated threat {tid} needs a '{key}'")
            mitigation = threat.get("mitigation")
            if text(mitigation) and not MITIGATION.match(mitigation.strip()):
                add("M8", f"mitigated threat {tid}: start the mitigation with 'Existing (<source>):' or 'Planned:'")
        refs = threat.get("asvs", [])
        for ref in refs if isinstance(refs, list) else [refs]:
            reference(ref, f"threat {tid}")

    cases = model.get("abuse_cases")
    if not isinstance(cases, list) or not cases:
        add("M10", "'abuse_cases' must list at least one abuse case")
    for n, case in enumerate(cases if isinstance(cases, list) else []):
        where = f"abuse case {case.get('id', n) if isinstance(case, dict) else n}"
        if not isinstance(case, dict):
            add("M10", f"{where} must be an object")
            continue
        for key in ("id", "actor", "goal"):
            if not text(case.get(key)):
                add("M10", f"{where} needs '{key}'")
        named = case.get("threats")
        if not isinstance(named, list) or not named:
            add("M10", f"{where} must name the threats it exercises")
        else:
            for tid in named:
                if not known(tid, threats):
                    add("M10", f"{where} names unknown threat {tid!r}")

    review = model.get("review")
    if not isinstance(review, list) or not review:
        add("M11", "'review' must list the standard's requirements reviewed")
    for n, row in enumerate(review if isinstance(review, list) else []):
        if not isinstance(row, dict):
            add("M11", f"review[{n}] must be an object")
            continue
        where = f"review {row.get('ref', n)}"
        reference(row.get("ref"), where)
        result = row.get("result")
        if result not in RESULTS:
            add("M11", f"{where} result must be one of {', '.join(RESULTS)}, not {result!r}")
        elif result == "met" and not text(row.get("evidence")):
            add("M11", f"{where} is 'met' only with 'evidence' a reader can check")
        elif result == "not applicable" and not text(row.get("reason")):
            add("M11", f"{where} is 'not applicable' only with a 'reason'")
        elif result == "gap":
            named = row.get("threats")
            if not isinstance(named, list) or not named:
                add("M11", f"{where} is a gap: name the threats that carry its disposition")
            else:
                for tid in named:
                    if not known(tid, threats):
                        add("M11", f"{where} names unknown threat {tid!r}")

    # Every well-formed reference a threat cites has a review row (any result).
    reviewed = {row.get("ref") for row in (review if isinstance(review, list) else [])
                if isinstance(row, dict) and isinstance(row.get("ref"), str)}
    for tid, threat in threats.items():
        refs = threat.get("asvs", [])
        for ref in refs if isinstance(refs, list) else [refs]:
            if form and isinstance(ref, str) and form.fullmatch(ref) and ref not in reviewed:
                add("M11", f"threat {tid} cites {ref} but no review row covers it; add the row")

    lines = model.get("not_examined")
    if lines is not None and not (isinstance(lines, list) and all(text(line) for line in lines)):
        add("M1", "'not_examined' must be a list of texts, one line each")

    for where, value in prose(model):
        described = where.startswith("threat ") and where.rsplit(" ", 1)[-1] in DESCRIBED
        claim = overclaim(value, described) if isinstance(value, str) else None
        if claim:
            add("M12", f"{where} claims {claim!r}; state what was checked and label the rest")
    return problems


def cell(value):
    """One Markdown table cell: lists joined, pipes escaped, line breaks removed."""
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return " ".join(str(value).split()).replace("|", "\\|") if value not in (None, "") else "-"


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return lines


def render(model):
    """The model as Markdown. Call only on a model that passes check."""
    zones = {z["id"]: z for z in model["zones"]}
    elements = {e["id"]: e for e in model["elements"]}
    flows = model["flows"]
    name = lambda eid: elements[eid].get("name", eid)
    where = {}
    for flow in flows:
        for key, names in (("stride", STRIDE), ("linddun", LINDDUN)):
            for category in names:
                value = flow.get(key, {}).get(category)
                for tid in value if isinstance(value, list) else []:
                    where.setdefault(tid, []).append(f"{flow['id']} {category.replace('_', ' ')}")

    out = [f"# Threat model: {model['name']}", "", f"Scope: {model['scope']}",
           f"Standard: {model['standard']}"]
    if model.get("summary"):
        out += ["", model["summary"]]

    out += ["", "## Elements", ""]
    out += table(["ID", "Element", "Kind", "Zone", "Entry point"],
                 [[e["id"], e.get("name", e["id"]), e["kind"], zones[e["zone"]].get("name", e["zone"]),
                   "yes" if e.get("entry_point") else "no"] for e in model["elements"]])

    crossings = {}
    for flow in flows:
        if crosses(flow, elements):
            pair = (elements[flow["from"]]["zone"], elements[flow["to"]]["zone"])
            crossings.setdefault(pair, []).append(flow["id"])
    out += ["", "## Trust boundaries", ""]
    out += table(["From zone", "To zone", "Flows"],
                 [[zones[a].get("name", a), zones[b].get("name", b), fids] for (a, b), fids in crossings.items()])

    out += ["", "## Flows", ""]
    out += table(["ID", "From", "To", "Data", "Crosses a boundary", "Personal data"],
                 [[f["id"], name(f["from"]), name(f["to"]), f["data"], "yes" if crosses(f, elements) else "no",
                   "yes" if f["personal_data"] else "no"] for f in flows])

    for key, names, title in (("stride", STRIDE, "STRIDE"), ("linddun", LINDDUN, "LINDDUN")):
        rows = [[f["id"]] + [f[key][c] for c in names] for f in flows if key in f]
        out += ["", f"## {title}", ""]
        out += table(["Flow"] + [c.replace("_", " ").capitalize() for c in names], rows)

    rows = []
    for t in model["threats"]:
        kind = t["disposition"]
        if kind == "mitigate":
            detail, evidence = f"{t['mitigation']}. Verify: {t['verification']}", t.get("evidence") or "not run"
        elif kind == "accept":
            detail = f"Owner: {t['owner']}. Reason: {t['reason']}"
            evidence = t.get("accepted") or "acceptance not recorded"
        else:
            detail, evidence = f"Item: {t['item']}", "open"
        rows.append([t["id"], t["title"], where.get(t["id"], "not on a flow"), kind, detail,
                     t.get("asvs"), evidence])
    out += ["", "## Threats", ""]
    out += table(["ID", "Threat", "Where", "Disposition", "Detail", "ASVS", "Evidence"], rows)

    out += ["", "## Abuse cases", ""]
    out += table(["ID", "Actor", "Goal", "How", "Threats"],
                 [[a["id"], a["actor"], a["goal"], a.get("how"), a["threats"]]
                  for a in model["abuse_cases"]])

    out += ["", "## Standard review", ""]
    out += table(["Requirement", "Result", "Evidence, reason or threats"],
                 [[r["ref"], r["result"], r.get("evidence") or r.get("reason") or r.get("threats")]
                  for r in model["review"]])

    out += ["", "## Not examined", ""]
    unexamined = [r["ref"] for r in model["review"] if r["result"] == "not examined"]
    lines = list(model.get("not_examined") or []) + [f"{ref} (standard review)" for ref in unexamined]
    out += [f"- {line}" for line in lines] or [
        "- Nothing listed. The model does not prove its threat list is complete."]
    return "\n".join(out) + "\n"


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(argv) != 2 or argv[0] not in ("check", "render"):
        print("usage: threat_check.py check|render model.json", file=sys.stderr)
        return 2
    try:
        model = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"M1: cannot read {argv[1]} as JSON: {error}")
        return 1
    problems = check(model)
    if problems:
        print("\n".join(problems))
        return 1
    if argv[0] == "check":
        print("pass")
    else:
        sys.stdout.write(render(model))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

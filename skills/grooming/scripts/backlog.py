#!/usr/bin/env python3
"""Validate and inspect a backlog/v1 file (see ../reference/contract.md).

  backlog.py validate backlog.json [--require-ready]   errors exit 1; warnings do not
  backlog.py tree backlog.json                        hierarchy, WSJF order, readiness, sign-off
  backlog.py status backlog.json [--all-approvers]    sign-off per approver, gates, open feedback
  backlog.py trace backlog.json [--today YYYY-MM-DD]  described → agreed → delivered → achieved, with gaps

Standard library only. `syncing` imports this module, so keep its functions stable.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

CONTRACT = "backlog/v1"
TYPES = {"initiative": "I", "goal": "G", "feature": "F", "story": "S", "bug": "B"}
PARENT = {"goal": "initiative", "feature": "goal", "story": "feature", "bug": "feature"}
TRACKERS = ("github", "linear", "azure")

COMMON = {"id", "type", "parent", "title", "trace", "notes", "external", "approvals"}
REQUIRED = {
    "initiative": {"domain", "problem", "drivers", "outcome", "owner"},
    "goal": {"metric", "baseline", "target", "by", "drivers", "trace"},
    "feature": {"description", "benefit_hypothesis", "wsjf", "trace"},
    "story": {"as_a", "i_want", "so_that", "work", "acceptance", "priority", "size", "status", "trace"},
    "bug": {"observed", "expected", "steps", "work", "acceptance", "priority", "urgency", "size", "status"},
}
OPTIONAL = {
    "initiative": {"prd", "non_goals"},
    "goal": {"measurements"},
    "feature": {"acceptance", "milestone", "owner"},
    "story": {"depends_on", "milestone", "owner", "delivery"},
    "bug": {"environment", "depends_on", "milestone", "owner", "delivery"},
}
ENUMS = {
    "domain": {"product", "operations", "marketing"},
    "work": {"build", "automate", "report", "process", "enable", "content", "launch", "research"},
    "priority": {"must", "should", "could", "wont"},
    "size": {"XS", "S", "M", "L", "XL"},
    "status": {"draft", "ready"},
    "urgency": {"critical", "high", "medium", "low"},
}
FIBONACCI = {1, 2, 3, 5, 8, 13, 20}
WSJF_KEYS = ("business_value", "time_criticality", "risk_reduction", "job_size")
DISPOSITIONS = {"open", "accepted", "declined", "duplicate"}

VAGUE = re.compile(
    r"\b(fast|quick(ly)?|easy|easily|simple|intuitive|user-friendly|seamless(ly)?|robust|scalable|"
    r"efficient(ly)?|appropriate(ly)?|as needed|properly|optimi[sz]ed|improved|better|etc)\b",
    re.I,
)
QUANTITY = re.compile(
    r"\d|\b(every|each|all|none|no|exactly|at least|at most|within|zero|one|two|three|four|five|six|"
    r"seven|eight|nine|ten|eleven|twelve)\b",
    re.I,
)
GENERIC_ACTORS = {"user", "users", "customer", "customers", "stakeholder", "stakeholders", "team"}
TIME_BOX = re.compile(r"\d+\s*-?\s*(working[\s-]*|business[\s-]*)?(hour|day|week|sprint|iteration)s?\b", re.I)
DAYS_PER = {"hour": 1 / 8, "day": 1, "week": 5, "sprint": 10, "iteration": 10}
SIZE_DAYS = (("XS", 0.5), ("S", 2), ("M", 5), ("L", 10))
PLACEHOLDER_OWNER = re.compile(
    r"\b(to be (named|confirmed|agreed|decided)|to confirm|names? (needed|to confirm)|tbd|tbc|unassigned|unknown)\b", re.I)
DECISION = re.compile(r"\b(decid\w*|decision|recommend\w*|choose|chooses|select\w*)\b", re.I)
ITEM_REF = re.compile(r"\b[IGFSB]-\d+\b")
ANY_ID = re.compile(r"\b(?:[IGFSBDR]|AC|FB)-\d+(?:\.\d+)?\b|\bE\d+\b")


def id_key(iid):
    """Sort IDs by prefix, then number: S-2 before S-10."""
    prefix, _, number = str(iid).partition("-")
    return (prefix, int(number) if number.isdigit() else 0, str(iid))


SYNC_ONLY = {"external", "approvals", "delivery", "measurements"}


def fingerprint(item, base=None):
    """Hash of everything a tracker shows for the item, so local edits since a sync are visible.
    Delivery records and measurements are progress, not content, so they are left out."""
    content = {k: v for k, v in item.items() if k not in SYNC_ONLY}
    text = json.dumps(content, sort_keys=True, ensure_ascii=False)
    if item.get("type") == "initiative" and base is not None and isinstance(item.get("prd"), str):
        prd = Path(base) / item["prd"]
        text += prd.read_text(encoding="utf-8") if prd.exists() else "<missing PRD>"
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def prd_ids(text):
    """Requirement and criterion IDs a PRD defines: written in bold, as in '**R-2 …**' or '**AC-3**'."""
    return set(re.findall(r"\*\*((?:R|AC)-\d+)\b", text))


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def items_by_id(data):
    return {item.get("id"): item for item in data.get("items", []) if isinstance(item, dict)}


def children(data):
    kids = {}
    for item in data.get("items", []):
        if isinstance(item, dict) and item.get("parent"):
            kids.setdefault(item["parent"], []).append(item)
    return kids


def wsjf_score(feature):
    w = feature.get("wsjf") or {}
    try:
        return round((w["business_value"] + w["time_criticality"] + w["risk_reduction"]) / w["job_size"], 2)
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def named_owner(value):
    """True when an owner names someone, not a placeholder such as 'Data lead (to be named)'."""
    return _text(value) and not PLACEHOLDER_OWNER.search(value)


def _iso_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def validate(data, require_ready=False, base=None):
    """Return (errors, warnings), each a list of (location, message)."""
    errors, warnings = [], []
    err = lambda where, msg: errors.append((where, msg))
    warn = lambda where, msg: warnings.append((where, msg))

    if not isinstance(data, dict):
        return [("file", "top level must be a JSON object")], []
    for key in set(data) - {"contract", "title", "approvers", "milestones", "items", "feedback"}:
        err("file", f"unknown top-level field '{key}'")
    if data.get("contract") != CONTRACT:
        err("file", f"'contract' must be '{CONTRACT}'")
    if not _text(data.get("title")):
        err("file", "'title' is required")
    if not isinstance(data.get("items"), list) or not data["items"]:
        err("file", "'items' must be a non-empty list")
        return errors, warnings

    if not data.get("approvers"):
        warn("file", "no approvers: no sign-off gate can pass")
    for n, approver in enumerate(data.get("approvers", [])):
        if not isinstance(approver, dict) or not _text(approver.get("name")):
            err(f"approvers[{n}]", "needs a 'name'")
        elif set(approver) - {"name", *TRACKERS}:
            err(f"approvers[{n}]", f"unknown fields {sorted(set(approver) - {'name', *TRACKERS})}")

    milestones = {}
    titles = set()
    for n, m in enumerate(data.get("milestones", [])):
        where = f"milestones[{n}]"
        if not isinstance(m, dict) or not _text(m.get("id")) or not _text(m.get("title")):
            err(where, "needs 'id' and 'title'")
            continue
        if set(m) - {"id", "title", "start", "due"}:
            err(m["id"], f"unknown fields {sorted(set(m) - {'id', 'title', 'start', 'due'})}")
        if m["id"] in milestones:
            err(m["id"], "duplicate milestone id")
        if m["title"] in titles:
            err(m["id"], "duplicate milestone title; trackers match on titles")
        for key in ("start", "due"):
            if key in m and not _iso_date(m[key]):
                err(m["id"], f"'{key}' must be YYYY-MM-DD")
        if _iso_date(m.get("start")) and _iso_date(m.get("due")) and m["start"] > m["due"]:
            err(m["id"], "'start' is after 'due'")
        if "start" in m and "due" not in m:
            err(m["id"], "'start' needs a 'due' date")
        milestones[m["id"]] = m
        titles.add(m["title"])

    seen = {}
    for n, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            err(f"items[{n}]", "must be an object")
            continue
        iid, kind = item.get("id"), item.get("type")
        if kind not in TYPES:
            err(iid or f"items[{n}]", f"'type' must be one of {sorted(TYPES)}")
            continue
        if not isinstance(iid, str) or not re.fullmatch(rf"{TYPES[kind]}-\d+", iid):
            err(iid or f"items[{n}]", f"a {kind} id must look like {TYPES[kind]}-1")
            continue
        if iid in seen:
            err(iid, "duplicate id")
        seen[iid] = item

    for iid, item in seen.items():
        _check_item(item, seen, milestones, err, warn)

    kids = children(data)
    deps = {}
    for iid, item in seen.items():
        kind = item["type"]
        if kind in ("story", "bug") and isinstance(item.get("depends_on"), list):
            deps[iid] = item["depends_on"]
        child_kind = {"initiative": ("goal",), "goal": ("feature",), "feature": ("story",)}.get(kind)
        if child_kind and not any(k["type"] in child_kind for k in kids.get(iid, [])):
            (err if require_ready else warn)(iid, f"has no {child_kind[0]} yet")
        if kind == "feature" and not _text(item.get("owner")):
            (err if require_ready else warn)(iid, "has no owner: name the one person accountable for it")
        elif kind == "feature" and not named_owner(item["owner"]):
            (err if require_ready else warn)(iid, f"owner '{item['owner']}' is a placeholder: name the one person accountable for it")
    for iid in _cycle_members(deps):
        _dor(seen[iid], "depends_on forms a cycle", err, warn)
    for iid, item in seen.items():
        if item["type"] != "initiative" or not isinstance(item.get("drivers"), list):
            continue
        served = {d for k in kids.get(iid, []) if k["type"] == "goal" for d in k.get("drivers") or []}
        for driver in item["drivers"]:
            if isinstance(driver, dict) and driver.get("id") not in served:
                (err if require_ready else warn)(iid, f"driver {driver.get('id')} is served by no goal")

    feedback_ids = set()
    for n, fb in enumerate(data.get("feedback", [])):
        where = fb.get("id") if isinstance(fb, dict) and fb.get("id") else f"feedback[{n}]"
        if not isinstance(fb, dict):
            err(where, "must be an object")
            continue
        extra = set(fb) - {"id", "feature", "from", "summary", "source", "at", "disposition", "resolution"}
        if extra:
            err(where, f"unknown fields {sorted(extra)}")
        if not isinstance(fb.get("id"), str) or not re.fullmatch(r"FB-\d+", fb["id"]):
            err(where, "feedback id must look like FB-1")
        elif fb["id"] in feedback_ids:
            err(where, "duplicate feedback id")
        feedback_ids.add(fb.get("id"))
        target = seen.get(fb.get("feature"))
        if not target or target["type"] != "feature":
            err(where, "'feature' must name a feature in this file")
        for field in ("from", "summary"):
            if not _text(fb.get(field)):
                err(where, f"'{field}' is required")
        disposition = fb.get("disposition")
        if disposition not in DISPOSITIONS:
            err(where, f"'disposition' must be one of {sorted(DISPOSITIONS)}")
        elif disposition == "open":
            (err if require_ready else warn)(where, "feedback is still open")
        elif not _text(fb.get("resolution")):
            err(where, f"'{disposition}' feedback needs a 'resolution'")
        elif disposition == "accepted":
            refs = ITEM_REF.findall(fb["resolution"])
            if not refs:
                err(where, "accepted feedback must name the item IDs that changed")
            for ref in refs:
                if ref not in seen:
                    err(where, f"resolution names unknown item {ref}")
    for fb in data.get("feedback", []):
        if isinstance(fb, dict) and fb.get("disposition") == "duplicate":
            other = re.findall(r"\bFB-\d+\b", fb.get("resolution") or "")
            if not other or any(o not in feedback_ids or o == fb.get("id") for o in other):
                err(fb.get("id", "feedback"), "duplicate feedback must name another existing FB- id")

    if require_ready:
        waiting = {}  # draft work that waits on a research story not yet delivered: held, not failed
        for iid, item in seen.items():
            if item["type"] in ("story", "bug") and item.get("status") == "draft":
                deps = item.get("depends_on") if isinstance(item.get("depends_on"), list) else []
                research = [d for d in deps if isinstance(d, str) and isinstance(seen.get(d), dict)
                            and seen[d].get("work") == "research" and not seen[d].get("delivery")]
                if research:
                    waiting[iid] = research
                else:
                    err(iid, "is still draft")
        promoted = [(w, m) for w, m in warnings if _is_story_level(w, seen) and w not in waiting]
        warnings = [(w, m) for w, m in warnings if not _is_story_level(w, seen) or w in waiting]
        errors.extend(promoted)
        warnings += [(iid, f"draft until research {', '.join(r)} is delivered") for iid, r in waiting.items()]

    if base is not None:
        _check_trace_sources(data, seen, Path(base), warn)
    return errors, warnings


def _is_story_level(where, seen):
    item = seen.get(where)
    return bool(item) and item["type"] in ("story", "bug")


def _dor(item, message, err, warn):
    """Definition of Ready finding: an error when the item is ready, a warning while draft."""
    (err if item.get("status") == "ready" else warn)(item["id"], message)


def _check_item(item, seen, milestones, err, warn):
    iid, kind = item["id"], item["type"]
    allowed = COMMON | REQUIRED[kind] | OPTIONAL[kind]
    for key in sorted(set(item) - allowed):
        err(iid, f"unknown field '{key}' for a {kind}")
    if not _text(item.get("title")):
        err(iid, "'title' is required")
    elif len(item["title"]) > 120:
        err(iid, "'title' is longer than 120 characters")

    if kind == "initiative":
        if "parent" in item:
            err(iid, "an initiative has no parent")
    else:
        parent = seen.get(item.get("parent"))
        if not parent or parent["type"] != PARENT[kind]:
            err(iid, f"'parent' must be a {PARENT[kind]} in this file")

    for field, values in ENUMS.items():
        if field in item and field in REQUIRED[kind] | OPTIONAL[kind] and not (isinstance(item[field], str) and item[field] in values):
            err(iid, f"'{field}' must be one of {sorted(values)}")
    if "milestone" in item and item["milestone"] not in milestones:
        err(iid, f"milestone '{item['milestone']}' is not defined")
    if "trace" in item and not (isinstance(item["trace"], list) and all(_text(t) for t in item["trace"])):
        err(iid, "'trace' must be a list of strings")

    work_item = kind in ("story", "bug")
    if work_item and not (isinstance(item.get("status"), str) and item["status"] in ENUMS["status"]):
        err(iid, "'status' is required: draft or ready")
        return
    for field in sorted(REQUIRED[kind] - {"status"}):
        value = item.get(field)
        missing = value is None or (isinstance(value, (str, list, dict)) and not value)
        if isinstance(value, str) and not value.strip():
            missing = True
        if missing:
            if work_item:
                _dor(item, f"'{field}' is required", err, warn)
            else:
                err(iid, f"'{field}' is required")

    if kind == "initiative" and "drivers" in item and not isinstance(item["drivers"], list):
        err(iid, "'drivers' must be a list")
    if kind == "goal" and "drivers" in item and not isinstance(item["drivers"], list):
        err(iid, "'drivers' must be a list of driver IDs")
    if kind == "initiative" and isinstance(item.get("drivers"), list):
        ids = [d.get("id") if isinstance(d, dict) else None for d in item["drivers"]]
        for d in item["drivers"]:
            if not isinstance(d, dict) or set(d) != {"id", "statement"} or not re.fullmatch(r"D-\d+", str(d.get("id"))) or not _text(d.get("statement")):
                err(iid, "each driver is exactly { \"id\": \"D-1\", \"statement\": \"…\" }")
        if len(ids) != len(set(ids)):
            err(iid, "duplicate driver id")
    if kind == "goal":
        if "by" in item and not _iso_date(item["by"]):
            err(iid, "'by' must be YYYY-MM-DD")
        parent = seen.get(item.get("parent")) or {}
        known = {d.get("id") for d in parent.get("drivers") or [] if isinstance(d, dict)}
        for d in item.get("drivers") if isinstance(item.get("drivers"), list) else []:
            if d not in known:
                err(iid, f"driver '{d}' is not a driver of {item.get('parent')}")
        for n, m in enumerate(item.get("measurements") or []):
            if not isinstance(m, dict) or not _iso_date(m.get("at")) or m.get("value") in (None, "") or set(m) - {"at", "value", "source"}:
                err(iid, f"measurements[{n}] is exactly {{ at: YYYY-MM-DD, value, source? }}")
    if kind == "feature":
        w = item.get("wsjf")
        if w is not None:
            if not isinstance(w, dict) or set(w) != set(WSJF_KEYS):
                err(iid, f"'wsjf' needs exactly {list(WSJF_KEYS)}")
            elif any(w[k] not in FIBONACCI for k in WSJF_KEYS):
                err(iid, f"wsjf values must be one of {sorted(FIBONACCI)}")
        if "acceptance" in item and not (isinstance(item["acceptance"], list) and all(_text(a) for a in item["acceptance"])):
            err(iid, "feature 'acceptance' must be a list of strings")
    if kind == "initiative" and "non_goals" in item and not isinstance(item["non_goals"], list):
        err(iid, "'non_goals' must be a list")
    if work_item:
        _check_work_item(item, seen, err, warn)


def _check_work_item(item, seen, err, warn):
    iid, kind = item["id"], item["type"]
    if kind == "story" and _text(item.get("as_a")):
        actor = re.sub(r"^(a|an|the)\s+", "", item["as_a"].strip().lower())
        if actor in GENERIC_ACTORS:
            _dor(item, f"'as_a' is a bare '{item['as_a']}'; name the specific actor", err, warn)
    if kind == "bug" and "steps" in item and not (
        isinstance(item["steps"], list) and item["steps"] and all(_text(s) for s in item["steps"])
    ):
        _dor(item, "'steps' must be a non-empty list of strings", err, warn)
    if item.get("size") == "XL":
        _dor(item, "size XL must be split into smaller items before it is ready", err, warn)

    criteria = item.get("acceptance")
    if criteria is not None and not isinstance(criteria, list):
        err(iid, "'acceptance' must be a list")
        criteria = []
    has_digit = False
    for n, ac in enumerate(criteria or []):
        if not isinstance(ac, dict):
            err(iid, f"acceptance[{n}] must be an object")
            continue
        extra = set(ac) - {"id", "given", "when", "then"}
        if extra:
            err(iid, f"acceptance[{n}] has unknown fields {sorted(extra)}")
        if not re.fullmatch(rf"{re.escape(iid)}\.\d+", str(ac.get("id", ""))):
            err(iid, f"acceptance[{n}] id must look like {iid}.{n + 1}")
        for part in ("given", "when", "then"):
            if not _text(ac.get(part)):
                _dor(item, f"acceptance {ac.get('id', n)} needs '{part}'", err, warn)
        then = ac.get("then") if _text(ac.get("then")) else ""
        if then:
            has_digit = has_digit or bool(re.search(r"\d", ANY_ID.sub(" ", then)))
            if not QUANTITY.search(then):
                _dor(item, f"acceptance {ac.get('id', n)} 'then' states no measurable quantity", err, warn)
            vague = VAGUE.search(then)
            if vague:
                _dor(item, f"acceptance {ac.get('id', n)} uses the vague word '{vague.group(0)}'", err, warn)
    if criteria and not has_digit:
        _dor(item, "no acceptance criterion contains a number", err, warn)

    if kind == "story" and item.get("work") == "research":
        texts = " ".join([item.get("i_want") or ""] + [a.get("then") or "" for a in criteria or [] if isinstance(a, dict)])
        box = TIME_BOX.search(item.get("i_want") or "") or TIME_BOX.search(texts)
        if not box:
            _dor(item, "research story must state its time box, such as '3-day'", err, warn)
        else:
            days = int(re.match(r"\d+", box.group(0)).group(0)) * DAYS_PER[box.group(2).lower()]
            fits = next((s for s, most in SIZE_DAYS if days <= most), "XL")
            if item.get("size") in dict(SIZE_DAYS) and item["size"] != fits:
                warn(iid, f"research time box '{box.group(0)}' is size {fits}, not {item['size']}: size it by its time box")
        if not DECISION.search(texts):
            _dor(item, "research story must state the decision it produces", err, warn)

    if "delivery" in item:
        _check_delivery(item, criteria or [], err)

    deps = item.get("depends_on", [])
    if not isinstance(deps, list):
        err(iid, "'depends_on' must be a list")
        return
    for dep in deps:
        target = seen.get(dep)
        if dep == iid:
            _dor(item, "depends on itself", err, warn)
        elif not target or target["type"] not in ("story", "bug"):
            _dor(item, f"depends on unknown story or bug '{dep}'", err, warn)


def _check_delivery(item, criteria, err):
    iid, d = item["id"], item["delivery"]
    if item.get("status") != "ready":
        err(iid, "only a ready item can have a delivery")
    if not isinstance(d, dict) or set(d) - {"at", "evidence", "criteria"}:
        err(iid, "'delivery' is exactly { at, evidence, criteria }")
        return
    if not _iso_date(d.get("at")):
        err(iid, "delivery 'at' must be YYYY-MM-DD")
    if not (isinstance(d.get("evidence"), list) and d["evidence"] and all(_text(e) for e in d["evidence"])):
        err(iid, "delivery needs at least one evidence entry")
    expected = {a.get("id") for a in criteria if isinstance(a, dict)}
    got = d.get("criteria") if isinstance(d.get("criteria"), dict) else {}
    if set(got) != expected:
        err(iid, f"delivery criteria must list exactly {sorted(expected)}")
    if any(v not in ("met", "not met") for v in got.values()):
        err(iid, "each delivery criterion is 'met' or 'not met'")


def _cycle_members(deps):
    members, state = set(), {}

    def visit(node, path):
        state[node] = "active"
        for nxt in deps.get(node, []):
            if nxt not in deps:
                continue
            if state.get(nxt) == "active":
                members.update(path[path.index(nxt):])
            elif nxt not in state:
                visit(nxt, path + [nxt])
        state[node] = "done"

    for node in deps:
        if node not in state:
            visit(node, [node])
    return sorted(members)


def _check_trace_sources(data, seen, base, warn):
    """Check E-, R- and AC- trace IDs against evidence.md and each initiative's PRD, when present."""
    evidence = base / "evidence.md"
    defined_e = set(re.findall(r"^\|\s*(?:~~)?(E\d+)(?:~~)?\s*\|", evidence.read_text(encoding="utf-8"), re.M)) if evidence.exists() else None
    prd_text = ""
    for item in seen.values():
        if item["type"] == "initiative" and _text(item.get("prd")):
            prd = base / item["prd"]
            if prd.exists():
                prd_text += prd.read_text(encoding="utf-8")
            else:
                warn(item["id"], f"PRD '{item['prd']}' not found next to the backlog")
    for item in seen.values():
        for ref in item.get("trace") or []:
            if not isinstance(ref, str):
                continue
            if re.fullmatch(r"E\d+", ref) and defined_e is not None and ref not in defined_e:
                warn(item["id"], f"trace {ref} is not in evidence.md")
            if re.fullmatch(r"(R|AC)-\d+", ref) and prd_text and ref not in prd_ids(prd_text):
                warn(item["id"], f"trace {ref} is not defined in the PRD")


# Sign-off -------------------------------------------------------------------------------------

def _covered(data, item):
    kind = {"initiative": "goal", "feature": "story"}[item["type"]]
    return [item] + [k for k in children(data).get(item["id"], []) if k["type"] == kind]


def approval_detail(data, item, tracker="github", base=None):
    """(state, {approver handle: 'current' | 'stale' | 'none'}) for an initiative or feature.

    state is 'not synced', 'unsynced changes' (edited locally since the last sync; needs base),
    'approved' (at least one current approval), 'stale', or 'missing'."""
    handles = {a[tracker].lower(): a[tracker] for a in data.get("approvers", []) if a.get(tracker)}
    covered = _covered(data, item)
    exts = [((k.get("external") or {}).get(tracker) or {}) for k in covered]
    if any(not e.get("synced_at") for e in exts):
        return "not synced", {h: "none" for h in handles.values()}
    latest = max(e["synced_at"] for e in exts)
    per = {h: "none" for h in handles.values()}
    for a in item.get("approvals", []):
        who = handles.get(str(a.get("by", "")).lower())
        if a.get("tracker") == tracker and who:
            per[who] = "current" if a.get("at", "") >= latest else (per[who] if per[who] == "current" else "stale")
    if base is not None and any(e.get("fingerprint") != fingerprint(k, base) for k, e in zip(covered, exts)):
        return "unsynced changes", per
    if "current" in per.values():
        return "approved", per
    return ("stale" if "stale" in per.values() else "missing"), per


def approval_state(data, item, tracker="github", base=None, require_all=False):
    state, per = approval_detail(data, item, tracker, base)
    if state == "approved" and require_all and any(v != "current" for v in per.values()):
        return "partly approved"
    return state


def gates(data, tracker="github", base=None, require_all=False):
    rows = []
    for kind, gate in (("initiative", "PRD"), ("feature", "backlog")):
        for item in sorted((i for i in data.get("items", []) if i.get("type") == kind), key=lambda i: id_key(i["id"])):
            state = approval_state(data, item, tracker, base, require_all)
            rows.append((gate, item, state, approval_detail(data, item, tracker, base)[1]))
    return rows


# Traceability ---------------------------------------------------------------------------------

def _number(value):
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None


def goal_state(goal, today):
    """'achieved', 'in progress', 'missed', or 'not measured' from the latest measurement."""
    ms = goal.get("measurements") or []
    overdue = str(goal.get("by", "9999-12-31")) < today
    if not ms:
        return "missed (not measured)" if overdue else "not measured"
    latest = ms[-1]["value"]
    base, target, value = _number(goal.get("baseline")), _number(goal.get("target")), _number(latest)
    limit = re.match(r"\s*at (most|least)\s+(-?\d+(?:\.\d+)?)", str(goal.get("target")), re.I)
    if limit and value is not None:  # a limit, such as a guardrail: direction comes from the words
        bound = float(limit.group(2))
        achieved = value <= bound if limit.group(1).lower() == "most" else value >= bound
    elif None not in (base, target, value):
        achieved = value <= target if base > target else value >= target
    else:
        achieved = str(latest).strip().lower() == str(goal.get("target")).strip().lower()
    if achieved:
        return "achieved"
    return "missed" if overdue else "in progress"


def delivery_state(item):
    d = item.get("delivery")
    closed = any((e or {}).get("state") == "closed" for e in (item.get("external") or {}).values())
    if not isinstance(d, dict):
        return "closed, no delivery record" if closed else "not delivered"
    unmet = sorted(k for k, v in (d.get("criteria") or {}).items() if v != "met")
    return f"partial: {', '.join(unmet)} not met" if unmet else "delivered"


def trace_report(data, base, today, tracker="github", require_all=False):
    """Markdown report of the chain and its gaps. Returns (text, gaps)."""
    seen, kids, gaps = items_by_id(data), children(data), []
    ordered = sorted(seen.values(), key=lambda i: id_key(i["id"]))
    traced = {t for i in seen.values() for t in i.get("trace") or []}
    out = [f"# Traceability: {data.get('title', '')}", ""]
    goals = [i for i in ordered if i.get("type") == "goal"]
    states = {g["id"]: goal_state(g, today) for g in goals}

    out += ["## Drivers", "", "| Initiative | Driver | Goals | Status |", "| --- | --- | --- | --- |"]
    for ini in (i for i in ordered if i.get("type") == "initiative"):
        sign = approval_state(data, ini, tracker, base, require_all)
        if sign != "approved":
            gaps.append(f"{ini['id']} has no current PRD sign-off ({sign})")
        for d in ini.get("drivers") or []:
            served = [g["id"] for g in goals if g.get("parent") == ini["id"] and d.get("id") in (g.get("drivers") or [])]
            if not served:
                status = "no goal serves it"
                gaps.append(f"{ini['id']} driver {d.get('id')} is served by no goal")
            elif all(states[g] == "achieved" for g in served):
                status = "satisfied"
            else:
                status = "open: " + ", ".join(f"{g} {states[g]}" for g in served if states[g] != "achieved")
            out.append(f"| {ini['id']} | {d.get('id')}: {d.get('statement')} | {', '.join(served) or '-'} | {status} |")
        prd = Path(base) / ini["prd"] if _text(ini.get("prd")) else None
        if prd and prd.exists():
            # A feature groups criteria; only a story or bug delivers one.
            built = {t for i in seen.values() if i.get("type") in ("story", "bug") for t in i.get("trace") or []}
            for ref in sorted(prd_ids(prd.read_text(encoding="utf-8")), key=id_key):
                if ref not in traced:
                    gaps.append(f"{ref} in {ini['prd']} is traced by no item")
                elif ref.startswith("AC-") and ref not in built:
                    gaps.append(f"{ref} in {ini['prd']} is traced only by a feature; no story or bug delivers it")

    out += ["", "## Goals", "", "| Goal | Drivers | Baseline → target, by | Latest | Status |", "| --- | --- | --- | --- | --- |"]
    for g in goals:
        latest = (g.get("measurements") or [{}])[-1]
        shown = f"{latest['value']} ({latest['at']})" if latest else "-"
        out.append(f"| {g['id']} {g.get('title', '')} | {', '.join(g.get('drivers') or [])} | {g.get('baseline')} → {g.get('target')}, {g.get('by')} | {shown} | {states[g['id']]} |")
        if states[g["id"]].startswith("missed"):
            gaps.append(f"{g['id']} is past {g.get('by')} and {states[g['id']]}")
        if not any(k.get("type") == "feature" for k in kids.get(g["id"], [])):
            gaps.append(f"{g['id']} has no feature")

    out += ["", "## Features", "", "| Feature | Goal | Rank score | Sign-off | Stories delivered | Acceptance checks met |", "| --- | --- | --- | --- | --- | --- |"]
    for f in (i for i in ordered if i.get("type") == "feature"):
        work = [k for k in kids.get(f["id"], []) if k.get("type") in ("story", "bug")]
        stories = [k for k in work if k["type"] == "story"]
        done = sum(1 for k in stories if delivery_state(k) == "delivered")
        crit = [v for k in work for v in ((k.get("delivery") or {}).get("criteria") or {}).values()]
        total = sum(len(k.get("acceptance") or []) for k in work)
        sign = approval_state(data, f, tracker, base, require_all)
        out.append(f"| {f['id']} {f.get('title', '')} | {f.get('parent')} | {wsjf_score(f)} | {sign} | {done}/{len(stories)} | {crit.count('met')}/{total} |")
        if sign != "approved":
            gaps.append(f"{f['id']} has no current sign-off ({sign})")

    out += ["", "## Stories and bugs", "", "| Item | Feature | Status | Delivery | Traces |", "| --- | --- | --- | --- | --- |"]
    for k in (i for i in ordered if i.get("type") in ("story", "bug")):
        state = delivery_state(k)
        out.append(f"| {k['id']} {k.get('title', '')} | {k.get('parent')} | {k.get('status')} | {state} | {', '.join(k.get('trace') or []) or '-'} |")
        if state.startswith(("partial", "closed")):
            gaps.append(f"{k['id']} {state}")

    feedback = data.get("feedback", [])
    if feedback:
        out += ["", "## Feedback", "", "| Feedback | Feature | From | Disposition | Resolution |", "| --- | --- | --- | --- | --- |"]
        for fb in sorted(feedback, key=lambda f: id_key(f.get("id"))):
            out.append(f"| {fb.get('id')} {fb.get('summary', '')} | {fb.get('feature')} | {fb.get('from')} | {fb.get('disposition')} | {fb.get('resolution', '-')} |")
            if fb.get("disposition") == "open":
                gaps.append(f"{fb.get('id')} on {fb.get('feature')} is still open")

    evidence = Path(base) / "evidence.md"
    if evidence.exists():
        defined_e = re.findall(r"^\|\s*(E\d+)\s*\|", evidence.read_text(encoding="utf-8"), re.M)
        unused = [e for e in defined_e if e not in traced]
        if unused:
            out += ["", f"Evidence not traced by any item (confirm each was left out on purpose): {', '.join(unused)}"]

    out += ["", "## Gaps", ""] + ([f"- {g}" for g in gaps] or ["None."])
    return "\n".join(out) + "\n", gaps


# Commands -------------------------------------------------------------------------------------

def cmd_validate(args):
    data = load(args.file)
    errors, warnings = validate(data, args.require_ready, base=Path(args.file).resolve().parent)
    for where, msg in errors:
        print(f"error   {where}: {msg}")
    for where, msg in warnings:
        print(f"warning {where}: {msg}")
    stories = sum(1 for i in data.get("items", []) if isinstance(i, dict) and i.get("type") in ("story", "bug"))
    ready = sum(1 for i in data.get("items", []) if isinstance(i, dict) and i.get("type") in ("story", "bug") and i.get("status") == "ready")
    gate = " (ready gate)" if args.require_ready else ""
    print(f"{len(errors)} errors, {len(warnings)} warnings; {ready}/{stories} stories and bugs ready{gate}")
    return 1 if errors else 0


def _load_checked(path):
    """Load for reporting commands: refuse files with contract errors, which would mislead."""
    data = load(path)
    errors, _ = validate(data)
    if errors:
        raise ValueError(f"{len(errors)} contract errors; run 'backlog.py validate {path}' first")
    return data


def cmd_tree(args):
    data = _load_checked(args.file)
    base = Path(args.file).resolve().parent
    kids = children(data)
    order = {"goal": 0, "feature": 1, "story": 2, "bug": 3}

    def line(item, depth):
        kind, pad = item["type"], "  " * depth
        if kind == "initiative":
            extra = f"[{item.get('domain')}] PRD sign-off: {approval_state(data, item, args.tracker, base)}"
        elif kind == "goal":
            extra = f"{item.get('baseline')} → {item.get('target')} by {item.get('by')}"
        elif kind == "feature":
            extra = f"WSJF {wsjf_score(item)} {item.get('milestone', '-')} sign-off: {approval_state(data, item, args.tracker, base)}"
        else:
            extra = f"{item.get('status')} {item.get('size')} {item.get('priority')}"
            if kind == "bug":
                extra += f" urgency:{item.get('urgency')}"
        print(f"{pad}{item['id']} {item.get('title', '')}  ({extra})")
        nested = sorted(kids.get(item["id"], []), key=lambda k: (
            order[k["type"]], -(wsjf_score(k) or 0) if k["type"] == "feature" else 0, id_key(k["id"])))
        for kid in nested:
            line(kid, depth + 1)
        if kind == "feature":
            for fb in data.get("feedback", []):
                if fb.get("feature") == item["id"]:
                    print(f"{pad}  {fb['id']} feedback from {fb.get('from')}: {fb.get('disposition')}")

    for item in sorted(data["items"], key=lambda i: id_key(i["id"])):
        if item.get("type") == "initiative":
            line(item, 0)
    return 0


def cmd_status(args):
    data = _load_checked(args.file)
    rows = gates(data, args.tracker, Path(args.file).resolve().parent, args.all_approvers)
    for gate, item, state, per in rows:
        who = ", ".join(f"{h} {v}" for h, v in per.items()) or "no approvers"
        print(f"{gate:8} {item['id']:6} {state:16} {item.get('title', '')}  [{who}]")
    open_fb = [fb for fb in data.get("feedback", []) if fb.get("disposition") == "open"]
    print(f"open feedback: {len(open_fb)}")
    passed = bool(rows) and all(state == "approved" for _, _, state, _ in rows) and not open_fb
    print("all gates approved" if passed else "gates open")
    return 0 if passed else 1


def cmd_trace(args):
    text, gaps = trace_report(_load_checked(args.file), Path(args.file).resolve().parent, args.today, args.tracker, args.all_approvers)
    print(text, end="")
    return 1 if gaps else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check the contract and the Definition of Ready")
    v.add_argument("file")
    v.add_argument("--require-ready", action="store_true", help="final gate: no drafts, gaps, or open feedback")
    v.set_defaults(run=cmd_validate)
    commands = (("tree", cmd_tree, "print the hierarchy"), ("status", cmd_status, "print sign-off gates; exit 0 when all pass"),
                ("trace", cmd_trace, "report the chain from evidence to drivers; exit 0 when there are no gaps"))
    for name, run, text in commands:
        p = sub.add_parser(name, help=text)
        p.add_argument("file")
        p.add_argument("--tracker", default="github", choices=TRACKERS)
        if name != "tree":
            p.add_argument("--all-approvers", action="store_true", help="a gate needs a current approval from every listed approver")
        if name == "trace":
            p.add_argument("--today", default=date.today().isoformat(), help="date to judge overdue goals against")
        p.set_defaults(run=run)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

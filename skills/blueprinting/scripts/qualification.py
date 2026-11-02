"""Pure checks of reported business evidence. Never authenticates or grants authority."""

from datetime import date, datetime


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except (ValueError, TypeError):
        return False


def baseline(store, decision_id, expected_intent="accept"):
    state = store.status()
    gaps = []

    def record(ref, kind=None):
        if not isinstance(ref, dict) or set(ref) != {"id", "revision"}:
            gaps.append("Missing exact record reference")
            return {}
        current = state["records"].get(ref["id"])
        if not current or current["revision"] != ref["revision"] or not current["current"]:
            gaps.append(f"Record {ref['id']} is stale, pending or absent")
            return {}
        value = store.read_record(ref["id"], ref["revision"])
        if kind and value["kind"] != kind:
            gaps.append(f"Record {ref['id']} is not a {kind}")
            return {}
        return value

    current = state["records"].get(decision_id)
    decision = record({"id": decision_id, "revision": current["revision"]} if current else None, "decision")
    data = decision.get("data", {})
    intent = data.get("intent", "accept")
    if intent != expected_intent:
        gaps.append(f"Decision does not authorize {expected_intent}")
    if data.get("state") != "accepted":
        gaps.append("No reported accepted decision")
    if not text(data.get("verified_by")) or not timestamp(data.get("verified_at")):
        gaps.append("Named consultant verification and dated review required")
    scope = data.get("scope")
    if not text(scope):
        gaps.append("Decision scope required")
    target = record(data.get("target"))
    if target.get("kind") not in {"requirement", "mission", "artifact"}:
        gaps.append("A requirement, mission or artifact version must be decided")
    authority = record(data.get("authority"), "authority").get("data", {})
    record(authority.get("basis"), "source")
    if (authority.get("status") != "confirmed" or not text(authority.get("actor"))
            or not isinstance(authority.get("scopes"), list) or scope not in authority.get("scopes", [])
            or not text(authority.get("verified_by"))):
        gaps.append("Confirmed client authority for this scope required")
    source = record(data.get("confirmation"), "source").get("data", {})
    if source.get("medium") != "written" or source.get("origin") != "client":
        gaps.append("Written client confirmation required; verbal statements and consultant recaps do not qualify")
    if (source.get("identity") != "confirmed" or source.get("author") != authority.get("actor")
            or not text(source.get("author")) or source.get("uncertainties") != []):
        gaps.append("Confirmation authorship or meaning is unresolved")
    try:
        date.fromisoformat(source.get("date"))
    except (ValueError, TypeError):
        gaps.append("Confirmation date required")
    if not text(source.get("location")):
        gaps.append("Confirmation evidence location required")
    confirmation = source.get("confirmation", {})
    if not isinstance(confirmation, dict) or (confirmation.get("target") != data.get("target")
            or confirmation.get("scope") != scope or confirmation.get("response") != "accept"
            or data.get("intent", "accept") not in ("accept", "exclude")
            or confirmation.get("intent", "accept") != data.get("intent", "accept")):
        gaps.append("Confirmation does not accept this exact scope and version")
    return {"ready": not gaps, "evidence_class": "reported", "decision": decision_id,
            "intent": intent, "expected_intent": expected_intent,
            "revision": current["revision"] if current else None, "gaps": gaps,
            "limitations": "Checks supplied records, not authorship, authority truth or semantic entailment. No publication permission."}


def coverage(store, mission_id):
    """Check declared coverage. Semantic completeness still requires independent review."""
    state = store.status()
    gaps, checked = [], set()

    def read(ref, kind):
        if not isinstance(ref, dict) or set(ref) != {"id", "revision"}:
            gaps.append(f"Missing exact {kind} reference")
            return {}
        current = state["records"].get(ref["id"])
        if not current or not current["current"] or current["revision"] != ref["revision"]:
            gaps.append(f"{ref['id']}: stale, pending or absent")
            return {}
        record = store.read_record(ref["id"], ref["revision"])
        if kind and record["kind"] != kind:
            gaps.append(f"{ref['id']}: expected {kind}")
            return {}
        return record.get("data", {})

    def items(data, key, nonempty=False):
        value = data.get(key)
        if not isinstance(value, list) or (nonempty and not value):
            gaps.append(f"Explicit {key} list required")
            return []
        return value

    def requirement(ref):
        data = read(ref, "requirement")
        for key in ("actor", "trigger", "outcome", "verification"):
            if not text(data.get(key)):
                gaps.append(f"Requirement {key} missing")
        if data.get("gaps") != []:
            gaps.append("Requirement has unresolved or unassessed gaps")
        if not all(text(rule) for rule in items(data, "rules", True)):
            gaps.append("Requirement rules must be explicit")
        for key, fields, rationale in (
                ("handoffs", ("to", "when", "information"), "handoff_rationale"),
                ("exceptions", ("condition", "response", "owner"), "exception_rationale")):
            entries = items(data, key)
            if not entries and not text(data.get(rationale)):
                gaps.append(f"{key}: entries or an evidence-backed absence rationale required")
            for entry in entries:
                if not isinstance(entry, dict) or not all(text(entry.get(f)) for f in fields):
                    gaps.append(f"{key}: missing {', '.join(fields)}")
        for source_ref in items(data, "sources", True):
            source = read(source_ref, "source")
            if (source.get("verification") != "checked" or not text(source.get("checked_by"))
                    or not text(source.get("location")) or not text(source.get("author"))
                    or source.get("uncertainties") != []):
                gaps.append("Material source is provisional, unattributed or uncertain")
            try:
                date.fromisoformat(source.get("date"))
            except (ValueError, TypeError):
                gaps.append("Material source date missing")

    def mission(ref):
        data = read(ref, "mission")
        if not data:
            gaps.append("Mission coverage has not been assessed")
            return
        pair = (ref["id"], ref["revision"])
        if pair in checked:
            return
        checked.add(pair)
        read(data.get("intent"), "source")
        if data.get("gaps") != []:
            gaps.append(f"{ref['id']}: unresolved or unassessed mission gaps")
        criteria = items(data, "criteria", True)
        ids = []
        for criterion in criteria:
            if not isinstance(criterion, dict) or not all(text(criterion.get(k)) for k in ("id", "description")):
                gaps.append("Each criterion needs a stable ID and observable description")
            else:
                ids.append(criterion["id"])
        if len(ids) != len(set(ids)):
            gaps.append("Duplicate criterion ID")
        covered = set()
        for entry in items(data, "coverage", True):
            if not isinstance(entry, dict) or entry.get("criterion") not in ids:
                gaps.append("Coverage references an unknown criterion")
                continue
            if entry["criterion"] in covered:
                gaps.append("Duplicate criterion disposition")
            covered.add(entry["criterion"])
            if entry.get("disposition") == "supported":
                requirement(entry.get("record"))
            elif entry.get("disposition") == "excluded":
                target = entry.get("record")
                read(target, "requirement")
                decision_ref = entry.get("decision")
                decision = read(decision_ref, "decision")
                if (not decision or decision.get("intent") != "exclude" or decision.get("target") != target
                        or not baseline(store, decision_ref["id"], "exclude")["ready"]):
                    gaps.append("Exclusion requires current written client agreement covering the excluded requirement")
            else:
                gaps.append(f"{entry['criterion']}: unresolved disposition")
        if set(ids) != covered:
            gaps.append(f"{ref['id']}: criteria missing coverage: {sorted(set(ids) - covered)}")
        for finding in items(data, "findings"):
            read(finding, None)
        for child in items(data, "children"):
            if not isinstance(child, dict):
                gaps.append("Invalid child mission")
                continue
            child_ref = child.get("mission")
            child_data = read(child_ref, "mission")
            mission(child_ref)
            review = read(child.get("integration"), "review")
            findings = child_data.get("findings")
            mapping = review.get("parent_criteria")
            if (not review or review.get("child") != child_ref or review.get("disposition") != "integrated"
                    or review.get("parent") != ref["id"] or review.get("parent_intent") != data.get("intent")
                    or not text(review.get("reviewer")) or review.get("unresolved") != []
                    or not isinstance(findings, list) or review.get("findings") != findings
                    or not isinstance(mapping, list) or not mapping or any(c not in criteria for c in mapping)):
                gaps.append("Child findings and gaps have not been reconciled into parent criteria")

    current = state["records"].get(mission_id)
    mission({"id": mission_id, "revision": current["revision"]} if current else None)
    return {"ready": not gaps, "check_class": "structural-reported", "mission": mission_id,
            "gaps": gaps, "checked_missions": len(checked),
            "limitations": "Declared coverage only. Independent review must detect omitted actors, rules, sources and misleading prose."}

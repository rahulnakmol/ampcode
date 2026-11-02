"""Pure checks of reported business evidence. Never authenticates or grants authority."""

from datetime import date, datetime


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except (ValueError, TypeError):
        return False


def baseline(store, decision_id):
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
            or confirmation.get("scope") != scope or confirmation.get("response") != "accept"):
        gaps.append("Confirmation does not accept this exact scope and version")
    return {"ready": not gaps, "evidence_class": "reported", "decision": decision_id,
            "revision": current["revision"] if current else None, "gaps": gaps,
            "limitations": "Checks supplied records, not authorship, authority truth or semantic entailment. No publication permission."}

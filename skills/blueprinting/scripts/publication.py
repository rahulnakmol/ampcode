"""Check a selected content packet against current reported review and inherited restrictions."""

import math
import re

from engagement import Invalid, digest, identifier, revision
from qualification import text, timestamp


def validate_packet(packet):
    fields = {"schema", "title", "snapshot", "audience", "destination", "blocks"}
    if isinstance(packet, dict) and packet.get("schema") == 3:
        fields.add("presentation")
    if (not isinstance(packet, dict) or set(packet) != fields
            or type(packet["schema"]) is not int or packet["schema"] not in (1, 2, 3)):
        raise Invalid("Unsupported content packet; attachments and unknown fields are not exported")
    if packet["schema"] == 3:
        from branding import validate
        validate(packet["presentation"])
    revision(packet["snapshot"])
    if not all(text(packet[k]) for k in ("title", "audience", "destination")):
        raise Invalid("Packet title, audience and destination required")
    blocks = packet["blocks"]
    if not isinstance(blocks, list) or not blocks:
        raise Invalid("Nonempty content blocks required")
    ids = set()
    for block in blocks:
        common = {"id", "kind", "title", "text", "notes", "caveats", "citations"}
        extra = {"text": set(), "table": {"columns", "rows"}, "chart": {"categories", "series", "unit"}}
        if packet["schema"] >= 2:
            extra["estimate"] = {"model"}
        if not isinstance(block, dict) or block.get("kind") not in extra or set(block) != common | extra[block["kind"]]:
            raise Invalid("Unsupported content block")
        key = identifier(block["id"])
        if key in ids:
            raise Invalid("Duplicate content block ID")
        ids.add(key)
        if not all(text(block[k]) for k in ("title", "text")) or not isinstance(block["notes"], str):
            raise Invalid("Title, explanatory text and explicit notes required")
        if not isinstance(block["caveats"], list) or any(not text(c) for c in block["caveats"]):
            raise Invalid("Explicit caveat list required")
        if block["kind"] == "estimate":
            from estimate import office_values
            office_values(block["model"])
        citations = block["citations"]
        if not isinstance(citations, list) or not citations:
            raise Invalid("Every block requires source citations")
        for cite in citations:
            if (not isinstance(cite, dict) or set(cite) != {"record", "label", "treatment"}
                    or not text(cite["label"]) or cite["treatment"] not in ("citation", "excerpt")):
                raise Invalid("Citation label, exact source and treatment required")
            ref = cite["record"]
            if not isinstance(ref, dict) or set(ref) != {"id", "revision"}:
                raise Invalid("Exact citation reference required")
            identifier(ref["id"])
            revision(ref["revision"])
        if block["kind"] == "table":
            columns, rows = block["columns"], block["rows"]
            if (not isinstance(columns, list) or not columns or any(not text(c) for c in columns)
                    or not isinstance(rows, list) or not rows
                    or any(not isinstance(row, list) or len(row) != len(columns)
                           or any(not isinstance(cell, str) for cell in row) for row in rows)):
                raise Invalid("Rectangular text table required")
        if block["kind"] == "chart":
            categories, series = block["categories"], block["series"]
            if (not text(block["unit"]) or not isinstance(categories, list) or not categories
                    or any(not text(c) for c in categories) or len(set(categories)) != len(categories)
                    or not isinstance(series, list) or not series):
                raise Invalid("Chart categories, series and units required")
            for line in series:
                if (not isinstance(line, dict) or set(line) != {"name", "values"} or not text(line["name"])
                        or not isinstance(line["values"], list) or len(line["values"]) != len(categories)
                        or any(type(v) not in (int, float) or not math.isfinite(v) for v in line["values"])):
                    raise Invalid("Chart needs finite values for every category")
    # Catch common private links across text, notes, tables and citation labels. Not a DLP engine.
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)
    if any(re.search(r"[\x00-\x09\x0b-\x1f\x7f\u2028\u2029]", s) for s in strings(packet)):
        raise Invalid("Unsupported control character in packet; use explicit newlines and re-review the content")
    if any(re.search(r"(?i)(?:file:|obsidian:|notion:|https?://(?:[^/]*\.)?notion\.(?:so|site)(?:/|$)|localhost|127\.0\.0\.1)", s)
           for s in strings(packet)):
        raise Invalid("Private source links must be replaced with approved recipient-safe citation labels")


def publication(store, packet_id, review_id):
    gaps = []
    state = store.status()
    if state["input_observation"]["issues"]:
        gaps.append("Unresolved intake; reconcile registered files and declared folders before publication")
    if any("input_file" in record.get("data", {}) or "intake_folders" in record.get("data", {})
           for operation in state["pending"] for record in store.intent(operation)["records"]):
        gaps.append("Pending input reconciliation; review it before publication")

    def read(ref, kind=None):
        current = state["records"].get(ref["id"])
        if not current or current["revision"] != ref["revision"] or not current["current"]:
            gaps.append(f"{ref['id']}: stale, pending or absent")
            return {}
        record = store.read_record(ref["id"], ref["revision"])
        if kind and record["kind"] != kind:
            gaps.append(f"{ref['id']}: expected {kind}")
            return {}
        return record

    def head(key, kind):
        ref = {"id": key, "revision": state["records"].get(key, {}).get("revision")}
        return ref, read(ref, kind)

    packet_ref, retained = head(packet_id, "artifact")
    _, review_record = head(review_id, "review")
    packet = retained.get("data", {}).get("packet")
    result = {"ready": False, "evidence_class": "reported", "gaps": gaps,
              "limitations": "Reported review and declared restrictions only; not authenticated permission, semantic assurance or delivery."}
    try:
        validate_packet(packet)
    except (ValueError, TypeError, KeyError) as error:
        gaps.append(str(error))
        return result
    review = review_record.get("data", {})
    expected = {"meaning", "language", "confidentiality", "citations"}
    if packet["schema"] == 3:
        expected.add("brand")
    assessments = review.get("assessments")
    if (review.get("purpose") != "publication" or review.get("status") != "approved"
            or review.get("packet") != packet_ref or review.get("packet_hash") != digest(packet)
            or review.get("audience") != packet["audience"] or review.get("destination") != packet["destination"]
            or not text(review.get("reviewer")) or not timestamp(review.get("at"))
            or not isinstance(assessments, dict) or set(assessments) != expected
            or any(v != "passed" for v in assessments.values())):
        gaps.append("Named publication review must cover exact content, recipient, destination and all assessments")
    selected = store.status(packet["snapshot"])
    presentation = packet.get("presentation")
    if presentation and presentation["brand"] is not None:
        from branding import validate_profile
        brand = read(presentation["brand"], "artifact")
        try:
            skill = validate_profile(brand.get("data", {}), presentation)
            if "input_file" not in read(skill, "source").get("data", {}):
                gaps.append("Selected brand skill needs a retained registered source file")
        except (ValueError, TypeError, KeyError) as error:
            gaps.append(str(error))
    for key, head_record in state["records"].items():
        retained_input = store.read_record(key, head_record["revision"])
        if ("input_file" in retained_input.get("data", {})
                and selected["records"].get(key, {}).get("revision") != head_record["revision"]):
            gaps.append("Input inventory changed since packet source snapshot; review impact and packet")

    def policy_check(record, treatments, caveats):
        policy = record.get("data", {}).get("publication", {})
        if not isinstance(policy, dict):
            gaps.append(f"{record.get('id')}: invalid publication policy")
            return
        grants = policy.get("grants", [])
        allowed = any(isinstance(g, dict) and g.get("audience") == packet["audience"]
                      and g.get("destination") == packet["destination"]
                      and isinstance(g.get("treatments"), list)
                      and all(isinstance(t, str) for t in g["treatments"])
                      and treatments <= set(g["treatments"])
                      for g in grants) if isinstance(grants, list) else False
        required = policy.get("required_caveats")
        if not allowed:
            gaps.append(f"{record.get('id')}: no declared permission for recipient, destination and treatment")
        if not isinstance(required, list) or any(not text(c) or c not in caveats for c in required):
            gaps.append(f"{record.get('id')}: unknown or omitted required caveat")

    def restrictions(ref, treatments, caveats, seen):
        pair = (ref["id"], ref["revision"])
        if pair in seen:
            return
        seen.add(pair)
        item = selected["records"].get(ref["id"])
        if not item or item["revision"] != ref["revision"] or not item["current"]:
            gaps.append(f"{ref['id']}: not current in selected source snapshot")
        record = read(ref)
        policy_check(record, treatments, caveats)
        for edge in record.get("inputs", []):
            restrictions({"id": edge["id"], "revision": edge["revision"]}, treatments, caveats, seen)

    cited = {(c["record"]["id"], c["record"]["revision"])
             for block in packet["blocks"] for c in block["citations"]}
    for block in packet["blocks"]:
        notes = {"notes"} if block["notes"] or block["kind"] == "estimate" else set()
        treatments = {c["treatment"] for c in block["citations"]} | notes
        # The packet postdates the source snapshot. Its declared restrictions still apply.
        if "publication" in retained.get("data", {}):
            policy_check(retained, treatments, block["caveats"])
        for edge in retained.get("inputs", []):
            if edge["relation"] == "governed-by" or (edge["id"], edge["revision"]) not in cited:
                restrictions({"id": edge["id"], "revision": edge["revision"]}, treatments, block["caveats"], set())
        for cite in block["citations"]:
            treatments = {cite["treatment"]} | notes
            restrictions(cite["record"], treatments, block["caveats"], set())
    if not gaps:
        result.update(ready=True, packet_hash=digest(packet), packet=packet)
    return result

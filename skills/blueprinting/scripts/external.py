"""Local external-effect journal. Never calls a cloud tool or turns a timeout into a retry."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile

from engagement import Invalid, digest, identifier, revision
from export import markdown
from publication import publication
from qualification import text, timestamp


def current(store, key):
    state = store.status()
    head = state["records"].get(key)
    if not head:
        raise Invalid("Unknown external operation")
    record = store.read_record(key, head["revision"])
    data = record.get("data", {})
    if record["kind"] != "artifact" or data.get("purpose") != "external-effect":
        raise Invalid("Not an external-operation record")
    return record, head


def save(store, key, data, inputs, previous=None):
    record = {"schema": 1, "engagement": store.config["engagement"], "id": identifier(key),
              "kind": "artifact", "previous": previous, "inputs": inputs,
              "body": "External effect journal. Status is reported; consult source evidence before relying on delivery.",
              "data": data}
    operation = store.prepare([record])
    store.commit(operation)
    return {"id": key, "revision": digest(record), "state": data["state"],
            "operation_marker": data["operation_marker"], "remote_effect": False}


def prepare(store, value):
    fields = {"id", "packet", "review", "kind", "content_hash", "authorized_by", "authorized_at"}
    if not isinstance(value, dict) or set(value) != fields:
        raise Invalid("Explicit operation ID, packet/review IDs, kind, content hash and authorization required")
    identifier(value["id"])
    revision(value["content_hash"])
    if value["kind"] not in ("notion-new-page", "native-reminder"):
        raise Invalid("Only new-page or native-reminder effects are supported")
    if not text(value["authorized_by"]) or not timestamp(value["authorized_at"]):
        raise Invalid("Named and dated effect authorization required; this is reported, not authenticated")
    state = store.status()
    if value["id"] in state["records"]:
        raise Invalid("Operation ID already exists; inspect and reconcile it rather than prepare a duplicate")
    checked = publication(store, value["packet"], value["review"])
    if not checked["ready"]:
        raise Invalid("Publication blocked: " + "; ".join(checked["gaps"]))
    prior = [store.read_record(key, head["revision"]) for key, head in state["records"].items()]
    prior.extend(record for operation in state["pending"] for record in store.intent(operation)["records"])
    for record in prior:
        effect = record.get("data", {})
        if (effect.get("purpose") == "external-effect" and effect.get("kind") == value["kind"]
                and effect.get("content_hash") == value["content_hash"]
                and effect.get("destination") == checked["packet"]["destination"]):
            raise Invalid("Matching content/destination already has an operation; a new ID must not bypass reconciliation")
    with tempfile.TemporaryDirectory() as temporary:
        content = Path(temporary) / "content.md"
        markdown(checked["packet"], content)
        if hashlib.sha256(content.read_bytes()).hexdigest() != value["content_hash"]:
            raise Invalid("Content hash must match the reviewed packet's Markdown export")
    inputs = [{"relation": "derived-from", "id": key, "revision": state["records"][key]["revision"]}
              for key in (value["packet"], value["review"])]
    data = dict(value, purpose="external-effect", state="prepared", audience=checked["packet"]["audience"],
                destination=checked["packet"]["destination"], packet_hash=checked["packet_hash"],
                packet={"id": value["packet"], "revision": inputs[0]["revision"]},
                review={"id": value["review"], "revision": inputs[1]["revision"]})
    data["operation_marker"] = digest({"engagement": store.config["engagement"], "intent": data})
    return save(store, value["id"], data, inputs)


def attempt(store, key):
    record, head = current(store, key)
    if not head["current"] or record["data"]["state"] != "prepared":
        raise Invalid("Only a current prepared operation may begin; reconcile any uncertain prior attempt")
    data = dict(record["data"], state="unknown", attempted_at=datetime.now(timezone.utc).isoformat())
    # Write uncertainty BEFORE the host tool call. A crash cannot leave a retryable prepared state.
    result = save(store, key, data, record["inputs"], head["revision"])
    result["instruction"] = "One host attempt may follow explicit authorization. If its result is uncertain, do not retry; reconcile the marker and destination."
    return result


def reconcile(store, key, evidence_ref):
    record, head = current(store, key)
    data = record["data"]
    if data["state"] != "unknown":
        raise Invalid("Only an attempted unknown operation can be reconciled")
    if not isinstance(evidence_ref, dict) or set(evidence_ref) != {"id", "revision"}:
        raise Invalid("Exact readback evidence reference required")
    evidence_head = store.status()["records"].get(evidence_ref["id"])
    if not evidence_head or not evidence_head["current"] or evidence_head["revision"] != evidence_ref["revision"]:
        raise Invalid("Readback evidence is absent, stale or pending")
    source = store.read_record(evidence_ref["id"], evidence_ref["revision"])
    observed = source.get("data", {})
    if (source["kind"] != "source" or observed.get("operation_marker") != data["operation_marker"]
            or observed.get("destination") != data["destination"] or not text(observed.get("checked_by"))
            or not timestamp(observed.get("checked_at")) or not text(observed.get("location"))):
        raise Invalid("Readback needs matching marker/destination, named check, timestamp and evidence location")
    if (observed.get("outcome") != "verified" or not text(observed.get("effect_id"))
            or observed.get("content_hash") != data["content_hash"]):
        raise Invalid("No verified matching effect; absence from search is not proof of absence and does not permit retry")
    if datetime.fromisoformat(observed["checked_at"]) < datetime.fromisoformat(data["attempted_at"]):
        raise Invalid("Readback predates the recorded attempt")
    updated = dict(data, state="verified", receipt=evidence_ref, effect_id=observed["effect_id"])
    inputs = [*record["inputs"], {"relation": "derived-from", **evidence_ref}]
    return save(store, key, updated, inputs, head["revision"])


def status(store, key):
    record, head = current(store, key)
    data = record["data"]
    return {"state": data["state"], "operation_marker": data["operation_marker"],
            "destination": data["destination"], "effect_id": data.get("effect_id"),
            "dependencies_current": head["current"], "evidence_class": "reported",
            "retry_allowed": False, "limitations": "Inspect the retained evidence. A recorded effect is not permission to reuse changed content or resend."}

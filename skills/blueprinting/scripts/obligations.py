"""Read-only response scan. Reported receipts are not authenticated delivery or decisions."""

from datetime import datetime, timedelta

from engagement import Invalid, digest, revision
from qualification import baseline, text, timestamp
from upkeep import deadline


def scan(store, at, cadence_seconds, last_check=None):
    if not timestamp(at) or type(cadence_seconds) is not int or cadence_seconds < 1:
        raise Invalid("An offset-aware check time and positive cadence in seconds are required")
    now = datetime.fromisoformat(at)
    state = store.status()
    records = {key: store.read_record(key, head["revision"]) for key, head in state["records"].items()}
    gaps = []

    def ref(key):
        return {"id": key, "revision": state["records"][key]["revision"]}

    def read(link, kind=None):
        if not isinstance(link, dict) or set(link) != {"id", "revision"}:
            raise Invalid("Missing exact evidence reference")
        head = state["records"].get(link["id"])
        if not head or not head["current"] or head["revision"] != link["revision"]:
            raise Invalid(f"{link['id']}: evidence stale, pending or absent")
        record = records[link["id"]]
        if kind and record["kind"] != kind:
            raise Invalid(f"{link['id']}: expected {kind}")
        if "data" not in record:
            raise Invalid(f"{link['id']}: structured evidence missing")
        return record["data"]

    def instant(value):
        if not timestamp(value):
            raise Invalid("Explicit offset-aware time required")
        return datetime.fromisoformat(value)

    def history(record):
        chain = [record]
        while chain[-1]["previous"]:
            chain.append(store.read_record(record["id"], chain[-1]["previous"]))
        return list(reversed(chain))

    decisions = []
    for key, record in records.items():
        if not any(item["kind"] == "decision" for item in history(record)):
            continue
        original = next(item for item in history(record) if item["kind"] == "decision")
        first = original.get("data", {}).get("first_raised")
        age = None
        try:
            age = (now - instant(first)).total_seconds()
            if age < 0:
                raise Invalid("Decision was first raised after this check")
        except Invalid as error:
            gaps.append(f"{key}: {error}")
        data = record.get("data", {})
        resolved = record["kind"] == "decision" and baseline(store, key)["ready"]
        if data.get("state") in ("accepted", "withdrawn") and not resolved:
            gaps.append(f"{key}: claimed closure lacks current qualified decision evidence")
        decisions.append({"id": key, "state": "resolved" if resolved else "open", "first_raised": first,
                          "age_seconds": age, "question": data.get("question", original.get("data", {}).get("question"))})

    protected = ("decision", "owner", "start", "due", "calendar", "due_basis", "next_action", "follows", "agreement")
    rows = []
    for key, record in records.items():
        chain = history(record)
        versions = [item for item in chain if item.get("data", {}).get("purpose") == "response-obligation"]
        if not versions:
            continue
        row_gaps = []
        rejected = []
        needs_repair = False
        retained = versions[0]
        for item in chain[chain.index(retained) + 1:]:
            before = {field: retained["data"].get(field) for field in protected}
            after = {field: item.get("data", {}).get(field) for field in protected}
            try:
                if item.get("data", {}).get("purpose") != "response-obligation" or item["kind"] != "artifact":
                    raise Invalid("Response obligation cannot be hidden by changing its kind or purpose")
                if before != after or needs_repair:
                    amendment = read(item["data"].get("amendment"), "review")
                    if (amendment.get("purpose") != "obligation-amendment" or amendment.get("status") != "approved"
                            or amendment.get("previous_revision") != digest(retained)
                            or amendment.get("changes_hash") != digest(after)
                            or not text(amendment.get("reviewer")) or not text(amendment.get("reason"))
                            or not timestamp(amendment.get("at")) or instant(amendment["at"]) > now):
                        raise Invalid("Exact reviewed amendment required")
                retained = item
                needs_repair = False
            except Invalid as error:
                rejected.append({"revision": digest(item), "reason": str(error)})
                needs_repair = True
        data = retained["data"]
        current = state["records"][key]["current"] and digest(retained) == state["records"][key]["revision"]
        if not current:
            row_gaps.append("Obligation is stale, pending or has an unqualified amendment")
            if rejected:
                row_gaps.append(f"Unqualified amendment: {rejected[-1]['reason']}")
        due, start = None, None
        try:
            start, due = instant(data.get("start")), instant(data.get("due"))
            if due <= start or start > now:
                raise Invalid("Deadline must follow start, and start must not be in the future")
            calendar = read(data.get("calendar"), "source")["calendar"]
            if data.get("due_basis") == "next-working-day":
                computed = deadline({"schema": 1, "start": data["start"], "calendar": calendar})
                if instant(computed["due"]) != due:
                    raise Invalid("Stored deadline differs from its working calendar; explicit agreement required")
            elif data.get("due_basis") == "agreed":
                agreement = read(data.get("agreement"), "source")
                if (agreement.get("outcome") != "agreed" or agreement.get("due") != data.get("due")
                        or agreement.get("owner") != data.get("owner") or agreement.get("decision") != data.get("decision")
                        or not text(agreement.get("agreed_by")) or not text(agreement.get("location"))
                        or not timestamp(agreement.get("at")) or instant(agreement["at"]) > now):
                    raise Invalid("Named agreement to this owner, decision and due time required")
            else:
                raise Invalid("Explicit deadline basis required")
            if not text(data.get("next_action")):
                raise Invalid("Specific next action required")
            read(data.get("decision"), "decision")
        except (Invalid, KeyError, TypeError, ValueError) as error:
            row_gaps.append(str(error))
        overdue = max(0, (now - due).total_seconds()) if due else None
        stage = "overdue" if overdue else "due" if due and now == due else "upcoming"
        rows.append({"id": key, "revision": digest(retained), "decision": data.get("decision"),
                     "owner": data.get("owner"), "unassigned": not text(data.get("owner")),
                     "start": data.get("start"), "due": data.get("due"), "state": "overdue" if overdue else "pending",
                     "overdue_seconds": overdue, "late_seconds": None, "current": current,
                     "reminder_stage": stage, "follows": data.get("follows"), "gaps": row_gaps,
                     "rejected_amendments": rejected})

    actions = {}
    for key, record in records.items():
        data = record.get("data", {})
        if data.get("purpose") != "response-action":
            continue
        try:
            read(ref(key), "artifact")
            obligation = read(data.get("obligation"), "artifact")
            if obligation.get("purpose") != "response-obligation" or data.get("state") != "sent":
                raise Invalid("Draft or unverified follow-up is not a sent action")
            review = read(data.get("review"), "review")
            receipt = read(data.get("receipt"), "source")
            revision(review.get("content_hash"))
            if (review.get("purpose") != "followup" or review.get("status") != "approved"
                    or review.get("obligation") != data["obligation"] or not text(review.get("reviewer"))
                    or not text(review.get("destination")) or receipt.get("outcome") != "sent"
                    or receipt.get("destination") != review["destination"]
                    or receipt.get("content_hash") != review["content_hash"]
                    or not all(text(receipt.get(field)) for field in ("checked_by", "effect_id", "location"))):
                raise Invalid("Reviewed follow-up and matching sent receipt required")
            sent = instant(receipt.get("sent_at"))
            if not instant(review.get("at")) <= sent <= instant(receipt.get("checked_at")) <= now:
                raise Invalid("Review, send, readback and scan times must be ordered")
            if sent < instant(obligation.get("start")):
                raise Invalid("Follow-up predates its obligation")
            actions[key] = {"obligation": data["obligation"], "sent": sent}
        except (Invalid, KeyError, TypeError) as error:
            gaps.append(f"{key}: {error}")

    for row in rows:
        matched = [(key, value) for key, value in actions.items()
                   if value["obligation"] == {"id": row["id"], "revision": row["revision"]}]
        if matched and row["current"] and not row["gaps"]:
            key, action = min(matched, key=lambda pair: pair[1]["sent"])
            row["state"] = "action-recorded"
            row["late_seconds"] = max(0, (action["sent"] - instant(row["due"])).total_seconds())
            successors = [item for item in rows if item["follows"] == ref(key) and item["decision"] == row["decision"]
                          and item["current"] and not item["gaps"] and not item["unassigned"]
                          and instant(item["start"]) == action["sent"]]
            if not successors:
                row["gaps"].append("Sent follow-up has no current owned next response obligation")
        if row["follows"]:
            parent = actions.get(row["follows"].get("id")) if isinstance(row["follows"], dict) else None
            if not parent or row["follows"] != ref(row["follows"]["id"]):
                row["gaps"].append("Next response does not follow a current verified sent action")
        marker = digest({"obligation": {"id": row["id"], "revision": row["revision"]}, "stage": row["reminder_stage"]})
        row["reminder_marker"] = marker
        row["notification"] = "needed" if row["state"] != "action-recorded" else "not-needed"
        for receipt_key, receipt_record in records.items():
            receipt = receipt_record.get("data", {})
            unknown = [item for item in history(receipt_record)
                       if item.get("data", {}).get("purpose") == "reminder-receipt"
                       and item["data"].get("outcome") == "unknown"
                       and isinstance(item["data"].get("obligation"), dict)
                       and item["data"]["obligation"].get("id") == row["id"]]
            for prior in unknown:
                try:
                    # Delivery is historical: an owner transfer cannot undo an observed effect.
                    # Only the original obligation edge may be old; other evidence stays current.
                    for edge in receipt_record["inputs"]:
                        link = {"id": edge["id"], "revision": edge["revision"]}
                        if link != prior["data"]["obligation"]:
                            read(link)
                    if (receipt_record["kind"] != "source" or receipt.get("purpose") != "reminder-receipt" or receipt.get("outcome") != "sent"
                            or not isinstance(receipt.get("reconciles"), list) or digest(prior) not in receipt["reconciles"]
                            or any(receipt.get(field) != prior["data"].get(field) for field in ("obligation", "marker", "stage"))
                            or not all(text(receipt.get(field)) for field in ("effect_id", "checked_by", "location"))
                            or not instant(prior["data"].get("checked_at")) <= instant(receipt.get("checked_at")) <= now):
                        raise Invalid("Unknown reminder needs matching reported readback reconciliation")
                except Invalid as error:
                    row["notification"] = "reconcile"
                    row["gaps"].append(f"{receipt_key}: {error}")
            target = receipt.get("obligation")
            if (receipt.get("purpose") != "reminder-receipt" or not isinstance(target, dict)
                    or target.get("id") != row["id"]):
                continue
            # An uncertain earlier stage cannot be bypassed by a later stage or amendment.
            if receipt.get("outcome") == "unknown":
                row["notification"] = "reconcile"
                continue
            if receipt.get("marker") != marker:
                continue
            try:
                read(ref(receipt_key), "source")
                if (receipt.get("outcome") != "sent" or not text(receipt.get("checked_by"))
                        or not text(receipt.get("location")) or instant(receipt.get("checked_at")) > now
                        or not text(receipt.get("effect_id"))
                        or target != {"id": row["id"], "revision": row["revision"]}):
                    raise Invalid("Observed reminder outcome, identity and time required")
                if row["notification"] != "reconcile":
                    row["notification"] = "recorded"
            except Invalid as error:
                row["gaps"].append(f"{receipt_key}: {error}")
        gaps.extend(f"{row['id']}: {gap}" for gap in row["gaps"])

    for decision in decisions:
        if decision["state"] == "open" and not any(isinstance(row["decision"], dict)
                and row["decision"].get("id") == decision["id"] for row in rows):
            gaps.append(f"{decision['id']}: open decision has no response obligation")
    for operation in state["pending"]:
        for record in store.intent(operation)["records"]:
            gaps.append(f"{record['id']}: pending operation {operation} requires reconciliation")
        # The committed view cannot safely decide whether an uncommitted receipt already sent.
        for row in rows:
            row["notification"] = "reconcile"
    recovery = {"last_check": None, "elapsed_seconds": None, "missed_checks": None}
    if last_check:
        check = read(ref(last_check), "artifact") if last_check in records else {}
        if check.get("purpose") != "obligation-check" or check.get("outcome") != "observed":
            raise Invalid("Last check must be a retained observed obligation scan")
        interval = now - instant(check.get("checked_at"))
        elapsed = interval.total_seconds()
        if elapsed < 0:
            raise Invalid("Last check is in the future")
        recovery = {"last_check": ref(last_check), "elapsed_seconds": elapsed,
                    "missed_checks": max(0, (interval - timedelta(microseconds=1)) // timedelta(seconds=cadence_seconds))}
    else:
        gaps.append("No previous observed check; monitoring coverage is unknown")
    return {"schema": 1, "checked_at": at, "snapshot": state["snapshot"], "evidence_class": "reported",
            "decisions": decisions, "obligations": rows, "pending_operations": state["pending"],
            "recovery": recovery, "gaps": gaps, "remote_effect": False,
            "limitations": "Full retained scan, not a scheduler or delivery proof. Review gaps and actual evidence; no client contact is authorized."}

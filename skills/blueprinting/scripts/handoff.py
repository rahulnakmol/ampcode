"""Private export candidates and exact inspected-byte ZIPs. No delivery or approval authority."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from engagement import Invalid, canonical, digest, exclusive, identifier, read_json, sync_directory
from export import render
from publication import publication
from qualification import text, timestamp


FORMATS = {"md": ".md", "docx": ".docx", "pptx": ".pptx", "xlsx": ".xlsx", "pdf-document": ".pdf", "pdf-deck": ".pdf"}


def current(store, key, kind):
    state = store.status()
    if state["pending"]:
        raise Invalid("Reconcile pending operations before preparing a handoff")
    head = state["records"].get(identifier(key))
    if not head or not head["current"]:
        raise Invalid(f"{key}: handoff evidence stale or absent")
    record = store.read_record(key, head["revision"])
    if record["kind"] != kind:
        raise Invalid(f"{key}: expected {kind}")
    return {"id": key, "revision": head["revision"]}, record


def reviewed(data, purpose, assessments):
    if (data.get("purpose") != purpose or data.get("status") != "approved"
            or not text(data.get("reviewer")) or not timestamp(data.get("at"))
            or datetime.fromisoformat(data["at"]) > datetime.now(timezone.utc)
            or data.get("assessments") != {key: "passed" for key in assessments}):
        raise Invalid("Named current reported review of every applicable assessment required")


def selection(store, selection_id, review_id):
    selected_ref, selected_record = current(store, selection_id, "artifact")
    review_ref, review_record = current(store, review_id, "review")
    data = selected_record.get("data", {})
    selected = data.get("selection")
    if (data.get("purpose") != "export-selection" or not isinstance(selected, dict)
            or set(selected) != {"schema", "audience", "destination", "files"}
            or type(selected["schema"]) is not int or selected["schema"] != 1
            or not all(text(selected[k]) for k in ("audience", "destination"))
            or not isinstance(selected["files"], list) or not selected["files"]):
        raise Invalid("Explicit schema-1 handoff selection required")
    review = review_record.get("data", {})
    reviewed(review, "package-selection", ("consistency", "confidentiality", "selection"))
    if review.get("selection") != selected_ref or review.get("selection_hash") != digest(selected):
        raise Invalid("Consistency review must cover this exact selection")
    names, packets = set(), []
    for item in selected["files"]:
        if not isinstance(item, dict) or set(item) != {"name", "format", "packet", "review"}:
            raise Invalid("Selected filename, format and exact packet/review references required")
        name, format = item["name"], item["format"]
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.[a-z]+", name)
                or not isinstance(format, str) or format not in FORMATS or not name.endswith(FORMATS[format])
                or name.casefold() in names or name.casefold() == "manifest.json"
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])", name.split(".")[0])):
            raise Invalid("Use unique portable filenames and supported matching formats")
        names.add(name.casefold())
        for field, kind in (("packet", "artifact"), ("review", "review")):
            link = item[field]
            if (not isinstance(link, dict) or set(link) != {"id", "revision"}
                    or current(store, link["id"], kind)[0] != link):
                raise Invalid("Selected packet or review revision changed")
        result = publication(store, item["packet"]["id"], item["review"]["id"])
        if not result["ready"]:
            raise Invalid("Publication blocked: " + "; ".join(result["gaps"]))
        packet = result["packet"]
        if any(packet[k] != selected[k] for k in ("audience", "destination")):
            raise Invalid("Every selected packet must share its reviewed audience and destination")
        packets.append(packet)
    return selected_ref, review_ref, selected, packets


def exporter_version():
    # Bind implementation/layout identity as well as native renderer identity on each file.
    libraries = {}
    for name in ("python-docx", "python-pptx", "lxml", "Pillow", "XlsxWriter"):
        try:
            libraries[name] = version(name)
        except PackageNotFoundError:
            libraries[name] = None
    return {"libraries": libraries, "implementation": {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ("export.py", "publication.py", "estimate.py", "workbook.py", "export-requirements.txt")}}


def stage(store, selection_id, review_id, candidate):
    selected_ref, review_ref, selected, packets = selection(store, selection_id, review_id)
    directory = store.path(".blueprinting", "exports", identifier(candidate))
    if directory.exists():
        raise Invalid("Candidate already exists; inspect it or choose a new candidate ID, never overwrite")
    directory.mkdir(parents=True, mode=0o700)
    plan = {"schema": 1, "candidate": candidate, "selection": selected_ref, "review": review_ref,
            "exporter": exporter_version()}
    exclusive(directory / "plan.json", canonical(plan))
    files = []
    for item, packet in zip(selected["files"], packets):
        result = render(packet, item["format"], store.path(".blueprinting", "exports", candidate, item["name"]))
        files.append({"name": item["name"], "format": item["format"], "revision": item["packet"]["revision"],
                      "sha256": result["sha256"], "renderer": result["renderer"]})
    if selection(store, selection_id, review_id)[:2] != (selected_ref, review_ref) or exporter_version() != plan["exporter"]:
        raise Invalid("Selection or exporter changed during staging; candidate remains incomplete")
    manifest = dict(plan, files=files, created_at=datetime.now(timezone.utc).isoformat())
    manifest_hash = digest(manifest)
    exclusive(directory / (manifest_hash + ".json"), canonical(manifest))
    return {"candidate": candidate, "directory": str(directory), "manifest_hash": manifest_hash,
            "files": files, "state": "awaiting-inspection", "remote_effect": False,
            "next": "Inspect these exact files; edit disposable copies only. Retain the named inspection before packaging."}


def status(store, candidate=None):
    if candidate is None:
        return [status(store, path.name) for path in sorted(store.path(".blueprinting", "exports").glob("*"))]
    directory = store.path(".blueprinting", "exports", identifier(candidate))
    if not directory.is_dir():
        raise Invalid("Candidate absent")
    manifests = [p for p in directory.glob("*.json") if p.name != "plan.json"]
    if not manifests:
        return {"candidate": candidate, "state": "incomplete", "directory": str(directory),
                "next": "Keep the incomplete candidate for recovery inspection; stage a new ID after resolving the failure"}
    if len(manifests) != 1:
        raise Invalid("Ambiguous candidate manifests")
    manifest = read_json(store.path(".blueprinting", "exports", candidate, manifests[0].name))
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schema", "candidate", "selection", "review", "exporter", "files", "created_at"}
            or digest(manifest) != manifests[0].stem or manifest["candidate"] != candidate
            or type(manifest["schema"]) is not int or manifest["schema"] != 1
            or not timestamp(manifest["created_at"]) or not isinstance(manifest["files"], list)
            or any(not isinstance(item, dict) or set(item) != {"name", "format", "revision", "sha256", "renderer"}
                   for item in manifest["files"])):
        raise Invalid("Candidate manifest changed")
    return {"candidate": candidate, "state": "awaiting-inspection", "directory": str(directory),
            "manifest_hash": digest(manifest), "manifest": manifest}


def package(store, candidate, inspection_id, output):
    report = status(store, candidate)
    if report["state"] == "incomplete":
        raise Invalid("Incomplete candidates cannot be inspected or packaged")
    manifest = report["manifest"]
    selected_ref, review_ref, selected, _ = selection(store, manifest["selection"]["id"], manifest["review"]["id"])
    if ((selected_ref, review_ref) != (manifest["selection"], manifest["review"])
            or exporter_version() != manifest["exporter"]):
        raise Invalid("Candidate selection or exporter changed; render and inspect a new candidate")
    inspection_ref, inspection_record = current(store, inspection_id, "review")
    inspection = inspection_record.get("data", {})
    reviewed(inspection, "package-inspection", ("rendering", "editability", "consistency", "brand"))
    links = {(edge["id"], edge["revision"]) for edge in inspection_record["inputs"]}
    if (inspection.get("candidate") != candidate or inspection.get("manifest_hash") != report["manifest_hash"]
            or inspection.get("files") != manifest["files"]
            or not {(r["id"], r["revision"]) for r in (selected_ref, review_ref)} <= links
            or datetime.fromisoformat(inspection["at"]) < datetime.fromisoformat(manifest["created_at"])):
        raise Invalid("Inspection must follow staging and bind every exact file and selection review")
    expected = [(i["name"], i["format"], i["packet"]["revision"]) for i in selected["files"]]
    if [(i["name"], i["format"], i["revision"]) for i in manifest["files"]] != expected:
        raise Invalid("Candidate files differ from selection")
    files = []
    for item in manifest["files"]:
        path = store.path(".blueprinting", "exports", candidate, item["name"])
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise Invalid("Staged bytes changed after inspection; do not regenerate or package them")
        files.append((item["name"], data))
    output = Path(output)
    if (not output.is_absolute() or output.suffix.lower() != ".zip" or output.exists()
            or any(p.is_symlink() for p in (output, *output.parents))):
        raise Invalid("New absolute non-symlink ZIP output required")
    with tempfile.TemporaryDirectory(prefix=".blueprint-package-", dir=output.parent) as temporary:
        archive_path = Path(temporary) / "handoff.zip"
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for name, data in files:
                archive.writestr(name, data)
            # Only filename/format/revision/hash cross the client boundary, never local plan metadata.
            archive.writestr("manifest.json", canonical({"schema": 1, "files": [
                {key: item[key] for key in ("name", "format", "revision", "sha256")} for item in manifest["files"]]}))
        # Recheck after assembly; the ZIP contains the same byte buffers whose hashes were checked.
        if (selection(store, selected_ref["id"], review_ref["id"])[:2] != (selected_ref, review_ref)
                or current(store, inspection_id, "review")[0] != inspection_ref
                or exporter_version() != manifest["exporter"]):
            raise Invalid("Handoff evidence changed during packaging")
        for item, (_, data) in zip(manifest["files"], files):
            if store.path(".blueprinting", "exports", candidate, item["name"]).read_bytes() != data:
                raise Invalid("Staged bytes changed during packaging")
        with archive_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(archive_path, output)
        sync_directory(output.parent)
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "status": "exported-not-delivered", "remote_effect": False,
            "limitations": "Reported inspection, not proof it occurred. Point-in-time freshness; no delivery, encryption or client acceptance."}

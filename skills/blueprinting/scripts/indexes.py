"""Rebuild derived navigation, preserving human edits before replacing a projection."""

import hashlib
import os
import tempfile
from urllib.parse import quote

from engagement import Invalid, canonical, digest, exclusive, identifier, read_json, revision, sync_directory


def conflicts(store):
    result = []
    for path in sorted(store.path(".blueprinting", "indexes", "conflicts").glob("*.json")):
        value = read_json(store.path(".blueprinting", "indexes", "conflicts", path.name))
        if set(value) != {"path", "sha256"} or digest(value) != path.stem:
            raise Invalid("Index conflict association changed")
        name = value["path"]
        if name != "Indexes/Current.md":
            if not isinstance(name, str) or not name.startswith("Indexes/records/") or not name.endswith(".md"):
                raise Invalid("Invalid projection conflict path")
            identifier(name[len("Indexes/records/"):-3])
        backup = store.path(".blueprinting", "indexes", "conflicts", revision(value["sha256"]) + ".md")
        if hashlib.sha256(backup.read_bytes()).hexdigest() != value["sha256"]:
            raise Invalid("Preserved index edit changed")
        result.append({"path": name, "backup": str(backup)})
    return result


def rebuild(store):
    state = store.status()
    previous, sequence, baseline = None, 0, {}
    for path in sorted(store.path(".blueprinting", "indexes", "generations").glob("*.json")):
        value = read_json(store.path(".blueprinting", "indexes", "generations", path.name))
        if (set(value) != {"schema", "sequence", "parent", "files"} or value["schema"] != 1
                or value["sequence"] != sequence + 1 or value["parent"] != previous
                or path.name != f'{value["sequence"]:08d}-{digest(value)}.json'):
            raise Invalid("Broken derived-index history")
        sequence, previous, baseline = value["sequence"], digest(value), value["files"]
    outputs = {}
    lines = ["# Current engagement index", "", "**Derived navigation — not evidence or approval.**",
             "", f"Observed: {state['input_observation']['completed_at']}",
             f"Snapshot: {state['snapshot'] or 'none'}", "",
             "Use Resume before relying on this view. Do not edit projection properties to record decisions.",
             "", "## Retained records", "", "| Record | Kind | Revision state |", "| --- | --- | --- |"]
    for key, head in sorted(state["records"].items()):
        record = store.read_record(key, head["revision"])
        freshness = "current" if head["current"] else "stale"
        metadata = {"kind": record["kind"], "revision_state": freshness, "record_id": key,
                    "revision": head["revision"], "derived": True}
        outputs[f"Indexes/records/{key}.md"] = ("---\n" + canonical(metadata) + "\n---\n\n"
            + f"# {key}\n\nDerived navigation only. Property edits cannot establish approval.\n\n"
            + f"[Open exact retained revision](../../records/{key}/{head['revision']}.md)\n")
        lines.append(f"| [{key}](records/{key}.md) | {record['kind']} | {freshness} |")
    lines.extend(["", "## Working notes", ""])
    for path in sorted(store.path("notes").glob("*.md")):
        store.path("notes", path.name)
        label = path.stem.replace("[", "\\[").replace("]", "\\]").replace("\n", " ")
        lines.append(f"- [{label}](../notes/{quote(path.name)})")
    if not any(line.startswith("- [") for line in lines):
        lines.append("No working notes yet. Create only the template needed for the next question.")
    lines.extend(["", "## Unresolved intake and operations", "",
                  f"Input observations: {len(state['input_observation']['issues'])}; pending operations: {len(state['pending'])}.",
                  "Run Resume for exact affected inputs and response obligations.", ""])
    outputs["Indexes/Current.md"] = "\n".join(lines)
    conflicts(store)
    for name, body in outputs.items():
        path = store.path(name)
        if path.exists():
            old = path.read_bytes()
            old_hash = hashlib.sha256(old).hexdigest()
            if old_hash != baseline.get(name):
                backup = store.path(".blueprinting", "indexes", "conflicts", old_hash + ".md")
                if not backup.exists():
                    exclusive(backup, old.decode("utf-8"))
                elif backup.read_bytes() != old:
                    raise Invalid("Index conflict backup differs; original preserved in place")
                sync_directory(backup.parent)
                association = {"path": name, "sha256": old_hash}
                link = store.path(".blueprinting", "indexes", "conflicts", digest(association) + ".json")
                if not link.exists():
                    exclusive(link, canonical(association))
                sync_directory(link.parent)
        # A partial rebuild is derived only. A retry preserves mismatched bytes again.
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            for directory in (path.parent, *path.parent.parents):
                sync_directory(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    value = {"schema": 1, "sequence": sequence + 1, "parent": previous,
             "files": {name: hashlib.sha256(body.encode()).hexdigest() for name, body in outputs.items()}}
    exclusive(store.path(".blueprinting", "indexes", "generations", f'{sequence + 1:08d}-{digest(value)}.json'), canonical(value))
    return {"index": str(store.path("Indexes", "Current.md")), "preserved_edits": conflicts(store),
            "next": "Review preserved edits; retain intended evidence through intake, never as projection authority"}

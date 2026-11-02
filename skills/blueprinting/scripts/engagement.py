#!/usr/bin/env python3
"""Local revision records. Reported evidence only; no remote effects or approvals."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


class Invalid(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", value):
        raise Invalid("Invalid identifier")
    return value


def revision(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise Invalid("Invalid revision")
    return value


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Invalid("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def sync_directory(path):
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def exclusive(path, text):
    """Publish complete bytes without replacing an existing path (one writer contract)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Persist directory links too, including those left by an interrupted mkdir on retry.
    for directory in (path.parent, *path.parent.parents):
        sync_directory(directory)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        sync_directory(path.parent)
    finally:
        os.unlink(temporary)


class Engagement:
    """One local automation writer; user notes outside managed folders stay untouched."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.config = read_json(self.path("engagement.json"))
        if self.config != {"schema": 1, "engagement": self.config.get("engagement")}:
            raise Invalid("Unsupported engagement config")
        identifier(self.config["engagement"])

    def path(self, *parts):
        path = self.root.joinpath(*parts)
        # Reject symlinks even when their current target happens to remain inside the repo.
        for parent in (path, *path.parents):
            if parent == self.root:
                break
            if parent.is_symlink():
                raise Invalid("Symlink in managed path")
        if not path.resolve().is_relative_to(self.root):
            raise Invalid("Path escapes engagement")
        return path

    @classmethod
    def create(cls, root, engagement):
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        exclusive(root / "engagement.json", canonical({"schema": 1, "engagement": identifier(engagement)}))
        return cls(root)

    def record_path(self, record_id, rev):
        return self.path("records", identifier(record_id), revision(rev) + ".md")

    def read_record(self, record_id, rev):
        text = self.record_path(record_id, rev).read_bytes().decode("utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            raise Invalid("Invalid retained Markdown")
        metadata, body = text[4:].split("\n---\n", 1)
        value = json.loads(metadata)
        value["body"] = body
        self.validate_record(value)
        if value["id"] != record_id or digest(value) != rev:
            raise Invalid("Immutable record changed")
        return value

    def validate_record(self, value):
        fields = {"schema", "engagement", "id", "kind", "previous", "inputs", "body"}
        if not isinstance(value, dict) or set(value) not in (fields, fields | {"data"}) or value["schema"] != 1:
            raise Invalid("Unsupported record schema")
        if value["engagement"] != self.config["engagement"]:
            raise Invalid("Wrong engagement")
        identifier(value["id"])
        if value["kind"] not in {"source", "note", "claim", "requirement", "decision", "mission", "review", "artifact", "authority"}:
            raise Invalid("Unknown record kind")
        if value["previous"] is not None:
            revision(value["previous"])
        if not isinstance(value["body"], str) or not value["body"].strip():
            raise Invalid("Record body required")
        if not isinstance(value["inputs"], list):
            raise Invalid("Input edges required")
        seen = set()
        for edge in value["inputs"]:
            if not isinstance(edge, dict) or set(edge) != {"relation", "id", "revision"}:
                raise Invalid("Invalid input edge")
            if edge["relation"] not in {"derived-from", "governed-by", "answers", "allocates"}:
                raise Invalid("Unknown relation")
            identifier(edge["id"])
            revision(edge["revision"])
            if canonical(edge) in seen or edge["id"] == value["id"]:
                raise Invalid("Duplicate or self input")
            seen.add(canonical(edge))
        if "data" in value:
            if not isinstance(value["data"], dict):
                raise Invalid("Structured record data must be an object")
            linked = {(e["id"], e["revision"]) for e in value["inputs"]}
            def check_refs(item):
                if isinstance(item, dict):
                    if set(item) == {"id", "revision"}:
                        pair = (identifier(item["id"]), revision(item["revision"]))
                        if pair not in linked:
                            raise Invalid("Structured reference missing from input edges")
                    else:
                        for child in item.values():
                            check_refs(child)
                elif isinstance(item, list):
                    for child in item:
                        check_refs(child)
            check_refs(value["data"])

    def history(self):
        manifests = []
        heads = {}
        parent = None
        for path in sorted(self.path("snapshots").glob("*.json")):
            self.path("snapshots", path.name)
            value = read_json(path)
            if set(value) != {"schema", "engagement", "sequence", "parent", "operation", "heads"}:
                raise Invalid("Invalid snapshot")
            if value["schema"] != 1 or value["engagement"] != self.config["engagement"]:
                raise Invalid("Unsupported snapshot")
            if value["sequence"] != len(manifests) + 1 or value["parent"] != parent:
                raise Invalid("Broken snapshot chain")
            if path.name != f'{value["sequence"]:08d}-{digest(value)}.json':
                raise Invalid("Immutable snapshot changed")
            intent = self.intent(value["operation"])
            if intent["base"] != parent:
                raise Invalid("Operation base mismatch")
            for record in intent["records"]:
                if record["previous"] != heads.get(record["id"]):
                    raise Invalid("Record predecessor mismatch")
                rev = digest(record)
                retained = self.read_record(record["id"], rev)
                if retained != record:
                    raise Invalid("Intent and retained record differ")
                # Dependencies must already exist in committed history, preventing cycles.
                for edge in record["inputs"]:
                    if not any(m["heads"].get(edge["id"]) == edge["revision"] for m in manifests):
                        raise Invalid("Uncommitted input")
                heads[record["id"]] = rev
            if heads != value["heads"]:
                raise Invalid("Snapshot does not match operation")
            manifests.append(value)
            parent = digest(value)
        return manifests

    def intent(self, operation):
        value = read_json(self.path("operations", revision(operation) + ".json"))
        if set(value) != {"schema", "engagement", "base", "records"} or value["schema"] != 1:
            raise Invalid("Invalid operation")
        if value["engagement"] != self.config["engagement"] or digest(value) != operation:
            raise Invalid("Operation changed or wrong engagement")
        if value["base"] is not None:
            revision(value["base"])
        if not isinstance(value["records"], list) or not value["records"]:
            raise Invalid("Empty operation")
        ids = []
        for record in value["records"]:
            self.validate_record(record)
            ids.append(record["id"])
        if len(set(ids)) != len(ids):
            raise Invalid("Duplicate record ID")
        return value

    def prepare(self, records):
        history = self.history()
        heads = history[-1]["heads"] if history else {}
        if not isinstance(records, list) or not records:
            raise Invalid("Nonempty record list required")
        for record in records:
            self.validate_record(record)
            if record["previous"] != heads.get(record["id"]):
                raise Invalid("Record predecessor mismatch")
            for edge in record["inputs"]:
                if not any(m["heads"].get(edge["id"]) == edge["revision"] for m in history):
                    raise Invalid("Uncommitted input")
        if len({r["id"] for r in records}) != len(records):
            raise Invalid("Duplicate record ID")
        value = {"schema": 1, "engagement": self.config["engagement"],
                 "base": digest(history[-1]) if history else None, "records": records}
        operation = digest(value)
        path = self.path("operations", operation + ".json")
        if path.exists():
            if self.intent(operation) != value:
                raise Invalid("Existing operation differs")
            sync_directory(path.parent)
        else:
            exclusive(path, canonical(value))
        return operation

    def commit(self, operation):
        history = self.history()
        intent = self.intent(operation)
        # A previous process may have linked these files but stopped before the directory sync.
        sync_directory(self.path("operations"))
        for manifest in history:
            if manifest["operation"] == operation:
                sync_directory(self.path("snapshots"))
                return digest(manifest)
        parent = digest(history[-1]) if history else None
        if intent["base"] != parent:
            raise Invalid("Pending operation needs reconciliation against newer snapshot")
        heads = dict(history[-1]["heads"]) if history else {}
        for value in intent["records"]:
            rev = digest(value)
            path = self.record_path(value["id"], rev)
            if path.exists():
                if self.read_record(value["id"], rev) != value:
                    raise Invalid("Existing retained revision differs")
                sync_directory(path.parent)
            else:
                metadata = {key: val for key, val in value.items() if key != "body"}
                exclusive(path, "---\n" + canonical(metadata) + "\n---\n" + value["body"])
            heads[value["id"]] = rev
        manifest = {"schema": 1, "engagement": self.config["engagement"],
                    "sequence": len(history) + 1, "parent": parent,
                    "operation": operation, "heads": heads}
        snap = digest(manifest)
        exclusive(self.path("snapshots", f'{manifest["sequence"]:08d}-{snap}.json'), canonical(manifest))
        self.history()
        return snap

    def validate_resolution(self, value, history):
        from qualification import text, timestamp
        if not isinstance(value, dict) or set(value) != {"operation", "snapshot", "reviewer", "reason", "at"}:
            raise Invalid("Invalid reconciliation record")
        if not text(value["reviewer"]) or not text(value["reason"]) or not timestamp(value["at"]):
            raise Invalid("Reconciliation needs named reviewer, reason and dated review")
        operation = revision(value["operation"])
        original = self.intent(operation)
        if any(m["operation"] == operation for m in history):
            raise Invalid("Committed operation cannot be reconciled away")
        replacement = next((m for m in history if digest(m) == revision(value["snapshot"])), None)
        if replacement is None:
            raise Invalid("Reconciliation requires a committed replacement")
        changes = self.intent(replacement["operation"])["records"]
        expected = {r["id"] for r in original["records"]}
        if not expected <= {r["id"] for r in changes}:
            raise Invalid("Replacement must cover every proposed record")
        if original["base"] is not None:
            base = next((m for m in history if digest(m) == original["base"]), None)
            if base is None or replacement["sequence"] <= base["sequence"]:
                raise Invalid("Replacement must follow the original base")

    def resolutions(self, history):
        resolved = {}
        for path in sorted(self.path("resolutions").glob("*.json")):
            value = read_json(self.path("resolutions", path.name))
            if path.stem != digest(value):
                raise Invalid("Reconciliation record changed")
            self.validate_resolution(value, history)
            if value["operation"] in resolved:
                raise Invalid("Conflicting reconciliation records")
            resolved[value["operation"]] = value
        return resolved

    def reconcile(self, value):
        history = self.history()
        self.validate_resolution(value, history)
        resolved = self.resolutions(history)
        if value["operation"] in resolved and resolved[value["operation"]] != value:
            raise Invalid("Operation already reconciled differently")
        path = self.path("resolutions", digest(value) + ".json")
        if path.exists():
            sync_directory(path.parent)
        else:
            if not history or value["snapshot"] != digest(history[-1]):
                raise Invalid("Review the latest snapshot before reconciliation")
            exclusive(path, canonical(value))
        return {"resolution": path.stem, "evidence_class": "reported"}

    def status(self, snapshot=None):
        history = self.history()
        current = history[-1] if history else None
        selected = current
        if snapshot is not None:
            selected = next((m for m in history if digest(m) == snapshot), None)
            if selected is None:
                raise Invalid("Unknown snapshot")
        heads = selected["heads"] if selected else {}
        latest = current["heads"] if current else {}
        committed = {m["operation"] for m in history}
        resolved = self.resolutions(history)
        pending = {}
        for path in sorted(self.path("operations").glob("*.json")):
            intent = self.intent(path.stem)
            if path.stem not in committed and path.stem not in resolved:
                pending[path.stem] = intent
        changing = {r["id"] for intent in pending.values() for r in intent["records"]}
        records = {}
        for manifest in history:
            for key, rev in manifest["heads"].items():
                pair = (key, rev)
                if pair not in records:
                    records[pair] = self.read_record(key, rev)
        stale = {pair for pair in records if pair[0] in changing or latest.get(pair[0]) != pair[1]}
        # Walk exact revision dependencies, not just current record IDs or the chosen snapshot.
        while True:
            affected = {pair for pair, record in records.items()
                        if any((e["id"], e["revision"]) in stale for e in record["inputs"])}
            expanded = stale | affected
            if expanded == stale:
                break
            stale = expanded
        return {"engagement": self.config["engagement"],
                "snapshot": digest(selected) if selected else None,
                "pending": sorted(pending),
                "records": {key: {"revision": rev, "current": (key, rev) not in stale}
                            for key, rev in heads.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init").add_argument("engagement")
    commands.add_parser("prepare").add_argument("records", help="JSON array of exact record envelopes")
    commands.add_parser("commit").add_argument("operation")
    commands.add_parser("status").add_argument("--snapshot")
    commands.add_parser("baseline").add_argument("decision")
    commands.add_parser("reconcile").add_argument("review", help="JSON reconciliation review")
    commands.add_parser("coverage").add_argument("mission")
    publication_parser = commands.add_parser("publication")
    publication_parser.add_argument("packet")
    publication_parser.add_argument("review")
    export_parser = commands.add_parser("export")
    export_parser.add_argument("packet")
    export_parser.add_argument("review")
    export_parser.add_argument("--format", required=True, choices=("md", "docx", "pptx", "pdf-document", "pdf-deck"))
    export_parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = Engagement.create(args.root, args.engagement).status()
        else:
            store = Engagement(args.root)
            if args.command == "prepare":
                result = {"operation": store.prepare(read_json(Path(args.records)))}
            elif args.command == "commit":
                result = {"snapshot": store.commit(args.operation)}
            elif args.command == "baseline":
                from qualification import baseline
                result = baseline(store, args.decision)
            elif args.command == "reconcile":
                result = store.reconcile(read_json(Path(args.review)))
            elif args.command == "coverage":
                from qualification import coverage
                result = coverage(store, args.mission)
            elif args.command == "publication":
                from publication import publication
                result = publication(store, args.packet, args.review)
            elif args.command == "export":
                from publication import publication
                from export import render
                result = publication(store, args.packet, args.review)
                if not result["ready"]:
                    raise Invalid("Publication review blocked: " + "; ".join(result["gaps"]))
                result = render(result["packet"], args.format, args.output)
            else:
                result = store.status(args.snapshot)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"Engagement blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

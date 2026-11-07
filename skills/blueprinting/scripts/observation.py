"""Observe registered human inputs without editing or interpreting them."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import PurePosixPath

from engagement import Invalid, revision


def input_path(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(ord(c) < 32 for c in value)):
        raise Invalid("Input path must be a portable relative path")
    path = PurePosixPath(value)
    if (path.is_absolute() or str(path) != value or any(p in (".", "..") for p in path.parts)
            or not path.parts or path.parts[0] in {
                ".git", ".obsidian", ".blueprinting", "records", "operations", "snapshots",
                "resolutions", "engagement.json"}):
        raise Invalid("Input path must stay outside managed records and configuration")
    return value


def validate(value):
    data = value.get("data", {})
    if "input_file" in data:
        entry = data["input_file"]
        if (value["kind"] != "source" or not isinstance(entry, dict)
                or set(entry) not in ({"path", "sha256"}, {"path", "sha256", "renamed_from"})):
            raise Invalid("Source input_file needs path and sha256")
        input_path(entry["path"])
        revision(entry["sha256"])
        if "renamed_from" in entry:
            input_path(entry["renamed_from"])
    if "intake_folders" in data:
        folders = data["intake_folders"]
        if value["kind"] != "note" or not isinstance(folders, list):
            raise Invalid("Intake folders belong to an explicit settings note")
        for folder in folders:
            input_path(folder)
        if len(set(folders)) != len(folders):
            raise Invalid("Duplicate intake folder")


def file_hash(store, relative):
    path = store.path(input_path(relative))
    if not path.is_file():
        raise FileNotFoundError(relative)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise Invalid("Input changed while being read")
    return digest.hexdigest()


def transition(store, old, new):
    prior = old.get("data", {}) if old else {}
    data = new.get("data", {})
    previous = prior.get("input_file")
    current = data.get("input_file")
    if previous and not current:
        raise Invalid("Cannot remove input registration; retain missing evidence")
    if current:
        if previous and previous["path"] != current["path"] and current.get("renamed_from") != previous["path"]:
            raise Invalid("Explicit rename mapping from the previous input path required")
        if current.get("renamed_from") and (not previous or current["renamed_from"] != previous["path"]):
            # A mapping can be retained unchanged on subsequent amendments at the same path.
            if not previous or current != previous:
                raise Invalid("Rename mapping must identify the previous registered path")
        if file_hash(store, current["path"]) != current["sha256"]:
            raise Invalid("Input hash differs from supplied file; reconcile before retaining")
    if not set(prior.get("intake_folders", [])) <= set(data.get("intake_folders", [])):
        raise Invalid("Cannot remove declared intake folders")


def scan(store, records):
    started = datetime.now(timezone.utc).isoformat()
    issues, registered, folders = [], {}, set()
    for key, record in records.items():
        data = record.get("data", {})
        folders.update(data.get("intake_folders", []))
        entry = data.get("input_file")
        if not entry:
            continue
        relative = entry["path"]
        if relative in registered:
            issues.append({"record": None, "path": relative, "state": "duplicate-identity"})
        registered[relative] = key
        try:
            state = "changed" if file_hash(store, relative) != entry["sha256"] else None
        except FileNotFoundError:
            state = "missing"
        except (ValueError, OSError):
            state = "unreadable-or-unsafe"
        if state:
            issues.append({"record": key, "path": relative, "state": state})
    for relative in sorted(folders):
        try:
            directory = store.path(relative)
            if not directory.is_dir():
                raise FileNotFoundError(relative)
            def onerror(error):
                issues.append({"record": None, "path": relative, "state": "unreadable"})
            for root, dirs, files in os.walk(directory, followlinks=False, onerror=onerror):
                for name in sorted(dirs + files):
                    path = store.root / root / name
                    name_in_vault = path.relative_to(store.root).as_posix()
                    if path.is_symlink():
                        issues.append({"record": None, "path": name_in_vault, "state": "unsafe"})
                    elif name in files and name_in_vault not in registered:
                        issues.append({"record": None, "path": name_in_vault, "state": "unregistered"})
        except (ValueError, OSError):
            issues.append({"record": None, "path": relative, "state": "missing-or-unsafe-folder"})
    unique = {(i["record"], i["path"], i["state"]): i for i in issues}
    return {"started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
            "issues": sorted(unique.values(), key=lambda i: (i["path"], i["record"] or "", i["state"])),
            "limits": "Point-in-time observation of registered files and declared intake folders; no automatic ingestion or editor lock."}

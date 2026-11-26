"""Local template assets: preview, stage, activate, then consume the activated version only."""

from pathlib import Path, PurePosixPath

from engagement import Invalid, canonical, digest, exclusive, identifier, read_json, revision, sync_directory


def asset_name(name):
    if not isinstance(name, str):
        raise Invalid("Template asset path must be text")
    parts = PurePosixPath(name).parts
    extensions = {"templates": ".md", "views": ".base", "navigation": ".md"}
    if (len(parts) != 2 or parts[0] not in extensions or str(PurePosixPath(name)) != name
            or not parts[1].endswith(extensions[parts[0]])):
        raise Invalid("Template asset path outside allowlist")
    identifier(Path(parts[1]).stem)
    return name


def assets(value):
    if not isinstance(value, dict) or not value:
        raise Invalid("Nonempty template asset map required")
    for name, body in value.items():
        asset_name(name)
        if not isinstance(body, str) or not body.strip() or "\0" in body:
            raise Invalid("Template assets must be nonempty UTF-8 text")
    return value


def source_package(root, selected):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink():
        raise Invalid("Explicit absolute template repository path required")
    root = root.resolve(strict=True)
    def read(name):
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents):
            raise Invalid("Symlink in template package")
        return path.read_bytes().decode("utf-8")
    # Validate manifest path too, before parsing it.
    read("template.json")
    manifest = read_json(root / "template.json")
    if (not isinstance(manifest, dict) or set(manifest) != {"schema", "version", "requires", "files"}
            or type(manifest["schema"]) is not int or manifest["schema"] != 1
            or type(manifest["requires"]) is not int or manifest["requires"] != 1
            or type(manifest["version"]) is not int or manifest["version"] < 1
            or not isinstance(manifest["files"], list)):
        raise Invalid("Incompatible template manifest; requires helper contract 1")
    names = [asset_name(name) for name in manifest["files"]]
    if len(set(names)) != len(names):
        raise Invalid("Duplicate template asset")
    if not isinstance(selected, list) or not selected or len(set(selected)) != len(selected):
        raise Invalid("Explicit distinct template selection required")
    requested = {f"templates/{identifier(name)}.md" for name in selected}
    if not requested <= set(names):
        raise Invalid("Selected template is absent from package")
    included = {name: read(name) for name in names if not name.startswith("templates/") or name in requested}
    return {"version": manifest["version"], "requires": 1, "files": assets(included)}


def stage_record(store, key):
    value = read_json(store.path(".blueprinting", "templates", "stages", revision(key) + ".json"))
    if digest(value) != key or set(value) != {"schema", "base", "local", "source", "files", "resolutions"}:
        raise Invalid("Immutable template stage changed")
    if value["schema"] != 1 or value["source"]["requires"] != 1:
        raise Invalid("Incompatible template stage")
    assets(value["source"]["files"])
    assets(value["files"])
    return value


def history(store):
    result = []
    parent = None
    for path in sorted(store.path(".blueprinting", "templates", "activations").glob("*.json")):
        value = read_json(store.path(".blueprinting", "templates", "activations", path.name))
        if (set(value) != {"schema", "sequence", "parent", "stage"} or value["schema"] != 1
                or value["sequence"] != len(result) + 1 or value["parent"] != parent
                or path.name != f'{value["sequence"]:08d}-{digest(value)}.json'):
            raise Invalid("Broken template activation history")
        stage = stage_record(store, value["stage"])
        if stage["base"] != parent:
            raise Invalid("Template stage has a different activation base")
        result.append(value)
        parent = digest(value)
    return result


def current(store):
    chain = history(store)
    if not chain:
        return None, None, {}
    active = chain[-1]
    stage = stage_record(store, active["stage"])
    local = {}
    for name in stage["files"]:
        path = store.path("Blueprinting", active["stage"], name)
        local[name] = path.read_bytes().decode("utf-8") if path.exists() else None
    return active, stage, local


def preview(store, source):
    active, old, local = current(store)
    baseline = old["source"]["files"] if old else {}
    names = sorted(set(baseline) | set(local) | set(source["files"]))
    conflicts, merged, changes = [], {}, []
    for name in names:
        before, ours, theirs = baseline.get(name), local.get(name), source["files"].get(name)
        if ours == before or ours == theirs:
            value, action = theirs, "upstream"
        elif theirs == before:
            value, action = ours, "local"
        else:
            value, action = ours, "conflict"
            conflicts.append(name)
        if value is not None:
            merged[name] = value
        changes.append({"path": name, "action": action, "baseline": before, "local": ours, "incoming": theirs})
    plan = {"schema": 1, "base": digest(active) if active else None, "local": digest(local),
            "source": source, "files": merged, "resolutions": {}}
    return plan, {"preview": digest(plan), "conflicts": conflicts, "changes": changes,
                  "version": source["version"], "base": plan["base"]}


def stage(store, source, expected, resolutions):
    plan, report = preview(store, source)
    if expected != report["preview"]:
        raise Invalid("Template inputs changed since preview; review a new preview")
    if (not isinstance(resolutions, dict) or set(resolutions) != set(report["conflicts"])
            or any(v not in ("local", "upstream") for v in resolutions.values())):
        raise Invalid("Resolve every template conflict explicitly as local or upstream")
    for row in report["changes"]:
        name = row["path"]
        if name in resolutions:
            body = row["local"] if resolutions[name] == "local" else row["incoming"]
            if body is None:
                plan["files"].pop(name, None)
            else:
                plan["files"][name] = body
    assets(plan["files"])
    plan["resolutions"] = resolutions
    key = digest(plan)
    retain(store.path(".blueprinting", "templates", "stages", key + ".json"), canonical(plan))
    for name, body in plan["files"].items():
        retain(store.path("Blueprinting", key, name), body)
    return {"stage": key, "state": "staged-not-active", "next": "Review staged assets, then template-activate this stage"}


def retain(path, body):
    if path.exists():
        if path.read_bytes().decode("utf-8") != body:
            raise Invalid("Existing staged file differs; preserve it and reconcile")
        sync_directory(path.parent)
    else:
        exclusive(path, body)


def activate(store, key):
    plan = stage_record(store, key)
    chain = history(store)
    if chain and chain[-1]["stage"] == key:
        sync_directory(store.path(".blueprinting", "templates", "activations"))
        return status(store)
    active, _, local = current(store)
    if plan["base"] != (digest(active) if active else None) or plan["local"] != digest(local):
        raise Invalid("Active template assets changed since preview; preserve edits and preview again")
    paths = [store.path(".blueprinting", "templates", "stages", key + ".json")]
    for name, body in plan["files"].items():
        path = store.path("Blueprinting", key, name)
        if not path.is_file() or path.read_bytes().decode("utf-8") != body:
            raise Invalid("Staged assets incomplete or changed; no activation occurred")
        paths.append(path)
    # A previous stage attempt may have linked a file but failed before syncing its
    # directory. Visible bytes alone cannot justify a durable activation manifest.
    for path in paths:
        for directory in (path.parent, *path.parent.parents):
            sync_directory(directory)
    value = {"schema": 1, "sequence": len(chain) + 1, "parent": plan["base"], "stage": key}
    retain(store.path(".blueprinting", "templates", "activations", f'{value["sequence"]:08d}-{digest(value)}.json'), canonical(value))
    return status(store)


def status(store):
    active, stage, local = current(store)
    chain = history(store)
    used = {value["stage"] for value in chain}
    pending = []
    for path in sorted(store.path(".blueprinting", "templates", "stages").glob("*.json")):
        stage_record(store, path.stem)
        if path.stem not in used:
            pending.append(path.stem)
    return {"active": {"activation": digest(active), "stage": active["stage"], "version": stage["source"]["version"],
                       "paths": {name: str(store.path("Blueprinting", active["stage"], name)) for name in local},
                       "modified": [name for name in local if local[name] != stage["files"][name]]} if active else None,
            "pending": pending, "limitations": "Template state only; no business approval, integration activation or client delivery."}


def create_note(store, name, note):
    active, _, local = current(store)
    if not active:
        raise Invalid("No active template; complete staged activation first")
    body = local.get(f"templates/{identifier(name)}.md")
    if not isinstance(body, str) or not body.strip():
        raise Invalid("Template absent or locally removed; select an available active template")
    path = store.path("notes", identifier(note) + ".md")
    exclusive(path, body)
    return {"path": str(path), "activation": digest(active), "state": "unreviewed-working-note"}

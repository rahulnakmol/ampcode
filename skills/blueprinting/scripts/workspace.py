"""Explicit, local Start/Resume. Unknown policy is not permission; no external effects."""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import tempfile

from engagement import Engagement, Invalid, canonical, digest, exclusive, identifier, read_json, sync_directory
import templates


def start(root, config, source_path, confirmation):
    root = Path(root)
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise Invalid("Start requires an explicit absolute, non-symlink root")
    root = root.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise Invalid("Start requires an absent or empty root; use Resume for an existing engagement")
    if (not isinstance(config, dict) or set(config) != {"schema", "engagement", "journey", "policy", "templates"}
            or type(config["schema"]) is not int or config["schema"] != 1
            or config["journey"] not in ("opportunity", "pre-sales", "rfp", "discovery", "kickoff", "post-engagement")
            or not isinstance(config["policy"], str) or not config["policy"].strip()):
        raise Invalid("Start needs schema 1, engagement, journey, explicit policy and selected templates")
    identifier(config["engagement"])
    source = templates.source_package(source_path, config["templates"])
    intent = {"root": str(root), "config": config, "source": source}
    token = digest(intent)
    if confirmation is None:
        return {"state": "confirmation-required", "confirmation": token, **intent,
                "next": "Review root, identity, policy and template selection; repeat Start with --confirm this hash or cancel without writes"}
    if confirmation != token:
        raise Invalid("Start inputs differ from confirmation; review a new preview")
    # Publish a fully initialized vault in one directory rename. Never adopt occupied data.
    # A process killed before rename may leave an inactive sibling staging directory.
    temporary = Path(tempfile.mkdtemp(prefix=".blueprinting-start-", dir=root.parent))
    try:
        store = Engagement.create(temporary, config["engagement"])
        policy = {"schema": 1, "engagement": config["engagement"], "id": "engagement-policy", "kind": "note",
                  "previous": None, "inputs": [], "body": config["policy"]}
        store.commit(store.prepare([policy]))
        plan, report = templates.preview(store, source)
        staged = templates.stage(store, source, report["preview"], {})
        templates.activate(store, staged["stage"])
        setup = {"schema": 1, "engagement": config["engagement"], "journey": config["journey"],
                 "policy": {"id": policy["id"], "revision": digest(policy)}, "confirmation": token}
        exclusive(store.path(".blueprinting", "start", digest(setup) + ".json"), canonical(setup))
        os.rename(temporary, root)
        sync_directory(root.parent)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return resume(Engagement(root), config["engagement"])


def resume(store, expected):
    if expected != store.config["engagement"]:
        raise Invalid("Wrong engagement; select its explicit root before proceeding")
    paths = list(store.path(".blueprinting", "start").glob("*.json"))
    if len(paths) != 1:
        raise Invalid("Start metadata missing or ambiguous; legacy records remain available through status")
    path = store.path(".blueprinting", "start", paths[0].name)
    setup = read_json(path)
    if digest(setup) != path.stem or setup["engagement"] != expected:
        raise Invalid("Immutable Start metadata changed")
    state = store.status()
    policy = state["records"].get(setup["policy"]["id"])
    from obligations import scan
    from indexes import conflicts
    return {"engagement": expected, "root": str(store.root), "journey": setup["journey"],
            "policy": {"initial": setup["policy"], "current": policy}, "records": state,
            "templates": templates.status(store),
            "preserved_index_edits": conflicts(store),
            "obligations": scan(store, datetime.now(timezone.utc).isoformat(), 3600),
            "next": "Review policy, pending work, changed inputs and response gaps before using conclusions",
            "limitations": "Local vault only; configure private Git backup separately. No remote, scheduler or client permission is created."}

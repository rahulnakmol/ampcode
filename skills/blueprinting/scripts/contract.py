#!/usr/bin/env python3
"""Validate explicitly host-selected skill packages. Read-only; no installation or fallback."""

import argparse
import json
from pathlib import Path
import sys


def package_file(base, relative):
    path = base / relative
    for parent in (path, *path.parents):
        if parent == base:
            break
        if parent.is_symlink():
            raise ValueError(f"Symlink in selected package: {relative}")
    if not path.is_file() or not path.resolve().is_relative_to(base):
        raise ValueError(f"Missing selected package file: {relative}")
    return path


def selected_base(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Host-selected absolute skill base required")
    return path.resolve(strict=True)


def check(base, required, domain_base=None, domain=None):
    base = selected_base(base)
    if base != Path(__file__).resolve().parents[1]:
        raise ValueError("Selected base differs from executing package; no alternate-install fallback")
    # Validate the local import path before importing its JSON reader. A broken package can
    # otherwise execute a symlinked helper even though its compatibility check later fails.
    package_file(base, "scripts/engagement.py")
    from engagement import Invalid, read_json

    manifest = read_json(package_file(base, "contract.json"))
    fields = {"schema", "skill", "version", "contract", "helper", "domains"}
    if not isinstance(manifest, dict) or set(manifest) != fields:
        raise Invalid("Unsupported coordinator manifest")
    if (any(type(manifest[k]) is not int or manifest[k] != 1 for k in ("schema", "contract", "helper"))
            or manifest["skill"] != "blueprinting" or required != manifest["contract"]
            or type(manifest["version"]) is not int or manifest["version"] < 1
            or not isinstance(manifest["domains"], dict)
            or any(not isinstance(k, str) or type(v) is not int or v < 1
                   for k, v in manifest["domains"].items())):
        raise Invalid("Incompatible coordinator contract or helper version")
    package_file(base, "SKILL.md")
    # Fixed local files only. The manifest cannot supply executable paths or imports.
    helpers = {}
    for name in ("engagement", "qualification", "publication", "estimate", "export", "upkeep", "external",
                 "obligations", "observation", "templates", "workspace", "indexes", "audio", "handoff", "workbook", "branding"):
        helpers[name] = str(package_file(base, f"scripts/{name}.py"))
    package_file(base, "scripts/audio-model.json")
    package_file(base, "scripts/audio-requirements.txt")
    if (domain_base is None) != (domain is None):
        raise Invalid("Both host-selected domain base and domain name are required")
    version = None
    if domain is not None:
        domain_base = selected_base(domain_base)
        entry = read_json(package_file(domain_base, "contract.json"))
        if (not isinstance(entry, dict) or set(entry) != {"schema", "skill", "version", "requires"}
                or type(entry["schema"]) is not int or entry["schema"] != 1
                or entry["skill"] != domain or domain not in manifest["domains"]
                or type(entry["version"]) is not int or entry["version"] != manifest["domains"][domain]
                or type(entry["requires"]) is not int or entry["requires"] != manifest["contract"]):
            raise Invalid("Incompatible domain contract or version")
        package_file(domain_base, "SKILL.md")
        version = entry["version"]
    return {"base": str(base), "contract": manifest["contract"], "version": manifest["version"],
            "helper_version": manifest["helper"], "domain": domain, "domain_version": version,
            "domain_base": str(domain_base) if domain_base else None, "helpers": helpers,
            "limitations": "Declared compatibility only; not host authentication, permission or installed-host qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Absolute coordinator base returned by Amp")
    parser.add_argument("--requires", required=True, type=int, help="Required coordinator contract")
    parser.add_argument("--domain-base", help="Absolute domain base returned by Amp")
    parser.add_argument("--domain", help="Loaded domain name")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.base, args.requires, args.domain_base, args.domain), indent=2))
    except (ValueError, OSError, TypeError, KeyError, ImportError) as error:
        print(f"Dependency blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

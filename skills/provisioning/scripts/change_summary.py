#!/usr/bin/env python3
"""Summarize an infrastructure-as-code preview and bind the approval to its digest. Reads one
file; never calls a cloud and never applies anything.

  python3 change_summary.py summarize PREVIEW --tool TOOL [--stateful TYPE ...] [--plan-file PATH] \\
      [--drift]
  python3 change_summary.py verify PREVIEW --tool TOOL --expect DIGEST [--stateful TYPE ...] \\
      [--plan-file PATH] [--confirm-destructive ADDRESS ...] [--accept-unknown]

TOOL and the preview file it reads:
  terraform       terraform show -json <saved plan file> (OpenTofu: tofu show -json)
  infra-manager   the JSON plan that gcloud infra-manager previews export downloads
  bicep           az deployment group what-if ... --no-pretty-print (or the REST what-if result)
  cloudformation  aws cloudformation describe-change-set ... --output json

summarize prints the counts (create, update, replace, delete, no-op, and read, import, ignored
or unknown when present), every change, the destructive changes to stateful resources, the
ignored and unknown entries, the changes made outside the tool (Terraform resource_drift) and a
"Summary digest:" line, and exits 0. A Terraform import (an import block) counts as import,
or as its other action with "(import)". With --drift it exits 2 when any change exists (create,
update, replace, delete, import, unknown, or a change made outside the tool) and 0 when none; it
prints the number of resources that changed, each counted once.

verify summarizes the file again. It exits 0 only when the digest equals --expect, each
destructive change to a stateful resource is named by its own --confirm-destructive, and the
unknown entries are accepted with --accept-unknown. Otherwise it prints one line per broken rule
and exits 1.

The digest covers the tool, each change's address, type, action and content, and the destructive
list. It ignores key order, the order of the changes and the file name. A stateful type is one
in STATEFUL below or named with --stateful; verify needs the same --stateful options.

For cloudformation, the digest also covers the change set's ChangeSetId (its ARN) and its
Parameters, so a change set deleted and made again under the same name needs a new approval.
Describe it with --include-property-values, so the changes carry their before and after values.

--plan-file (terraform only) adds the SHA-256 of the saved plan file that terraform apply will run
to the summary and the digest, so verify refuses another plan file, and names its new SHA-256.
Pass the file that terraform show -json read; a file that is not a zip (PK) is refused. Without
--plan-file, a Terraform summary says "Plan file: not bound", its Next line asks for the plan
file, and verify --tool terraform refuses it: do not apply from it.

An unknown tool, an unreadable or malformed file, or a bad option prints one line and exits 1.
Standard library only.
"""

import argparse
import hashlib
import json
import re
import shlex
import sys

TOOLS = ("terraform", "infra-manager", "bicep", "cloudformation")
MAIN = ("create", "update", "replace", "delete", "no-op")
EXTRA = ("read", "import", "ignored", "unknown")
NOT_A_CHANGE = {"no-op", "read", "ignored"}
DESTROYS = {"replace", "delete"}

TERRAFORM_ACTIONS = {
    ("no-op",): "no-op", ("create",): "create", ("read",): "read", ("update",): "update",
    ("delete", "create"): "replace", ("create", "delete"): "replace", ("delete",): "delete",
}
BICEP_CHANGES = {
    "Create": "create", "Modify": "update", "Deploy": "update", "Delete": "delete",
    "NoChange": "no-op", "Ignore": "ignored", "Unsupported": "unknown",
}
CFN_REPLACEMENT = {"False": "update", "True": "replace", "Conditional": "replace"}
CFN_NO_CHANGES = ("didn't contain changes", "No updates are to be performed")

# Types that hold data. A delete or replace of one is destructive. Keep this list and
# ../reference/environments.md in step; a test compares them.
STATEFUL = frozenset({
    # Terraform: Azure
    "azurerm_storage_account", "azurerm_mssql_server", "azurerm_mssql_database",
    "azurerm_postgresql_flexible_server", "azurerm_mysql_flexible_server", "azurerm_cosmosdb_account",
    "azurerm_key_vault", "azurerm_managed_disk", "azurerm_redis_cache", "azurerm_recovery_services_vault",
    # Terraform: AWS
    "aws_db_instance", "aws_rds_cluster", "aws_dynamodb_table", "aws_s3_bucket", "aws_efs_file_system",
    "aws_ebs_volume", "aws_kms_key", "aws_elasticache_replication_group", "aws_opensearch_domain",
    "aws_backup_vault",
    # Terraform: Google Cloud (also Infrastructure Manager)
    "google_sql_database_instance", "google_sql_database", "google_storage_bucket",
    "google_bigquery_dataset", "google_bigquery_table", "google_spanner_database",
    "google_firestore_database", "google_compute_disk", "google_filestore_instance",
    "google_kms_crypto_key",
    # Bicep and ARM (matched without case)
    "Microsoft.Storage/storageAccounts", "Microsoft.Sql/servers", "Microsoft.Sql/servers/databases",
    "Microsoft.DBforPostgreSQL/flexibleServers", "Microsoft.DBforMySQL/flexibleServers",
    "Microsoft.DocumentDB/databaseAccounts", "Microsoft.KeyVault/vaults", "Microsoft.Compute/disks",
    "Microsoft.Cache/redis", "Microsoft.RecoveryServices/vaults",
    # CloudFormation
    "AWS::RDS::DBInstance", "AWS::RDS::DBCluster", "AWS::DynamoDB::Table", "AWS::S3::Bucket",
    "AWS::EFS::FileSystem", "AWS::EC2::Volume", "AWS::KMS::Key", "AWS::ElastiCache::ReplicationGroup",
    "AWS::OpenSearchService::Domain", "AWS::Backup::BackupVault",
})
HEX64 = re.compile(r"[0-9a-f]{64}")
ZIP_MAGIC = b"PK\x03\x04"  # a saved Terraform plan file is a zip archive


class Refused(Exception):
    """One clear error: the input or the options cannot be summarized."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused(message)


def need(condition, message):
    if not condition:
        raise Refused(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def entry(address, kind, action, raw, note=""):
    return {"address": address, "type": kind, "action": action, "note": note, "content": fingerprint(raw)}


def terraform_list(data, key):
    items = data.get(key)
    if items is None:
        return []
    need(isinstance(items, list), f"{key} must be a list")
    out = []
    for index, raw in enumerate(items):
        where = f"{key}[{index}]"
        need(isinstance(raw, dict), f"{where} must be an object")
        address, kind, change = raw.get("address"), raw.get("type"), raw.get("change")
        need(isinstance(address, str) and address, f"{where} has no address")
        need(isinstance(kind, str), f"{where} has no type")
        need(isinstance(change, dict), f"{where} has no change object")
        actions = change.get("actions")
        need(isinstance(actions, list) and all(isinstance(a, str) for a in actions),
             f"{where}.change.actions must be a list of strings")
        action = TERRAFORM_ACTIONS.get(tuple(actions), "unknown")
        note = "" if action != "unknown" else f": actions {actions} are not a known Terraform plan action"
        if change.get("importing"):  # an import block: Terraform writes the object into state
            if action == "no-op":
                action = "import"
            else:
                note += " (import)"
        out.append(entry(address, kind, action, raw, note))
    return out


def read_terraform(data):
    need(isinstance(data, dict) and "format_version" in data,
         "not a Terraform plan JSON (no format_version): use terraform show -json <saved plan file>")
    need(data.get("errored") is not True, "the plan errored and cannot be applied: fix it and plan again")
    return terraform_list(data, "resource_changes"), terraform_list(data, "resource_drift")


def arm_type(resource_id):
    """Microsoft.Sql/servers/s1/databases/db1 -> Microsoft.Sql/servers/databases."""
    _, found, tail = resource_id.rpartition("/providers/")
    parts = [p for p in tail.split("/") if p] if found else []
    if len(parts) < 3:
        return ""
    return "/".join([parts[0], *parts[1::2]])


def read_bicep(data):
    need(isinstance(data, dict), "not a what-if result: the top level must be an object")
    status, error = data.get("status"), data.get("error")
    need(error in (None, {}) and status in (None, "Succeeded"),
         f"the what-if did not succeed (status {status!r}, error {json.dumps(error)}): fix it and run what-if again")
    holder = data.get("properties") if isinstance(data.get("properties"), dict) else data
    changes, potential = holder.get("changes"), holder.get("potentialChanges") or []
    need(isinstance(changes, list), "not a what-if result: no changes list (use what-if --no-pretty-print)")
    need(isinstance(potential, list), "potentialChanges must be a list")
    out = []
    for key, items in (("changes", changes), ("potentialChanges", potential)):
        for index, raw in enumerate(items):
            where = f"{key}[{index}]"
            need(isinstance(raw, dict), f"{where} must be an object")
            address = raw.get("resourceId") or raw.get("symbolicName")
            change_type = raw.get("changeType")
            need(isinstance(address, str) and address, f"{where} has no resourceId")
            need(isinstance(change_type, str), f"{where} has no changeType")
            snapshot = raw.get("after") or raw.get("before") or {}
            kind = snapshot.get("type") if isinstance(snapshot, dict) else None
            kind = kind if isinstance(kind, str) and kind else arm_type(address)
            action = BICEP_CHANGES.get(change_type, "unknown") if key == "changes" else "unknown"
            note = ""
            if key == "potentialChanges":
                note = f": potential change ({change_type}); what-if could not decide"
            elif action == "unknown":
                reason = raw.get("unsupportedReason")
                note = f": {change_type}" + (f": {reason}" if isinstance(reason, str) and reason else "")
            out.append(entry(address, kind, action, raw, note))
    return out, []


def read_cloudformation(data):
    need(isinstance(data, dict) and "Changes" in data,
         "not a change set description (no Changes): use aws cloudformation describe-change-set --output json")
    changes = data["Changes"]
    need(isinstance(changes, list), "Changes must be a list")
    need(not data.get("NextToken"), "the change set has more pages (NextToken): join every page's Changes first")
    arn = data.get("ChangeSetId")
    need(isinstance(arn, str) and arn.startswith("arn:"),
         "no ChangeSetId ARN: the approval binds the change set that runs; describe it with "
         "aws cloudformation describe-change-set --include-property-values --output json")
    need(isinstance(data.get("Parameters", []), list), "Parameters must be a list")
    status = data.get("Status")
    if status == "FAILED":
        reason = str(data.get("StatusReason", ""))
        need(any(text in reason for text in CFN_NO_CHANGES) and not changes,
             f"the change set FAILED: {' '.join(reason.split())}")
    else:
        need(status in (None, "CREATE_COMPLETE"),
             f"the change set status is {status}: wait for CREATE_COMPLETE "
             "(aws cloudformation wait change-set-create-complete)")
    out = []
    for index, raw in enumerate(changes):
        where = f"Changes[{index}]"
        need(isinstance(raw, dict) and isinstance(raw.get("ResourceChange"), dict),
             f"{where} has no ResourceChange object")
        change = raw["ResourceChange"]
        action, address, kind = change.get("Action"), change.get("LogicalResourceId"), change.get("ResourceType")
        need(isinstance(action, str), f"{where}.ResourceChange.Action must be a string")
        need(isinstance(address, str) and address, f"{where} has no LogicalResourceId")
        need(isinstance(kind, str), f"{where} has no ResourceType")
        if action == "Modify":
            mapped = CFN_REPLACEMENT.get(change.get("Replacement"), "unknown")
        else:
            mapped = {"Add": "create", "Remove": "delete", "Import": "import"}.get(action, "unknown")
        note = ""
        if change.get("ChangeSetId"):
            mapped, note = "unknown", ": nested change set; summarize it separately"
        elif mapped == "unknown":
            note = f": Action {action}, Replacement {change.get('Replacement')}"
        if change.get("PolicyAction"):
            note += f" [policy action: {change['PolicyAction']}]"
        out.append(entry(address, kind, mapped, raw, note))
    return out, []


HINTS = {
    "terraform": "pass the output of terraform show -json <plan file>, not the binary plan file",
    "infra-manager": "pass the JSON plan from gcloud infra-manager previews export",
    "bicep": "pass the output of what-if --no-pretty-print --output json",
    "cloudformation": "pass the output of describe-change-set --output json",
}
READERS = {"terraform": read_terraform, "infra-manager": read_terraform,
           "bicep": read_bicep, "cloudformation": read_cloudformation}


def summarize(path, tool, extra_stateful, plan_file=None):
    need(tool in TOOLS, f"unknown tool {tool!r}: use one of {', '.join(TOOLS)}")
    need(plan_file is None or tool == "terraform",
         "--plan-file applies to --tool terraform only: the saved plan file that terraform apply runs")
    plan_sha256 = None
    if plan_file is not None:
        try:
            with open(plan_file, "rb") as handle:
                content = handle.read()
        except OSError as error:
            raise Refused(f"{plan_file}: cannot read the plan file: {error.strerror or error}")
        need(content.startswith(ZIP_MAGIC),
             f"{plan_file}: not a saved Terraform plan (a saved plan is a zip file that starts with PK); "
             "pass the file that terraform plan -out wrote, not its JSON")
        plan_sha256 = hashlib.sha256(content).hexdigest()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        raise Refused(f"{path}: cannot read: {error.strerror or error}")
    except (ValueError, RecursionError) as error:
        raise Refused(f"{path}: not JSON ({HINTS[tool]}): {' '.join(str(error).split())}")
    try:
        changes, outside = READERS[tool](data)
    except Refused as refused:
        raise Refused(f"{path}: {refused}")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise Refused(f"{path}: not a {tool} preview: {type(error).__name__} {error}")
    outside = [e for e in outside if e["action"] not in NOT_A_CHANGE]
    stateful = {t.lower() for t in STATEFUL | set(extra_stateful)}
    destructive = [e for e in changes if e["action"] in DESTROYS and e["type"].lower() in stateful]
    payload = {
        "tool": tool,
        "changes": sorted([e["address"], e["type"], e["action"], e["content"]] for e in changes),
        "outside": sorted([e["address"], e["type"], e["action"], e["content"]] for e in outside),
        "destructive": sorted(e["address"] for e in destructive),
    }
    if plan_sha256:
        payload["plan_file_sha256"] = plan_sha256
    change_set = None
    if tool == "cloudformation":  # bind the change set that runs: its ARN and its parameters
        change_set = data["ChangeSetId"]
        payload["change_set_id"] = change_set
        payload["parameters"] = sorted(fingerprint(item) for item in data.get("Parameters") or [])
    return {"tool": tool, "changes": changes, "outside": outside, "destructive": destructive,
            "plan_sha256": plan_sha256, "change_set": change_set, "digest": fingerprint(payload)}


def order(items):
    rank = {name: i for i, name in enumerate(MAIN + EXTRA)}
    return sorted(items, key=lambda e: (rank.get(e["action"], len(rank)), e["address"]))


def lines_for(heading, items, empty="none"):
    if not items:
        return [f"{heading}: {empty}"]
    return [f"{heading}:"] + [f"- {e['action']} {e['address']} ({e['type']}){e['note']}" for e in order(items)]


def render(summary, args):
    changes = summary["changes"]
    tally = {name: sum(e["action"] == name for e in changes) for name in MAIN + EXTRA}
    shown = [f"{name} {tally[name]}" for name in MAIN] + [f"{name} {tally[name]}" for name in EXTRA if tally[name]]
    out = [f"Tool: {summary['tool']}"]
    if summary["change_set"]:
        out.append(f"Change set: {summary['change_set']}")
    out.append("Counts: " + ", ".join(shown))
    out += lines_for("Changes", [e for e in changes if e["action"] not in NOT_A_CHANGE | {"unknown"}])
    out += lines_for("Destructive changes to stateful resources (each needs its own explicit confirmation)",
                     summary["destructive"])
    out += lines_for("Ignored (listed, not changed)", [e for e in changes if e["action"] == "ignored"])
    out += lines_for("Unknown (listed; verify refuses until --accept-unknown)",
                     [e for e in changes if e["action"] == "unknown"])
    if summary["tool"] in ("terraform", "infra-manager"):
        out += lines_for("Changed outside the tool (resource_drift)", summary["outside"])
    if summary["plan_sha256"]:
        out.append(f"Plan file SHA-256: {summary['plan_sha256']} ({args.plan_file})")
    elif summary["tool"] == "terraform":
        out.append("Plan file: not bound (summarize again with --plan-file <plans>/tfplan before any apply)")
    out.append(f"Summary digest: {summary['digest']}")
    options = " ".join(f"--stateful {shlex.quote(t)}" for t in args.stateful)
    if args.plan_file:
        options += f" --plan-file {shlex.quote(args.plan_file)}"
    if unbound(summary):
        out.append("Next: get the saved plan file and summarize again with --plan-file <plans>/tfplan; "
                   "this summary cannot be verified or applied")
    else:
        out.append(f"Next: get this summary digest approved, then run: python3 <skill>/scripts/change_summary.py "
                   f"verify {shlex.quote(args.preview)} --tool {summary['tool']} {options} "
                   f"--expect {summary['digest']}".replace("  ", " "))
    if summary["destructive"]:
        out.append("Add --confirm-destructive <address> for a destructive change only after the owner "
                   "confirms that change by name.")
    return "\n".join(out)


def drift_count(summary):
    """Resources with a change or a change made outside the tool, each counted once."""
    changed = {e["address"] for e in summary["changes"] if e["action"] not in NOT_A_CHANGE}
    return len(changed | {e["address"] for e in summary["outside"]})


def unbound(summary):
    """A Terraform summary without --plan-file: nothing ties it to the plan file that apply runs."""
    return summary["tool"] == "terraform" and not summary["plan_sha256"]


def verify(summary, args):
    if unbound(summary):
        return ["plan file not bound: get the saved plan file, then summarize and verify with "
                "--plan-file <plans>/tfplan; get that summary digest approved"]
    broken = []
    given = args.expect.strip().lower().removeprefix("sha256:")
    if not HEX64.fullmatch(given):
        broken.append(f"--expect {args.expect!r} is not a full 64-character summary digest; "
                      "a shortened digest is not an approval")
    elif given != summary["digest"]:
        line = (f"summary digest {summary['digest'][:12]}… does not match the approved "
                f"{given[:12]}…: summarize again and get the new digest approved")
        if summary["plan_sha256"]:
            line += (f"; the plan file SHA-256 is now {summary['plan_sha256']}: compare it with the "
                     "approved one (a new plan file means a new plan)")
        broken.append(line)
    destructive = {e["address"]: e for e in summary["destructive"]}
    confirmed = set(args.confirm_destructive)
    for address in sorted(set(destructive) - confirmed):
        e = destructive[address]
        broken.append(f"destructive change to a stateful resource is not confirmed: {e['action']} {address} "
                      f"({e['type']}); pass --confirm-destructive {shlex.quote(address)} only after its own "
                      "explicit confirmation")
    for address in sorted(confirmed - set(destructive)):
        broken.append(f"--confirm-destructive {address} names no destructive change in this summary")
    unknown = [e for e in summary["changes"] if e["action"] == "unknown"]
    if unknown and not args.accept_unknown:
        names = ", ".join(e["address"] for e in order(unknown))
        broken.append(f"{len(unknown)} unknown entr{'y' if len(unknown) == 1 else 'ies'} ({names}): "
                      "pass --accept-unknown only after the owner accepts them")
    return broken


def main(argv=None):
    parser = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    shared = Parser(add_help=False)
    shared.add_argument("preview", help="the preview file (JSON)")
    shared.add_argument("--tool", required=True, help="one of: " + ", ".join(TOOLS))
    shared.add_argument("--stateful", action="append", default=[], metavar="TYPE",
                        help="another stateful resource type; repeat")
    shared.add_argument("--plan-file", metavar="PATH",
                        help="terraform only: the saved plan file to apply; its SHA-256 joins the digest")
    show = commands.add_parser("summarize", parents=[shared], help="print the summary and its digest")
    show.add_argument("--drift", action="store_true", help="exit 2 when any change exists, 0 when none")
    check = commands.add_parser("verify", parents=[shared], help="check the summary against an approved digest")
    check.add_argument("--expect", required=True, metavar="DIGEST", help="the approved summary digest")
    check.add_argument("--confirm-destructive", action="append", default=[], metavar="ADDRESS",
                       help="a destructive change the owner confirmed by name; repeat")
    check.add_argument("--accept-unknown", action="store_true", help="the owner accepted the unknown entries")
    try:
        args = parser.parse_args(argv)
        summary = summarize(args.preview, args.tool, args.stateful, args.plan_file)
    except Refused as refused:
        print(f"error: {refused}")
        return 1
    if args.command == "summarize":
        print(render(summary, args))
        if args.drift:
            count = drift_count(summary)
            print(f"Drift: {count} resource{'s' if count != 1 else ''}" if count else "Drift: none")
            return 2 if count else 0
        return 0
    broken = verify(summary, args)
    if broken:
        print("\n".join(broken))
        return 1
    print(f"pass: the summary matches digest {summary['digest']}")
    print("- apply only the plan this summary came from, and only when the mission contract pre-authorizes "
          "this effect for this environment or the owner approved this summary digest")
    return 0


if __name__ == "__main__":
    sys.exit(main())

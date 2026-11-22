"""Tests for skills/provisioning: the change summary script (W10.1 to W10.9) and the skill text
(W11.1 to W11.5, X1, X7).

Run: python3 -m unittest tests.test_provisioning -v

Expected counts, mappings and destructive lists are written by hand from the fixtures in
tests/fixtures/provisioning (see its README), not taken from the script.
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "provisioning"
SCRIPT = SKILL / "scripts" / "change_summary.py"
REFERENCE = SKILL / "reference"
FIXTURES = ROOT / "tests" / "fixtures" / "provisioning"
TF_PLAN = FIXTURES / "terraform-local-plan.json"
TF_SAME = FIXTURES / "terraform-local-no-changes.json"
TF_STATEFUL = FIXTURES / "terraform-stateful-sample.json"
BICEP = FIXTURES / "bicep-whatif-sample.json"
CFN = FIXTURES / "cloudformation-changeset-sample.json"
sys.path.insert(0, str(ROOT / "tests"))

from test_skill_anatomy import problems as anatomy  # noqa: E402

DIGEST = re.compile(r"^Summary digest: ([0-9a-f]{64})$", re.M)
# A stand-in saved Terraform plan: a zip header is all the script checks. verify --tool terraform
# needs --plan-file (eval round 1, F2), so Terraform verify tests bind this file.
_PLANS = tempfile.TemporaryDirectory()
SAVED_PLAN = Path(_PLANS.name) / "tfplan"
SAVED_PLAN.write_bytes(b"PK\x03\x04stand-in saved plan")
BOUND = ("--plan-file", SAVED_PLAN)


def run(*args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def counts(out):
    line = next(l for l in out.splitlines() if l.startswith("Counts: "))
    return {name: int(n) for n, name in
            (part.rsplit(" ", 1)[::-1] for part in line[len("Counts: "):].split(", "))}


def listed(out, heading):
    """Return [(action, address, type)] under the line that starts with heading."""
    lines = out.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None or lines[start].endswith(": none"):
        return []
    rows = []
    for line in lines[start + 1:]:
        match = re.match(r"^- (\S+) (.+?) \(([^()]*)\)", line)
        if not match:
            break
        rows.append(match.groups())
    return rows


def digest_of(out):
    match = DIGEST.search(out)
    if not match:
        raise AssertionError(f"no 'Summary digest:' line in:\n{out}")
    return match.group(1)


def write(folder, name, data):
    path = Path(folder) / name
    path.write_text(json.dumps(data))
    return path


def reorder(value, top=True):
    """Reverse the key order of every object, and the order of the top-level change list.

    Lists inside a resource keep their order: there, order can carry meaning."""
    if isinstance(value, dict):
        out = {key: reorder(value[key], False) for key in reversed(list(value))}
        for key in ("resource_changes", "changes", "Changes") if top else ():
            if isinstance(out.get(key), list):
                out[key] = out[key][::-1]
        if top and isinstance(out.get("properties"), dict):
            out["properties"]["changes"] = out["properties"]["changes"][::-1]
        return out
    if isinstance(value, list):
        return [reorder(v, False) for v in value]
    return value


DESTRUCTIVE = "Destructive changes to stateful resources"


class Terraform(unittest.TestCase):
    def test_w10_1_counts_equal_hand_counts(self):
        code, out = run("summarize", TF_PLAN, "--tool", "terraform")
        self.assertEqual(code, 0, out)
        # By hand from the fixture README: 2 creates, 1 update, 2 replacements, 1 delete, 2 no-ops.
        self.assertEqual(counts(out), {"create": 2, "update": 1, "replace": 2, "delete": 1, "no-op": 2})

    def test_w10_1_stateful_sample_counts(self):
        code, out = run("summarize", TF_STATEFUL, "--tool", "terraform")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out), {"create": 1, "update": 1, "replace": 2, "delete": 3, "no-op": 1,
                                       "read": 1})

    def test_w10_2_delete_then_create_is_one_replace(self):
        code, out = run("summarize", TF_PLAN, "--tool", "terraform")
        rows = {address: action for action, address, _ in listed(out, "Changes:")}
        # local_file.report is ["delete", "create"]; random_pet.name is ["create", "delete"].
        self.assertEqual(rows["local_file.report"], "replace")
        self.assertEqual(rows["random_pet.name"], "replace")
        self.assertEqual(sorted(rows), ["local_file.notes", "local_file.report", "random_pet.name",
                                        "terraform_data.new", "terraform_data.old",
                                        "terraform_data.settings"])
        with tempfile.TemporaryDirectory() as tmp:
            one = {"format_version": "1.2", "resource_changes": [
                {"address": "x.a", "type": "x", "change": {"actions": ["delete", "create"]}}]}
            code, out = run("summarize", write(tmp, "one.json", one), "--tool", "terraform")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out), {"create": 0, "update": 0, "replace": 1, "delete": 0, "no-op": 0})

    def test_w10_3_destructive_stateful_changes_listed(self):
        code, out = run("summarize", TF_STATEFUL, "--tool", "terraform")
        self.assertEqual(code, 0, out)
        # Replace or delete of a listed stateful type; not the create, the update, the security group.
        self.assertEqual(sorted((a, addr) for a, addr, _ in listed(out, DESTRUCTIVE)), [
            ("delete", "aws_db_instance.orders"),
            ("delete", "google_storage_bucket.exports"),
            ("replace", "azurerm_mssql_database.orders"),
            ("replace", "google_sql_database_instance.main"),
        ])

    def test_w10_3_extra_stateful_type(self):
        code, out = run("summarize", TF_PLAN, "--tool", "terraform")
        line = next(l for l in out.splitlines() if l.startswith(DESTRUCTIVE))
        self.assertTrue(line.endswith(": none"), line)
        code, out = run("summarize", TF_PLAN, "--tool", "terraform", "--stateful", "local_file")
        # local_file.report is replaced; local_file.notes is only created.
        self.assertEqual(listed(out, DESTRUCTIVE), [("replace", "local_file.report", "local_file")])

    def test_resource_drift_is_listed(self):
        code, out = run("summarize", TF_STATEFUL, "--tool", "terraform")
        self.assertEqual(listed(out, "Changed outside the tool"),
                         [("update", "azurerm_storage_account.logs", "azurerm_storage_account")])

    def test_unknown_terraform_action_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = {"format_version": "1.2", "resource_changes": [
                {"address": "x.gone", "type": "x", "change": {"actions": ["forget"]}}]}
            path = write(tmp, "forget.json", plan)
            code, out = run("summarize", path, "--tool", "terraform", *BOUND)
            self.assertEqual(listed(out, "Unknown"), [("unknown", "x.gone", "x")])
            code, out = run("verify", path, "--tool", "terraform", *BOUND, "--expect", digest_of(out))
        self.assertEqual(code, 1, out)
        self.assertIn("--accept-unknown", out)

    def test_infra_manager_reads_the_terraform_plan(self):
        code, out = run("summarize", TF_STATEFUL, "--tool", "infra-manager")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out)["replace"], 2)


class Bicep(unittest.TestCase):
    def test_w10_4_change_types_map(self):
        code, out = run("summarize", BICEP, "--tool", "bicep")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out), {"create": 1, "update": 2, "replace": 0, "delete": 2, "no-op": 1,
                                       "ignored": 1, "unknown": 1})
        base = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-orders-prod/providers/"
        rows = {addr[len(base):]: (action, kind) for action, addr, kind in listed(out, "Changes:")}
        self.assertEqual(rows, {
            "Microsoft.Storage/storageAccounts/stordersexport": ("create", "Microsoft.Storage/storageAccounts"),
            "Microsoft.Sql/servers/sql-orders-prod/databases/orders": ("update", "Microsoft.Sql/servers/databases"),
            "Microsoft.Web/sites/app-orders-prod": ("update", "Microsoft.Web/sites"),
            "Microsoft.DocumentDB/databaseAccounts/cosmos-orders-legacy":
                ("delete", "Microsoft.DocumentDB/databaseAccounts"),
            "Microsoft.Network/publicIPAddresses/pip-orders-legacy":
                ("delete", "Microsoft.Network/publicIPAddresses"),
        })
        self.assertEqual([(a, addr[len(base):]) for a, addr, _ in listed(out, "Ignored")],
                         [("ignored", "Microsoft.Compute/disks/disk-orders-scratch")])
        self.assertEqual([(a, addr[len(base):]) for a, addr, _ in listed(out, "Unknown")],
                         [("unknown", "Microsoft.Web/sites/app-orders-prod/config/appsettings")])
        self.assertIn("cannot be calculated until the deployment is under way", out)
        self.assertEqual([(a, addr[len(base):]) for a, addr, _ in listed(out, DESTRUCTIVE)],
                         [("delete", "Microsoft.DocumentDB/databaseAccounts/cosmos-orders-legacy")])

    def test_w10_4_unsupported_needs_accept_unknown(self):
        cosmos = ("/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-orders-prod/"
                  "providers/Microsoft.DocumentDB/databaseAccounts/cosmos-orders-legacy")
        digest = digest_of(run("summarize", BICEP, "--tool", "bicep")[1])
        code, out = run("verify", BICEP, "--tool", "bicep", "--expect", digest, "--confirm-destructive", cosmos)
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("--accept-unknown", out)
        code, out = run("verify", BICEP, "--tool", "bicep", "--expect", digest, "--confirm-destructive", cosmos,
                        "--accept-unknown")
        self.assertEqual(code, 0, out)

    def test_cli_shape_with_top_level_changes(self):
        data = json.loads(BICEP.read_text())
        flat = {"status": "Succeeded", "changes": data["properties"]["changes"], "error": None}
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "flat.json", flat), "--tool", "bicep")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out)["delete"], 2)

    def test_arm_types_match_without_case(self):
        data = json.loads(BICEP.read_text())
        change = data["properties"]["changes"][3]
        change["resourceId"] = change["resourceId"].replace("Microsoft.DocumentDB/databaseAccounts",
                                                            "microsoft.documentdb/DATABASEACCOUNTS")
        del change["before"]
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "case.json", data), "--tool", "bicep")
        self.assertEqual(len(listed(out, DESTRUCTIVE)), 1, out)


class CloudFormation(unittest.TestCase):
    def test_w10_5_actions_map(self):
        code, out = run("summarize", CFN, "--tool", "cloudformation")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out), {"create": 1, "update": 1, "replace": 2, "delete": 2, "no-op": 0})
        self.assertEqual({addr: action for action, addr, _ in listed(out, "Changes:")}, {
            "ReportsBucket": "create",       # Add
            "OrdersFunction": "update",      # Modify, Replacement False
            "OrdersDatabase": "replace",     # Modify, Replacement True
            "SessionsTable": "replace",      # Modify, Replacement Conditional
            "LegacyTopic": "delete",         # Remove
            "ArchiveBucket": "delete",       # Remove
        })
        self.assertEqual(sorted(addr for _, addr, _ in listed(out, DESTRUCTIVE)),
                         ["ArchiveBucket", "OrdersDatabase", "SessionsTable"])
        self.assertIn("Retain", next(l for l in out.splitlines() if "ArchiveBucket" in l))

    def test_modify_without_replacement_is_unknown(self):
        data = json.loads(CFN.read_text())
        del data["Changes"][1]["ResourceChange"]["Replacement"]
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "nr.json", data), "--tool", "cloudformation")
        self.assertEqual([addr for _, addr, _ in listed(out, "Unknown")], ["OrdersFunction"])

    def test_empty_change_set_has_no_changes(self):
        data = {"Changes": [], "Status": "FAILED", "StackName": "s",
                "ChangeSetId": "arn:aws:cloudformation:us-east-1:123456789012:changeSet/c/00000000-0000-0000-0000-000000000005",
                "StatusReason": "The submitted information didn't contain changes. "
                                "Submit different information to create a change set."}
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "empty.json", data), "--tool", "cloudformation", "--drift")
        self.assertEqual(code, 0, out)


class Digest(unittest.TestCase):
    def test_w10_6_key_and_list_order_do_not_change_the_digest(self):
        for tool, path in (("terraform", TF_PLAN), ("bicep", BICEP), ("cloudformation", CFN)):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as tmp:
                shuffled = write(tmp, "shuffled.json", reorder(json.loads(path.read_text())))
                self.assertNotEqual(shuffled.read_text(), json.dumps(json.loads(path.read_text())))
                self.assertEqual(digest_of(run("summarize", path, "--tool", tool)[1]),
                                 digest_of(run("summarize", shuffled, "--tool", tool)[1]))

    def test_w10_6_any_action_change_changes_the_digest(self):
        plan = json.loads(TF_PLAN.read_text())
        base = digest_of(run("summarize", TF_PLAN, "--tool", "terraform")[1])
        seen = {base}
        for index, change in enumerate(plan["resource_changes"]):
            edited = json.loads(json.dumps(plan))
            old = change["change"]["actions"]
            edited["resource_changes"][index]["change"]["actions"] = ["delete"] if old != ["delete"] else ["update"]
            with tempfile.TemporaryDirectory() as tmp:
                digest = digest_of(run("summarize", write(tmp, "e.json", edited), "--tool", "terraform")[1])
            self.assertNotIn(digest, seen, change["address"])
            seen.add(digest)

    def test_w10_6_a_changed_value_changes_the_digest(self):
        plan = json.loads(TF_PLAN.read_text())
        settings = next(c for c in plan["resource_changes"] if c["address"] == "terraform_data.settings")
        settings["change"]["after"]["input"] = "v3"
        with tempfile.TemporaryDirectory() as tmp:
            edited = digest_of(run("summarize", write(tmp, "v3.json", plan), "--tool", "terraform")[1])
        self.assertNotEqual(edited, digest_of(run("summarize", TF_PLAN, "--tool", "terraform")[1]))

    def test_w10_7_verify_passes_the_same_and_refuses_a_different_summary(self):
        digest = digest_of(run("summarize", TF_PLAN, "--tool", "terraform", *BOUND)[1])
        code, out = run("verify", TF_PLAN, "--tool", "terraform", *BOUND, "--expect", digest)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("pass"), out)
        code, out = run("verify", TF_PLAN, "--tool", "terraform", *BOUND, "--expect", "sha256:" + digest.upper())
        self.assertEqual(code, 0, out)
        code, out = run("verify", TF_SAME, "--tool", "terraform", *BOUND, "--expect", digest)
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("does not match", out)
        code, out = run("verify", TF_PLAN, "--tool", "terraform", *BOUND, "--expect", digest[:12])
        self.assertEqual(code, 1, out)

    def test_w10_7_verify_uses_the_same_stateful_list(self):
        digest = digest_of(run("summarize", TF_PLAN, "--tool", "terraform", *BOUND, "--stateful", "local_file")[1])
        code, out = run("verify", TF_PLAN, "--tool", "terraform", *BOUND, "--expect", digest)
        self.assertEqual(code, 1, out)
        self.assertIn("does not match", out)


class DestructiveConfirmation(unittest.TestCase):
    def test_w11_2_verify_needs_each_destructive_change_confirmed(self):
        digest = digest_of(run("summarize", CFN, "--tool", "cloudformation")[1])
        code, out = run("verify", CFN, "--tool", "cloudformation", "--expect", digest)
        self.assertEqual(code, 1, out)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 3, out)
        for name in ("ArchiveBucket", "OrdersDatabase", "SessionsTable"):
            self.assertTrue(any(name in line and "--confirm-destructive" in line for line in lines), out)
        code, out = run("verify", CFN, "--tool", "cloudformation", "--expect", digest,
                        "--confirm-destructive", "OrdersDatabase", "--confirm-destructive", "SessionsTable")
        self.assertEqual(code, 1, out)
        self.assertIn("ArchiveBucket", out)
        code, out = run("verify", CFN, "--tool", "cloudformation", "--expect", digest,
                        "--confirm-destructive", "OrdersDatabase", "--confirm-destructive", "SessionsTable",
                        "--confirm-destructive", "ArchiveBucket")
        self.assertEqual(code, 0, out)

    def test_w11_2_a_confirmation_must_name_a_destructive_change(self):
        digest = digest_of(run("summarize", TF_PLAN, "--tool", "terraform", *BOUND)[1])
        code, out = run("verify", TF_PLAN, "--tool", "terraform", *BOUND, "--expect", digest,
                        "--confirm-destructive", "terraform_data.old")
        self.assertEqual(code, 1, out)
        self.assertIn("--confirm-destructive terraform_data.old names no destructive change", out)


class Drift(unittest.TestCase):
    def test_w10_8_drift_exits_2_on_any_change_and_0_on_none(self):
        self.assertEqual(run("summarize", TF_PLAN, "--tool", "terraform", "--drift")[0], 2)
        code, out = run("summarize", TF_SAME, "--tool", "terraform", "--drift")
        self.assertEqual(code, 0, out)
        self.assertEqual(counts(out), {"create": 0, "update": 0, "replace": 0, "delete": 0, "no-op": 6})
        self.assertEqual(run("summarize", BICEP, "--tool", "bicep", "--drift")[0], 2)
        self.assertEqual(run("summarize", CFN, "--tool", "cloudformation", "--drift")[0], 2)

    def test_w10_8_each_kind_of_change_is_drift(self):
        for actions in (["create"], ["update"], ["delete"], ["delete", "create"], ["forget"]):
            plan = {"format_version": "1.2", "resource_changes": [
                {"address": "x.a", "type": "x", "change": {"actions": actions}}]}
            with self.subTest(actions=actions), tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(run("summarize", write(tmp, "p.json", plan), "--tool", "terraform", "--drift")[0], 2)

    def test_w10_8_outside_drift_alone_is_drift(self):
        plan = json.loads(TF_SAME.read_text())
        plan["resource_drift"] = [{"address": "terraform_data.keep_a", "type": "terraform_data",
                                   "change": {"actions": ["update"]}}]
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run("summarize", write(tmp, "d.json", plan), "--tool", "terraform", "--drift")[0], 2)

    def test_w10_8_no_change_and_ignore_are_not_drift(self):
        data = {"status": "Succeeded", "changes": [
            {"resourceId": "/subscriptions/0/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv",
             "changeType": "NoChange"},
            {"resourceId": "/subscriptions/0/resourceGroups/rg/providers/Microsoft.Compute/disks/d",
             "changeType": "Ignore"}]}
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "w.json", data), "--tool", "bicep", "--drift")
        self.assertEqual(code, 0, out)


class Errors(unittest.TestCase):
    def assertOneError(self, code, out, *words):
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertNotIn("Traceback", out)
        for word in words:
            self.assertIn(word, out)

    def test_w10_9_unknown_tool(self):
        code, out = run("summarize", TF_PLAN, "--tool", "pulumi")
        self.assertOneError(code, out, "pulumi", "terraform", "bicep", "cloudformation", "infra-manager")
        self.assertOneError(*run("verify", TF_PLAN, "--tool", "pulumi", "--expect", "0" * 64), "pulumi")

    def test_w10_9_missing_file_and_missing_options(self):
        self.assertOneError(*run("summarize", FIXTURES / "nope.json", "--tool", "terraform"), "nope.json")
        self.assertOneError(*run("summarize", TF_PLAN))
        self.assertOneError(*run("verify", TF_PLAN, "--tool", "terraform"))
        self.assertOneError(*run("explode"))

    def test_w10_9_malformed_input(self):
        # Each case names the words of the guard it is written for (gate 2 round 2, F7): a case that
        # fails on another guard does not protect its own.
        arn = "arn:aws:cloudformation:us-east-1:123456789012:changeSet/c/00000000-0000-0000-0000-000000000006"
        resource = {"Type": "Resource", "ResourceChange": {
            "Action": "Add", "LogicalResourceId": "A", "ResourceType": "AWS::S3::Bucket"}}
        cases = {
            "not json": ("terraform", "{not json", "not JSON"),
            "a list": ("terraform", [], "no format_version"),
            "no format_version": ("terraform", {"resource_changes": []}, "no format_version"),
            "changes not a list": ("terraform", {"format_version": "1.2", "resource_changes": {}},
                                   "resource_changes must be a list"),
            "change not an object": ("terraform", {"format_version": "1.2", "resource_changes": [3]},
                                     "resource_changes[0] must be an object"),
            "no address": ("terraform", {"format_version": "1.2", "resource_changes": [
                {"type": "x", "change": {"actions": ["create"]}}]}, "resource_changes[0] has no address"),
            "actions not a list": ("terraform", {"format_version": "1.2", "resource_changes": [
                {"address": "x.a", "type": "x", "change": {"actions": "create"}}]},
                "change.actions must be a list of strings"),
            "no change": ("terraform", {"format_version": "1.2", "resource_changes": [
                {"address": "x.a", "type": "x"}]}, "resource_changes[0] has no change object"),
            "errored plan": ("terraform", {"format_version": "1.2", "errored": True, "resource_changes": []},
                             "the plan errored"),
            "drift not a list": ("terraform", {"format_version": "1.2", "resource_drift": "x"},
                                 "resource_drift must be a list"),
            "bicep no changes": ("bicep", {"status": "Succeeded"}, "no changes list"),
            "bicep change no id": ("bicep", {"changes": [{"changeType": "Create"}]}, "changes[0] has no resourceId"),
            "bicep no change type": ("bicep", {"changes": [{"resourceId": "/x"}]}, "changes[0] has no changeType"),
            "bicep failed": ("bicep", {"status": "Failed", "error": {"code": "InvalidTemplate"}, "changes": None},
                             "the what-if did not succeed"),
            "bicep changes not a list": ("bicep", {"changes": "Create"}, "no changes list"),
            "cfn no changes key": ("cloudformation", {"StackName": "s", "ChangeSetId": arn}, "(no Changes)"),
            "cfn changes not a list": ("cloudformation", {"Changes": {}, "ChangeSetId": arn},
                                       "Changes must be a list"),
            "cfn change not an object": ("cloudformation", {"Changes": ["Add"], "ChangeSetId": arn},
                                         "Changes[0] has no ResourceChange object"),
            "cfn no resource change": ("cloudformation", {"Changes": [{"Type": "Resource"}], "ChangeSetId": arn},
                                       "Changes[0] has no ResourceChange object"),
            "cfn action not a string": ("cloudformation", {"ChangeSetId": arn, "Changes": [
                {"Type": "Resource", "ResourceChange": {
                    "Action": 1, "LogicalResourceId": "A", "ResourceType": "AWS::S3::Bucket"}}]},
                "Changes[0].ResourceChange.Action must be a string"),
            "cfn no logical id": ("cloudformation", {"ChangeSetId": arn, "Changes": [
                {"Type": "Resource", "ResourceChange": {"Action": "Add", "ResourceType": "AWS::S3::Bucket"}}]},
                "Changes[0] has no LogicalResourceId"),
            "cfn no resource type": ("cloudformation", {"ChangeSetId": arn, "Changes": [
                {"Type": "Resource", "ResourceChange": {"Action": "Add", "LogicalResourceId": "A"}}]},
                "Changes[0] has no ResourceType"),
            "cfn more pages": ("cloudformation", {"Changes": [resource], "ChangeSetId": arn, "NextToken": "abc"},
                               "more pages (NextToken)"),
            "cfn no arn": ("cloudformation", {"Changes": [resource]}, "no ChangeSetId ARN"),
            "cfn name not arn": ("cloudformation", {"Changes": [resource], "ChangeSetId": "orders-prod"},
                                 "no ChangeSetId ARN"),
            "cfn parameters not a list": ("cloudformation", {"Changes": [resource], "ChangeSetId": arn,
                                                             "Parameters": {"TablePrefix": "x"}},
                                          "Parameters must be a list"),
            "cfn still creating": ("cloudformation", {"Changes": [resource], "ChangeSetId": arn,
                                                      "Status": "CREATE_IN_PROGRESS"},
                                   "status is CREATE_IN_PROGRESS: wait for CREATE_COMPLETE"),
            "cfn failed": ("cloudformation", {"Changes": [], "ChangeSetId": arn, "Status": "FAILED",
                                              "StatusReason": "Template error"},
                           "the change set FAILED: Template error"),
        }
        for name, (tool, data, words) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "input.json"
                path.write_text(data if isinstance(data, str) else json.dumps(data))
                self.assertOneError(*run("summarize", path, "--tool", tool), "input.json", words)
                self.assertOneError(*run("verify", path, "--tool", tool, "--expect", "0" * 64), "input.json", words)

    def test_a7_help(self):
        code, out = run("--help")
        self.assertEqual(code, 0, out)
        for word in ("summarize", "verify", "--drift", "--expect", "--accept-unknown", "--confirm-destructive"):
            self.assertIn(word, out)


def paragraphs(text):
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]


def has_paragraph(text, *phrases):
    return any(all(p.lower() in para.lower() for p in phrases) for para in paragraphs(text))


SECRET_PATTERNS = {
    "AWS access key ID": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "AWS secret key setting": r"(?i)aws_secret_access_key",
    "Azure storage key": r"(?i)AccountKey=",
    "Azure SAS token": r"(?i)(?:SharedAccessSignature|[?&]sig=)[A-Za-z0-9%+/=]{10,}",
    "client secret": r"(?i)client_secret",
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "GCP service account key": r"\"private_key(?:_id)?\"\s*:",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,})",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "JSON web token": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}",
    "password value": r"(?i)\"(?:password|passwd|admin_password|master_password|secret)\"\s*:\s*\"[^\"]+\"",
}


class SkillText(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL / "SKILL.md").read_text()

    def test_anatomy_a1_a3_a4_a6_a7(self):
        self.assertEqual(anatomy("provisioning", item=True), [])

    def test_w11_1_and_x1_approval_binds_to_the_summary_digest(self):
        self.assertTrue(has_paragraph(self.skill, "shared or production", "pre-authorizes", "summary digest",
                                      "owner approves"), "W11.1 rule missing")
        self.assertTrue(has_paragraph(self.skill, "Outside a contract mission, the owner approves the exact"),
                        "X1 rule missing")
        self.assertIn("verify", self.skill)
        self.assertIn("--expect", self.skill)

    def test_w11_2_destructive_stateful_change_needs_its_own_confirmation(self):
        self.assertTrue(has_paragraph(self.skill, "destructive", "stateful", "own explicit confirmation"))
        self.assertIn("--confirm-destructive", self.skill)

    def test_w11_3_each_reference_names_its_commands(self):
        expected = {
            "terraform.md": {"Preview": "terraform plan", "Apply": "terraform apply", "Drift": "-detailed-exitcode",
                             "Policy": "checkov", "Cost": "infracost"},
            "bicep.md": {"Preview": "az deployment group what-if", "Apply": "az deployment group create",
                         "Drift": "what-if", "Policy": "Assert-PSRule", "Cost": "azure-cost-estimator"},
            "cloudformation.md": {"Preview": "create-change-set", "Apply": "execute-change-set",
                                  "Drift": "detect-stack-drift", "Policy": "cfn-guard",
                                  "Cost": "estimate-template-cost"},
            "gcp-infrastructure-manager.md": {"Preview": "gcloud infra-manager previews create",
                                              "Apply": "gcloud infra-manager deployments apply",
                                              "Drift": "resource-drifts list", "Policy": "terraform vet",
                                              "Cost": "infracost"},
        }
        for name, steps in expected.items():
            text = (REFERENCE / name).read_text()
            for step, command in steps.items():
                with self.subTest(reference=name, step=step):
                    row = re.search(rf"^\| {step} \|(.*)$", text, re.M)
                    self.assertIsNotNone(row, f"{name} has no '| {step} |' row")
                    commands = " ".join(re.findall(r"`([^`]+)`", row.group(1)))
                    self.assertIn(command, commands)
            self.assertIn("change_summary.py", text, name)

    def test_w11_4_credentials_rule_and_oidc(self):
        for path in (SKILL / "SKILL.md", REFERENCE / "identity.md"):
            text = path.read_text()
            with self.subTest(file=path.name):
                self.assertTrue(has_paragraph(text, "credentials never enter the repository, the mission file or chat"))
                self.assertIn("OIDC federation", text)
        identity = (REFERENCE / "identity.md").read_text()
        for word in ("Azure", "AWS", "Google Cloud", "remote", "lock"):
            self.assertIn(word, identity)

    def test_w11_4_no_fixture_matches_a_secret_pattern(self):
        files = sorted(p for p in FIXTURES.rglob("*") if p.is_file())
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            text = path.read_text()
            for name, pattern in SECRET_PATTERNS.items():
                with self.subTest(file=path.name, pattern=name):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} matches {name}")

    def test_w11_4_secret_patterns_catch_samples(self):
        # Built at run time so this file holds no secret-shaped string.
        samples = {
            "AWS access key ID": "AKIA" + "Q" * 16,
            "Azure storage key": "Account" + "Key=abc",
            "private key block": "-----BEGIN RSA " + "PRIVATE KEY-----",
            "GitHub token": "ghp_" + "a" * 36,
            "password value": '"pass' + 'word": "x"',
        }
        for name, sample in samples.items():
            self.assertIsNotNone(re.search(SECRET_PATTERNS[name], sample), name)

    def test_w11_5_deployment_manager_is_migration_only(self):
        gcp = (REFERENCE / "gcp-infrastructure-manager.md").read_text()
        for name, text in (("SKILL.md", self.skill), ("gcp-infrastructure-manager.md", gcp)):
            with self.subTest(file=name):
                self.assertTrue(has_paragraph(text, "Deployment Manager", "migration only"))
        for command in ("deployment-manager deployments create", "deployment-manager deployments update"):
            self.assertNotIn(command, gcp + self.skill)

    def test_x7_without_a_shell_rule(self):
        rule = re.search(r"^#+ .*Without a shell.*?\n(.*?)(?=^#+ |\Z)", self.skill, re.M | re.S)
        self.assertIsNotNone(rule, "SKILL.md needs a 'Without a shell' rule")
        self.assertIn("change_summary.py", rule.group(1))
        self.assertIn("not run", rule.group(1))

    def test_stateful_list_is_documented(self):
        sys.path.insert(0, str(SCRIPT.parent))
        sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
        import change_summary
        environments = (REFERENCE / "environments.md").read_text()
        # Review nit 6: compare both ways. The stateful table has one row per cloud.
        rows = [l for l in environments.splitlines() if re.match(r"^\| (Azure|AWS|Google Cloud) \|", l)]
        self.assertEqual(len(rows), 3, rows)
        documented = {t for row in rows for t in re.findall(r"`([^`]+)`", row)}
        self.assertEqual(documented, set(change_summary.STATEFUL))

    def test_companions_and_fixture_labels(self):
        for name in ("scanning-vulnerabilities", "releasing", "architecting", "monitoring"):
            self.assertIn(name, self.skill)
        readme = (FIXTURES / "README.md").read_text()
        for sample in ("terraform-stateful-sample.json", "bicep-whatif-sample.json",
                       "cloudformation-changeset-sample.json"):
            row = next(l for l in readme.splitlines() if l.startswith(f"| `{sample}`"))
            self.assertIn("https://", row)
        self.assertIn("hand-written sample", readme)
        self.assertIn("Terraform 1.17.2", readme)


TF_IMPORT = FIXTURES / "terraform-local-import.json"
# A plan or preview file named in a command without the <plans>/ folder (review M2).
LOOSE_PLAN_FILE = re.compile(
    r"(?<![\w/<>.-])(?:tfplan|(?:plan|after|drift|whatif|changeset|preview)\.(?:json|tfplan)|preview)(?![\w.-])")


class ReviewRound1(unittest.TestCase):
    """Repairs from reviews/m3/W10W11-r1.md: M1 to M3, nits 2 to 7 and the two follow-ups."""

    def test_m1_terraform_import_is_counted_and_is_drift(self):
        code, out = run("summarize", TF_IMPORT, "--tool", "terraform", "--drift")
        # By hand: random_integer.n is ["no-op"] with "importing"; terraform_data.marker is a create.
        # Terraform's own line: "Plan: 1 to import, 1 to add, 0 to change, 0 to destroy."
        self.assertEqual(code, 2, out)
        self.assertEqual(counts(out), {"create": 1, "update": 0, "replace": 0, "delete": 0, "no-op": 0,
                                       "import": 1})
        self.assertIn(("import", "random_integer.n", "random_integer"), listed(out, "Changes:"))

    def test_m1_update_with_import_stays_an_update_and_says_import(self):
        plan = {"format_version": "1.2", "resource_changes": [
            {"address": "x.a", "type": "x", "change": {"actions": ["update"], "importing": {"id": "a"}}}]}
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "u.json", plan), "--tool", "terraform")
        self.assertEqual(counts(out), {"create": 0, "update": 1, "replace": 0, "delete": 0, "no-op": 0})
        self.assertIn("- update x.a (x) (import)", out)

    def test_m2_plan_files_live_in_the_plans_folder(self):
        for path in [SKILL / "SKILL.md", *sorted(REFERENCE.glob("*.md"))]:
            text = path.read_text()
            fence = r"^[ \t]*```\w*\n(.*?)^[ \t]*```"
            fenced = re.findall(fence, text, re.M | re.S)
            inline = re.findall(r"`([^`\n]+)`", re.sub(fence, "", text, flags=re.M | re.S))
            for command in fenced + inline:
                with self.subTest(file=path.name, command=command[:60]):
                    self.assertIsNone(LOOSE_PLAN_FILE.search(command), command)
        for name in ("terraform.md", "bicep.md", "cloudformation.md", "gcp-infrastructure-manager.md"):
            text = (REFERENCE / name).read_text()
            with self.subTest(file=name):
                self.assertIn("<plans>/", text)
                self.assertTrue(has_paragraph(text, "`<plans>`", "outside the checkout"))
        self.assertTrue(has_paragraph(self.skill_text(), "`<plans>`", "outside the checkout"))

    def test_m2_the_pattern_catches_a_loose_file(self):
        for bad in ("terraform plan -out=tfplan", "terraform show -json tfplan > plan.json",
                    "gcloud infra-manager previews export <preview> --file=preview"):
            self.assertIsNotNone(LOOSE_PLAN_FILE.search(bad), bad)
        for good in ("terraform plan -out=<plans>/tfplan", "--file=<plans>/preview",
                     "gcloud infra-manager previews create <preview>", "--preview=<drift-preview>"):
            self.assertIsNone(LOOSE_PLAN_FILE.search(good), good)

    def test_m3_psrule_needs_template_expansion(self):
        row = self.row("bicep.md", "Policy")
        self.assertIn("ps-rule.yaml", row)
        self.assertIn("AZURE_PARAMETER_FILE_EXPANSION: true", row)
        self.assertIn("not a policy result", row)

    def test_nit1_preview_flags_cite_the_gcloud_reference(self):
        gcp = (REFERENCE / "gcp-infrastructure-manager.md").read_text()
        self.assertIn("sdk/gcloud/reference/infra-manager/previews/create", gcp)
        self.assertIn("--tf-version-constraint", gcp)

    def test_nit2_each_preview_gets_a_new_id(self):
        gcp = (REFERENCE / "gcp-infrastructure-manager.md").read_text()
        ids = re.findall(r"previews create (<[^>]+>)", gcp)
        self.assertGreaterEqual(len(ids), 3, ids)
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertTrue(has_paragraph(gcp, "new preview ID"))

    def test_nit3_drift_counts_each_resource_once(self):
        plan = json.loads(TF_SAME.read_text())
        keep = next(c for c in plan["resource_changes"] if c["address"] == "terraform_data.keep_a")
        keep["change"]["actions"] = ["create"]
        plan["resource_drift"] = [{"address": "terraform_data.keep_a", "type": "terraform_data",
                                   "change": {"actions": ["delete"]}}]
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("summarize", write(tmp, "d.json", plan), "--tool", "terraform", "--drift")
        self.assertEqual(code, 2, out)
        self.assertIn("Drift: 1 resource", out.splitlines())

    def test_nit4_what_if_writes_json(self):
        bicep = (REFERENCE / "bicep.md").read_text()
        commands = [c for c in re.findall(r"`([^`]+)`", bicep) if c.startswith("az deployment group what-if")]
        self.assertGreaterEqual(len(commands), 2)
        for command in commands:
            self.assertIn("--output json", command)

    def test_nit5_approvals_become_ledger_rows(self):
        self.assertTrue(has_paragraph(self.skill_text(), "missioning", "ledger row", "destructive"))

    def test_nit7_a_binary_plan_gets_a_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tfplan"
            path.write_bytes(b"PK\x03\x04\x14\x00\x08\x00\x9c\x8f binary plan")
            code, out = run("summarize", path, "--tool", "terraform")
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("terraform show -json", out)

    def test_followup_plan_file_hash_is_bound_to_the_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a.tfplan", Path(tmp) / "b.tfplan"
            # A saved Terraform plan is a zip file: it starts with PK\x03\x04 (recheck N3).
            first.write_bytes(b"PK\x03\x04saved plan one")
            second.write_bytes(b"PK\x03\x04saved plan two")
            code, out = run("summarize", TF_PLAN, "--tool", "terraform", "--plan-file", first)
            self.assertEqual(code, 0, out)
            # SHA-256 of the bytes written above, computed here, not by the script.
            expected = hashlib.sha256(b"PK\x03\x04saved plan one").hexdigest()
            self.assertIn(f"Plan file SHA-256: {expected}", out)
            digest = digest_of(out)
            self.assertNotEqual(digest, digest_of(run("summarize", TF_PLAN, "--tool", "terraform")[1]))
            ok = run("verify", TF_PLAN, "--tool", "terraform", "--plan-file", first, "--expect", digest)
            self.assertEqual(ok[0], 0, ok[1])
            other = run("verify", TF_PLAN, "--tool", "terraform", "--plan-file", second, "--expect", digest)
            self.assertEqual(other[0], 1, other[1])
            self.assertEqual(len(other[1].strip().splitlines()), 1, other[1])
            self.assertEqual(run("verify", TF_PLAN, "--tool", "terraform", "--expect", digest)[0], 1)
            wrong_tool = run("summarize", BICEP, "--tool", "bicep", "--plan-file", first)
            missing = run("summarize", TF_PLAN, "--tool", "terraform", "--plan-file", Path(tmp) / "nope")
        for code, out in (wrong_tool, missing):
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("--plan-file", wrong_tool[1])

    def test_followup_terraform_apply_uses_the_summarized_plan_file(self):
        terraform = (REFERENCE / "terraform.md").read_text()
        self.assertTrue(has_paragraph(terraform, "same file", "terraform show -json", "--plan-file", "SHA-256"))
        self.assertIn("--plan-file <plans>/tfplan", self.row("terraform.md", "Apply"))
        self.assertTrue(has_paragraph(self.skill_text(), "SHA-256", "summary digest", "report"))

    def test_followup_bicep_volatile_properties_caveat(self):
        bicep = (REFERENCE / "bicep.md").read_text()
        self.assertTrue(has_paragraph(bicep, "volatile", "new approval", "not proven"))

    def skill_text(self):
        return (SKILL / "SKILL.md").read_text()

    def row(self, name, step):
        match = re.search(rf"^\| {step} \|(.*)$", (REFERENCE / name).read_text(), re.M)
        self.assertIsNotNone(match, f"{name} has no {step} row")
        return match.group(1)


class ReviewRecheck(unittest.TestCase):
    """Repairs from the recheck in reviews/m3/W10W11-r1.md: N1 to N4."""

    REFERENCES = ("terraform.md", "bicep.md", "cloudformation.md", "gcp-infrastructure-manager.md")

    def test_n1_plans_example_is_outside_any_checkout(self):
        files = {"SKILL.md": (SKILL / "SKILL.md").read_text()}
        files.update({name: (REFERENCE / name).read_text() for name in self.REFERENCES})
        for name, text in files.items():
            with self.subTest(file=name):
                self.assertNotIn("../plans", text)
                self.assertIn("$HOME/plans/", text)
                self.assertIn("git -C <plans> rev-parse", text)
        self.assertTrue(has_paragraph(files["SKILL.md"], "git -C <plans> rev-parse", "must fail"))

    def test_n2_terraform_summary_without_a_plan_file_is_labelled(self):
        code, out = run("summarize", TF_PLAN, "--tool", "terraform")
        self.assertEqual(code, 0, out)
        self.assertIn("Plan file: not bound", out)
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "tfplan"
            plan.write_bytes(b"PK\x03\x04x")
            out = run("summarize", TF_PLAN, "--tool", "terraform", "--plan-file", plan)[1]
        self.assertNotIn("not bound", out)
        self.assertNotIn("Plan file:", run("summarize", BICEP, "--tool", "bicep")[1])

    def test_n2_rule_for_a_summary_without_the_saved_plan_file(self):
        for path in (SKILL / "SKILL.md", REFERENCE / "terraform.md"):
            with self.subTest(file=path.name):
                self.assertTrue(has_paragraph(path.read_text(), "plan file not bound", "--plan-file",
                                              "do not apply"))

    def test_n2_eval_pass_rule_3_uses_the_plan_file_form(self):
        readme = (ROOT / "evals" / "provisioning" / "README.md").read_text()
        rule = re.search(r"^3\. (.*?)(?=^\d+\. )", readme, re.M | re.S).group(1)
        for phrase in ("plan file not bound", "<plans>/tfplan", "--plan-file", "not run"):
            self.assertIn(phrase, rule)
        self.assertNotIn("apply -input=false tfplan", readme)

    def test_n3_plan_file_must_be_a_saved_plan_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            not_zip = write(tmp, "plan.json", {"format_version": "1.2"})
            code, out = run("summarize", TF_PLAN, "--tool", "terraform", "--plan-file", not_zip)
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out.strip().splitlines()), 1, out)
            self.assertIn("not a saved Terraform plan", out)
            code, out = run("verify", TF_PLAN, "--tool", "terraform", "--plan-file", not_zip,
                            "--expect", "0" * 64)
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out.strip().splitlines()), 1, out)

    def test_n4_refusal_names_the_plan_file_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            approved, replanned = Path(tmp) / "a.tfplan", Path(tmp) / "b.tfplan"
            approved.write_bytes(b"PK\x03\x04first plan")
            replanned.write_bytes(b"PK\x03\x04second plan")
            digest = digest_of(run("summarize", TF_PLAN, "--tool", "terraform", "--plan-file", approved)[1])
            code, out = run("verify", TF_PLAN, "--tool", "terraform", "--plan-file", replanned, "--expect", digest)
        self.assertEqual(code, 1, out)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 1, out)
        self.assertIn("does not match", lines[0])
        now = hashlib.sha256(b"PK\x03\x04second plan").hexdigest()
        self.assertIn(f"plan file SHA-256 is now {now}", lines[0])


class EvalRound1(unittest.TestCase):
    """Fixes from evals/provisioning/results.md, round 1: findings F1 to F4."""

    def test_f2_verify_terraform_without_a_plan_file_refuses(self):
        digest = digest_of(run("summarize", TF_PLAN, "--tool", "terraform")[1])
        code, out = run("verify", TF_PLAN, "--tool", "terraform", "--expect", digest)
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("plan file not bound", out)
        self.assertIn("--plan-file <plans>/tfplan", out)
        # Only Terraform applies a saved plan file; Infrastructure Manager verifies without one.
        digest = digest_of(run("summarize", TF_PLAN, "--tool", "infra-manager")[1])
        code, out = run("verify", TF_PLAN, "--tool", "infra-manager", "--expect", digest)
        self.assertEqual(code, 0, out)

    def test_f2_unbound_next_line_asks_for_the_plan_file(self):
        out = run("summarize", TF_PLAN, "--tool", "terraform")[1]
        nxt = next(l for l in out.splitlines() if l.startswith("Next: "))
        self.assertIn("get the saved plan file", nxt)
        self.assertIn("summarize again with --plan-file <plans>/tfplan", nxt)
        self.assertNotIn("verify", nxt)
        self.assertNotIn("approved", nxt)
        bound = run("summarize", TF_PLAN, "--tool", "terraform", *BOUND)[1]
        nxt = next(l for l in bound.splitlines() if l.startswith("Next: "))
        self.assertIn("verify", nxt)
        self.assertIn("--plan-file", nxt)

    def test_f1_unbound_summary_gives_the_apply_commands_verbatim(self):
        for path in (SKILL / "SKILL.md", REFERENCE / "terraform.md"):
            with self.subTest(file=path.name):
                self.assertTrue(has_paragraph(path.read_text(), "plan file not bound", "Apply commands verbatim",
                                              "`<digest>`", "not run"))
        terraform = (REFERENCE / "terraform.md").read_text()
        apply_row = re.search(r"^\| Apply \|(.*)$", terraform, re.M).group(1)
        for command in ("terraform show -json <plans>/tfplan > <plans>/plan.json",
                        "verify <plans>/plan.json --tool terraform --plan-file <plans>/tfplan --expect <digest>",
                        "terraform apply -input=false <plans>/tfplan"):
            self.assertIn(command, apply_row)

    def test_f3_a_refused_destructive_change_stops_the_plan(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(has_paragraph(text, "refuses a destructive change", "stop", "cannot be applied in part",
                                      "delete-change-set", "discard the plan file", "preview again",
                                      "Never list the apply commands for the refused plan"))

    def test_f4_s1_operator_approves_any_full_digest(self):
        readme = (ROOT / "evals" / "provisioning" / "README.md").read_text()
        self.assertTrue(has_paragraph(readme, "In S1", "any message", "full summary digest",
                                      "Approved: <that digest>"))


class Gate2(unittest.TestCase):
    """Fixes from reviews/m3/gate2.md: F1, F2 and F5."""

    CONFIRM = ("--confirm-destructive", "OrdersDatabase", "--confirm-destructive", "SessionsTable",
               "--confirm-destructive", "ArchiveBucket")

    def cfn_copy(self, tmp, name, edit):
        data = json.loads(CFN.read_text())
        edit(data)
        return write(tmp, name, data)

    def test_f1_change_set_id_and_parameters_bind_the_digest(self):
        digest = digest_of(run("summarize", CFN, "--tool", "cloudformation")[1])
        code, out = run("verify", CFN, "--tool", "cloudformation", "--expect", digest, *self.CONFIRM)
        self.assertEqual(code, 0, out)

        def new_id(data):  # the same change set name, deleted and created again
            data["ChangeSetId"] = data["ChangeSetId"].replace("000000000002", "000000000004")
            data["CreationTime"] = "2026-11-22T10:00:00.000Z"

        def new_parameter(data):
            data["Parameters"][0]["ParameterValue"] = "CHANGED-orders-prod"

        with tempfile.TemporaryDirectory() as tmp:
            for name, edit in (("new-id.json", new_id), ("new-parameter.json", new_parameter)):
                with self.subTest(copy=name):
                    path = self.cfn_copy(tmp, name, edit)
                    self.assertEqual(json.loads(path.read_text())["Changes"], json.loads(CFN.read_text())["Changes"])
                    code, out = run("verify", path, "--tool", "cloudformation", "--expect", digest, *self.CONFIRM)
                    self.assertEqual(code, 1, out)
                    self.assertEqual(len(out.strip().splitlines()), 1, out)
                    self.assertIn("does not match", out)

    def test_f1_summary_names_the_change_set_arn(self):
        arn = json.loads(CFN.read_text())["ChangeSetId"]
        self.assertTrue(arn.startswith("arn:aws:cloudformation:"))
        out = run("summarize", CFN, "--tool", "cloudformation")[1]
        self.assertIn(f"Change set: {arn}", out.splitlines())

    def test_f1_change_set_id_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.cfn_copy(tmp, "no-id.json", lambda data: data.pop("ChangeSetId"))
            code, out = run("summarize", path, "--tool", "cloudformation")
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("ChangeSetId", out)

    def test_f1_reference_fetches_property_values_and_executes_by_arn(self):
        text = (REFERENCE / "cloudformation.md").read_text()
        commands = re.findall(r"`([^`\n]+)`", text)
        describes = [c for c in commands if c.startswith("aws cloudformation describe-change-set")]
        executes = [c for c in commands if c.startswith("aws cloudformation execute-change-set")]
        self.assertGreaterEqual(len(describes), 2, describes)
        self.assertGreaterEqual(len(executes), 1, executes)
        for command in describes:
            self.assertIn("--include-property-values", command)
        for command in executes:
            self.assertIn("--change-set-name <change-set-arn>", command)
            self.assertNotIn("--stack-name", command)
        apply_row = re.search(r"^\| Apply \|(.*)$", text, re.M).group(1)
        self.assertIn("describe-change-set --change-set-name <change-set-arn>", apply_row)
        # Gate 2 round 2, F10: the introduction says the same.
        intro = " ".join(text.split("## Commands")[0].split())
        self.assertIn("execute that change set by its ARN", intro)
        self.assertNotIn("by name", intro)

    def test_f1_fixture_carries_property_values(self):
        data = json.loads(CFN.read_text())
        targets = [d["Target"] for c in data["Changes"] for d in c["ResourceChange"].get("Details", [])]
        self.assertTrue(targets)
        for target in targets:
            self.assertIn("BeforeValue", target)
            self.assertIn("AfterValue", target)

    def test_f2_infra_manager_apply_verifies_a_new_preview(self):
        text = (REFERENCE / "gcp-infrastructure-manager.md").read_text()
        rows = {step: re.search(rf"^\| {step} \|(.*)$", text, re.M).group(1) for step in ("Preview", "Summary", "Apply")}
        summary_file = re.search(r"summarize (\S+)", rows["Summary"]).group(1)
        preview_id = re.search(r"previews create (<[^>]+>)", rows["Preview"]).group(1)
        apply = rows["Apply"]
        created = re.search(r"previews create (<[^>]+>) --deployment=<deployment> <pins>", apply)
        self.assertIsNotNone(created, apply)
        self.assertNotEqual(created.group(1), preview_id)
        exported = re.search(rf"previews export {re.escape(created.group(1))} --file=(<plans>/\S+)`", apply)
        self.assertIsNotNone(exported, apply)
        verified = re.search(r"verify (\S+) --tool infra-manager --expect <digest>", apply)
        self.assertIsNotNone(verified, apply)
        self.assertNotEqual(verified.group(1), summary_file)
        self.assertTrue(verified.group(1).startswith(exported.group(1)))
        order = [apply.index(part) for part in ("previews create", "previews export", " verify ",
                                                "deployments apply")]
        self.assertEqual(order, sorted(order), apply)

    def test_f5_bicep_potential_change_is_unknown_and_needs_accept_unknown(self):
        data = json.loads(BICEP.read_text())
        changes = data["properties"]["changes"]
        data["properties"]["changes"] = [c for c in changes if c["changeType"] != "Unsupported"]
        rg = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-orders-prod/providers/"
        potential = rg + "Microsoft.Sql/servers/sql-orders-prod/databases/reports"
        data["properties"]["potentialChanges"] = [{"resourceId": potential, "changeType": "Modify"}]
        cosmos = rg + "Microsoft.DocumentDB/databaseAccounts/cosmos-orders-legacy"
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "potential.json", data)
            code, out = run("summarize", path, "--tool", "bicep")
            self.assertEqual(code, 0, out)
            self.assertEqual(counts(out)["unknown"], 1)
            self.assertEqual([addr for _, addr, _ in listed(out, "Unknown")], [potential])
            self.assertIn("potential change (Modify)", out)
            self.assertNotIn(potential, [addr for _, addr, _ in listed(out, "Changes:")])
            digest = digest_of(out)
            code, out = run("verify", path, "--tool", "bicep", "--expect", digest, "--confirm-destructive", cosmos)
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out.strip().splitlines()), 1, out)
            self.assertIn(potential, out)
            self.assertIn("--accept-unknown", out)
            code, out = run("verify", path, "--tool", "bicep", "--expect", digest, "--confirm-destructive", cosmos,
                            "--accept-unknown")
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()

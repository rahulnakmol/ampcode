"""Tests for the syncing skill's Azure DevOps (W17) and Linear (W18) adapters.

Run: python3 -m unittest tests.test_syncing -v
No network calls (Q6): each tracker is an in-memory fake behind the adapter's transport, and the
real transports are only given fake openers. Expected values are written out by hand.
"""

import base64
import contextlib
import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "syncing"
SYNC = SKILL / "scripts" / "sync.py"
FIXTURE = ROOT / "tests" / "fixtures" / "syncing" / "fake_plan.py"
EXAMPLES = ROOT / "skills" / "grooming" / "reference" / "examples"
sys.path.insert(0, str(ROOT / "skills" / "grooming" / "scripts"))
sys.path.insert(0, str(SKILL / "scripts"))

import azure  # noqa: E402
import backlog  # noqa: E402
import linear  # noqa: E402
import sync  # noqa: E402

# The operations example, in the order every plan lists items: type, then ID.
ORDERED = ["I-1", "G-1", "G-2", "F-1", "F-2", "F-3", "S-1", "S-2", "S-3", "S-4", "S-5", "S-6", "B-1"]
PARENTS = {"G-1": "I-1", "G-2": "I-1", "F-1": "G-2", "F-2": "G-1", "F-3": "G-1", "S-1": "F-1", "S-2": "F-1",
           "S-3": "F-1", "S-4": "F-2", "S-5": "F-2", "S-6": "F-3", "B-1": "F-1"}
PRIYA_AZ, TOM_AZ = "priya.raman@acme.example", "tom.okafor@acme.example"


def example():
    data = json.loads((EXAMPLES / "operations.json").read_text())
    data["approvers"][0].update(azure=PRIYA_AZ, linear="priya")      # Linear display name
    data["approvers"][1].update(azure=TOM_AZ, linear=TOM_AZ)         # Linear email
    return data


def item(data, iid):
    return backlog.items_by_id(data)[iid]


class Clock:
    def __init__(self):
        self.ticks = 0

    def now(self):
        self.ticks += 1
        return f"2027-01-10T{self.ticks // 3600:02d}:{self.ticks // 60 % 60:02d}:{self.ticks % 60:02d}Z"


# Azure DevOps fake -----------------------------------------------------------------------------

class FakeAzure:
    """Just enough of the Azure DevOps REST API for organisation acme, project close."""

    PARENT = "System.LinkTypes.Hierarchy-Reverse"

    def __init__(self, me=PRIYA_AZ, project="close", tag_case=None):
        self.items, self.iterations, self.comments = {}, [], {}
        self.writes, self.clock, self.me, self.project = 0, Clock(), me, project
        self.tag_case = tag_case or {}  # like Azure, reuse the casing of a tag the organisation already has
        self.profile_calls, self.identity, self.after_get, self.patches = 0, "ok", None, []

    def call(self, method, path, body=None):
        route, _, query = path.partition("?")
        if method != "GET":
            self.writes += 1
        if "app.vssps.visualstudio.com" in route:  # Profiles - Get refuses a personal access token
            self.profile_calls += 1
            raise RuntimeError("GET https://app.vssps.visualstudio.com/_apis/profile/profiles/me failed: HTTP 401")
        assert route.startswith("acme/"), path
        route = route.removeprefix("acme/")
        if route == "_apis/connectionData":
            assert query == "api-version=7.1-preview.1", query
            if self.identity == "refused":
                raise RuntimeError("GET https://dev.azure.com/acme/_apis/connectionData failed: HTTP 401")
            account = {"$type": "System.String", "$value": self.me} if self.identity == "ok" else {}
            return {"authenticatedUser": {"id": "d6245f20", "providerDisplayName": "Priya Raman", "properties": {"Account": account}}}
        route = route.removeprefix(f"{self.project}/_apis/wit/")
        parts = route.split("/")
        if route == "wiql":
            self.writes -= 1  # a WIQL query is a read
            assert "CONTAINS 'backlog'" in body["query"]
            return {"workItems": [{"id": i} for i, w in sorted(self.items.items()) if "backlog" in map(str.lower, self.tags(w))]}
        if route == "workitems" and method == "GET":
            ids = [int(i) for i in re.search(r"ids=([\d,]+)", query).group(1).split(",")]
            return {"value": [copy.deepcopy(self.items[i]) for i in ids if i in self.items]}
        if route.startswith("workitems/$") and method == "POST":
            kind = route.split("$", 1)[1].replace("%20", " ")
            wid = 100 + len(self.items)
            self.items[wid] = {"id": wid, "rev": 0, "fields": {"System.WorkItemType": kind, "System.State": "New",
                                                     "System.IterationPath": self.project}, "relations": [], "multilineFieldsFormat": {}}
            return self.patch(wid, body)
        if parts[0] == "workitems" and len(parts) == 2:
            wid = int(parts[1])
            if wid not in self.items:
                raise RuntimeError("Azure DevOps GET workitems: HTTP 404")
            if method == "PATCH":
                return self.patch(wid, body)
            found = copy.deepcopy(self.items[wid])
            if self.after_get:  # someone edits the item between our read and our write
                self.after_get(wid)
            return found
        if route == "classificationnodes/Iterations":
            if method == "GET":
                return {"name": self.project, "children": copy.deepcopy(self.iterations)} if self.iterations else {"name": self.project}
            self.iterations.append(body)
            return body
        if parts[0] == "workItems" and parts[2] == "comments":
            wid = int(parts[1])
            mine = self.comments.setdefault(wid, [])
            if method == "GET":
                return {"comments": copy.deepcopy(mine), "count": len(mine)}
            if method == "POST":
                assert "format=markdown" in query
                return self.comment(wid, self.me, body["text"])
            comment = next(c for c in mine if c["id"] == int(parts[3]))
            comment["text"] = body["text"]
            return comment
        raise AssertionError(f"unexpected call {method} {path}")

    def patch(self, wid, ops):
        work = self.items[wid]
        self.patches.append((wid, copy.deepcopy(ops)))
        if any(op["op"] == "test" and op["path"] == "/rev" and op["value"] != work["rev"] for op in ops):
            raise RuntimeError("Azure DevOps PATCH: HTTP 412 the work item changed (test /rev failed)")
        work = copy.deepcopy(work)  # a JSON Patch applies all of its operations or none
        for op in ops:
            if op["op"] == "test":
                continue
            assert op["op"] in ("add", "replace", "remove"), op
            where, _, name = op["path"][1:].partition("/")
            if op["op"] == "remove":
                assert where == "relations", op
                del work["relations"][int(name)]
            elif where == "fields" and name == "System.Tags":
                work["fields"][name] = "; ".join(self.tag_case.get(x.strip().lower(), x.strip()) for x in op["value"].split(";"))
            elif where == "fields":
                work["fields"][name] = op["value"]
            elif where == "multilineFieldsFormat":
                work["multilineFieldsFormat"][name] = op["value"].lower()
            elif where == "relations":
                if op["value"]["rel"] == self.PARENT and any(r["rel"] == self.PARENT for r in work["relations"]):
                    raise RuntimeError("Azure DevOps PATCH: HTTP 400 work item already has a parent")
                work["relations"].append(dict(op["value"], attributes={"name": "Parent"}))
        work["fields"]["System.ChangedDate"] = self.clock.now()
        work["rev"] += 1
        self.items[wid] = work
        return copy.deepcopy(work)

    def comment(self, wid, who, text, at=None):
        mine = self.comments.setdefault(wid, [])
        comment = {"id": 700 + sum(len(c) for c in self.comments.values()), "workItemId": wid, "text": text,
                   "createdBy": {"uniqueName": who, "displayName": who.split("@")[0]}, "createdDate": at or self.clock.now(),
                   "url": f"https://dev.azure.com/acme/close/_apis/wit/workItems/{wid}/comments/{700 + len(mine)}"}
        comment["url"] = f"https://dev.azure.com/acme/close/_apis/wit/workItems/{wid}/comments/{comment['id']}"
        mine.append(comment)
        return comment

    @staticmethod
    def tags(work):
        return [t.strip() for t in (work["fields"].get("System.Tags") or "").split(";") if t.strip()]

    def parent_of(self, wid):
        urls = [r["url"] for r in self.items[wid]["relations"] if r["rel"] == self.PARENT]
        return int(urls[0].rsplit("/", 1)[1]) if urls else None


class AzureCase(unittest.TestCase):
    process = "agile"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        Path(self.base, "prd.md").write_text((ROOT / "skills/planning/reference/worked-example/prd.md").read_text())
        self.fake = FakeAzure()
        self.az = azure.Azure("acme", "close", self.process, call=self.fake.call)
        self.data = example()

    def tearDown(self):
        self.tmp.cleanup()

    def wid(self, iid):
        return item(self.data, iid)["external"]["azure"]["id"]


class AzurePlan(AzureCase):
    def test_w17_1_agile_plan_creates_each_item_with_its_type_links_and_iterations(self):
        actions = sync.plan_tracker(self.data, self.base, self.az)
        self.assertEqual([(a["do"], a.get("title")) for a in actions[:2]],
                         [("create milestone", "PI 27.1 - pilot UK01"), ("create milestone", "PI 27.2 - all EU entities")])
        self.assertEqual([(a["start"], a["due"]) for a in actions[:2]], [("2027-01-11", "2027-02-26"), ("2027-02-27", "2027-05-28")])
        creates = {a["id"]: a for a in actions if a["do"] == "create"}
        self.assertEqual(list(creates), ORDERED)
        self.assertEqual({i: a["kind"] for i, a in creates.items()},
                         {"I-1": "Epic", "G-1": "Epic", "G-2": "Epic", "F-1": "Feature", "F-2": "Feature", "F-3": "Feature",
                          "S-1": "User Story", "S-2": "User Story", "S-3": "User Story", "S-4": "User Story",
                          "S-5": "User Story", "S-6": "User Story", "B-1": "Bug"})
        self.assertIn("goal", creates["G-1"]["labels"])
        self.assertNotIn("goal", creates["F-1"]["labels"])
        self.assertIn("backlog:S-3", creates["S-3"]["labels"])
        self.assertEqual(creates["S-3"]["title"], "[S-3] " + item(self.data, "S-3")["title"])
        pi1, pi2 = "PI 27.1 - pilot UK01", "PI 27.2 - all EU entities"  # ':' is not allowed in an iteration name
        self.assertEqual({i: a["milestone"] for i, a in creates.items()},
                         {"I-1": None, "G-1": None, "G-2": None, "F-1": pi1, "F-2": pi1, "F-3": pi2, "S-1": pi1, "S-2": pi1,
                          "S-3": pi1, "S-4": pi1, "S-5": pi1, "S-6": pi2, "B-1": pi1})
        links = [(a["id"], a["parent"], a["link"]) for a in actions if a["do"] == "link"]
        self.assertEqual(links, [(i, PARENTS[i], "child") for i in ORDERED[1:]])
        self.assertEqual(len(actions), 2 + 13 + 12)
        self.assertEqual(self.fake.writes, 0)

    def test_w17_1_scrum_and_basic_map_stories_and_bugs(self):
        for process, story, feature in (("scrum", "Product Backlog Item", "Feature"), ("basic", "Issue", "Epic")):
            az = azure.Azure("acme", "close", process, call=self.fake.call)
            kinds = {a["id"]: a["kind"] for a in sync.plan_tracker(self.data, self.base, az) if a["do"] == "create"}
            self.assertEqual((kinds["S-1"], kinds["B-1"], kinds["F-1"], kinds["I-1"]), (story, story, feature, "Epic"), process)

    def test_w17_1_plan_output_names_child_links_and_a_digest(self):
        path = Path(self.base, "backlog.json")
        path.write_text(json.dumps(self.data))
        code, out, _ = run_main(["azure", "plan", str(path), "--org", "acme", "--project", "close"], azure, self.fake.call)
        self.assertEqual(code, 0)
        self.assertIn("link             S-3 child of F-1", out)
        self.assertIn("plan: 2 create milestone, 13 create, 12 link", out)
        self.assertRegex(out, r"digest: [0-9a-f]{12}  \(apply with --expect [0-9a-f]{12} once approved\)")


class AzureApply(AzureCase):
    def test_w17_2_apply_with_the_right_digest_creates_links_and_records_ids(self):
        digest = sync.plan_digest(sync.plan_tracker(self.data, self.base, self.az), self.az.target)
        sync.apply_tracker(self.data, self.base, self.az, expect=digest)
        self.assertEqual(len(self.fake.items), 13)
        self.assertEqual([n["name"] for n in self.fake.iterations], ["PI 27.1 - pilot UK01", "PI 27.2 - all EU entities"])
        self.assertEqual(self.fake.iterations[0]["attributes"], {"startDate": "2027-01-11T00:00:00Z", "finishDate": "2027-02-26T00:00:00Z"})
        for iid, parent in PARENTS.items():
            self.assertEqual(self.fake.parent_of(self.wid(iid)), self.wid(parent), iid)
        s3 = self.fake.items[self.wid("S-3")]
        self.assertEqual(s3["fields"]["System.WorkItemType"], "User Story")
        self.assertEqual(s3["fields"]["System.IterationPath"], "close\\PI 27.1 - pilot UK01")
        self.assertEqual(s3["multilineFieldsFormat"], {"System.Description": "markdown"})
        self.assertIn("## Acceptance criteria", s3["fields"]["System.Description"])
        b1 = self.fake.items[self.wid("B-1")]
        self.assertIn("## What happens", b1["fields"]["Microsoft.VSTS.TCM.ReproSteps"])  # a Bug shows Repro Steps
        g1 = self.fake.items[self.wid("G-1")]
        self.assertEqual(FakeAzure.tags(g1), ["backlog", "backlog:G-1", "goal", "type:goal"])
        ext = item(self.data, "S-3")["external"]["azure"]
        self.assertEqual(ext["url"], f"https://dev.azure.com/acme/close/_workitems/edit/{ext['id']}")
        self.assertEqual(ext["milestone"], "PI 27.1 - pilot UK01")
        self.assertTrue(ext["synced_at"] and ext["hash"].startswith("sha256:") and ext["fingerprint"].startswith("sha256:"))
        self.assertNotIn("github", item(self.data, "S-3")["external"])
        errors, _ = backlog.validate(self.data)
        self.assertEqual(errors, [])

    def test_w17_3_replan_after_apply_prints_nothing_to_do(self):
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])
        path = Path(self.base, "backlog.json")
        path.write_text(json.dumps(self.data))
        code, out, _ = run_main(["azure", "plan", str(path), "--org", "acme", "--project", "close"], azure, self.fake.call)
        self.assertEqual((code, out), (0, "plan: nothing to do\n"))

    def test_w17_4_a_stale_digest_refuses_with_no_writes(self):
        digest = sync.plan_digest(sync.plan_tracker(self.data, self.base, self.az), self.az.target)
        item(self.data, "S-2")["title"] = "Changed after the plan was approved"
        with self.assertRaisesRegex(RuntimeError, "the plan changed since it was approved"):
            sync.apply_tracker(self.data, self.base, self.az, expect=digest)
        self.assertEqual(self.fake.writes, 0)
        self.assertEqual(self.fake.items, {})

    def test_w17_4_cli_apply_needs_expect_and_refuses_a_stale_one(self):
        path = Path(self.base, "backlog.json")
        path.write_text(json.dumps(self.data))
        args = ["azure", "apply", str(path), "--org", "acme", "--project", "close"]
        code, _, err = run_main(args, azure, self.fake.call)
        self.assertEqual((code, err.strip()), (2, "error: apply needs --expect DIGEST from a plan the user approved; run plan first"))
        code, _, err = run_main(args + ["--expect", "000000000000"], azure, self.fake.call)
        self.assertEqual(code, 2)
        self.assertIn("the plan changed since it was approved", err)
        self.assertEqual(self.fake.writes, 0)

    def test_w17_5_a_title_edited_in_azure_boards_is_a_conflict_not_overwritten(self):
        sync.apply_tracker(self.data, self.base, self.az)
        s2 = self.fake.items[self.wid("S-2")]
        s2["fields"]["System.Title"] = "[S-2] Renamed in Azure Boards"
        item(self.data, "S-2")["title"] = "Nightly job posts single-match bank lines"
        actions = [a for a in sync.plan_tracker(self.data, self.base, self.az) if a.get("id") == "S-2"]
        self.assertEqual([a["do"] for a in actions], ["conflict"])
        self.assertIn("title or body edited in Azure Boards since the last sync", actions[0]["why"])
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertEqual(self.fake.items[self.wid("S-2")]["fields"]["System.Title"], "[S-2] Renamed in Azure Boards")
        forced = [a["do"] for a in sync.plan_tracker(self.data, self.base, self.az, overwrite=("S-2",)) if a.get("id") == "S-2"]
        self.assertEqual(forced, ["update"])

    def test_w17_5_tag_and_iteration_edits_and_moved_parents_are_conflicts(self):
        sync.apply_tracker(self.data, self.base, self.az)
        s3 = self.fake.items[self.wid("S-3")]
        s3["fields"]["System.Tags"] = s3["fields"]["System.Tags"].replace("priority:must", "priority:could")
        self.fake.items[self.wid("S-4")]["fields"]["System.IterationPath"] = "close"
        self.fake.items[self.wid("S-5")]["relations"][0]["url"] = f"https://dev.azure.com/acme/_apis/wit/workItems/{self.wid('F-1')}"
        plan = sync.plan_tracker(self.data, self.base, self.az)
        self.assertEqual({a["id"]: a["do"] for a in plan}, {"S-3": "conflict", "S-4": "conflict", "S-5": "conflict"})

    def test_w17_5_removed_identity_tag_never_creates_a_duplicate(self):
        sync.apply_tracker(self.data, self.base, self.az)
        s2 = self.fake.items[self.wid("S-2")]
        s2["fields"]["System.Tags"] = s2["fields"]["System.Tags"].replace("backlog:S-2; ", "")
        self.assertEqual([a["do"] for a in sync.plan_tracker(self.data, self.base, self.az) if a.get("id") == "S-2"], ["conflict"])
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertEqual(len(self.fake.items), 13)

    def test_lost_sync_records_rebind_by_identity_tag(self):
        sync.apply_tracker(self.data, self.base, self.az)
        fresh = example()
        self.assertEqual({a["do"] for a in sync.plan_tracker(fresh, self.base, self.az)}, {"record"})
        sync.apply_tracker(fresh, self.base, self.az)
        self.assertEqual((len(self.fake.items), sync.plan_tracker(fresh, self.base, self.az)), (13, []))


class AzurePull(AzureCase):
    def setUp(self):
        super().setUp()
        sync.apply_tracker(self.data, self.base, self.az)

    def test_w17_6_approve_from_a_listed_approver_is_recorded_others_are_feedback(self):
        self.fake.comment(self.wid("I-1"), "Priya.Raman@acme.example", "<div>/approve</div><div>Looks right.</div>")
        self.fake.comment(self.wid("F-2"), "intern@acme.example", "<p>/approve</p>")
        self.fake.comment(self.wid("F-2"), TOM_AZ, "<div>Can we start in week 2?</div>")
        before = len(self.data["feedback"])
        report = sync.pull_tracker(self.data, self.az)
        self.assertEqual(report["approvals"], ["I-1 by Priya.Raman@acme.example"])
        approval = item(self.data, "I-1")["approvals"][-1]
        self.assertEqual((approval["tracker"], approval["by"]), ("azure", PRIYA_AZ))
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "I-1"), tracker="azure", base=self.base), "approved")
        new = [(f["id"], f["feature"], f["from"], f["summary"]) for f in self.data["feedback"][before:]]
        self.assertEqual(new, [("FB-3", "F-2", "intern@acme.example", "/approve"),
                               ("FB-4", "F-2", TOM_AZ, "Can we start in week 2?")])
        self.assertEqual(report["ignored"], ["/approve on F-2 by intern@acme.example, who is not an approver; treated as a comment"])
        sync.pull_tracker(self.data, self.az)
        self.assertEqual(len(self.data["feedback"]), before + 2)  # pulling twice adds nothing

    def test_w17_7_a_story_comment_is_feedback_on_its_feature(self):
        self.fake.comment(self.wid("S-3"), TOM_AZ, "<div>Can the report also show the supplier name?</div>")
        self.fake.comment(self.wid("G-1"), TOM_AZ, "<div>Is 3 days realistic?</div>")
        self.fake.comment(self.wid("S-3"), PRIYA_AZ, "<div>Thanks, logged.</div>")  # the planner's own comment
        self.fake.items[self.wid("S-4")]["fields"]["System.State"] = "Closed"
        report = sync.pull_tracker(self.data, self.az)
        fb = self.data["feedback"][-1]
        self.assertEqual((fb["feature"], fb["from"], fb["summary"]), ("F-1", TOM_AZ, "Can the report also show the supplier name?"))
        self.assertEqual(report["feedback"], ["FB-3 on F-1 from tom.okafor@acme.example"])
        self.assertEqual([t["item"] for t in report["triage"]], ["G-1"])
        self.assertEqual(report["closed_without_delivery"], ["S-4"])
        self.assertEqual(item(self.data, "S-4")["external"]["azure"]["state"], "closed")

    def test_report_post_creates_one_status_comment_then_updates_it(self):
        first = sync.post_status(self.data, self.base, self.az, "2027-01-20")
        second = sync.post_status(self.data, self.base, self.az, "2027-01-21")
        self.assertEqual(first, second)
        comments = self.fake.comments[self.wid("I-1")]
        self.assertEqual(len(comments), 1)
        self.assertIn("updated 2027-01-21", comments[0]["text"])
        self.assertIn("Tom Okafor (Group Controller) on I-1", comments[0]["text"])  # names approvers by their azure handle
        self.assertEqual(sync.pull_tracker(self.data, self.az)["feedback"], [])


# Linear fake -----------------------------------------------------------------------------------

class FakeLinear:
    """Just enough of Linear's GraphQL API for team FIN and project 'Month-end close'.

    Like the real editor, it rewrites '- ' bullets as '* ', so a stored description differs from
    the Markdown that was sent."""

    def __init__(self, me=("priya", "priya.raman@acme.example"), labels=("backlog",), project_teams=("team-1",)):
        self.issues, self.labels, self.milestones, self.comments = {}, {f"lab-{n}": l for n, l in enumerate(labels)}, {}, {}
        self.writes, self.clock, self.me, self.project_teams = 0, Clock(), me, list(project_teams)

    def call(self, query, variables):
        op = re.match(r"\s*(query|mutation) (\w+)", query).group(2)
        v = variables
        if query.lstrip().startswith("mutation"):
            self.writes += 1
        if op == "Setup":
            return {"teams": {"nodes": [{"id": "team-1", "key": v["team"]}]},
                    "projects": {"nodes": [{"id": "proj-1", "name": v["project"],
                                            "teams": {"nodes": [{"id": k} for k in self.project_teams]}}]}}
        if op == "Milestones":
            return {"project": {"projectMilestones": {"nodes": [{"id": k, "name": n} for k, n in self.milestones.items()]}}}
        if op == "Labels":
            return {"issueLabels": {"nodes": [{"id": k, "name": n} for k, n in self.labels.items()],
                                    "pageInfo": {"hasNextPage": False, "endCursor": None}}}
        if op == "Issues":  # like Linear, archived issues are listed only with includeArchived
            shown = [k for k in self.issues if "includeArchived: true" in query or not self.issues[k].get("archivedAt")]
            return {"project": {"issues": {"nodes": [self.view(k) for k in shown],
                                           "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if op == "Issue":
            if v["id"] not in self.issues:
                raise RuntimeError("Linear GraphQL: Entity not found: Issue")
            return {"issue": self.view(v["id"])}
        if op == "Viewer":
            return {"viewer": {"displayName": self.me[0], "email": self.me[1]}}
        if op == "Comments":
            return {"issue": {"comments": {"nodes": copy.deepcopy(self.comments.get(v["id"], [])),
                                           "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if op == "LabelCreate":
            key = f"lab-{len(self.labels)}"
            self.labels[key] = v["input"]["name"]
            return {"issueLabelCreate": {"issueLabel": {"id": key, "name": v["input"]["name"]}}}
        if op == "MilestoneCreate":
            key = f"ms-{len(self.milestones) + 1}"
            self.milestones[key] = v["input"]["name"]
            self.targets = getattr(self, "targets", {}) | {v["input"]["name"]: v["input"].get("targetDate")}
            return {"projectMilestoneCreate": {"projectMilestone": {"id": key, "name": v["input"]["name"]}}}
        if op == "IssueCreate":
            key = f"iss-{len(self.issues) + 1}"
            assert (v["input"]["teamId"], v["input"]["projectId"]) == ("team-1", "proj-1")
            self.issues[key] = {"identifier": f"FIN-{len(self.issues) + 1}", "parent": None, "state": "unstarted",
                                "labels": [], "milestone": None}
            return {"issueCreate": {"issue": self.update(key, v["input"])}}
        if op == "IssueUpdate":  # like Linear, a new parentId replaces the present parent
            return {"issueUpdate": {"issue": self.update(v["id"], v["input"])}}
        if op == "CommentCreate":
            return {"commentCreate": {"comment": self.comment(v["input"]["issueId"], self.me, v["input"]["body"])}}
        if op == "CommentUpdate":
            comment = next(c for cs in self.comments.values() for c in cs if c["id"] == v["id"])
            comment["body"] = v["input"]["body"]
            return {"commentUpdate": {"comment": comment}}
        raise AssertionError(f"unexpected operation {op}")

    def update(self, key, data):
        issue = self.issues[key]
        for field, name in (("title", "title"), ("description", "description"), ("parentId", "parent"),
                            ("labelIds", "labels"), ("projectMilestoneId", "milestone")):
            if field in data:
                issue[name] = data[field]
        if "description" in data:
            issue["description"] = re.sub(r"(?m)^- ", "* ", data["description"])
        issue["updatedAt"] = self.clock.now()
        return self.view(key)

    def view(self, key):
        i = self.issues[key]
        return {"id": key, "identifier": i["identifier"], "url": f"https://linear.app/acme/issue/{i['identifier']}",
                "title": i["title"], "description": i["description"], "updatedAt": i["updatedAt"], "archivedAt": i.get("archivedAt"),
                "state": {"type": i["state"]}, "parent": {"id": i["parent"]} if i["parent"] else None,
                "labels": {"nodes": [{"id": k, "name": self.labels[k]} for k in i["labels"]]},
                "projectMilestone": {"id": i["milestone"], "name": self.milestones[i["milestone"]]} if i["milestone"] else None}

    def comment(self, key, who, body, bot=False, at=None):
        mine = self.comments.setdefault(key, [])
        cid = f"c-{sum(len(c) for c in self.comments.values()) + 1}"
        comment = {"id": cid, "body": body, "createdAt": at or self.clock.now(), "url": f"https://linear.app/acme/issue/x#comment-{cid}",
                   "user": None if bot else {"displayName": who[0], "email": who[1]}, "botActor": {"name": "GitHub"} if bot else None}
        mine.append(comment)
        return comment

    def label_names(self, key):
        return sorted(self.labels[k] for k in self.issues[key]["labels"])


class LinearCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        Path(self.base, "prd.md").write_text((ROOT / "skills/planning/reference/worked-example/prd.md").read_text())
        self.fake = FakeLinear()
        self.ln = linear.Linear("FIN", "Month-end close", call=self.fake.call)
        self.data = example()

    def tearDown(self):
        self.tmp.cleanup()

    def key(self, iid):
        return item(self.data, iid)["external"]["linear"]["id"]


class LinearPlan(LinearCase):
    def test_w18_1_plan_creates_one_issue_per_item_with_type_labels_sub_issues_and_milestones(self):
        actions = sync.plan_tracker(self.data, self.base, self.ln)
        self.assertEqual(actions[0]["do"], "create labels")
        self.assertNotIn("backlog", actions[0]["labels"])  # the team already has it
        self.assertTrue({"type:initiative", "type:goal", "type:feature", "type:story", "type:bug"} <= set(actions[0]["labels"]))
        self.assertEqual([(a["do"], a["title"], a["due"]) for a in actions[1:3]],
                         [("create milestone", "PI 27.1: pilot UK01", "2027-02-26"),
                          ("create milestone", "PI 27.2: all EU entities", "2027-05-28")])
        creates = {a["id"]: a for a in actions if a["do"] == "create"}
        self.assertEqual(list(creates), ORDERED)
        for iid, a in creates.items():
            self.assertIn(f"type:{item(self.data, iid)['type']}", a["labels"])
            self.assertIn("backlog", a["labels"])
            self.assertTrue(a["body"].endswith(f"Backlog ID: {iid}"), iid)
        self.assertEqual((creates["S-3"]["milestone"], creates["S-6"]["milestone"], creates["G-1"]["milestone"]),
                         ("PI 27.1: pilot UK01", "PI 27.2: all EU entities", None))
        links = [(a["id"], a["parent"], a.get("link")) for a in actions if a["do"] == "link"]
        self.assertEqual(links, [(i, PARENTS[i], None) for i in ORDERED[1:]])  # printed as sub-issues
        self.assertEqual(len(actions), 1 + 2 + 13 + 12)
        self.assertEqual(self.fake.writes, 0)


class LinearApply(LinearCase):
    def test_w18_2_apply_with_the_right_digest_creates_links_and_records_ids(self):
        digest = sync.plan_digest(sync.plan_tracker(self.data, self.base, self.ln), self.ln.target)
        sync.apply_tracker(self.data, self.base, self.ln, expect=digest)
        self.assertEqual(len(self.fake.issues), 13)
        for iid, parent in PARENTS.items():
            self.assertEqual(self.fake.issues[self.key(iid)]["parent"], self.key(parent), iid)
        s3 = self.fake.issues[self.key("S-3")]
        self.assertEqual(self.fake.milestones[s3["milestone"]], "PI 27.1: pilot UK01")
        self.assertEqual(self.fake.targets, {"PI 27.1: pilot UK01": "2027-02-26", "PI 27.2: all EU entities": "2027-05-28"})
        self.assertEqual(self.fake.label_names(self.key("B-1")),
                         ["backlog", "priority:must", "size:S", "status:ready", "type:bug", "urgency:critical", "work:automate"])
        ext = item(self.data, "S-3")["external"]["linear"]
        self.assertEqual((ext["id"], ext["url"]), (self.key("S-3"), f"https://linear.app/acme/issue/{s3['identifier']}"))
        self.assertNotEqual(ext["hash"], ext["sent"])  # Linear rewrote the bullets; both are kept
        errors, _ = backlog.validate(self.data)
        self.assertEqual(errors, [])

    def test_w18_3_replan_after_apply_prints_nothing_to_do(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.ln), [])
        path = Path(self.base, "backlog.json")
        path.write_text(json.dumps(self.data))
        code, out, _ = run_main(["linear", "plan", str(path), "--team", "FIN", "--project", "Month-end close"], linear, self.fake.call)
        self.assertEqual((code, out), (0, "plan: nothing to do\n"))

    def test_w18_4_a_stale_digest_refuses_with_no_writes(self):
        digest = sync.plan_digest(sync.plan_tracker(self.data, self.base, self.ln), self.ln.target)
        item(self.data, "S-2")["title"] = "Changed after the plan was approved"
        with self.assertRaisesRegex(RuntimeError, "the plan changed since it was approved"):
            sync.apply_tracker(self.data, self.base, self.ln, expect=digest)
        self.assertEqual((self.fake.writes, self.fake.issues), (0, {}))

    def test_w18_5_a_title_edited_in_linear_is_a_conflict_not_overwritten(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        self.fake.issues[self.key("S-2")]["title"] = "[S-2] Renamed in Linear"
        item(self.data, "S-2")["title"] = "Nightly job posts single-match bank lines"
        actions = [a for a in sync.plan_tracker(self.data, self.base, self.ln) if a.get("id") == "S-2"]
        self.assertEqual([a["do"] for a in actions], ["conflict"])
        self.assertIn("title or body edited in Linear since the last sync", actions[0]["why"])
        sync.apply_tracker(self.data, self.base, self.ln)
        self.assertEqual(self.fake.issues[self.key("S-2")]["title"], "[S-2] Renamed in Linear")
        forced = [a["do"] for a in sync.plan_tracker(self.data, self.base, self.ln, overwrite=("S-2",)) if a.get("id") == "S-2"]
        self.assertEqual(forced, ["update"])

    def test_w18_5_label_milestone_and_parent_edits_are_conflicts(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        self.fake.issues[self.key("S-3")]["labels"].pop()
        self.fake.issues[self.key("S-4")]["milestone"] = None
        self.fake.issues[self.key("S-5")]["parent"] = self.key("F-1")
        plan = sync.plan_tracker(self.data, self.base, self.ln)
        self.assertEqual({a["id"]: a["do"] for a in plan}, {"S-3": "conflict", "S-4": "conflict", "S-5": "conflict"})


class LinearPull(LinearCase):
    def setUp(self):
        super().setUp()
        sync.apply_tracker(self.data, self.base, self.ln)

    def test_w18_6_approve_from_a_listed_approver_is_recorded_others_are_feedback(self):
        self.fake.comment(self.key("F-1"), ("Tom", TOM_AZ.upper()), "/approve\nGood to go.")  # matched by email
        self.fake.comment(self.key("I-1"), ("priya", "p@elsewhere.example"), "/approve")  # matched by display name
        self.fake.comment(self.key("F-2"), ("intern", "intern@acme.example"), "/approve")
        before = len(self.data["feedback"])
        report = sync.pull_tracker(self.data, self.ln)
        self.assertEqual(sorted(report["approvals"]), ["F-1 by tom.okafor@acme.example", "I-1 by priya"])
        self.assertEqual([(a["tracker"], a["by"]) for a in item(self.data, "F-1")["approvals"] if a["tracker"] == "linear"],
                         [("linear", TOM_AZ)])
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), tracker="linear", base=self.base), "approved")
        new = [(f["feature"], f["from"], f["summary"]) for f in self.data["feedback"][before:]]
        self.assertEqual(new, [("F-2", "intern <intern@acme.example>", "/approve")])  # not a handle: name and email
        sync.pull_tracker(self.data, self.ln)
        self.assertEqual(len(self.data["feedback"]), before + 1)

    def test_w18_7_a_story_comment_is_feedback_on_its_feature(self):
        self.fake.comment(self.key("S-5"), ("tom", TOM_AZ), "Does this cover DE01?")
        self.fake.comment(self.key("S-5"), ("", ""), "Linked a pull request", bot=True)
        self.fake.issues[self.key("B-1")]["state"] = "completed"
        report = sync.pull_tracker(self.data, self.ln)
        self.assertEqual(report["feedback"], [f"FB-3 on F-2 from {TOM_AZ}"])
        self.assertEqual(self.data["feedback"][-1]["source"], "https://linear.app/acme/issue/x#comment-c-1")
        self.assertEqual(report["closed_without_delivery"], ["B-1"])

    def test_report_post_creates_one_status_comment_then_updates_it(self):
        sync.post_status(self.data, self.base, self.ln, "2027-01-20")
        sync.post_status(self.data, self.base, self.ln, "2027-01-21")
        comments = self.fake.comments[self.key("I-1")]
        self.assertEqual(len(comments), 1)
        self.assertIn("updated 2027-01-21", comments[0]["body"])
        self.assertEqual(sync.pull_tracker(self.data, self.ln)["feedback"], [])


# Review round 1 (reviews/m4/W17W18-r1.md) ------------------------------------------------------

class ReviewAzure(AzureCase):
    def test_m2_tags_stored_in_another_case_are_not_a_conflict(self):
        self.fake.tag_case = {"backlog": "Backlog", "priority:must": "Priority:Must"}  # tags the organisation already had
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertIn("Priority:Must", FakeAzure.tags(self.fake.items[self.wid("S-3")]))
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])

    def test_m3_the_digest_binds_organisation_project_and_process(self):
        test_fake = FakeAzure(project="close-test")
        test_project = azure.Azure("acme", "close-test", call=test_fake.call)
        real, trial = sync.plan_tracker(self.data, self.base, self.az), sync.plan_tracker(self.data, self.base, test_project)
        self.assertEqual(real, trial)  # the same actions ...
        trial_digest = sync.plan_digest(trial, test_project.target)
        self.assertNotEqual(sync.plan_digest(real, self.az.target), trial_digest)  # ... but not the same approval
        self.assertNotEqual(sync.plan_digest(real, self.az.target), sync.plan_digest(real, azure.Azure("acme", "close", "scrum", call=self.fake.call).target))
        with self.assertRaisesRegex(RuntimeError, "the plan changed since it was approved"):
            sync.apply_tracker(self.data, self.base, self.az, expect=trial_digest)
        self.assertEqual(self.fake.writes, 0)

    def test_n1_a_parent_changed_in_backlog_json_is_relinked_not_a_conflict(self):
        sync.apply_tracker(self.data, self.base, self.az)
        item(self.data, "S-3")["parent"] = "F-2"
        plan = [a for a in sync.plan_tracker(self.data, self.base, self.az) if a.get("id") == "S-3"]
        self.assertEqual([(a["do"], a.get("parent"), a.get("relink")) for a in plan], [("link", "F-2", True)])
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertEqual(self.fake.parent_of(self.wid("S-3")), self.wid("F-2"))
        self.assertEqual(len(self.fake.items[self.wid("S-3")]["relations"]), 1)  # the old parent link was removed
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])

    def test_n1_a_parent_changed_in_azure_boards_is_a_conflict_until_overwrite(self):
        sync.apply_tracker(self.data, self.base, self.az)
        self.fake.items[self.wid("S-5")]["relations"][0]["url"] = f"https://dev.azure.com/acme/_apis/wit/workItems/{self.wid('F-1')}"
        plan = sync.plan_tracker(self.data, self.base, self.az)
        self.assertEqual([(a["do"], a["id"]) for a in plan], [("conflict", "S-5")])
        self.assertIn("moved in Azure Boards", plan[0]["why"])
        sync.apply_tracker(self.data, self.base, self.az, overwrite=("S-5",))
        self.assertEqual(self.fake.parent_of(self.wid("S-5")), self.wid("F-2"))
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])

    def test_n3_since_leaves_out_older_comments_without_losing_them(self):
        sync.apply_tracker(self.data, self.base, self.az)
        self.fake.comment(self.wid("S-3"), TOM_AZ, "<div>Old point</div>", at="2027-01-05T09:00:00Z")
        self.fake.comment(self.wid("S-2"), TOM_AZ, "<div>New point</div>", at="2027-01-12T09:00:00Z")
        self.assertEqual([f["summary"] for f in self.data["feedback"][2:]], [])
        sync.pull_tracker(self.data, self.az, since="2027-01-12")
        self.assertEqual([f["summary"] for f in self.data["feedback"][2:]], ["New point"])
        sync.pull_tracker(self.data, self.az)
        self.assertEqual([f["summary"] for f in self.data["feedback"][2:]], ["New point", "Old point"])

    def test_n3_only_our_own_status_comment_is_skipped_a_quote_of_it_is_filed(self):
        sync.apply_tracker(self.data, self.base, self.az)
        sync.post_status(self.data, self.base, self.az, "2027-01-20")
        quote = "<div>About the line 'Status from the planning backlog': the dates look wrong.</div>"
        self.fake.comment(self.wid("F-1"), TOM_AZ, quote)
        self.fake.comment(self.wid("F-2"), TOM_AZ, "<div>_Status from the planning backlog_ is mine too</div>")
        report = sync.pull_tracker(self.data, self.az)
        self.assertEqual(report["feedback"], ["FB-3 on F-1 from tom.okafor@acme.example", "FB-4 on F-2 from tom.okafor@acme.example"])
        self.assertEqual(report["triage"], [])  # our own status comment on I-1 is not triage

    def test_n5_an_iteration_with_the_same_name_in_another_case_is_reused(self):
        self.fake.iterations.append({"name": "pi 27.1 - pilot uk01"})
        plan = sync.plan_tracker(self.data, self.base, self.az)
        self.assertEqual([a["title"] for a in plan if a["do"] == "create milestone"], ["PI 27.2 - all EU entities"])
        self.assertEqual({a["milestone"] for a in plan if a["do"] == "create" and a["id"] in ("F-1", "S-3")}, {"pi 27.1 - pilot uk01"})
        sync.apply_tracker(self.data, self.base, self.az)
        self.assertEqual(self.fake.items[self.wid("S-3")]["fields"]["System.IterationPath"], "close\\pi 27.1 - pilot uk01")
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])

    def test_r1_me_is_read_from_connection_data(self):
        self.assertEqual(self.az.me({}), PRIYA_AZ)
        self.assertEqual(self.fake.profile_calls, 0)

    def test_r1_pull_and_status_never_call_profiles_which_refuse_a_pat(self):
        sync.apply_tracker(self.data, self.base, self.az)
        self.fake.comment(self.wid("S-3"), TOM_AZ, "<div>Please add the supplier name</div>")
        self.fake.comment(self.wid("S-3"), PRIYA_AZ, "<div>Thanks, logged.</div>")  # our own: skipped
        self.assertEqual(sync.pull_tracker(self.data, self.az)["feedback"], ["FB-3 on F-1 from tom.okafor@acme.example"])
        sync.post_status(self.data, self.base, self.az, "2027-01-20")
        sync.post_status(self.data, self.base, self.az, "2027-01-21")
        self.assertEqual(len(self.fake.comments[self.wid("I-1")]), 1)
        self.assertEqual(self.fake.profile_calls, 0)

    def test_r1_a_failed_identity_lookup_is_one_error_line(self):
        sync.apply_tracker(self.data, self.base, self.az)
        path = Path(self.base, "backlog.json")
        path.write_text(json.dumps(self.data))
        for identity, words in (("refused", "HTTP 401"), ("empty", "signed-in user")):
            self.fake.identity = identity
            code, out, err = run_main(["azure", "pull", str(path), "--org", "acme", "--project", "close"], azure, self.fake.call)
            self.assertEqual((code, out), (2, ""), identity)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertTrue(err.startswith("error: ") and words in err, err)

    def test_relink_patch_tests_the_revision_it_read(self):
        sync.apply_tracker(self.data, self.base, self.az)
        rev = self.fake.items[self.wid("S-3")]["rev"]
        item(self.data, "S-3")["parent"] = "F-2"
        sync.apply_tracker(self.data, self.base, self.az)
        relink = [ops for wid, ops in self.fake.patches if wid == self.wid("S-3") and any(o["op"] == "remove" for o in ops)]
        self.assertEqual(relink[0][0], {"op": "test", "path": "/rev", "value": rev})
        self.assertEqual(self.fake.parent_of(self.wid("S-3")), self.wid("F-2"))

    def test_relink_refuses_when_the_work_item_changed_after_the_read(self):
        sync.apply_tracker(self.data, self.base, self.az)
        relations = copy.deepcopy(self.fake.items[self.wid("S-3")]["relations"])

        def someone_edits(wid):
            self.fake.items[wid]["rev"] += 1
        self.fake.after_get = someone_edits
        item(self.data, "S-3")["parent"] = "F-2"
        done = sync.apply_tracker(self.data, self.base, self.az)
        self.fake.after_get = None
        self.assertEqual([(a["do"], a["id"]) for a in done if a["id"] == "S-3"], [("conflict", "S-3")])
        self.assertIn("test /rev failed", [a for a in done if a["id"] == "S-3"][0]["why"])
        self.assertEqual(self.fake.items[self.wid("S-3")]["relations"], relations)  # nothing removed

    def test_f3_an_approvers_approve_on_a_story_is_feedback_not_a_sign_off(self):
        sync.apply_tracker(self.data, self.base, self.az)
        self.fake.comment(self.wid("S-3"), TOM_AZ, "<div>/approve</div>")
        report = sync.pull_tracker(self.data, self.az)
        self.assertEqual((report["approvals"], report["feedback"]), ([], ["FB-3 on F-1 from tom.okafor@acme.example"]))
        self.assertFalse([a for i in self.data["items"] for a in i.get("approvals", []) if a["tracker"] == "azure"])
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), tracker="azure", base=self.base), "missing")

    def test_the_backlog_id_tag_is_matched_without_case(self):
        sync.apply_tracker(self.data, self.base, self.az)
        s2 = self.fake.items[self.wid("S-2")]
        s2["fields"]["System.Tags"] = s2["fields"]["System.Tags"].replace("backlog:S-2", "BACKLOG:s-2")
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.az), [])


class ReviewLinear(LinearCase):
    def test_m1_an_archived_issue_counts_as_closed_and_replan_is_empty(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        b1 = self.fake.issues[self.key("B-1")]
        b1["state"], b1["archivedAt"] = "completed", "2027-04-01T00:00:00Z"  # Linear auto-archives closed issues
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.ln), [])
        report = sync.pull_tracker(self.data, self.ln)
        self.assertEqual(report["closed_without_delivery"], ["B-1"])
        self.assertEqual(item(self.data, "B-1")["external"]["linear"]["state"], "closed")
        b1["state"] = "backlog"  # archived but not completed: still closed
        sync.pull_tracker(self.data, self.ln)
        self.assertEqual(item(self.data, "B-1")["external"]["linear"]["state"], "closed")

    def test_m2_an_existing_label_in_another_case_is_not_a_conflict(self):
        self.fake = FakeLinear(labels=("Backlog", "Type:Story"))
        self.ln = linear.Linear("FIN", "Month-end close", call=self.fake.call)
        plan = sync.plan_tracker(self.data, self.base, self.ln)
        self.assertNotIn("type:story", plan[0]["labels"])
        sync.apply_tracker(self.data, self.base, self.ln)
        self.assertIn("Backlog", self.fake.label_names(self.key("S-3")))
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.ln), [])

    def test_m3_the_digest_binds_team_and_project(self):
        trial = linear.Linear("FIN", "Month-end close (test)", call=FakeLinear().call)
        other_team = linear.Linear("OPS", "Month-end close", call=FakeLinear().call)
        actions = sync.plan_tracker(self.data, self.base, self.ln)
        self.assertEqual(actions, sync.plan_tracker(self.data, self.base, trial))
        digests = {sync.plan_digest(actions, t.target) for t in (self.ln, trial, other_team)}
        self.assertEqual(len(digests), 3)
        with self.assertRaisesRegex(RuntimeError, "the plan changed since it was approved"):
            sync.apply_tracker(self.data, self.base, self.ln, expect=sync.plan_digest(actions, trial.target))
        self.assertEqual(self.fake.writes, 0)

    def test_n1_a_parent_changed_in_backlog_json_is_relinked_not_a_conflict(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        item(self.data, "S-3")["parent"] = "F-2"
        plan = [a for a in sync.plan_tracker(self.data, self.base, self.ln) if a.get("id") == "S-3"]
        self.assertEqual([(a["do"], a.get("parent")) for a in plan], [("link", "F-2")])
        sync.apply_tracker(self.data, self.base, self.ln)
        self.assertEqual(self.fake.issues[self.key("S-3")]["parent"], self.key("F-2"))
        self.assertEqual(sync.plan_tracker(self.data, self.base, self.ln), [])

    def test_n3_since_and_status_filters(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        sync.post_status(self.data, self.base, self.ln, "2027-01-20")
        self.fake.comment(self.key("S-5"), ("tom", TOM_AZ), "Old point", at="2027-01-05T09:00:00Z")
        self.fake.comment(self.key("S-5"), ("tom", TOM_AZ), "Status from the planning backlog says DE01 is late?")
        report = sync.pull_tracker(self.data, self.ln, since="2027-01-08")
        self.assertEqual(report["feedback"], [f"FB-3 on F-2 from {TOM_AZ}"])
        self.assertEqual(self.data["feedback"][-1]["summary"], "Status from the planning backlog says DE01 is late?")
        self.assertEqual(report["triage"], [])

    def test_f1_a_spoofed_display_name_does_not_record_a_sign_off(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        self.fake.comment(self.key("F-1"), (TOM_AZ, "mallory@acme.example"), "/approve")
        self.fake.comment(self.key("F-2"), ("tom", "mallory@acme.example"), "/approve")  # no 'tom' display-name handle either
        report = sync.pull_tracker(self.data, self.ln)
        self.assertEqual(report["approvals"], [])
        self.assertFalse([a for a in item(self.data, "F-1").get("approvals", []) if a["tracker"] == "linear"])
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), tracker="linear", base=self.base), "missing")
        self.assertEqual(report["ignored"], [f"/approve on F-1 by {TOM_AZ} <mallory@acme.example>, who is not an approver; treated as a comment",
                                             "/approve on F-2 by tom <mallory@acme.example>, who is not an approver; treated as a comment"])

    def test_f3_an_approvers_approve_on_a_bug_is_feedback_not_a_sign_off(self):
        sync.apply_tracker(self.data, self.base, self.ln)
        self.fake.comment(self.key("B-1"), ("Tom", TOM_AZ), "/approve")
        report = sync.pull_tracker(self.data, self.ln)
        self.assertEqual((report["approvals"], report["feedback"]), ([], [f"FB-3 on F-1 from {TOM_AZ}"]))
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), tracker="linear", base=self.base), "missing")

    def test_n5_a_project_without_the_team_stops_before_any_write(self):
        self.fake.project_teams = ["team-2"]
        with self.assertRaisesRegex(RuntimeError, "project 'Month-end close' does not include team FIN"):
            sync.apply_tracker(self.data, self.base, self.ln)
        self.assertEqual(self.fake.writes, 0)


class ReviewShared(unittest.TestCase):
    def test_m2_edit_conflict_ignores_label_case_only_for_azure_and_linear(self):
        ext = {"hash": "h", "labels": ["backlog", "type:story"]}
        same = [("labels", ["Backlog", "type:story"], "labels changed")]
        self.assertIsNone(sync.edit_conflict(ext, "h", "h", "a work item", "Azure Boards", same, fold_case=True))
        self.assertEqual(sync.edit_conflict(ext, "h", "h", "an issue", "GitHub", same), "labels changed; merge, or pass --overwrite")  # F4
        changed = [("labels", ["backlog", "type:bug"], "labels changed")]
        self.assertEqual(sync.edit_conflict(ext, "h", "h", "an issue", "Linear", changed, fold_case=True), "labels changed; merge, or pass --overwrite")
        self.assertIsNotNone(sync.edit_conflict({"hash": "h", "milestone": "M1"}, "h", "h", "an issue", "Linear", [("milestone", "m1", "x")], fold_case=True))

    def test_f4_a_github_label_recased_in_github_is_still_a_conflict(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("test_planning_for_f4", ROOT / "tests" / "test_planning.py")
        planning = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(planning)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        Path(tmp.name, "prd.md").write_text((ROOT / "skills/planning/reference/worked-example/prd.md").read_text())
        fake, data = planning.FakeGitHub(), planning.example()
        gh = sync.GitHub("acme/close", call=fake.call)
        sync.apply(data, tmp.name, gh)
        s3 = fake.issues[item(data, "S-3")["external"]["github"]["number"]]
        s3["labels"] = [{"name": "Priority:Must" if l["name"] == "priority:must" else l["name"]} for l in s3["labels"]]
        actions = [a for a in sync.plan(data, tmp.name, gh) if a.get("id") == "S-3"]
        self.assertEqual([a["do"] for a in actions], ["conflict"])
        self.assertIn("labels changed in GitHub since the last sync", actions[0]["why"])

    def test_f1_a_display_name_shaped_like_an_approver_email_does_not_sign_off(self):
        handles = {"priya": "priya", TOM_AZ: TOM_AZ}
        self.assertEqual(linear.who({"displayName": TOM_AZ, "email": "mallory@acme.example"}, handles),
                         f"{TOM_AZ} <mallory@acme.example>")
        self.assertEqual(linear.who({"displayName": "mallory", "email": "priya"}, handles), "mallory <priya>")  # a name handle never matches an email
        self.assertEqual(linear.who({"displayName": "Priya", "email": "p@acme.example"}, handles), "priya")
        self.assertEqual(linear.who({"displayName": "x", "email": TOM_AZ.upper()}, handles), TOM_AZ)

    def secret_run(self, args, variable, value):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, "backlog.json")
        path.write_text(json.dumps(example()))
        env = {k: v for k, v in os.environ.items() if k not in ("AZURE_DEVOPS_EXT_PAT", "LINEAR_API_KEY")}
        env.update({variable: value, "HTTPS_PROXY": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9"})  # nothing may leave
        run = subprocess.run([sys.executable, str(SYNC), args[0], "plan", str(path), *args[1:]], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual((run.returncode, run.stdout), (2, ""), run.stderr)
        self.assertEqual(len(run.stderr.splitlines()), 1, run.stderr)
        self.assertIn(variable, run.stderr)
        self.assertIn("control character", run.stderr)
        return run.stdout + run.stderr

    def test_f2_a_token_with_a_control_character_is_refused_and_never_printed(self):
        out = self.secret_run(["linear", "--team", "FIN", "--project", "Month-end close"], "LINEAR_API_KEY", "lin_api_SECRETPART1\nSECRETPART2")
        out += self.secret_run(["azure", "--org", "acme", "--project", "close"], "AZURE_DEVOPS_EXT_PAT", "patSECRETPART3\tSECRETPART4")
        out += self.secret_run(["linear", "--team", "FIN", "--project", "Month-end close"], "LINEAR_API_KEY", "lin_api_SECRETPART5\x1b[31m")
        for part in ("SECRETPART", "lin_api_", "patSECRET"):
            self.assertNotIn(part, out)
        with self.assertRaises(RuntimeError) as caught, mock.patch.dict(os.environ, {"LINEAR_API_KEY": "abc\rdef"}):
            sync.secret("LINEAR_API_KEY", "a key")
        self.assertNotIn("abc", str(caught.exception))

    def test_d16_a_token_pasted_with_a_trailing_newline_is_used_without_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, "backlog.json")
        path.write_text(json.dumps(example()))
        Path(tmp.name, "prd.md").write_text("**R-1** x")
        cases = ((azure, FakeAzure, ["azure", "plan", str(path), "--org", "acme", "--project", "close"], "AZURE_DEVOPS_EXT_PAT", "patSECRET"),
                 (linear, FakeLinear, ["linear", "plan", str(path), "--team", "FIN", "--project", "Month-end close"], "LINEAR_API_KEY", "lin_api_SECRET"))
        for module, fake_class, args, variable, token in cases:
            for pasted in (token + "\n", token + "\r\n"):
                seen, out, err, fake = [], io.StringIO(), io.StringIO(), fake_class()
                with mock.patch.object(module, "transport", lambda secret: seen.append(secret) or fake.call), \
                        mock.patch.dict(os.environ, {variable: pasted}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = sync.main(args)
                self.assertEqual((code, err.getvalue()), (0, ""), repr(pasted))
                self.assertEqual(seen, [token], repr(pasted))  # the adapter gets the token without the newline
                self.assertNotIn(token, out.getvalue())

    def test_d16_line_breaks_inside_del_nel_and_line_separator_are_refused_in_one_line(self):
        linear_args = ["linear", "--team", "FIN", "--project", "Month-end close"]
        azure_args = ["azure", "--org", "acme", "--project", "close"]
        values = ("lin_api_SECRETPART1\nSECRETPART2",   # a line break inside
                  "lin_api_SECRETPART1\rSECRETPART2",   # a carriage return inside
                  "lin_api_SECRETPART1\x7fSECRETPART2",  # DEL
                  "lin_api_SECRETPART1\x85SECRETPART2",  # U+0085 next line (NEL)
                  "lin_api_SECRETPART1\u2028SECRETPART2",  # U+2028 line separator
                  "lin_api_SECRETPART1\r\n\r\n")         # only one trailing newline is forgiven
        out = ""
        for value in values:
            out += self.secret_run(linear_args, "LINEAR_API_KEY", value)
            out += self.secret_run(azure_args, "AZURE_DEVOPS_EXT_PAT", value.replace("lin_api_", "pat"))
        for part in ("SECRETPART", "lin_api_", "patSECRET", "Traceback"):
            self.assertNotIn(part, out)

    def test_d19_a_non_ascii_token_is_refused_in_one_line(self):
        linear_args = ["linear", "--team", "FIN", "--project", "Month-end close"]
        azure_args = ["azure", "--org", "acme", "--project", "close"]
        values = ("lin_api_SECRETPART1\u20acSECRETPART2",   # euro sign: not Latin-1, crashed the Linear header
                  "lin_api_SECRETPART1\u00e9SECRETPART2",   # e acute: Latin-1, but not ASCII
                  "lin_api_SECRETPART1\u00a0SECRETPART2",   # no-break space
                  "lin_api_SECRETPART1\u201cSECRETPART2")   # a curly quote, as editors paste
        out = ""
        for value in values:
            for args, variable, token in ((linear_args, "LINEAR_API_KEY", value), (azure_args, "AZURE_DEVOPS_EXT_PAT", value.replace("lin_api_", "pat"))):
                text = self.secret_run(args, variable, token)
                self.assertIn("non-ASCII", text)
                out += text
        for part in ("SECRETPART", "lin_api_", "patSECRET", "Traceback", "UnicodeEncodeError"):
            self.assertNotIn(part, out)

    def test_m3_github_digest_is_unchanged_without_a_target(self):
        actions = [{"do": "create", "id": "S-1", "title": "x"}]
        import hashlib
        expected = hashlib.sha256(json.dumps(actions, sort_keys=True).encode()).hexdigest()[:12]  # the old formula
        self.assertEqual(sync.plan_digest(actions), expected)

    def bad_reply(self, module, opener, args):
        fake_call = module.transport("tok-SHOULD-NOT-APPEAR", opener=opener)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, "backlog.json")
        path.write_text(json.dumps(example()))
        code, out, err = run_main([args[0], "plan", str(path), *args[1:]], module, fake_call)
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertTrue(err.startswith("error: ") and "tok-SHOULD-NOT-APPEAR" not in err, err)
        return err

    def test_n2_a_non_json_reply_or_a_timeout_is_one_error_line(self):
        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def html_page(request, timeout=None):
            return Reply(b"<html>Sign in</html>")

        def timeout(request, timeout=None):
            raise TimeoutError("The read operation timed out")

        def no_data(request, timeout=None):
            return Reply(b'{"other": 1}')

        azure_args = ["azure", "--org", "acme", "--project", "close"]
        linear_args = ["linear", "--team", "FIN", "--project", "Month-end close"]
        self.assertIn("not JSON", self.bad_reply(azure, html_page, azure_args))
        self.assertIn("timed out", self.bad_reply(azure, timeout, azure_args))
        self.assertIn("timed out", self.bad_reply(linear, timeout, linear_args))
        self.assertIn("no data", self.bad_reply(linear, no_data, linear_args))


# Credentials, CLI, and skill text --------------------------------------------------------------

def run_main(argv, module, call, token="test-token-not-real"):
    """sync.main with the adapter's transport replaced by a fake; returns (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    env = {"AZURE_DEVOPS_EXT_PAT": token, "LINEAR_API_KEY": token}
    with mock.patch.object(module, "transport", lambda secret: call), mock.patch.dict(os.environ, env), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = sync.main(argv)
    return code, out.getvalue(), err.getvalue()


class Credentials(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name, "backlog.json")
        self.file.write_text(json.dumps(example()))

    def tearDown(self):
        self.tmp.cleanup()

    def missing(self, variable, args):
        env = {k: v for k, v in os.environ.items() if k not in ("AZURE_DEVOPS_EXT_PAT", "LINEAR_API_KEY")}
        run = subprocess.run([sys.executable, str(SYNC), *args], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        lines = run.stderr.splitlines()
        self.assertEqual(len(lines), 1, run.stderr)
        self.assertIn(variable, lines[0])
        return lines[0]

    def test_w17_8_missing_token_is_one_error_naming_the_variable(self):
        line = self.missing("AZURE_DEVOPS_EXT_PAT", ["azure", "plan", str(self.file), "--org", "acme", "--project", "close"])
        self.assertTrue(line.startswith("error: "))

    def test_w18_8_missing_key_is_one_error_naming_the_variable(self):
        line = self.missing("LINEAR_API_KEY", ["linear", "pull", str(self.file), "--team", "FIN", "--project", "Month-end close"])
        self.assertTrue(line.startswith("error: "))

    def opener(self, secret):
        seen = []

        def opener(request, timeout=None):
            seen.append(request)
            raise urllib.error.HTTPError(request.full_url, 401, f"Unauthorized {secret}", {}, io.BytesIO(b'{"message": "bad token"}'))
        return opener, seen

    def test_w17_8_the_token_is_sent_as_basic_auth_and_never_in_errors(self):
        secret = "pat-SECRET-value-1234"
        opener, seen = self.opener(secret)
        call = azure.transport(secret, opener=opener)
        with self.assertRaises(RuntimeError) as caught:
            call("GET", "acme/close/_apis/wit/workitems/1")
        encoded = base64.b64encode(f":{secret}".encode()).decode()
        self.assertEqual(seen[0].get_header("Authorization"), f"Basic {encoded}")
        self.assertEqual(seen[0].full_url, "https://dev.azure.com/acme/close/_apis/wit/workitems/1")
        for text in (str(caught.exception), repr(caught.exception)):
            self.assertNotIn(secret, text)
            self.assertNotIn(encoded, text)
        self.assertIn("401", str(caught.exception))

    def test_w18_8_the_key_is_sent_as_authorization_and_never_in_errors(self):
        secret = "lin_api_SECRET_value_1234"
        opener, seen = self.opener(secret)
        call = linear.transport(secret, opener=opener)
        with self.assertRaises(RuntimeError) as caught:
            call("query Viewer { viewer { email } }", {})
        self.assertEqual(seen[0].get_header("Authorization"), secret)
        self.assertEqual(seen[0].full_url, "https://api.linear.app/graphql")
        self.assertNotIn(secret, str(caught.exception))

    def test_secrets_never_reach_the_output_of_a_full_cli_run(self):
        for module, fake, args in ((azure, FakeAzure(), ["azure", "plan", str(self.file), "--org", "acme", "--project", "close"]),
                                   (linear, FakeLinear(), ["linear", "plan", str(self.file), "--team", "FIN", "--project", "Month-end close"])):
            Path(self.tmp.name, "prd.md").write_text("**R-1** x")
            code, out, err = run_main(args, module, fake.call, token="tok-SHOULD-NOT-APPEAR")
            self.assertEqual(code, 0, err)
            self.assertNotIn("tok-SHOULD-NOT-APPEAR", out + err)


class SkillText(unittest.TestCase):
    def text(self, path):
        return " ".join(path.read_text().split())

    def test_x1_tracker_writes_name_contract_pre_authorization_or_the_exact_plan_digest(self):
        text = self.text(SKILL / "SKILL.md")
        for phrase in ("outside effect", "pre-authorizes that exact effect", "approves the exact plan digest"):
            self.assertTrue(phrase in text, phrase)

    def test_q6_live_use_is_labelled_not_tested_live(self):
        for path in (SKILL / "SKILL.md", SKILL / "reference" / "trackers.md"):
            text = self.text(path)
            self.assertTrue("not tested live" in text, path.name)
            self.assertFalse("planned, not built" in text or "Not built yet" in text, path.name)

    def test_n4_adapter_help_shows_a_command_that_works(self):
        for name in ("azure", "linear"):
            run = subprocess.run([sys.executable, str(SKILL / "scripts" / f"{name}.py"), "--help"], capture_output=True, text=True, timeout=60)
            self.assertIn(f"usage: sync.py {name} ", run.stdout)
            self.assertNotIn(f"{name}.py {name}", run.stdout)

    def test_n7_the_fake_tracker_fixture_runs_plan_from_the_command_line(self):
        env = {k: v for k, v in os.environ.items() if k not in ("AZURE_DEVOPS_EXT_PAT", "LINEAR_API_KEY")}
        for name, kind in (("azure", "create           S-3 User Story"), ("linear", "link             S-3 sub-issue of F-1")):
            run = subprocess.run([sys.executable, str(FIXTURE), name], capture_output=True, text=True, timeout=60, env=env, cwd=ROOT)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn(kind, run.stdout)
            self.assertRegex(run.stdout, r"digest: [0-9a-f]{12}")
        self.assertIn("python3 tests/fixtures/syncing/fake_plan.py azure", self.text(SKILL / "reference" / "trackers.md"))

    def test_adapter_scripts_answer_help(self):
        for name in ("azure.py", "linear.py", "sync.py"):
            run = subprocess.run([sys.executable, str(SKILL / "scripts" / name), "--help"], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, name)


# W19: one signer per feature, and sign-off given outside the tracker ---------------------------

BACKLOG = ROOT / "skills" / "grooming" / "scripts" / "backlog.py"
ELENA = {"name": "Elena Petrova (Treasury lead)", "github": "epetrova"}


def planning_module():
    """tests/test_planning.py, for its GitHub fake (the file itself is left unchanged)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_planning_for_w19", ROOT / "tests" / "test_planning.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OutsideSignOff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        Path(self.base, "prd.md").write_text((ROOT / "skills/planning/reference/worked-example/prd.md").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data, name="backlog.json"):
        path = Path(self.base, name)
        path.write_text(json.dumps(data, indent=2))
        return path

    def record(self, path, *args):
        run = subprocess.run([sys.executable, str(SYNC), "record-signoff", str(path), *args], capture_output=True, text=True, timeout=60)
        return run.returncode, run.stdout, run.stderr

    def status(self, path, iid, tracker="github"):
        run = subprocess.run([sys.executable, str(BACKLOG), "status", str(path), "--tracker", tracker], capture_output=True, text=True, timeout=60)
        return next(line for line in run.stdout.splitlines() if line.split()[1:2] == [iid])

    def signed_line(self, data, tracker="github"):
        body = sync.report_comment(data, self.base, "2027-01-20", tracker)
        return next(l for l in body.splitlines() if l.startswith("- **Not yet signed by:**"))

    def test_w19_1_a_named_signer_is_the_only_one_listed_for_that_feature(self):
        data = example()
        data["approvers"].append(dict(ELENA))  # three approvers
        item(data, "F-1")["notes"] = "Signs off: Elena Petrova, due 2027-02-12."
        line = self.signed_line(data)
        self.assertIn("Elena Petrova (Treasury lead) on I-1, F-1, F-2, F-3", line)
        self.assertIn("Priya Raman (Finance Operations lead) on I-1, F-2, F-3", line)
        self.assertIn("Tom Okafor (Group Controller) on I-1, F-2, F-3", line)
        self.assertIn("Who signs: any listed approver for I-1, F-2, F-3; Elena Petrova (Treasury lead) for F-1.", line)  # in gate order

    def test_w19_1_the_named_signer_does_not_change_the_gate(self):
        data = example()  # Q14: any listed approver still passes the gate
        data["approvers"].append(dict(ELENA))
        item(data, "F-1")["notes"] = "Signs off: Elena Petrova, due 2027-02-12."
        path = self.write(data)
        self.assertEqual(self.record(path, "--item", "F-1", "--by", "Tom Okafor (Group Controller)", "--source", "email, 2027-01-19")[0], 0)
        self.assertIn(" approved ", self.status(path, "F-1"))

    def test_w19_2_a_feature_without_a_signer_note_lists_any_listed_approver(self):
        line = self.signed_line(example())
        self.assertIn("Priya Raman (Finance Operations lead) on I-1, F-1, F-2, F-3", line)
        self.assertIn("Who signs: any listed approver for I-1, F-1, F-2, F-3.", line)

    def test_w19_3_record_signoff_approves_a_never_synced_feature_until_its_content_changes(self):
        path = self.write(json.loads((EXAMPLES / "product.json").read_text()))
        code, out, err = self.record(path, "--item", "F-1", "--by", "Dana Whitfield (VP Product)", "--source", "email from Dana, 2027-01-20")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("F-1", out)
        entry = item(json.loads(path.read_text()), "F-1")["approvals"][-1]
        self.assertEqual((entry["tracker"], entry["by"], entry["source"]), ("written", "Dana Whitfield (VP Product)", "email from Dana, 2027-01-20"))
        self.assertTrue(entry["fingerprint"].startswith("sha256:") and entry["at"])
        line = self.status(path, "F-1")
        self.assertIn(" approved ", line)
        self.assertIn("dwhitfield current", line)
        self.assertIn(" not synced ", self.status(path, "F-2"))  # nothing else changes
        data = json.loads(path.read_text())
        item(data, "S-2")["title"] += " (edited)"  # a story the sign-off covers
        self.write(data)
        line = self.status(path, "F-1")
        self.assertIn(" stale ", line)
        self.assertIn("dwhitfield stale", line)

    def test_w19_3_record_signoff_counts_on_a_synced_backlog_and_goes_stale_on_any_change(self):
        planning = planning_module()
        fake, data = planning.FakeGitHub(), example()
        gh = sync.GitHub("acme/close", call=fake.call)
        sync.apply(data, self.base, gh)
        path = self.write(data)
        self.assertEqual(self.record(path, "--item", "F-2", "--by", "priya raman (finance operations lead)", "--source", "minutes, steering 2027-01-21")[0], 0)
        self.assertIn("priya-r current", self.status(path, "F-2"))
        self.assertIn(" approved ", self.status(path, "F-2"))
        data = json.loads(path.read_text())
        item(data, "S-4")["title"] += " (edited)"  # not synced: the written sign-off is stale anyway
        self.write(data)
        self.assertIn("priya-r stale", self.status(path, "F-2"))
        self.assertNotIn(" approved ", self.status(path, "F-2"))

    def test_w19_3b_an_approved_feature_leaves_the_not_yet_signed_line_whoever_signed(self):
        planning = planning_module()
        fake, data = planning.FakeGitHub(), example()
        gh = sync.GitHub("acme/close", call=fake.call)
        sync.apply(data, self.base, gh)
        fake.comment(item(data, "F-2")["external"]["github"]["number"], "tokafor", "/approve")
        sync.pull(data, gh)  # Tom signs F-2 in GitHub
        path = self.write(data)
        self.assertEqual(self.record(path, "--item", "F-3", "--by", "Priya Raman", "--source", "email, 2027-01-22")[0], 0)  # Priya signs F-3 by email
        line = self.signed_line(json.loads(path.read_text()))
        self.assertIn("Priya Raman (Finance Operations lead) on I-1, F-1;", line)
        self.assertIn("Tom Okafor (Group Controller) on I-1, F-1.", line)
        self.assertNotIn("F-2", line)
        self.assertNotIn("F-3", line)
        self.assertIn("Who signs: any listed approver for I-1, F-1.", line)

    def test_w19_4_a_sign_off_by_someone_not_in_approvers_is_refused(self):
        path = self.write(json.loads((EXAMPLES / "product.json").read_text()))
        before = path.read_text()
        for who in ("Mallory Smith", "dwhitfield"):  # not a listed name; a handle is not a name
            code, out, err = self.record(path, "--item", "F-1", "--by", who, "--source", "email")
            self.assertEqual((code, out), (2, ""), who)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertIn("not a listed approver", err)
        self.assertEqual(path.read_text(), before)

    def test_w19_5_a_sign_off_without_a_source_is_refused(self):
        path = self.write(json.loads((EXAMPLES / "product.json").read_text()))
        before = path.read_text()
        for source in ([], ["--source", ""], ["--source", "   "]):
            code, out, err = self.record(path, "--item", "F-1", "--by", "Dana Whitfield (VP Product)", *source)
            self.assertEqual((code, out), (2, ""), source)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertIn("--source", err)
        self.assertEqual(path.read_text(), before)

    def test_w19_5_only_an_initiative_or_feature_can_be_signed(self):
        path = self.write(json.loads((EXAMPLES / "product.json").read_text()))
        for iid in ("S-1", "F-9"):
            code, _, err = self.record(path, "--item", iid, "--by", "Dana Whitfield (VP Product)", "--source", "email")
            self.assertEqual(code, 2, iid)
            self.assertEqual(len(err.splitlines()), 1, err)

    def test_w19_rule_a_written_entry_by_someone_not_listed_is_ignored_by_the_gate(self):
        # Gate 1 F6, gate 2 F4: a hand-edited entry by "Mallory" with the right fingerprint must not count.
        data = json.loads((EXAMPLES / "product.json").read_text())
        f1 = item(data, "F-1")
        f1["approvals"] = [{"tracker": "written", "by": "Mallory", "at": "2027-01-20T09:00:00Z", "source": "email",
                            "fingerprint": sync.signoff_fingerprint(data, f1, self.base)}]
        state, per = backlog.approval_detail(data, f1, "github", self.base)
        self.assertEqual((state, per), ("not synced", {"dwhitfield": "none", "msilva-cs": "none"}))
        path = self.write(data)
        line = self.status(path, "F-1")
        self.assertIn(" not synced ", line)
        self.assertNotIn("Mallory", line)

    def test_w19_4_a_name_that_matches_two_approvers_is_refused(self):
        # Gate 2 F5: "Tom Okafor" matches both entries, so nobody is recorded; the full name works.
        data = example()
        data["approvers"].append({"name": "Tom Okafor (Treasury)", "github": "tokafor2"})
        path = self.write(data)
        before = path.read_text()
        code, out, err = self.record(path, "--item", "F-1", "--by", "Tom Okafor", "--source", "email")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("matches 2 listed approvers", err)
        self.assertEqual(path.read_text(), before)
        self.assertEqual(self.record(path, "--item", "F-1", "--by", "Tom Okafor (Treasury)", "--source", "email")[0], 0)
        self.assertEqual(item(json.loads(path.read_text()), "F-1")["approvals"][-1]["by"], "Tom Okafor (Treasury)")

    def test_w19_4_an_exact_full_name_wins_over_a_name_without_its_role(self):
        # Gate 2 F17: "Tom Okafor" and "Tom Okafor (CFO)" can both be recorded.
        data = example()
        data["approvers"] = [{"name": "Tom Okafor", "github": "tokafor"}, {"name": "Tom Okafor (CFO)", "github": "tokafor-cfo"}]
        path = self.write(data)
        for by, recorded in (("Tom Okafor", "Tom Okafor"), ("Tom Okafor (CFO)", "Tom Okafor (CFO)"), ("tom  okafor", "Tom Okafor")):
            code, out, err = self.record(path, "--item", "F-1", "--by", by, "--source", f"email {by}")
            self.assertEqual((code, err), (0, ""), by)
            self.assertEqual(item(json.loads(path.read_text()), "F-1")["approvals"][-1]["by"], recorded, by)

    def signs_off_report(self, approvers, note):
        data = example()
        data["approvers"] = approvers
        item(data, "F-1")["notes"] = note
        run = subprocess.run([sys.executable, str(SYNC), "github", "report", str(self.write(data)), "--repo", "acme/close",
                              "--today", "2027-01-20"], capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout, run.stderr

    def test_w19_1_a_signer_note_that_fits_two_approvers_warns_and_shows_any_listed_approver(self):
        # Gate 2 F19: neither Tom is chosen.
        out, err = self.signs_off_report([{"name": "Tom Okafor (Group Controller)", "github": "tokafor"},
                                          {"name": "Tom Okafor (Treasury)", "github": "tokafor2"}], "Signs off: Tom Okafor, due 2027-02-12.")
        self.assertEqual(err.splitlines(), ["warning: F-1 notes say 'Signs off: Tom Okafor', which is not exactly one listed approver; "
                                            "the status comment shows 'any listed approver'"])
        self.assertIn("Who signs: any listed approver for I-1, F-1, F-2, F-3.", out)

    def test_w19_1_a_sentence_after_the_name_is_dropped_to_find_the_signer(self):
        # Gate 1 N4: kills a split that does not retry without the sentence after '. '.
        out, err = self.signs_off_report([dict(ELENA), {"name": "Tom Okafor (Group Controller)", "github": "tokafor"}],
                                         "Signs off: Elena Petrova. Tom approved verbally.")
        self.assertEqual(err, "")
        self.assertIn("Who signs: any listed approver for I-1, F-2, F-3; Elena Petrova (Treasury lead) for F-1.", out)

    def test_w19_1_a_title_before_the_name_is_not_cut_off_at_its_dot(self):
        # Gate 1 N4: kills a split at the first '.': "Dr. Elena Petrova" must not resolve to an approver named "Dr".
        out, err = self.signs_off_report([dict(ELENA), {"name": "Dr (duty reviewer)", "github": "duty"}],
                                         "Signs off: Dr. Elena Petrova")
        self.assertEqual(err.splitlines(), ["warning: F-1 notes say 'Signs off: Dr. Elena Petrova', which is not exactly one listed "
                                            "approver; the status comment shows 'any listed approver'"])
        self.assertIn("Who signs: any listed approver for I-1, F-1, F-2, F-3.", out)
        self.assertNotIn("Dr (duty reviewer) for", out)

    def test_w19_3_a_written_initiative_sign_off_goes_stale_when_the_prd_changes(self):
        # Gate 2 F6: the PRD is part of what an initiative's sign-off covers.
        path = self.write(json.loads((EXAMPLES / "product.json").read_text()))
        self.assertEqual(self.record(path, "--item", "I-1", "--by", "Marco Silva", "--source", "steering minutes, 2027-01-21")[0], 0)
        line = self.status(path, "I-1")
        self.assertIn(" approved ", line)
        self.assertIn("msilva-cs current", line)
        prd = Path(self.base, "prd.md")
        prd.write_text(prd.read_text() + "\nOne more requirement.\n")
        line = self.status(path, "I-1")
        self.assertIn(" stale ", line)
        self.assertIn("msilva-cs stale", line)

    def test_w19_1_a_signer_note_that_matches_no_approver_warns_in_plan_and_report(self):
        # Gate 1 F7: the comment still falls back to "any listed approver", but plan and report say why.
        data = example()
        data["approvers"].append(dict(ELENA))
        item(data, "F-1")["notes"] = "Signs off: Dr. Elena Petrova, due 2027-02-12."
        item(data, "F-2")["notes"] = "Signs off: Elena Petrov."
        item(data, "F-3")["notes"] = "Signs off: Elena Petrova. Sign-off by Tom is not needed."  # matches: no warning
        path = self.write(data)
        expected = ["warning: F-1 notes say 'Signs off: Dr. Elena Petrova', which is not exactly one listed approver; "
                    "the status comment shows 'any listed approver'",
                    "warning: F-2 notes say 'Signs off: Elena Petrov', which is not exactly one listed approver; "
                    "the status comment shows 'any listed approver'"]
        report = subprocess.run([sys.executable, str(SYNC), "github", "report", str(path), "--repo", "acme/close", "--today", "2027-01-20"],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual((report.returncode, report.stderr.splitlines()), (0, expected))
        self.assertIn("Who signs: any listed approver for I-1, F-1, F-2; Elena Petrova (Treasury lead) for F-3.", report.stdout)
        code, out, err = run_main(["azure", "plan", str(path), "--org", "acme", "--project", "close"], azure, FakeAzure().call)
        self.assertEqual((code, err.splitlines()), (0, expected))
        self.assertNotIn("warning", out)
        code, out, err = run_main(["linear", "plan", str(path), "--team", "FIN", "--project", "Month-end close"], linear, FakeLinear().call)
        self.assertEqual((code, err.splitlines()), (0, expected))
        item(data, "F-1")["notes"] = item(data, "F-2")["notes"] = ""
        code, _, err = run_main(["azure", "plan", str(self.write(data)), "--org", "acme", "--project", "close"], azure, FakeAzure().call)
        self.assertEqual((code, err), (0, ""))

    def test_w19_6_the_grooming_examples_stay_valid_with_a_written_sign_off(self):
        for name in ("operations", "product", "marketing"):
            data = json.loads((EXAMPLES / f"{name}.json").read_text())
            self.assertEqual(backlog.validate(data)[0], [], name)
            path = self.write(data, f"{name}.json")
            approver = data["approvers"][0]["name"]
            self.assertEqual(self.record(path, "--item", "F-1", "--by", approver, "--source", "email")[0], 0, name)
            self.assertEqual(backlog.validate(json.loads(path.read_text()))[0], [], name)

    def test_w19_6_the_planning_tests_pass_unchanged(self):
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromModule(planning_module()))
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertGreaterEqual(result.testsRun, 44)


if __name__ == "__main__":
    unittest.main()

"""Tests for the planning skills' scripts: grooming/backlog.py and syncing/sync.py.

Run: python3 -m unittest discover -s tests -p 'test_planning.py' -v
No network calls: GitHub is an in-memory fake behind the same `gh api` paths.
"""

import copy
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "skills" / "grooming" / "reference" / "examples"
sys.path.insert(0, str(ROOT / "skills" / "grooming" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "syncing" / "scripts"))

import backlog  # noqa: E402
import sync  # noqa: E402


def example(name="operations"):
    return json.loads((EXAMPLES / f"{name}.json").read_text())


def item(data, iid):
    return backlog.items_by_id(data)[iid]


def messages(findings, where=None):
    return [m for w, m in findings if where is None or w == where]


class Examples(unittest.TestCase):
    def test_every_example_is_valid(self):
        names = sorted(p.stem for p in EXAMPLES.glob("*.json"))
        self.assertEqual(names, ["marketing", "operations", "product"])
        for name in names:
            errors, _ = backlog.validate(example(name))
            self.assertEqual(errors, [], name)


class DefinitionOfReady(unittest.TestCase):
    def setUp(self):
        self.data = example()
        self.story = item(self.data, "S-3")

    def test_same_finding_is_an_error_when_ready_and_a_warning_when_draft(self):
        self.story["acceptance"][0]["then"] = "the report is produced quickly for 2 teams"
        errors, _ = backlog.validate(self.data)
        self.assertIn("acceptance S-3.1 uses the vague word 'quickly'", messages(errors, "S-3"))
        self.story["status"] = "draft"
        errors, warnings = backlog.validate(self.data)
        self.assertEqual(messages(errors, "S-3"), [])
        self.assertIn("acceptance S-3.1 uses the vague word 'quickly'", messages(warnings, "S-3"))

    def test_a_criterion_id_is_not_a_number(self):
        for ac in self.story["acceptance"]:
            ac["then"] = "every line from S-2.1 is listed"
        errors, _ = backlog.validate(self.data)
        self.assertIn("no acceptance criterion contains a number", messages(errors, "S-3"))

    def test_then_without_any_quantity_fails(self):
        self.story["acceptance"][1]["then"] = "the clerk is happy"
        errors, _ = backlog.validate(self.data)
        self.assertIn("acceptance S-3.2 'then' states no measurable quantity", messages(errors, "S-3"))

    def test_quantity_words_match_whole_words_only(self):
        self.story["acceptance"][1]["then"] = "the clerk has attended"  # 'ten' inside a word
        errors, _ = backlog.validate(self.data)
        self.assertIn("acceptance S-3.2 'then' states no measurable quantity", messages(errors, "S-3"))

    def test_xl_must_be_split_before_ready(self):
        self.story["size"] = "XL"
        errors, _ = backlog.validate(self.data)
        self.assertIn("size XL must be split into smaller items before it is ready", messages(errors, "S-3"))
        self.story["size"] = "XXL"
        errors, _ = backlog.validate(self.data)
        self.assertTrue(any("'size' must be one of" in m for m in messages(errors, "S-3")))

    def test_bare_user_is_not_an_actor(self):
        self.story["as_a"] = "the user"
        errors, _ = backlog.validate(self.data)
        self.assertIn("'as_a' is a bare 'the user'; name the specific actor", messages(errors, "S-3"))

    def test_dependency_cycle_is_reported_for_each_member(self):
        item(self.data, "S-1")["depends_on"] = ["S-3"]
        errors, _ = backlog.validate(self.data)
        for iid in ("S-1", "S-2", "S-3"):
            self.assertIn("depends_on forms a cycle", messages(errors, iid))
        self.assertEqual(messages(errors, "S-4"), [])

    def test_research_story_needs_time_box_and_decision(self):
        s1 = item(self.data, "S-1")
        s1["i_want"] = "a spike on bank formats"
        s1["acceptance"][0]["then"] = "a note of at most 1 page is linked"
        errors, _ = backlog.validate(self.data)
        self.assertIn("research story must state its time box, such as '3-day'", messages(errors, "S-1"))
        self.assertIn("research story must state the decision it produces", messages(errors, "S-1"))

    def test_draft_story_may_be_partial_but_schema_errors_still_fail(self):
        s6 = item(self.data, "S-6")
        del s6["size"]
        s6["acceptence"] = []
        errors, warnings = backlog.validate(self.data)
        self.assertIn("'size' is required", messages(warnings, "S-6"))
        self.assertIn("unknown field 'acceptence' for a story", messages(errors, "S-6"))


class Structure(unittest.TestCase):
    def test_parent_must_have_the_right_type(self):
        data = example()
        item(data, "S-2")["parent"] = "G-1"
        errors, _ = backlog.validate(data)
        self.assertIn("'parent' must be a feature in this file", messages(errors, "S-2"))

    def test_goal_driver_must_belong_to_its_initiative(self):
        data = example()
        item(data, "G-1")["drivers"] = ["D-9"]
        errors, _ = backlog.validate(data)
        self.assertIn("driver 'D-9' is not a driver of I-1", messages(errors, "G-1"))

    def test_delivery_must_list_exactly_the_items_criteria(self):
        data = example()
        item(data, "S-1")["delivery"]["criteria"] = {"S-1.1": "met", "S-1.2": "met"}
        errors, _ = backlog.validate(data)
        self.assertIn("delivery criteria must list exactly ['S-1.1']", messages(errors, "S-1"))

    def test_accepted_feedback_must_name_existing_items(self):
        data = example()
        data["feedback"][0]["resolution"] = "S-99 changed"
        errors, _ = backlog.validate(data)
        self.assertIn("resolution names unknown item S-99", messages(errors, "FB-1"))

    def test_ready_gate(self):
        data = example()
        errors, _ = backlog.validate(data, require_ready=True)
        self.assertIn("is still draft", messages(errors, "S-6"))
        # Draft work may wait on research that is not delivered yet, but not on delivered research.
        held = copy.deepcopy(data)
        item(held, "S-6")["depends_on"] = ["S-1"]
        errors, _ = backlog.validate(held, require_ready=True)
        self.assertIn("is still draft", messages(errors, "S-6"))  # S-1's decision is already in
        del item(held, "S-1")["delivery"]
        errors, warnings = backlog.validate(held, require_ready=True)
        self.assertEqual(messages(errors, "S-6"), [])
        self.assertIn("draft until research S-1 is delivered", messages(warnings, "S-6"))
        item(data, "S-6")["status"] = "ready"
        data["feedback"].append({"id": "FB-3", "feature": "F-2", "from": "x", "summary": "y", "disposition": "open"})
        data["items"] = [i for i in data["items"] if i["id"] != "S-6"]
        item(data, "I-1")["drivers"].append({"id": "D-3", "statement": "Unserved"})
        del item(data, "F-1")["owner"]
        errors, _ = backlog.validate(data, require_ready=True)
        self.assertIn("has no owner: name the one person accountable for it", messages(errors, "F-1"))
        self.assertEqual(messages(errors, "F-2"), [])  # F-2 names its owner
        self.assertIn("feedback is still open", messages(errors, "FB-3"))
        self.assertIn("has no story yet", messages(errors, "F-3"))
        self.assertIn("driver D-3 is served by no goal", messages(errors, "I-1"))
        errors, warnings = backlog.validate(data)
        self.assertEqual(errors, [])
        self.assertIn("has no story yet", messages(warnings, "F-3"))
        self.assertIn("has no owner: name the one person accountable for it", messages(warnings, "F-1"))


class WorkedExample(unittest.TestCase):
    def test_backlog_traces_resolve_against_the_worked_examples_evidence_and_prd(self):
        worked = ROOT / "skills" / "planning" / "reference" / "worked-example"
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("evidence.md", "prd.md"):
                Path(tmp, name).write_text((worked / name).read_text())
            data = example()
            errors, warnings = backlog.validate(data, base=Path(tmp))
            _, gaps = backlog.trace_report(data, tmp, "2027-03-10")
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual([g for g in gaps if "sign-off" not in g], [])


class Traceability(unittest.TestCase):
    def test_goal_direction_follows_baseline_to_target(self):
        goal = {"baseline": "60", "target": "10", "by": "2027-04-30", "measurements": [{"at": "2027-03-01", "value": "22"}]}
        self.assertEqual(backlog.goal_state(goal, "2027-03-10"), "in progress")
        self.assertEqual(backlog.goal_state(goal, "2027-05-01"), "missed")
        goal["measurements"].append({"at": "2027-04-01", "value": "9"})
        self.assertEqual(backlog.goal_state(goal, "2027-05-01"), "achieved")
        unknown = {"baseline": "unknown", "target": "3", "by": "2027-06-30", "measurements": [{"at": "2027-05-01", "value": "6"}]}
        self.assertEqual(backlog.goal_state(unknown, "2027-05-02"), "in progress")
        rising = {"baseline": "0", "target": "400", "by": "2027-03-31", "measurements": [{"at": "2027-03-31", "value": "399"}]}
        self.assertEqual(backlog.goal_state(rising, "2027-03-31"), "in progress")
        # A limit above today's value ("tickets must stay at most 80", today 40) is direction-free.
        limit = {"baseline": "40", "target": "at most 80", "by": "2027-09-30", "measurements": [{"at": "2027-07-01", "value": "120"}]}
        self.assertEqual(backlog.goal_state(limit, "2027-07-02"), "in progress")
        limit["measurements"].append({"at": "2027-08-01", "value": "80"})
        self.assertEqual(backlog.goal_state(limit, "2027-08-02"), "achieved")
        floor = {"baseline": "unknown", "target": "At least 85%", "by": "2027-08-27", "measurements": [{"at": "2027-08-20", "value": "84.5%"}]}
        self.assertEqual(backlog.goal_state(floor, "2027-08-28"), "missed")

    def test_trace_reports_untraced_prd_requirements_and_partial_delivery(self):
        data = example()
        item(data, "S-2")["delivery"] = {"at": "2027-02-20", "evidence": ["PR 88"],
                                          "criteria": {"S-2.1": "met", "S-2.2": "met", "S-2.3": "not met", "S-2.4": "met"}}
        item(data, "S-3")["trace"] = ["E4"]  # AC-4 is now listed on feature F-1 only
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "prd.md").write_text("- **R-1** a\n- **R-2** b\n- **R-3** c\n- **R-9** d\n**AC-1** **AC-2** **AC-3** **AC-4** **AC-5**\n"
                                           "## Change log\n- removed R-7 and AC-8")
            text, gaps = backlog.trace_report(data, tmp, "2027-03-10")
        self.assertIn("R-9 in prd.md is traced by no item", gaps)
        self.assertIn("S-2 partial: S-2.3 not met", gaps)
        self.assertIn("AC-4 in prd.md is traced only by a feature; no story or bug delivers it", gaps)
        self.assertFalse([g for g in gaps if g.startswith("AC-3 ")])  # delivered by S-1, S-2, and B-1
        self.assertNotIn("R-1 in prd.md is traced by no item", gaps)
        self.assertFalse([g for g in gaps if "R-7" in g or "AC-8" in g])  # mentioned, not defined
        self.assertIn("| I-1 | D-1:", text)


class FakeGitHub:
    """Just enough of the GitHub REST API, keyed by the paths sync.py calls, with its own clock."""

    def __init__(self, me="planner"):
        self.issues, self.milestones, self.labels, self.subs, self.comments = {}, {}, set(), {}, []
        self.writes, self.clock, self.me = 0, 0, me
        self.project = FakeProject(self)

    def now(self):
        self.clock += 1
        return f"2027-01-{10 + self.clock // 3600:02d}T{self.clock // 60 % 60:02d}:{self.clock % 60:02d}:00Z".replace("T00:", "T01:")

    def call(self, method, path, body=None, paginate=False):
        route = path.split("?")[0]
        if route == "user":
            return {"login": self.me}
        if route.startswith("users/acme") or route == "graphql":
            return self.project.call(method, route, body)
        route = route.removeprefix("repos/acme/close/")
        parts = route.split("/")
        if method != "GET":
            self.writes += 1
        if method == "GET" and route == "issues":
            return list(self.issues.values())
        if method == "GET" and route == "milestones":
            return list(self.milestones.values())
        if method == "GET" and route == "labels":
            return [{"name": n} for n in sorted(self.labels)]
        if method == "GET" and route == "issues/comments":
            return self.comments
        if method == "POST" and route == "labels":
            self.labels.add(body["name"])
            return {}
        if method == "POST" and route == "milestones":
            number = len(self.milestones) + 1
            self.milestones[number] = {"number": number, "title": body["title"], "due_on": body.get("due_on")}
            return self.milestones[number]
        if method == "PATCH" and parts[0] == "milestones":
            self.milestones[int(parts[1])].update(body)
            return self.milestones[int(parts[1])]
        if method == "POST" and route == "issues":
            number = len(self.issues) + 1
            self.issues[number] = {"number": number, "id": 9000 + number, "title": body["title"], "body": body["body"],
                                   "state": "open", "labels": [{"name": n} for n in body["labels"]],
                                   "milestone": self._milestone(body.get("milestone")), "updated_at": self.now(),
                                   "html_url": f"https://github.com/acme/close/issues/{number}"}
            return self.issues[number]
        if parts[0] == "issues" and parts[1] == "comments" and method == "PATCH":
            comment = next(c for c in self.comments if c["id"] == int(parts[2]))
            comment["body"] = body["body"]
            return comment
        if parts[0] == "issues" and len(parts) == 2:
            if int(parts[1]) not in self.issues:
                raise RuntimeError("gh api: HTTP 404")
            issue = self.issues[int(parts[1])]
            if method == "PATCH":
                for key in ("title", "body"):
                    if key in body:
                        issue[key] = body[key]
                if "milestone" in body:
                    issue["milestone"] = self._milestone(body["milestone"])
                issue["updated_at"] = self.now()
            return issue
        if parts[0] == "issues" and parts[2] == "comments":
            if method == "GET":
                return [c for c in self.comments if c["issue_url"].endswith(f"/{parts[1]}")]
            return self.comment(int(parts[1]), self.me, body["body"])
        if parts[0] == "issues" and parts[2] == "labels":
            issue = self.issues[int(parts[1])]
            if method == "POST":
                issue["labels"] += [{"name": n} for n in body["labels"]]
            else:
                issue["labels"] = [l for l in issue["labels"] if l["name"] != parts[3].replace("%3A", ":")]
            return {}
        if parts[0] == "issues" and parts[2] == "sub_issues":
            parent = int(parts[1])
            if method == "GET":
                return [self.issues[n] for n in self.subs.get(parent, [])]
            child = next(n for n, i in self.issues.items() if i["id"] == body["sub_issue_id"])
            if any(child in kids for p, kids in self.subs.items() if p != parent):
                raise RuntimeError("gh api: HTTP 422 sub-issue already has a parent")
            self.subs.setdefault(parent, []).append(child)
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    def _milestone(self, number):
        return {"title": self.milestones[number]["title"]} if number else None

    def comment(self, number, login, body, kind="User"):
        comment = {"id": 500 + len(self.comments), "issue_url": f"https://api.github.com/repos/acme/close/issues/{number}",
                   "user": {"login": login, "type": kind}, "body": body, "created_at": self.now(),
                   "html_url": f"https://github.com/acme/close/issues/{number}#c{len(self.comments)}"}
        self.comments.append(comment)
        return comment


class FakeProject:
    """User project acme/7, in the REST shapes of fields and items and the GraphQL views and iteration update."""

    def __init__(self, github):
        self.github, self.fields, self.cards, self.views, self.next_id = github, {}, {}, [], 100

    def new_id(self):
        self.next_id += 1
        return self.next_id

    def call(self, method, route, body):
        if route == "users/acme":
            return {"login": "acme", "type": "User"}
        if route == "graphql":
            if "updateProjectV2Field" in body["query"]:
                self.github.writes += 1
                field = next(f for f in self.fields.values() if f["node_id"] == body["variables"]["f"])
                field["configuration"]["iterations"] = [
                    {"id": i.get("id") or f"it{self.new_id()}", "title": {"raw": i["title"]}, "start_date": i["startDate"],
                     "duration": i["duration"]} for i in body["variables"]["c"]["iterations"]]
                return {"data": {}}
            return {"data": {"user": {"projectV2": {"views": {"nodes": [{"name": v["name"]} for v in self.views]}}}}}
        if method != "GET":
            self.github.writes += 1
        tail = route.removeprefix("users/acme/projectsV2/7/").split("/")
        if tail == ["fields"] and method == "GET":
            return list(self.fields.values())
        if tail == ["fields"]:
            field = {"id": self.new_id(), "node_id": f"F{self.next_id}", "name": body["name"], "data_type": body["data_type"]}
            if "single_select_options" in body:
                if not all(isinstance(o["name"], str) and isinstance(o["description"], str) for o in body["single_select_options"]):
                    raise RuntimeError("gh api: HTTP 422 data matches no possible input")  # as the live API does
                field["options"] = [{"id": f"o{self.new_id()}", "name": {"raw": o["name"], "html": o["name"]}}
                                    for o in body["single_select_options"]]
            if "iteration_configuration" in body:
                field["configuration"] = {"iterations": [
                    {"id": f"it{self.new_id()}", "title": {"raw": i["title"]}, "start_date": i["start_date"], "duration": i["duration"]}
                    for i in body["iteration_configuration"]["iterations"]]}
            self.fields[body["name"]] = field
            return field
        if tail == ["items"] and method == "GET":
            return [{"id": cid, "content_type": "Issue", "content": {"id": c["issue"]},
                     "fields": [self.shown(name, value) for name, value in c["values"].items()]} for cid, c in self.cards.items()]
        if tail == ["items"]:
            if any(c["issue"] == body["id"] for c in self.cards.values()):
                raise RuntimeError("gh: Content already exists in this project (HTTP 422)")
            cid = self.new_id()
            self.cards[cid] = {"issue": body["id"], "values": {}}
            self.add_sub_issues(body["id"])
            return {"id": cid}
        if tail[0] == "items" and method == "PATCH":
            by_id = {f["id"]: f for f in self.fields.values()}
            for update in body["fields"]:
                self.cards[int(tail[1])]["values"][by_id[update["id"]]["name"]] = update["value"]
            return {}
        if tail == ["views"]:
            self.views.append(body)
            return {}
        raise AssertionError(f"unexpected project call {method} {route}")

    def add_sub_issues(self, issue_id):
        """Like GitHub's default workflow: a new card's sub-issues get cards of their own."""
        number = next(n for n, i in self.github.issues.items() if i["id"] == issue_id)
        for child in self.github.subs.get(number, []):
            child_id = self.github.issues[child]["id"]
            if not any(c["issue"] == child_id for c in self.cards.values()):
                self.cards[self.new_id()] = {"issue": child_id, "values": {}}
                self.add_sub_issues(child_id)

    def shown(self, name, value):
        """A card value as the REST API returns it: options and iterations by name, numbers as numbers."""
        field = self.fields[name]
        for option in field.get("options", []):
            if option["id"] == value:
                return {"name": name, "value": {"id": value, "name": option["name"]}}
        for it in field.get("configuration", {}).get("iterations", []):
            if it["id"] == value:
                return {"name": name, "value": {"id": value, "title": it["title"]}}
        return {"name": name, "value": value}

    def card(self, issue_number):
        issue_id = self.github.issues[issue_number]["id"]
        return next(c for c in self.cards.values() if c["issue"] == issue_id)

    def card_text(self, issue_number):
        return {name: sync._text_value(self.shown(name, v)["value"]) for name, v in self.card(issue_number)["values"].items()}

    def option(self, name, text):
        return next(o["id"] for o in self.fields[name]["options"] if o["name"]["raw"] == text)


class GitHubSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        Path(self.base, "prd.md").write_text((ROOT / "skills/planning/reference/worked-example/prd.md").read_text())
        self.fake = FakeGitHub()
        self.gh = sync.GitHub("acme/close", call=self.fake.call)
        self.data = example()

    def tearDown(self):
        self.tmp.cleanup()

    def number(self, iid):
        return item(self.data, iid)["external"]["github"]["number"]

    def plan_for(self, iid, data=None, **kw):
        return [a["do"] for a in sync.plan(data or self.data, self.base, self.gh, **kw) if a.get("id") == iid]

    def sign_off(self, iid, login="tokafor"):
        self.fake.comment(self.number(iid), login, "/approve\nLooks right.")
        sync.pull(self.data, self.gh)

    def test_first_apply_builds_the_tree_and_a_second_plan_is_empty(self):
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(len(self.fake.issues), len(self.data["items"]))
        self.assertEqual({m["title"] for m in self.fake.milestones.values()}, {"PI 27.1: pilot UK01", "PI 27.2: all EU entities"})
        kids_of_f1 = {self.fake.issues[n]["title"][:5] for n in self.fake.subs[self.number("F-1")]}
        self.assertEqual(kids_of_f1, {"[S-1]", "[S-2]", "[S-3]", "[B-1]"})
        self.assertEqual(self.fake.issues[self.number("S-3")]["milestone"], {"title": "PI 27.1: pilot UK01"})  # from F-1
        self.assertIn("urgency:critical", {l["name"] for l in self.fake.issues[self.number("B-1")]["labels"]})
        self.assertIn("**R-2 Bank reconciliation", self.fake.issues[self.number("I-1")]["body"])  # PRD content, not a link
        writes = self.fake.writes
        self.assertEqual(sync.plan(self.data, self.base, self.gh), [])
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(self.fake.writes, writes)

    def project_plan(self, **kw):
        return [a for a in sync.plan(self.data, self.base, self.gh, project="acme/7", **kw) if a["do"].startswith("project") or a["do"] == "conflict"]

    def test_project_gets_fields_schedule_cards_and_views_then_nothing_to_do(self):
        sync.apply(self.data, self.base, self.gh, project="acme/7")
        p = self.fake.project
        self.assertEqual(set(p.fields), {"Item type", "Priority", "Urgency", "Size", "Readiness", "Rank score", "Schedule"})
        slots = [(i["title"]["raw"], i["start_date"], i["duration"]) for i in p.fields["Schedule"]["configuration"]["iterations"]]
        # M1 runs from its start to its due date; M2 from the day after M1's due date to its own.
        self.assertEqual(slots, [("PI 27.1: pilot UK01", "2027-01-11", 47), ("PI 27.2: all EU entities", "2027-02-27", 91)])
        self.assertEqual(len(p.cards), len(self.data["items"]))
        s6 = p.card_text(self.number("S-6"))
        self.assertEqual((s6["Item type"], s6["Priority"], s6["Schedule"]), ("story", "should", "PI 27.2: all EU entities"))  # slot from F-3
        f1 = p.card_text(self.number("F-1"))
        self.assertNotIn("Priority", f1)
        self.assertEqual(f1["Rank score"], backlog.wsjf_score(item(self.data, "F-1")))
        self.assertEqual({v["name"]: v["layout"] for v in p.views}, {"Roadmap": "roadmap", "Backlog by milestone": "table"})
        writes = self.fake.writes
        self.assertEqual(sync.plan(self.data, self.base, self.gh, project="acme/7"), [])
        sync.apply(self.data, self.base, self.gh, project="acme/7")
        self.assertEqual(self.fake.writes, writes)

    def test_project_card_edited_in_github_is_a_conflict_until_overwrite(self):
        sync.apply(self.data, self.base, self.gh, project="acme/7")
        p = self.fake.project
        p.card(self.number("S-2"))["values"]["Priority"] = p.option("Priority", "could")
        item(self.data, "S-1")["priority"] = "should"
        actions = [(a["do"], a["id"]) for a in self.project_plan()]
        self.assertIn(("conflict", "S-2"), actions)
        self.assertNotIn(("project values", "S-2"), actions)
        self.assertIn(("project values", "S-1"), actions)  # a local change with no edit in GitHub just flows
        forced = [(a["id"], a["set"]) for a in self.project_plan(overwrite=("S-2",)) if a["do"] == "project values"]
        self.assertIn(("S-2", {"Priority": "must"}), forced)
        # A card value set by hand before this file ever wrote the card is not overwritten either.
        del item(self.data, "S-3")["external"]["github"]["project"]
        p.card(self.number("S-3"))["values"]["Size"] = p.option("Size", "XL")
        self.assertIn(("conflict", "S-3"), [(a["do"], a["id"]) for a in self.project_plan()])

    def test_moving_a_due_date_moves_the_slot_and_keeps_cards_on_it(self):
        sync.apply(self.data, self.base, self.gh, project="acme/7")
        p = self.fake.project
        before = [i["id"] for i in p.fields["Schedule"]["configuration"]["iterations"]]
        self.data["milestones"][1]["due"] = "2027-06-11"
        self.assertEqual([a["do"] for a in self.project_plan()], ["project schedule"])
        sync.apply(self.data, self.base, self.gh, project="acme/7")
        slots = p.fields["Schedule"]["configuration"]["iterations"]
        self.assertEqual([i["id"] for i in slots], before)
        self.assertEqual(slots[1]["duration"], 105)
        self.assertEqual(p.card_text(self.number("F-3"))["Schedule"], "PI 27.2: all EU entities")
        self.assertEqual(sync.plan(self.data, self.base, self.gh, project="acme/7"), [])

    def test_project_refuses_a_wrong_field_type_and_a_first_milestone_without_start(self):
        self.fake.project.fields["Size"] = {"id": 1, "node_id": "F1", "name": "Size", "data_type": "text"}
        with self.assertRaisesRegex(RuntimeError, "'Size' exists as text"):
            sync.plan(self.data, self.base, self.gh, project="acme/7")
        del self.fake.project.fields["Size"]
        del self.data["milestones"][0]["start"]
        with self.assertRaisesRegex(RuntimeError, "M1 needs a 'start'"):
            sync.plan(self.data, self.base, self.gh, project="acme/7")

    def test_lost_sync_records_rebind_by_marker_when_github_matches(self):
        sync.apply(self.data, self.base, self.gh)
        fresh = example()
        self.assertEqual({a["do"] for a in sync.plan(fresh, self.base, self.gh)}, {"record"})
        sync.apply(fresh, self.base, self.gh)
        self.assertEqual(len(self.fake.issues), len(fresh["items"]))
        self.assertEqual(sync.plan(fresh, self.base, self.gh), [])

    def test_unknown_issue_with_the_same_id_is_a_conflict_not_an_overwrite(self):
        sync.apply(self.data, self.base, self.gh)
        before = {n: dict(i) for n, i in self.fake.issues.items()}
        other = example("product")  # a second backlog pointed at the same repository
        actions = sync.plan(other, self.base, self.gh)
        self.assertEqual({a["do"] for a in actions if a.get("id") == "I-1"}, {"conflict"})
        self.assertNotIn("update", {a["do"] for a in actions})
        Path(self.base, "prd.md").write_text("**R-1** x")
        sync.apply(other, self.base, self.gh)
        for n, issue in before.items():
            self.assertEqual((self.fake.issues[n]["title"], self.fake.issues[n]["body"]), (issue["title"], issue["body"]))

    def test_github_edits_to_body_labels_or_milestone_are_conflicts_until_overwritten(self):
        sync.apply(self.data, self.base, self.gh)
        self.fake.issues[self.number("S-2")]["body"] += "\nEdited in GitHub"
        s3 = self.fake.issues[self.number("S-3")]
        s3["labels"] = [l for l in s3["labels"] if l["name"] != "priority:must"] + [{"name": "priority:could"}]
        self.fake.issues[self.number("S-4")]["milestone"] = None
        item(self.data, "S-2")["title"] = "Nightly job posts single-match bank lines"
        for iid in ("S-2", "S-3", "S-4"):
            self.assertEqual(self.plan_for(iid), ["conflict"], iid)
        self.assertIn("update", self.plan_for("S-2", overwrite=("S-2",)))
        self.assertEqual(self.plan_for("S-3", overwrite=("S-3",)), ["labels"])

    def test_removed_marker_or_label_never_creates_a_duplicate(self):
        sync.apply(self.data, self.base, self.gh)
        s2 = self.fake.issues[self.number("S-2")]
        s2["labels"] = [l for l in s2["labels"] if l["name"] != "backlog"]
        self.assertEqual(self.plan_for("S-2"), ["conflict"])  # label change is detected, not "create"
        s2["body"] = s2["body"].replace("<!-- backlog:S-2 -->", "")
        self.assertEqual(self.plan_for("S-2"), ["conflict"])
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(len(self.fake.issues), len(self.data["items"]))

    def test_same_marker_on_two_issues_is_a_conflict(self):
        sync.apply(self.data, self.base, self.gh)
        copy_of = dict(self.fake.issues[self.number("S-2")], number=99, id=9099)
        self.fake.issues[99] = copy_of
        self.assertEqual(self.plan_for("S-2"), ["conflict"])

    def test_apply_refuses_a_plan_that_changed_since_approval(self):
        digest = sync.plan_digest(sync.plan(self.data, self.base, self.gh))
        item(self.data, "S-2")["title"] = "Changed after the plan was approved"
        with self.assertRaises(RuntimeError):
            sync.apply(self.data, self.base, self.gh, expect=digest)
        self.assertEqual(self.fake.writes, 0)

    def test_sign_off_goes_stale_when_a_covered_story_changes_and_is_synced(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("F-1")
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "approved")
        item(self.data, "S-3")["acceptance"][0]["then"] = "the report is in the AP folder by 06:30 with every unmatched line"
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "unsynced changes")
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "stale")
        self.sign_off("F-1")
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "approved")

    def test_bug_changes_and_delivery_records_do_not_reopen_sign_off(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("F-1")
        item(self.data, "B-1")["observed"] += " Seen again on 2027-03-09."
        item(self.data, "S-3")["delivery"] = {"at": "2027-02-20", "evidence": ["run log"], "criteria": {"S-3.1": "met", "S-3.2": "met"}}
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "approved")

    def test_issue_bodies_have_named_sections_and_a_project_can_bring_its_own_template(self):
        headings = lambda iid: re.findall(r"(?m)^## (.+)$", sync.render(self.data, item(self.data, iid), self.base)[1])  # noqa: E731
        self.assertEqual(headings("S-2"), ["User story", "Acceptance criteria (definition of done)", "Depends on", "Owner", "Sources"])
        self.assertEqual(headings("S-1")[:2], ["User story", "Acceptance criteria (definition of done)"])
        self.assertNotIn("Depends on", headings("S-1"))  # an empty section is left out, heading and all
        self.assertEqual(headings("G-1"), ["Metric", "Baseline and target", "Serves business drivers", "Sources"])
        Path(self.base, "issue-templates").mkdir()
        Path(self.base, "issue-templates/story.md").write_text("Read this first.\n\n## Done when\n{acceptance}\n\n## Why\n{user_story}\n")
        title, body, _, _ = sync.render(self.data, item(self.data, "S-2"), self.base)
        self.assertTrue(body.startswith("Read this first.\n\n## Done when\n- [ ] **S-2.1**"))
        self.assertIn("## Why\n**As an accounts payable clerk**", body)
        self.assertTrue(body.endswith("<!-- backlog:S-2 -->"))  # identity is kept whatever the template says
        Path(self.base, "issue-templates/story.md").write_text("## Size\n{size}\n")
        with self.assertRaisesRegex(RuntimeError, r"unknown slots \['size'\]"):
            sync.render(self.data, item(self.data, "S-2"), self.base)

    def test_a_new_issue_layout_updates_bodies_without_reopening_sign_off(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("F-1")
        Path(self.base, "issue-templates").mkdir()
        Path(self.base, "issue-templates/story.md").write_text("## Done when\n{acceptance}\n\n## Story\n{user_story}\n")
        self.assertIn(("update", "S-2"), [(a["do"], a.get("id")) for a in sync.plan(self.data, self.base, self.gh)])
        sync.apply(self.data, self.base, self.gh)
        self.assertTrue(self.fake.issues[self.number("S-2")]["body"].startswith("## Done when"))
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-1"), base=self.base), "approved")

    def test_editing_the_prd_reopens_the_prd_gate(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("I-1", "priya-r")
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "I-1"), base=self.base), "approved")
        prd = Path(self.base, "prd.md")
        prd.write_text(prd.read_text().replace("by 02:30", "by 03:00"))
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "I-1"), base=self.base), "unsynced changes")
        sync.apply(self.data, self.base, self.gh)
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "I-1"), base=self.base), "stale")

    def test_every_approver_can_be_required(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("I-1", "PRIYA-R")  # GitHub logins are case-insensitive
        ini = item(self.data, "I-1")
        self.assertEqual(backlog.approval_detail(self.data, ini, base=self.base)[1], {"priya-r": "current", "tokafor": "none"})
        self.assertEqual(backlog.approval_state(self.data, ini, base=self.base, require_all=True), "partly approved")
        self.sign_off("I-1", "tokafor")
        self.assertEqual(backlog.approval_state(self.data, ini, base=self.base, require_all=True), "approved")

    def test_pull_routes_comments_by_who_and_where(self):
        sync.apply(self.data, self.base, self.gh)
        self.fake.comment(self.number("S-3"), "priya-r", "Can the report also show the supplier name?")
        self.fake.comment(self.number("F-2"), "intern", "/approve")
        self.fake.comment(self.number("G-1"), "tokafor", "Is 3 days realistic for DE01?")
        self.fake.comment(self.number("S-3"), "planner", "Thanks, logged.")
        self.fake.comment(self.number("S-3"), "dependabot", "Bump", kind="Bot")
        self.fake.issues[self.number("S-4")]["state"] = "closed"
        before = len(self.data["feedback"])
        report = sync.pull(self.data, self.gh)
        new = self.data["feedback"][before:]
        self.assertEqual([(f["id"], f["feature"], f["from"]) for f in new], [("FB-3", "F-1", "priya-r"), ("FB-4", "F-2", "intern")])
        self.assertEqual(report["approvals"], [])
        self.assertEqual([t["item"] for t in report["triage"]], ["G-1"])
        self.assertEqual(report["closed_without_delivery"], ["S-4"])
        self.assertEqual(item(self.data, "S-4")["external"]["github"]["state"], "closed")
        sync.pull(self.data, self.gh)
        self.assertEqual(len(self.data["feedback"]), before + 2)  # pulling twice adds nothing

    def test_planner_who_is_an_approver_can_sign_off(self):
        self.data["approvers"].append({"name": "Planner", "github": "planner"})
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("F-2", "planner")
        self.assertEqual(backlog.approval_state(self.data, item(self.data, "F-2"), base=self.base), "approved")

    def test_status_report_is_one_comment_updated_in_place(self):
        sync.apply(self.data, self.base, self.gh)
        self.sign_off("F-2", "tokafor")
        sync.post_report(self.data, self.base, self.gh, "2027-03-10")
        sync.post_report(self.data, self.base, self.gh, "2027-03-11")
        reports = [c for c in self.fake.comments if sync.REPORT_MARKER in c["body"]]
        self.assertEqual(len(reports), 1)
        body = reports[0]["body"]
        self.assertIn("updated 2027-03-11", body)
        # Five plain lines for stakeholders, not the trace tables.
        self.assertEqual(len([l for l in body.splitlines() if l.startswith("- **")]), 5)
        self.assertNotIn("| ", body)
        signed = next(l for l in body.splitlines() if l.startswith("- **Not yet signed by:**"))
        self.assertIn("Priya Raman (Finance Operations lead) on I-1, F-1, F-2, F-3", signed)
        self.assertIn("Tom Okafor (Group Controller) on I-1, F-1, F-3", signed)
        self.assertIn("PI 27.1: pilot UK01 due 2027-02-26, overdue: 1 of", body)
        before = len(self.data["feedback"])
        sync.pull(self.data, self.gh)
        self.assertEqual(len(self.data["feedback"]), before)  # the report is not feedback

    def test_missing_prd_blocks_sync(self):
        Path(self.base, "prd.md").unlink()
        with self.assertRaises(RuntimeError):
            sync.plan(self.data, self.base, self.gh)


class Excel(unittest.TestCase):
    def test_workbook_has_every_item_and_criterion(self):
        data = example()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "b.xlsx")
            sync.write_xlsx(out, sync.excel_rows(data, tmp))
            with zipfile.ZipFile(out) as z:
                ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                book = ElementTree.fromstring(z.read("xl/workbook.xml"))
                names = [s.get("name") for s in book.find("m:sheets", ns)]
                backlog_rows = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:row", ns)
                criteria_rows = ElementTree.fromstring(z.read("xl/worksheets/sheet2.xml")).findall(".//m:row", ns)
                first = "".join(backlog_rows[1].itertext())
        self.assertEqual(names, ["Backlog", "Acceptance criteria", "Feedback", "Milestones", "Traceability gaps"])
        self.assertEqual(len(backlog_rows), len(data["items"]) + 1)
        expected = sum(len(i.get("acceptance") or []) for i in data["items"] if i["type"] in ("story", "bug"))
        self.assertEqual(len(criteria_rows), expected + 1)
        self.assertTrue(first.startswith("I-1initiative"))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Linear adapter for sync.py, over the GraphQL API. Not tested live.

  sync.py linear plan   backlog.json --team KEY --project NAME
  sync.py linear apply  backlog.json --team KEY --project NAME --expect DIGEST [--overwrite ID,...]
  sync.py linear pull   backlog.json --team KEY --project NAME [--since YYYY-MM-DD]
  sync.py linear report backlog.json --team KEY --project NAME [--post]

Each backlog item is one Linear issue in one team and project, labelled `backlog`, `type:<type>`,
and the other labels GitHub gets. Parents are sub-issues (initiative, goal, feature, then story
or bug). Milestones are project milestones matched by title. The last line of each description,
"Backlog ID: S-2", is the identity. Archived issues are listed too and count as closed. An approver's `linear` handle is a display name or an email.
The API key comes from LINEAR_API_KEY and is never printed. Standard library only. Running this
file is the same as `sync.py linear …`.
"""

import re
import sys

import sync

KEY = "LINEAR_API_KEY"
URL = "https://api.linear.app/graphql"
ID_LINE = re.compile(r"(?m)^Backlog ID: ([IGFSB]-\d+)\s*$")
CLOSED = {"completed", "canceled"}
ISSUE = ("id identifier url title description updatedAt archivedAt state { type } parent { id } "
         "labels { nodes { id name } } projectMilestone { id name }")
PAGE = "pageInfo { hasNextPage endCursor }"


def transport(key, opener=None):
    """call(query, variables) -> data. A GraphQL error is an exception."""
    def call(query, variables):
        reply = sync.http_json("POST", URL, {"Authorization": key}, {"query": query, "variables": variables}, opener=opener) or {}
        if reply.get("errors"):
            raise RuntimeError("Linear GraphQL: " + "; ".join(e.get("message", "?") for e in reply["errors"]))
        if not isinstance(reply.get("data"), dict):
            raise RuntimeError("Linear GraphQL: the reply has no data")
        return reply["data"]
    return call


def who(user, handles):
    """A commenter as `approvers` names them, else 'display name <email>'.

    A handle with '@' matches only the commenter's email, any other handle only their display
    name, because users can set their own display name to look like someone's email. The fallback
    holds the real email too, so it does not equal a listed approver's handle."""
    email, name = user.get("email") or "", user.get("displayName") or ""
    if "@" in handles.get(email.lower(), ""):
        return handles[email.lower()]
    if name and "@" not in handles.get(name.lower(), "@"):
        return handles[name.lower()]
    return f"{name} <{email}>"


class Linear:
    name, tracker, noun, marker = "linear", "Linear", "an issue", "'Backlog ID' line"
    label_word, milestone_word, link_kind = "labels", "project milestone", None

    def __init__(self, team, project, call=None):
        self.team, self.project = team, project
        self.call = call or transport(sync.secret(KEY, "a Linear personal API key"))
        self._ids = self._labels = self._milestones = None
        self.target = ("linear", team, project)  # bound into the plan digest

    def ids(self):
        """(team ID, project ID), looked up once by team key and project name, before any write.
        Linear creates an issue in a project only when the project includes the issue's team."""
        if self._ids is None:
            found = self.call("query Setup($team: String!, $project: String!) { teams(filter: {key: {eq: $team}}) { nodes { id key } } "
                              "projects(filter: {name: {eq: $project}}) { nodes { id name teams { nodes { id } } } } }",
                              {"team": self.team, "project": self.project})
            teams, projects = found["teams"]["nodes"], found["projects"]["nodes"]
            if not teams:
                raise RuntimeError(f"no Linear team with key {self.team!r}")
            if len(projects) != 1:
                raise RuntimeError(f"expected one Linear project named {self.project!r}, found {len(projects)}")
            if teams[0]["id"] not in {n["id"] for n in projects[0]["teams"]["nodes"]}:
                raise RuntimeError(f"Linear project {self.project!r} does not include team {self.team}; add the team to the project first")
            self._ids = (teams[0]["id"], projects[0]["id"])
        return self._ids

    def _pages(self, query, variables, path):
        nodes, after = [], None
        while True:
            page = self.call(query, {**variables, "after": after})
            for step in path:
                page = page[step]
            nodes += page["nodes"]
            if not page["pageInfo"]["hasNextPage"]:
                return nodes
            after = page["pageInfo"]["endCursor"]

    def view(self, data, item, base):
        title, body, labels, milestone = sync.render(data, item, base)
        body = body.replace(f"<!-- backlog:{item['id']} -->", f"Backlog ID: {item['id']}")
        return {"title": title, "body": body, "labels": sorted(labels), "milestone": milestone}

    def milestone_title(self, title):
        return title

    def _rec(self, issue):
        found = ID_LINE.findall(issue.get("description") or "")
        return {"key": issue["id"], "iid": found[-1] if found else None, "title": issue.get("title") or "",
                "body": issue.get("description") or "", "labels": sync._own_labels({"labels": issue["labels"]["nodes"]}),
                "milestone": (issue.get("projectMilestone") or {}).get("name"), "parent": (issue.get("parent") or {}).get("id"),
                "state": "closed" if issue.get("archivedAt") or (issue.get("state") or {}).get("type") in CLOSED else "open",
                "url": issue["url"], "at": issue.get("updatedAt")}

    def items(self):
        """({backlog ID: issue}, {backlog ID: [issue IDs]} for IDs on more than one issue)."""
        query = f"query Issues($project: String!, $after: String) {{ project(id: $project) {{ issues(first: 100, after: $after, includeArchived: true) {{ nodes {{ {ISSUE} }} {PAGE} }} }} }}"
        found, dupes = {}, {}
        for issue in self._pages(query, {"project": self.ids()[1]}, ("project", "issues")):
            rec = self._rec(issue)
            if rec["iid"] in found:
                dupes.setdefault(rec["iid"], [found[rec["iid"]]["key"]]).append(rec["key"])
            if rec["iid"]:
                found[rec["iid"]] = rec
        return found, dupes

    def _issue(self, key):
        return self.call(f"query Issue($id: String!) {{ issue(id: $id) {{ {ISSUE} }} }}", {"id": key})["issue"]

    def exists(self, key):
        try:
            return bool(self._issue(key))
        except RuntimeError:
            return False

    def _milestone_ids(self):
        if self._milestones is None:
            found = self.call("query Milestones($project: String!) { project(id: $project) { projectMilestones { nodes { id name } } } }",
                              {"project": self.ids()[1]})
            self._milestones = {m["name"]: m["id"] for m in found["project"]["projectMilestones"]["nodes"]}
        return self._milestones

    def milestones(self):
        return set(self._milestone_ids())

    def _label_ids(self):
        if self._labels is None:
            query = ("query Labels($team: ID!, $after: String) { issueLabels(first: 250, after: $after, "
                     f"filter: {{or: [{{team: {{id: {{eq: $team}}}}}}, {{team: {{null: true}}}}]}}) {{ nodes {{ id name }} {PAGE} }} }}")
            self._labels = {n["name"].lower(): n["id"] for n in self._pages(query, {"team": self.ids()[0]}, ("issueLabels",))}
        return self._labels

    def missing_labels(self, wanted):
        return sorted(l for l in wanted if l.lower() not in self._label_ids())

    def create_labels(self, names):
        for name in names:
            label = self.call("mutation LabelCreate($input: IssueLabelCreateInput!) { issueLabelCreate(input: $input) { issueLabel { id name } } }",
                              {"input": {"name": name, "teamId": self.ids()[0], "color": "#" + sync.LABEL_COLORS[name.split(":")[0]]}})
            self._label_ids()[name.lower()] = label["issueLabelCreate"]["issueLabel"]["id"]

    def create_milestone(self, a):
        self.call("mutation MilestoneCreate($input: ProjectMilestoneCreateInput!) { projectMilestoneCreate(input: $input) { projectMilestone { id name } } }",
                  {"input": {"projectId": self.ids()[1], "name": a["title"], **({"targetDate": a["due"]} if a["due"] else {})}})
        self._milestones = None

    def _update(self, key, change):
        query = f"mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {{ issueUpdate(id: $id, input: $input) {{ issue {{ {ISSUE} }} }} }}"
        return self.call(query, {"id": key, "input": change})["issueUpdate"]["issue"]

    def create(self, a):
        team, project = self.ids()
        change = {"teamId": team, "projectId": project, "title": a["title"], "description": a["body"],
                  "labelIds": [self._label_ids()[l.lower()] for l in a["labels"]]}
        if a["milestone"]:
            change["projectMilestoneId"] = self._milestone_ids()[a["milestone"]]
        query = f"mutation IssueCreate($input: IssueCreateInput!) {{ issueCreate(input: $input) {{ issue {{ {ISSUE} }} }} }}"
        return self._rec(self.call(query, {"input": change})["issueCreate"]["issue"])

    def update(self, key, a):
        return self._rec(self._update(key, {"title": a["title"], "description": a["body"]}))

    def set_labels(self, key, add, remove):
        drop = {r.lower() for r in remove}
        keep = [l["id"] for l in self._issue(key)["labels"]["nodes"] if l["name"].lower() not in drop]
        self._update(key, {"labelIds": keep + [self._label_ids()[l.lower()] for l in add]})

    def set_milestone(self, key, milestone):
        self._update(key, {"projectMilestoneId": self._milestone_ids()[milestone] if milestone else None})

    def link(self, child, parent, replace=False):
        self._update(child, {"parentId": parent})  # setting parentId replaces any present parent

    def _comments(self, key):
        query = ("query Comments($id: String!, $after: String) { issue(id: $id) { comments(first: 100, after: $after) { "
                 f"nodes {{ id body url createdAt user {{ displayName email }} botActor {{ id }} }} {PAGE} }} }} }}")
        return [c for c in self._pages(query, {"id": key}, ("issue", "comments")) if c.get("user") and not c.get("botActor")]

    def comments(self, key, handles):
        """[(login, url, body, created)] for each person's comment; bot comments are left out."""
        return [(who(c["user"], handles), c["url"], c.get("body") or "", c["createdAt"]) for c in self._comments(key)]

    def me(self, handles):
        return who(self.call("query Viewer { viewer { displayName email } }", {})["viewer"], handles).lower()

    def post_status(self, key, body, handles):
        me = self.me(handles)
        mine = [c for c in self._comments(key) if sync.is_status(c.get("body") or "") and who(c["user"], handles).lower() == me]
        if mine:
            done = self.call("mutation CommentUpdate($id: String!, $input: CommentUpdateInput!) { commentUpdate(id: $id, input: $input) { comment { id url } } }",
                             {"id": mine[0]["id"], "input": {"body": body}})
            return done["commentUpdate"]["comment"]["url"]
        done = self.call("mutation CommentCreate($input: CommentCreateInput!) { commentCreate(input: $input) { comment { id url } } }",
                         {"input": {"issueId": key, "body": body}})
        return done["commentCreate"]["comment"]["url"]


if __name__ == "__main__":
    sys.exit(sync.main(["linear", *sys.argv[1:]], prog="sync.py"))

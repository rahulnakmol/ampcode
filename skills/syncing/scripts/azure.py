#!/usr/bin/env python3
"""Azure DevOps (Azure Boards) adapter for sync.py, over REST API 7.1. Not tested live.

  sync.py azure plan   backlog.json --org ORG --project NAME [--process agile|scrum|basic]
  sync.py azure apply  backlog.json --org ORG --project NAME --expect DIGEST [--overwrite ID,...]
  sync.py azure pull   backlog.json --org ORG --project NAME [--since YYYY-MM-DD]
  sync.py azure report backlog.json --org ORG --project NAME [--post]

Each backlog item is one work item. Agile process: initiative and goal are Epics (a goal is
tagged `goal`), feature is a Feature, story a User Story, bug a Bug. Scrum makes stories and bugs
Product Backlog Items; Basic makes them Issues, and features Epics (Basic has no Feature type).
Parents use the hierarchy link. Milestones are iterations matched by title without case
(characters Azure does not allow in a name, such as ':', become ' - '). The tag `backlog:<ID>`
is the identity. The personal access token (Work Items read and write) comes from
AZURE_DEVOPS_EXT_PAT and is never printed. Standard library only. Running this file is the
same as `sync.py azure …`.
"""

import base64
import html
import re
import sys
from urllib.parse import quote

import sync

TOKEN = "AZURE_DEVOPS_EXT_PAT"
API = "api-version=7.1"
COMMENTS_API = "api-version=7.1-preview.4"
PARENT = "System.LinkTypes.Hierarchy-Reverse"
# The signed-in user, as Microsoft's own Python SDK reads it (LocationClient.get_connection_data).
# Not in the published REST reference; not tested live. Profiles - Get would refuse a PAT.
CONNECTION = "_apis/connectionData?api-version=7.1-preview.1"
TYPES = {
    "agile": {"initiative": "Epic", "goal": "Epic", "feature": "Feature", "story": "User Story", "bug": "Bug"},
    "scrum": {"initiative": "Epic", "goal": "Epic", "feature": "Feature", "story": "Product Backlog Item", "bug": "Product Backlog Item"},
    "basic": {"initiative": "Epic", "goal": "Epic", "feature": "Epic", "story": "Issue", "bug": "Issue"},
}
CLOSED = {"Closed", "Done", "Removed"}
ID_TAG = re.compile(r"backlog:([IGFSB]-\d+)", re.I)
NOT_IN_NAMES = re.compile(r'\s*[\\/$?*:"&<>#%|+]+\s*')


def transport(token, opener=None):
    """call(method, path, body) on https://dev.azure.com/<path>. A list body is a JSON Patch."""
    auth = {"Authorization": "Basic " + base64.b64encode(f":{token}".encode()).decode()}

    def call(method, path, body=None):
        kind = "application/json-patch+json" if isinstance(body, list) else "application/json"
        return sync.http_json(method, f"https://dev.azure.com/{path}", auth, body, kind, opener)
    return call


def iteration_name(title):
    """A milestone title as an iteration name: Azure refuses \\ / $ ? * : " & < > # % | + in names."""
    return NOT_IN_NAMES.sub(" - ", title).strip(" -") if title else None


def plain(text):
    """Comment text without HTML: the ends of blocks become line breaks."""
    text = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|h\d)>", "\n", text or "")
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _tags(fields):
    return [t.strip() for t in (fields.get("System.Tags") or "").split(";") if t.strip()]


def _own(tag):
    low = tag.lower()
    return low in ("backlog", "goal") or low.startswith(sync.OWN_LABEL_PREFIXES + ("backlog:",))


class Azure:
    name, tracker, noun, marker = "azure", "Azure Boards", "a work item", "backlog:ID tag"
    label_word, milestone_word, link_kind = "tags", "iteration", "child"

    def __init__(self, org, project, process="agile", call=None):
        self.org, self.project, self.types = org, project, TYPES[process]
        self.call = call or transport(sync.secret(TOKEN, "an Azure DevOps personal access token with Work Items read and write"))
        self.api = f"{quote(org)}/{quote(project)}/_apis/wit"
        self.target = ("azure", org, project, process)  # bound into the plan digest
        self._names = None

    @staticmethod
    def body_field(kind):
        return "Microsoft.VSTS.TCM.ReproSteps" if kind == "Bug" else "System.Description"

    def view(self, data, item, base):
        title, body, labels, milestone = sync.render(data, item, base)
        tags = set(labels) | {f"backlog:{item['id']}"} | ({"goal"} if item["type"] == "goal" else set())
        return {"title": title, "body": body.replace(f"\n\n<!-- backlog:{item['id']} -->", ""), "labels": sorted(tags),
                "milestone": self.milestone_title(milestone), "kind": self.types[item["type"]]}

    def _iteration_names(self):
        """{lower-case name: name} of the iterations under the project root. Azure ignores case."""
        if self._names is None:
            root = self.call("GET", f"{self.api}/classificationnodes/Iterations?$depth=1&{API}") or {}
            self._names = {c["name"].lower(): c["name"] for c in root.get("children") or []}
        return self._names

    def milestone_title(self, title):
        """The iteration name for a milestone title: an existing iteration's own casing, if any."""
        name = iteration_name(title)
        return self._iteration_names().get(name.lower(), name) if name else None

    def _rec(self, wi):
        f = wi["fields"]
        ids = [m.group(1).upper() for t in _tags(f) if (m := ID_TAG.fullmatch(t))]
        path = f.get("System.IterationPath") or ""
        parents = [r["url"] for r in wi.get("relations") or [] if r.get("rel") == PARENT]
        return {"key": wi["id"], "iid": ids[0] if ids else None, "title": f.get("System.Title") or "",
                "body": f.get(self.body_field(f.get("System.WorkItemType"))) or "",
                "labels": sorted(t for t in _tags(f) if _own(t)),
                "milestone": path.split("\\", 1)[1] if "\\" in path else None,
                "parent": int(parents[0].rstrip("/").rsplit("/", 1)[1]) if parents else None,
                "state": "closed" if f.get("System.State") in CLOSED else "open",
                "url": f"https://dev.azure.com/{quote(self.org)}/{quote(self.project)}/_workitems/edit/{wi['id']}",
                "at": f.get("System.ChangedDate")}

    def items(self):
        """({backlog ID: work item}, {backlog ID: [work item IDs]} for IDs on more than one)."""
        query = {"query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.Tags] CONTAINS 'backlog'"}
        ids = [w["id"] for w in (self.call("POST", f"{self.api}/wiql?{API}", query) or {}).get("workItems", [])]
        found, dupes = {}, {}
        for n in range(0, len(ids), 200):  # the batch read takes at most 200 IDs
            batch = ",".join(str(i) for i in ids[n:n + 200])
            for wi in self.call("GET", f"{self.api}/workitems?ids={batch}&$expand=all&{API}")["value"]:
                rec = self._rec(wi)
                if rec["iid"] in found:
                    dupes.setdefault(rec["iid"], [found[rec["iid"]]["key"]]).append(rec["key"])
                if rec["iid"]:
                    found[rec["iid"]] = rec
        return found, dupes

    def exists(self, key):
        try:
            return bool(self.call("GET", f"{self.api}/workitems/{key}?{API}"))
        except RuntimeError:
            return False

    def milestones(self):
        self._names = None  # read them fresh for each plan
        return set(self._iteration_names().values())

    def missing_labels(self, wanted):
        return []  # Azure Boards creates a tag the first time a work item uses it

    def create_milestone(self, a):
        body = {"name": a["title"]}
        if a["start"] and a["due"]:
            body["attributes"] = {"startDate": f"{a['start']}T00:00:00Z", "finishDate": f"{a['due']}T00:00:00Z"}
        self.call("POST", f"{self.api}/classificationnodes/Iterations?{API}", body)
        self._iteration_names()[a["title"].lower()] = a["title"]

    def _content(self, a):
        field = self.body_field(a["kind"])
        return [{"op": "add", "path": "/fields/System.Title", "value": a["title"]},
                {"op": "add", "path": f"/fields/{field}", "value": a["body"]},
                {"op": "add", "path": f"/multilineFieldsFormat/{field}", "value": "Markdown"}]

    def _path(self, milestone):
        return f"{self.project}\\{milestone}" if milestone else self.project

    def _patch(self, key, ops):
        return self.call("PATCH", f"{self.api}/workitems/{key}?{API}", ops)

    def create(self, a):
        ops = self._content(a) + [{"op": "add", "path": "/fields/System.Tags", "value": "; ".join(a["labels"])},
                                  {"op": "add", "path": "/fields/System.IterationPath", "value": self._path(a["milestone"])}]
        return self._rec(self.call("POST", f"{self.api}/workitems/${quote(a['kind'])}?{API}", ops))

    def update(self, key, a):
        return self._rec(self._patch(key, self._content(a)))

    def set_labels(self, key, add, remove):
        tags = _tags(self.call("GET", f"{self.api}/workitems/{key}?{API}")["fields"])
        keep = sorted({t for t in tags if t not in remove} | set(add))
        self._patch(key, [{"op": "replace", "path": "/fields/System.Tags", "value": "; ".join(keep)}])

    def set_milestone(self, key, milestone):
        self._patch(key, [{"op": "add", "path": "/fields/System.IterationPath", "value": self._path(milestone)}])

    def link(self, child, parent, replace=False):
        """Link child under parent; with replace, remove its present parent link first (one parent only).
        The removal names links by position, so the patch first tests the revision it read: if the
        work item changed in between, Azure refuses the whole patch."""
        ops = []
        if replace:
            work = self.call("GET", f"{self.api}/workitems/{child}?$expand=relations&{API}")
            ops.append({"op": "test", "path": "/rev", "value": work["rev"]})
            ops += [{"op": "remove", "path": f"/relations/{n}"} for n, r in enumerate(work.get("relations") or []) if r.get("rel") == PARENT]
        url = f"https://dev.azure.com/{quote(self.org)}/_apis/wit/workItems/{parent}"
        self._patch(child, ops + [{"op": "add", "path": "/relations/-", "value": {"rel": PARENT, "url": url}}])

    def _comments(self, key):
        found, token = [], None
        while True:
            more = f"&continuationToken={quote(token)}" if token else ""
            page = self.call("GET", f"{self.api}/workItems/{key}/comments?{COMMENTS_API}{more}") or {}
            found += page.get("comments") or []
            token = page.get("continuationToken")
            if not token:
                return found

    def comments(self, key, handles):
        """[(login, url, text, created)] for each comment on a work item; login is the UPN."""
        return [(c["createdBy"]["uniqueName"], c["url"], plain(c.get("text")), c["createdDate"])
                for c in self._comments(key) if (c.get("createdBy") or {}).get("uniqueName")]

    def me(self, handles):
        """The signed-in user's sign-in name (UPN), to tell your own comments from stakeholders'."""
        user = (self.call("GET", f"{quote(self.org)}/{CONNECTION}") or {}).get("authenticatedUser") or {}
        account = str(((user.get("properties") or {}).get("Account") or {}).get("$value") or "").lower()
        if not account:
            raise RuntimeError("Azure DevOps did not return the signed-in user (connectionData); cannot tell your own comments apart")
        return account

    def post_status(self, key, body, handles):
        me, path = self.me(handles), f"{self.api}/workItems/{key}/comments"
        mine = [c for c in self._comments(key) if sync.is_status(plain(c.get("text")))
                and ((c.get("createdBy") or {}).get("uniqueName") or "").lower() == me]
        if mine:
            self.call("PATCH", f"{path}/{mine[0]['id']}?format=markdown&{COMMENTS_API}", {"text": body})
        else:
            self.call("POST", f"{path}?format=markdown&{COMMENTS_API}", {"text": body})
        return f"https://dev.azure.com/{quote(self.org)}/{quote(self.project)}/_workitems/edit/{key}"


if __name__ == "__main__":
    sys.exit(sync.main(["azure", *sys.argv[1:]], prog="sync.py"))

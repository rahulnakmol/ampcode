#!/usr/bin/env python3
"""Copy a backlog/v1 file to trackers and read sign-off and feedback back.

  sync.py github plan   backlog.json --repo OWNER/NAME [--project OWNER/NUMBER]   read-only; prints a digest
  sync.py github apply  backlog.json --repo OWNER/NAME [--project …] --expect DIGEST [--overwrite ID,...]
  sync.py github pull   backlog.json --repo OWNER/NAME [--since YYYY-MM-DD]       sign-offs, feedback, closed state
  sync.py github report backlog.json --repo OWNER/NAME [--post]                   status comment for stakeholders
  sync.py excel backlog.json --out backlog.xlsx                                   spreadsheet export

GitHub calls go through the signed-in `gh` CLI. Standard library only. Needs the `grooming`
skill installed beside this one: its backlog.py owns the contract.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "grooming" / "scripts"))
try:
    import backlog  # noqa: E402
except ImportError:
    sys.exit("error: the grooming skill must be installed beside syncing (needs grooming/scripts/backlog.py)")

ORDER = {"initiative": 0, "goal": 1, "feature": 2, "story": 3, "bug": 4}
OWN_LABEL_PREFIXES = ("type:", "work:", "priority:", "size:", "urgency:", "status:", "domain:")
LABEL_COLORS = {"backlog": "5319e7", "type": "1d76db", "work": "0e8a16", "priority": "d93f0b",
                "size": "c5def5", "urgency": "b60205", "status": "fbca04", "domain": "006b75"}
MARKER = re.compile(r"<!-- backlog:([IGFSB]-\d+) -->")
REPORT_MARKER = "<!-- backlog:report -->"
MAX_BODY = 60000
SIGN_OFF = "_To sign off, comment `/approve` as the first line. Any other comment is recorded as feedback._"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_a(actor):
    """'As an AP clerk' / 'As the nightly job': the article follows the actor's first word."""
    actor = (actor or "").strip()
    if actor.lower().startswith(("a ", "an ", "the ")):
        return f"As {actor}"
    return f"As {'an' if actor[:1].lower() in 'aeiou' and actor else 'a'} {actor}"


def content_hash(title, body):
    return "sha256:" + hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()


# Rendering ------------------------------------------------------------------------------------

def render(data, item, base):
    """Title, body, labels, and milestone title for one item. Only title and body are hashed."""
    kids = backlog.children(data)
    kind, lines = item["type"], []
    add = lines.append
    if kind == "initiative":
        add(f"**Problem.** {item['problem']}\n")
        add("**Business drivers**\n")
        lines.extend(f"- **{d['id']}** {d['statement']}" for d in item["drivers"])
        add(f"\n**Outcome.** {item['outcome']}\n\n**Owner.** {item['owner']}\n")
        if item.get("non_goals"):
            add("**Non-goals**\n")
            lines.extend(f"- {g}" for g in item["non_goals"])
            add("")
        goals = sorted((k for k in kids.get(item["id"], []) if k["type"] == "goal"), key=lambda k: backlog.id_key(k["id"]))
        if goals:
            add("**Goals**\n")
            lines.extend(f"- **{g['id']}** {g['title']}: {g['baseline']} → {g['target']} by {g['by']}" for g in goals)
            add("")
        if item.get("prd"):
            prd = Path(base) / item["prd"]
            if not prd.exists():
                raise RuntimeError(f"{item['id']}: PRD '{item['prd']}' not found; stakeholders would sign off without it")
            add("<details><summary>Full PRD (part of what you approve)</summary>\n\n" + prd.read_text(encoding="utf-8").strip() + "\n\n</details>\n")
        add(SIGN_OFF)
    elif kind == "goal":
        parent = backlog.items_by_id(data)[item["parent"]]
        drivers = {d["id"]: d["statement"] for d in parent["drivers"]}
        add(f"**Metric.** {item['metric']}\n\n**Baseline → target.** {item['baseline']} → {item['target']} by {item['by']}\n")
        add("**Serves drivers**\n")
        lines.extend(f"- **{d}** {drivers.get(d, '')}" for d in item["drivers"])
        add("")
    elif kind == "feature":
        add(f"{item['description']}\n\n**Benefit hypothesis.** {item['benefit_hypothesis']}\n")
        if item.get("acceptance"):
            add("**Feature acceptance**\n")
            lines.extend(f"- {a}" for a in item["acceptance"])
            add("")
        stories = sorted((k for k in kids.get(item["id"], []) if k["type"] == "story"), key=lambda k: backlog.id_key(k["id"]))
        add("**Stories your sign-off covers**\n")
        lines.extend(f"- **{s['id']}** {s['title']} ({s.get('size')}, {s.get('priority')})" for s in stories)
        add("\n" + SIGN_OFF)
    elif kind == "story":
        add(f"**{as_a(item.get('as_a'))}**, **I want** {item.get('i_want', '')}, **so that** {item.get('so_that', '')}.\n")
        _criteria(item, add)
    else:
        add(f"**Observed.** {item.get('observed', '')}\n\n**Expected.** {item.get('expected', '')}\n")
        add("**Steps to reproduce**\n")
        steps = item.get("steps") if isinstance(item.get("steps"), list) else [item.get("steps") or ""]
        lines.extend(f"{n}. {s}" for n, s in enumerate(steps, 1))
        add("")
        if item.get("environment"):
            add(f"**Environment.** {item['environment']}\n")
        _criteria(item, add)
    if kind in ("story", "bug") and item.get("depends_on"):
        add(f"**Depends on:** {', '.join(item['depends_on'])}\n")
    if kind in ("feature", "story", "bug") and item.get("owner"):
        add(f"**Owner:** {item['owner']}\n")
    if item.get("trace"):
        add(f"**Sources in the plan:** {', '.join(item['trace'])}\n")
    if item.get("notes"):
        add(f"**Notes.** {item['notes']}\n")
    add(f"<!-- backlog:{item['id']} -->")
    body = "\n".join(lines)
    if len(body) > MAX_BODY:
        raise RuntimeError(f"{item['id']}: tracker body is {len(body)} characters; GitHub allows 65,536. Shorten it (for a PRD, link the file instead)")
    title = f"[{item['id']}] {item['title']}"

    labels = ["backlog", f"type:{kind}"]
    for field in ("domain", "work", "priority", "size", "urgency", "status"):
        if item.get(field):
            labels.append(f"{field}:{item[field]}")
    return title, body, labels, _milestone_title(data, item)


def _criteria(item, add):
    add("**Acceptance criteria (definition of done)**\n")
    for ac in item.get("acceptance") or []:
        add(f"- [ ] **{ac.get('id')}** Given {ac.get('given')}, when {ac.get('when')}, then {ac.get('then')}.")
    add("")


def _milestone_title(data, item):
    ids = backlog.items_by_id(data)
    mid = item.get("milestone")
    if not mid and item["type"] in ("story", "bug"):
        mid = ids.get(item.get("parent"), {}).get("milestone")
    titles = {m["id"]: m["title"] for m in data.get("milestones", [])}
    return titles.get(mid)


# GitHub ---------------------------------------------------------------------------------------

def gh_call(method, path, body=None, paginate=False):
    args = ["gh", "api", "--method", method, path]
    if paginate:
        args += ["--paginate", "--slurp"]
    if body is not None:
        args += ["--input", "-"]
    run = subprocess.run(args, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(f"gh api {method} {path} failed: {run.stderr.strip() or run.stdout.strip()}")
    if not run.stdout.strip():
        return None
    result = json.loads(run.stdout)
    return [x for page in result for x in page] if paginate else result


class GitHub:
    def __init__(self, repo, call=gh_call):
        self.repo, self.call = repo, call
        self._me = None

    def graphql(self, query, variables):
        result = self.call("POST", "graphql", {"query": query, "variables": variables}) or {}
        if result.get("errors"):
            raise RuntimeError("GitHub GraphQL: " + "; ".join(e.get("message", "?") for e in result["errors"]))
        return result["data"]

    def path(self, suffix):
        return f"repos/{self.repo}/{suffix}"

    def me(self):
        if self._me is None:
            self._me = ((self.call("GET", "user") or {}).get("login") or "").lower()
        return self._me

    def issues(self):
        """({backlog ID: issue}, {backlog ID: [issue numbers]} for IDs found on more than one issue)."""
        found, dupes = {}, {}
        for issue in self.call("GET", self.path("issues?state=all&per_page=100"), paginate=True):
            if "pull_request" in issue:
                continue
            match = MARKER.search(issue.get("body") or "")
            if match:
                iid = match.group(1)
                if iid in found:
                    dupes.setdefault(iid, [found[iid]["number"]]).append(issue["number"])
                found[iid] = issue
        return found, dupes

    def issue(self, number):
        try:
            return self.call("GET", self.path(f"issues/{number}"))
        except RuntimeError:
            return None


def _own_labels(issue):
    return sorted(l["name"] for l in issue.get("labels", []) if l["name"].lower() == "backlog" or l["name"].lower().startswith(OWN_LABEL_PREFIXES))


def plan(data, base, gh, overwrite=(), project=None):
    """Actions apply would take, in order. Reads GitHub; changes nothing.

    An item is a conflict, and nothing is done to it, when GitHub holds something this file did not
    write: a title, body, label, or milestone edited since the last sync, an issue with this ID that
    the file has no record of, a removed marker, or the same marker on two issues."""
    actions, conflicts = [], set()
    remote, dupes = gh.issues()
    milestones = {m["title"]: m for m in gh.call("GET", gh.path("milestones?state=all&per_page=100"), paginate=True)}
    labels = {l["name"].lower() for l in gh.call("GET", gh.path("labels?per_page=100"), paginate=True)}

    def conflict(item, number, why):
        conflicts.add(item["id"])
        actions.append({"do": "conflict", "id": item["id"], "number": number, "why": why})

    for m in data.get("milestones", []):
        due = f"{m['due']}T12:00:00Z" if m.get("due") else None
        have = milestones.get(m["title"])
        if not have:
            actions.append({"do": "create milestone", "title": m["title"], "due_on": due})
        elif due and (have.get("due_on") or "")[:10] != m["due"]:
            actions.append({"do": "update milestone", "title": m["title"], "number": have["number"], "due_on": due})

    wanted_labels = set()
    items = sorted(data["items"], key=lambda i: (ORDER[i["type"]], backlog.id_key(i["id"])))
    for item in items:
        title, body, want, milestone = render(data, item, base)
        wanted_labels.update(want)
        ext = (item.get("external") or {}).get("github") or {}
        forced = item["id"] in overwrite
        if item["id"] in dupes:
            conflict(item, dupes[item["id"]][0], f"marker found on issues {dupes[item['id']]}; close the extra issues")
            continue
        issue = remote.get(item["id"])
        if not issue:
            if ext.get("number") and gh.issue(ext["number"]) and not forced:
                conflict(item, ext["number"], "its marker was removed in GitHub; restore it or pass --overwrite to create a new issue")
            else:
                actions.append({"do": "create", "id": item["id"], "title": title, "body": body, "labels": want, "milestone": milestone})
            continue
        number = issue["number"]
        remote_hash = content_hash(issue["title"], issue.get("body") or "")
        new_hash = content_hash(title, body)
        remote_ms = (issue.get("milestone") or {}).get("title")
        if not forced:
            if not ext.get("hash") and remote_hash != new_hash:
                conflict(item, number, "an issue with this ID exists but this file has no record of syncing it (another backlog, or lost sync fields); merge, or pass --overwrite")
                continue
            if ext.get("hash") and remote_hash != ext["hash"]:
                conflict(item, number, "title or body edited in GitHub since the last sync; merge the edit into backlog.json, or pass --overwrite")
                continue
            if "labels" in ext and _own_labels(issue) != sorted(ext["labels"]):
                conflict(item, number, f"labels changed in GitHub since the last sync (now {_own_labels(issue)}); merge, or pass --overwrite")
                continue
            if "milestone" in ext and remote_ms != ext["milestone"]:
                conflict(item, number, f"milestone changed in GitHub to {remote_ms!r}; merge, or pass --overwrite")
                continue
        if remote_hash != new_hash:
            actions.append({"do": "update", "id": item["id"], "number": number, "title": title, "body": body,
                            "diff": _diff(issue.get("body") or "", body)})
        elif ext.get("number") != number or ext.get("hash") != new_hash:
            actions.append({"do": "record", "id": item["id"], "number": number, "issue_id": issue["id"],
                            "url": issue["html_url"], "hash": new_hash, "updated_at": issue.get("updated_at")})
        have = {l.lower(): l for l in _own_labels(issue)}
        add = sorted(l for l in want if l.lower() not in have)
        remove = sorted(name for low, name in have.items() if low not in {w.lower() for w in want})
        if add or remove:
            actions.append({"do": "labels", "id": item["id"], "number": number, "add": add, "remove": remove})
        if remote_ms != milestone:
            actions.append({"do": "milestone", "id": item["id"], "number": number, "milestone": milestone})

    missing_labels = sorted(l for l in wanted_labels if l.lower() not in labels)
    if missing_labels:
        actions.insert(0, {"do": "create labels", "labels": missing_labels})

    for item in items:
        if item["type"] == "initiative" or item["id"] in conflicts or item["parent"] in conflicts:
            continue
        parent_issue, child_issue = remote.get(item["parent"]), remote.get(item["id"])
        if parent_issue and child_issue:
            subs = {s["number"] for s in gh.call("GET", gh.path(f"issues/{parent_issue['number']}/sub_issues?per_page=100"), paginate=True)}
            if child_issue["number"] in subs:
                continue
        actions.append({"do": "link", "id": item["id"], "parent": item["parent"]})

    ids = backlog.items_by_id(data)
    for iid, issue in sorted(remote.items(), key=lambda kv: backlog.id_key(kv[0])):
        if iid not in ids:
            actions.append({"do": "orphan", "id": iid, "number": issue["number"],
                            "why": "in GitHub but not in backlog.json; close or re-add it by hand"})
    if project:
        actions += plan_project(data, gh, project, remote, conflicts, overwrite)
    return actions


def plan_digest(actions):
    """Short fingerprint of a plan, so apply runs exactly the plan the user approved."""
    stable = [{k: v for k, v in a.items() if k != "diff"} for a in actions]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:12]


def _diff(old, new):
    import difflib
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "github", "backlog.json", lineterm="", n=1))
    return "\n".join(lines[:40] + (["…"] if len(lines) > 40 else []))


def apply(data, base, gh, project=None, overwrite=(), expect=None):
    """Run the plan and record what was written in data. Returns the actions done.

    With expect, refuse to run unless the plan's digest matches the one the user approved."""
    actions = plan(data, base, gh, overwrite, project)
    if expect is not None and plan_digest(actions) != expect:
        raise RuntimeError(f"the plan changed since it was approved (digest {plan_digest(actions)}, expected {expect}); review the new plan")
    ids = backlog.items_by_id(data)
    numbers = {m["title"]: m["number"] for m in gh.call("GET", gh.path("milestones?state=all&per_page=100"), paginate=True)}
    remote, _ = gh.issues()
    done, conflicts = [], {a["id"] for a in actions if a["do"] == "conflict"}
    for a in actions:
        do = a["do"]
        if do == "create labels":
            for name in a["labels"]:
                gh.call("POST", gh.path("labels"), {"name": name, "color": LABEL_COLORS[name.split(":")[0]]})
        elif do == "create milestone":
            body = {"title": a["title"], **({"due_on": a["due_on"]} if a["due_on"] else {})}
            numbers[a["title"]] = gh.call("POST", gh.path("milestones"), body)["number"]
        elif do == "update milestone":
            gh.call("PATCH", gh.path(f"milestones/{a['number']}"), {"due_on": a["due_on"]})
        elif do == "create":
            body = {"title": a["title"], "body": a["body"], "labels": a["labels"]}
            if a["milestone"]:
                body["milestone"] = numbers[a["milestone"]]
            issue = gh.call("POST", gh.path("issues"), body)
            remote[a["id"]] = issue
            _record(ids[a["id"]], issue, content_hash(a["title"], a["body"]), changed=True)
        elif do == "update":
            issue = gh.call("PATCH", gh.path(f"issues/{a['number']}"), {"title": a["title"], "body": a["body"]})
            _record(ids[a["id"]], issue, content_hash(a["title"], a["body"]), changed=True)
        elif do == "record":
            _record(ids[a["id"]], {"number": a["number"], "id": a["issue_id"], "html_url": a["url"],
                                   "updated_at": a["updated_at"]}, a["hash"], changed=False)
        elif do == "labels":
            if a["add"]:
                gh.call("POST", gh.path(f"issues/{a['number']}/labels"), {"labels": a["add"]})
            for name in a["remove"]:
                gh.call("DELETE", gh.path(f"issues/{a['number']}/labels/{quote(name, safe='')}"))
        elif do == "milestone":
            gh.call("PATCH", gh.path(f"issues/{a['number']}"), {"milestone": numbers[a["milestone"]] if a["milestone"] else None})
        elif do == "link":
            parent, child = remote[a["parent"]], remote[a["id"]]
            try:
                gh.call("POST", gh.path(f"issues/{parent['number']}/sub_issues"), {"sub_issue_id": child["id"]})
            except RuntimeError as exc:
                a = {"do": "conflict", "id": a["id"], "number": child["number"],
                     "why": f"could not link under {a['parent']} (moved to another parent in GitHub?): {exc}"}
                conflicts.add(a["id"])
        done.append(a)
    if project:
        apply_project(data, gh, project, actions, remote)
    for item in data["items"]:
        ext = (item.get("external") or {}).get("github")
        if ext and item["id"] not in conflicts:
            _, _, want, milestone = render(data, item, base)
            ext.update({"labels": sorted(want), "milestone": milestone, "fingerprint": backlog.fingerprint(item, base)})
    return done


def _record(item, issue, digest, changed):
    ext = item.setdefault("external", {}).get("github") or {}
    ext.update({"number": issue["number"], "id": issue["id"], "url": issue["html_url"], "hash": digest})
    if changed or "synced_at" not in ext:
        ext["synced_at"] = issue.get("updated_at") or now()
    ext.setdefault("state", "open")
    item["external"]["github"] = ext


def pull(data, gh, since=None):
    """Record sign-offs, open feedback, and tracker state. Returns a report dict."""
    ids = backlog.items_by_id(data)
    handles = {a["github"].lower(): a["github"] for a in data.get("approvers", []) if a.get("github")}
    me = gh.me()
    by_number = {((i.get("external") or {}).get("github") or {}).get("number"): i for i in data["items"]}
    by_number.pop(None, None)
    report = {"approvals": [], "feedback": [], "triage": [], "ignored": [], "closed_without_delivery": []}

    remote, _ = gh.issues()
    for iid, issue in remote.items():
        item = ids.get(iid)
        if item and "github" in (item.get("external") or {}):
            item["external"]["github"]["state"] = issue["state"]
            if issue["state"] == "closed" and item["type"] in ("story", "bug") and not item.get("delivery"):
                report["closed_without_delivery"].append(iid)

    query = "issues/comments?per_page=100" + (f"&since={since}T00:00:00Z" if since else "")
    known = {fb.get("source") for fb in data.get("feedback", [])}
    feedback = data.setdefault("feedback", [])
    next_fb = max([int(fb["id"][3:]) for fb in feedback] + [0]) + 1
    for c in gh.call("GET", gh.path(query), paginate=True):
        item = by_number.get(int(c["issue_url"].rsplit("/", 1)[1]))
        login, url, body = c["user"]["login"], c["html_url"], (c.get("body") or "").strip()
        if not item or c["user"].get("type") == "Bot" or url in known or REPORT_MARKER in body:
            continue
        first = body.splitlines()[0].strip().lower() if body else ""
        if first == "/approve" and item["type"] in ("initiative", "feature"):
            if login.lower() in handles:
                if url not in {a.get("url") for a in item.get("approvals", [])}:
                    item.setdefault("approvals", []).append({"tracker": "github", "by": handles[login.lower()], "at": c["created_at"], "url": url})
                    report["approvals"].append(f"{item['id']} by {login}")
                continue
            report["ignored"].append(f"/approve on {item['id']} by {login}, who is not an approver; treated as a comment")
        if login.lower() == me:
            continue
        summary = " ".join(body.split())[:300]
        if item["type"] in ("initiative", "goal"):
            report["triage"].append({"item": item["id"], "from": login, "at": c["created_at"], "url": url, "summary": summary})
            continue
        feature = item["id"] if item["type"] == "feature" else item["parent"]
        feedback.append({"id": f"FB-{next_fb}", "feature": feature, "from": login, "summary": summary or "(empty comment)",
                         "source": url, "at": c["created_at"], "disposition": "open"})
        report["feedback"].append(f"FB-{next_fb} on {feature} from {login}")
        known.add(url)
        next_fb += 1
    if not feedback:
        data.pop("feedback")
    return report


def report_comment(data, base, today):
    """The status comment for stakeholders: the trace report, trimmed to fit a GitHub comment."""
    text, _ = backlog.trace_report(data, base, today)
    # Planner housekeeping, not something stakeholders can act on.
    text = "\n".join(line for line in text.splitlines() if not line.startswith("Evidence not traced")) + "\n"
    if len(text) > MAX_BODY:
        head, _, rest = text.partition("## Stories and bugs")
        text = head + "_Stories and bugs omitted for length; see the backlog export._\n\n" + rest[rest.find("## Feedback"):] if "## Feedback" in rest else head
    return f"{REPORT_MARKER}\n_Status from the planning backlog, updated {today}. Edits here are overwritten._\n\n{text}"


def post_report(data, base, gh, today):
    """Create or update one status comment on each synced initiative issue. Returns their URLs."""
    body, urls = report_comment(data, base, today), []
    for item in data["items"]:
        number = ((item.get("external") or {}).get("github") or {}).get("number")
        if item["type"] != "initiative" or not number:
            continue
        mine = [c for c in gh.call("GET", gh.path(f"issues/{number}/comments?per_page=100"), paginate=True)
                if REPORT_MARKER in (c.get("body") or "") and c["user"]["login"].lower() == gh.me()]
        if mine:
            urls.append(gh.call("PATCH", gh.path(f"issues/comments/{mine[0]['id']}"), {"body": body})["html_url"])
        else:
            urls.append(gh.call("POST", gh.path(f"issues/{number}/comments"), {"body": body})["html_url"])
    return urls


# GitHub Projects ------------------------------------------------------------------------------

# The fields this script owns in a Project. Stakeholders may add their own; these are matched by
# name. "Status" is GitHub's built-in workflow field and is never touched.
PROJECT_FIELDS = [
    ("Item type", "single_select", ["initiative", "goal", "feature", "story", "bug"]),
    ("Priority", "single_select", ["must", "should", "could", "wont"]),
    ("Urgency", "single_select", ["critical", "high", "medium", "low"]),
    ("Size", "single_select", ["XS", "S", "M", "L", "XL"]),
    ("Readiness", "single_select", ["draft", "ready"]),
    ("Rank score", "number", None),
    ("Schedule", "iteration", None),
]
PROJECT_VIEWS = [
    # name, layout, filter, group by, sort by (field name, direction)
    ("Roadmap", "roadmap", 'label:"type:feature"', None, None),
    ("Backlog by milestone", "table", 'label:"type:story","type:bug"', "Schedule", ("Priority", "asc")),
]


def schedule(data):
    """[(title, start, days)] for milestones with a due date: the roadmap's time slots."""
    from datetime import date, timedelta
    slots, previous = [], None
    for m in sorted((m for m in data.get("milestones", []) if m.get("due")), key=lambda m: m["due"]):
        due = date.fromisoformat(m["due"])
        if m.get("start"):
            start = date.fromisoformat(m["start"])
        elif previous:
            start = previous + timedelta(days=1)
        else:
            raise RuntimeError(f"milestone {m['id']} needs a 'start' date to be placed on the Project roadmap")
        if previous and start <= previous:
            raise RuntimeError(f"milestone {m['id']} starts before the previous milestone ends; GitHub schedule slots cannot overlap")
        slots.append((m["title"], start.isoformat(), (due - start).days + 1))
        previous = due
    return slots


def project_values(data, item):
    """{field name: value} this script wants on an item's Project card; None clears the field."""
    kind = item["type"]
    work = kind in ("story", "bug")
    slot = _milestone_title(data, item)
    if slot not in {m["title"] for m in data.get("milestones", []) if m.get("due")}:
        slot = None  # a milestone without a due date has no slot on the schedule
    return {
        "Item type": kind,
        "Priority": item.get("priority") if work else None,
        "Urgency": item.get("urgency") if kind == "bug" else None,
        "Size": item.get("size") if work else None,
        "Readiness": item.get("status") if work else None,
        "Rank score": backlog.wsjf_score(item) if kind == "feature" else None,
        "Schedule": slot if kind in ("feature", "story", "bug") else None,
    }


def _text_value(value):
    """A Project field value from the REST API as plain text, whatever its shape."""
    if isinstance(value, dict):
        for key in ("name", "title"):
            if key in value:
                inner = value[key]
                return inner.get("raw") if isinstance(inner, dict) else inner
        return value.get("raw")
    return value


def _field_names(field):
    return [(_text_value(o.get("name")), o["id"]) for o in field.get("options") or []]


def _iterations(field):
    return [{"id": i["id"], "title": _text_value(i.get("title")), "startDate": i["start_date"], "duration": i["duration"]}
            for i in (field.get("configuration") or {}).get("iterations") or []]


class Project:
    def __init__(self, gh, spec):
        owner, _, number = spec.partition("/")
        if not number.isdigit():
            raise RuntimeError(f"--project must be OWNER/NUMBER, not {spec!r}")
        self.gh, self.owner, self.number = gh, owner, int(number)
        kind = (gh.call("GET", f"users/{owner}") or {}).get("type")
        self.scope = "orgs" if kind == "Organization" else "users"
        self.base = f"{self.scope}/{owner}/projectsV2/{number}"

    def fields(self):
        return {f["name"]: f for f in self.gh.call("GET", f"{self.base}/fields?per_page=100", paginate=True)}

    def items(self, field_ids):
        """{issue id: (project item id, {field name: value as text})}."""
        query = f"{self.base}/items?per_page=100" + "".join(f"&fields[]={i}" for i in field_ids)
        found = {}
        for it in self.gh.call("GET", query, paginate=True):
            content = it.get("content") or {}
            if it.get("content_type") != "Issue" or "id" not in content:
                continue
            values = {f.get("name"): _text_value(f.get("value")) for f in it.get("fields") or []}
            found[content["id"]] = (it["id"], values)
        return found

    def views(self):
        owner_field = "organization" if self.scope == "orgs" else "user"
        query = f"query($o:String!,$n:Int!){{ {owner_field}(login:$o){{ projectV2(number:$n){{ views(first:50){{ nodes{{ name }} }} }} }} }}"
        result = self.gh.graphql(query, {"o": self.owner, "n": self.number})
        return {v["name"] for v in result[owner_field]["projectV2"]["views"]["nodes"]}


def plan_project(data, gh, spec, remote, conflicts, overwrite):
    """Project actions: fields, schedule slots, cards, card values, and views. Reads only."""
    project = Project(gh, spec)
    actions, fields = [], project.fields()
    slots = schedule(data)
    for name, kind, options in PROJECT_FIELDS:
        have = fields.get(name)
        if not have:
            actions.append({"do": "project field", "name": name, "type": kind, "options": options,
                            "slots": slots if kind == "iteration" else None})
            continue
        if have.get("data_type") != kind:
            raise RuntimeError(f"Project field {name!r} exists as {have.get('data_type')}, not {kind}; rename it in GitHub")
        if options:
            missing = [o for o in options if o not in {n for n, _ in _field_names(have)}]
            if missing:
                raise RuntimeError(f"Project field {name!r} lacks options {missing}; add them in GitHub or rename the field")
        if kind == "iteration":
            existing = {i["title"]: i for i in _iterations(have)}
            if any(existing.get(t, {}).get("startDate") != s or existing.get(t, {}).get("duration") != d for t, s, d in slots):
                actions.append({"do": "project schedule", "slots": slots})

    cards = project.items([f["id"] for f in fields.values()]) if fields else {}
    for item in sorted(data["items"], key=lambda i: (ORDER[i["type"]], backlog.id_key(i["id"]))):
        if item["id"] in conflicts:
            continue
        issue = remote.get(item["id"])
        want = project_values(data, item)
        stored = ((item.get("external") or {}).get("github") or {}).get("project") or {}
        card = cards.get(issue["id"]) if issue else None
        if not card:
            actions.append({"do": "project add", "id": item["id"]})
            change = {k: v for k, v in want.items() if v is not None}
        else:
            current = {name: card[1].get(name) for name in want}
            if "fields" in stored:
                edited = [n for n in want if _same(current[n]) != _same(stored["fields"].get(n))]
            else:  # a card this file never wrote: values someone set by hand are not overwritten
                edited = [n for n in want if current[n] not in (None, "") and _same(current[n]) != _same(want[n])]
            if edited and item["id"] not in overwrite:
                actions.append({"do": "conflict", "id": item["id"], "number": issue["number"],
                                "why": f"Project fields {edited} changed in GitHub since the last sync; merge, or pass --overwrite"})
                continue
            change = {k: v for k, v in want.items() if _same(current[k]) != _same(v)}
        if change:
            actions.append({"do": "project values", "id": item["id"], "set": change})

    views = project.views()
    for name, layout, flt, group, sort in PROJECT_VIEWS:
        if name not in views:
            actions.append({"do": "project view", "name": name, "layout": layout, "filter": flt})
    return actions


def _same(value):
    """Compare Project values loosely: numbers as numbers, everything else as text."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def apply_project(data, gh, spec, actions, remote):
    """Run the Project actions from plan_project and record what was written."""
    project = Project(gh, spec)
    ids = backlog.items_by_id(data)
    fields = project.fields()
    for a in (a for a in actions if a["do"] == "project field"):
        body = {"name": a["name"], "data_type": a["type"]}
        if a["options"]:
            # Plain strings: the live API rejects the {raw, html} objects it returns (checked 2026-11-11).
            body["single_select_options"] = [{"name": o, "color": "GRAY", "description": ""} for o in a["options"]]
        if a["type"] == "iteration":
            slots = a["slots"] or [("Unscheduled", datetime.now().date().isoformat(), 14)]
            body["iteration_configuration"] = {"start_date": slots[0][1], "duration": slots[0][2],
                                               "iterations": [{"title": t, "start_date": s, "duration": d} for t, s, d in slots]}
        fields[a["name"]] = gh.call("POST", f"{project.base}/fields", body)
    for a in (a for a in actions if a["do"] == "project schedule"):
        field = fields["Schedule"]
        existing = {i["title"]: i for i in _iterations(field)}
        wanted = {t: {"title": t, "startDate": s, "duration": d, **({"id": existing[t]["id"]} if t in existing else {})} for t, s, d in a["slots"]}
        keep = [i for t, i in existing.items() if t not in wanted]  # slots stakeholders added stay
        merged = sorted(keep + list(wanted.values()), key=lambda i: i["startDate"])
        gh.graphql("mutation($f:ID!,$c:ProjectV2IterationFieldConfigurationInput!){ updateProjectV2Field(input:{fieldId:$f, iterationConfiguration:$c}){ clientMutationId } }",
                   {"f": field["node_id"], "c": {"startDate": merged[0]["startDate"], "duration": merged[0]["duration"], "iterations": merged}})
        fields = project.fields()
    field_ids = [f["id"] for f in fields.values()]
    cards = project.items(field_ids)
    for a in actions:
        if a["do"] == "project add":
            issue = remote[a["id"]]
            if issue["id"] not in cards:
                try:
                    cards[issue["id"]] = (gh.call("POST", f"{project.base}/items", {"type": "Issue", "id": issue["id"]})["id"], {})
                except RuntimeError as exc:
                    if "already exists" not in str(exc):
                        raise
                    cards = project.items(field_ids)  # GitHub adds a card's sub-issues by itself
        elif a["do"] == "project values":
            item_id = cards[remote[a["id"]]["id"]][0]
            updates = [{"id": fields[name]["id"], "value": _value_for(fields[name], value)} for name, value in a["set"].items()]
            gh.call("PATCH", f"{project.base}/items/{item_id}", {"fields": updates})
        elif a["do"] == "project view":
            name, layout, flt, group, sort = next(v for v in PROJECT_VIEWS if v[0] == a["name"])
            body = {"name": name, "layout": layout, "filter": flt}
            if group:
                body["group_by"] = [fields[group]["id"]]
            if sort:
                body["sort_by"] = [[fields[sort[0]]["id"], sort[1]]]
            gh.call("POST", f"{project.base}/views", body)
    for item in data["items"]:
        ext = (item.get("external") or {}).get("github")
        if ext and item["id"] in remote and not any(a["do"] == "conflict" and a.get("id") == item["id"] for a in actions):
            ext["project"] = {"project": spec, "fields": project_values(data, item)}


def _value_for(field, value):
    if value is None:
        return None
    if field.get("data_type") == "single_select":
        return dict(_field_names(field))[value]
    if field.get("data_type") == "iteration":
        match = [i["id"] for i in _iterations(field) if i["title"] == value]
        if not match:
            raise RuntimeError(f"no schedule slot named {value!r}; give its milestone a 'due' date")
        return match[0]
    return value


# Excel ----------------------------------------------------------------------------------------

def excel_rows(data, base, today=None):
    today = today or datetime.now().date().isoformat()
    ids, kids = backlog.items_by_id(data), backlog.children(data)
    head = ["ID", "Type", "Parent", "Title", "Statement", "Domain or work", "Priority", "Urgency", "Size",
            "Status", "WSJF", "Milestone", "Owner", "Depends on", "Drivers", "Traces to", "Sign-off", "Delivery", "Tracker link"]
    rows = [head]
    for item in sorted(data["items"], key=lambda i: (ORDER[i["type"]], backlog.id_key(i["id"]))):
        kind = item["type"]
        statement = {
            "initiative": lambda i: f"Problem: {i['problem']}\nOutcome: {i['outcome']}",
            "goal": lambda i: f"{i['metric']}: {i['baseline']} → {i['target']} by {i['by']}",
            "feature": lambda i: f"{i['description']}\nHypothesis: {i['benefit_hypothesis']}",
            "story": lambda i: f"{as_a(i.get('as_a'))}, I want {i.get('i_want', '')}, so that {i.get('so_that', '')}",
            "bug": lambda i: f"Observed: {i.get('observed', '')}\nExpected: {i.get('expected', '')}",
        }[kind](item)
        drivers = item.get("drivers") or []
        if kind == "initiative":
            drivers = [f"{d['id']}: {d['statement']}" for d in drivers]
        sign = backlog.approval_state(data, item, base=base) if kind in ("initiative", "feature") else ""
        delivery = backlog.delivery_state(item) if kind in ("story", "bug") else (
            backlog.goal_state(item, today) if kind == "goal" else "")
        rows.append([
            item["id"], kind, item.get("parent", ""), item["title"], statement,
            item.get("domain") or item.get("work") or "", item.get("priority", ""), item.get("urgency", ""),
            item.get("size", ""), item.get("status", ""), backlog.wsjf_score(item) if kind == "feature" else "",
            _milestone_title(data, item) or "", item.get("owner", ""), ", ".join(item.get("depends_on") or []),
            "\n".join(drivers), ", ".join(item.get("trace") or []), sign, delivery,
            ((item.get("external") or {}).get("github") or {}).get("url", ""),
        ])
    criteria = [["Item", "Criterion", "Given", "When", "Then", "Delivered"]]
    for item in data["items"]:
        result = (item.get("delivery") or {}).get("criteria") or {}
        for ac in item.get("acceptance") or []:
            if isinstance(ac, dict):
                criteria.append([item["id"], ac.get("id"), ac.get("given"), ac.get("when"), ac.get("then"), result.get(ac.get("id"), "")])
    fb = [["ID", "Feature", "From", "At", "Summary", "Disposition", "Resolution", "Source"]]
    fb += [[f["id"], f["feature"], f["from"], f.get("at", ""), f["summary"], f["disposition"], f.get("resolution", ""), f.get("source", "")]
           for f in data.get("feedback", [])]
    ms = [["ID", "Title", "Due"]] + [[m["id"], m["title"], m.get("due", "")] for m in data.get("milestones", [])]
    _, gaps = backlog.trace_report(data, base, today)
    return [("Backlog", rows), ("Acceptance criteria", criteria), ("Feedback", fb), ("Milestones", ms),
            ("Traceability gaps", [["Gap"]] + [[g] for g in gaps])]


def write_xlsx(path, sheets):
    """Minimal Office Open XML workbook: inline strings, bold frozen header, autofilter."""
    def col(n):
        name = ""
        while n:
            n, r = divmod(n - 1, 26)
            name = chr(65 + r) + name
        return name

    def sheet_xml(rows):
        widths = [min(60, max(8, *(len(str(r[c] if c < len(r) else "").split("\n")[0]) for r in rows))) for c in range(len(rows[0]))]
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
               '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
               "<cols>" + "".join(f'<col min="{i}" max="{i}" width="{w + 2}" customWidth="1"/>' for i, w in enumerate(widths, 1)) + "</cols>",
               "<sheetData>"]
        for r, row in enumerate(rows, 1):
            cells = []
            for c, value in enumerate(row, 1):
                ref, style = f"{col(c)}{r}", ' s="1"' if r == 1 else ' s="2"'
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
                elif value not in (None, ""):
                    text = escape(str(value)).replace('"', "&quot;")
                    cells.append(f'<c r="{ref}"{style} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
            out.append(f'<row r="{r}">{"".join(cells)}</row>')
        out.append("</sheetData>")
        out.append(f'<autoFilter ref="A1:{col(len(rows[0]))}{len(rows)}"/>')
        out.append("</worksheet>")
        return "".join(out)

    names = [escape(n) for n, _ in sheets]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets) + 1))
                   + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
                   + "</sheets>"
                   + "<definedNames>" + "".join(
                       f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i - 1}" hidden="1">\'{n}\'!$A$1:${col(len(rows[0]))}${len(rows)}</definedName>'
                       for i, (n, (_, rows)) in enumerate(zip(names, sheets), 1)) + "</definedNames></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1))
                   + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("xl/styles.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
                   '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                   '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                   '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
                   '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>'
                   '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                   "</styleSheet>")
        for i, (_, rows) in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))


# Commands -------------------------------------------------------------------------------------

def _load_valid(path):
    data = backlog.load(path)
    errors, _ = backlog.validate(data)
    if errors:
        for where, msg in errors:
            print(f"error   {where}: {msg}", file=sys.stderr)
        raise SystemExit("error: fix validation errors before syncing (backlog.py validate)")
    return data


def _save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _print_actions(actions):
    counts = {}
    for a in actions:
        counts[a["do"]] = counts.get(a["do"], 0) + 1
        target = a.get("id") or a.get("title") or ", ".join(a.get("labels", []))
        extra = a.get("why") or (f"#{a['number']}" if a.get("number") else "") or ""
        if a["do"] == "labels":
            extra = f"+{a['add']} -{a['remove']}"
        if a["do"] == "link":
            extra = f"sub-issue of {a['parent']}"
        if a["do"] == "project field":
            target = f"{a['name']} ({a['type']})"
        if a["do"] in ("project schedule",):
            target = ", ".join(t for t, _, _ in a["slots"])
        if a["do"] == "project values":
            extra = ", ".join(f"{k}={v}" for k, v in a["set"].items())
        if a["do"] == "project view":
            target = f"{a['name']} ({a['layout']}, {a['filter']})"
        print(f"{a['do']:16} {target} {extra}".rstrip())
        if a.get("diff"):
            print("\n".join("    " + line for line in a["diff"].splitlines()))
    print("plan: " + (", ".join(f"{n} {k}" for k, n in counts.items()) or "nothing to do"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="adapter", required=True)
    g = sub.add_parser("github", help="GitHub issues, sub-issues, milestones, and Projects")
    g.add_argument("action", choices=("plan", "apply", "pull", "report"))
    g.add_argument("file")
    g.add_argument("--repo", required=True, help="OWNER/NAME")
    g.add_argument("--project", help="OWNER/NUMBER of a GitHub Project: cards, fields, schedule, and roadmap views")
    g.add_argument("--overwrite", default="", help="comma-separated IDs whose GitHub edits may be overwritten")
    g.add_argument("--expect", help="apply: the digest printed by the plan the user approved")
    g.add_argument("--since", help="pull: only comments updated on or after YYYY-MM-DD")
    g.add_argument("--post", action="store_true", help="report: post or update the comment instead of printing it")
    g.add_argument("--today", default=datetime.now().date().isoformat(), help="report: date to judge goals against and stamp")
    x = sub.add_parser("excel", help="export to .xlsx")
    x.add_argument("file")
    x.add_argument("--out", required=True)
    x.add_argument("--today", default=datetime.now().date().isoformat(), help="date to judge goals against")
    args = parser.parse_args(argv)
    base = Path(args.file).resolve().parent

    try:
        if args.adapter == "excel":
            data = _load_valid(args.file)
            write_xlsx(args.out, excel_rows(data, base, args.today))
            print(f"wrote {args.out}")
            return 0
        data = _load_valid(args.file)
        gh = GitHub(args.repo)
        overwrite = tuple(i.strip() for i in args.overwrite.split(",") if i.strip())
        if args.action == "plan":
            actions = plan(data, base, gh, overwrite, args.project)
            _print_actions(actions)
            if actions:
                print(f"digest: {plan_digest(actions)}  (apply with --expect {plan_digest(actions)} once approved)")
            return 1 if any(a["do"] == "conflict" for a in actions) else 0
        if args.action == "report":
            today = args.today
            if not args.post:
                print(report_comment(data, base, today), end="")
                return 0
            print("\n".join(post_report(data, base, gh, today)))
            return 0
        if args.action == "apply":
            if not args.expect:
                raise RuntimeError("apply needs --expect DIGEST from a plan the user approved; run plan first")
            try:
                done = apply(data, base, gh, args.project, overwrite, args.expect)
            finally:
                _save(args.file, data)
            _print_actions(done)
            return 1 if any(a["do"] == "conflict" for a in done) else 0
        report = pull(data, gh, args.since)
        _save(args.file, data)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

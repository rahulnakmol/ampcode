---
name: syncing
description: "Copies a backlog.json (contract backlog/v1) into the tracker stakeholders use and reads their sign-off and feedback back: GitHub issues with sub-issues, labels, milestones, and an optional GitHub Project, a status comment showing what was agreed, delivered, and achieved, Azure DevOps work items or Linear issues (adapters not tested live), or an Excel workbook. Shows a read-only plan before every write and applies only that exact plan, never duplicates or overwrites edits made in the tracker, records /approve sign-offs from listed approvers, and files comments as feedback on the right feature. Use when asked to sync, push, publish, or export a groomed backlog to GitHub, Azure DevOps, Linear, or Excel, pull stakeholder comments or approvals, update stakeholders on progress, or check what a sync would change. Not for editing the backlog itself (use grooming)."
---

# Syncing

Stakeholders live in their tracker; the backlog lives in `backlog.json`. This skill moves the
backlog out and brings sign-off and feedback back, without losing anyone's edits. It needs the
`grooming` skill installed beside it, because `grooming/scripts/backlog.py` owns the contract.

```sh
S=<this skill>/scripts/sync.py
python3 $S github plan   backlog.json --repo acme/close [--project acme/7]   # read-only; prints a digest
python3 $S github apply  backlog.json --repo acme/close [--project acme/7] --expect <digest>
python3 $S github pull   backlog.json --repo acme/close [--since 2027-01-14]
python3 $S github report backlog.json --repo acme/close [--post] [--today 2027-04-21]
python3 $S excel backlog.json --out backlog.xlsx
python3 $S record-signoff backlog.json --item F-1 --by "Dana Whitfield (VP Product)" --source "email, 2027-01-20"
```

GitHub calls use the signed-in `gh` CLI; check with `gh auth status`. The token needs issues
write access on the repository and, for `--project`, Projects access. The script refuses a file
with validation errors, and refuses an initiative whose `prd` file is missing.

## Publish to GitHub

1. **Plan.** Run `plan` and show the user its output: labels and milestones to create, issues to
   create or update (with a diff), sub-issue links, conflicts, orphans, and the digest line.
2. **Get approval.** Writing to a tracker is an outside effect: apply only when the mission
   contract pre-authorizes that exact effect, or the owner approves the exact plan digest.
   Outside a contract mission, the owner approves the exact plan. This holds for every tracker.
3. **Apply exactly that plan.** `apply --expect <digest>` re-plans and refuses to write anything
   if the plan changed since the user saw it (someone edited GitHub or the file). It then
   records issue numbers, IDs, URLs, what it wrote, and `synced_at` in `backlog.json`. Commit
   `backlog.json` afterwards.
4. **Re-run plan.** It must print `nothing to do`; anything else is unfinished.

How the backlog appears in GitHub:

| Backlog | GitHub |
| --- | --- |
| Initiative, goal, feature, story, bug | One issue each, titled `[ID] title`, with labels `backlog`, `type:…`, and `work:`, `priority:`, `size:`, `urgency:`, `status:`, `domain:` as they apply |
| Issue body | Named sections from the type's template (below): for a story, User story, Acceptance criteria, Depends on, Owner, Sources, Notes |
| Parent and child | Sub-issues: goals under the initiative, features under goals, stories and bugs under features |
| Milestone | Repository milestone matched by title; stories and bugs inherit their feature's |
| PRD | Its "In short" section opens the initiative's PRD section, with the full PRD folded below it, so `/approve` there signs off the PRD and goals |
| Stories covered by sign-off | Listed in the feature issue body |
| Identity | A hidden `<!-- backlog:ID -->` marker in each body |
| GitHub Project | `--project OWNER/NUMBER` puts every issue on that Project as a card, with the fields and views below |

### Issue templates

Each issue body is filled from a Markdown template per type in [`templates/`](templates/):

| Type | Sections |
| --- | --- |
| Initiative | Problem, Outcome, Business drivers, Goals, Non-goals, Owner, PRD, How to sign off |
| Goal | Metric, Baseline and target, Serves business drivers |
| Feature | What we deliver, Why: benefit hypothesis, Done when, Stories your sign-off covers, Owner, How to sign off |
| Story | User story, Acceptance criteria (definition of done), Depends on, Owner |
| Bug | What happens, What should happen, Steps to reproduce, Environment, Acceptance criteria, Depends on, Owner |

Every type ends with Sources and Notes. A section is a `## ` heading followed by slots such as
`{acceptance}`; a section whose slots are all empty is left out, so issues show no empty
headings. To change the layout for one backlog, copy a template to `issue-templates/<type>.md`
beside `backlog.json` and rename, reorder, or drop sections, or add fixed text. A slot the
script does not know is an error that lists the slots it does know. The identity marker is
always added after the template.

A new layout changes every body, so the next plan shows an `update` for each issue. Content is
unchanged, so sign-offs stay current. If a template change alters what approvers agreed to
(for example, it drops acceptance criteria), ask them to approve again.

### GitHub Project: fields and roadmap

With `--project`, the plan also creates and fills these Project fields, matched by name:

| Field | Type | Value |
| --- | --- | --- |
| Item type | single select | initiative, goal, feature, story, bug |
| Priority, Size, Readiness | single select | the story's or bug's `priority`, `size`, and `status` |
| Urgency | single select | bugs only |
| Rank score | number | the feature's WSJF score: higher goes first |
| Schedule | iteration | the milestone of the feature, story, or bug; one slot per milestone with a `due` date |

It also creates two views: **Roadmap** (roadmap layout, features only, bars placed by
Schedule) and **Backlog by milestone** (table of stories and bugs, grouped by Schedule, sorted
by Priority). GitHub's own `Status` field is left to the delivery team.

Each Schedule slot runs from the milestone's `start`, or from the day after the previous
milestone's `due`. The first milestone therefore needs a `start`; the plan stops with an error
if it has none, or if a field with one of these names exists with another type.

- **Token:** a fine-grained token cannot create user-owned Projects (`createProjectV2` is
  refused). Use a classic token with the `project` scope, or an organisation Project the token
  has Projects permission on.
- **Once, after the first apply:** open the Roadmap view and check that its date field is
  Schedule (the API cannot set it; GitHub picks an iteration field when one exists).
- **Edits on cards are kept:** a Priority, Size, or Schedule changed on a card since the last
  sync, or set by hand on a card this file never wrote, is a `conflict`, like an edited issue.
  Moving a milestone's dates moves its slot and keeps the cards on it; slots someone added by
  hand stay.

Safety rules the script enforces:

- **No duplicates:** issues are matched by their marker, never by title or label. If a marker
  disappears from an issue the file links to, or appears on two issues, that item is a conflict.
- **No overwrites:** when GitHub holds anything this file did not write (a title, body, label,
  or milestone edited in GitHub, or an issue with this ID that the file has no record of, as with
  a second `backlog.json` for the same repository), the item is a `conflict` and nothing is done
  to it. Merge the edit into `backlog.json`, or pass `--overwrite S-2` once the user agrees the
  GitHub state can go.
- **No deletions:** issues with a marker that are no longer in the file are reported as
  `orphan`. The script never closes, reopens, or deletes issues.
- **Moved sub-issues are not moved back:** linking fails as a conflict instead.
- **Labels it does not own are left alone.**

One repository, one `backlog.json`: a second initiative for the same repository joins the
existing file with new IDs.

## Pull sign-off and feedback

`pull` reads comments on synced issues and each issue's open or closed state:

- A comment whose first line is `/approve`, on an initiative or feature, by a login listed in
  `approvers` (case-insensitive), is recorded in that item's `approvals`, including when it is
  your own login. `backlog.py status` decides whether it is current.
- Every other comment on a feature, story, or bug becomes `open` feedback on that feature, with
  the comment URL as `source`. That includes `/approve` from someone not listed. Your own other
  comments, bot comments, and the status comment are skipped.
- Comments on an initiative or goal are printed under `triage` for `grooming`. They are printed
  again on each pull until filed as feedback with their URL as `source`; use `--since` with the
  date of the last pull to see only new ones.
- Closed stories and bugs without a delivery record are listed under `closed_without_delivery`.

Pulling twice adds nothing new. Commit `backlog.json` after each pull and hand the report to
`grooming`. To have new comments wake the planning thread, subscribe it to each initiative and
feature issue (see `planning`, section 5).

## Record a sign-off given outside the tracker

When an approver signs by email, in a letter, or in meeting minutes instead of commenting
`/approve`, record it:

```sh
python3 $S record-signoff backlog.json --item F-1 --by "Dana Whitfield (VP Product)" --source "email from Dana, 2027-01-20"
```

- `--item` is an initiative or feature. `--by` is an approver's `name` from `approvers`, with or
  without the role in brackets, in any case. `--source` names the email or document; it is
  required. Anything else is refused with one error line, and the file is not changed.
- It appends `{ "tracker": "written", "by", "at", "source", "fingerprint" }` to the item's
  `approvals`. The fingerprint covers the item and its stories (or goals). The sign-off counts
  for every tracker in `backlog.py status`, also on a backlog never synced, until any of that
  content changes; then it is stale and needs a new sign-off. Recording the same one twice adds
  nothing.
- This writes a sign-off into the backlog, so run it only when the mission contract
  pre-authorizes that exact effect, or the owner approves the exact command (item, approver, and
  source). Outside a contract mission, the owner approves the exact command. Never record a
  sign-off without the email or document that shows it.

## Show stakeholders where things stand

`report` prints the status comment: five plain points for people who will not open the backlog.
They cover goals with their latest reading (one per line), the next milestone dates with delivery
counts, what is blocked (features with no named owner or an assumed one, drafts with the
research they wait on, and ready work behind a draft), who has not signed what yet, and open
feedback. A gate that is approved, by anyone, is left out of "Not yet signed by". A feature whose
notes say "Signs off: Elena Petrova" lists only her, and "Who signs" names her for it; other
gates show "any listed approver". The note changes only the comment: any listed approver still
passes the gate. A milestone whose date has passed shows how many items have a delivery record, not
"overdue": work can be live before its delivery is recorded. Won't-have items are left out of
every count and of GitHub milestones. The full chain from driver to delivery stays in `backlog.py trace` and the Excel export. With
`--post` (after the user approves the text) it creates the comment on each initiative issue, or
updates the one it posted before, so stakeholders see what was agreed, delivered, and achieved
without leaving GitHub.

## Export to Excel

`excel` writes an `.xlsx` with sheets for the backlog (one row per item, with statement,
priority, urgency, size, WSJF, milestone, drivers, traces, sign-off, delivery, and tracker link),
acceptance criteria (one row per criterion with its delivery result), feedback, milestones, and
traceability gaps. It is an export: edits in the workbook do not flow back. Use it for steering
committees, offline review, or importing into a tool without an adapter.

## Azure DevOps and Linear

Both adapters are **not tested live**: tests drive them through fake transports only. Before
the first real apply, run `plan` against a test project and read it.

```sh
python3 $S azure  plan backlog.json --org acme --project close [--process scrum|basic]  # token in AZURE_DEVOPS_EXT_PAT
python3 $S linear plan backlog.json --team FIN --project "Month-end close"              # key in LINEAR_API_KEY
```

`apply --expect <digest>`, `pull`, and `report [--post]` work as for GitHub, with the same steps,
approval rule, conflicts, orphans, sign-off, and feedback rules. Here the digest also binds the
target that `plan` prints (organisation, project, and process, or team and project), so a plan
approved for a test project does not apply to the real one. A missing token or key stops
with one error that names the variable; the value is never printed. Read sign-off with
`backlog.py status --tracker azure` (or `linear`). The mapping, in short (details in
[reference/trackers.md](reference/trackers.md)):

| Backlog | Azure DevOps (Agile process) | Linear |
| --- | --- | --- |
| Initiative, goal | Epic; a goal is also tagged `goal` | Issue labelled `type:initiative`, `type:goal` |
| Feature | Feature (Epic with `--process basic`) | Issue labelled `type:feature` |
| Story, bug | User Story, Bug; Product Backlog Item with `scrum`, Issue with `basic` | Issue labelled `type:story`, `type:bug` |
| Parent and child | Parent (hierarchy) link | Sub-issue |
| Milestone | Iteration matched by title | Project milestone matched by title |
| Identity | Tag `backlog:ID` | Last description line `Backlog ID: ID` |
| Approver handle | `approvers[].azure`: sign-in name (UPN) | `approvers[].linear`: display name or email |

## Adapt it

- **Your own labels or colours:** change `OWN_LABEL_PREFIXES` and `LABEL_COLORS` in `sync.py`
  and the tests together.
- **Issue layout:** copy a template to `issue-templates/<type>.md` beside `backlog.json` (see
  [Issue templates](#issue-templates)).
- **Organisation issue types:** labels are used because personal repositories lack issue types;
  an organisation can map to its types in `render`.
- **Very long PRDs:** GitHub bodies hold 65,536 characters; the script refuses longer ones.
  Split the PRD, or move appendices out of it.

## Example

```text
$ python3 sync.py github plan backlog.json --repo acme/close
create labels    backlog, domain:operations, priority:must, …
create milestone PI 27.1: pilot UK01
create           I-1
…
link             S-2 sub-issue of F-1
plan: 1 create labels, 2 create milestone, 14 create, 13 link
digest: 4f1c09a2b7de  (apply with --expect 4f1c09a2b7de once approved)
```

After `apply --expect 4f1c09a2b7de`, Priya comments `/approve` on the initiative; `pull` prints
`"approvals": ["I-1 by priya-r"]`, and `backlog.py status` shows
`PRD I-1 approved … [priya-r current, tokafor none]`.

## Check your work

- `plan` after `apply` prints `nothing to do`, and `backlog.json` is committed.
- Every conflict in the plan was resolved with the user, not overwritten by default.
- After `pull`, `backlog.py status` lists the approvals stakeholders posted, and every new
  feedback entry is on the feature the comment was about.
- Every `record-signoff` names its source, and the command was approved before it ran.
- For Excel, read the workbook back and check that the row counts match `backlog.py tree`.

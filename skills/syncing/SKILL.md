---
name: syncing
description: "Copies a backlog.json (contract backlog/v1) into the tracker stakeholders use and reads their sign-off and feedback back: GitHub issues with sub-issues, labels, milestones, and an optional GitHub Project, a status comment showing what was agreed, delivered, and achieved, or an Excel workbook. Shows a read-only plan before every write and applies only that exact plan, never duplicates or overwrites edits made in the tracker, records /approve sign-offs from listed approvers, and files comments as feedback on the right feature. Use when asked to sync, push, publish, or export a groomed backlog to GitHub or Excel, pull stakeholder comments or approvals, update stakeholders on progress, or check what a sync would change. Linear and Azure DevOps adapters are planned, not built. Not for editing the backlog itself (use grooming)."
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
python3 $S github report backlog.json --repo acme/close [--post]
python3 $S excel backlog.json --out backlog.xlsx
```

GitHub calls use the signed-in `gh` CLI; check with `gh auth status`. The token needs issues
write access on the repository and, for `--project`, Projects access. The script refuses a file
with validation errors, and refuses an initiative whose `prd` file is missing.

## Publish to GitHub

1. **Plan.** Run `plan` and show the user its output: labels and milestones to create, issues to
   create or update (with a diff), sub-issue links, conflicts, orphans, and the digest line.
2. **Get approval.** Writing issues in a shared repository changes external state: apply only
   after the user approves this plan.
3. **Apply exactly that plan.** `apply --expect <digest>` re-plans and refuses to write anything
   if the plan changed since the user saw it (someone edited GitHub or the file). It then
   records issue numbers, IDs, URLs, what it wrote, and `synced_at` in `backlog.json`. Commit
   `backlog.json` afterwards.
4. **Re-run plan.** It must print `nothing to do`; anything else is unfinished.

How the backlog appears in GitHub:

| Backlog | GitHub |
| --- | --- |
| Initiative, goal, feature, story, bug | One issue each, titled `[ID] title`, with labels `backlog`, `type:…`, and `work:`, `priority:`, `size:`, `urgency:`, `status:`, `domain:` as they apply |
| Parent and child | Sub-issues: goals under the initiative, features under goals, stories and bugs under features |
| Milestone | Repository milestone matched by title; stories and bugs inherit their feature's |
| PRD | Written in full into the initiative issue body, so `/approve` there signs off the PRD and goals |
| Stories covered by sign-off | Listed in the feature issue body |
| Identity | A hidden `<!-- backlog:ID -->` marker in each body |
| GitHub Project | `--project OWNER/NUMBER` adds every issue to that Project. Project fields (status, size, WSJF, dates) are not set yet; group or filter by the labels and milestone instead |

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

## Show stakeholders where things stand

`report` prints the status comment: drivers, goals with their latest measurements, features with
sign-off and delivery counts, stories and bugs, feedback with dispositions, and gaps. With
`--post` (after the user approves the text) it creates the comment on each initiative issue, or
updates the one it posted before, so stakeholders see what was agreed, delivered, and achieved
without leaving GitHub.

## Export to Excel

`excel` writes an `.xlsx` with sheets for the backlog (one row per item, with statement,
priority, urgency, size, WSJF, milestone, drivers, traces, sign-off, delivery, and tracker link),
acceptance criteria (one row per criterion with its delivery result), feedback, milestones, and
traceability gaps. It is an export: edits in the workbook do not flow back. Use it for steering
committees, offline review, or importing into a tool without an adapter.

## Linear and Azure DevOps

Not built yet. [reference/trackers.md](reference/trackers.md) records the intended mapping and
the guarantees each adapter must keep. Until then, sync to GitHub or export to Excel.

## Adapt it

- **Your own labels or colours:** change `OWN_LABEL_PREFIXES` and `LABEL_COLORS` in `sync.py`
  and the tests together.
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
- For Excel, read the workbook back and check that the row counts match `backlog.py tree`.

# Tracker mapping

What each adapter does with the contract. GitHub and Excel are built and tested against GitHub.
Azure DevOps and Linear are built but **not tested live**: their tests use fake transports only,
so the API details below are taken from the vendors' documentation, not from a real run.

## Guarantees every adapter keeps

1. **Plan before write:** a read-only plan the user approves before anything changes.
2. **Stable identity:** each tracker item carries the backlog ID in a place users cannot easily
   break (a hidden body marker, an external ID field, or a tag), and matching never uses titles.
3. **Conflict detection:** remember a hash of what was last written; skip and report items edited
   in the tracker since.
4. **Never delete:** orphans are reported, not removed.
5. **Sign-off by comment:** `/approve` as a comment's first line from a listed approver handle;
   everything else is feedback filed on the feature.
6. **Hashed content excludes delivery data** (measurements, delivery records, workflow state),
   so recording progress does not make sign-offs stale.

## GitHub (built)

Known limit: the GitHub plan digest covers the actions only, not `--repo` or `--project`. A
digest approved for one repository would also pass `--expect` against another that needs the
same actions, so check the repository named in the apply command. (Azure DevOps and Linear bind
their target; see below.)

See the table in `SKILL.md`. Hierarchy uses sub-issues; type, work, priority, size, urgency,
status, and domain use labels; milestones are repository milestones. With `--project`, the
same values also go into Project fields, milestones become slots of an iteration field named
Schedule, and a Roadmap view shows features on it.

## Excel (built, export only)

Sheets: Backlog, Acceptance criteria, Feedback, Milestones, Traceability gaps. Nested fields are
flattened: acceptance criteria get their own sheet; lists are joined with commas or line breaks.
No import: a spreadsheet has no comment identity or edit history to sign off with.

## Azure DevOps and Linear (built, not tested live)

`sync.py azure …` (in `azure.py`) and `sync.py linear …` (in `linear.py`) share one plan, apply,
and pull in `sync.py`, with the GitHub rules: the same plan digest and `--expect` binding, the
same conflict test (`edit_conflict`), and the same sign-off and feedback rules
(`file_comments`). An apply writes to a tracker, which is an outside effect: run it only when
the mission contract pre-authorizes that exact effect, or the owner approves the exact plan
digest.

- **The digest binds the target.** `plan` prints a `target:` line (tracker, organisation and
  project and process, or team and project), and the digest covers it. A plan approved for a test
  project does not pass `--expect` against the real one.
- **Labels and tags are compared without case** (Azure DevOps and Linear only; GitHub compares them exactly). A tracker that already has `Backlog` reuses it
  for `backlog`; that is not an edit.
- **Tokens.** One trailing newline, as a paste often adds, is removed and the token accepted; a
  token or key that still contains a control character, such as a line break, or any non-ASCII
  character is refused with one error that names the variable, never the value.
- **Parents.** Each item records the parent it was last linked under (`external.<tracker>.parent`).
  If `parent` changed in backlog.json, the plan links the item again (`link`, replacing the old
  parent). If the item was moved in the tracker, it is a conflict until `--overwrite <ID>`. In Azure DevOps
the re-link patch first tests the work item's revision (`test /rev`), so an edit made between the
read and the write refuses the patch and the item becomes a conflict.
- **Comments.** `pull` skips only this skill's own status comment (your comment that starts with
  "Status from the planning backlog"). A stakeholder comment that quotes it is filed like any
  comment. `--since` leaves out comments created before that date; a later pull without it files
  them.
- **Errors.** A timeout, a dropped connection, or a reply that is not JSON (Azure answers a
  refused token with a sign-in page) stops with one `error:` line.

Neither tracker stores Markdown exactly as sent. Each item therefore records two hashes in
`external.<tracker>`: `sent` (what this file rendered) and `hash` (title and body as the tracker
returned them). A changed `hash` means someone edited the item in the tracker: a conflict. A
changed `sent` means the file changed: an update. A lost sync record rebinds only when the
tracker's copy equals the rendered text; otherwise it is a conflict until `--overwrite`. In
Linear this includes a create whose reply was lost: Linear rewrites the Markdown, so the next
plan reports "this file has no record of syncing it". Check that the issue is the one just
created, then pass `--overwrite <ID>`; no duplicate is made. Azure DevOps keeps the Markdown
as sent, so the same case rebinds with `record`.

### Try it without a tracker

```sh
python3 tests/fixtures/syncing/fake_plan.py azure  [backlog.json]
python3 tests/fixtures/syncing/fake_plan.py linear [backlog.json]
```

This runs `plan` against an empty in-memory fake of each tracker (the fakes in
`tests/test_syncing.py`), with no network and no token. Read the actions, the `target:` line,
and the digest.

### Azure DevOps (Azure Boards)

| Backlog | Azure DevOps | Notes |
| --- | --- | --- |
| Initiative | Epic | |
| Goal | Epic tagged `goal`, child of its initiative | Same-level parent link |
| Feature | Feature | Basic process: Epic, because Basic has no Feature type |
| Story, bug | User Story, Bug (Agile, the default) | `--process scrum`: Product Backlog Item; `--process basic`: Issue |
| Body | Description in Markdown; a Bug uses Repro Steps | Set with `/multilineFieldsFormat/<field>` = Markdown |
| Labels | Tags `backlog`, `type:…`, `priority:…` and the rest, as on GitHub | Tags it does not own are left alone |
| Parent and child | `System.LinkTypes.Hierarchy-Reverse` link on the child | A work item with another parent is a conflict |
| Milestone | Iteration directly under the project root, matched by title without case | `\ / $ ? * : " & < > # % \| +` become ` - `, so `PI 27.1: pilot UK01` is `PI 27.1 - pilot UK01`; an existing iteration keeps its own casing; start and finish dates are set when known. Iterations nested deeper are not matched |
| Identity | Tag `backlog:<ID>` | Matched by tag (without case), never by title |
| Comments | Work item comments (API 7.1-preview.4); HTML is read as plain text | Status comment posted in Markdown |
| Approver handle | `approvers[].azure`: the sign-in name (UPN), case-insensitive | |
| Signed-in user | `https://dev.azure.com/{org}/_apis/connectionData?api-version=7.1-preview.1`, `authenticatedUser.properties.Account.$value` | Not in the published REST reference; not tested live. Microsoft's Python SDK uses it (`azure-devops-python-api`, `LocationClient.get_connection_data`). It answers an organisation-scoped token, which Profiles - Get refuses. Compared with comment authors' sign-in names to skip your own comments; `pull` and `report --post` stop with one error line if it gives no user |
| Closed | State Closed, Done, or Removed | |

Credentials: a personal access token with Work Items (read and write) scope in `AZURE_DEVOPS_EXT_PAT`
(the variable the Azure DevOps CLI reads). Store it as an Amp secret; the agent never asks for
it in chat. After the first apply, add the new iterations to the team's iterations if the team
plans by sprint; the adapter does not change team settings or process customisation.

### Linear

| Backlog | Linear | Notes |
| --- | --- | --- |
| Every item | One issue in one team (`--team KEY`) and project (`--project NAME`) | The project must include the team; the plan stops before any write if not. Linear initiatives and cycles are not used |
| Type and the rest | Labels `backlog`, `type:<type>`, `priority:…` and the rest, as on GitHub | Missing labels are created in the team |
| Parent and child | Sub-issues: initiative, goal, feature, then story or bug | An issue with another parent is a conflict |
| Milestone | Project milestone matched by title, target date from `due` | |
| Identity | Last description line `Backlog ID: <ID>` | Matched by that line, never by title |
| Comments | Issue comments; bot comments are skipped | |
| Approver handle | `approvers[].linear`: display name or email, case-insensitive | A handle with `@` matches only the commenter's email; any other handle only their display name. Anyone else is recorded as `display name <email>`. Prefer email handles: users can change their display name |
| Closed | Workflow state of type completed or canceled, or archived | Archived issues are listed (`includeArchived`), so Linear's auto-archive of closed issues is not a conflict |

Credentials: a personal API key in `LINEAR_API_KEY`, stored as an Amp secret.

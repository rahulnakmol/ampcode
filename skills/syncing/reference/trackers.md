# Tracker mapping

What each adapter does with the contract. GitHub and Excel are built; Linear and Azure DevOps
are plans, recorded so the adapters keep the same guarantees. Verify the tracker's current API
before building one; the notes below are design intent, not tested behaviour.

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

See the table in `SKILL.md`. Hierarchy uses sub-issues; type, work, priority, size, urgency,
status, and domain use labels; milestones are repository milestones.

## Excel (built, export only)

Sheets: Backlog, Acceptance criteria, Feedback, Milestones, Traceability gaps. Nested fields are
flattened: acceptance criteria get their own sheet; lists are joined with commas or line breaks.
No import: a spreadsheet has no comment identity or edit history to sign off with.

## Linear (planned)

| Backlog | Linear | Decision needed |
| --- | --- | --- |
| Initiative | Initiative | none |
| Goal | Project, with the goal's metric in its description | Linear has no goal type; alternative is a label on issues |
| Feature | Project milestone or parent issue | Choose per team; parent issue keeps comments and sign-off simple |
| Story, bug | Issue with label `type:story` / `type:bug`, parent set to the feature issue | none |
| Priority, urgency | Linear has one priority field: map urgency to it for bugs, priority to a label | Confirm with the team |
| Size | Estimate (t-shirt scale) | Team must use the t-shirt estimate scale |
| Milestone | Cycle or project milestone | Cycles have numbers, not titles: match by date range |
| Approver handle | `approvers[].linear` (Linear user name or email) | none |

Needs a Linear API key stored as an Amp secret; the agent never asks for it in chat.

## Azure DevOps (planned)

| Backlog | Azure DevOps | Decision needed |
| --- | --- | --- |
| Initiative | Epic work item (the name only; no epic layer is added) or a custom type | Choose per organisation process |
| Goal | Feature-level custom type, or Epic tag | Depends on the process template |
| Feature | Feature | none |
| Story, bug | User Story; Bug with "bugs are managed with requirements" | Team setting |
| Priority, urgency | Priority (1–4) and Severity for bugs | Fix a mapping table |
| Size | Effort as t-shirt via a custom picklist, or a numeric mapping XS=1, S=2, M=3, L=5 | Choose one |
| WSJF | Business Value, Time Criticality, custom Risk Reduction, Effort | Add the custom field |
| Milestone | Iteration path | Match by name |
| Approver handle | `approvers[].azure` (UPN) | none |

Needs organisation, project, and a personal access token stored as an Amp secret.

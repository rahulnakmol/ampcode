# The mission file

One Markdown file per mission holds the charter, the gate ledger, the decision trail and the
close-out. Copy the template, fill it, and run `scripts/ledger_check.py` after every change to the
ledger. The filled example below passes the checker; a test keeps it that way.

## Where it lives

Default: `missions/<slug>/mission.md` in the repository where the work lives, committed when the
repository allows it. Conductors keep it where they keep mission state:

| Conductor | Mission file |
| --- | --- |
| `planning` | `mission.md` in the mission folder; the README links it in its first line |
| `blueprinting` | A working note in the engagement repository, outside intake and record folders; its text is retained as a `mission` record each time a human gate passes |
| `delivering` | Its mission record, `.amp/in/missions/<id>/mission.md`. This is local: transfer it before moving to another host |

Keep briefs and review records as plain Markdown files beside it (for example `briefs/` and
`reviews/`). Paths in the ledger are relative to the mission file. Sections other than the four
below are allowed and ignored by the checker.

## Grammar

- **Charter:** under `## Charter`, one field per line, `- **Name:** value`. Names are exact and
  case-sensitive. A value continues on lines indented by two spaces. Extra fields are allowed.
  Required, each once: Outcome, Decision owner, Approvers, Success criteria, Definition of Done,
  Budget, Budget used, May do without asking, Always ask, Stop and ask when, Playbook, Host.
- **Placeholder:** an empty value, the upper-case words TBD, TODO or TBC, `?`, or `<text>` that
  is not an `https://` or `mailto:` autolink.
- **People:** Decision owner and Approvers are comma-separated names, each optionally followed by
  one `(handle)`; prose, roles and notes go elsewhere. `Elena Petrova (@elena-p)` gives two
  identities, the name and the handle. A Decider must equal one of them, ignoring case and a
  leading `@`. Approvers is `none` when the Decision owner is the only approver; the Decision
  owner is never `none`. Name client authorities and outside approvers as Approvers.
- **Gate ledger:** under `## Gate ledger`, a table with exactly these headers: Gate, Kind, State,
  Evidence, Review, Brief, Decider, Source, Date, then a `| --- |` separator line. Kind is `human`
  or `agent`; State is `open`, `pending`, `passed`, `failed` or `waived`, lower case. Empty cells
  hold `-`. The State column is the gate's decision.
- **Source:** `<kind>: <reference>`. Kinds: `dialog` (an Amp owner dialog such as mission-control;
  name Amp in the reference when the host is not Amp), `question` (the host's question tool),
  `tracker` (an approval in the tracker, such as GitHub `/approve`), `written` (a signed document,
  email or a client decision record). Only the Decision owner answers a `dialog` or `question`:
  the session belongs to them. Other approvers sign by `tracker` or `written`. Anything else, chat
  included, is not an approval.
- **Decision trail:** under `## Decision trail`, a table with headers Date, Decision, Why,
  Evidence, Decider. Add rows; never rewrite them (the checker cannot verify this). A conductor
  that already keeps decision provenance adds one row that links it.

## Rules the checker applies

| Rule | What passes |
| --- | --- |
| R1 | Every required charter field appears once and is not a placeholder; Decision owner and Approvers follow People |
| R2 | Host is Amp, Claude Code, Copilot in VS Code or Copilot app; Playbook is a playbook name or `none: <reason>` |
| R3 | Budget names a limit with a number and does not say "unlimited", or says `no limit on <what>, decided by <name>` |
| R4 | The gate ledger table has the nine headers in order, the separator line, nine cells per row and at least one row |
| R5 | Kind and State take the values above |
| R6 | A passed human gate, and any waived gate, has a Decider who is the Decision owner or an Approver, and a Source with a reference; a `dialog` or `question` Decider is the Decision owner |
| R7 | The Source kind is `dialog`, `question`, `tracker` or `written`, and the reference cites neither chat, a conversation, Slack or a DM nor an acknowledgement such as "looks good" or "LGTM" (a fixed word list, "Copilot Chat" excepted): approval is never inferred from chat |
| R8 | A passed human gate's Brief is a local `.md` file, relative to the mission file, that passes `briefing-decisions`' `brief_check.py`; a published URL may follow in parentheses |
| R9 | A passed gate's Review is an existing file or an `https` URL (the first path in the cell is the review record, and it is not the brief); an agent gate may say `none needed: <reason>` |
| R10 | A passed agent gate has Evidence that is not a placeholder |
| R11 | A waived gate gives its reason in Evidence, not a placeholder; it is never reported as passed |
| R12 | The decision trail table has its five headers, and every row names a Decider |

## Template

````markdown
# Mission: <outcome in a few words>

## Charter

- **Outcome:** <what changes, for whom>
- **Decision owner:** <name>
- **Approvers:** <names, with handles in parentheses>
- **Success criteria:** <measurable results, written before the work>
- **Definition of Done:** <what must be true to close>
- **Budget:** <limits: tokens, time, money, attempts, review rounds>
- **Budget used:** <measured, estimated or unknown, with delegated work>
- **May do without asking:** <actions>
- **Always ask:** <actions>
- **Stop and ask when:** <conditions>
- **Playbook:** <playbook name>
- **Host:** <Amp | Claude Code | Copilot in VS Code | Copilot app>

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Charter and criteria | human | open | - | - | - | - | - | - |

## Decision trail

| Date | Decision | Why | Evidence | Decider |
| --- | --- | --- | --- | --- |

## Close-out

- Trail audit: <each passed gate checked against its evidence>
- Needs your attention: <waived gates, accepted risks, open items with owner and date>
- Proposed skill edits: <lesson, file, change; waiting for approval>
````

## Filled example (synthetic)

````markdown
# Mission: choose an expense tool for finance

## Charter

- **Outcome:** The finance team gets a recommended expense-management product,
  with conditions, before the April budget review.
- **Decision owner:** Elena Petrova (@elena-p)
- **Approvers:** Tom Okafor (@tokafor)
- **Success criteria:** Three products scored against weights agreed before scoring.
- **Definition of Done:** Every score cites evidence; unverified claims are labelled.
- **Budget:** 5 working days; 3 review rounds per gate; no spend on paid trials.
- **Budget used:** estimated 1 day; tokens unknown: no usage telemetry on this host.
- **May do without asking:** read public vendor documents, draft the criteria and scores.
- **Always ask:** contacting vendors; sharing the report outside finance.
- **Stop and ask when:** a requirement is unclear, or a vendor claim cannot be checked.
- **Playbook:** product-assessment
- **Host:** Copilot app

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Charter | human | passed | charter above | reviews/charter-novice.md | briefs/charter.md | Elena Petrova | question: ask_user answer "Approve the charter" | 2026-02-27 |
| Requirements and weights | human | passed | criteria.md | reviews/weights-novice.md | briefs/weights.md | Elena Petrova | question: ask_user answer "Approve the weights" | 2026-03-02 |
| Evidence pack | agent | passed | scores.md, 3 products | none needed: checked at the shortlist gate | - | - | - | 2026-03-04 |
| Shortlist | human | pending | scores.md | reviews/shortlist-novice.md | briefs/shortlist.md | - | - | - |
| Recommendation | human | open | - | - | - | - | - | - |

## Decision trail

| Date | Decision | Why | Evidence | Decider |
| --- | --- | --- | --- | --- |
| 2026-03-02 | Weight security at 30 percent | Card data is in scope | criteria.md | Elena Petrova |
| 2026-03-03 | Label vendor uptime figures as claimed | No status page history | scores.md | Elena Petrova |

## Close-out

- Trail audit: not yet run.
- Needs your attention: none yet.
- Proposed skill edits: none yet.
````

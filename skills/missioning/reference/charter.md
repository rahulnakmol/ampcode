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
  case-sensitive. A value continues on lines indented by two spaces. Extra fields are allowed, so
  an old charter's budget lines still pass. Required, each once: Outcome, Decision owner,
  Approvers, Success criteria, Definition of Done, Open questions, Pre-authorized effects, May do
  without asking, Always ask, Stop and ask when, Playbook, Host.
- **Contract fields:** Open questions lists each question with the default the agent takes unless
  the owner changes it at kickoff (`Q1 <question> Default: <answer>`), or `none`. Pre-authorized
  effects lists each outside effect the owner approves at kickoff, each starting with its ID
  (`E1 <effect>`), or `none` with an optional reason. Always ask names outside effects that are
  not pre-authorized. Stop and ask when refers to the five stop reasons below, and adds nothing.
- **Placeholder:** an empty value, the upper-case words TBD, TODO or TBC anywhere, a whole value
  of tbd, todo or tbc in any case, `?`, or `<text>` that is not an `https://` or `mailto:` autolink.
- **People:** Decision owner is one name and Approvers are comma-separated names, each optionally
  followed by one `(handle)`; prose, roles and notes go elsewhere. `Elena Petrova (@elena-p)` gives two
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

## The five stop reasons

After kickoff, the agent asks the owner only when one of these holds. Anything else becomes a
recorded assumption, taken from the open question's default or a safe, reversible choice.

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

## Rules the checker applies

| Rule | What passes |
| --- | --- |
| R1 | One Charter section; every required field appears once and is not a placeholder; Decision owner (one person) and Approvers follow People |
| R2 | Host is Amp, Claude Code, Copilot in VS Code or Copilot app; Playbook is a playbook name or `none: <reason>` |
| R3 | Retired: missions have no budget. An old budget line is an extra field and passes |
| R4 | One `## Gate ledger` section and one ledger table in the file; the table (every line up to a blank one, with no table row after it) has the nine headers in order, the separator line with one cell per header, nine cells per row and at least one row |
| R5 | Kind and State take the values above; a gate named Charter or Kickoff is `human` |
| R6 | A passed human gate, and any waived gate, has a Decider who is the Decision owner or an Approver, and a Source with a reference; a `dialog` or `question` Decider is the Decision owner |
| R7 | The Source kind is `dialog`, `question`, `tracker` or `written`, and the reference cites neither chat, a conversation, Slack or a DM nor an acknowledgement such as "looks good" or "LGTM" (a fixed word list; "ask_user in Copilot Chat" names the question tool and is excepted): approval is never inferred from chat |
| R8 | A passed human gate's Brief is a local `.md` file, relative to the mission file, that passes `briefing-decisions`' `brief_check.py`; a published URL may follow in parentheses |
| R9 | A passed gate's Review is an existing file or an `https` URL (the first path in the cell is the review record, and it is not the brief); an agent gate may say `none needed: <reason>` |
| R10 | A passed agent gate has Evidence that is not a placeholder |
| R11 | A waived gate gives its reason in Evidence, not a placeholder; it is never reported as passed |
| R12 | The decision trail table has its five headers, and every row names a Decider |
| R13 | Pre-authorized effects is `none` or a list of `E<n> <effect>` entries. An `agent` row whose Evidence starts with "pre-authorized", whose Gate names `(E<n>)`, or whose Evidence speaks of pre-authorization and names an `E<n>` (upper case) has Evidence `pre-authorized: <source>`, and names only `E<n>` IDs the charter lists, at least one. A human row's Evidence never starts with "pre-authorized", and its Gate never names a listed `(E<n>)`. Other codes such as `E501` are plain evidence |

## Template

````markdown
# Mission: <outcome in a few words>

## Charter

- **Outcome:** <what changes, for whom>
- **Decision owner:** <name>
- **Approvers:** <names, with handles in parentheses>
- **Success criteria:** <measurable results, written before the work>
- **Definition of Done:** <what must be true to close>
- **Open questions:** <Q1 question. Default: answer; or none>
- **Pre-authorized effects:** <E1 effect, with its source; or none>
- **May do without asking:** <actions>
- **Always ask:** <outside effects that are not pre-authorized>
- **Stop and ask when:** one of the five stop reasons in missioning; nothing else.
- **Playbook:** <playbook name>
- **Host:** <Amp | Claude Code | Copilot in VS Code | Copilot app>

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kickoff | human | open | - | - | - | - | - | - |

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
- **Approvers:** none
- **Success criteria:** Three products scored against weights agreed before scoring.
- **Definition of Done:** Every score cites evidence; unverified claims are labelled.
- **Open questions:** Q1 How many products to shortlist? Default: the top three by score.
  Q2 Use paid trials? Default: no; vendor documents and free sandboxes only.
- **Pre-authorized effects:** E1 share the report with the finance team, approved at kickoff.
- **May do without asking:** read public vendor documents, draft the criteria and scores.
- **Always ask:** contacting vendors; sharing the report outside finance; any spending.
- **Stop and ask when:** one of the five stop reasons in missioning; nothing else.
- **Playbook:** product-assessment
- **Host:** Copilot app

## Gate ledger

| Gate | Kind | State | Evidence | Review | Brief | Decider | Source | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kickoff | human | passed | charter above, criteria.md | reviews/kickoff-novice.md | briefs/kickoff.md | Elena Petrova | question: ask_user answer "Approve the kickoff" | 2026-03-02 |
| Evidence pack | agent | passed | scores.md, 3 products | none needed: scored by script from the frozen weights | - | - | - | 2026-03-04 |
| Share the report with finance (E1) | agent | open | pre-authorized: charter E1, kickoff 2026-03-02 | - | - | - | - | - |

## Decision trail

| Date | Decision | Why | Evidence | Decider |
| --- | --- | --- | --- | --- |
| 2026-03-02 | Weight security at 30 percent | Card data is in scope | criteria.md | Elena Petrova |
| 2026-03-03 | Label vendor uptime figures as claimed | No status page history | scores.md | Elena Petrova |
| 2026-03-04 | Shortlist the top three by score | Default of Q1, taken as an assumption | scores.md | Agent (default Q1) |

## Close-out

- Trail audit: not yet run.
- Needs your attention: none yet.
- Proposed skill edits: none yet.
````

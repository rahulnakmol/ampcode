# Backlog contract `backlog/v1`

`backlog.json` is the source of truth for everything planned into one tracker project, such as
one GitHub repository: usually one initiative, sometimes several. Trackers (GitHub now; Linear
and Azure DevOps later) are copies that `syncing` writes and reads back; Excel is an export.
Planners change the file through an agent in an Amp thread; stakeholders comment and sign off in
the tracker. Keep exactly one file per tracker project, because trackers key on item IDs: a
second initiative for the same repository joins the existing `backlog.json` with new IDs.

Rules marked **checked** are enforced by `scripts/backlog.py validate`; when this page and the
script disagree about one, the script is wrong: fix it and add a test. Rules marked **review**
need judgment, and the fresh-context review in `grooming` checks them.

## Shape

```json
{
  "contract": "backlog/v1",
  "title": "Month-end close in three days",
  "approvers": [{ "name": "Priya Raman (Finance Ops lead)", "github": "priya-r" }],
  "milestones": [{ "id": "M1", "title": "PI 27.1: pilot UK01", "due": "2027-02-26" }],
  "items": [{ "id": "I-1", "type": "initiative" }, { "id": "G-1", "type": "goal", "parent": "I-1" }],
  "feedback": [{ "id": "FB-1", "feature": "F-1", "from": "priya-r", "summary": "…", "disposition": "open" }]
}
```

`contract`, `title`, and a non-empty `items` list are required; `approvers`, `milestones`, and
`feedback` are optional lists. Without at least one approver no sign-off gate can pass, so
`validate` warns. Each item names its one `parent`, so the items form a tree. Read the
cardinalities parent to child:

```text
initiative (I-n)                     why: problem, business drivers (D-n), outcome, PRD
└── 1:n goal (G-n)                   a measured outcome: metric, baseline, target, date; serves drivers
    └── 1:n feature (F-n)            benefit hypothesis, WSJF rank; a capability, process change, or campaign component
        ├── 1:n story (S-n)          one executable unit of work with measurable acceptance criteria
        ├── 0:n bug (B-n)            a defect against agreed behavior; a sibling of stories, with urgency
        └── 0:n feedback (FB-n)      what stakeholders and users said (kept in the separate `feedback` list)
```

While drafting, a parent may have no children yet; `validate` warns. At the final gate
(`--require-ready`) every initiative needs a goal, every goal a feature, and every feature a
story (a feature with only bugs fails). **Checked.**

## Traceability: described, agreed, delivered, achieved

The contract exists to keep one unbroken chain from what people first said to whether the
business got what it needed. `backlog.py trace` prints the chain and every gap in it.

| Stage | Recorded as | Gap reported when |
| --- | --- | --- |
| **Described** | Evidence IDs (`E7`) from `synthesizing`; requirement and criterion IDs (`R-3`, `AC-2`) from the PRD | A PRD requirement or criterion is traced by no item |
| **Agreed** | `/approve` sign-offs on initiatives (PRD and goals) and features (scope), recorded by `syncing` | A sign-off is missing or stale |
| **Delivered** | `delivery` on each story and bug: when, the evidence, and each acceptance criterion met or not | A tracker item is closed with no delivery record; a delivered item has an unmet criterion |
| **Achieved** | `measurements` on each goal, compared with its baseline and target | A goal is past its `by` date and not at target |
| **Drivers satisfied** | Each initiative's `drivers`, served by its goals | A driver is served by no goal; a driver's goals are not all achieved |

### Inspired by SAFe, not bound to it

| SAFe | Here | Why |
| --- | --- | --- |
| Strategic theme, epic, lean business case | Initiative, its drivers, and its PRD | One problem, one outcome, one signed-off PRD; an epic layer adds a level to groom and sync without adding a decision |
| PI objectives, OKRs | Goals | Measurable outcomes the features must move, each tied to a driver |
| Capability | none | Use a goal, or split the initiative |
| Feature (benefit hypothesis, acceptance criteria, WSJF) | Feature | Same; feature-level `acceptance` is optional because its stories carry the measurable criteria |
| User story, enabler story | Story with `work` | Enablers are `research` (exploration) or the kind of work they need. Sized XS–L, never in points, so every team sizes the same way |
| Defect | Bug | Sibling of stories, with urgency on top of priority |
| PI, release | Milestone | Features, stories, and bugs are planned into them |
| Delivery and outcome tracking | `delivery`, `measurements`, `trace` | Our own addition: proof of what was delivered against what was agreed, and of the goals and drivers it satisfied |

## Schema rules (checked, always errors)

Whatever the status, these are errors:

- an unknown field anywhere (top level, items, drivers, milestones, approvers, acceptance
  criteria, `wsjf`, `delivery`, measurements, feedback), so a typo such as `acceptence` cannot
  silently drop content;
- a wrong ID format, a duplicate ID, a `parent` that does not exist or has the wrong type, or a
  `milestone` that is not defined;
- a value outside its enumeration, or of the wrong type;
- a missing required field on an initiative, goal, or feature.

Stories and bugs are the exception: a draft can be partial, so a missing or empty required field
on a story or bug is a Definition of Ready finding (below). `status` itself is always required.

## Common fields

| Field | Required | Rule |
| --- | --- | --- |
| `id` | yes | Checked: unique; prefix by type `I-`, `G-`, `F-`, `S-`, `B-`, then digits. Review: never reuse or renumber an ID after the first sync |
| `type` | yes | `initiative`, `goal`, `feature`, `story`, or `bug` |
| `parent` | all but initiatives | An initiative for a goal, a goal for a feature, a feature for a story or bug |
| `title` | yes | Checked: at most 120 characters. Review: names the result, not the activity ("Bank lines reconcile nightly", not "Work on bank feeds") |
| `trace` | see each type | A list of strings: evidence IDs from `synthesizing` (`E7`) or PRD IDs from `specifying` (`R-3`, `AC-2`). When `evidence.md` or the PRD sits beside the file, `validate` warns about IDs missing from them. A PRD defines an ID by writing it in bold (`**R-3 …**`, `**AC-2**`); plain mentions, such as in a change log, are references |
| `notes` | no | Free text copied to the tracker |
| `external`, `approvals` | written by `syncing` only | See [Sync fields](#sync-fields) |

## Initiative

| Field | Required | Rule |
| --- | --- | --- |
| `domain` | yes | `product` (new or changed software), `operations` (an operational challenge or new way of working, including automation and reporting), or `marketing` (a campaign or launch) |
| `problem` | yes | Who is hurt, how, and the evidence |
| `drivers` | yes | At least one `{ "id": "D-1", "statement": "…" }`, IDs unique within the initiative. A driver is why the business cares (cost, revenue, risk, compliance, customer, strategy), stated so someone can tell later whether it was met |
| `outcome` | yes | What is true when the initiative succeeds |
| `owner` | yes | Accountable person or role |
| `prd` | no | PRD path relative to `backlog.json`. Syncing writes the PRD's content into the initiative's tracker item, so an edited PRD makes its sign-off stale |
| `non_goals` | no | List of strings |
| `trace` | no | Evidence IDs |

## Goal

An outcome, not a task, with a number someone can check.

| Field | Required | Rule |
| --- | --- | --- |
| `metric` | yes | What is measured and where it is read |
| `baseline` | yes | Today's value, string or number. Review: `unknown` only when a story measures it |
| `target` | yes | The value that counts as success, string or number |
| `by` | yes | `YYYY-MM-DD` |
| `drivers` | yes | IDs of the parent initiative's drivers this goal serves, at least one |
| `measurements` | no | `[{ "at": "YYYY-MM-DD", "value": "4", "source": "…" }]`, oldest first. The latest decides: when baseline, target, and value all start with a number, the goal is achieved at or past the target (inclusive) in the direction from baseline to target; otherwise only when `value` equals `target`, ignoring case. For a limit, write the target as `at most 80` or `at least 85%`: the latest value is compared with that number whatever the baseline, so guardrails ("must not rise above 7.1") and goals with no baseline yet work too |
| `trace` | yes | At least one entry |

## Feature

| Field | Required | Rule |
| --- | --- | --- |
| `description` | yes | What is delivered and for whom |
| `benefit_hypothesis` | yes | Review: "We believe *this* will result in *that*; we will know when *the parent goal's metric moves*" |
| `wsjf` | yes | Checked: exactly `business_value`, `time_criticality`, `risk_reduction`, `job_size`, each 1, 2, 3, 5, 8, 13, or 20. Review: scored relative to the other features. Score = (value + time criticality + risk reduction) ÷ job size; `backlog.py tree` ranks by it |
| `acceptance` | no | List of plain-language conditions for the whole feature |
| `milestone` | no | A milestone `id`; stories and bugs inherit it unless they set their own |
| `owner` | for ready | The one named person accountable for the feature. Checked: `--require-ready` fails without one, or on a placeholder such as "to be named", "name to confirm", or "TBD" (a warning before). Review: a person, not a team or role. When nobody in the role is named, the mission owner may stand in, even as an approver, to find the person: the `notes` say "Owner assumed: …, standing in for <role> until <who> names one by <date>", and gate 6 stays open. An owner the planner chose for the user is written as an assumption in the feature's `notes` |
| `trace` | yes | At least one entry |

## Story: the executable unit

A story is **executable** when a person or agent who has read only the story, its parents, and
the outputs of the items it depends on can do the work and prove it is done without asking
anyone a question. The checked part of that is the Definition of Ready below; the rest is review.

| Field | Required | Rule |
| --- | --- | --- |
| `as_a` | yes | A specific actor ("accounts payable clerk", "the nightly reconciliation job"), not "user" |
| `i_want` | yes | The capability or change |
| `so_that` | yes | The value, ideally tied to the goal's metric |
| `work` | yes | `build` (software), `automate` (workflow or job automation), `report` (dashboard, report, metric), `process` (procedure, policy, role, or way-of-working change), `enable` (training, communication, change management), `content` (copy, creative, asset), `launch` (campaign setup and channel execution), or `research` (a time-boxed exploration that ends in a decision) |
| `acceptance` | yes | One or more `{ "id", "given", "when", "then" }`; IDs are the story ID plus `.n`, such as `S-4.1`. These are the story's definition of done |
| `priority` | yes | `must`, `should`, `could`, or `wont`, within the feature. A `wont` item records a decision not to do the work: it takes no `milestone`, gets none from its feature, and the ready gate skips it |
| `size` | yes | `XS` (up to half a day), `S` (up to 2 days), `M` (up to 5 days), or `L` (up to 10 days, one iteration); never points. `XL` is only a draft flag meaning "too big, split me": an item cannot be ready at XL |
| `status` | yes | `draft` or `ready`. Tracker workflow states (in progress, done) belong to the tracker |
| `depends_on` | no | Story or bug IDs that must finish first |
| `milestone` | no | Overrides the feature's milestone |
| `owner` | for ready | Person, team with its contact ("Claims data team (lead: Ana Silva)"), or `agent`. With no contact named yet, the mission owner stands in: "Team Atlas (contact: Dana Whitfield until she names the lead by 27 April)". `--require-ready` fails on a `ready` story with none. A placeholder such as "lead (to be named)" fails `--require-ready` (a warning before) |
| `delivery` | no | Added when the work is done; see [Delivery](#delivery) |
| `trace` | yes | At least one entry, normally a PRD acceptance criterion |

## Bug: a sibling of stories

A bug says agreed behavior is broken. It hangs under the feature whose behavior it breaks and is
executable on the same terms: someone who reads only the bug can reproduce it, fix it, and prove
the fix. Priority says how much the fix matters; urgency says how soon it must land.

| Field | Required | Rule |
| --- | --- | --- |
| `observed` | yes | What happens, with the evidence: error text, wrong number, link |
| `expected` | yes | What should happen, citing the criterion it breaks when there is one |
| `steps` | yes | A non-empty list of reproduction steps |
| `environment` | no | System, entity, browser, channel, or date range |
| `work`, `priority`, `size`, `status`, `depends_on`, `milestone`, `owner`, `delivery` | as for stories | |
| `acceptance` | yes | Given/When/Then checks that prove the fix, IDs `B-n.m`. Review: one reproduces the original failure |
| `urgency` | yes | `critical` (interrupts planned work now), `high` (before the bug's milestone, or its feature's, is due), `medium` (plan into a milestone), or `low` (when convenient) |
| `trace` | no | May be empty for a bug found in production |

## Definition of Ready (checked)

`validate` reports these as **errors** for `ready` stories and bugs and as **warnings** for
`draft` ones. Words match case-insensitively as whole words.

1. Every required field is present and non-empty, including each `given`, `when`, and `then`,
   and a bug's `steps`.
2. A story's `as_a`, without a leading "a", "an", or "the", is not "user", "users", "customer",
   "customers", "stakeholder", "stakeholders", or "team".
3. The acceptance criteria are measurable:
   - every `then` states a quantity: a digit, or one of every, each, all, none, no, exactly,
     at least, at most, within, zero, one, two, three, four, five, six, seven, eight, nine, ten,
     eleven, twelve;
   - at least one `then` per item contains a digit that is not part of an ID (`S-2.1`, `AC-3`,
     `E7`), so each item has a real number, date, time, or amount;
   - no `then` uses one of these vague words: fast, quick, quickly, easy, easily, simple,
     intuitive, user-friendly, seamless, seamlessly, robust, scalable, efficient, efficiently,
     appropriate, appropriately, as needed, properly, optimized, optimised, improved, better,
     etc. Write the number or the observable result instead.
4. `size` is not `XL`.
5. A `research` story's `i_want` or a `then` states a time box (a number followed by hour, day,
   week, sprint, or iteration) and a decision (decide, decision, recommend, choose, or select).
   Its `size` is the smallest size that holds the time box (a 3-day spike is `M`); a mismatch
   is a warning, except on a `wont` item. `tree`, the tracker, and Excel show the time box
   ("3-day time box") instead of the size.
6. Every `depends_on` ID is a story or bug in the file, is not the item itself, and forms no cycle.
   A `ready` item that depends on a `draft` one gets a warning: it cannot start before it.

`validate --require-ready` is the final grooming gate. Every warning about a story or bug becomes
an error, and it also fails on any `draft` story or bug (except one whose `depends_on` chain
reaches a `research` story not yet delivered: that is held, with a warning; and a `wont` item,
which is skipped), any parent without the children listed above, any feature without a named
`owner`, any `ready` story or bug with no `owner` or one that is a placeholder, a `wont` item with a milestone, any
driver no goal serves, and any `open` feedback. It
does not look at sign-offs;
`backlog.py status` does.

### What "executable" looks like in each domain

| Domain | Weak story | Executable story |
| --- | --- | --- |
| product | "As a user I want faster onboarding" | As a **new workspace admin** I want to **import up to 500 users from a CSV** so that **the team is active on day 1**. *Given* a CSV with 500 valid rows *when* the admin uploads it *then* 500 accounts exist within 60 seconds and a summary lists 0 failures |
| operations | "Automate reconciliation" | As an **AP clerk** I want **bank lines matched to open invoices nightly** so that **I review only exceptions**. *Given* yesterday's bank file *when* the 02:00 job runs *then* every matched line is posted and every unmatched line is in the exception report by 07:00 |
| marketing | "Do social posts for launch" | As the **campaign manager** I want **6 LinkedIn posts scheduled for launch week** so that **we reach 40k impressions**. *Given* the approved copy deck *when* the posts are scheduled *then* all 6 carry `utm_campaign=q1-launch` and are in the scheduler for 3–7 March |

## Delivery (checked)

When a story or bug is done, the person or agent who verified it records what was delivered:

```json
"delivery": { "at": "2027-02-20", "evidence": ["https://github.com/acme/close/pull/88", "Run log 2027-02-19"],
              "criteria": { "S-2.1": "met", "S-2.2": "met", "S-2.3": "not met" } }
```

`at` is `YYYY-MM-DD`; `evidence` has at least one entry; `criteria` lists exactly the item's
acceptance criterion IDs, each `met` or `not met`, so a partial delivery stays visible instead of
being rounded up. Only a `ready` item can have a delivery. A closed tracker item is not evidence
on its own: `syncing pull` records the tracker state in `external`, and `trace` flags closed
items with no delivery record.

## Feedback (checked)

Feedback from stakeholders and users belongs to exactly one feature, so every comment ends up
attached to the capability it is about. A feature can collect many entries.

| Field | Required | Rule |
| --- | --- | --- |
| `id` | yes | `FB-` plus digits, unique |
| `feature` | yes | A feature `id` in the file |
| `from` | yes | Tracker handle, name, or role |
| `summary` | yes | The point in one or two sentences, in the giver's terms |
| `source` | no | Comment URL, evidence ID, survey, or support ticket |
| `at` | no | ISO date or timestamp |
| `disposition` | yes | `open`, `accepted` (the backlog changed), `declined`, or `duplicate` |
| `resolution` | all but `open` | A string. For `accepted` it names at least one existing item ID that changed; for `declined` it gives the reason; for `duplicate` it names another existing `FB-` ID |

`syncing pull` adds each comment on a feature, story, or bug as `open` feedback on that feature
(for a story or bug, its parent feature). It prints comments on an initiative or goal for triage
instead: the groomer files them under a feature, creating one if needed, or, when they are about
the PRD, changes the PRD.

## Milestones (checked)

`{ "id": "M1", "title": "PI 27.1: pilot UK01", "start": "2027-01-11", "due": "2027-02-26" }`. IDs
and titles are unique, because trackers match milestones on titles. `start` and `due` are
optional `YYYY-MM-DD` dates; `start` needs `due` and is not after it. Milestones are the roadmap:
PIs or releases that features, stories, and bugs are planned into. On a GitHub Project roadmap,
a milestone with a `due` date runs from its `start`, or else from the day after the previous
milestone's `due`; the first milestone needs a `start`.

## Approvers and sign-off

`approvers` lists who may sign off: `{ "name", "github"?, "linear"?, "azure"? }`, one handle per
tracker. A stakeholder signs off by posting a comment whose first line is `/approve` on an
initiative or feature. Comments by handles not in `approvers` never count as sign-off.
`/approve` anywhere else is ordinary feedback.

- **PRD gate:** one current approval on each initiative. It covers the PRD, the initiative, and
  its goals.
- **Backlog gate:** one current approval on each feature. It covers the feature and its stories;
  the feature's tracker item lists its stories, so adding or removing one also changes the
  feature. Bugs need no sign-off and do not make it stale: they restore behavior already agreed.

One current approval from a listed approver passes a gate. When every approver must sign, run
`status --all-approvers`; `status` always lists each approver as `current`, `stale`, or `none`.
Handles match case-insensitively.

An approval is **current** when its comment was created at or after the last content change
synced to every item it covers (`synced_at`, GitHub's own timestamp). A gate reads:

- `unsynced changes` when a covered item (or the PRD) was edited locally after the last sync:
  sync first, because approvers have not seen the edit;
- `stale` when the change was synced after the approval: ask for `/approve` again;
- `missing`, `approved`, `partly approved` (with `--all-approvers`), or `not synced`.

## Sync fields

`syncing` writes these; grooming leaves them alone:

```json
"external": { "github": { "number": 41, "id": 2938475610, "url": "https://github.com/acme/close/issues/41",
                          "hash": "sha256:…", "fingerprint": "sha256:…", "labels": ["backlog", "type:feature"],
                          "milestone": "PI 27.1: pilot UK01", "synced_at": "2027-01-12T09:30:00Z", "state": "open" } },
"approvals": [{ "tracker": "github", "by": "priya-r", "at": "2027-01-13T05:02:11Z",
                "url": "https://github.com/acme/close/issues/41#issuecomment-1" }]
```

`hash`, `labels`, and `milestone` are what syncing last wrote, so it notices edits made in the
tracker and reports them as conflicts instead of overwriting them. `fingerprint` is
`backlog.py`'s hash of the item (and, for an initiative, its PRD) at that sync, so `status` notices
local edits not yet synced. Delivery records and measurements are left out of it: recording
progress never reopens a sign-off. `synced_at` is when content last changed in the tracker;
`state` is its open or closed state at the last pull.

## Versioning

A change that makes a valid file invalid needs `backlog/v2` and a migration note here. Adding an
optional field does not.

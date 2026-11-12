# Mission-driven planning

For the strategist who is also the delivery lead: you run the workshops, own the PRD and the
backlog, and answer for whether the work moved the business. A planning mission takes one
initiative (a product, an operations change or new way of working, or a marketing campaign)
from raw notes to an agreed backlog of executable stories in the tracker your stakeholders use,
and then keeps score until the goals are met.

**Start here for a PRD and tracker-ready backlog.** For enterprise client workshops,
functional specifications, operating models and pre-sales/RFP work, use
[Blueprinting](blueprinting.md). Its client-authority and evidence rules are separate
from tracker sign-offs; a handoff does not transfer approval automatically. To build software from the result, see
[mission-driven development](mission-driven-development.md). For individual skills, see
[Using the skills](using-skills.md).

## Start with one message

Open your planning repository in Amp and fill in the brackets:

```text
Use planning to run a mission for [initiative] ([product | operations | marketing]).
Inputs are in [planning/<slug>/inputs/ or pasted below]. Approvers are [names and GitHub
logins]. Sync to [owner/repo] and Project [owner/number, optional]. Success means
[signed-off PRD and a ready backlog by <date> | your own criteria].
```

Amp drafts a short charter (initiative, entry point, approvers, tracker, success criteria,
folder) and asks you to confirm it before any stage starts.

## What happens, stage by stage

| Gate | You give | Amp does | You get |
| --- | --- | --- | --- |
| **G1 Evidence and intent** | Notes, transcripts, minutes, drafts; answers to a few questions | `synthesizing`: numbers every source and claim, with who said it and where; then uses `grilling` to settle the intent and place each ask (new initiative, new goal, feature, change, bug, feedback) | `evidence.md` you can check against the sources, and `intake.md`: the kickoff for the PRD or the agenda for a backlog session |
| **G2 PRD drafted** | Answers to a few questions per round | `specifying` with `grilling`: drivers, measurable goals, requirements with measurable acceptance criteria; a fresh reader tests it | `prd.md` and the initiative in `backlog.json` |
| **G3 PRD agreed** | Your OK on the sync plan | `syncing`: the initiative issue carries the PRD; approvers comment `/approve` | Sign-off recorded in the file |
| **G4 Backlog ready** | Decisions on scope, priority, splits | `grooming`: features with benefit hypotheses and WSJF; stories sized XS–L with measurable done criteria; bugs with urgency | `backlog.json` that passes `validate --require-ready` |
| **G5 Backlog agreed** | Your OK on the sync plan; feedback decisions | Issues, sub-issues, milestones in GitHub; comments come back as feedback on the right feature | Every feature signed off; no open feedback |
| **G6 Handed off** | Owners and dates | Software stories go to `delivering`; operations and marketing stories to their teams | A backlog people are executing |
| **G7 Achieved** | Delivery evidence and metric readings | Delivery records per story; goal measurements; the trace report | Proof of which drivers are satisfied, and every gap |

Your stakeholders never open Amp. They read issues, comment, and type `/approve`; a status
comment on the initiative issue shows them what was agreed, delivered, and achieved, and what
happened to their feedback. Every write to GitHub waits for your approval of a plan Amp shows
you, and Amp applies only that exact plan. Edits stakeholders make in GitHub are never
overwritten silently: they come back as conflicts for you to merge.

## The backlog model

Inspired by SAFe, without epics, with traceability added:

```text
initiative (business drivers, PRD)
└── goals (metric, baseline, target, date; serve drivers)
    └── features (benefit hypothesis, WSJF)
        ├── stories (executable; XS–L; measurable acceptance criteria = definition of done)
        ├── bugs (siblings of stories; priority and urgency)
        └── feedback (every comment lands on exactly one feature)
```

A story is executable when someone who reads only the story, its parents, and the outputs it
depends on can do the work and prove it is done without asking a question. Every acceptance
criterion states a quantity, and every story has at least one real number, time, or date.

## Traceability you can show a steering committee

`backlog.py trace` prints one chain per initiative:

- **Described:** each item cites evidence rows and PRD requirements; PRD requirements no item
  covers are gaps.
- **Agreed:** sign-off per initiative and feature, and whether it went stale after a change.
- **Delivered:** per story and bug, each acceptance criterion met or not, with evidence.
- **Achieved:** each goal's latest measurement against its target and date.
- **Drivers satisfied:** a driver is satisfied when all of its goals are achieved.

Export it with the backlog to Excel (`syncing excel`) for people who want a spreadsheet.

## Choose your starting point

| Your situation | Say this |
| --- | --- |
| Workshop just happened | "Use planning; inputs are in `inputs/`; start with synthesizing." |
| New asks for a backlog you already have | "Use synthesizing on these notes against `backlog.json`, and prepare the grooming session." |
| Rethinking how a team works | "Use planning for a new way of working in [team]; use the operations template." |
| Campaign | "Use planning for the [campaign]; domain marketing; brief draft attached." |
| PRD already approved | "Use grooming to turn `prd.md` into a backlog, then syncing to [repo]." |
| Messy backlog in GitHub or Excel | "Use grooming to rebuild this backlog against the contract; keep links to the old items." |
| Stakeholders commented | "Pull feedback from [repo] and triage it with me." |
| Work shipped, numbers in | "Record delivery for S-2 and S-3 from these PRs, add February's measurement for G-2, and show the trace." |

## Try it in five minutes

The [worked example](../skills/planning/reference/worked-example/README.md) contains a
workshop transcript, minutes, and a rough draft for a month-end close initiative, with the
evidence ledger, PRD, and backlog they become. Run:

```sh
python3 skills/grooming/scripts/backlog.py tree skills/grooming/reference/examples/operations.json
python3 skills/syncing/scripts/sync.py excel skills/grooming/reference/examples/operations.json --out /tmp/close.xlsx
```

## What is built and what is not

| Area | State |
| --- | --- |
| Skills `planning`, `synthesizing`, `specifying`, `grooming`, `syncing` | Built; instructions only, no plugin |
| Contract checks, tree, sign-off status, trace report (`backlog.py`) | Built; unit-tested |
| GitHub sync (issues, sub-issues, labels, milestones, pull, status comment) | Built; unit-tested against an in-memory fake of the GitHub API |
| GitHub Projects | Built: cards, fields (type, priority, urgency, size, readiness, rank score, schedule), a Roadmap view, and a backlog table. Unit-tested against a fake, and run against a live user Project on 2026-11-11 (first sync, a card edited in GitHub, a milestone date moved) |
| Excel export | Built; tested by reading the workbook back |
| Linear, Azure DevOps | Planned; mapping recorded in `skills/syncing/reference/trackers.md` |
| Audio transcription | Not included: supply transcripts from your meeting tool |
| Dedicated enterprise functional-discovery workshops | Use [Blueprinting](blueprinting.md); this planning workflow consumes evidence to produce a PRD and backlog |

Gates are instructions the agent follows plus checks scripts enforce; no plugin blocks a step.
Sign-off identity is the tracker's: anyone with a listed GitHub login can approve.

## How to adapt it

Each skill's `SKILL.md` ends with "Adapt it" and "Check your work". Common changes: add sections
to the PRD template, change size anchors in the charter, add labels in `sync.py`, or propose a
contract field (contract page, `backlog.py`, and a test together).

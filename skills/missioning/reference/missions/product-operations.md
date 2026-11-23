# Playbook: product design and delivery operations

## When to use

A product, operations or marketing initiative from workshop notes to an agreed backlog, then
weekly delivery tracking until the business goals are met. Not for building the software itself:
ready stories go to `delivering` through the `software-delivery` playbook.

## Skills

- `planning`: the conductor through gate 6, with `synthesizing`, `specifying`, `grooming` and
  `syncing`. Follow its gates, sign-off and writing rules; they override this playbook.
- `steering`: the weekly loop: flow, a forecast against each milestone, the log of risks, issues,
  decision requests and guardrails, and the five-line status. If not installed: each week, read
  `backlog.py status` and `trace`, list throughput, work in progress and blockers, keep a
  risks-and-issues list with owner and date, apply each guardrail's stated action on breach, and
  label the report "manual, no skill".
- `releasing`: each promotion of what the initiative ships, with a rollback plan and a read-back.
  A promotion is an outside effect: it runs when the mission contract pre-authorizes it, otherwise
  it is stop reason 2. If not installed: track releases as milestones in the tracker.
- Linear and Azure DevOps adapters and outside sign-off (`record-signoff`) in `syncing`: the
  backlog in those trackers (adapters not tested live), and a sign-off given by email or document
  recorded with its source. If not installed: export to Excel; record outside sign-off as
  `written:` with the email or document.

## Steps

1. Charter the mission with `missioning` in `mission.md` in the planning mission folder; add
   planning's fields (Initiative, Entry point, Tracker, Folder). The README links it.
2. Pick planning's entry point.
3. Run planning's stages and gates 1 to 6 as `planning` says.
4. Each week until gate 7: refresh status and trace, report flow and blockers, act on breaches.
5. Raise each decision request with a deadline and a default.
6. Re-plan when the forecast misses a milestone.
7. Record delivery and goal measurements with `grooming`; run `backlog.py trace`.
8. Close out when gate 7 passes.

Milestones: M1 agreed backlog (steps 2 and 3, planning's gates 1 to 6), M2 delivery tracking
(steps 4 to 7), with the weekly status as the checkpoint report.

## Human gates

Planning's gates 1 to 7 are **agent** rows in the ledger, labelled "gate 1" to "gate 7". Their
Evidence cites the output named in planning's "Checked by" column. Gates 3 and 5 cite the
`backlog.py status` result and its date, never a signer: stakeholders sign in the tracker.

The **human** gates in the ledger are:

- the kickoff: the charter, its success criteria, open questions with defaults and pre-authorized
  effects;
- each decision request, to its named decider with a deadline and a default (`steering`): at the
  deadline the default is applied and recorded in the trail, the row stays open, and work goes on;
- a re-plan that changes a goal, a milestone date or its scope: stop reason 1.

The Definition of Done is shown by gate 7 and the close-out; the owner's review blocks nothing.

Each has a brief in the mission folder's `reviews/`. Owner confirmations inside a stage, such as
the intake in gate 1, stay as that stage's skill runs them and are cited as evidence. Routine
tracker writes keep `syncing`'s shown-plan approval and go in the decision trail.

## Definition of Done

Existing gate 7, plus every breached guardrail shows the action taken, and every blocker has an
owner, a date and an outcome.

## Red flags

- A file that says a stakeholder signed; the tracker shows that.
- "G1" in a document people read; write "gate 1".
- A guardrail reported as breached with no action taken.
- A blocker with no owner or date.

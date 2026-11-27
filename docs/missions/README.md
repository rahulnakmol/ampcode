# Missions you can run

A mission is a piece of work with a clear outcome that an agent runs after you approve it once,
at kickoff. Every mission starts from the [`missioning`](../../skills/missioning/SKILL.md) skill,
which loads one playbook. The playbook says which skills run, in what order, which gates you
decide and when the mission is done. Use a mission for substantial work. For a typo or a
one-line question, a normal Amp request is enough.

## Pick a mission

| Mission | Use it when you want | It delivers | Guide |
| --- | --- | --- | --- |
| ERP and AI transformation | a client moved from today's ERP, processes and ways of working to a funded portfolio of change, AI use cases included | evidence-backed operating model, roadmap and business case; a steering committee decision; one planning mission per funded initiative | [transformation](transformation.md) |
| Product delivery operations | a product, operations or marketing initiative taken from workshop notes to an agreed backlog, then tracked weekly until its goals are met | signed-off PRD, a ready backlog in the stakeholders' tracker, weekly status and forecast, goals traced to delivery | [product-operations](product-operations.md) |
| AI-native software delivery | an idea or requirement built, reviewed, merged and released | milestones merged into `dev` after tests, CI and two fresh reviews; a release verified on its target; each criterion traced to evidence | [software-delivery](software-delivery.md) |
| Campaigns, communications and research | a campaign from brief to launch and readout, or research that informs one | message house, channel plan, approved assets, a launch you approved, funnel measures against target | [campaigns-and-research](campaigns-and-research.md) |
| UX and UI design | how a person or agent experiences something, designed from the need to a checked handoff | journeys, states, directions, a mockup for every state, a passed handoff check, built screens compared with the mockups | [experience-design](experience-design.md) |
| Code and security review | a standalone code review, security review or threat model of a repository, service or change | threat model, triaged scans, proven findings with owners, a coverage statement, a reviewed report | [security-review](security-review.md) |
| Infrastructure and DevSecOps | cloud infrastructure as code, CI/CD, monitoring, releases or incident response | applied plan with zero drift, alerts shown to fire, a tagged release, incident reviews with fixes in the backlog | [infrastructure](infrastructure.md) |
| Product and SaaS assessment | vendors shortlisted, compared or checked against requirements | frozen weights, scores that cite evidence, a ranking with its sensitivity, a recommendation with conditions and owners | [product-assessment](product-assessment.md) |

Not sure which? Name the outcome and say "use missioning to pick the playbook". If two fit,
run them in sequence: an assessment or a design mission often hands its result to a delivery
mission.

## How every mission runs

1. **Charter.** You name the outcome, who decides and who else approves. The agent finds facts
   itself, then asks you once for the facts only you hold (each mission's guide lists them) and
   drafts the charter: success criteria, Definition of Done, open questions with defaults,
   outside effects you can pre-authorize, and what it may do without asking.
2. **Kickoff, the one approval.** The agent checks every outside target (repository, CI,
   credentials, tracker, cloud) and writes a plain-English brief that a fresh reader has
   reviewed. You approve the whole baseline once. Nothing outside the agent's workspace happens
   before that.
3. **Milestones.** The playbook's steps go into the todo list, grouped into milestones. Each
   milestone ends with a checkpoint report that asks nothing.
4. **Questions only for five reasons:** a change to the baseline, an outside effect you did not
   pre-authorize, a fact only a person holds, a red line (security, legal, safety), or a
   milestone that cannot meet its exit criteria after re-planning. Everything else is a recorded
   default you see in the next checkpoint.
5. **Close-out.** The agent audits every gate against its evidence and lists what needs your
   attention, each item with an owner and a date.

Every approval is a row in the mission file's gate ledger naming who answered and where; "looks
good" in chat never counts. On Amp, the [mission-control](../mission-control.md) plugin shows
the kickoff as a dialog and enforces the delivery gates.

A start message has the same shape for every mission:

```text
Use missioning to run a [mission] mission for [outcome]. I decide;
[name, role] approves [what]. Pre-authorize [effects, or none].
```

## Which skills each mission uses

Three skills run in every mission: `missioning` keeps the charter and ledger, `briefing-decisions`
writes the brief for each human gate, and `goldfishing` reviews each brief with fresh eyes. The
table shows the other skills each playbook names (● uses it). Every skill in the kit is used by at
least one mission; `tests/test_missioning.py` fails if a new skill is not.

| Skill | Transformation | Product ops | Software | Campaigns | UX | Security | Infra | Assessment |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `architecting` | | | ● | | | | ● | ● |
| `assessing-products` | | | | | | | | ● |
| `blueprinting` | ● | | | | | | | |
| `crafting` | | | ● | ● | ● | | | |
| `delivering` | | | ● | | ● | | ● | |
| `designing-functions` | ● | | | | | | | |
| `discovering-requirements` | ● | | | | | | | ● |
| `distill` | ● | | | ● | | | | |
| `grilling` | ● | | ● | | ● | | | |
| `grooming` | | ● | | | | ● | | |
| `interrogating-changes` | | | ● | | | ● | | |
| `investigating-incidents` | | | | | | | ● | |
| `monitoring` | | | | | | | ● | |
| `planning` | ● | ● | | ● | | | | |
| `provisioning` | | | | | | | ● | |
| `publishing-engagements` | ● | | | | | | | ● |
| `releasing` | | ● | ● | | | | ● | |
| `reviewing-engagements` | ● | | | | | | | ● |
| `scanning-vulnerabilities` | | | | | | ● | ● | |
| `shaping-engagements` | ● | | | | | | | ● |
| `specifying` | | ● | | | | | | ● |
| `steering` | | ● | | ● | | | | |
| `syncing` | | ● | | | | | | |
| `synthesizing` | | ● | | ● | | | | |
| `threat-modelling` | | | ● | | | ● | | ● |

Three skills are planned, not built: `campaigning` and `researching` (campaigns) and `roadmapping`
(transformation). Their playbooks give a manual fallback, and the output is labelled "manual, no
skill"; a mission never reports that a planned skill ran.

## Where the examples come from

Each guide ends with an example from the 24 real-world validation runs of November 2026 (three
per mission, judged for outcome, process and evidence; one run was refused by a model's safety
check). The runs' findings are in the "Mission validation findings" artifact of
[the validation thread](https://ampcode.com/threads/T-01a1d081-12a6-75af-af66-837c6c0dba88);
fixes from them are already in the playbooks. Simulated scenario runs are in
[`evals/missioning/`](../../evals/missioning/README.md).

## Adapt it

- **Change a mission:** edit its playbook in
  [`skills/missioning/reference/missions/`](../../skills/missioning/reference/missions/); the
  playbook is the source of truth and its guide here explains it. Update both together.
- **Add a mission type:** copy a playbook and keep its six headings (When to use, Skills, Steps,
  Human gates, Definition of Done, Red flags); add it to the table in `missioning`'s SKILL.md, to
  `PLAYBOOKS` in `scripts/ledger_check.py`, to "Owner facts by playbook" in
  `reference/charter.md`, and add a guide here with a row in the tables above.
- **Add a skill:** name it in at least one playbook's Skills section with an `If not installed:`
  fallback, and add its row to the table above.

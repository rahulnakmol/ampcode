# Amp frontier kit

Rahul's personal extensions for [Amp](https://ampcode.com): skills that run substantial work as
**missions** (one approval at kickoff, then autonomous milestones), plus plugins that add agent
modes and the mission-control coordinator. They are designed around clear ownership, efficient
model routing and deliberate token use.

This GitHub repository is the readable source of truth. Amp loads published copies from separate
Personal Plugins and Personal Skills repositories; cloning this one installs nothing
(see [Publish](#publish)).

## Start here

| You want to | Read |
| --- | --- |
| Run a piece of work end to end: software, planning, transformation, design, review, infrastructure, assessment, campaigns | [Missions you can run](./docs/missions/README.md) |
| Pick one skill for a task and copy a prompt for it | [Using the skills](./docs/using-skills.md) |
| Build software from an idea or requirement | [Mission-driven development](./docs/mission-driven-development.md), then the [mission-control reference](./docs/mission-control.md) |
| Take an initiative from workshop notes to a signed-off PRD and a backlog | [Mission-driven planning](./docs/mission-driven-planning.md) |
| Run an enterprise functional-discovery or pre-sales engagement | [Start a Blueprinting engagement](./docs/blueprinting.md) |
| Use the Swift, Weave and Prime modes | [Custom mode dials](./docs/custom-mode-dials.md) |
| Add or change a skill or plugin | [`skills/README.md`](./skills/README.md), [`plugins/README.md`](./plugins/README.md) and [Validate](#validate) |

## How a mission runs

Every mission starts from [`missioning`](./skills/missioning/SKILL.md): one charter, one gate
ledger and one decision trail. The owner approves the charter **once, at kickoff**. The agent then
works milestone by milestone and writes a checkpoint report after each one; the reports ask
nothing. Missions have no budgets and use no agent teams. A software mission starts like this:

```text
Use delivering to start a mission for [outcome] in [repository]. Use grilling
to make the criteria concrete and crafting to render every changed state.
Write one contract with milestones, items, open questions with defaults and
every outside effect, run the readiness preflight on it, and ask me for one
approval at kickoff. Pre-authorize the milestone merges into dev and pushing
mission branches.
```

After kickoff the owner is asked only for one of the five stop reasons:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

Anything else is a recorded assumption, listed in the next checkpoint report.

## Skills

Each skill works on its own and is also used by at least one mission playbook. Prompts, trigger
words and expected results for each are in [Using the skills](./docs/using-skills.md).

| Area | Skill | Does |
| --- | --- | --- |
| Mission core | [missioning](./skills/missioning/SKILL.md) | Charter, gate ledger, decision trail and the eight mission playbooks |
| | [briefing-decisions](./skills/briefing-decisions/SKILL.md) | Plain-English decision brief for every human sign-off, checked by a script |
| | [goldfishing](./skills/goldfishing/SKILL.md) | Fresh-reader review of a brief, spec, plan or design, on a model that wrote none of it |
| | [grilling](./skills/grilling/SKILL.md) | Turns a vague ask into a confirmed brief, plan and handoff prompt |
| Software delivery | [delivering](./skills/delivering/SKILL.md) | Contract mission: one kickoff approval, test-first milestones merged into `dev` |
| | [crafting](./skills/crafting/SKILL.md) | Designs and renders the experience on any surface, for people or agents |
| | [architecting](./skills/architecting/SKILL.md) | Technical design: contracts, ADRs, measurable NFRs; data and AI architecture |
| | [interrogating-changes](./skills/interrogating-changes/SKILL.md) | Adversarial review of a diff or PR with proven findings and a patch-bound verdict |
| | [releasing](./skills/releasing/SKILL.md) | Promotion from `dev` to `rolling` to `main`, release notes, rollback before GO |
| Security and operations | [threat-modelling](./skills/threat-modelling/SKILL.md) | Trust zones, STRIDE and LINDDUN per flow, abuse cases, OWASP ASVS review |
| | [scanning-vulnerabilities](./skills/scanning-vulnerabilities/SKILL.md) | Merges and triages scanner SARIF with stated coverage |
| | [provisioning](./skills/provisioning/SKILL.md) | Infrastructure as code: preview, policy, cost, approved apply, drift check |
| | [monitoring](./skills/monitoring/SKILL.md) | SLOs, error budgets and burn-rate alerts proven to fire outside production |
| | [investigating-incidents](./skills/investigating-incidents/SKILL.md) | Read-only incident investigation and a post-incident review |
| Planning | [planning](./skills/planning/SKILL.md) | Runs a planning mission through gates G1–G7 |
| | [synthesizing](./skills/synthesizing/SKILL.md) | Notes and transcripts into cited evidence and a confirmed intent |
| | [specifying](./skills/specifying/SKILL.md) | One PRD per initiative with measurable goals and criteria |
| | [grooming](./skills/grooming/SKILL.md) | Backlog contract: features, executable stories, bugs, feedback, trace |
| | [syncing](./skills/syncing/SKILL.md) | Syncs the backlog to GitHub, Azure DevOps, Linear or Excel and reads sign-off back |
| | [steering](./skills/steering/SKILL.md) | Weekly flow metrics, forecast, risks and decisions log, five-line status |
| Blueprinting | [blueprinting](./skills/blueprinting/SKILL.md) | Engagement continuity, policy and shared helpers for the five domain skills |
| | [shaping-engagements](./skills/shaping-engagements/SKILL.md) | Opportunity, pre-sales and RFP work, including a weighted fit-gap |
| | [discovering-requirements](./skills/discovering-requirements/SKILL.md) | Workshops, questionnaires and attributed evidence |
| | [designing-functions](./skills/designing-functions/SKILL.md) | Processes, operating model and functional handover |
| | [publishing-engagements](./skills/publishing-engagements/SKILL.md) | Narratives, reviewed packets and Office or PDF exports |
| | [reviewing-engagements](./skills/reviewing-engagements/SKILL.md) | Source-grounded review of functional evidence and deliverables |
| Research and assessment | [assessing-products](./skills/assessing-products/SKILL.md) | Vendor and product assessment with weights frozen before scoring |
| | [distill](./skills/distill/SKILL.md) | YouTube videos into an original article, brief and offline package (formerly `distilling-videos`; runtime cache and archive identifiers keep that name) |

## Plugins and modes

| Plugin | Adds | Guide |
| --- | --- | --- |
| [`amp-custom-mode-dials.ts`](./plugins/amp-custom-mode-dials.ts) | Swift, Weave and Prime modes between Amp's Dial positions | [Custom mode dials](./docs/custom-mode-dials.md) |
| [`mission-control/`](./plugins/mission-control/) | The contract record for `delivering`: kickoff dialog, preflight, merge blockers, reports | [Mission-control reference](./docs/mission-control.md) |

Every agent mode here runs its work as a mission through the shared mission core in
[`missioning`](./skills/missioning/reference/agent-modes.md). For architecture, data and AI, or
incident advice, run a mission: its playbook loads `architecting` or `investigating-incidents`.
The Archi, Darci and Opsci modes were retired for those skills.

## Layout

```text
plugins/                  TypeScript or JavaScript Amp plugins
skills/<skill-name>/      Agent Skills, each rooted at SKILL.md
docs/                     User guides; docs/missions/ has one guide per mission type, docs/research/ the design rationale
evals/<skill>/            Fresh-agent evaluations per skill: scenarios, rubrics and results
tests/                    Bun plugin tests and Python skill-script tests
scripts/check.sh          Repository validation (run with `make check`)
.amp/plugins/             Project-only plugins, such as the mission-control dialog preview
```

Branches: `dev` is integration, `rolling` the canary snapshot and `main` the stable release.
Every change is a pull request to `dev`.

## Validate

Run:

```sh
make check
```

The check loads every plugin through the installed Amp CLI, runs the Bun plugin tests and the
Python skill-script tests, syntax-checks skill shell scripts, checks formatting errors detectable
by Git, and validates the metadata and 500-line limit of every skill. It needs `amp`, `bun` and
`python3`; the tests make no network, paid or cloud calls.

Pull requests targeting `dev` and pushes to `dev` run the same command in
[`Validate extensions`](./.github/workflows/check.yml). Its stable required check is
**Extension checks**, emitted by GitHub Actions. The workflow uses pinned actions and tool
versions, verifies the Amp binary checksum, grants read-only repository access and supplies no Amp
or cloud credentials. PR code runs on disposable GitHub-hosted Ubuntu runners; no Depot runner is
configured for this repository.

`dev` requires a pull request, an up-to-date successful **Extension checks** result from GitHub
Actions, and resolved review conversations. Protection applies to administrators and disallows
force pushes and deletion. No mandatory human review count is imposed: a contract mission merges
each milestone into `dev` after its own tests, CI and two fresh reviews, with no owner merge gate.
These controls do not stop an agent with repository-administration credentials from changing
policy. Rolling and stable promotion and extension publication remain separate.

## Publish

Amp stores personal plugins and personal skills in separate global repositories:

- `amp plugins repositories`
- `amp skills repositories`

Copy standalone plugin entry points, or complete directory plugins such as `mission-control/`, to the
root of the Personal Plugins repository. Do not omit supporting Markdown files. Copy each complete
`skills/<skill-name>/` directory to the root of the Personal Skills repository. Review and commit
changes, then push only after explicit approval; new threads load published versions
automatically.

Never commit API keys, provider credentials, access tokens or generated secret-bearing settings
here.

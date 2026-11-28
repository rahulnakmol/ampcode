# Using the skills in Amp

Choose a skill by the result you need. You can name it directly in a normal Amp
message: **“Use missioning…”**, **“Use grilling…”**, **“Use crafting…”**, **“Use delivering…”**,
**“Use planning…”**, **“Use blueprinting…”**, or **“Distill this video…”**. The examples below are prompts to paste into chat, not
terminal commands. Natural-language triggers help Amp select an installed skill;
they are not exact-match keywords or a guarantee that a skill was loaded. Name
the skill explicitly when you want it, and ask Amp which skill it is using if unclear.

## Pick the result, then the skill

| What you need | Skill | Typical trigger words | What you receive |
| --- | --- | --- | --- |
| Start, run or close any kind of mission with one charter and sign-off log | **missioning** | start a mission, mission charter, open questions and defaults, record or audit approvals, which playbook | Charter, gate ledger and decision trail checked by `ledger_check.py`; one kickoff approval; the playbook's steps in your todo list; a close-out audit |
| Make an idea or requirement concrete | **grilling** | grill me, clarify requirements, pressure-test, pre-mortem, spec this out, write a PRD | Confirmed brief, acceptance criteria, risks, plan and handoff prompt |
| Design how a person or agent experiences something | **crafting** | design, redesign, craft, prototype, mock up, polish, critique, accessibility audit, user flow | Journeys, states, design direction, mockups/specification and critique |
| Deliver a substantial software outcome | **delivering** | use delivering, deliver this feature, execute this approved brief, resume this mission | One contract approved once at kickoff; milestones merged into `dev` after local end-to-end evidence per package, a pure-core check, CI and two fresh reviews on another model; checkpoint and close-out reports |
| Review a document with fresh eyes | **goldfishing** | fresh-eyes review, Goldfish review, can a newcomer follow this, novice-reader test | Findings with location, severity and smallest fix; a review record |
| Write a sign-off a non-technical approver understands | **briefing-decisions** | decision brief, approval summary, sign-off text, executive sign-off | A checked plain-English brief with risks, exclusions, undo steps and a technical record |
| Turn public YouTube research into an original article | **distill** | distill this video, distill these videos, write a whitepaper from these videos | Original evidence-backed article, research brief and supported offline package |
| Plan an initiative from workshop inputs to an agreed backlog | **planning** | plan this initiative, run a planning mission, from workshop notes to backlog | Charter, gated stages, signed-off PRD, ready backlog in GitHub or Excel, traceability |
| Turn notes, transcripts, minutes and drafts into evidence and a confirmed intent | **synthesizing** | synthesize these notes, what are they really asking for, prepare the kickoff or grooming session | `evidence.md` with cited evidence; `intake.md` with the intent, where each ask goes in the backlog, and the next session's agenda |
| Write a PRD, process-change brief or campaign brief | **specifying** | write a PRD, draft the brief, complete this PRD | `prd.md` with drivers, measurable goals, requirements and criteria; initiative seeded in the backlog |
| Groom a backlog of executable stories | **grooming** | groom, refine, break down, split, size, prioritise, triage feedback | `backlog.json` that passes the contract and Definition of Ready; trace report |
| Write a technical design with contracts, decisions and measurable quality targets | **architecting** | technical design, architecture, ADR, NFRs, API contract, data platform design | `design.md` with contracts, ADRs and NFRs (number, unit, test) checked by `design_check.py`; a threat-model link when trust boundaries change |
| Review a diff or pull request adversarially before it merges | **interrogating-changes** | interrogate this change, adversarial review, review gate, review this PR against its criteria | A finding ledger with proven, located findings, regressions apart from old defects, a lowered-bar check, and a verdict tied to the exact patch |
| Promote, tag and release with a rollback plan | **releasing** | rolling snapshot, stable release, promote dev to rolling, release notes, rollback plan | A read-only promotion plan with a digest, release notes, and a GO or NO-GO that requires a rollback plan |
| Threat model a design or system | **threat-modelling** | threat model, STRIDE, LINDDUN, abuse cases, ASVS review, trust boundaries | `model.json` checked by `threat_check.py` and rendered tables; every threat mitigated with a verification, accepted by a named person, or a backlog item |
| Merge and triage security scan results | **scanning-vulnerabilities** | triage these scans, SARIF, dependency or secret scan, what did the scanners find | One findings table with dispositions, coverage per category ("scanned, N findings" or "not examined"), never "secure" |
| Assess products or vendors against agreed criteria | **assessing-products** | vendor assessment, compare tools, score products, SOC 2 or ISO evidence | Frozen weights with a digest, scores with cited evidence, claims kept "claimed", a recommendation with conditions and owners |
| Plan and apply infrastructure changes safely | **provisioning** | terraform plan, bicep what-if, change set, apply infrastructure, drift check | A change summary with counts and a digest, destructive stateful changes named, an apply only of the approved plan, then a read-back and drift check |
| Turn NFRs into SLOs and alerts | **monitoring** | SLO, error budget, burn-rate alert, runbook, dashboards, synthetic checks | `slos.json` checked by `slo_check.py`, the fast and slow alert pairs, a runbook per alert, and each alert "not proven" until it fires outside production |
| Investigate an incident and write its review | **investigating-incidents** | incident, outage, error spike, post-incident review, postmortem, root cause | Hypotheses with evidence and counter-evidence, mitigation apart from the durable fix, a review checked by `pir_check.py`, and its actions filed as draft bugs |
| Publish a backlog and collect sign-off | **syncing** | sync to GitHub, Azure DevOps or Linear, export to Excel, pull comments and approvals | Tracker items with parent links and milestones or iterations, or a workbook; sign-offs and feedback back in the file |
| Steer delivery week by week | **steering** | weekly steering, flow metrics, forecast, RAID log, status report, are we on track | Throughput, cycle time, aging work and a seeded forecast from `flow.py`; a log checked by `raid_check.py`; a five-line status and a full pack |
| Run an enterprise functional-discovery engagement | **blueprinting** | start or resume a consulting engagement, functional discovery, ERP/CRM workshops | Retained evidence, decision lineage, explicit gaps and coordinated functional handoffs |
| Prepare client workshops and interpret supplied evidence | **discovering-requirements** | workshop agenda, client questionnaire, attributed transcript, debrief | Cited findings, contradictions and owned follow-up questions |
| Design business processes and operating models | **designing-functions** | as-is/to-be, roles, exceptions, handoffs, functional specification, kickoff | Traceable functional design, alternatives and acceptance gaps |
| Qualify an offer or prepare an RFP response | **shaping-engagements** | pre-sales, bid decision, proposal, fit-gap, weighted fit-gap, effort estimate | Grounded commercial scope, assumptions, estimates, a weighted fit-gap with frozen weights, and unresolved obligations |
| Prepare reviewed consulting documents and decks | **publishing-engagements** | executive brief, editable handoff, client-safe packet | Inspected selected exports with evidence and sharing restrictions |
| Challenge consulting evidence and deliverables | **reviewing-engagements** | review functional coverage, check claims, review proposal or handoff | Source-grounded findings tied to exact revisions |

The planning skills are covered in [Mission-driven planning](mission-driven-planning.md);
the six enterprise consulting skills are covered in [Start a Blueprinting engagement](blueprinting.md).
Source availability and publication to your own Amp account are separate. Swift, Weave and Prime
are execution modes, not skills; each runs its work as a mission through `missioning`. The Archi,
Darci and Opsci advisory modes were retired: use `architecting` and `investigating-incidents`.

## Grilling: make the ask executable

**Use when:** the intended result, audience, constraints or success criteria are
unclear, or a wrong assumption would be expensive. It is also useful for testing
an apparently complete proposal before committing to it.

**Say:** “Grill me,” “What am I missing?”, “Poke holes in this,” “Turn this into a
plan,” “Clarify the edge cases,” or “Use grilling to write a PRD.”

```text
Use grilling to turn this idea into a concrete brief: recover unsaved edits in
our desktop document app. Find the important unknowns, recommend answers and
pressure-test failure cases. End with scope, non-goals, measurable acceptance
criteria, verification and a handoff prompt. Do not implement yet.
```

**Give Amp:** the idea/problem, who it affects, existing evidence, known constraints,
and what decision or artifact you want at the end. You do not need a complete spec.

**A good result looks like:** a few high-value questions, facts researched rather
than asked back to you, explicit assumptions, testable criteria, an edge-case and
pre-mortem pass, and a brief you can confirm. A fresh reader can explain the intended
outcome without private coaching. For example, “preserve the last acknowledged
edit after forced termination” is testable; “make recovery robust” is not.

**Not good:** endless interviews, questions answered by the repository, invented
user decisions, or a polished PRD whose success cannot be measured. Clear, small,
reversible requests should proceed without a full interview.

**Next:** use crafting if the experience needs design; use delivering when you want
the confirmed outcome built. [Skill instructions](../skills/grilling/SKILL.md).

## Crafting: design the whole interaction

**Use when:** you need an intentional experience, not just working functionality.
This includes screens, CLI/TUI, messages, documents and agent-facing APIs/MCP tools.
Use it independently for design-only work or within a delivery mission for relevant UX.

**Say:** “Craft the flow,” “Redesign this screen,” “Mock up alternatives,” “Critique
this experience,” “Audit accessibility,” “Find inspiration,” or “Polish these states.”

```text
Use crafting to design document recovery for a macOS editor. Cover the interrupted
session, recovered edits, conflicts, empty state, permission failure and cancel/undo.
Show the user journey and alternative directions, recommend one, and explain
keyboard and accessibility behavior. Produce a design handoff, not code yet.
```

**Give Amp:** the user/job, platform, screenshots or current flow, branding constraints,
states that matter, and whether you want exploration, critique or implementation-ready
design. State any research budget or unavailable tools.

**A good result looks like:** a clear reason for the design, complete journeys and
failure/recovery states, native platform behavior, accessibility, and inspected visual
or interaction artifacts. A CLI design should have meaningful command/error examples;
an API design should explain agent inputs, outputs and recovery, not fabricate a screen.

**Not good:** attractive happy-path mockups with no errors, unexplained generic styling,
or a screenshot presented as proof that an interaction works. Generated concepts are
design references, not running UI. Missing research/rendering tools must be disclosed.

**Next:** refine the selected direction or hand it to delivering alongside acceptance
criteria. [Skill instructions](../skills/crafting/SKILL.md).

## Delivering: own the outcome through verification

**Use when:** you want a major feature, use case or concrete requirement implemented, or need to
resume a multi-step delivery. It brings grilling and crafting into the work; you do not need to
launch every skill yourself.

**Say:** "Use delivering for this feature," "Deliver this approved brief," "Execute this
implementation plan," or "Resume the mission."

```text
Use delivering to implement the document-recovery brief in [repository].
Check the brief against the current code and report drift. Write one contract
with milestones, items, open questions with defaults and every outside effect,
run the readiness preflight on it, and ask me for one approval at kickoff.
Pre-authorize the milestone merges into dev and pushing mission branches.
Do not release or deploy.
```

**How it runs:** one contract, a readiness preflight, one approval at kickoff. Then milestones
run on their own: items test-first in child threads or subagents, end-to-end tests run locally
for each changed package before any pull request, two fresh reviews per milestone on a model that
wrote none of it, a squash merge into `dev` when the gates pass, and a checkpoint report that asks
nothing. After kickoff it asks you only when:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

Anything else becomes a recorded assumption in the next checkpoint report.

**Give Amp:** the outcome or brief, repository, relevant design and decision references,
constraints, and which outside effects you pre-authorize. Say whether existing work is
uncommitted or only on a particular runner.

**A good result looks like:** criteria with finite case lists, each tied to failing-then-passing
evidence; small coherent changes; real journeys; two independent reviews per milestone with every
finding fixed, re-planned or filed; and a close-out that separates merged into `dev`, released
and installed. It says whether customers can now do the intended job and what remains unverified.

**Not good:** "all tests green" with no demonstrated outcome, a merge request called a merge,
fabricated evidence, a question to you that a default answers, or a release inferred from
permission to code. Do not use a mission for a typo, a standalone review or a release-only task.

**Next:** follow the [Mission-driven development guide](mission-driven-development.md) for the
five journeys and the [kickoff prompts](mission-control.md#ways-to-kick-off-a-mission).
[Skill instructions](../skills/delivering/SKILL.md).

## Goldfishing: review with fresh eyes

**What it is:** the shared fresh-reader review. The reviewer gets the artifact, its sources and
the grading criteria, never your conversation or the verdict you hope for. Other skills call it;
you can call it directly.

**Use when:** a plan, spec, brief, design or handoff must work without its author: before a
sign-off, before handing work to another agent, or to test whether a non-technical approver
understands it.

```text
Use goldfishing to review docs/designs/export.md at its current commit.
Lenses: comprehension, then critic against src/export/. Report each finding with
location, severity and the smallest fix, and list the files the reviewer read.
Do not edit anything.
```

**A good result looks like:** findings tied to exact lines, a paraphrase for the comprehension
lens, concrete counterexamples for the critic lens, and an honest "not run" when a reviewer
failed. **Not good:** a reviewer that was told the answer, a self-review called fresh, or a
round cap treated as acceptance.

**Adapt it:** add your own reviewer questions in the calling skill; change the novice persona to
match your approver; set a different round cap in the calling skill and say why. On Claude Code,
VS Code or the Copilot app, follow [`reference/hosts.md`](../skills/goldfishing/reference/hosts.md)
and run the isolation check once. [Skill instructions](../skills/goldfishing/SKILL.md).

## Briefing decisions: sign-offs in plain English

**What it is:** a fixed brief shape with ten headings, a front-matter summary and a closing
technical record, plus `scripts/brief_check.py`, which rejects long sentences, hard text, missing
sections, codes such as hashes or task IDs outside the technical record, and any HTML or Markdown
that hides words when the brief is rendered.

**Use when:** anyone must approve, sign off or choose: a design, merge, release, budget, vendor
or roadmap. `delivering` uses it for the one kickoff brief of a contract mission.

```text
Use briefing-decisions to write the sign-off brief for moving our demo site to
paid hosting. The approver is our finance director, who does not write software.
Run brief_check.py until it passes, then a goldfishing novice-reader review.
```

**A good result looks like:** a reader answers what they approve, what can go wrong, what it
costs and what is not included from the brief alone; every risk in the summary matches the risks
section word for word; undo steps say who acts and how long it takes. **Not good:** a brief that
passes the checker but hides the real decision in the technical record.

**Adapt it:** edit the constants at the top of `brief_check.py` and `banned.json`, then the copy in
`plugins/mission-control/lib/brief.ts`; a test fails when the lists differ. Without Amp, give the
approver the Markdown file and open any HTML picture in a browser. On Amp, publish it as a
document; mission-control links that document in its kickoff dialog.
[Skill instructions](../skills/briefing-decisions/SKILL.md).

## Missioning: one charter and sign-off log for any mission

**What it is:** the thin conductor every mission starts from. One mission file holds the charter
(outcome, decision owner, approvers, success criteria, Definition of Done, open questions with
defaults, pre-authorized effects, and what the agent may do without asking, must always ask, and
must stop for), the gate ledger and the decision trail. The owner approves it once, at kickoff. Eight playbooks (ERP and AI transformation, product delivery operations,
software delivery, campaigns and research, UX and UI design, code and security review,
infrastructure and DevSecOps, product and SaaS assessment) list the steps, human gates and
Definition of Done; only the chosen one is loaded. `blueprinting`, `planning`, `delivering` and
`crafting` stay the conductors their playbooks call. Skills planned for later waves are marked
*planned* with a manual fallback. [Missions you can run](missions/README.md) explains each
mission type: when to use it, how to start it, the skills it runs in order, what it delivers and
its Definition of Done.

**Use when:** you start or resume a mission of any kind, want one place that shows who approved
what and on which brief, or work on Claude Code or Copilot where no owner dialog exists.

```text
Use missioning to run a product assessment of three expense tools for finance,
on the Copilot app. Elena Petrova decides; Tom Okafor approves. Open question:
paid trials, default none. Agree the weights with Elena before any scoring.
```

**A good result looks like:** a charter with every field, agreed before the work; the playbook's
steps in the todo list with `skip: <reason>` where a step is not done; questions only at
kickoff and for the five stop reasons, each with a recommended answer; a checked brief and a
fresh novice-reader review before every sign-off; each approval a ledger row naming an approver and where they answered;
`ledger_check.py` printing `pass`; a close-out that lists what needs your attention. **Not
good:** "looks good" in chat recorded as approval, a planned skill reported as run, a deleted
todo step, or a question that a recorded default already answers.

**Adapt it:** add a playbook with the same six headings and add its name to `PLAYBOOKS` in
`scripts/ledger_check.py`; change charter fields in the checker's `FIELDS` and
`reference/charter.md` together; add a host column to `reference/hosts.md` and label it "not
tested" until you run it. The checker proves the record is complete, not that a person answered:
on Amp, `mission-control`'s kickoff dialog remains the stronger record for delivery missions.
[Skill instructions](../skills/missioning/SKILL.md).

## Distill: turn video sources into an original argument

**Use when:** one or more public YouTube videos are research inputs for an article,
whitepaper or decision brief. This is not the default tool for repository research,
ordinary webpage summaries or implementing software.

**Say:** “Distill this video,” “Distill these videos,” or “Write an evidence-backed
article from these YouTube sources.”

```text
Distill these public YouTube videos: [URLs]. Write an original article for
engineering leaders deciding whether local-first CI suits their teams. Develop
a thesis, check counterevidence and preserve source timestamps. Include a research
brief and offline HTML/PDF package if the required tools are available. State any
transcript verification gaps; do not archive to Azure without my approval.
```

**Give Amp:** up to ten public YouTube URLs, intended reader and decision, desired
angle, language, output format and research/spending limits. Tell it if you already
have transcripts or need to retain media.

**A good result looks like:** an original analyst-authored argument, supported claims
and counterevidence, reusable timed transcripts, relevant visual evidence, attribution,
and an inspected package. The article should help a reader decide or act, not simply
retell each speaker. Missing or unchecked evidence is visibly incomplete.

**Not good:** a recap relabeled a whitepaper, invented experiments, unsupported claims,
or “fully automatic” transcription promises. No transcription provider adapter is
selected; normalized transcripts and required audio checks must be supplied/performed.
PDF needs a supported local browser; live Azure archival remains separately authorized
and unqualified. See [current capability limits](../skills/distill/SKILL.md#what-works-today-and-what-does-not).

**Next:** review the argument and evidence before publication or archival.
[Skill instructions](../skills/distill/SKILL.md).

## Planning: from workshop to agreed, traceable backlog

**Use when:** you own an initiative (product, operations change or new way of working,
or marketing campaign) and need to go from raw inputs to a PRD stakeholders sign off and a
backlog teams can execute, with proof later that it met the business goals. `planning`
conducts the mission; `synthesizing`, `specifying`, `grooming` and `syncing` each work
alone too.

```text
Use planning to run a mission for our month-end close (operations). Inputs are in
planning/close-3-days/inputs/. Approvers are priya-r and tokafor on GitHub; sync to
acme/close. Success means a signed-off PRD and a ready backlog by 31 January.
```

**A good result looks like:** a confirmed charter; evidence that cites sources; a PRD with
numbered drivers, goals and measurable criteria tested by a fresh reader; a backlog that
passes `validate --require-ready`; a sync plan shown before any write; sign-offs and
feedback read back from GitHub; and a gate-by-gate report.

**Not good:** a PRD with unmeasurable goals, stories without numbers in their acceptance
criteria, issues created without your approval, or "done" claimed from a closed issue.
See [Mission-driven planning](mission-driven-planning.md) for stages, entry points and limits.

## Blueprinting: from client evidence to a functional decision

**Use when:** consultants or business analysts need workshops, as-is/to-be processes,
operating models, functional specifications, implementation kickoff or pre-sales/RFP work.
Choose `planning` for a tracker-ready backlog, not as a substitute for Blueprinting's client
authority and evidence rules. Blueprinting is functional consulting, not technical architecture.

```text copy Copy Blueprinting Workshop Prompt
Use blueprinting to prepare a discovery workshop about our order-to-cash handoffs.
The audience is the finance and operations leads. Help us identify the next business
decision, missing evidence, actors and receiving teams. Draft an agenda and questionnaire.
Check processing restrictions before reading client material. Do not create a vault,
activate integrations or send the questionnaire yet.
```

**Give Amp:** the business problem, journey, audience, desired decision, available evidence,
client authority and known processing restrictions. For retained engagement setup, also supply
an explicit absolute private root and an authorized compatible template package on the execution
machine. The skills are published to Rahul's User Skills; the separate template repository is
not remotely published. Missing templates block template-backed Start, not a draft agenda.

**A good result looks like:** attributed evidence, explicit contradictions and missing voices,
questions tied to decisions, traceable functional requirements, scope-bound client confirmation,
and only the editable handoffs needed for the journey. A transcript is not business approval;
an export is not permission to share. Qualification is synthetic/redacted, not production certification.

Follow [Start a Blueprinting engagement](blueprinting.md) for the complete kickoff prompt,
preview/confirmation boundary, domain choices, resume prompt and current limits.

## Engineering, security and operations

- **architecting:** "Use architecting to design the webhook delivery service in `services/hooks`:
  contracts, ADRs and NFRs with numbers." It runs `scripts/design_check.py` on the design. Without
  a shell it gives you the command and marks the check "not run".
- **interrogating-changes:** "Use interrogating-changes on `origin/dev...HEAD` (from the merge-base), with
  the acceptance criteria in `docs/brief.md`." A fresh reviewer gets the diff and the criteria,
  never the author's claims. `scripts/review_ledger.py verdict` ties the verdict to the patch, and
  `scripts/floor_guard.py` flags lowered bars such as new skips or silenced checkers.
- **releasing:** "Use releasing to plan a rolling snapshot of `dev`." `scripts/release_plan.py
  plan` only reads git; a promotion runs only with your approval of the exact plan, or when a
  mission contract pre-authorizes it.
- **threat-modelling:** "Use threat-modelling on `docs/designs/order-export.md`; its trust
  boundaries change." It writes `model.json`, checks it with `scripts/threat_check.py check` and
  renders the tables where the design's `Threat model:` line points. Backlog items stay proposed
  until `grooming` files them.
- **scanning-vulnerabilities:** "Merge and triage these SARIF files from the scan of `services/api`."
  `scripts/sarif_triage.py merge` and `coverage` build the findings table; `check` rejects a
  report without dispositions or with words such as "secure". It scans only local paths you name.
- **assessing-products:** "Use assessing-products to score the three tools against the criteria
  we agreed." `scripts/score.py freeze` locks the weights before any score; `score` refuses a
  changed weight; `check` needs conditions with named owners. `shaping-engagements` uses
  `score.py --fit-gap` for a weighted pre-sales fit-gap.
- **provisioning:** "Use provisioning on this Terraform plan for staging."
  `scripts/change_summary.py summarize` gives the counts and a digest; an apply runs only on
  that exact plan, with your approval or a mission contract that pre-authorizes it, and a
  destructive stateful change needs its own confirmation.
- **monitoring:** "Use monitoring to set SLOs and alerts from the NFRs in `design.md`."
  `scripts/slo_check.py check` validates the SLO file and `alerts` prints the burn-rate pairs;
  `check --release` fails while any alert has no firing evidence from outside production.
- **investigating-incidents:** "Use investigating-incidents: checkout errors rose after this
  morning's release." It works read-only from the evidence you give it; `scripts/pir_check.py
  check` validates the review and `bugs` files its actions in a `grooming` backlog.
- **steering:** "Use steering for this week's review of the close initiative." `scripts/flow.py`
  measures flow and forecasts from `flow.json` or a `gh issue list --json` export;
  `scripts/raid_check.py` checks the log and the status. It writes to no tracker.

## Combine skills without unnecessary ceremony

- **“I have an idea.”** Grilling makes it concrete; crafting designs relevant
  interactions; delivering owns implementation when you authorize it.
- **“The requirement is clear, but the flow is confusing.”** Start with crafting;
  clarify only missing decisions instead of restarting a full interview.
- **“The brief and design are already approved.”** Start with delivering; reuse
  valid approval and check drift rather than repeat every earlier discussion.
- **“These videos may inform our product decision.”** Distill can supply research;
  its article does not itself approve a design or start a software mission.
- **“The backlog is agreed; build the software stories.”** Hand ready stories to
  delivering; the backlog's acceptance criteria become its expectations.
- **“Run a security review / product assessment / infrastructure change.”** Start with
  missioning; its playbook names the steps, the sign-offs and what is not built yet. See
  [Missions you can run](missions/README.md).
- **“Fix this typo.”** Use a normal Amp request. A mission is disproportionate.

Skills must be installed to be loaded. Ask Amp to check availability and reload existing
Personal Skills if needed. Installing a missing skill is a separate action with a
destination; cloning this GitHub repository alone is not Personal installation.
Skill instructions guide the agent; they do not create permissions, a scheduler,
guaranteed spend limits or a security boundary.

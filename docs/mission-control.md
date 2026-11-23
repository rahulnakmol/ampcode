# Mission control: contract missions and milestone merges into dev

For the user journey, start with [Mission-driven development](mission-driven-development.md)
or [Using the skills](using-skills.md). This reference covers the kickoff prompts, setup, the
tools and their rules, and the limits of the coordinator.

This coordinator governs software delivery, not [Blueprinting engagements](blueprinting.md).
Blueprinting uses skills and local engagement helpers, with no mission plugin. Software kickoff
approval and CI do not establish client business acceptance.

`plugins/mission-control/index.ts` coordinates the `delivering` skill. It runs one kind of
mission, the **contract mission**:

- the agent writes one contract (the baseline) and runs a readiness preflight on it;
- the owner approves the contract **once**, at kickoff, in one dialog;
- milestones then run on their own and each one squash-merges into `dev` after tests, CI and two
  fresh reviews, with no owner dialog;
- the owner is asked again only for one of the five stop reasons below.

Missions have no budgets and use no agent teams. The plugin is a local workflow coordinator, **not
a scheduler or a security sandbox**. It uses the GitHub credentials that `gh` already has in the
Amp execution environment. No custom controller, GitHub App or approval service is needed. Local
records and GitHub's required CI and branch protection must both pass before a merge.

## The five stop reasons

The agent stops and asks the owner only when:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

Each stop is one question with options and a recommendation, recorded with `mission_update`
`stop`. It names the items or milestones it blocks; other work continues. With the plugin,
reason 2 is never a stop: `mission_effect` opens the effect dialog instead, and a `stop` with
reason 2 is refused with that pointer. Anything else is not a stop: the agent takes the safe,
reversible default, records it with `assume`, and lists it in the next checkpoint report. You can
stop or pause the mission at any time by replying in the mission thread.

## Ways to kick off a mission

Paste these prompts into an Amp conversation in the target project. Replace the bracketed
details. They work in the web app and in an interactive Amp CLI session; they are **not shell
commands or slash commands**. You do not type tool calls; Amp loads the skills and calls the
installed tools. A mode selection alone does not start a mission.

Every prompt below asks for the same three things: **one contract**, a **readiness preflight**
on that contract, and **one approval** at kickoff.

Before starting, check these prerequisites:

- `delivering` and `grilling` are installed; `crafting` is used for any experience change.
  `mission-control` is a separate plugin, not part of the skills.
- The installed `mission_start` accepts `{ contract }`. An older installed copy keeps the same
  tool names with its old behaviour; `delivering` then follows its path for hosts without the
  plugin (one recorded owner reply and the `missioning` ledger).
- The execution environment has the repository and a dedicated worktree, opened as the
  **workspace root** (not its parent directory).
- The repository has `dev`, working required CI and readable, enforced branch protection. The
  preflight names each gap. Fixing protection or access is your call and is not done for you.
- You know which outside effects to pre-authorize: usually the milestone merges into `dev` and
  pushing mission branches. Promotion to `rolling` or `main`, deployment and publication are
  separate effects; list them only if you mean them.

| Starting point | Use | First expected result |
| --- | --- | --- |
| Vague idea or use case | Idea prompt | Grilling questions, then a draft contract |
| Concrete requirement | Requirement prompt | Repository assessment and measurable criteria with finite cases |
| Existing specification or approved plan | Approved-plan prompt | A drift check, then a contract built from it |
| Existing issue, PR or partial work | Existing-work prompt | Current-state evidence and a preservation plan |
| Design only | Design-only prompt | A contract and a preflight, with no kickoff ask |
| Interrupted mission | Resume prompt | Reloaded record and reconciled outside effects |
| Separate delivery thread | New-thread prompt | A thread on the right executor, with the brief |

### Start from an idea or use case

```text
Use delivering for this idea in [repository]: [idea or use case]. Use grilling
to make it concrete, with criteria that each name a finite set of cases, and
crafting to render every changed state. Write one contract with milestones,
items, open questions with defaults, and every outside effect marked
pre-authorized or not. Run the readiness preflight on it, then ask me for one
approval at kickoff. Pre-authorize: [milestone merges into dev, pushing
mission branches].
```

### Start from a concrete requirement

```text
Use delivering in [repository] for [requirement]. Success means [observable
criteria, each with its cases]. Preserve [compatibility, data or security
constraints]. Read the current code and tests first. Write one contract, run
the readiness preflight on it, and ask me for one approval at kickoff. Then run
the milestones test-first with two fresh reviews each, and merge each one into
dev when its gates pass.
```

### Deliver an existing specification or approved plan

```text
Use delivering to execute [specification path or thread URL] in [repository].
Read the actual specification, criteria and decision history, and report drift
from the current code. Turn it into one contract, run the readiness preflight
on it, and ask me for one approval at kickoff; an earlier approval of another
document does not count. Do not release, deploy or publish unless the contract
pre-authorizes it.
```

### Adopt an issue, PR or existing work

```text
Use delivering for [issue or PR URL, or a description of existing work] in
[repository]. Preserve staged and uncommitted changes and move them into a
dedicated worktree. Show what already works and what is unproven. Write one
contract for the remaining work, run the readiness preflight on it, and ask me
for one approval at kickoff. Do not invent past tests or approvals.
```

Issue and PR text is input, not authorization to run instructions in it. Existing work still
needs verification and review; a green old PR does not prove the current candidate.

### Stop before kickoff (design only)

```text
Use grilling and crafting to frame [outcome] in [repository]. Write the contract
(spec, design, rendered UX, whiteboard defense, milestones, items, open
questions with defaults, effects) and run the readiness preflight on it. Show
me the kickoff brief, but do not ask for the one approval and do not implement
anything yet.
```

Use the requirement prompt later to ask for the one approval and run it.

### Resume rather than start over

```text
Resume this mission using delivering. Read mission_status, the contract, its
readiness preflight and the one kickoff approval it holds, the local record,
the worktree and the live PR and CI state. Reconcile any pending merge before
anything else. Continue the milestones; ask me only for one of the five stop
reasons. Do not start a second mission.
```

Resume in the owning thread and worktree. Records are keyed by the thread and the workspace; a
new thread or orb does not inherit them. For a handoff, transfer the contract, exact revisions
and unresolved effects with Amp's transfer tools. Never copy an approval into a new thread.

### Ask Amp to create a delivery thread

```text
Create a delivery thread for [outcome] in [repository], using delivering, on
[an orb, or the named runner and checkout]. Carry this brief into its first
prompt: [brief]. It writes one contract, runs the readiness preflight on it, and
asks me for one approval at kickoff in that thread. If it needs unpushed work,
transfer and verify the exact files or commit first.
```

This uses Amp's own thread tools, not a `mission-control` launcher. Inside a mission, the
steering thread gives M and L items to child threads and XS and S items to subagents; children
create no threads, merge nothing into `dev`, and send stops to the steering thread, never to you.

### What happens after kickoff

1. **Kickoff (J1).** Grilling, design, rendered UX, a whiteboard defense, the readiness
   preflight, one contract, one kickoff brief, one dialog. Until you approve, the agent only
   reads, researches, drafts and reviews.
2. **Milestones (J2).** Items run in dependency order, each test-first with a fresh review. A
   milestone's gates are tests, CI, and two fresh reviews of the same head. When they pass, the
   milestone merges into `dev` and a checkpoint report goes out. The report asks nothing.
3. **Questions (J3).** A question with a safe default becomes a recorded assumption. New scope
   becomes a filed item in a later milestone, or a reason 1 stop.
4. **Liveness (J4).** The steering thread watches its children and answers, continues, restarts
   or re-plans any child that settles without a report.
5. **Close-out (J5).** A final report with evidence per criterion, every assumption, filed items
   and follow-ups, the effects performed, the gate ledger and the human tests. Your end review is
   a review, not a gate a merge waited on.

Common blockers and what to do:

| Observation | Response |
| --- | --- |
| Skill or plugin unavailable | Ask Amp to reload installed skills and plugins; installing one is a separate, approved action |
| `mission_start` refuses `requirements` or a v2 manifest | Those schemas are retired; pass `{ contract }` |
| Wrong workspace root | Open the dedicated Git worktree as the workspace before starting |
| "Mission already exists" | Use `mission_status` and resume; use a new thread for a new mission |
| Preflight fails | Fix the named check, or ask the owner if only they can (a 403 needs a plan or admin access); then run `mission_preflight` again |
| Kickoff dialog dismissed | Nothing is recorded; use the "Open kickoff approval" quick action |
| Pending merge or uncertain result | `mission_reconcile` first; never repeat the merge |
| A retired v1 or v2 record | Read the retired-schema message; start a contract mission in a new thread |

## Install and open the workspace

Copy the **whole** `plugins/mission-control/` directory into an authorized Amp plugin location.
Source integration does not publish it to Personal Plugins. Install `delivering`, `grilling` and
`crafting` separately as skills. Do not silently install missing dependencies.

Open the dedicated Git worktree root, then start with `mission_start({ contract })`. The tool
refuses any other input and refuses a workspace that is not the Git top level. It adds `/.amp/in/`
to the repository-local Git exclude, keeping existing rules, and stores the record at
`.amp/in/missions/<thread-hash>/state.json`. Do not commit these records.

## The contract

`mission_start({ contract })` takes a schema 3 contract with 16 top-level fields, in camelCase.
[`delivering`'s mission record](../skills/delivering/reference/mission-record.md) explains each.

```text
schemaVersion 3, missionId, repository "owner/name"
outcome, scope { in[], out[] }, spec, design { high, low }, ux[] (https links), defense
cases[]          { id, case, mitigation }             the closed list for adversarial review
openQuestions[]  { id, question, default }            each default is taken unless the owner changes it
effects[]        { id, effect, preAuthorized, source } every outside effect the mission needs
readiness[]      { id, check, evidence }               targets outside GitHub, reported by the agent
milestones[]     { id, title, exit[] }                 ordered; they merge in this order
items[]          id, title, milestone, size (XS|S|M|L), outcome, inScope[], outOfScope[],
                 dependsOn[], done[], automatedTest, humanTest, trace[]
brief            { markdown, url }                     the kickoff brief and its link
```

The plugin refuses an invalid contract and names the field, for example
`Refused (items[1].done)`. It refuses a missing field, size XL, an unknown dependency, a
dependency in a later milestone, a dependency cycle, a duplicate ID, an item in an unknown
milestone, a milestone with no item, an empty `done` list, and a `ux` or brief link that is not
https on `ampcode.com` or `github.com`. The `brief.markdown` must pass the `briefing-decisions`
rules that `lib/brief.ts` copies (headings, summary, technical record, sentence length, banned
codes, and no HTML or Markdown that hides words). The plugin cannot prove that the linked page
shows the same text; publish the page from the checked text.

**The approval digest.** Kickoff approval binds to a digest of 13 parts: `missionId`,
`repository`, `outcome`, `scope`, `spec`, `design`, `ux`, `defense`, `cases`, `openQuestions`,
`effects`, the brief, and each milestone as its ID, title, exit criteria and the sorted `done`
criteria of its items. So:

- a re-plan that keeps every criterion in the same milestone keeps the digest;
- filed items are outside the digest;
- any other change to a digest part voids the approval and the preflight (stop reason 1, then a
  new kickoff).

## Tools

| Tool | What it does |
| --- | --- |
| `mission_start({ contract })` | Validates the contract and starts the mission. Refuses a second mission in the same thread |
| `mission_status()` | The full status: digest, approval, preflight, pending approval, items, milestones with fingerprints, failed rounds and blockers, open stops, and the next action |
| `mission_preflight()` | Runs the GitHub readiness checks, binds the result to the current digest, and lists the contract's agent-reported `readiness` entries |
| `mission_approve()` | Opens the kickoff dialog. Refused before a passing preflight on the current contract |
| `mission_effect({ effectId })` or `({ effect, why })` | Call right before an outside effect. A pre-authorized effect is recorded with no dialog; any other effect opens the effect dialog |
| `mission_update({ action })` | The 12 public actions below |
| `mission_merge({ milestoneId })` | Checks every merge blocker and GitHub's merge readiness, saves the pending state, then requests one exact-head squash merge into `dev`. Opens no dialog |
| `mission_reconcile({ milestoneId })` | Reads the PR after a restart or an uncertain merge. Records the merge only for an exact-head merge into `dev`. Never repeats the merge |
| `mission_recover({ milestoneId })` | After a settled, unqueued attempt: reads GitHub twice, starts a new generation, voids the milestone's reviews and evidence, and returns it to review. Sends no merge and opens no dialog |
| `mission_report({ kind, milestoneId? })` | `checkpoint` for a merged milestone (`milestoneId` defaults to the latest merged), or `close-out` once every milestone is merged (no `milestoneId`) |

The readiness preflight checks six things and names each failure:

1. the repository is visible, with push permission;
2. `dev` exists;
3. branch protection is readable; a 403 reads "protection unreadable: needs a plan that supports
   it, or admin access";
4. protection is enforced: administrators included, strict checks, PR reviews configured, no
   bypass allowances;
5. every required check is pinned to an app;
6. the latest `dev` commit has every required check completed with success.

A check whose prerequisite failed is reported as failed and not checked.

### `mission_update` actions

Each action is `{ type, ...fields }`. Read fingerprints from `mission_status`. The internal
actions (`approval-pending`, `approve`, `preflight`, `effect`, `merge-requested`, `merged`,
`recover`) come only from the plugin's own tools and dialogs; `mission_update` refuses them.

| Action | Fields | Rules |
| --- | --- | --- |
| `amend` | `contract`, `reason` | See [Amend](#amend) below |
| `replan` | `itemId`, `into[]` | The new items hold exactly the original `done` criteria, verbatim, in the same milestone; put extra checks in `automatedTest`. Refused for a done item (reopen it first with a "replanned" disposition), and while a gate of that milestone has failed rounds, until a "replanned" disposition on each failing gate. Dependents and open stops move to the new items |
| `file` | `item`, or `followUp { id, text }` | An item goes into a milestone after the earliest unmerged one, so a current candidate is never voided. A follow-up needs an ID and is allowed only when the earliest unmerged milestone is the last one; it is listed in the close-out. Neither needs approval |
| `delegate` | `itemId`, `executor { kind, id }` | `kind` is `thread` (a `T-…` thread ID) or `subagent` |
| `item-done` | `itemId`, `evidence[{ criterion, result }]`, `review { reviewer, record }` | One result per `done` criterion. The reviewer is not the mission thread. When the milestone already has a candidate, it starts a new generation and voids the milestone's reviews and evidence |
| `candidate` | `milestoneId`, `pr`, `head`, `base` | Needs every item of the milestone done and every earlier milestone merged; full Git SHAs. A new head voids reviews and evidence; failed-round counters survive |
| `review` | `milestoneId`, `gate` (1 or 2), `fingerprint`, `passed`, `reviewer`, `record` | Bound to the current fingerprint. The reviewer is not the mission thread. Gate 2 needs a passing gate 1 on the same fingerprint and a different reviewer. After 3 failed rounds at a gate, a further `passed: false` is refused until a "replanned" disposition. A pass does not reset the count |
| `disposition` | `milestoneId`, `gate`, `outcome`, `record`, `itemIds?` | `fixed` names no items. `replanned` names done or delegated items of that milestone: they go back to planned, lose their evidence, the milestone's reviews and evidence are voided, and that gate's count resets. `filed` names filed item or follow-up IDs. Only `replanned` resets a count |
| `evidence` | `milestoneId`, `fingerprint`, `results[{ criterion, result }]`, `humanTest` | One result per `done` criterion of the milestone's items (filed items included) and per exit criterion |
| `assume` | `question`, `assumption`, `why` | Shown in the next checkpoint report |
| `stop` | `reason`, `question`, `options[]`, `recommendation`, `blocks[]` | `reason` is 1 to 5 or the exact text; anything else is refused and the refusal lists the five. Reason 2 is refused and redirected to `mission_effect`. `blocks[]` names at least one known item or milestone |
| `resume` | `stopId`, `answer`, `source` | Closes that stop; the answer joins the record |

### Amend

`amend` replaces the contract and records the reason. The rules:

- **Approval.** With the same digest, approval stays. Only item fields outside the baseline may
  then change: `title`, `inScope`, `outOfScope`, `size`, `dependsOn`, `automatedTest`,
  `humanTest` and `trace`. Item IDs, outcomes, milestones and `done` criteria may not. A change
  only to `readiness` keeps the approval but voids the preflight, so run `mission_preflight`
  again. A new digest voids approval, preflight and any pending approval.
- **Progress.** An unchanged item (same ID, identical fields) keeps its progress; a changed one
  returns to planned. Filed items and follow-ups live in the record, so they survive.
- **Refused** while a merge is pending; when it changes a merged milestone or its items; when an
  open stop names an item or milestone that the amend removes (resume the stop first); and when
  it would change the ID, items, outcomes or criteria of a milestone with failed review rounds,
  or move that milestone or a candidate milestone from the earliest unmerged place. Record a
  "replanned" disposition first to change a failed milestone.

## The kickoff and effect dialogs

**The kickoff dialog** is titled "Approve the mission contract". It has:

- a link field, "Open the contract brief";
- one checkbox per open-question default and per pre-authorized effect, all starting unticked;
- an optional "Changes" text field;
- a "Submit" button. There is no typed word and no secret field.

The answer is read in this order, and the first case that applies decides:

| Case | What the agent gets |
| --- | --- |
| 1. The dialog is dismissed or fails | Nothing recorded; the reopen quick action appears |
| 2. No responder is reported | "This client could not confirm who answered; open the approval in the Amp web app"; the quick action appears |
| 3. The responder is not the thread owner | Nothing recorded; the quick action appears |
| 4. Changes holds text | That text, as the owner's answer. Not approved |
| 5. A box is unticked and Changes is empty | "Not approved: tick every box, or write what to change." |

Kickoff is approved only when every box is ticked, Changes is empty, the responder is the
signed-in owner, and the contract is unchanged since the dialog opened. A contract that changed
while the dialog was open is stale, and nothing is recorded.

**The effect dialog** is titled "Approve an outside effect" and has the same pattern with one
checkbox: a contract effect that is not pre-authorized, or an effect that is not in the contract
with its reason. An approval is for that one effect, once. It records the effect as performed and
never changes the contract.

**Reopen.** Opening either dialog first records a pending approval. When the dialog ends in case
1, 2 or 3, the quick action "Open kickoff approval" or "Open effect approval" appears above the
composer in the Amp web app. It runs the command **Reopen mission approval**
(`mission-reopen-approval`, category Mission control), which reopens the dialog for the pending
entry and records the answer. Changes text given there is posted to the thread as the owner's
dialog answer. While an approval is pending, `agent.start` reminds the agent, which tells you and
reopens it only when you ask.

**Preview.** To see the real dialogs without a mission, run the command **Preview approval
dialogs** (category Mission control) from the preview-only project plugin
[`.amp/plugins/mission-control-preview.ts`](../.amp/plugins/mission-control-preview.ts). It shows
the kickoff dialog for the contract fixture (9 boxes: 6 defaults and 3 effects), then an effect
dialog for a sample effect, and reports what each answer would do. It records nothing.

**Who may answer.** Only the thread owner's answer counts; Amp reports who answered. Never enter
a password, key or other secret in a dialog. These records are workflow records, not externally
verifiable authentication receipts.

## Effects

- An effect listed in the contract as pre-authorized is recorded with `mission_effect({ effectId })`
  and no dialog, and only after kickoff is approved on the current contract.
- A listed effect that is not pre-authorized, or an effect that is not in the contract
  (`{ effect, why }`), opens the effect dialog. Perform it only after the owner approves it.
- Milestone merges into `dev` happen through `mission_merge`, not `mission_effect`. The contract
  should still list them as a pre-authorized effect so the brief shows them.

## Milestones, reviews and merges

**Fingerprint.** Reviews and evidence bind to a fingerprint of the approval digest, the milestone,
its candidate and its generation. A new candidate head, a recovery, a "replanned" disposition, or
an item done after the candidate makes the old reviews and evidence lapse.

**Merge blockers.** `mission_merge` refuses and names each missing one:

1. kickoff approved on the current digest;
2. the milestone is not blocked by an open stop naming it or one of its items;
3. all its items done;
4. every earlier milestone merged;
5. a current candidate;
6. gate 1 and gate 2 passed on the current fingerprint;
7. evidence recorded on that fingerprint.

Then GitHub's merge readiness is checked as below. There is no risk field and no owner merge
gate at any risk level; high risk means independent reviewers and the full case list.

**The review cap.** A gate allows 3 failed rounds, and the count survives new heads. Then the
disposition policy decides, never the owner: a Blocker or Major inside the case list or the
milestone's criteria is fixed, or its items are reopened and re-planned ("replanned"); a finding
outside them is filed ("filed") and does not fail the review; a Nit never fails a review. If the
re-planned items still cannot meet the exit criteria, that is stop reason 5.

## Hooks and the nudge

- `session.start` shows the compact status as a notification.
- `agent.start` adds the compact status and the next action to the agent's context, plus a
  reminder when an approval is pending.
- `agent.end` sends "continue" (at most 3 in a row) only when kickoff is approved on the current
  contract, no item is delegated, and at least one unmerged milestone is not blocked by a stop.
  It sends nothing while kickoff is pending, while any item is delegated, when every unmerged
  milestone is blocked, or once every milestone is merged.
- The hooks never open a dialog. The steering thread, not the plugin, watches child threads.

## Reports

`mission_report` writes reports that ask nothing; post them where the contract says. Their
sections come from `lib/contract-text.json` (`reportSections`):

- **Checkpoint:** Merged, Done, Assumptions taken, Filed for later, Try it yourself, Next.
- **Close-out:** Outcome, Criteria and evidence, Assumptions, Filed items and follow-ups, Effects
  performed, Gate ledger, Human tests.

## GitHub prerequisites and the workflow boundary

Use the GitHub authentication `gh` already has; do not create or copy credentials into mission
records. The account needs to read PRs, branch protection and check runs, and to request the
merge.

- Protect `dev`, require PRs, enable strict up-to-date required checks and administrator
  enforcement, and leave bypass allowances empty.
- Pin every required check to its source App in branch protection (GitHub Actions is App ID
  `15368`). The plugin reads these requirements from GitHub, not from a local setting.
- Each required check must have completed successfully on the candidate head, and the PR must
  still target the recorded `dev` base and head; the merge preflight reads it twice.

The current adapter supports REST branch protection, not rulesets-only repositories, merge
queues, legacy commit-status contexts or more than 100 check runs. It refuses unpinned, skipped
or neutral checks, bypass allowances, missing administrator enforcement, and head or base motion
during the merge preflight. GitHub's strict checks and the exact-head merge condition govern any
race after the last read.

Mission merges do **not** enable GitHub's persistent auto-merge. The plugin requests one
immediate merge with `--match-head-commit`; if the remote gates no longer pass, the merge fails.
Never add `--auto` as a shortcut.

You accept local workflow enforcement, not protection from a hostile shell. An unrestricted
executor can edit local records or call GitHub outside these tools, and GitHub does not
authenticate the local approvals or reviews. Do not bypass the workflow, weaken protection or use
administrator overrides. The plugin does not configure CI or protection.

## Retired v1 and v2 records

The v1 single-PR flow and the v2 shadow flow are retired. Their tools are gone, and
`mission_start` takes only `{ contract }`. When a thread still holds a v1 or v2 record, every
tool and hook reports a "Retired schema" message and leaves the file's bytes unchanged. For a v1
record that requested a merge, check its pull request on GitHub first. To continue the work,
start a contract mission in a new thread.

## Recovery and limits

Atomic replacement, file fsync, an exclusive lock and a stale-copy check protect local updates.
The record is rebuilt by replaying its events on every load, and a record whose saved state
differs from its replay is refused: preserve it and investigate. This is not a distributed
transaction or a tamper-resistant audit log. A leftover lock after a crash blocks writes on
purpose: check that no writer runs, keep the evidence, and remove only the stale lock. Never
delete the record to get a clean state.

The pending merge state is saved **before** the merge request. A timeout, cancellation or restart
can leave the outcome unknown. Run `mission_reconcile` first; never send the merge again. Use
`mission_recover` only when the attempt has settled: it needs an open, unmerged, unqueued PR into
`dev` on two reads, refuses while a request may be in flight, and sends no merge. It does not
prove that another executor has stopped.

Session start shows the saved state; it does not replay interrupted dialogs. The nudge does not
wake an offline runner or promise unattended completion. Use Amp's exact-head CI and PR event
subscriptions for follow-up; this plugin provisions no daemon or subscription.

## Verification

Run `make check`. The mission tests cover the contract validation, the digest, every action rule,
the dialogs and their order rule, the reopen command, the hooks, the reports, the retired
records, and GitHub readiness and merges through a controlled transport. The repository check
also loads every plugin, including the preview plugin, through the Amp CLI. Controlled GitHub and
dialog adapters are not a live GitHub integration or a multiplayer identity test.

Promotion to `rolling` or `main`, deployment, access changes and Personal publication are
outside effects with their own approvals, unless the contract pre-authorizes them.

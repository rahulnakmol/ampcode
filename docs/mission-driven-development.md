# Mission-driven development

A mission starts with a customer outcome and ends with evidence about whether the delivered
software achieves it. It is useful for a substantial feature or use case, not a ceremony for
every edit. Precision means explicit expectations, accountable ownership and reproducible
evidence, not a guarantee of perfect software.

A mission has **one approval**. You approve one contract at kickoff. After that the agent works
milestone by milestone on its own, each milestone merges into `dev` at a checkpoint, and it asks
you again only for one of five stop reasons. Missions have no budgets and use no agent teams.

**Start here if you want software built.** For enterprise functional discovery, operating models
and client-approved business specifications, start with [Blueprinting](blueprinting.md). Its
functional baseline is input to delivery, not approval of a contract. For individual skill
selection, see [Using the skills](using-skills.md). For tools, rules and limits, see the
[mission-control reference](mission-control.md).

## Start with one message

Open the target project in Amp and replace the bracketed details:

```text
Use delivering to start a mission for [customer outcome] in [repository].
Use grilling to make the criteria concrete, each with a finite set of cases,
and crafting to render every changed state. Write one contract with
milestones, items, open questions with defaults, and every outside effect
marked pre-authorized or not. Run the readiness preflight on it, then ask me
for one approval at kickoff. Pre-authorize the milestone merges into dev and
pushing mission branches. These constraints must hold: [constraints].
```

You do not need to know tool names. "Use delivering", "deliver this feature", "deliver this
approved brief" and "resume this mission" are useful triggers. Naming the skill is clearer than
assuming the word "mission" starts a special command; there is no `/mission` slash command. For
more starting points, see the [kickoff prompts](mission-control.md#ways-to-kick-off-a-mission).

## The five journeys

| Journey | What happens | What good looks like |
| --- | --- | --- |
| **J1 Kickoff** | Grilling, design, rendered UX, a whiteboard defense, a readiness preflight of the repository, CI, credentials and every outside target, then one contract and one kickoff brief | One dialog (or one recorded reply without the plugin). You tick each default and each pre-authorized effect. An effect you did not pre-authorize gets its own effect dialog later, when the mission needs it |
| **J2 Milestones** | Items run in dependency order, each test-first with a fresh review. A milestone's gates are tests, CI and two fresh reviews of the same head against its criteria and the closed case list | Each milestone squash-merges into `dev` when its gates pass, followed by a checkpoint report that asks nothing |
| **J3 Questions** | A question with a safe default becomes a recorded assumption. New scope becomes an item in a later milestone | Assumptions and filed items appear in the next checkpoint report; only the five stop reasons reach you |
| **J4 Liveness** | The steering thread watches its child threads and subagents | A child that settles without a report is answered, told to continue, restarted or re-planned, never left idle |
| **J5 Close-out** | A final report with evidence per criterion, every assumption, filed items and follow-ups, the effects performed, the gate ledger and the human tests | Your end review is a review, not a gate a merge waited on |

The readiness preflight runs before the kickoff ask, so prerequisites such as branch protection,
CI or a token scope surface before the build, not halfway through it. Kickoff is refused until
the preflight passes on the current contract.

## The five stop reasons

After kickoff, the agent stops and asks you only when:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

Each stop is one question with options and a recommendation. It blocks only the items and
milestones it names; other work continues. Everything else is a recorded assumption. You can stop
or pause the mission at any time by replying in the mission thread.

## Example: document recovery, not "add autosave"

**Weak ask:** "Add reliable autosave."

**Concrete outcome:** "A desktop editor user can recover the last acknowledged edit after the
process terminates unexpectedly, without overwriting a newer saved file."

A useful mission asks what "acknowledged" means, what data is durable, whether recovery needs
consent, how conflicting edits appear, and what happens when storage is full. Each criterion
lists its cases, for example "recovery after a kill, after a power loss, and with a newer saved
file". The design covers recovery, discard, permission errors and keyboard navigation. The
harness interrupts the actual persistence path and checks recovered content; it does not mock a
successful save. Reviews check data loss and concurrency. The final report shows the recovered
edit and the protected newer file, and names any untested operating systems. This is an
illustration, not a claim that the kit implements or has tested a document editor.

## Choose the right starting point

| Your situation | Say this | Expected first step |
| --- | --- | --- |
| New idea | "Use grilling to make [idea] concrete; I want to deliver it afterward." | Clarify the customer need, not start coding |
| Known requirement | "Use delivering for [requirement]; success means [criteria]. Write one contract, run the readiness preflight and ask me for one approval at kickoff." | Assess current code and gaps, then draft the contract |
| Approved brief | "Deliver [brief, path or thread]; turn it into one contract, run the readiness preflight and ask me for one approval at kickoff." | Read the actual brief and check drift |
| Partial implementation | "Adopt this work into a delivery mission; preserve my changes. Write one contract, run the readiness preflight and ask me for one approval at kickoff." | Inventory ownership and evidence without inventing past gates |
| Design only | "Write the contract and run the readiness preflight; do not ask for the one approval yet." | The contract and its preflight, with no build |
| Interrupted work | "Resume this mission from its contract, preflight and one kickoff approval; reconcile state before retrying effects." | Read the record, worktree and remote state |
| Need another executor | "Create a delivery thread on [runner or orb] for [brief]; it writes one contract, runs the readiness preflight and asks me for one approval at kickoff." | Check access and transfer exact work if needed |

## Know which component does what

- **Grilling** turns the ask into criteria with finite case lists.
- **Crafting** designs and renders the human and agent interactions, including failure states.
- **Delivering** runs the contract loop and owns the outcome.
- **Missioning** holds the charter, the gate ledger and the decision trail.
- **Mission-control** holds the contract, binds the kickoff approval to it, runs the preflight,
  checks every merge blocker and writes the reports.
- **Native Amp capabilities** supply the tools, subagents, threads and execution.
- **GitHub required CI and branch protection** independently constrain every merge into `dev`.

One steering thread stays the integration owner. M and L items run in child threads and XS and S
items in subagents; children create no threads, merge nothing into `dev`, and send stops to the
steering thread. Parallel outputs still need combined validation.

## Your decisions and a good final handoff

You decide the outcome, the contract, each open question's default and which outside effects to
pre-authorize, all in the one kickoff approval. The kickoff dialog links the brief; you tick each
box, or write what to change. Never type a secret into a dialog. Milestone merges into `dev` need
no further answer from you at any risk level. Promotion to `rolling` or `main`, deployment and
publication happen only if the contract pre-authorizes them or you approve each one once in the
effect dialog (without the plugin, that question is stop reason 2).

A good close-out answers:

1. Which criteria were met, and with what evidence?
2. Which assumptions were taken, and why?
3. What did the reviews find, and how was each finding fixed, re-planned or filed?
4. Which outside effects were performed?
5. Is the work merged into `dev`, released, deployed or installed?
6. How can you try the result yourself?

"Tests passed" alone is not that handoff. Neither is a requested merge, a screenshot of
behaviour that was not exercised, or an agent's unsupported assurance. Review gates improve
dependability; they do not promise perfection, hostile-shell isolation, or progress when tools or
permissions are missing.

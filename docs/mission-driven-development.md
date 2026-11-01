# Mission-driven development

A mission starts with a customer outcome and ends with evidence about whether the
delivered software achieves it. It is useful for a substantial feature or use case,
not a ceremony for every edit. Precision means explicit expectations, accountable
ownership and reproducible evidence—not a guarantee of perfect software.

**Start here if you want something built.** For individual skill selection, see
[Using the skills](using-skills.md). For tool schemas, storage and protection, see
the [mission-control reference](mission-control.md).

## Start with one message

Open the target project in Amp and replace the bracketed details:

```text
Use delivering to start a mission for [customer outcome] in [repository].
Use grilling to make expectations concrete and crafting for relevant user/agent
journeys. Present the spec, technical/UX design and plan for my acknowledgment;
then defend the design before building. Use outcome-driven TDD, real journeys,
two review gates and a post-delivery adversarial/learning pass.
Use v1 for protected dev integration. My delivery target is [dev only / release],
my budget is [limit], and these constraints must hold: [constraints].
Ask separately before any unapproved release, deployment or Personal publication.
```

You do not need to know tool names. “Use delivering,” “deliver this feature,”
“deliver this approved brief” and “resume this mission” are useful natural-language
triggers. Explicitly naming the skill is clearer than assuming the word “mission”
starts a special command. There is no custom `/mission` slash command in this kit.

## Four stages, with visible entry and exit gates

| Stage | What you provide / entry | What Amp does | What good looks like / exit |
| --- | --- | --- | --- |
| **1. Expectations** | Problem/use case, audience, repository and known constraints | Grilling: inspect current state, research facts, clarify decisions; crafting: design relevant journeys/states | A concrete spec, technical/UX design, non-goals, measurable criteria, verification plan and budget. You acknowledge the exact package |
| **2. Whiteboard defense** | Acknowledged design package | Explain the outcome, data flow, alternatives, invariants, threats and recovery; challenge consequential assumptions | The implementer can explain why the design meets the criteria. Blocking gaps are resolved before build; material changes return to acknowledgment |
| **3. Build and delivery** | Defended design and a bounded slice | Establish behavioral failure, implement minimally, run real journeys, review, repair, revalidate, review again and assess customer value | Evidence supports the slice; required CI and protection pass; applicable exact-candidate acknowledgment is recorded; integration is remotely confirmed |
| **4. Adversarial review and learning** | Integrated result and retained expectations/evidence | Examine the assembled result with fresh context, investigate escaped defects, preserve lessons and corrective work | Clear findings/dispositions and remaining uncertainty. No claim of closure from partial delivery; no automatic publishing of shared-skill changes |

Design acknowledgment is not final-candidate merge acknowledgment. Whiteboard defense
does not replace either build review. Stage 4 does not excuse knowingly shipping a
stage-3 blocker. A changed requirement reopens the affected decisions, rather than
quietly changing what “success” means.

The Elephant-Goldfish adaptation combines retained context with a fresh reader who
must understand the brief from its actual contents. Missing context is repaired in
the brief, not supplied as private coaching. It is a review technique, not an extra
agent runtime or proof that every defect was found.

## Example: document recovery, not “add autosave”

**Weak ask:** “Add reliable autosave.”

**Concrete outcome:** “A desktop editor user can recover the last acknowledged edit
after the process terminates unexpectedly, without overwriting a newer saved file.”

A useful mission asks what “acknowledged” means, what data is durable, whether recovery
needs consent, how conflicting edits appear, and what happens when storage is full.
The design covers recovery, discard, permission errors and keyboard navigation.
The harness interrupts the actual persistence path and checks recovered content;
it does not merely mock a successful save. Reviews inspect data loss and concurrency.
The final demonstration shows the recovered edit and the protected newer file, and
states any untested operating systems. This is an illustrative outcome, not a claim
that the kit implements or has tested a document editor.

## Choose the right starting point

| Your situation | Say this | Expected first step |
| --- | --- | --- |
| New idea | “Use grilling to make [idea] concrete; I want to deliver it afterward.” | Clarify the customer need, not start coding |
| Known requirement | “Use delivering for [requirement]; success means [criteria].” | Assess current code and gaps, then design acknowledgment |
| Approved brief | “Deliver [brief/path/thread]; preserve the approved expectations.” | Read the actual agreement and check drift |
| Partial implementation | “Adopt this work into a delivery mission; preserve my changes.” | Inventory ownership and evidence without fabricating past gates |
| Design only | “Use grilling and crafting; stop at the reviewed design.” | Produce the package, not implement |
| Interrupted work | “Resume this mission; reconcile state before retrying effects.” | Read checkpoints, worktree and remote state |
| Need another executor | “Create a delivery thread on [runner/orb] for [brief].” | Verify access and transfer exact work if needed |
| Explore traceability | “Start a v2 shadow mission with stable criteria and per-PR units.” | Prepare a complete manifest; disclose disabled merge/closure qualification |

For complete copyable variants, including budgets, migration and subagent requests,
see [kickoff prompts](mission-control.md#ways-to-kick-off-a-mission).

## Know which component does what

- **Grilling** turns the ask into concrete expectations.
- **Crafting** designs applicable human and agent interactions, including failure states.
- **Delivering** guides the overall workflow and owns the outcome.
- **Mission-control** persists local records and checks supported workflow transitions.
- **Native Amp capabilities** supply tools, subagents, threads, execution and available
  research/review specialists. The kit complements them rather than replacing them.
- **GitHub required CI and branch protection** independently constrain integration.

Ask for subagents when useful, but expect one integration owner. Independent investigations
and separate file scopes can run concurrently; dependent work must wait for its inputs.
Consequential changes receive independent review. Parallel outputs still need combined
validation. The released foundation has **no automatic dependency scheduler**.

## V1 delivers; v2 records shadow traceability

| Choice | Use it for | Do not assume |
| --- | --- | --- |
| **V1, default** | Owner-approved local workflow and protected exact-head `dev` integration | Local prose is authenticated execution, or plugin installation configures protection |
| **V2, explicit opt-in** | Stable criteria, retained designs, per-PR attempts, finding/evidence lineage and post-delivery reports | That v2 can request remote merges or mark qualified closure |

V2 always exposes `remote-verification-unqualified`. Do not erase the record, downgrade
or bypass tools to remove that blocker. Migration is explicit, preserves legacy history,
and disables v1 merge capability for that record. This is a foundation for traceability,
not activated trusted enforcement or a replacement for CI.

## Your decisions and a good final handoff

You decide the outcome, consequential tradeoffs, exact design, work budget and delivery
boundary. Native dialogs require **ACKNOWLEDGE**, never a secret. V1 high-risk candidates
and ask-before-merge mode require final acknowledgment; low/medium automatic integration
still needs all required gates. Permission to build is not permission to release.

A good handoff answers:

1. Which customer outcomes and criteria were met, and with what observable evidence?
2. Which failures, security boundaries and recovery cases were exercised?
3. What did both reviews find, and how were the findings resolved?
4. What remains missing, blocked, risky or unverified?
5. Is the work local, pushed, integrated into `dev`, released, deployed or installed?
6. How can you try the result, and what corrective work or learning follows?

“Tests passed” alone is not that handoff. Neither is a requested merge, a screenshot
of unexecuted behavior, or an agent's unsupported assurance. Review gates improve
dependability; they do not promise perfection, hostile-shell isolation, or unlimited
autonomous progress when tools, permissions or budget are missing.

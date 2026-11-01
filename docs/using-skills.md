# Using the skills in Amp

Choose a skill by the result you need. You can name it directly in a normal Amp
message: **“Use grilling…”**, **“Use crafting…”**, **“Use delivering…”**, or
**“Distill this video…”**. The examples below are prompts to paste into chat, not
terminal commands. Natural-language triggers help Amp select an installed skill;
they are not exact-match keywords or a guarantee that a skill was loaded. Name
the skill explicitly when you want it, and ask Amp which skill it is using if unclear.

## Pick the result, then the skill

| What you need | Skill | Typical trigger words | What you receive |
| --- | --- | --- | --- |
| Make an idea or requirement concrete | **grilling** | grill me, clarify requirements, pressure-test, pre-mortem, spec this out, write a PRD | Confirmed brief, acceptance criteria, risks, plan and handoff prompt |
| Design how a person or agent experiences something | **crafting** | design, redesign, craft, prototype, mock up, polish, critique, accessibility audit, user flow | Journeys, states, design direction, mockups/specification and critique |
| Deliver a substantial software outcome | **delivering** | use delivering, deliver this feature, execute this approved brief, resume this mission | Implemented and verified slices, two reviews, evidence and authorized integration |
| Turn public YouTube research into an original article | **distill** | distill this video, distill these videos, write a whitepaper from these videos | Original evidence-backed article, research brief and supported offline package |

These are the four skills maintained in this repository. Archi, Darci and Opsci are
[advisory modes/tools](advisory-team.md); Swift, Weave and Prime are execution modes,
not skills. Selecting a mode does not select a workflow or start a mission.

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

**Use when:** you want a major feature, use case or concrete requirement implemented,
or need to resume a multi-step delivery. It brings grilling and relevant crafting into
the work; you do not need to manually launch every skill in a fixed sequence.

**Say:** “Use delivering for this feature,” “Deliver this approved brief,” “Execute
this implementation plan,” or “Resume the mission.”

```text
Use delivering to implement the approved document-recovery brief in [repository].
Check the approved design against the current code, resolve drift, and complete
whiteboard defense before build. Use outcome-driven TDD, real interruption/recovery
journeys and two review gates. Commit and open a PR to dev; integrate only after
required gates pass. Do not release or deploy yet.
```

**Give Amp:** the outcome or brief, repository, relevant design/decision references,
constraints, delivery destination and budget. Say whether existing work is uncommitted
or only available on a particular runner.

**A good result looks like:** criteria connected to failing-then-passing behavioral
evidence, small coherent changes, real journeys, independent review for consequential
changes, repaired findings and a second review. The final account distinguishes local
verification, dev integration, release and installation. It explains whether customers
can now do the intended job and what remains unverified.

**Not good:** “all tests green” with no demonstrated customer outcome, a merge request
called a completed merge, fabricated evidence, or a release inferred from permission
to code. Do not use a full mission for a typo, standalone review or release-only task.

**Next:** follow the [Mission-driven development guide](mission-driven-development.md)
for the four stages, owner decisions and kickoff variations.
[Skill instructions](../skills/delivering/SKILL.md).

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
and unqualified. See [current capability limits](../README.md#distill).

**Next:** review the argument and evidence before publication or archival.
[Skill instructions](../skills/distill/SKILL.md).

## Combine skills without unnecessary ceremony

- **“I have an idea.”** Grilling makes it concrete; crafting designs relevant
  interactions; delivering owns implementation when you authorize it.
- **“The requirement is clear, but the flow is confusing.”** Start with crafting;
  clarify only missing decisions instead of restarting a full interview.
- **“The brief and design are already approved.”** Start with delivering; reuse
  valid approval and check drift rather than repeat every earlier discussion.
- **“These videos may inform our product decision.”** Distill can supply research;
  its article does not itself approve a design or start a software mission.
- **“Fix this typo.”** Use a normal Amp request. A mission is disproportionate.

Skills must be installed to be loaded. Ask Amp to check availability and reload existing
Personal Skills if needed. Installing a missing skill is a separate action with a
destination; cloning this GitHub repository alone is not Personal installation.
Skill instructions guide the agent; they do not create permissions, a scheduler,
guaranteed spend limits or a security boundary.

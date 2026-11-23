---
name: missioning
description: "Conducts a mission of any kind with one charter, one gate ledger and one decision trail: outcome, decision owner, approvers, success criteria, Definition of Done, open questions with defaults, pre-authorized effects and authority agreed in one kickoff approval; playbook steps grouped into milestones and work items; then questions only for the five stop reasons, and no budgets; a checked plain-English brief and a fresh-reader review before every human sign-off; approvals recorded as ledger rows, never inferred from chat; and a close-out audit. Ships eight playbooks (ERP and AI transformation, product delivery operations, AI-native software delivery, campaigns and research, UX and UI design, code and security review, infrastructure and DevSecOps, product and SaaS assessment) and a host guide for Amp, Claude Code, Copilot in VS Code and the Copilot app. Use when asked to start, run, resume or close a mission, write a mission charter or contract, record or audit approvals, or pick the playbook for a kind of work."
---

# Missioning

A mission is a piece of work with a clear outcome, run by an agent after one approval at kickoff.
This skill is the thin conductor: it decides what happens next and records it; other skills do the
work, the same on every host ([reference/hosts.md](reference/hosts.md) names each host's tools).

It starts no agent teams, swarms or multi-agent Projects; work items run as the conductor says.
It never holds authority the owner did not grant, and one integration owner stays accountable. On
hosts without an owner-only dialog its rules are not a security boundary.

## 1. Write the charter

Draft the charter, the mission's contract, from the owner's ask with
[reference/charter.md](reference/charter.md). Find facts first. It names:

- **Outcome**, **Decision owner** and **Approvers** (client and outside approvers included);
- **Success criteria** and **Definition of Done**, each with a finite set of cases;
- **Open questions**, each with the default the agent takes unless the owner changes it;
- **Pre-authorized effects**: each outside effect approved at kickoff, with its source;
- **Authority**: what the agent **may do without asking**, what it must **always ask** (outside
  effects that are not pre-authorized), and **stop and ask when**: the five stop reasons only;
- **Playbook** and **Host**.

There is no budget. Until kickoff is approved, the agent only reads, researches, drafts, reviews,
records and publishes the brief for the owner. It takes no effects action.

## 2. Kickoff: one approval for the whole baseline

The baseline is the charter, the success criteria, the first design or plan, and the milestones.
First run a readiness preflight on every outside target the mission needs (repository, CI,
credentials, trackers, deploy targets); turn each gap into an open question or an effect. The
owner then approves once, from one brief showing the baseline, every open question with its
default and every effect. Reviewers grade against these criteria, not the author's.

## 3. Run the playbook

Load only the chosen playbook:

| Mission | Playbook | Conductor it calls |
| --- | --- | --- |
| ERP and Agile AI transformation | [transformation](reference/missions/transformation.md) | `blueprinting` |
| Product design and delivery operations | [product-operations](reference/missions/product-operations.md) | `planning` |
| AI-native software delivery | [software-delivery](reference/missions/software-delivery.md) | `delivering` |
| Campaigns, communications and research | [campaigns-and-research](reference/missions/campaigns-and-research.md) | `planning` |
| UX and UI design | [experience-design](reference/missions/experience-design.md) | `crafting` |
| Code and security review | [security-review](reference/missions/security-review.md) | this skill |
| Infrastructure and DevSecOps | [infrastructure](reference/missions/infrastructure.md) | this skill |
| Product and SaaS assessment | [product-assessment](reference/missions/product-assessment.md) | this skill |

- Copy the playbook's steps into the todo list with their numbers, which briefs and the charter
  cite. Mark a step you will not do `skip: <reason>`; never delete it. A step holding stand-in
  content stays open, marked `draft: <reason>`.
- The playbook's **Milestones** line groups the steps after kickoff into milestones, each ending
  with a checkpoint report that asks nothing. Each step is one or more work items with an outcome
  and a definition of done.
- Load each skill only when its step starts. When a playbook's conductor runs the work, follow
  that conductor; this skill keeps only the charter, ledger and close-out.
- Some skills are **planned**, not built. Check which are installed. For a missing one, use the
  playbook's `Fallback:` (or the step's own text) and label its output "manual, no skill", or
  mark the step `skip:`. Never report that a planned skill ran; a host skill with the same name
  but another purpose is not the planned skill.

## 4. Ask only at kickoff and for the five stop reasons

Settle facts by lookup or a bounded experiment. Choices of priority, taste, risk or money go into
the kickoff as open questions with a recommended default. After kickoff, take the default or a
safe, reversible choice, record it as an assumption and report it at the next checkpoint. Stop
and ask only when one of these holds, with one question, options and a recommendation:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

A stop blocks only the items and milestones it names; other work continues. Use the host's
question tool; a message can go unseen. When it is off (an autopilot mode), the gate stays
pending. When the owner says stop or pause, finish the current step and report.

## 5. Keep the gate ledger and decision trail

The mission file holds both; each gate is one ledger row. Every playbook uses this pattern:

| Gate | The owner decides | The agent does |
| --- | --- | --- |
| Kickoff | The whole baseline, once: charter, criteria, design or plan, defaults, effects | Drafts it, finds facts first, runs the preflight, writes the brief |
| Effects | Each outside effect the charter does not pre-authorize, when it arises | Shows the exact plan, applies only that plan, reads the result back |
| Stops | One question for one of the five stop reasons | Keeps working on everything the stop does not block |
| Outcome | Reviews the close-out; the review blocks no merge | Evidence, trace, gaps, lessons |

- **Approval is a recorded row.** A human gate passes only with a named decider who is the
  decision owner or an approver, a source (`dialog` or `question` for the decision owner only,
  `tracker` or `written` for anyone), the brief and its review. An answer counts only when it
  answers the exact gate question, by choosing an offered option or naming the decision. "Looks
  good", an earlier conversation or silence is never an approval. Write the row after the answer.
- **Effects.** A pre-authorized effect (a release, publish, outside send or apply that the
  charter lists) is an `agent` row whose Evidence reads `pre-authorized: <source>`; never ask for
  it again. Any other outside effect is a human Effects gate on the exact plan (stop reason 2).
  Merges into the integration branch under the conductor's gates are agent rows at every risk
  level: high risk means independent reviewers and the full case list, not an owner gate.
- **Stakeholder sign-offs** a conductor requires from people outside the agent loop (`planning`,
  `blueprinting`'s client authorities, a risk owner) stay human rows.
- **Decision trail.** One row per consequential decision or assumption: date, decision, why,
  evidence, decider. Routine writes the charter grants go here too. Never rewrite earlier rows.
- **Check it.** Run `python3 scripts/ledger_check.py <mission.md>` after every ledger change and
  before reporting a gate. It proves the record is complete; it cannot prove that a person really
  answered. On Amp, `mission-control`'s kickoff dialog is the stronger evidence; cite it in the row.

## 6. Prepare every human gate

1. Write the brief with `briefing-decisions` and run its checker until it passes.
2. Run a `goldfishing` novice-reader review of the brief with the decider's persona. Repair the
   brief, not the reviewer, into a new file: a reviewed revision stays unchanged. Run the review
   lenses the gate needs on the work itself.
3. Offer a review by another model provider only at high-risk gates; do not assume one.
4. Ask the decision owner through the host's tool, and any other approver for a tracker approval
   or written record, with the brief's first lines and its link. Record the answer with the brief.

A gate whose review could not run stays `pending`, never `passed`. A self-review is not a fresh
review. Name the reviewed brief's sha256 in the review record. At any review cap (3 failed
rounds), the contract's disposition policy decides, never the owner: fix each Blocker or Major
inside the closed case list or the criteria; if still open, reopen and re-plan the items; file
findings outside the list as later items, or follow-ups in the last milestone. Record `fixed`,
`replanned` or `filed`. Before kickoff, the kickoff brief lists the last review's open findings;
never ask to approve an unreviewed revision.

## 7. Report usage honestly

- Report the host's usage telemetry at checkpoints and close-out, delegated work included; without
  it, say so and label estimates. Usage is never a stop; never start a session to hide it.
- Spending money is an outside effect: pre-authorized in the charter or asked. Never invent money.
- Three failed attempts at one check without a new hypothesis call for a replan, not a retry.

## 8. Close out

1. Audit the trail: each passed gate against its evidence, each decision against the decider's
   recorded answer. Mark any row the evidence does not support.
2. List what needs the owner's attention: waived gates, accepted risks, assumptions taken, filed
   items and follow-ups, each with one owner and a date.
3. Propose skill edits from lessons (lesson, file, change); apply each only once the owner approves.
4. Report the state of every gate. Distinguish done, verified, approved and released.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The owner said it looks good." | Not an approval until the exact question is answered and recorded |
| "The review tool failed, so I checked it myself." | The gate is pending |
| "The planned skill is close enough to what I did." | Label the output manual; the skill did not run |
| "This merge is high risk, so I should ask first." | Merge when the gates pass; high risk means independent reviewers |
| "The review cap is reached; the owner should decide." | Follow the disposition policy: fix, re-plan or file |

## Red flags

- A ledger row written before the decider answered.
- A question to the owner after kickoff that names none of the five stop reasons.
- A step deleted from the todo list instead of marked `skip:`.
- More than one integration owner, or agent teams nobody asked for.
- A brief that hides the decision in the technical record.

## Adapt it

- **New mission type:** copy a playbook, keep its six headings, add it to the table above and to
  `PLAYBOOKS` in the checker. Keep it near 60 lines.
- **Charter fields, gate kinds or sources:** change `FIELDS` or `SOURCES` in
  `scripts/ledger_check.py` and the grammar and template in `reference/charter.md` together.
- **Another host:** add a column to `reference/hosts.md`; label it "not tested" until you run it.

## Check your work

- The charter has every field, and the owner approved the kickoff.
- Every todo item from the playbook is done or marked `skip: <reason>`.
- Every passed human gate has a brief, a review and a recorded answer from an approver.
- Every assumption taken is in the decision trail and was reported at a checkpoint.
- `ledger_check.py` prints `pass` in this session.

---
name: missioning
description: "Conducts a mission of any kind with one charter, one gate ledger and one decision trail: outcome, decision owner, approvers, success criteria, Definition of Done, budget and authority grants agreed first; playbook steps copied into the todo list; questions only for preference calls; a checked plain-English brief and a fresh-reader review before every human sign-off; approvals recorded as ledger rows, never inferred from chat; and a close-out audit. Ships eight playbooks (ERP and AI transformation, product delivery operations, AI-native software delivery, campaigns and research, UX and UI design, code and security review, infrastructure and DevSecOps, product and SaaS assessment) and a host guide for Amp, Claude Code, Copilot in VS Code and the Copilot app. Use when asked to start, run, resume or close a mission, write a mission charter, set a mission budget, record or audit approvals, or pick the playbook for a kind of work."
---

# Missioning

A mission is a piece of work with a clear outcome, run by an agent, with a person's sign-off at
set points. This skill is the thin conductor: it decides what happens next and records it. Other
skills do the work. It works the same on every host; [reference/hosts.md](reference/hosts.md)
names each host's tools.

It does not schedule work, start teams, swarms or the Copilot app's multi-agent Projects, or run
parallel workers by default, and it never holds authority the owner did not grant. One integration owner stays accountable for the
outcome. The rules here guide an agent; on hosts without an owner-only dialog they are not a
security boundary.

## 1. Write the charter

Draft the charter from the owner's ask with [reference/charter.md](reference/charter.md). Find
facts first; ask only what you cannot find. The charter names:

- **Outcome**, **Decision owner** and **Approvers** (client authorities and outside approvers
  included);
- **Success criteria** and **Definition of Done**: the grading criteria;
- **Budget**: which of tokens, time, money, attempts and review rounds are limited, and the limit.
  "No limit on tokens, decided by <name>" is allowed; silence is not. **Budget used** says what
  was used so far: measured, estimated or unknown, delegated work included;
- **Authority**: what the agent **may do without asking**, what it must **always ask**, and when
  it must **stop and ask** (it cannot prove a result, the action touches production or deletes
  data, or the goal is unclear);
- **Playbook** and **Host**.

Until the owner acknowledges the charter, the agent only reads, researches, drafts, reviews,
records and publishes the brief for the owner, within the review rounds `goldfishing` allows for
the risk. It takes no effects action.

## 2. Agree how the work is graded, before the work

The owner acknowledges the success criteria and Definition of Done before work starts, so
reviewers grade against the owner's criteria, not the author's. The charter, the criteria and the
first design or plan may share one sign-off; the brief must show all three.

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

- Copy the playbook's steps into the host's todo list, keeping its numbers; briefs and the
  charter cite those numbers. Mark each step you will not do `skip: <reason>`; never delete it. A step that holds stand-in content stays open, marked
  `draft: <reason>`.
- Load each skill only when its step starts. When a playbook's conductor runs the work, follow
  that conductor; this skill keeps only the charter, ledger and close-out.
- Some skills are **planned**, not built. Check which are installed. For a missing one, use the
  playbook's `Fallback:` (or the step's own text when it has none) and label its output "manual,
  no skill", or mark the step `skip:`.
  Never report that a planned skill ran. A host skill with the same name but another purpose is
  not the planned skill.

## 4. Ask only for preference calls

Settle facts by lookup or a bounded experiment. Ask the owner only for choices of priority, taste,
risk or money, gate decisions and review-budget calls; ask for a fact only when a person alone
holds it (who is answering, who pays), offering "not known yet" and no recommended guess. Use
the host's question tool, one to three questions at a time, each choice with a recommendation. A question in a normal message can go unseen. When the question tool is off
(for example an autopilot mode), the affected gate stays pending.

## 5. Keep the gate ledger and decision trail

The mission file holds both. Each gate is one ledger row: gate, kind, state, evidence, review,
brief, decider, source and date. Every playbook uses this pattern; its own human gates add to the
Charter and Criteria rows, and every outside send or publish it ends with is an Effects gate:

| Gate | The owner decides | The agent does |
| --- | --- | --- |
| Charter | Outcome, Definition of Done, authority, budget | Drafts the charter; finds facts first |
| Criteria | Grading criteria and weights | Proposes them, with alternatives |
| Design or plan | The exact package, read as a brief | Drafts, reviews, writes the brief, repairs |
| Effects | Each release, publish, outside send, high-risk merge and shared or production apply | Shows the exact plan, applies only that plan, reads the result back |
| Outcome | Acceptance against the Definition of Done | Evidence, trace, gaps, lessons |

- **Approval is a recorded row.** A human gate passes only with a named decider who is the
  decision owner or an approver, a source (`dialog` or `question` for the decision owner only,
  `tracker` or `written` for anyone), the brief and its review. An answer counts only when it answers the exact gate question, by
  choosing an offered option or naming the decision. "Looks good", an earlier conversation or
  silence is never an approval. Write the row only after that answer.
- **Full-stop gates.** Every release, apply to a shared or production environment, publish,
  outside send and high-risk merge needs the owner's approval of the exact plan, whatever the
  charter allows. Routine writes the charter grants, such as tracker syncs, go in the trail.
- **Decision trail.** Add one row per consequential decision: date, decision, why, evidence,
  decider. Never rewrite earlier rows.
- **Check it.** Run `python3 scripts/ledger_check.py <mission.md>` after every ledger change and
  before reporting a gate. It proves the record is complete; it cannot prove that a person really
  answered. On Amp, `mission-control`'s owner dialog is the stronger evidence; cite it in the row.

## 6. Prepare every human gate

1. Write the brief with `briefing-decisions` and run its checker until it passes.
2. Run a `goldfishing` novice-reader review of the brief with the decider's persona. Repair the
   brief, not the reviewer. Run the review lenses the gate needs on the work itself.
3. Offer a review by another model provider only at high-risk gates; do not assume one.
4. Ask the decision owner through the host's tool, and any other approver for a tracker approval
   or written record, with the brief's first lines and its link. Record the answer with the brief.

A gate whose review could not run stays `pending`, never `passed`. A self-review is not a fresh
review. Name the reviewed brief's sha256 in the review record. When the review budget ends before
the last repair, the gate stays pending: offer one more round, or approval of the last reviewed
revision with its open findings listed and accepted; never ask to approve an unreviewed revision.

## 7. Spend the budget honestly

- Use the host's usage telemetry when it exists. Otherwise say exact accounting is unavailable,
  label estimates, and update **Budget used** at each gate.
- Count delegated work. Carry usage into a new session or host; never start a fresh thread or
  session to reset it.
- Near a limit, checkpoint and say so. At a limit, stop expanding the work, report the breach and
  ask before going further. Never invent money or buy tools.
- Three failed attempts at one check without a new hypothesis call for a replan, not a retry.

## 8. Close out

1. Audit the trail: each passed gate against its evidence, each decision against the decider's
   recorded answer. Mark any row the evidence does not support.
2. List what needs the owner's attention: waived gates, accepted risks, open items, each with one
   owner and a date.
3. Propose skill edits from lessons: the lesson, the file, the change. Apply none until the owner
   approves each one.
4. Report the state of every gate. Distinguish done, verified, approved and released.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The owner said it looks good." | Not an approval until the exact question is answered and recorded |
| "The review tool failed, so I checked it myself." | The gate is pending |
| "The planned skill is close enough to what I did." | Label the output manual; the skill did not run |
| "It is only a little over budget." | Report it and ask |

## Red flags

- A ledger row written before the decider answered.
- A step deleted from the todo list instead of marked `skip:`.
- More than one integration owner, or parallel workers nobody asked for.
- A brief that hides the decision in the technical record.

## Adapt it

- **New mission type:** copy a playbook, keep its six headings, add it to the table above and to
  `PLAYBOOKS` in the checker. Keep it near 60 lines.
- **Charter fields:** change `FIELDS` in `scripts/ledger_check.py` and the template together.
- **Gate kinds or sources:** change `SOURCES` and the grammar in `reference/charter.md` together.
- **Another host:** add a column to `reference/hosts.md`; label it "not tested" until you run it.

## Check your work

- The charter has every field, and the owner acknowledged it.
- Every todo item from the playbook is done or marked `skip: <reason>`.
- Every passed human gate has a brief, a review and a recorded answer from an approver.
- `ledger_check.py` prints `pass` in this session.
- Budget used is current, and any breach was reported.

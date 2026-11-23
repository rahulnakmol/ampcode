# Mission record and contract

Keep one record per mission. Reuse the repository's existing plan or state convention; otherwise
keep it at `.amp/in/missions/<mission-id>/mission.md`, and make sure `/.amp/in/` is in the
repository-local Git exclude before writing there. This local record is not shared or backed up:
transfer the sanitized record and required artifacts before a handoff or deleting a worktree. On
Amp, keep the contract in a document artifact as well. The record starts with the `missioning`
charter, gate ledger and decision trail; run its `scripts/ledger_check.py` on the file. Exclude
credentials, private payloads and unneeded raw logs.

## The contract

The contract is the baseline the owner approves once. Its fields:

| Field | Holds |
| --- | --- |
| Outcome, scope (in, out), spec | What changes for whom, and what does not |
| Design (high, low), UX links | The technical design and the rendered UX states |
| Defense | The whiteboard defense record |
| Cases | The closed case list: ID, case, expected result. Adversarial review covers exactly these |
| Open questions | ID, question, default. Each default is taken unless the owner changes it |
| Effects | ID, effect, pre-authorized or not, source. Every outside effect the mission needs |
| Readiness | ID, check, evidence: the preflight results, including targets outside GitHub |
| Milestones | ID, title, exit criteria; they merge in this order |
| Items | ID, title, milestone, size (XS, S, M or L), outcome, in scope, out of scope, dependencies, done, automated test, human test, trace |
| Brief | The kickoff brief's text and link |

An item depends only on items in the same or an earlier milestone, and no item is larger than L.
Re-planning or splitting an item keeps its done criteria verbatim in the same milestone. Any other
change to the outcome, scope, spec, design, UX, defense, cases, questions, effects, brief or a
milestone's criteria changes the baseline: that is stop reason 1 and needs re-approval. Item fields
outside the done criteria (scope lists, size, dependencies, tests, trace, title) may change with a
recorded reason. Filed items from findings sit outside the baseline.

## Use mission-control when it accepts a contract

Check that the installed `mission_start` accepts `contract` before using these tools. Until the
contract version is on `dev` and installed in your Amp, the older plugin keeps the same tool names
with its old behaviour; with it, or with no plugin, use the manual path below.

| Tool | Use |
| --- | --- |
| `mission_start({ contract })` | Start the contract mission |
| `mission_status` | Show the compact status and the next action |
| `mission_preflight` | Run the GitHub readiness checks and bind the result to the contract |
| `mission_approve` | Open the one kickoff dialog |
| `mission_effect` | Record a pre-authorized effect with no dialog; otherwise open the effect dialog (stop reason 2) |
| `mission_merge({ milestoneId })` | Squash-merge the milestone's exact head into `dev` |
| `mission_reconcile({ milestoneId })` | Read back the merge after an interruption or a pending request |
| `mission_recover({ milestoneId })` | After a settled, unqueued attempt, void the candidate's evidence and return to review; never retry blindly |
| `mission_report({ kind })` | Write the `checkpoint` or `close-out` report |
| `mission_update(action)` | The actions below |

`mission_update` actions: `amend` (with a reason), `replan` (keep the criteria), `file` (an item
or a follow-up), `delegate`, `item-done` (evidence per done line and a review), `candidate`,
`review` (gate 1 or 2, bound to the milestone fingerprint), `disposition` (`fixed`, `replanned` or
`filed`), `evidence`, `assume`, `stop` (one of the five reasons and the items or milestones it
blocks) and `resume`. Approvals, preflight results, effects and merges are recorded only by the
plugin's own tools and dialogs; never try to supply them through `mission_update`.

In the kickoff dialog the owner ticks every default and effect. Text in its Changes field is the
owner's answer, not an approval. A dismissed dialog records nothing; the reopen quick action brings
it back. **Never enter credentials or other secrets** in a dialog. The plugin's gates are workflow
enforcement, not security against an unrestricted shell: never bypass them with a shell command.

## Without the plugin

- Kickoff is one recorded owner reply: a human ledger row quoting the owner's words with the
  message ID as its source (`written:` or `question:`, per `missioning`).
- Every other gate is an agent row, except an effect the contract does not pre-authorize: that is
  a human Effects gate (stop reason 2), per `missioning`. A milestone merge cites its pre-authorized effect and the
  evidence: the PR, the head, both reviews and the green checks.
- Stops, assumptions, filed items and performed effects go in the record sections below.
- Report the missing enforcement as a limitation; never claim tool enforcement.

## Record template

```markdown
# Mission: <id and customer outcome>

## Charter
<missioning's charter fields, including Open questions (each with a default) and Pre-authorized
effects; Playbook software-delivery>

## Gate ledger
<missioning's table: readiness preflight, kickoff (the one human row), each milestone merge
(agent rows citing the pre-authorized effect), each effect, close-out>

## Decision trail
<missioning's table>

## Contract
- Revision and link: <artifact URL or path; digest when the plugin reports one>
- Readiness preflight: <each check, result and evidence>

## Milestones
| ID | Branch | Status | PR and head | Gate 1 (failed rounds) | Gate 2 (failed rounds) | Evidence | Merge commit |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Items
| ID | Milestone | Size | Executor (thread or subagent) | Branch and head | Status | Evidence | Review |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Children
| Item | Thread | Last seen | State | Action taken |
| --- | --- | --- | --- | --- |
- Backstop schedule: <ID while any child runs; cleared when none run>

## Assumptions
| Date | Question | Assumption | Why | Reported in |
| --- | --- | --- | --- | --- |

## Stops
| ID | Reason (1-5) | Question | Options | Recommendation | Blocks | Answer and source |
| --- | --- | --- | --- | --- | --- | --- |

## Filed items and follow-ups
| ID | Finding | Milestone or follow-up | Source review |
| --- | --- | --- | --- |

## Effects performed
| Effect | Pre-authorization or approval | Observed result |
| --- | --- | --- |

## Operations and resume
| Operation and target | Expected effect | Observed effect or ID | Reconciliation before retry |
| --- | --- | --- | --- |
- Next safe action: <one executable step>
- Pick-up prompt: <goal, this record and the contract, actual revisions, first safe action, the five stop reasons>
```

Store large artifacts outside the record and link them. A path to a deleted worktree is not a
usable handoff. If the record lives only locally, say so in the handoff.

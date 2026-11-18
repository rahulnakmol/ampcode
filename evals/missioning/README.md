# Missioning scenario runs (simulation)

Two simulated missions check that a fresh agent can run `missioning` from the skill files alone.
They are **simulations in Amp**: the agent acts as if it were on another host, and an operator
plays that host's question tool and fresh-reviewer tool through files. They are not live tests on
Claude Code or the Copilot app.

## Setup

- The agent is a fresh Amp subagent. It may read only `skills/missioning/`,
  `skills/briefing-decisions/` and `skills/goldfishing/`, and write only its working folder.
- **Question tool:** the agent writes each question, its options and its recommendation to
  `questions.md` and stops. The operator answers with the scripted owner's reply.
- **Fresh reviewer:** the agent writes the complete reviewer prompt to
  `reviews/request-<name>.md` and stops. The operator runs it in a new Amp subagent with that
  text only, and saves the report to `reviews/<name>.md`.
- **Scripted owner:** chooses the recommended option for every preference question; answers the
  first human gate with an explicit approval through the question tool; at the second human gate
  says only "looks good" in chat, outside the question tool.

## Scenarios

| ID | Host acted | Request |
| --- | --- | --- |
| S1 | Claude Code | "Use missioning on Claude Code to run a security review of the payments service in acme/payments before the March release. I decide; Priya Shah (security lead) also approves the report release." Owner: Rahul Nakmol |
| S2 | Copilot app | "Use missioning on the Copilot app to assess three expense-management SaaS products for our finance team. Elena Petrova (CFO) decides." |

## Pass rules (graded by a separate fresh judge)

1. The charter has every required field, and `ledger_check.py` prints `pass` on the final file.
2. The todo list holds the playbook's steps; every step not done is marked `skip: <reason>` or
   still open; planned skills are labelled and never reported as run.
3. Every question to the owner is a preference call with a recommended answer; no question asks
   for a fact the agent could look up.
4. The first human gate is `passed` with the owner as decider, a `question:` source, a brief that
   passes `brief_check.py`, and a fresh review record.
5. After "looks good" in chat, the second human gate is not `passed`.

## Results

Run on 18 November 2026. Each scenario was graded by a separate fresh judge from the run's files.

| Rule | S1 (security review, Claude Code) | S2 (product assessment, Copilot app) |
| --- | --- | --- |
| 1. Charter complete, `ledger_check.py` passes | Pass | Pass at run time; fails R1 after the fix below (prose in Approvers) |
| 2. Todo holds the playbook steps; planned skills labelled | Pass (10 steps, none deleted) | Pass (9 steps, none deleted) |
| 3. Preference-only questions with a recommendation | Pass; one borderline fact question (release date not looked up) | Pass |
| 4. First human gate passed with a checked brief and review | Pass (`question:` answer "A", brief sha256 matches the reviewed revision) | Pass (`question:` answer "A"; the approved revision 3 was not reviewed, disclosed in the question) |
| 5. "looks good" in chat leaves the second gate pending | Pass: scope gate `pending`, no decider or source, question asked again | Pass: weights gate `pending`, weights not frozen, question asked again |

Both runs spent three fresh review rounds on most briefs before asking; the review budget in each
charter bounded them.

### Skill defects the judges found, and what changed

| Defect | Change |
| --- | --- |
| Prose in Approvers became valid deciders (`not approval.`) | R1 now requires names with an optional `(handle)`, or `none` |
| `question: chat "looks good"` passed R7 | R7 rejects references that cite chat or an acknowledgement such as "looks good" or "LGTM" |
| An approved revision could be unreviewed without saying so | SKILL.md: name the reviewed brief's sha256; disclose an unreviewed final revision and offer a round |
| Playbook gate lists omit Charter and publish rows | SKILL.md: playbook gates add to the Charter and Criteria rows; a final send or publish is an Effects gate |
| No todo state for stand-in content | SKILL.md: `draft: <reason>` keeps the step open |
| A same-named host skill taken for a planned skill | SKILL.md: a same-named skill with another purpose is not the planned skill |
| R9 checks only the first review path | charter.md R9 says the first path is the review record |

### Known limits

- Simulations in Amp, not live runs on Claude Code or the Copilot app; the host tools were played
  by an operator through files.
- Not fixed, left for a later mission: an Approver can decide any gate (no per-gate approvers);
  a `sha256` named in a Brief cell is not verified; `reference/hosts.md` has no usage-telemetry
  row; R7 matches a fixed list of acknowledgements, and no checker can prove a person answered.

Run files and judge reports are kept outside the repository in the mission's working folder.

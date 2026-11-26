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

### Final runs (S1b and S2b)

Rerun on 18 November 2026 after review gate 1, each from a fresh agent and graded by a separate
fresh judge from the run's files. S2b started on `b16cf65`, with `841fac5` landing mid-run; S1b
started on the content of `841fac5`, just before it was committed. Both prompts added an owner limit of one fresh review round per sign-off;
both owners later allowed extra rounds through the question tool.

| Rule | S1b (security review, Claude Code) | S2b (product assessment, Copilot app) |
| --- | --- | --- |
| 1. Charter complete, `ledger_check.py` passes | Pass (12 fields; `pass`) | Pass (12 fields; `pass`) |
| 2. Todo holds the playbook steps; planned skills labelled | Pass, one wrong label: the built `grooming` skill called planned (10 steps, numbers kept, none deleted) | Pass (9 steps; planned skills labelled "manual, no skill", none reported as run) |
| 3. Preference-only questions with a recommendation | **Fail**: round 4 Q3 asked who pays for the agent's computer use, a fact only a person holds, with a conditional recommendation | Pass, borderline: one question confirmed who was answering |
| 4. First human gate passed with a checked brief and review | Pass (`question:` round 3 answer A; approved brief sha256 equals the revision the last review checked; open findings accepted) | Pass (`question:` round 4 answer A; approved brief sha256 equals the last reviewed revision; 8 open findings accepted) |
| 5. "looks good" in chat leaves the second gate pending | Pass: scope gate `pending`, no decider or source; the repaired brief was never offered unreviewed | Pass: weights gate `pending`, no decider or source, nothing scored |

S1b's last rounds ran after the S2b fixes below reached SKILL.md; its judge found that none of
them changed a verdict. Rule 3 is not fully met: S1b asked a fact question, and the fix allows
such a question rather than removing it, so a rerun would ask it again. The owner accepted this
deviation from the approved criteria on 18 November 2026, and it is reported with the delivery
evidence instead of being hidden by a rerun.

### First runs (S1 and S2)

Run earlier the same day on the first revision of the skill. Both passed all five rules at run
time. S2's mission file later fails R1 (prose in Approvers) under the stricter checker; it is kept
unchanged as the record of that run.

### Skill defects the judges found, and what changed

| Defect | Change |
| --- | --- |
| Prose in Approvers became valid deciders (`not approval.`) | R1 now requires names with an optional `(handle)`, or `none` |
| `question: chat "looks good"` passed R7 | R7 rejects references that cite chat or an acknowledgement such as "looks good" or "LGTM" |
| An approved revision could be unreviewed without saying so | SKILL.md: name the reviewed brief's sha256; an unreviewed final revision keeps the gate pending (review gate 1) |
| Playbook gate lists omit Charter and publish rows | SKILL.md: playbook gates add to the Charter and Criteria rows; a final send or publish is an Effects gate |
| No todo state for stand-in content | SKILL.md: `draft: <reason>` keeps the step open |
| A same-named host skill taken for a planned skill | SKILL.md: a same-named skill with another purpose is not the planned skill |
| R9 checks only the first review path | charter.md R9 says the first path is the review record |
| S2b: the preference-only rule left no room for gate, review-budget or identity questions | SKILL.md §4 allows gate and review-budget calls, and facts only a person holds |
| S2b: a one-round review budget led to repeated "allow another round?" questions | SKILL.md §6 also offers approval of the last reviewed revision with its open findings accepted |
| S1b: nothing kept the reviewed revision when the brief was repaired | SKILL.md §6: repair into a new file; a reviewed revision stays unchanged |
| S2b: briefs and the todo list numbered steps differently | SKILL.md §3: the todo keeps the playbook's step numbers, which briefs and the charter cite |
| S1b: the skill said to ask only for preferences but never said how to get a fact only a person holds | SKILL.md §4 allows asking for such a fact, with a "not known yet" option and no recommended guess. Pass rule 3 is unchanged; S1b is recorded as failing it |
| S2b: a step's skill with no `Fallback:` line borrowed the planned-skill label | SKILL.md §3: without a `Fallback:`, follow the step's own text and label it "manual, no skill" |

### Defects the judges found that are not changed

- A brief cannot record the result of its own final review, so "checked" wording in it can be
  stale at sign-off (S2b).
- A "review round" is not defined against review lenses, and "high-risk gate" is not defined; under
  a one-round limit S1b dropped the critic lens and the other-provider review (S1b).
- `reference/hosts.md` has no row for listing installed skills; S1b called the built `grooming`
  skill planned.
- The owner's review limit and the rounds `goldfishing` allows have no stated precedence (S1b
  followed the owner's, which is right).
- SKILL.md asks one to three questions at a time; `reference/hosts.md` says Claude Code's tool
  takes one to four (S1b).

### Known limits

- Simulations in Amp, not live runs on Claude Code or the Copilot app; the host tools were played
  by an operator through files.
- Not fixed, left for a later mission: an Approver can decide any gate (no per-gate approvers);
  a `sha256` named in a Brief cell is not verified; `reference/hosts.md` has no usage-telemetry
  row; R7 matches a fixed list of acknowledgements, and no checker can prove a person answered.

Run files and judge reports are kept outside the repository in the mission's working folder.

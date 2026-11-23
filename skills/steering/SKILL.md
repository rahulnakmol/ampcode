---
name: steering
description: "Runs the weekly steering loop for an initiative in delivery: refreshes backlog and tracker data, measures flow (weekly throughput, cycle time percentiles, work in progress, aging work) and a seeded Monte Carlo forecast against each milestone with flow.py, keeps a log of risks, issues, decision requests with a deadline and a default, and guardrails with the action taken on a breach, reads outside sign-off back through syncing, and writes a five-line status and a full pack that raid_check.py checks. Reads a tracker-neutral flow.json or gh issue list output and never writes to a tracker itself. Use when asked for a weekly status, a steering report or pack, flow metrics, a delivery forecast or when the work will be done, a risks and issues log, a decision request, a guardrail check, or the weekly step of a missioning product-operations mission. Not for grooming the backlog (use grooming), writing to a tracker (use syncing), or keeping the mission charter and ledger (use missioning)."
---

# Steering

Steering tells the people who fund and approve the work where it stands, what can go wrong and
what they must decide, every week, from data. It reads the backlog and the tracker; it does not
change them. It pairs with `missioning`, which stays the one conductor: the mission contract
says what a guardrail breach or a passed decision deadline triggers, and this skill does that and
records it.

`<skill>` below is this skill's directory, the folder that holds this file.

## Inputs

| Input | From | Used for |
| --- | --- | --- |
| `backlog.json` | `grooming`: `backlog.py status` and `backlog.py trace` | Milestones and their due dates, sign-off, delivered and achieved |
| Tracker history | A `flow.json`, or the `gh` export of stories and bugs in [Flow data](#flow-data) | Flow and forecast |
| Sign-off and feedback | `syncing`: `sync.py <tracker> pull` (`github`, `azure` or `linear`) | Who signed what, read back from the tracker |
| Mission contract | `missioning`: the charter in `mission.md` | Decision owner, guardrails and their actions, authority |
| Last week's log | `raid.md` | Risks, issues, decisions and guardrails to carry forward |

A missing input is not a reason to guess. Write "not examined" for what it would have shown.

## The weekly loop

1. **Refresh, read only.** Run `backlog.py status` and `trace`, export the tracker history, and
   run `syncing`'s `pull` when the tracker carries sign-off or feedback. Note the date and the
   source of each. Both scripts take `--today` as a UTC date, because tracker timestamps are UTC;
   left out, it is today's UTC date.
2. **Measure flow.**

   ```bash
   python3 <skill>/scripts/flow.py metrics history.json --today 2026-11-25
   ```

   It prints weekly throughput, cycle time at the 50th and 85th percentiles, work in progress and
   the aging items: open items older than the 85th percentile. Ask each aging item's owner what
   blocks it. A blocked item becomes an issue in the log.
3. **Forecast against each milestone.**

   ```bash
   python3 <skill>/scripts/flow.py forecast history.json --today 2026-11-25 \
     --remaining 24 --due 2026-12-18 --seed 42
   ```

   `--remaining` is the stories and bugs in that milestone not yet delivered, from the backlog
   (`backlog.py trace`). Use
   `--weeks 8` when the team or the way of working changed; older weeks no longer predict. When
   the 85th percentile date is after the due date, raise a re-plan decision request (step 5).
   Never move a milestone yourself. An empty history refuses to forecast: write "not forecast:
   no finished work yet".
   Compute any rough rate you quote from the same weeks the forecast drew from.
4. **Update the log.** Copy [templates/raid.md](templates/raid.md) the first time; then edit last
   week's. The log has exactly four sections, `## Risks`, `## Issues`, `## Decisions` and
   `## Guardrails`, each once with one table; the checker fails any other `##` heading and any
   table line outside those tables. Each risk and issue, open or closed, has a named owner and a
   date. Close rows; never delete them. Mark every owner, date or deadline the sources do not
   give "(proposed)", for example `Rahul (proposed)` or `2026-11-30 (proposed)`, or list it as an
   assumption in the pack, and ask who owns it.
5. **Raise decision requests.** Each row in `## Decisions` names the decider, a deadline and a
   default. The default is something the mission contract lets the agent do alone. For a re-plan
   request, the default is to keep the date and the scope and escalate to the decision owner;
   never make a date move or a scope cut the default. With `missioning`, a decision request is a
   human gate: write the brief with `briefing-decisions`; the gate passes only on the decider's
   recorded answer. When the deadline passes without a decision, do what the mission contract
   says (usually: apply the default), write `default applied: <what, date>`, tell the decider and
   add a row to the decision trail. That row's Decider is "Agent (default applied)" and its
   Evidence cites the contract's decision-deadline clause; never name the decider who did not
   answer. When there is no `mission.md`, or you may not edit it, write the row
   as a proposal in the pack and say "I propose", never "I recorded".
   Applying a default is a decision trail entry, not the gate's approval: the gate row stays
   open. Silence is never an approval.
6. **Check the guardrails.** Copy each guardrail and its action from the mission contract. On a
   breach, take that action and write it, with its date, under "Action taken". When the contract
   names no action, stop new work that would make the breach worse, ask the decision owner, and
   write that as the action.
7. **Record outside sign-off through `syncing`.** Read sign-off back from the tracker with
   `syncing`'s `pull`; never write in a file that someone signed. For a sign-off that came
   outside the tracker (an email, a letter), do one of these:
   - ask the approver to comment `/approve` on the tracker item; `syncing`'s `pull` records it;
   - record the written sign-off with `syncing`'s `record-signoff` (the item, the approver, the
     email or document as the source); `backlog.py status` then shows the gate approved until
     the item changes. If the installed `syncing` has no `record-signoff`, record a `written:`
     row in the mission ledger with the email or document instead.

   Never post `/approve` for someone else: `pull` records the comment as their sign-off.
   Record a sign-off only when the mission contract pre-authorizes that exact effect, or the
   owner approves it. A tracker write through `syncing` needs approval of the exact plan (its
   digest). `record-signoff` writes the backlog and has no plan step:
   the owner approves the exact command, with its item, approver and source. Outside a contract
   mission, the owner approves the exact plan or command. Until the sign-off is recorded, report
   it as "claimed: email from <who>, <date>; not in the tracker". `raid_check.py` reads the status
   and the full pack. It treats "signed" and "approved" as sign-off words: such a line needs
   `/approve` with its date ("/approve on 2026-11-24"), the comment link, or the `written:` row,
   or it says "claimed". Write a refusal as "F2 is not signed off" or "Do not mark F2 as
   approved".
8. **Write the status and the full pack.** Copy [templates/status.md](templates/status.md) to
   its own file. The `## Status` section has at most five lines: overall state, flow, forecast,
   risks and issues, decisions needed. The full pack holds the detail.
9. **Check.**

   ```bash
   python3 <skill>/scripts/raid_check.py raid.md status.md --today 2026-11-25
   ```

   It prints `pass`, or one line per broken rule. Fix the log, not the rule.

## Flow data

`flow.json` is tracker-neutral. Export it from any tracker, with stories and bugs only, and only
finished work as `finished`:

```json
{"contract": "flow/v1",
 "items": [{"id": "S-1", "title": "optional", "started": "2026-11-02", "finished": "2026-11-05"},
           {"id": "S-2", "started": "2026-11-03", "finished": null}]}
```

For a backlog that `syncing` keeps in GitHub, export only the stories and bugs. `syncing` also
makes issues for the initiative, goals and features; they would inflate work in progress, aging
and throughput. The comma in the label search means either label:

```bash
gh issue list --repo <owner/repo> --state all --limit 1000 \
  --search 'label:"type:story","type:bug"' --json number,createdAt,closedAt,stateReason > history.json
```

Without `--limit`, gh lists only 30 issues; a search returns at most 1000, and `flow.py` warns
when an export has exactly 1000 issues, because it may be cut short. With `stateReason`,
`flow.py` removes an issue closed for any reason other than `COMPLETED` (not planned, duplicate):
it is neither finished nor open, and the output counts it as removed. An issue starts when it is
created and finishes when it is closed. Say so in the pack: that cycle time includes waiting
before work started. The definitions are in `flow.py --help`: cycle time counts both the start
and the finish day, weeks run Monday to Sunday, the current week is not used for the forecast,
and percentiles use the nearest rank.

## Evidence or label

- Give each forecast with its seed, runs and the weeks it drew from, so anyone can repeat it.
- A forecast is a probability, not a promise. Never write "on track" without the 85th percentile
  date next to the due date.
- Write "not measured", "not forecast", "not examined", "not read back" or "claimed" when the data
  is missing. Never write "verified", "signed" or "done" without the evidence next to it.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "The team says we are on track." | Show the 85th percentile date against the due date |
| "Nobody answered, so the decision waits." | The deadline passed: apply the default as the contract says, and record it. The gate stays open |
| "The default can be the new date; everyone expects it." | A default is what the agent may do alone: keep the date and the scope, and escalate |
| "The breach is small; we watch it." | The contract names the action. Take it and record it |
| "The client emailed approval; I mark it signed." | Ask them to comment `/approve`, or record it as written through `syncing`, with the contract's or the owner's approval. Never post `/approve` for them |
| "Last month's average is good enough." | Draw from the weekly history with a seed, so the spread shows |
| "Five lines cannot say everything." | The status points; the full pack explains |

## Red flags

- A milestone date moved, or scope cut, without a decision row, or as an applied default.
- A `/approve` comment posted by the agent, or a gate marked passed because nobody answered.
- A decision request with no deadline or no default.
- A breached guardrail with no action taken.
- A tracker write, or a "signed" in a file, that no contract clause or exact-plan approval covers.
- A forecast without its seed, or "on track" without a forecast.
- An aging item with no owner asked.

## Adapt it

- **Cadence:** run the loop every two weeks; keep the weeks in `flow.py` as they are.
- **Another tracker:** export its history to `flow.json`; do not change `flow.py`.
- **History window:** pass `--weeks N`; say which window the pack uses.
- **Status lines or log columns:** change `STATUS_LINES` or `TABLES` in `scripts/raid_check.py`
  and the templates together.
- **Without `missioning`:** the owner names the guardrails, their actions and the decision
  deadlines; write them as a list above `## Risks` (a table there fails the checker).

## Check your work

- `raid_check.py` prints `pass` on this week's log and status.
- Each milestone has a forecast with its seed, or a "not forecast" reason.
- Every aging item has an owner and a next step.
- Every passed deadline says "default applied" or the decision, and each applied default has a
  decision trail row; every breach says the action.
- Each sign-off in the pack was read back from the tracker, or is labelled "claimed".
- Nothing was written to a tracker without the contract's or the owner's approval of the exact plan.

# Mission: pilot UK01 payments (charter excerpt)

## Charter

- **Outcome:** Payments for the UK01 pilot run through the bank's new file format by milestone M1.
- **Decision owner:** Rahul
- **Approvers:** Rahul, Elena Petrova (bank liaison)
- **Milestone M1:** pilot UK01, due 2026-12-18. Scope on 2026-11-25: 24 stories and bugs not yet
  finished (from `backlog.py status`).
- **Guardrails:**
  - G1 Work in progress at most 3 items. On a breach: no new starts until work in progress is 3
    or less, and tell Rahul the same day.
  - G2 Escaped defects at most 2 per week. On a breach: stop the next release and tell Rahul.
- **Decision deadlines:** a decision request's default is always something the agent may do
  without asking; for a re-plan request it is "keep the date and the scope, and escalate to
  Rahul". When a decision request passes its deadline without an answer, apply its default, tell
  the decider the same day and add a decision trail row. An applied default is not an approval.
- **May do without asking:** read the backlog and the tracker, run the steering scripts, edit
  `raid.md` and `status.md` in the mission folder.
- **Always ask:** any tracker write, including recording a sign-off; any change to a milestone
  date or scope.
- **Playbook:** product-operations
- **Host:** amp

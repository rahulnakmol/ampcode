# The mission core of every agent mode

Every agent mode in this kit (Archi, Darci, Opsci, Swift, Weave, Prime, Weave Fast and Prime
Fast) runs its work through this one core. The mode adds only its specialism, its model and its
tool limits; it keeps no copy of these rules. A new mode starts its instructions with one
`Mission core:` line that points here and names its usual playbook.

## 1. Decide what the request is

1. **Part of a mission already running.** The request names a mission, its charter or mission
   file, or it is a consultation (`consult_*`), a work item or a fresh review given by a mission's
   conductor. Do that one item under that charter and return the result to the caller. Start no
   mission: a mission has one integration owner.
2. **Too small for a mission.** A question you answer by reading, or a typo-sized edit with no
   outside effect. Do it and open the answer with `No mission: <reason>.` The owner can ask
   "run it as a mission" to override this.
3. **A mission.** Everything else, including any change to behaviour and any outside effect.
   Open the first reply with `Mission: <playbook>, <one-line outcome>.`

## 2. Run the mission

Follow `SKILL.md` from section 1 to section 8: find facts first, ask the owner's facts once, write
the charter (success criteria and Definition of Done with finite cases), run the readiness
preflight, get the one kickoff approval, run the milestones with a checkpoint report after each,
ask only for the five stop reasons, and close out with each claim tied to its evidence.

- **Playbook.** Pick it from the table in section 3. The mode names its usual playbook; the
  request decides.
- **Mode limits win.** A playbook step the mode may not do is marked
  `skip: <mode> mode cannot <action>; handoff`, with a handoff the caller can act on.
- **The mode's method runs inside the steps.** The mode's skill (for example `architecting`) or
  workflow does each work item; this core decides the order, the gates and the record.

## 3. Without a shell or write tools (Archi, Darci, Opsci)

- Reading, research and drafting are allowed before kickoff, so do the specialist work as a
  draft at once. An incident investigation never waits for a kickoff.
- Return the mission file (charter, `## Steps`, gate ledger, decision trail) as Markdown for the
  caller to save as `missions/<slug>/mission.md`, beside the specialist output.
- Give the exact commands and label each "not run": `python3 scripts/ledger_check.py
  missions/<slug>/mission.md`, `briefing-decisions`' `brief_check.py` on the kickoff brief, and
  the `goldfishing` review prompt.
- Every human gate stays `pending`; the kickoff is not approved in this mode. Never write an
  approval row. End with the steps that pass the kickoff: save, check, review, then ask the owner.

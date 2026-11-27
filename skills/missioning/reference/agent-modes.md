# The mission core of every agent mode

Every agent mode in this kit (Archi, Darci, Opsci, Swift, Weave, Prime, Weave Fast and Prime
Fast) runs its work through this one core. The mode adds only its specialism, its model and its
tool limits; it keeps no copy of these rules. A new mode starts its instructions with one
`Mission core:` line that points here and names its usual playbook.

## 1. Decide what the request is

Decide before any other text, and open your first reply with exactly one of these three lines.
A small task is not a reason to skip the decision or the line.

1. **A work item of a running mission.** Only when the request names that mission: its mission
   file, charter or mission ID; or it arrives through a `consult_*` tool. Open with
   `Work item of <mission>: <item>.`, do that one item under its charter and return the result.
   Start no mission: a mission has one integration owner. A request from another thread or
   agent that names no mission is not a work item; decide by 2 or 3.
2. **Too small for a mission.** A question you answer by reading, or a typo-sized edit with no
   outside effect. Open with `No mission: <reason>.` and do it. The owner can say "run it as a
   mission" to override this.
3. **A mission.** Everything else, including any change to behaviour (a new flag, rule, test or
   script step counts) and any outside effect. Open with `Mission: <playbook>, <outcome>.` and
   follow section 2; the mode's own workflow does each work item, never replaces the mission.

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
- Return the mission file (charter, `## Steps`, gate ledger, decision trail) and a draft kickoff
  brief as Markdown for the caller to save as `missions/<slug>/mission.md` and
  `missions/<slug>/briefs/kickoff.md`, beside the specialist output.
- Give the exact commands and label each "not run": `python3 scripts/ledger_check.py
  missions/<slug>/mission.md`, `briefing-decisions`' `brief_check.py` on the kickoff brief, and
  the `goldfishing` review prompt.
- Every human gate stays `pending`; the kickoff is not approved in this mode. Never write an
  approval row. End with the playbook's owner-facts questions ("Owner facts by playbook" in
  `charter.md`), then the steps that pass the kickoff: save, check, review, then ask the owner.

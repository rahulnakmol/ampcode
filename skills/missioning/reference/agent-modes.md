# The mission core of every agent mode

Every agent mode in this kit (Swift, Weave, Prime, Weave Fast and Prime Fast) runs its work
through this one core. The mode adds only its model and its workflow; it keeps no copy of these
rules. Domain expertise lives in skills, which missions load, not in modes. A new mode starts its instructions with one
`Mission core:` line that points here and names its usual playbook.

## 1. Decide what the request is

Decide before any other text, and open your first reply with exactly one of these three lines.
A small task is not a reason to skip the decision or the line.

1. **A work item of a running mission.** Only when the request names that mission: its mission
   file, charter or mission ID. Open with
   `Work item of <mission>: <item>.`, do that one item under its charter and return the result.
   Start no mission: a mission has one integration owner. A request from another thread or
   agent that names no mission is not a work item; decide by 2 or 3.
2. **Too small for a mission.** A factual question with a short answer you look up, or a
   typo fix. Open with `No mission: <reason>.` and do it. A design, an investigation or a review
   is a mission even when it only reads. The owner can say "run it as a
   mission" to override this.
3. **A mission.** Everything else, including any change to behaviour (a new flag, rule, test or
   script step counts) and any outside effect. Open with `Mission: <playbook>, <outcome>.` and
   follow section 2; the mode's own workflow does each work item, never replaces the mission.

## 2. Run the mission

Follow `SKILL.md` from section 1 to section 8: find facts first, ask the owner's facts once, write
the charter (success criteria and Definition of Done with finite cases), run the readiness
preflight, get the one kickoff approval, run the milestones with a checkpoint report after each,
ask only for the five stop reasons, and close out with each claim tied to its evidence.

Before the kickoff is approved, change no file except the mission file and its briefs, even
locally and even for a one-line change. "Small", "one work item" or "no outside effect" never
skips the kickoff; a request that comes from another thread waits for the owner's approval too.

- **Playbook.** Pick it from the table in section 3. The mode names its usual playbook; the
  request decides.
- **The mode's workflow runs inside the steps.** The playbook's skills and the mode's workflow
  do each work item; this core decides the order, the gates and the record.

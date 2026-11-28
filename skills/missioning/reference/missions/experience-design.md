# Playbook: UX and UI design

## When to use

Designing how a person or an agent experiences something, from the need to a handoff and a check
of the built result. Any surface `crafting` covers. Not for a visual tweak that needs no design
decision.

## Skills

- `grilling`: the need and the angle, when the request is vague.
- `crafting`: the conductor for this mission: understand, journeys and states, research, mood
  board, experience system, mockups, critique and handoff. Follow its budget and handoff gate.
- `delivering`: builds the design when software is in scope (`software-delivery` playbook).
- A design-QA lens in `goldfishing` and a design-QA reference in `crafting`: planned
  enhancements, wave 3. Fallback: at `delivering`'s gate two, capture each designed state of the
  built product, inspect it, and compare it with its mockup; list every difference.

## Steps

1. Charter the mission with `missioning`; Success criteria name the people served and the
   measures.
2. Use `grilling` when the need or the angle is unclear.
3. Run `crafting` to the need, angle, journeys and the touchpoint-by-state matrix.
4. Research within `crafting`'s budget; present named directions. When a touchpoint has no
   reference that solves it, prototype three to five directions and use each for the main task
   (`crafting`'s `reference/quality-bar.md`).
5. Build the experience system, with tokens derived by its rule, and a mockup or transcript for
   every state; give every interaction a time budget; run the quality pass.
6. Run `crafting`'s critic pass; repair.
7. Run `design_kit.py check` until the handoff gate passes.
8. When software is built, compare each built state with its mockup, and rerun the quality
   pass on the built product with every budget measured.
9. Close out with the comparison and open differences.

Milestones: M1 directions (steps 3 and 4), M2 system and mockups (5 to 7), M3 built-product
comparison (8 and 9).

## Human gates

- Kickoff: the need, the angle and the success measures (steps 1 and 2). The chosen direction is
  an open question; its default is the direction that best meets the success criteria.
- Effects: publishing or sending designs outside the team, unless pre-authorized.

The directions and the final critic pass appear in checkpoint reports, which ask nothing; the
owner may redirect at any time.

## Definition of Done

`design_kit.py check` passes; every designed state has a matching inspected capture of the built
product; the last quality pass leaves no P0 or P1 open; and when a prototype or software is built,
every interaction's time budget has a measured time on a fast and a throttled network. A measure built on real data checks for and states which rows it drops or caps
(negative durations, open items, duplicates) and how many.

## Red flags

- A state in the matrix with no mockup.
- A screenshot taken but not inspected.
- Paid research that is not pre-authorized, done without asking.
- Accessibility left to "later".
- A time budget reported as met with no measurement, or an animation with no named job.
- A P0 or P1 friction, or a missed measured budget, deferred to make a date.
- A measure or term redefined after approval without a reason 1 stop.

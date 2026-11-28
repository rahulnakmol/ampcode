# UX and UI design mission

Designing how a person or an agent experiences something, from the need to a handoff and a check
of the built result, on any surface `crafting` covers: web, mobile, CLI, chat, email, print and
more. Playbook:
[`experience-design.md`](../../skills/missioning/reference/missions/experience-design.md).
[All missions](README.md).

## Use it when

- a flow, screen, conversation or dashboard needs design decisions, not a visual tweak;
- you want named directions, a mockup for every state and an accessibility check before build.

Not for a tweak that needs no design decision; use `crafting` on its own.

## Start it

```text
Use missioning to run an experience-design mission for [surface] so that
[people] can [need]. I decide. Success means [measures]. Pre-authorize none.
```

Before drafting, the agent asks you once for: the users' screens, zoom and assistive technology,
and brand rules and banned assets. You then approve, once, the need, the angle and the success
measures. The direction to take is an open question whose default is the one that best meets the
success criteria; you can redirect at any checkpoint.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| Kickoff | The need and the angle, when the request is vague | `grilling` |
| M1 Directions | Need, journeys and a touchpoint-by-state matrix; research within budget; named directions | `crafting` |
| M2 System and mockups | Experience system; a mockup or transcript for every state; quality pass (time budgets measured once a prototype runs); critic pass; `design_kit.py check` until the handoff gate passes | `crafting` |
| M3 Built-product comparison | When software is built, each built state captured, inspected and compared with its mockup; the quality pass rerun with every time budget measured | `delivering` (through a [software delivery](software-delivery.md) mission) |

`crafting` is the conductor. A design-QA lens is planned; until then the agent compares each
built state with its mockup at `delivering`'s second review gate and lists every difference.

## Gates you decide

- Kickoff (above).
- Publishing or sending designs outside the team, unless pre-authorized.

## Done when

`design_kit.py check` passes, every designed state has a matching inspected capture of the
built product, and the last quality pass leaves no serious friction open. When a prototype or
software is built, every interaction's time budget is measured on a fast and a slow connection. A measure built on real data states which rows it drops or caps, and how many.

## Example

**Mastodon sign-up redesign** (validation run 5a, scores 8/7/8). The proposed "Open house" flow
cut sign-up from 3 gates and 7 inputs to 2 gates and 3 inputs, found 4 high-priority
accessibility issues and delivered 12 artifacts; its kickoff brief took 8 revisions. In another
run, a 311 dashboard on NYC data (5b), the agent counted negative durations and open rows as
"closed within 7 days" and missed the need for 200% zoom on 1366×768 screens. Both lessons are now
in the playbook: the owner-facts round asks for screens and zoom, and the Definition of Done
requires dropped rows to be stated.

## Adapt it

Journeys, research, critique and the handoff check live in
[`crafting`](../../skills/crafting/SKILL.md).

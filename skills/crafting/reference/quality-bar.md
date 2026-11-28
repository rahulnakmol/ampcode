# The quality bar

Quality, intuitiveness, elegance, efficiency and reliability are checks here, not adjectives.
Each has a test you run on the rendered states, the prototype or the built product.

**What blocks.** A P0 or P1 finding, and a measured budget that is missed, block handoff (and, in
`delivering`, leave the item not done): fix them, or raise a stop when the fix is out of reach.
P2 and P3 findings are listed with their severity in `HANDOFF.md`. Polish is not deferred to make
a date; a team that ships later and polished beats one that ships half-baked on time.

**Where it applies.** Interactive surfaces: screens (`web`, `ios`, `android`, `macos`, `windows`),
terminals (`cli`, `tui`), ambient devices and conversation (`chat`, `voice`). For a voice or chat
touchpoint, the keyboard and pointer checks become turns: the pass walks the spoken or typed
turns, barge-in and recovery. For other surfaces (print, messaging, social, media, agent APIs)
the rubric's Efficiency and Speed dimensions are "N/A", and agent APIs use `agent-experience.md`.

**Sources.** Rows marked *(Linear)* come from Linear's design and engineering team in "Behind
The Scenes Of Linear's INSANE Design" (Enrico Tartarotti, 2026-11-25); the latency budget comes
from the same video's sponsor segment on Wispr Flow. Unmarked numbers and rows are this kit's
defaults. Take the discipline, not the look.

## The five checks

| Quality | The check | Recorded in |
| --- | --- | --- |
| **Intuitive** | A cold walkthrough by a fresh reader with no brief (the critic's "Feel" walk, `critic.md`) finishes the main task without guessing, and every applicable row of the [detail checklist](#interaction-details) behaves as listed. Recommend a human usability test of the moments of truth before launch | Rubric "Clarity"; critique file |
| **Efficient** | The main task's steps and keystrokes are counted and compared with the best reference, whose count is recorded with its source in `research/`; every frequent action has a keyboard path | Rubric "Efficiency"; `HANDOFF.md` |
| **Reliable** | Every interaction has a [budget](#performance-budgets) designed into the architecture and, once a prototype or the product runs, met as measured on a throttled network; no state loses typed input; failure keeps the last good data on screen | Rubric "Speed and reliability"; `HANDOFF.md` |
| **Elegant** | Colours follow the [derivation rule](#tokens-derived-not-picked); the [motion purpose test](#motion-purpose-test) passes; nothing on screen lacks a job | Rubric "Color", "Motion" and "Craft" |
| **Quality** | The [quality pass](#the-quality-pass) ran and nothing that blocks is open | `.design/quality-pass.md` |

## A point of view

An opinionated product makes the right way of working the easy way *(Linear)*. In `BRIEF.md`,
under the principles, write:

- **Easy**: what the product makes one step (the frequent, healthy action).
- **Harder on purpose**: what it keeps possible but demotes, and why. Linear keeps due dates in
  a submenu because dating everything is a poor way to prioritise.
- **One owner**: where a thing could have several owners, whether it has one and why (one
  assignee per issue, one lead per project).
- **Sized for its use**: inputs sized for the length the product wants. A small project-update
  box keeps updates short and comment-like.

Check each one in the mockups. A demoted option that sits on the first screen anyway is a P2.

## Interaction details

Apply each row whose trigger the design contains, and only those. Record each applicable row as
an entry in the touchpoint's `interactions` in `touchpoints.json`, with `"motion": "none"` and
`"reduced_motion": "none"` when it has no motion. A row that applies and fails is a P1 on a
moment of truth, otherwise a P2.

| Trigger | The detail |
| --- | --- |
| A menu or popover | It grows out of its trigger: the transform origin is the edge nearest the trigger, and the animation runs the way it opens (down and right opens down and right) *(Linear)* |
| A submenu | A safe triangle from the pointer to the submenu keeps it open while the pointer travels diagonally across sibling rows *(Linear)* |
| An icon-only control | It has a tooltip with its name and shortcut *(Linear)*. The first tooltip waits by how urgent the name is: about 1 s by default, shorter for icons people must identify at once. Once one is open, the next in the group shows at once *(Linear)*; the warm-up resets after about 1 s away |
| A picker, combobox or command menu | It opens with focus in the filter field, typing filters, and arrow keys move *(Linear)*; Enter picks, Esc closes and returns focus. A just-picked item stays in place until the menu reopens; then selected items group at the top *(Linear)* |
| A list that changes while used | Nothing moves under the pointer or the focus; a re-sort waits until the person is done |
| A frequent action | It has a keyboard shortcut, shown in its tooltip and menu entry *(Linear: keyboard-first)*. A product whose frequent actions do not fit one toolbar has a command menu (⌘K or Ctrl+K) that reaches them all |
| A control that changes state | Its icon or label reflects the state (a sidebar toggle that shows open or closed) *(Linear)*, and assistive technology can read it |
| A resizable or collapsible region | A hover hint shows it can be dragged *(Linear)*, and it has a keyboard path |
| A form | Focus starts in the first field; validation waits for blur or submit; an error keeps the input, moves focus to the field, and says how to fix it |
| An action that usually succeeds | It updates at once and rolls back with a message that names what failed |
| An agent or background change | See "Human and agent together" in `agent-experience.md` |

## Performance budgets

Perceived speed is mostly architecture: Linear's sync engine keeps the workspace on the device,
so views need no loading screen *(Linear)*. Give every interaction on an interactive surface a
`budget` in `touchpoints.json`: a number with a unit for the time from the input to the result
the person sees, the stages it splits into when it crosses the network, and the network it holds
on. `design_kit.py check` requires a number and unit (`100 ms`, `1 s`).

| Interaction | Default budget when the brief sets none |
| --- | --- |
| Feedback to a press, key or hover | 100 ms |
| Opening a menu, picker or tooltip (after its delay); filtering as you type | 100 ms |
| Moving to a view whose data is already loaded or cached | 100 ms, with no spinner and no skeleton |
| A view that needs the network | Shell and last-known data at once; fresh data within 1 s on a fast connection, and a stated time on a throttled one (for example "Fast 3G: 3 s") |
| A long job (an export, a search over a large range) | Progress within 1 s, with real numbers; the rest of the view stays usable |

These budgets take priority over the loading thresholds in `motion.md`, which then decide what a
view shows while it waits. Split a networked budget into stages, the way Wispr Flow split 700 ms
from key release to text into 200 ms for speech recognition, 200 ms for the clean-up model,
200 ms for the round trip and a buffer; the stage that breaks the budget is the one to change.

Meet budgets with the architecture, not with spinners: cache or keep data locally, render the
shell first, keep the previous content visible while refreshing, prefetch the likely next view,
and aggregate on the server. Before anything runs, a budget is a specification with its stages,
and the rubric scores Speed on that plan. Once a prototype or the product runs, measure each
budget (DevTools Performance panel, `performance.now()` marks, or a clip with timestamps) on a
fast and a throttled connection, and record the times next to the budgets in `HANDOFF.md`. A
budget nobody measured is "not measured", never "met".

## Motion purpose test

For every animation, name its job from the table in `motion.md`. Nothing moves at rest. During
an action, only the elements that carry its job move; if more moves, the interface becomes a
"Christmas tree" *(Linear)*, so remove the motion with the weakest job. Purposeful motion stands
out because little else moves: Linear animates the status column an issue is dragged into.

## Tokens derived, not picked

Derive the palette the design creates from a few inputs by a stated rule, so themes stay
balanced and pairs pass contrast by construction. Linear derives about 80 to 90 colours by math
from three inputs: accent, background and contrast *(Linear)*.

1. Name the inputs. Brand-supplied colours are inputs, kept exact.
2. Write the rule in `DESIGN.md`: for each token, the formula that derives it from the inputs in
   OKLCH (lightness steps from the background toward the text, the accent's chroma capped per
   step, the contrast input scaling the steps).
3. Check every text and UI pair against WCAG contrast for each theme the product offers (light
   and dark, and high contrast when the product has a contrast setting). For a themeable
   product, generate the tokens with a small script.
4. A colour in the mockups that is neither an input nor derived is a P2.

## Explore before converging

When a touchpoint has no reference that solves it (a new interaction model), build three to five
directions as working prototypes in its medium and use each for the main task before choosing:
Linear built five directions for its code review surface instead of choosing among Figma frames
*(Linear)*. Record what each attempt taught in `.design/research/explorations.md`. Other
touchpoints keep the two or three directions in `taste.md`; Inspire and Refine work never
prototypes directions.

## The quality pass

Use the product the way its people will, and write what you find in `.design/quality-pass.md`
*(Linear dogfoods the product and ran weekly quality sessions where every engineer shipped one
quality fix)*:

1. Walk the journeys on real data. Once a prototype or the product runs: by pointer and by
   keyboard only, at the main widths, on a fast and a throttled connection, measuring each
   budget. Before that: walk the mockups state by state for the detail checklist and count the
   main task's steps; mark the budgets "not measured".
2. Log each friction: where it happened, what you expected, and its severity from `taste.md`.
   Small things count: a lagging tooltip, an item that jumps, lost focus, an extra step.
3. Fix what blocks (above), and fix at least one smaller friction in each pass.
4. List what remains, with its severity, in `HANDOFF.md`.

In `delivering`, the pass covers the journeys the change touches, with the default budgets above
when the design set none. The pass finds friction by use; the critic pass still judges cold.

# The quality bar

Quality, intuitiveness, elegance, efficiency and reliability are checks here, not adjectives.
Each one has a test you run on the rendered states, the prototype or the built product. A design
that fails a check is not finished, even when it looks good. Ship later and polished rather than
on time and half-baked: a missed check is a finding, not a note for the next release.

Source of the practices: Linear's design and engineering team, in "Behind The Scenes Of Linear's
INSANE Design" (Enrico Tartarotti, 2026-11-25), and the dictation team's latency budget in the
same video. Take the discipline, not the look.

## The five checks

| Quality | The check | Where it is recorded |
| --- | --- | --- |
| **Intuitive** | A first-time user finishes the main task without help on the first try, and every interaction in the [detail checklist](#interaction-details) that applies behaves as listed | Rubric "Clarity"; quality pass log |
| **Efficient** | The main task's steps and keystrokes are counted, and the count is no higher than the best reference in research; every frequent action has a keyboard path | Rubric "Efficiency"; `HANDOFF.md` |
| **Reliable** | Every interaction meets its [budget](#performance-budgets) on a throttled network; no state loses typed input; failure states keep the last good data on screen | Rubric "Speed and reliability"; `HANDOFF.md` |
| **Elegant** | Colours come from the [derivation rule](#tokens-derived-not-picked); one signature motion; at most one element moves at rest; nothing on screen without a job | Rubric "Craft" and "Motion" |
| **Quality** | The [quality pass](#the-quality-pass) ran on real data and each friction it found is fixed or listed | `.design/critique/quality-pass.md` |

## A point of view

A product that people love is opinionated: it makes the right way of working the easy way. In
`BRIEF.md`, under the principles, write:

- **Easy**: what the product makes one step (the frequent, healthy action).
- **Harder on purpose**: what it keeps possible but demotes, and why (Linear keeps due dates in a
  submenu because dating everything is a poor way to prioritise).
- **One owner**: where a thing could have several owners or several of something, say whether
  it has one and why (one assignee per issue, one lead per project).
- **Sized for its use**: inputs are sized for the length the product wants (a small update box
  keeps updates short; a large box invites essays).

Check each one in the mockups. A demoted option that sits on the first screen anyway is a P2.

## Interaction details

Apply each row whose trigger the design contains. List the rows that apply under the
touchpoint's `interactions` in `touchpoints.json`. A row that applies and fails is a P1 when the
touchpoint is a moment of truth, otherwise a P2.

| Trigger | The detail |
| --- | --- |
| A menu or popover | It grows out of its trigger: the transform origin is the edge nearest the trigger, and the direction matches where it opens (down and right opens down and right) |
| A submenu | A safe triangle (pointer-intent area) from the pointer to the submenu keeps it open while the pointer travels diagonally across sibling rows |
| An icon-only control | It has a tooltip with the name and the shortcut. The first tooltip waits about 500 to 1000 ms; once one is open, the next one shows at once while the pointer moves across the group (warm-up), and the delay resets after about 1 s away |
| A picker, combobox or command menu | It opens with focus in the filter field; typing filters at once; arrow keys move, Enter picks, Esc closes and returns focus to the trigger. A just-picked item stays in place until the menu reopens; then selected items group at the top |
| A list that changes while used | Nothing moves under the pointer or the focus: new items appear without shifting the row being acted on, and a re-sort waits until the person is done |
| A frequent action | It has a keyboard shortcut, shown in its tooltip and menu entry. A product with more than about ten actions has a command menu (⌘K or Ctrl+K) that reaches all of them |
| A control that changes state | Its icon or label reflects the state (a sidebar toggle icon that shows open or closed), and the state is exposed to assistive technology |
| A resizable or collapsible region | A hover hint shows it can be dragged, it has a keyboard path, and it remembers its size |
| A form | Focus starts in the first field; validation waits for blur or submit, never fires on the first keystroke; an error keeps the input, moves focus to the field, and says how to fix it |
| An action that usually succeeds | It updates optimistically, at once, and rolls back with a message that names what failed |
| An agent or background change | See "Human and agent together" in `agent-experience.md` |

Write the details as micro-interaction specs with the template in `motion.md`. Do not copy a row
into a design where its trigger does not exist.

## Performance budgets

Speed is part of the design, and perceived speed is mostly architecture: a view that reads from
data already on the device needs no loading screen. Give every interaction in
`touchpoints.json` a `budget`: the time from the input to the result the person sees, with the
stages it is split into, and the network it holds on.

| Interaction | Default budget |
| --- | --- |
| Feedback to a press, key or hover | 100 ms |
| Opening a menu, tooltip (after its delay), or picker; filtering as you type | 100 ms |
| Moving to a view whose data is already loaded or cached | 100 ms, no spinner and no skeleton |
| A view that needs the network | Shell and last-known data at once; fresh data within 1 s on a fast connection, with a stated budget on a slow one (for example "Fast 3G: 3 s") |
| A long job (an export, a search over a large range) | Progress within 1 s, real numbers, and the rest of the view stays usable |

Split a budget into its stages when it crosses the network, the way the dictation team split
700 ms into 200 ms to recognise speech, 200 ms to clean it, 200 ms for the round trip and a
buffer. Then the stage that breaks the budget is the one to change.

Design for budgets with the architecture, not with spinners: cache or keep the data locally,
render the shell first, keep the previous content visible while refreshing, prefetch the likely
next view, and aggregate on the server. Measure each budget on the prototype or the built product
(DevTools Performance panel, `performance.now()` marks, or a recorded clip with timestamps), on a
fast connection and on a throttled one, and record the measured times next to the budgets in
`HANDOFF.md`. A budget with no measurement is "not measured", never "met".

## Motion purpose test

For every animation, name its job from the table in `motion.md`. Then look at each view at rest:
if more than one element moves, or a routine action animates more than its feedback, the view is
turning into a Christmas tree. Remove the motion whose job is weakest. Purposeful motion stands
out because little else moves: animate the drop target an issue is dragged into, not the sidebar.

## Tokens derived, not picked

Derive the palette from a few inputs by a stated rule, so every theme stays balanced and every
pair passes contrast by construction:

1. Choose the inputs: an accent, a background and a contrast level (Linear builds every theme
   from these three).
2. Write the rule in `DESIGN.md`: for each token, the formula that derives it from the inputs in
   OKLCH (lightness steps from the background toward the text, the accent's chroma capped per
   step, the contrast level scaling the steps).
3. Generate the tokens with a small script, and check every text and UI pair against WCAG
   contrast for light, dark and high-contrast inputs.
4. No colour in the mockups is outside the derived set. A hand-picked one-off value is a P2.

Spacing and type follow the same idea: one base unit and one scale.

## Explore before converging

For the hardest touchpoint (a new interaction model, a moment of truth no reference solves),
build three to five directions as working prototypes in the medium, not only static frames, and
use each for the main task with real data before choosing. Record what each attempt taught in
`.design/research/explorations.md`. Easier touchpoints keep the two or three directions in
`taste.md`.

## The quality pass

Before handoff, and again on the built product, use the product the way its people will:

1. Do every journey end to end on real data, once with the pointer and once by keyboard only,
   at the main widths, on a fast connection and on a throttled one.
2. Write each friction in `.design/critique/quality-pass.md`: where it happened, what you
   expected, and its severity from the rubric in `taste.md`. Small things count: a tooltip that
   lags, an item that jumps, a focus that is lost, an extra step.
3. Fix every P0 and P1, and fix at least one smaller friction in each pass, the way Linear's
   engineers ship one quality fix each week. Record the measured budgets.
4. List what remains, with its severity, in `HANDOFF.md`.

The quality pass does not replace the critic pass: the pass finds friction by using the product,
and the critic judges it cold.

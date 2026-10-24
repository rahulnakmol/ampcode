# Motion, micro-interactions, and complex rendering

Motion is how an interface explains cause and effect. Done well it is barely noticed: things
feel solid, responsive, and continuous. Done badly it is decoration that slows people down.

## Why something moves

Every animation must serve one of these jobs. If it serves none, remove it.

| Job | Example |
| --- | --- |
| **Feedback**: the system heard you | Button press depresses in under 100 ms; a toggle's thumb follows the finger |
| **Orientation**: where did it come from and go | A card expands into its detail view; a deleted row collapses toward its neighbors |
| **Continuity**: this is the same object | A thumbnail becomes the full image; a tab underline slides to the new tab |
| **Status**: something is happening | A progress hairline; a skeleton that matches the final layout |
| **Attention**: look here, once | A new item settles in; a validation error nudges once |
| **Delight**: a reward at a meaningful moment | A completion animation on finishing a goal; never on routine actions |

## Principles

1. **Responsive first.** Visual response to input within 100 ms, always. Animation never delays
   input: the user can act on the destination while it is still arriving.
2. **Interruptible and reversible.** Any animation can be grabbed, reversed, or replaced mid-flight
   without jumping. Springs do this naturally; fixed-duration tweens need care.
3. **Velocity preserved.** A gesture's release velocity becomes the animation's starting velocity.
4. **Physical, not mechanical.** Prefer springs for anything spatial. Use curves for opacity and
   color. Linear only for continuous loops such as spinners and progress.
5. **Hierarchy in time.** The most important element moves first or most; others follow with a
   small stagger (20 to 40 ms each, capped so a list finishes within about 300 ms total).
6. **Exits are quicker than entrances.** Leaving takes about two thirds of the arrival time.
7. **Distance and size scale duration.** Small, near movements are quick; large, far ones take
   longer. Springs give this automatically.
8. **Restraint.** One signature motion per product, used consistently, beats ten clever ones.
9. **Reduced motion is designed.** Replace movement with a cross-fade or an instant change;
   keep feedback. Never just disable feedback.

## Motion tokens

Define these in `DESIGN.md` and map them per platform. Values are starting points; tune by eye
in the prototype and record the final numbers.

| Token | Use | Web (duration, curve or spring) | SwiftUI | Compose | WinUI |
| --- | --- | --- | --- | --- | --- |
| `instant` | Press feedback, toggles, hover | 80 to 120 ms, ease-out | `.snappy(duration: 0.15)` | `spring(stiffness = Spring.StiffnessHigh)` | 83 ms, fast decelerate |
| `quick` | Small reveals, menus, tooltips | 150 to 200 ms, ease-out | `.snappy` | `spring(stiffness = Spring.StiffnessMedium)` | 167 ms |
| `standard` | Sheets, panels, page elements | 250 to 350 ms, spring | `.smooth` | theme `MotionScheme` default spatial spec | 250 to 333 ms |
| `emphasized` | Hero transitions, continuity | 400 to 500 ms, spring | `.spring(duration: 0.45, bounce: 0.15)` | `MotionScheme` slow spatial spec | `ConnectedAnimation` |
| `exit` | Dismissals | about two thirds of the entrance | `.smooth(duration: 0.25)` | faster spec | about two thirds |

Curves for non-spatial properties on the web: ease-out `cubic-bezier(0.2, 0, 0, 1)` for entering,
ease-in `cubic-bezier(0.3, 0, 1, 1)` for leaving. For spatial movement on the web, approximate a
spring with a generated `linear()` easing curve and its matching duration, or use a spring library.

Spring vocabulary to record for each token so every platform can reproduce it:

- **Response or duration**: how long the spring takes to mostly settle (0.15 to 0.5 s for UI).
- **Damping ratio or bounce**: 1.0 is critically damped, with no overshoot (default for chrome and
  productivity apps); 0.8 to 0.9 gives a slight, lively settle; below 0.7 is playful and rarely
  appropriate.
- Conversions: SwiftUI `bounce` ≈ 1 − damping ratio; Compose takes `dampingRatio` and `stiffness`;
  WinUI composition natural-motion springs take `DampingRatio` and `Period`.

## Micro-interaction spec template

Use Dan Saffer's structure. Write one entry per interaction in `touchpoints.json` (`interactions`)
and in `HANDOFF.md`.

```json
{
  "id": "save-draft",
  "trigger": "User presses Save (⌘S, button, or autosave after 2 s idle)",
  "rules": "Saves locally at once and syncs in the background; a conflict opens the merge sheet",
  "feedback": "Button label crossfades to 'Saved' for 1.2 s; status dot turns green; no toast",
  "loops_and_modes": "Autosave repeats on each idle; offline mode queues and shows 'Saved on this device'",
  "motion": "instant for the press; quick crossfade for the label",
  "haptics_and_sound": "None on desktop; .success sensory feedback on iOS only for manual saves",
  "reduced_motion": "Label swaps without crossfade; status dot still changes color",
  "agent_state": "aria-live polite 'Saved'; data-state=saved on the editor; CLI equivalent prints 'saved' and exits 0"
}
```

`design_kit.py check` requires `trigger`, `feedback`, `motion`, and `reduced_motion` on every
interaction.

## Patterns worth getting right

- **Press**: scale to 0.97 or darken within 80 ms on pointer down, not on release. Restore with a
  spring. Never animate layout on press.
- **Toggle and selection**: the thumb or indicator moves with the finger; state commits on
  release; selection haptic on iOS.
- **Lists**: inserted rows grow in height and fade in; deleted rows collapse; reordering lifts the
  row with a shadow and moves its neighbors with springs. Animate at most the visible rows.
- **Navigation**: push and pop follow the platform. Custom continuity (shared element, zoom) only
  where the object truly persists across screens.
- **Sheets and dialogs**: enter from their anchor, dim the background with opacity only, and dismiss
  by gesture with velocity.
- **Loading**: under 300 ms show nothing; under 2 s use a skeleton that matches the final layout
  exactly (no layout shift when content lands); longer, show progress with real numbers. Prefer
  optimistic updates with a clear rollback for actions that usually succeed.
- **Errors**: one horizontal nudge of about 4 to 6 px with a quick spring, never repeated; focus
  moves to the problem; the message stays.
- **Success**: brief and proportional. A checkmark draw-on for a payment; nothing for a routine save.
- **Numbers**: counters roll with tabular numerals so widths do not jitter.
- **Scroll**: scroll-linked effects only when they explain structure (a collapsing header), never
  scroll-jacking.

## Complex rendering

Interfaces that feel premium are often just fast. Budget it like a feature.

- **Frame budget**: 16.7 ms at 60 Hz and 8.3 ms at 120 Hz (ProMotion and high-refresh Android).
  Animate only compositor-friendly properties (transform and opacity on the web; layer
  properties natively). Never animate width, height, top, or left on the web.
- **Long lists and tables**: virtualize (`LazyVStack` or `List`, `LazyColumn`, `ItemsRepeater`,
  windowed rendering on the web). Keep row heights predictable, cache measurements, and diff
  updates rather than re-render.
- **Large data and charts**: canvas, WebGL or WebGPU, Metal, or Skia-backed drawing beyond a few
  thousand marks; aggregate before drawing; keep an accessible table or summary alongside.
- **Images**: reserve space with the aspect ratio, show a blurred or color placeholder, decode off
  the main thread, and serve sizes for the display density.
- **Text**: avoid layout thrash from web fonts (metric-matched fallbacks, `font-display`), use
  tabular numerals for changing numbers, and measure truncation with real localized strings.
- **Perceived performance**: render the shell immediately, stream content in priority order, keep
  previous content visible while refreshing, and prefetch the likely next view.
- **Verification**: profile the critical interactions (DevTools Performance panel, Instruments,
  Android Studio profilers, Windows Performance Analyzer) and record frame times in `HANDOFF.md`.

## Capturing motion for review

Static screenshots cannot show motion. For each important transition, capture either a short
recording or a frame strip at 0, 25, 50, 75, and 100 percent, and a separate capture with reduced
motion enabled. On the web, slow the animation (DevTools animation speed or a temporary global
multiplier) to capture intermediate frames, then restore it. Inspect each strip for jumps, layout
shift, overlapping elements, and late feedback.

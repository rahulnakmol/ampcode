# Taste, directions, and critique

Taste here means specific, deliberate choices that a skilled designer can defend, applied with
restraint and finished to the last pixel. It is not a style. A brutalist CLI and a soft
consumer app can both have it.

## What award-grade work has in common

Apple Design Awards judge Delight and Fun, Inclusivity, Innovation, Interaction, Social Impact,
and Visuals and Graphics. Winners across those categories share traits worth designing toward:

- **A single idea**, visible everywhere: the product's own material (its data, its domain, its
  verbs) becomes the visual language, not a borrowed template.
- **Native fluency**: they use the platform so well that the custom parts feel inevitable.
- **Completeness**: empty, error, and edge states are as considered as the hero.
- **Physical interaction**: direct manipulation, interruptible motion, honest feedback, haptics
  that mean something.
- **Inclusion by default**: Dynamic Type, VoiceOver, keyboard paths, contrast, and localization are
  part of the design, not a later pass.
- **Restraint**: one accent, one signature motion, few type sizes, and empty space used on purpose.

### Calibration reference: parallel.ai

The user named [parallel.ai](https://parallel.ai/) as the quality bar. Measured on 2026-10-24
(Firecrawl `branding` and a screenshot):

- Near-monochrome palette (text `#181818` on white) with one vivid accent (`#FB631B`) reserved for
  the primary action; a blue link color as the only other hue.
- One grotesque family (`gerstnerProgramm`) for text, a monospaced face for uppercase labels and
  buttons, and a 4 px spacing base and 4 px radius everywhere: no mixed rounding.
- Thin vertical rules framing the content column, like an engineering drawing.
- Keyboard-shortcut chips inside buttons (`LOG IN [P]`, `CONTACT [C]`): affordances for experts.
- A **Human / Machine** toggle on the hero: the same page served to people and to agents. This is
  the clearest example of designing for both audiences.
- One atmospheric photographic hero behind a calm, functional product demo instead of an
  illustration of the product.

Take the discipline (constraint, consistency, dual audience), not the look.

## Building the board

`.design/board/index.html` is one self-contained page (inline CSS; images downloaded into
`.design/research/img/` and credited), grouped by what to take from each reference. It is a point of
view that serves the chosen angle, not a pattern library:

- Lead with look and feel: about 40% of images come from outside the category (objects, print, type
  specimens, architecture, film, motion), shown large, with color fields and type set at specimen
  size beside them. UI and behaviour references go in a smaller strip after.
- Name the one specific detail worth stealing from each reference, never "nice vibe", and describe
  only what it actually shows.
- Every image, including anti-references, links to its source.
- Assumptions keep their label on the board.
- Each section gets its own readable capture, which you inspect.

## Proposing directions

Each direction is a hypothesis about what this product should feel like. Write it like this:

```markdown
### Direction B: "Ledger"
Idea: the app is a well-kept paper ledger; numbers are the hero and everything else steps back.
Expected answer it beats: the dark fintech dashboard with a gradient card and a big balance.
Type: Newsreader (text serif with tabular figures) for amounts at 34/28/17 pt; SF Pro for UI at the
  Dynamic Type defaults; one scale, five steps.
Grid: 4 pt base, 16 pt margins, amounts right-aligned on a shared column.
Palette: warm off-white and ink; one green accent, only for money that has arrived.
Motion: weighted and calm; critically damped springs; amounts roll with tabular digits.
Signature detail: a hairline rule that draws across when a transfer settles.
Refuses: gradients, cards inside cards, and celebrating spending.
Look anchor: <a ledger, type specimen, or object outside the category, with link>
Behaviour anchor: <a shipped product interaction, with link>
Lo-fi frame: one sketch on the target platform's real chrome (status bar, sheets, controls).
Risks: may feel old-fashioned to under-25s; mitigated by modern sans UI and fast motion.
```

Rules:

- Directions differ in idea, not just color. At least one is unexpected for the category, and
  "unexpected" is earned: check it against the category's obvious ideas (a mine/yours/ours Venn for
  couples' money is obvious) and replace it if it is one of them.
- Name the typefaces, the scale, and the grid. "A grotesk" is not a decision. Choose fonts the
  project can license and ship; for native apps prefer the system fonts unless the brand demands
  otherwise.
- Every direction has a look anchor (often outside the category: print, objects, places) and a
  behaviour anchor (a shipped interaction).
- For a place-specific audience, include real local texture beyond translating the place name:
  language and wit, landmarks, materials, rituals, or the way people there actually communicate.
- A borrowed metaphor keeps its meaning: if the direction borrows from software, sport, or
  paperwork, check that its interactions mean the same thing (in GitHub, a ticked box means done,
  not a vote).
- Label each direction's position (expected, adjacent, or unexpected) and name the category
  baseline the unexpected one beats.
- Every direction's lo-fi frame shows the same moment (the brief's top moment of truth), so they
  compare like for like; show the recommended one before and after its key action.
- An invite or consent frame always has a pressure-free exit ("Not now", "Decline"). A softer
  action in its place is not an exit.
- For an Inspire board, keep each direction card to the idea, type, palette and material, the
  signature detail, and the anchors; motion timings, grid, and risk tables wait for the system.
- Every choice traces to the brief or a reference.

## Critique rubric

Score each dimension from 1 to 10 on the rendered captures, never on the code. Ship bar: every
dimension at 8 or above and no P0 or P1 findings.

| Dimension | 10 looks like |
| --- | --- |
| **Typesetting** | No widows or orphans in display text, units on the numeral's baseline, no element touching a rule or edge, display lines fill their measure |
| **Need fit** | Serves the job, principles, and measures in the brief's Need section; the design-worthy bar is met |
| **Angle** | The chosen angle from the brief is visible in every state; a juror would call it a new take, not the category default done well |
| **Joy** | The tell-a-friend moment exists in a rendered state and is earned by the need (relief, competence, being understood); for agent surfaces, zero guesses |
| **Hierarchy** | One clear focal point per view; the eye path matches the job's order |
| **Clarity** | A first-time user knows what this is, what state it is in, and what to do next within five seconds |
| **Craft** | Alignment, spacing rhythm, optical balance, consistent radii and strokes; nothing off by a pixel |
| **Typography** | Few sizes with clear steps, comfortable measure and leading, correct numerals and punctuation |
| **Color** | Purposeful: accent has one job, state colors are consistent, contrast passes, both themes are designed |
| **Motion** | Purposeful, interruptible, on tokens, reduced-motion variant designed (see `motion.md`) |
| **States** | Every required and implied state designed with real content (see `states.md`) |
| **Medium fidelity** | Indistinguishable from the best work in its medium: the platform's best apps in controls, navigation, gestures, and materials; the best CLIs, conversations, notifications, and APIs in theirs |
| **Audience fit** | Matches the primary cohort's conventions, reading level, pace, and context, and meets its safety requirements (see `audiences.md`) |
| **Journey coherence** | The touchpoint hands off cleanly to the steps before and after it, across surfaces, with the same names and no dead ends |
| **Accessibility** | Meets the checklist in `accessibility.md` for this surface: names, focus, targets, contrast, scaling, captions, alt text |
| **Agent legibility** | An agent can read every state and perform every key action without guessing (see below) |
| **Distinctiveness** | Recognizably this product; would not be mistaken for a template |

Severity of findings:

- **P0**: blocks use or excludes people (missing label on a required field, contrast failure on
  body text, a state that strands the user, a broken keyboard path).
- **P1**: clearly wrong or confusing (competing focal points, inconsistent components, a missing
  state from the matrix, motion that blocks input).
- **P2**: craft issues a careful user notices (spacing drift, weak empty state copy, rough truncation).
- **P3**: polish (a 1 px misalignment, a slightly long transition).

## Slop scan

These are the defaults that make interfaces look machine-made. Each one found is at least a P2;
remove it unless the brief explicitly calls for it.

Visual:

- Purple-to-blue gradients, gradient text, glowing blobs, and "AI beige" (warm gray on cream with a
  muted accent) used as a default palette.
- Glassmorphism on everything; drop shadows on every card; cards inside cards inside cards.
- The three-card feature grid with an icon, a bold word, and one line each; numbered "01 / 02 / 03"
  process steps; bento grids without a reason.
- An italic serif word inside a sans headline as the only flourish; sparkle (✦) icons for AI;
  emoji as feature icons; a pulsing dot for "live" on static content.
- A colored left border on cards ("side-tab"); pill badges everywhere; random rounding (8, 12, 16,
  and 24 px radii on one screen).
- Gray text on gray backgrounds below contrast; tiny all-caps labels on everything; too many
  weights.
- Centered everything; uniform spacing with no rhythm; a hero that says nothing ("Build faster
  together").

Copy:

- "Seamless", "elevate", "unlock", "supercharge", "effortless", "Get started →" everywhere,
  invented metrics ("10x faster"), lorem ipsum, "John Doe", and "Something went wrong".

Interaction and motion:

- Bounce and overshoot on every element; fade-up on scroll for every section; parallax for
  nothing; spinners for anything under 300 ms; hover-only actions; toasts for routine success;
  modal dialogs for non-critical information.

Platform:

- Web patterns on native apps: hamburger menus on iOS, custom back buttons, Material components on
  iOS or Cupertino on Android, ignored safe areas.
- Desktop apps without menus, keyboard shortcuts, context menus, or proper title bars and materials.
- CLIs and TUIs with emoji noise, color without a `NO_COLOR` path, spinners in pipes, and prompts
  without flags.

## Agent legibility

For agent-facing surfaces (APIs, MCP tools, CLIs) and human-agent surfaces (chat, copilots), also
apply `agent-experience.md` and its AX slop list. Check every touchpoint against these. A failure
is at least a P1 when the brief names agents as users, otherwise a P2.

- **Readable**: every control has an accessible name that matches its visible label; icons have
  names; state is exposed (`aria-busy`, `aria-invalid`, `aria-expanded`, selected, checked; native
  accessibility traits and values; UI Automation properties on Windows).
- **Addressable**: each view, filter, tab, and modal state has a URL or deep link; reloading
  restores it.
- **Operable without the UI's eyes**: no hover-only, drag-only, long-press-only, or canvas-only
  action without an equivalent; keyboard paths exist.
- **Deterministic**: stable labels and structure across renders; no layout that reorders based on
  animation timing; confirmations name the object and the consequence.
- **Machine paths**: CLIs have `--json`, stable exit codes, and flags for every prompt; content
  pages have a text or Markdown view; native apps expose key actions as App Intents, Android app
  actions, or deep links; products with an API or MCP server keep parity for key actions.
- **Results are observable**: after an action, the UI states the outcome in text (not only color or
  motion) so an agent can confirm it.

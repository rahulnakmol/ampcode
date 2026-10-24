# Surfaces

Each platform has its own physics, type, navigation, and materials. A design that looks the same
everywhere is native nowhere. Share the brand (voice, accent, iconography, signature detail) and
the information architecture; let each platform own its controls, gestures, and motion.

For every surface below: the craft rules, the mockup medium, and how to verify it rendered. Check
current platform guidance through research (see `research.md`); version-specific APIs here are
starting points.

## Choosing the mockup medium

| Situation | Medium |
| --- | --- |
| The repository already has the app in that platform's stack | Build the states in the real code, behind previews or a sample route |
| Brief's destination is Figma | `figma.use_figma` with the platform's UI kit and the file's components and variables |
| Web, no destination fixed | A self-contained HTML prototype in `.design/mockups/<touchpoint>/` |
| Native, no code and no Figma | Figma, or a device-sized HTML mock clearly labelled as an approximation |
| CLI or TUI | Real terminal output captured from a script or a working prototype |
| Chat, voice | A rendered chat prototype for visual chat; a scripted transcript (with timing and audio notes) for voice |
| Notification | Rendered lock-screen, banner, and email mockups; the exact copy and payload |
| API, MCP | Example request and response transcripts (`.md` or `.json`), plus tool descriptions and schemas; see `agent-experience.md` |

Never present an approximation as the native result. Label it.

## CLI

Craft:

- Follow clig.dev. Human output by default, `--json` for machines, consistent nouns and verbs,
  `--help` with examples first, suggestions on typos, and a next-step hint after success.
- Output hierarchy with weight and dim, not a rainbow: one accent color, red only for errors,
  yellow only for warnings. Symbols (`✓`, `✗`, `!`, `→`) always paired with words.
- Respect `NO_COLOR`, `TERM=dumb`, and non-TTY output: no color, spinners, or cursor movement when
  piped; plain lines that `grep` can use. Stable exit codes, documented.
- Progress: nothing under 100 ms; a spinner with a verb under about 2 s; a progress bar with counts
  and an estimate beyond that; for parallel work, one line per task that settles in place.
- Errors say what happened, why, and the exact command to fix it. Never a stack trace by default.
- Prompts only on a TTY, each with a flag equivalent (`--yes`, `--name`), so agents never block.
- Destructive commands show the impact and require confirmation or `--force`.

Mockup and verification: write each state as a script that prints the exact output (or run the
prototype), then capture it. Prefer `vhs` (Charm) tapes for screenshots and GIFs at 80 and 120
columns; otherwise render with a terminal and screenshot it. Also capture `--json` output and the
piped (`| cat`) and `NO_COLOR=1` variants as text.

## TUI

Craft:

- Pick the stack the project uses: Bubble Tea and Lip Gloss (Go), Ratatui (Rust), Textual (Python),
  Ink (TypeScript).
- Layout in cells: design for 80×24 first, then 120×40 and resize. Truncate with an ellipsis in the
  middle for paths and at the end for prose. Never wrap a table row.
- Keyboard first: visible focus, a footer of the three to five most useful keys, `?` for all keys,
  `q` or `Esc` to back out, `/` to filter, vim keys as an alternative and not the only way. Mouse
  support as a bonus.
- Color: design in 16 ANSI colors first so user themes apply, then enhance for 256 and truecolor.
  Check light and dark terminal backgrounds. Box-drawing lines in a dim tone; one accent.
- Motion: redraw only what changed, cap animation at about 30 to 60 fps, spring-based movement
  (Harmonica) for panes and cursors sparingly, spinners at about 80 to 120 ms per frame. No flicker:
  use the alternate screen and synchronized output where supported.

Mockup and verification: run the prototype in a pseudo-terminal and capture it with `vhs` at 80×24
and 120×40, in a light and a dark theme, with `NO_COLOR=1`, and with focus on each region.

## Web

Craft:

- Start from content and the register (persuade, operate, read, experience). Grid, type scale,
  and density follow from it. Operating surfaces are quiet: color on data and state, not chrome.
- Typography: at most two families, a scale with clear steps, 45 to 75 characters per line for
  prose, tabular numerals for data, real quotes and dashes, `text-wrap: balance` for headings.
- Responsive by intent: design at 390, 768, and 1440 pixels wide; check 320 and 1920. Layout changes
  at content breakpoints, not device names. Touch targets at least 44×44 pixels on touch.
- Color in OKLCH with light and dark themes from the start; contrast 4.5:1 for text, 3:1 for UI.
- Focus states designed, not default. Full keyboard paths. Hover is enhancement only.
- Motion via CSS transitions and `linear()` springs, the Web Animations API, and View Transitions
  where Baseline support allows; check support at the time of design.
- Agent legibility: semantic HTML, accessible names, ARIA state attributes, URLs for every view
  and filter, and a text or Markdown alternative for content-heavy pages.

Mockup and verification: a self-contained HTML file per touchpoint with a state switcher (query
parameter such as `?state=empty`) so every state renders by URL. Capture with the available browser
tooling (`agent-browser`, Chrome DevTools MCP, or Playwright) at the three widths, light and dark,
with `prefers-reduced-motion` emulated, and with keyboard focus visible. Check the accessibility tree
for names and states.

## iOS and iPadOS

Craft:

- SwiftUI-native structure: `NavigationStack`, `TabView`, sheets with detents, `List` and `Form`
  for settings, toolbars, context menus, swipe actions, and the system share sheet. No hamburger
  menus or custom back buttons.
- Typography with Dynamic Type text styles (SF Pro by default); check accessibility sizes up to
  AX5. Use the system's semantic colors and materials, and the current design language's controls
  (verify in research; for example Liquid Glass since iOS 26).
- Respect safe areas, the Dynamic Island, the home indicator, and keyboard avoidance. Thumb reach:
  primary actions at the bottom on iPhone.
- Motion with springs (`.smooth`, `.snappy`, `.bouncy`, or `.spring(duration:bounce:)`), matched
  geometry and zoom transitions for continuity, `.sensoryFeedback` for haptics tied to meaning
  (success, warning, selection). Gestures are interruptible and keep velocity.
- iPad: sidebar layouts, pointer hover effects, keyboard shortcuts, multiple windows, drag and drop.
- Agents and automation: accessibility labels, values, and traits on every control; App Intents
  for key actions so Siri, Shortcuts, and agents can act without the UI.

Mockup and verification: in a code destination, one `#Preview` per state and variant, rendered
with Xcode previews or an `ImageRenderer` snapshot script, or with snapshot tests if the project has
them. Otherwise build Figma frames with Apple's official UI kit. Check light and dark, the smallest
and largest Dynamic Type sizes, and iPhone SE and Pro Max sizes.

## macOS

Craft:

- A Mac app is keyboard- and menu-driven: every command in the menu bar with a shortcut, standard
  shortcuts honored (⌘, for Settings, ⌘F, ⌘Z), and a full keyboard path through the window.
- Structure: `NavigationSplitView` sidebars, unified toolbars, inspectors, a `Settings` scene,
  multiple windows and tabs, drag and drop, Quick Look, services, and the menu bar extra where it
  fits. Windows remember size and position.
- Density is higher than iOS: 13-point body text, compact controls, hover states, and right-click
  menus everywhere content is selectable.
- Materials and vibrancy from the system (sidebar, window background, the current glass treatment);
  do not paint your own translucency.
- Motion is quieter than iOS: short, critically damped springs; no bouncing chrome. Trackpad haptics
  (`NSHapticFeedbackManager`) only for alignment and snapping.

Mockup and verification: SwiftUI previews or a running build captured with `screencapture`, or
Figma with Apple's macOS kit. Check light, dark, a narrow window, full screen, and with the sidebar
collapsed. Check keyboard focus rings.

## Android

Craft:

- Jetpack Compose with Material 3, adopting Material 3 Expressive where the brand allows (verify the
  current guidance). Use color roles from a dynamic or brand color scheme instead of raw hex values,
  and the Material type scale.
- Edge-to-edge layouts with correct insets, predictive back with its preview animation, top app
  bars that collapse with scroll, a navigation bar or rail by window size class, and a floating
  action button only for the primary action.
- Design for window size classes (compact, medium, expanded), foldables, and tablets.
- Motion with Compose springs (`spring(dampingRatio, stiffness)`) or the theme's `MotionScheme`;
  shared element transitions for continuity. Haptics with `HapticFeedbackConstants`, sparingly.
- Agents and automation: `contentDescription` and semantics on every control; app actions and deep
  links for key tasks.

Mockup and verification: one `@Preview` per state with `uiMode` light and dark and font scale 1.0
and 2.0, rendered by the project's screenshot tests (Paparazzi or Roborazzi) if present. Otherwise
Figma with the Material 3 kit. Check compact and expanded widths.

## Windows (WinUI 3)

Craft:

- Fluent 2 and WinUI 3 controls: `NavigationView` (left or top), `TabView`, `CommandBar`,
  `InfoBar`, `TeachingTip`, `ContentDialog`. Segoe UI Variable type ramp, Segoe Fluent Icons.
- Mica for the window background and Acrylic for transient surfaces; a custom title bar that keeps
  the caption buttons, drag regions, and the system menu. Respect light, dark, and high-contrast
  themes and the user's accent color.
- Keyboard and accessibility: access keys (Alt shortcuts), keyboard accelerators, logical tab order,
  visible focus visuals, and UI Automation names on everything (agents and assistive technology use
  UIA).
- Motion from the platform: built-in theme transitions, `ConnectedAnimation` for continuity, and
  composition springs for custom movement. Fluent motion is quick and decelerating, never bouncy on
  chrome.
- Snap layouts, resizing down to small widths, and pen and touch where the app supports them.

Mockup and verification: if a Windows build machine or VM is available, run the app and capture
screenshots; on macOS without one, build Figma frames from the Fluent 2 kit and label them as
mockups. Check light, dark, high contrast, a narrow window, and text scaling at 200%.

## Chat (`chat`)

Craft:

- The conversation is the layout: clear turn boundaries, the person's messages compact, the
  assistant's answers structured (headings, lists, tables, code) when longer than a few lines.
- Streaming without jank: reserve space, keep the scroll anchored to the reading position, and
  render Markdown incrementally without reflowing earlier content.
- Visible work: status line for what the agent is doing, expandable tool calls and sources, and
  citations inline. Stop and edit controls always within reach.
- Input: a composer that grows, attachments and voice input where the job needs them, keyboard
  send and newline conventions of the platform, and starters on the empty state that teach what the
  product can do.
- Rich responses (cards, forms, charts) only when they beat text, and each with a text equivalent.

Mockup and verification: a prototype that replays a scripted conversation per state (`?state=streaming`),
captured mid-stream and settled, light and dark, narrow and wide. See `agent-experience.md` for
the human-agent states.

## Voice (`voice`)

Craft:

- Write for the ear: short sentences, the most important word last, numbers and dates spoken
  naturally, one question at a time, and a limit of about three options per turn.
- Turn-taking: fast acknowledgment (under about a second), barge-in so people can interrupt, and
  confirmation proportional to risk (implicit for low risk, explicit for money or deletion).
- Recovery: re-prompts that add help rather than repeat (`no-match`, `no-input`), and an exit to a
  screen or a person.
- Multimodal: when a screen exists, show what was heard and the result; voice and touch stay in sync.

Mockup and verification: a transcript per state with turn timing, prosody notes, and the screen
state alongside; if a TTS tool is available, render audio for the key turns and listen.

## Notifications (`notification`)

Craft:

- Every notification earns its interruption: a person would want it now. Default to fewer;
  let people tune categories and timing; respect quiet hours and platform focus modes.
- The first line carries the whole message (it is often all anyone reads); then the detail; then one
  or two actions that work from the notification itself.
- Group related notifications; update in place instead of stacking (a delivery's progress is one
  notification, not five); remove them when they no longer apply.
- Channels fit urgency: in-app for context, push for time-sensitive, email for records and digests,
  and SMS only when the person chose it.
- Deep links land exactly on the object, in the right state.

Mockup and verification: render each state on the lock screen, as a banner, in the notification
center group, and as the email (light and dark clients). Check truncation at real lengths.

## API and MCP (`api`, `mcp`)

The interface is names, schemas, descriptions, outputs, and errors. Follow `agent-experience.md`.
Mock each state as a transcript: the call, the response, and what the consumer (agent or developer)
does next.

## Cross-surface consistency

Keep these identical across platforms: names of things, information architecture, the accent's job,
iconography metaphors, tone of copy, and the signature detail. Let these differ: controls,
navigation patterns, type families, motion physics, density, and materials. Record both lists in
`DESIGN.md`.

# Screen surfaces: web, iOS, Android, macOS, Windows

Each platform has its own physics, type, navigation, and materials. A design that looks the same
everywhere is native nowhere. Share the brand (voice, accent, iconography, signature detail) and
the information architecture; let each platform own its controls, gestures, and motion. Check
current platform guidance through research; version-specific APIs here are starting points.

## Web (`web`)

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

## iOS and iPadOS (`ios`)

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

## macOS (`macos`)

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

## Android (`android`)

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

## Windows, WinUI 3 (`windows`)

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

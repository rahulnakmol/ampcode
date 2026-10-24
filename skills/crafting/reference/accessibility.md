# Accessibility

Accessibility is design quality for everyone who is not the designer: people who are blind or have
low vision, who are deaf or hard of hearing, who have motor, cognitive, or speech disabilities, who
are older, tired, distracted, holding a baby, in sunlight, or reading in their second language. It
is also the layer agents read. Design it in from the brief; audit it before handoff.

## Standards and law

- **Target WCAG 2.2 level AA** by default (the user can raise it). Know the newer criteria:
  focus not obscured, dragging alternatives, target size (minimum 24×24 CSS pixels), consistent help,
  redundant entry, and accessible authentication.
- Laws reference these standards: for example the ADA and Section 508 in the US, the European
  Accessibility Act (applying to many consumer products and services in the EU since June 2025) with
  EN 301 549, and national equivalents. Confirm which apply for the markets in the brief.
- Platform guidance adds detail: Apple, Android, and Windows accessibility guidelines; children's
  design rules in `audiences.md`.

## Design checklist

Apply these while designing, on every surface:

**Perceivable**
- Text contrast at least 4.5:1 (3:1 for large text), UI and graphics 3:1, in both themes and every
  state (including disabled, placeholder, and focus).
- Never color alone for meaning; pair with text, shape, or icons.
- Text alternatives: alt text for meaningful images, empty alt for decorative ones; captions and
  transcripts for audio and video; audio description for informative video.
- Text scales: web reflows at 320 CSS pixels and 400% zoom; native supports the largest Dynamic Type
  and font scale sizes without truncating meaning.

**Operable**
- Everything works by keyboard, switch, and voice control, with a visible focus indicator and a
  logical focus order. No keyboard traps.
- Targets at least 24×24 CSS pixels on the web (44 pt on iOS and 48 dp on Android recommended), with
  spacing.
- Alternatives for gestures: no action that needs a path-based gesture, multi-finger gesture,
  drag, or shake without a simple alternative.
- Time limits can be extended; motion can be paused or reduced; no flashing above three per second.

**Understandable**
- Plain language at the audience's reading level; labels and instructions visible, not only in
  placeholders; errors named and explained at the field with a suggested fix.
- Consistent navigation, naming, and help location; no unexpected context changes on focus or input.
- Cognitive load kept low: one task per step, progress shown, input remembered, and no puzzles for
  authentication.

**Robust**
- Semantic structure and native controls first; custom controls expose role, name, state, and value
  to the platform's accessibility API (ARIA on the web, accessibility traits and labels natively,
  UI Automation on Windows).
- Status messages announced (live regions, accessibility notifications) without moving focus.

## Per-surface notes

| Surface | What to check beyond the checklist |
| --- | --- |
| Web | Headings and landmarks, form labels, skip link, focus after route changes and dialogs, live regions |
| iOS, macOS | VoiceOver labels, traits, rotor navigation, Dynamic Type, Reduce Motion, Increase Contrast, Full Keyboard Access |
| Android | TalkBack labels and grouping, font scale 200%, touch targets, switch access |
| Windows | Narrator, UI Automation names, high-contrast themes, text scaling, keyboard accelerators |
| CLI, TUI | Screen reader output in a terminal (no box art or animated spinners read aloud), `NO_COLOR`, no meaning in color |
| Chat, voice | Streaming announced sensibly; alternatives for speech input and output; time to respond |
| Watch, TV, car, spatial, kiosk | Platform screen readers, focus visibility at distance, reach ranges, audio alternatives |
| Email, documents, print | Tagged PDF and reading order, real text over images, large-print versions, contrast on real stock |
| Social, video | Alt text, captions, CamelCase hashtags, audio description, no flashing |

## Audit method

Use this when the entry point is an accessibility audit, and on every Craft deliverable before
handoff:

1. **Scope**: list the touchpoints and states to audit, the standard and level, and the assistive
   technologies to test (at least one screen reader per platform in scope).
2. **Automated scan**: axe-core (for example through Playwright or the available browser tooling),
   Lighthouse, the Xcode Accessibility Inspector, Android's Accessibility Scanner, and Accessibility
   Insights for Windows, as available. Automated tools catch only part of the issues; never stop here.
3. **Manual checks**: keyboard-only walk of every journey; screen reader walk of every journey
   (VoiceOver, TalkBack, NVDA or Narrator); zoom to 400% and largest text size; Reduce Motion and
   high contrast; color-blindness simulation; read the copy for plain language.
4. **Assistive-technology scripts**: for each journey, write the expected announcements and focus
   moves, then compare with what actually happened.
5. **Record findings** in `.design/research/accessibility-audit.md`: WCAG criterion (number and name),
   touchpoint and state, what happens, who is affected, severity (P0 blocks a task for some users, P1
   major barrier, P2 friction, P3 best practice), fix, and evidence (screenshot or transcript).
6. **Fix and retest** P0 and P1 findings, and list the rest in `HANDOFF.md`.

## Accessibility slop

- Focus outlines removed for looks; placeholder-only labels; icon buttons without names.
- Gray-on-gray text; disabled buttons as the only hint that a form is invalid.
- `div` buttons, custom dropdowns without roles, ARIA added on top of native semantics.
- Carousels that auto-advance; animations that cannot be stopped; captchas without alternatives.
- "Accessible version" pages instead of an accessible product.

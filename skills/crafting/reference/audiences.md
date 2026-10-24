# Audiences: Gen Alpha to Millennials

Generations are priors, not personas. They describe what a cohort grew up with, which shapes the
conventions people expect and the frictions they tolerate. They do not tell you what one person
needs. Use this file to form hypotheses, then confirm them for this product with research (Mobbin
screens of apps this audience already loves, reviews, studies) and, when possible, real users.
Context (on a phone in a hallway or at a desk), ability, culture, and expertise usually beat age.

## Who is who (as of 2026)

| Cohort | Birth years | Ages in 2026 | Grew up with |
| --- | --- | --- | --- |
| **Gen Alpha** | 2010 to 2024 (McCrindle) | about 2 to 16 | Tablets before reading, voice assistants, YouTube and short video, Roblox and Minecraft, generative AI as a normal tool |
| **Gen Z** | 1997 to 2012 (Pew) | about 14 to 29 | Smartphones and social feeds as teenagers, vertical video, group chats, creator culture, dark mode |
| **Millennials** | 1981 to 1996 (Pew) | about 30 to 45 | The shift from desktop web to mobile, the early social web, app stores, subscriptions; now running households and teams |

Definitions overlap (Pew ends Gen Z in 2012; McCrindle starts Gen Alpha in 2010). Say which you use.

## Gen Alpha (children and young teens)

Design hypotheses:

- **Touch and voice before text.** Many use the product before they read fluently. Pair every
  word with an icon or picture, offer voice input and read-aloud, and keep reading level low (check
  it). Large targets (well above 44 pt) and forgiving gestures for developing motor control.
- **Play as the interface.** Expect direct manipulation, immediate feedback, characters, sound, and
  progress they can see. Motion and sound can be richer than for adults, but always with a mute,
  and never as a lure.
- **Creation over consumption.** Builders, editors, avatars, and remixing (the Minecraft and Roblox
  mental model) engage more than feeds.
- **AI-native but not AI-literate.** They talk to assistants naturally and trust them too easily.
  Make it obvious when something is AI, what it can be wrong about, and when to ask an adult.
- **Two users at once.** The child uses it; a parent or teacher buys, configures, and oversees it.
  Design both journeys, with a parent area that a child cannot stumble into.

Hard requirements, which override engagement goals. Verify the current rules by research for the
markets in the brief:

- Children's privacy and safety law applies: in the US COPPA (children under 13; the FTC amended the
  rule in 2025), in the UK the Age Appropriate Design Code (under 18), and in the EU the Digital
  Services Act Article 28 and the Commission's July 2025 guidelines on protecting minors, plus
  GDPR's parental consent age (13 to 16 by country). Bring legal review in early.
- High privacy by default: minimal data, no behavioral advertising, location off, profiles private.
- No manipulative patterns: no streak pressure, loot-box mechanics, infinite feeds, autoplay chains,
  fake urgency, or rewards for time spent. Natural stopping points and time awareness instead.
- Safe social features: no contact from strangers by default, easy and visible reporting and
  blocking, and moderation designed into every user-generated content surface.
- Age assurance that fits the risk, with the least intrusive method that works.

## Gen Z (teens and young adults)

Design hypotheses:

- **Mobile first, often mobile only.** Thumb-zone layouts, vertical media, gestures they know from
  social apps (swipe between items, long-press for options, pull to refresh), and fast cold starts.
- **Low friction tolerance.** Sign in with a passkey or an existing account, try before you sign
  up, no forms longer than needed, no phone calls. A slow or confusing first minute is a lost user.
- **Expression and identity.** Personalization (themes, app icons, avatars, profile flair), dark mode
  as a default, and shareable moments designed as real artifacts (a well-composed share card, not a
  screenshot of the UI).
- **Authenticity over polish theatre.** Direct, plain, slightly playful copy; no corporate voice and
  no forced slang. Social proof from real people. Transparent pricing.
- **Chat as the default way to communicate.** Messaging patterns (reactions, quick replies, voice
  notes) feel natural; so do AI assistants, but they expect them to be fast and honest.
- **Captions and sound-off by default** for any video; many watch without sound in public.
- **Values and wellbeing.** Privacy controls they can find, easy account deletion, and visible
  choices about data. Younger Gen Z are still minors: the Gen Alpha requirements apply to them.

## Millennials (adults managing life and work)

Design hypotheses:

- **Efficiency and control.** They want to get the job done: clear information architecture, search
  that works, keyboard shortcuts on desktop, bulk actions, and no forced tutorials.
- **Cross-device continuity.** Start on the phone, finish on the laptop. Sync, handoff, and the same
  names for things everywhere.
- **Trust signals.** Clear pricing and cancellation, security cues, reviews, and receipts. They
  remember the early web's dark patterns and punish them.
- **Life admin.** Money, family, health, home, and work tools for people with little time and
  several roles. Design for interruption: save progress and resume easily.
- **Accessibility needs grow.** Presbyopia starts in the early forties: larger default text options,
  good contrast, and respect for system text size matter more each year.
- **Familiar conventions with craft.** Fewer novel gestures, more polish on known patterns. Nostalgia
  can be a delightful accent, not a theme.

## Designing across cohorts

Most products serve several cohorts. Do not average them. Instead:

- Pick a **primary cohort and context** in the brief, and make the core journey excellent for them.
- Use **progressive disclosure** so playful or expressive layers do not slow down task-focused users,
  and power features do not overwhelm newcomers.
- Let people **choose their mode**: themes, density, motion and sound levels, text size, and
  notification intensity.
- Keep **one system** with tunable dials (density, motion amplitude, copy tone), not separate
  products, unless the audience is children, where a separate experience is often required.

## Research prompts

Use these as Parallel Search objectives or the core of one Parallel Task deep research run. Add the
product category and markets:

- "Which apps in <category> do <cohort> users rate highest, and which specific interaction details
  do reviews and studies credit?"
- "Recent studies (last two years) of how <cohort> users experience onboarding, sign-in, and
  pricing in <category> apps."
- "Current legal and regulatory requirements for designing <product type> used by children aged
  <range> in <markets>."

Mobbin queries: name apps the cohort already uses (for example "Duolingo lesson complete screen",
"BeReal camera screen"), then take the mechanism, not the look.

## In the critique

Add **Audience fit** to the rubric scores: does each touchpoint match the primary cohort's
conventions, reading level, pace, and context, and does it respect the requirements above? For
any product a minor might use, a manipulative pattern or a privacy default that is not high is a P0.

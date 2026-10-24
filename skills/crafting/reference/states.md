# Journeys, touchpoints, and states

A touchpoint is any moment where the product meets a person or an agent: a screen, a command, a
dialog, a chat turn, a voice prompt, a notification, an email, an API response, an MCP tool call, an
error page. Polished products feel polished because their unglamorous states were designed as
carefully as the hero shot, and because the journey holds together across all of them.

## Journeys first

Before listing screens, map each important journey end to end, across every surface it crosses
and every actor in it. A journey names its actor (a cohort from `audiences.md`, a role, or an agent),
the goal, the ordered touchpoints, and the moments of truth: the two or three steps where the
experience is won or lost (first value, the first error, paying, getting help).

Include touchpoints outside the product's main surface: the store listing, the sign-up email, the
push notification that brings someone back, the docs page, the support reply, the agent's tool call
that does the job without any screen, and the receipt.

## The matrix

`.design/touchpoints.json` is the source of truth. `design_kit.py init` creates it; you fill it in.

```json
{
  "journeys": [
    {
      "id": "send-money",
      "actor": "Gen Z first-time user, on a phone between classes",
      "goal": "Pay a friend back in under a minute",
      "steps": ["transfer-status"],
      "moments_of_truth": ["The transfer is pending and the friend asks if it arrived"]
    }
  ],
  "touchpoints": [
    {
      "id": "transfer-status",
      "surface": "ios",
      "job": "Know whether my money arrived, and what to do if it did not",
      "states": {
        "ideal": { "mockup": "mockups/transfer-status/ideal.png", "notes": "Arrived; amount and time" },
        "empty": { "skip": "A status screen always has a transfer" },
        "loading": { "mockup": "mockups/transfer-status/loading.png" },
        "error": { "mockup": "mockups/transfer-status/error.png", "notes": "Failed; reason and retry" },
        "offline": { "mockup": "mockups/transfer-status/offline.png" },
        "large-text": { "mockup": "mockups/transfer-status/large-text.png" },
        "dark": { "mockup": "mockups/transfer-status/dark.png" },
        "pending": { "mockup": "mockups/transfer-status/pending.png", "notes": "May still fail; expected time" }
      },
      "interactions": [
        {
          "id": "pull-to-refresh",
          "trigger": "Pull down on the status card",
          "feedback": "Card stretches with resistance; status re-checks; time stamp updates",
          "motion": "standard spring, no overshoot",
          "reduced_motion": "No stretch; spinner in the toolbar"
        }
      ]
    }
  ]
}
```

Mockup paths are relative to `.design/`. For non-visual surfaces (voice, API, MCP, and CLI `json`), the
mockup is a transcript file (`.md` or `.json`) with the exact input, output, and timing. Every journey
step must name a touchpoint `id` in the file. A state is covered when its mockup file exists or when it
has a `skip` reason. Add any extra states the job implies (like `pending` above); `check` validates
every state you list, not only the required ones.

## Required states by surface

`design_kit.py check` enforces these. They are the floor, not the ceiling. Interactive surfaces
share the core states `ideal`, `empty`, `loading`, and `error`. Static media (messages, print,
social, video, documents) have no loading moment, so their required "states" are the variants that
must be designed and checked. Each family's craft rules are in the file listed below the table.

| Family | Surface | Required states |
| --- | --- | --- |
| Terminal | `cli` | `ideal`, `empty`, `loading`, `error`, `non-tty`, `no-color`, `json` |
| Terminal | `tui` | `ideal`, `empty`, `loading`, `error`, `narrow-terminal`, `no-color`, `keyboard-focus` |
| Screens | `web` | `ideal`, `empty`, `loading`, `error`, `keyboard-focus`, `narrow`, `dark` |
| Screens | `ios` | `ideal`, `empty`, `loading`, `error`, `offline`, `large-text`, `dark` |
| Screens | `android` | `ideal`, `empty`, `loading`, `error`, `offline`, `large-text`, `dark` |
| Screens | `macos` | `ideal`, `empty`, `loading`, `error`, `keyboard-focus`, `narrow-window`, `dark` |
| Screens | `windows` | `ideal`, `empty`, `loading`, `error`, `keyboard-focus`, `narrow-window`, `dark` |
| Ambient | `watch` | `ideal`, `empty`, `loading`, `error`, `glance`, `always-on`, `large-text` |
| Ambient | `tv` | `ideal`, `empty`, `loading`, `error`, `focus`, `safe-area`, `large-text` |
| Ambient | `car` | `ideal`, `empty`, `loading`, `error`, `driving`, `night`, `voice-only` |
| Ambient | `spatial` | `ideal`, `empty`, `loading`, `error`, `gaze-focus`, `immersive`, `large-text` |
| Ambient | `kiosk` | `ideal`, `empty`, `loading`, `error`, `idle`, `timeout`, `reach-range` |
| Ambient | `device` | `ideal`, `empty`, `loading`, `error`, `setup`, `offline`, `firmware-update` |
| Conversation | `chat` | `ideal`, `empty`, `loading`, `error`, `streaming`, `tool-call`, `interrupted` |
| Conversation | `voice` | `ideal`, `empty`, `loading`, `error`, `no-match`, `no-input`, `barge-in` |
| Messaging | `notification` | `ideal`, `grouped`, `actioned`, `dark` |
| Messaging | `email` | `ideal`, `dark`, `images-off`, `narrow`, `plain-text` |
| Messaging | `sms` | `ideal`, `long-message`, `opt-out` |
| Agents | `api` | `ideal`, `empty`, `loading`, `error`, `validation-error`, `rate-limited`, `auth-error` |
| Agents | `mcp` | `ideal`, `empty`, `loading`, `error`, `validation-error`, `auth-error`, `large-result` |
| Agents | `a2a` | `ideal`, `empty`, `loading`, `error`, `input-required`, `cancelled`, `auth-error` |
| Agents | `webhook` | `ideal`, `retry`, `signature-failure`, `replay` |
| Agents | `agent-docs` | `ideal`, `ambiguity`, `outdated` |
| Social | `social` | `ideal`, `square`, `vertical`, `link-preview`, `sound-off`, `safe-zone` |
| Physical | `print` | `ideal`, `bleed`, `grayscale`, `long-copy`, `preflight` |
| Physical | `packaging` | `ideal`, `dieline`, `shelf-distance`, `regulatory-panel`, `preflight` |
| Physical | `signage` | `ideal`, `viewing-distance`, `low-light`, `sequence`, `tactile` |
| Media | `presentation` | `ideal`, `projector`, `handout`, `speaker-notes` |
| Media | `video` | `ideal`, `sound-off`, `vertical`, `thumbnail` |
| Media | `document` | `ideal`, `print`, `screen-reader`, `long-content` |
| Media | `dataviz` | `ideal`, `empty`, `loading`, `error`, `color-blind`, `dense`, `table-alternative` |

Families map to files: Terminal `surfaces/terminal.md`, Screens `surfaces/screens.md`, Ambient
`surfaces/ambient.md`, Conversation `surfaces/conversation.md`, Messaging `surfaces/messaging.md`,
Agents `agent-experience.md`, Social `surfaces/social.md`, Physical `surfaces/print.md`, and Media
`surfaces/media.md`.

For `cli`, `ideal` is the successful run, `empty` is "nothing to do or no results", and `loading`
is progress output. For `api`, `mcp`, and `a2a`, `loading` is the accepted-and-in-progress response.
A state that cannot occur on a touchpoint gets a `skip` reason.

Every non-skipped `social` state also needs a non-empty `"alt"` (the alt text that ships with that
asset) and `"copy"` (the words that go out with it: the caption, the forward message for a square,
the overlay or sticker text for a story, the title and description for a link preview). `check`
reports a gap when either is missing, so every asset that can be posted or forwarded alone carries
both, not only the carousel.

## State catalog

Walk this list for every touchpoint and add the states that apply.

**Data**
- `empty`, split when it matters: first use (teach and invite), no results (help recover the
  query), cleared (confirm the achievement), and no permission (explain who can grant access).
- `partial`: some data loaded, some failed or still streaming.
- `ideal`: realistic volume, not three perfect rows.
- `overflow`: very long names, huge numbers, hundreds of items, many tags, long translations
  (German about 30% longer, Finnish compounds), right-to-left scripts, emoji.
- `stale`: cached data shown while refreshing, with its age.
- `cold-start`: a metric, chart, or recommendation before there is enough data to be honest. Say
  what is missing and when it will be ready rather than showing a misleading number.
- `mixed`: a group whose items disagree (a customer with one disputed and one overdue invoice, a
  selection of files with different permissions). Say what happens to each item.

**Time and progress**
- `loading` (skeleton or nothing under 300 ms), `long-running` (real progress, cancel), `background`
  (the user left; how do they learn it finished?), `timeout`.

**Failure**
- `error` with a recovery action; `offline`; `rate-limited`; `permission-denied`; `not-found`;
  `conflict` (someone else changed it); `validation` (inline, at the field, on blur or submit);
  `destructive-confirmation`; `undo` window after a destructive action.
- One state per exit code or error code the touchpoint can return, including the generic internal
  and network failures, each with its recovery.

**Stress**
- `long-copy`, `overflow`, and translation states are checked against the trim, live area, or
  safe zone. Content that is clipped or pushed outside the live area blocks the state; it is not
  "copy-fit".

**People and context**
- `first-run` and onboarding; `returning` (pick up where I left off); `signed-out`;
  `trial-expired` or `upgrade`; `multiple-accounts`; `shared` (someone else's content).

**Presentation variants**
- `dark` and light; `high-contrast`; `large-text` (accessibility sizes); `reduced-motion`;
  `keyboard-focus`; `screen-reader` (reading order and announcements); `narrow` and `wide`;
  `landscape`; `split-view` or `narrow-window`; `print` for documents.

**Agents and automation**
- `non-tty` and `json` for CLIs; `deep-link` restoration for apps and pages; `api-error` mapping
  (what an agent sees when an action fails); `headless` (the action performed through an intent,
  shortcut, or MCP tool shows its result in the UI when the person returns).

## Writing good state content

- Empty states are invitations, not apologies: one sentence on what will be here, one primary
  action, and an example or template when the blank page is intimidating.
- Errors name the cause in human terms, keep the user's input, and offer the next step. Never
  "Something went wrong" alone; include a reference code for support when there is one.
- Loading states show the shape of what is coming. Long operations say what is happening and how
  long it will take.
- Success is quiet for routine actions and visible for important ones.

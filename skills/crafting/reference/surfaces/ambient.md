# Ambient surfaces: watch, TV, car, spatial, kiosk, and device screens

These surfaces live in the world, not on a desk. Attention is a glance, input is constrained, and
context (driving, a living room, a public lobby, a kitchen) dominates. Design for the seconds a
person actually gives, and verify current platform guidance by research.

## Watch (`watch`)

Craft:

- Glanceable in about two seconds: one fact per view, large type, high contrast, and the most
  important data in complications, widgets, or the Smart Stack (watchOS) or tiles (Wear OS).
- Input by Digital Crown or rotary input, taps on large targets, and voice. No typing.
- Always On: a dimmed state that stays legible and private, with motion stopped.
- Haptics carry meaning (success, alert, direction); sound is often off.
- Short, interruptible sessions; heavy work hands off to the phone.

Mockup and verification: frames at the smallest and largest case sizes, round and rectangular for
Wear OS, Always On, and the largest text size; complications in each family the app supports.

## TV (`tv`)

Craft:

- A ten-foot interface: large type, generous spacing, and content art doing most of the work.
- Focus is the cursor: one clear focused element at all times, a focus effect that scales or
  lifts, predictable directional movement with a remote's D-pad or touch surface, and Back that always
  goes back.
- Keep text and controls inside the TV safe area; assume overscan on some sets.
- Lean-back flows: few steps, no typing (sign in with a phone or a code), and playback controls that
  appear and fade without hiding what people watch.

Mockup and verification: 1920×1080 frames (and 4K where relevant) with the safe area overlaid, every
screen with its focused element shown, and navigation sequences captured as frame strips.

## Car (`car`)

Craft:

- Safety first: CarPlay and Android Auto apps use the platforms' templates and categories; follow
  them rather than fighting them. Driver distraction guidelines (for example, task glances of about
  two seconds) set the limits.
- Voice first, then large targets; no long lists or text entry while driving, and content that
  locks out when the vehicle moves where required.
- Day and night themes that switch with the car's lighting; audio ducking for navigation prompts.

Mockup and verification: the platform templates filled with real content, in day and night, plus
the voice transcript for each primary task, and a glance count per task.

## Spatial and XR (`spatial`)

Craft:

- visionOS and Android XR: windows, volumes, and immersive spaces. Start in a window; go immersive
  only when it earns it, with a clear way back.
- Eyes target and hands confirm: targets at least about 60 points with hover feedback on gaze, no
  precision gestures, and nothing important at the edges of the field of view.
- Comfort: content at a comfortable distance and height, no forced head movement, no motion that
  moves the world around a still user, and stable anchors.
- Legibility over passthrough: the system glass materials, vibrancy, and sufficient contrast
  against unknown real-world backgrounds.

Mockup and verification: the simulator or Figma frames with the platform kit, in a light and a dark
room environment, with gaze focus states; motion described with comfort notes.

## Kiosk (`kiosk`)

Craft:

- Strangers, standing, in public, in a hurry: one task per screen, big targets, and plain words.
- Attract state that explains what the kiosk does; a session that resets after inactivity, with a
  visible warning and countdown first, and no personal data left behind.
- Reach and posture: controls within accessible reach ranges for wheelchair users, glare-resistant
  contrast, audio output with a headphone jack or speaker for blind users, and a tactile or
  keypad alternative where regulation requires it.
- Hardware integration (payment terminal, printer, scanner) has its own states: waiting, failed,
  out of paper.

Mockup and verification: full-resolution frames at the kiosk's real size and orientation, including
idle, timeout warning, and hardware failure; a reach-height diagram for physical controls.

## Device screens (`device`)

Covers appliances, IoT hubs, wearables without app platforms, e-ink, small LCDs, and LED-only devices.

Craft:

- Design within the hardware: pixel grid, refresh rate, color depth, and viewing angle. On e-ink,
  avoid animation and plan partial refreshes; on segment displays, design the glyph set.
- Physical controls are part of the UX: label them, keep their meaning constant, and give feedback
  within 100 ms (light, sound, or haptic).
- Status lights need a legend: a small vocabulary of colors and blink patterns, never color alone.
- Setup and pairing (usually via a companion app over Bluetooth or Wi-Fi) is the riskiest journey:
  design every failure, and recovery without a support call.
- Firmware updates: state, progress, safe interruption, and what happens if power fails.

Mockup and verification: pixel-accurate renders at the device's resolution (and a photo-real
context render if useful), a light-pattern table, and the companion-app setup journey.

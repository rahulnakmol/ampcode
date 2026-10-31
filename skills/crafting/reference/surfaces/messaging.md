# Messaging surfaces: notifications, email, and SMS

Messages reach people outside the product, often at a bad moment. Every one must earn the
interruption, carry its meaning in the first line, and land the person exactly where they need to be.

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

## Email (`email`)

Craft:

- One message, one job, one primary action. The subject line and preheader together are the
  notification; write them as a pair.
- Transactional email (receipts, security, password reset) is product UX: plain, fast to scan,
  with the key fact above the fold and the reference numbers support will ask for.
- Build for hostile renderers: table-based or well-tested responsive layout, live text over images,
  system or web-safe fonts with fallbacks, and a 600 px-ish column that reflows on phones.
- Dark mode: clients invert or partially invert colors. Use transparent logos with a light outline
  or dark-mode variants, and avoid text baked into images.
- Images off: alt text that carries meaning; the email still works as text.
- Always a plain-text part, a visible unsubscribe for marketing, and a real reply address when
  replies are welcome. Sender name and address people recognize.
- Agents read inboxes too: put machine-meaningful facts (order number, amounts, dates, links) in
  text, and use structured data markup where clients support it.

Mockup and verification: render the HTML in a browser at 600 and 375 px, light and dark, with
images blocked, and the plain-text part. If an email testing service is available, check the main
clients (Apple Mail, Gmail web and app, Outlook desktop and web).

## SMS (`sms`)

Craft:

- Identify the sender in the first words; put the fact and the action next; keep it to one segment
  (160 GSM-7 characters, or 70 with emoji or non-Latin text, where longer messages split).
- Links only from a recognizable domain; never ask for secrets; one-time codes formatted so the
  phone can autofill them.
- Opt-in and opt-out are part of the design: confirmation on opt-in, `STOP` honored and confirmed,
  quiet hours respected. Check the rules for each market.

Mockup and verification: the exact text per state, its character and segment count, and a render
in the native messaging app frame for iOS and Android.

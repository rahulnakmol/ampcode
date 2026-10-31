# Agent experience

AI agents are now users: they read pages, call APIs and MCP tools, run CLIs, and act for people.
Agent experience (AX) is UX where the user is a model with a context window, no eyes for
decoration, little patience for ambiguity, and a person somewhere relying on its result. Good AX
is good UX made explicit.

There are two kinds of touchpoint here:

1. **Agent-facing surfaces**: APIs, MCP servers, agent-to-agent endpoints, webhooks and events,
   docs written for agents, CLIs, machine-readable pages, and the accessibility layer of every UI
   that computer-use and browser agents operate. The agent is the direct user.
2. **Human-agent surfaces**: chat, voice, copilots, agentic workflows, delegation and consent
   screens, and agent-driven checkout, where a person works with, authorizes, or supervises an
   agent. Both are users.

Protocols in this space change quickly (MCP, Agent2Agent, agentic commerce and payment protocols).
Check the current specifications by research before designing to one.

An agent's version of delight is **zero guesses**: it completes a task it has never seen from the
descriptions and outputs alone, and every consequential call does exactly what the person
expected. Treat each guess a fresh agent makes as a design defect, not a documentation gap.

## What agents need from any surface

- **Discoverability**: the agent can find what is possible from the surface itself (tool lists,
  `--help`, OpenAPI, `llms.txt` or a Markdown view, accessible names), without outside knowledge.
- **Unambiguous names**: one name per concept everywhere (UI label, API field, CLI flag, tool name,
  docs). Verbs for actions, nouns for things.
- **Predictable structure**: stable shapes, consistent errors, stable identifiers, and no meaning
  carried only by color, position, or animation.
- **Errors that teach**: say what was wrong, which input caused it, what is allowed, and the next
  call to make. An agent can recover from "`due_date` must be ISO 8601, for example 2026-11-01";
  it cannot recover from "Bad request".
- **Token economy**: concise outputs by default, with pagination, filters, field selection, and
  a summary first. Never dump megabytes into a context window.
- **Safe actions**: dry runs, idempotency keys, confirmations for destructive or costly actions,
  and undo where possible. Agents retry; design for it.
- **Observable results**: every action returns what changed and the new state, so the agent can
  verify without a second lookup.

## MCP servers and tools (`mcp`)

The tool list is the interface; its descriptions are the copy. Design it like a product surface:

- **Few, task-shaped tools** over many thin CRUD endpoints: `schedule_meeting` instead of
  `create_event` plus `add_attendee` plus `set_reminder`. Each tool maps to a job a person would
  ask for.
- **Descriptions that route**: first sentence says what it does; then when to use it; then a "Not
  for X; use Y" clause; then side effects and cost. Name the inputs the way the user's request
  would. When an optional parameter's omission triggers a long default (a 90-day hold), recommend a
  value for each common case.
- **Non-goals are stated**: list the plausible requests agents cannot do (void, refund, record a
  payment, edit contacts) in the server instructions or the nearest tool's description, with the
  handoff (an app link), and add one refusal or handoff transcript for each.
- **Schemas that prevent errors**: enums over free text, formats and examples on fields, sensible
  defaults, and required fields only when truly required.
- **Outputs designed for reading**: structured content with an `outputSchema` when consumers parse
  it; a short human-readable summary first; links back to the human UI for the same object.
- **Long work is asynchronous**: return an ID at once, offer a cheap status call and a separate
  result call (the Parallel Task MCP's `getStatus` and `getResultMarkdown` are a good model).
- **Permissions are explicit**: read-only tools separate from writing tools so clients can allow
  one and ask for the other.
- **Guards have parity**: every tool that moves money, contacts people, publishes, or deletes gets
  the same server-side protection, whether it acts on one item or a batch (a batch read-back of
  recipient count and total, or a threshold confirmation). Write a parity table: approval, what it
  binds, caps, stale re-check, retry reuse; single-item and batch tools match row for row.
- **Approval binds everything outward**: every field that changes who receives something (`to`,
  `cc`, `bcc`, `cc_me`, webhook URLs) and every customer-visible free-text value (message, note) is
  shown in the read-back and bound to the approval, together with the caller and an expiry.
- **Approved, then the world changed**: a scheduled or delayed send re-checks full eligibility at
  send time (hold, dispute, contact change, payment), and every tool that changes eligibility says
  what happens to sends already scheduled.
- **Hints match behaviour**: annotations such as `idempotentHint` hold for every argument
  combination; a flag like `resend: true` makes a tool non-idempotent.
- **Defaults are visible**: any server default an agent must know (send limits, automatic resume
  after a pause, retention) is stated in the tool description, not only in examples.
- **Money is a string** with a decimal pattern and an explicit currency, never `string | number`.
- **Errors fit the contract**: error results have their own documented shape (for example a `oneOf`
  branch in the output schema), and status-like fields are enums.
- **Next steps are agent-safe**: suggested `next` calls never delete, spend, or contact anyone
  without the user, never act on another owner's objects, and never need a secret the agent does
  not have. Tag each error with an action such as `retry`, `fix_input`, `fix_code`, or `needs_human`.
- **Injection pass**: assume tool inputs and fetched content can carry hostile instructions. Check
  that no tool can be steered into sending data or money to an address the user did not approve.

States to mock for an MCP touchpoint (as example transcripts in `.design/mockups/`): `ideal`,
`empty` (no results, with a hint), `loading` (accepted, in progress), `error`, plus
`validation-error`, `auth-error`, and `large-result` (paginated or truncated with a next step).

## APIs and SDKs (`api`)

Developer experience is UX for people who build with agents and for the agents themselves:

- A first successful call in under five minutes: copy-paste examples with real values, a test key or
  sandbox, and errors that name the fix.
- Consistent resource naming, pagination, filtering, and error format across every endpoint.
- Rate limits and quotas visible in headers and in errors, with a retry time.
- Versioning and deprecations announced in responses, not only in a changelog.

States to mock (as example requests and responses): `ideal`, `empty`, `loading` (202 accepted with a
status URL), `error`, plus `validation-error`, `rate-limited`, and `auth-error`.

## Agent-to-agent (`a2a`)

When the product is itself an agent, or exposes one, other agents are its users:

- **A discoverable card**: what the agent can do, its skills with examples, input and output
  formats, authentication, and limits (for example an Agent2Agent agent card at a well-known URL).
- **Task lifecycle as UX**: accepted, working, needs input, completed, failed, cancelled, each with
  a clear message and the artifacts produced so far. Streaming or push updates for long tasks.
- **Asking for input** is a designed state: the question, the allowed answers, and the default.
- **Scope and trust**: what the agent will not do, who it acts for, and how a calling agent can
  verify results.

States to mock (as transcripts): `ideal`, `empty`, `loading`, `error`, plus `input-required`,
`cancelled`, and `auth-error`.

## Webhooks and events (`webhook`)

Events are messages to software that will act on them unattended:

- Clear event names (`invoice.paid`), versioned payloads with the full object or a stable link to
  it, and an event ID for idempotent handling.
- Signatures with a documented verification method, retries with backoff, ordering guarantees
  stated honestly, and a replay tool.
- A human surface for the same events: a delivery log with payloads, responses, and a resend button.

States to mock: `ideal`, `retry` (failed delivery and its schedule), `signature-failure`, and
`replay`.

## Docs written for agents (`agent-docs`)

Agents learn a product from text: `llms.txt`, `AGENTS.md`, skill files, OpenAPI descriptions, MCP
tool descriptions, and README files. Design them like an onboarding flow:

- Lead with what the product does and the three most common tasks, each with a working example.
- One page or file per task, short, with exact names, valid values, and expected outputs.
- State constraints and things not to do; agents follow explicit rules better than implied ones.
- Keep human and agent docs in sync from one source; a Markdown version of every docs page.
- Test them: give a fresh agent only these docs and a task, and record where it guessed.

States to mock: `ideal` (the task succeeds from the docs alone), `ambiguity` (where the test agent
guessed, and the fix), and `outdated` (how stale docs are detected).

## CLIs as agent surfaces

See `surfaces/terminal.md`. The agent essentials: `--json` on every command that prints
data, stable exit codes, flags for every prompt, no color or spinners when not a TTY, and help text
with examples first.

## Pages and apps as agent surfaces

- Semantic HTML and native accessibility APIs are the agent's view of the UI. A browser agent
  sees the accessibility tree; a well-labelled UI is an agent-usable UI.
- Offer a machine view for content: a Markdown version, `llms.txt`, structured data, or a toggle like
  parallel.ai's Human and Machine views.
- Every important state is addressable by URL or deep link.
- Native: App Intents (Apple), app actions and deep links (Android), and UI Automation names
  (Windows) expose key actions to assistants and agents.
- Computer-use and browser agents operate the visual UI directly: stable layouts, visible labels on
  icons, no essential information only in tooltips or on hover, standard controls rather than custom
  canvas widgets, and confirmation text after every action.

## Human and agent together

When a person works with an agent (chat, copilot, background agent), design for trust that matches
the agent's actual reliability:

- **Show the work, at the right depth**: a one-line status of what the agent is doing now, with
  details (tool calls, sources, diffs) one tap away. Never a silent spinner for minutes.
- **Stream, but stay readable**: render progressively without layout jumps; keep the reading
  position stable while text arrives; never fake typing delays.
- **Interruptible**: stop, steer, and edit at any point; the agent acknowledges and adapts.
- **Approvals designed as decisions**: before a consequential action, show exactly what will happen,
  to what, with what cost, and how to undo it. Batch low-risk approvals; never ask for meaningless
  ones (approval fatigue leads to rubber-stamping).
- **Honest uncertainty**: cite sources, mark guesses, and make it easy to check. Calibrated
  confidence beats confident prose.
- **Recoverable**: undo, version history, and a clear record of what the agent did and why.
- **Handoffs**: when the agent stops (done, blocked, needs input), notify through the channel the
  person chose, with the result and the one action needed.
- **Memory with consent**: show what the agent remembers and let people edit or delete it.
- **Delegation and consent**: when a person grants an agent access (OAuth consent, connecting an
  account, a spending limit), the screen names the agent, what it can do, for how long, with what
  limits, and how to revoke it. Revocation is one step from the place people look for it.
- **Agent-driven commerce**: when agents buy on someone's behalf, design the mandate (what may be
  bought, the budget, the merchant), the confirmation the person sees, the receipt that names the
  agent, and refunds. Check the current agentic payment protocols by research.

States to mock for a chat or copilot touchpoint: `ideal`, `empty` (first message, with starters that
teach capability), `loading` (thinking), `error`, plus `streaming`, `tool-call` (work in progress
and its detail view), and `interrupted` (stopped or redirected mid-answer). Add `approval`,
`refusal`, and `handoff` when the product has them.

## Checking agent surfaces

- Validate every example call and result against the schemas with a script that exits non-zero on
  any problem, and check that every fact in a result summary (amounts, dates, names) comes from the
  call's inputs or from state shown earlier, and that timelines agree across transcripts.
- Run `design_kit.py tools <tools.json>` and fix every gap. Then audit each annotation against
  the tool's own text for every argument combination: anything that cancels or replaces without
  restore is `destructiveHint: true`; any path that "sends again" is not idempotent unless keyed.
- Every reference parameter (customer, invoice) has a lookup tool or a documented no-match result
  with a transcript, and constraints a person states about an owner ("anyone who disputed") can be
  expressed without the agent filtering items by hand.
- Send-time re-checks listed in descriptions match the server's full eligibility list (holds,
  disputes, void, cooldown from any sender, contact changes, payment, caps, revoked scope).
- Form-mode elicitation trusts the client to show a person; say so, prefer URL mode for outward
  actions when client trust is not established, put no clickable links in form messages, and make
  approval state single-use with a fresh ID when content changes.
- **Transcript-to-contract sweep**: for every rule a transcript, approval prompt, or "what the agent
  does next" relies on, find it in a tool description or schema. Check each number in the defaults table (limits, rate limits, windows, durations) appears in the
  description of every tool it applies to, once, not only in server instructions. A rule found only in
  transcripts, `DESIGN.md`, or `HANDOFF.md` is a defect: agents never see those files.
- For CLIs and APIs, give every exit code or error code its own state, including the generic
  internal or network failure, and list every exit code in `--help`.
- Walk recovery for each failing code: using only the help text and the outputs, write the exact next
  call. If it needs another command's output, that command's contract is in scope or is a stated gap.
- Run the agent usability test in `user-research.md` with tasks the transcripts do not already
  cover, and report guesses per task. Include a customer- or owner-level request (not one item), an
  ambiguous verb ("cancel"), and a request for a non-goal. If you have no subagent, do the sweep
  above instead of scoring yourself, and give the user the test prompt.

## AX slop

- Dozens of tools that mirror database tables; descriptions that repeat the tool name.
- Errors as stack traces or bare status codes; success responses with no new state.
- Huge unpaginated outputs; HTML where JSON or Markdown was possible.
- Chat UIs that hide tool use, apologize in loops, open with "Great question!", or answer in walls
  of text with no structure.
- Approval prompts for everything, or for nothing.

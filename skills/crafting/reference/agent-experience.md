# Agent experience

AI agents are now users: they read pages, call APIs and MCP tools, run CLIs, and act for people.
Agent experience (AX) is UX where the user is a model with a context window, no eyes for
decoration, little patience for ambiguity, and a person somewhere relying on its result. Good AX
is good UX made explicit.

There are two kinds of touchpoint here:

1. **Agent-facing surfaces**: APIs, MCP servers, CLIs, machine-readable pages, and the
   accessibility layer of every UI. The agent is the direct user.
2. **Human-agent surfaces**: chat, voice, copilots, and agentic workflows, where a person works
   with or supervises an agent. Both are users.

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

## MCP servers and tools

The tool list is the interface; its descriptions are the copy. Design it like a product surface:

- **Few, task-shaped tools** over many thin CRUD endpoints: `schedule_meeting` instead of
  `create_event` plus `add_attendee` plus `set_reminder`. Each tool maps to a job a person would
  ask for.
- **Descriptions that route**: first sentence says what it does; then when to use it and when to use
  another tool instead; then side effects and cost. Name the inputs the way the user's request
  would.
- **Schemas that prevent errors**: enums over free text, formats and examples on fields, sensible
  defaults, and required fields only when truly required.
- **Outputs designed for reading**: structured content with an `outputSchema` when consumers parse
  it; a short human-readable summary first; links back to the human UI for the same object.
- **Long work is asynchronous**: return an ID at once, offer a cheap status call and a separate
  result call (the Parallel Task MCP's `getStatus` and `getResultMarkdown` are a good model).
- **Permissions are explicit**: read-only tools separate from writing tools so clients can allow
  one and ask for the other.

States to mock for an MCP touchpoint (as example transcripts in `.design/mockups/`): `ideal`,
`empty` (no results, with a hint), `loading` (accepted, in progress), `error`, plus
`validation-error`, `auth-error`, and `large-result` (paginated or truncated with a next step).

## APIs and SDKs

Developer experience is UX for people who build with agents and for the agents themselves:

- A first successful call in under five minutes: copy-paste examples with real values, a test key or
  sandbox, and errors that name the fix.
- Consistent resource naming, pagination, filtering, and error format across every endpoint.
- Rate limits and quotas visible in headers and in errors, with a retry time.
- Versioning and deprecations announced in responses, not only in a changelog.

States to mock (as example requests and responses): `ideal`, `empty`, `loading` (202 accepted with a
status URL), `error`, plus `validation-error`, `rate-limited`, and `auth-error`.

## CLIs as agent surfaces

See the CLI section of `surfaces.md`. The agent essentials: `--json` on every command that prints
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

States to mock for a chat or copilot touchpoint: `ideal`, `empty` (first message, with starters that
teach capability), `loading` (thinking), `error`, plus `streaming`, `tool-call` (work in progress
and its detail view), and `interrupted` (stopped or redirected mid-answer). Add `approval`,
`refusal`, and `handoff` when the product has them.

## AX slop

- Dozens of tools that mirror database tables; descriptions that repeat the tool name.
- Errors as stack traces or bare status codes; success responses with no new state.
- Huge unpaginated outputs; HTML where JSON or Markdown was possible.
- Chat UIs that hide tool use, apologize in loops, open with "Great question!", or answer in walls
  of text with no structure.
- Approval prompts for everything, or for nothing.

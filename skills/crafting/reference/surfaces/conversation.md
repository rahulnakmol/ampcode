# Conversation surfaces: chat and voice

A conversation is an interface made of turns. Design the turn-taking, the pacing, and the recovery
as carefully as the words. Human-agent patterns (showing work, approvals, interruption) are in
`../agent-experience.md`.

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


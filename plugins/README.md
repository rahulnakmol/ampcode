# Plugins

Store personal Amp plugin source here.

[`amp-custom-mode-dials.ts`](./amp-custom-mode-dials.ts) adds Swift, Weave, and Prime without replacing Amp's built-in Dial modes.

[`advisory-team/`](./advisory-team/) adds Archi, Darci, and Opsci as modes and consultation tools. Read the [usage guide](../docs/advisory-team.md). Copy the entire directory when installing or publishing; its Markdown files contain the role instructions.

[`mission-control/`](./mission-control/) coordinates the [`delivering`](../skills/delivering/SKILL.md)
workflow with revision-bound local checkpoints and owner-restricted acknowledgment dialogs.
Read the [mission guide](../docs/mission-control.md). Tools are `mission_start(requirements)`,
`mission_update(action)`, `mission_status()`, `mission_approve(stage: design|merge)`,
`mission_merge_mode(mode: auto|ask)`, `mission_present()`, `mission_merge()`, and
`mission_reconcile()`, plus owner-only `mission_recover()` for settled, unqueued
attempts. Use the installed schemas for action payloads.

Requirements → grilling → concrete spec/plan/technical design plus relevant crafting UX →
initiator acknowledgment → whiteboard defense → outcome-driven TDD, two reviews, inspected
artifacts and customer value → evidence/try-it presentation → gated dev integration.
Material changes reopen design acknowledgment. At build entry low/medium risk defaults to auto,
with optional owner-selected ask-before-merge and no response/timer needed for auto. High risk
always needs exact-candidate acknowledgment; unknown risk blocks merge. Version one requires the
initiator to be the thread owner or the owner to adopt the mission. Owner-restricted fields take
non-sensitive typed acknowledgment, never secrets.

Local state is operational only, not trusted authorization. The external trusted controller,
pinned App check, and enforced dev branch protection are not provisioned by this source plugin.
Automatic merge fails closed without those prerequisites; loading the plugin does not establish
deployed enforcement. A queued auto-merge request is not a verified merge. Copy the entire plugin
directory if separately authorized to install/publish; skills belong in Personal Skills, not in
the Personal Plugins destination. Source integration grants no Personal publication authority.

- Use one root `.ts` or `.js` file for a standalone plugin.
- Use `<plugin-name>/index.ts` for a plugin with supporting files or bundled skills.
- Include a static `description` export.
- Custom modes require matching `@amp-agent-mode` metadata comments.
- Discover valid models, efforts, and tool names with `amp plugins show-agent-options --json`.
- Validate all plugins with `make check`.

To publish globally, obtain explicit approval for the Amp Personal Plugins destination, then copy
the plugin file or complete directory to the root of the repository listed by
`amp plugins repositories`, review, commit, and push that repository. Personal Skills publication
uses its separate repository and approval; source pushes, dev integration, rolling/stable promotion,
and deployment do not authorize either publication.

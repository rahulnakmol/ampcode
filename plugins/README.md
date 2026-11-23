# Plugins

Store personal Amp plugin source here.

[`amp-custom-mode-dials.ts`](./amp-custom-mode-dials.ts) adds Swift, Weave, and Prime without replacing Amp's built-in Dial modes.

[`advisory-team/`](./advisory-team/) adds Archi, Darci, and Opsci as modes and consultation tools. Read the [usage guide](../docs/advisory-team.md). Copy the entire directory when installing or publishing; its Markdown files contain the role instructions.

[`mission-control/`](./mission-control/) runs contract missions for the
[`delivering`](../skills/delivering/SKILL.md) skill: one contract, a readiness preflight bound to
it, **one owner approval at kickoff**, then milestones that squash-merge into `dev` after tests,
CI and two fresh reviews, with no owner dialog. Read the [mission guide](../docs/mission-control.md).
Tools are `mission_start({ contract })`, `mission_status()`, `mission_preflight()`,
`mission_approve()` (the kickoff dialog), `mission_effect({ effectId } or { effect, why })`,
`mission_update({ action })` with 12 actions (`amend`, `replan`, `file`, `delegate`, `item-done`,
`candidate`, `review`, `disposition`, `evidence`, `assume`, `stop`, `resume`),
`mission_merge({ milestoneId })`, `mission_reconcile({ milestoneId })`,
`mission_recover({ milestoneId })` and `mission_report({ kind, milestoneId? })`. The command
"Reopen mission approval" and its quick action reopen a dismissed dialog; the project plugin
[`.amp/plugins/mission-control-preview.ts`](../.amp/plugins/mission-control-preview.ts) adds
"Preview approval dialogs", which records nothing. Retired v1 and v2 records report a retired
schema and stay unchanged.

The owner is asked again only for one of the five stop reasons, which `lib/contract-text.json`
holds:

1. Change to the baseline: a criterion, scope item or design decision is wrong or conflicts, and no reading inside the contract works.
2. Outside effect not in the contract: an irreversible or outside effect that the contract does not pre-authorize.
3. A fact only a person holds, with no safe, reversible default.
4. A red line: security, legal or safety.
5. A milestone cannot meet its exit criteria after the work was re-planned and split.

Local state enforces the workflow, not security against unrestricted shell access. Existing GitHub
credentials available to `gh` in Amp are used; no custom controller, App or approval service is
needed. Required CI checks must be pinned to source Apps by strict, administrator-enforced `dev`
protection. The plugin does not configure CI or protection; a failing preflight blocks kickoff and
failing requirements block a merge. Never type a secret into a dialog. Copy the entire plugin
directory if separately authorized to install or publish; skills belong in Personal Skills, not in
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

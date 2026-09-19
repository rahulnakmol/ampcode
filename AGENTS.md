# Repository guidance

This repository is the source of truth for Rahul's personal Amp extensions.

- Keep standalone plugins under `plugins/`. A plugin directory must use `index.ts` or `index.js`.
- Keep skills under `skills/<skill-name>/SKILL.md`. Skill names use lowercase gerunds and must match their directory names.
- Run `make check` after changing plugins, skills, validation, or extension metadata.
- Confirm model IDs and supported reasoning efforts with `amp plugins show-agent-options --json` before pinning them.
- Prefer Amp's automatic subagent routing unless a mode intentionally constrains every specialist to one provider.
- Treat token cost as a design constraint: use the lowest sufficient effort, delegate only bounded independent work, and reserve Oracle for consequential unresolved questions.
- MCP-backed skills must restrict exposed tools with `includeTools`.
- Never commit secrets or provider credentials.
- Keep `README.md` routing tables and publication guidance current.
- Publish plugins and skills to their separate Amp Personal repositories only after explicit approval.

# Starting a fresh reviewer on each host

Each host has its own way to run work in a separate context. Use it, pass only what section 1 of
`SKILL.md` allows, and run the isolation check (section 7) once per host and session. Rows
marked "from documentation, not tested" were read from the host's documentation on 16 Nov 2026
and have not been run with this skill.

| Host | How to start a fresh reviewer | Watch for | Status |
| --- | --- | --- | --- |
| Amp | The Task tool (a subagent). It sees only the prompt you write and returns one final message | Do not paste your conversation or your verdict into the prompt. Tell it not to edit files | Used for this repository's reviews; isolation check not yet run |
| Claude Code | A custom subagent (`.claude/agents/<name>.md`) or a built-in one; each "starts with a fresh, isolated context window" and sees only the task message. Source: https://code.claude.com/docs/en/sub-agents | A **fork** inherits the full conversation, so it is not a fresh reviewer. Subagents still load `CLAUDE.md`/`AGENTS.md`; set `omitClaudeMd: true` when those files hold context the reviewer must not see | From documentation, not tested |
| VS Code with Copilot | A skill with `context: fork` in its frontmatter runs "in a dedicated subagent" and returns only its result (experimental; needs the `github.copilot.chat.skillTool.enabled` setting). Or the `runSubagent` tool. Sources: https://code.visualstudio.com/docs/agent-customization/agent-skills, https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/use-copilot-agents/use-subagents | `context: fork` is experimental and may change. Check what the subagent receives with the isolation check | From documentation, not tested |
| Copilot app | A custom agent profile (`.github/agents/<name>.md` or `~/.copilot/agents/<name>.md`), chosen with the agent picker or `/agent`; Copilot delegates to subagents "in a separate context window". Sources: https://docs.github.com/en/copilot/concepts/agents/github-copilot-app, https://docs.github.com/en/copilot/concepts/customizations/custom-agents | Selecting a custom agent in the main session does not give it a fresh context; delegate to it as a subagent instead | From documentation, not tested |

## A reviewer prompt that works on every host

```text
You are a fresh reviewer. Do not edit any file.
Artifact: <path> at <revision>.
Read these sources: <path at revision>, <path at revision>.
Lens: <comprehension | critic | readiness | novice reader as "<persona>">.
Grade against: <criteria or questions>.
Report each finding with location, problem, consequence, severity (Blocker, Major, Nit) and
the smallest fix. List the files you actually read. Say what you could not check.
```

When no fresh context is available on a host, the gate is pending (SKILL.md section 6).

# Read-only incident investigator on other hosts

On Amp, the Opsci mode loads this skill with a fixed read-only tool list. On other hosts, copy one
of the wrappers below. Each lists only read, search and web-reading tools: no edit, shell or
delegation tool. The wrappers were written from the host documentation read on 22 Nov 2026 and
have not been run with this skill. Check the tool names against your host's documentation before
you rely on them.

A tool list narrows what the agent can call. It is not a security sandbox: files the agent can
read may still hold secrets. Give it sanitized exports and a source checkout without production
credentials.

## Claude Code

Save as `.claude/agents/incident-investigator.md` (project) or
`~/.claude/agents/incident-investigator.md` (personal). Install the skill first, as
`.claude/skills/investigating-incidents/` (project) or `~/.claude/skills/investigating-incidents/`
(personal), with all its files. The `skills` field preloads it from there, so the agent needs no
`Skill` tool; a missing skill is skipped with only a debug-log warning. Source:
https://code.claude.com/docs/en/sub-agents

```markdown
---
name: incident-investigator
description: Investigates production incidents read-only from logs, traces and deployed source. Use for incident triage and post-incident reviews.
tools: Read, Grep, Glob, WebFetch, WebSearch
skills:
  - investigating-incidents
---

Follow the investigating-incidents skill. You are advisory: never edit files, run commands,
execute mitigation, change alert thresholds, restart services or deploy. You have no shell:
follow the skill's "Without a shell" rule and label every check "not run".
```

Tools, check the tool names against your host's documentation:

| Tool | Why |
| --- | --- |
| `Read` | Read logs, exports and source |
| `Grep` | Search file contents |
| `Glob` | Find files by name |
| `WebFetch` | Read a platform's documentation page |
| `WebSearch` | Find documentation; never with customer identifiers |

## Copilot (GitHub Copilot custom agent)

Save as `.github/agents/incident-investigator.agent.md` (repository) or
`~/.copilot/agents/incident-investigator.agent.md` (personal, Copilot CLI). Put the skill where
your Copilot host reads skills, for example `.github/skills/investigating-incidents/`. Source:
https://docs.github.com/en/copilot/reference/custom-agents-configuration

```markdown
---
name: incident-investigator
description: Investigates production incidents read-only from logs, traces and deployed source. Use for incident triage and post-incident reviews.
tools: ["read", "search", "web"]
---

Read and follow the investigating-incidents skill (its SKILL.md and the files it links). You are
advisory: never edit files, run commands, execute mitigation, change alert thresholds, restart
services or deploy. You have no shell: follow the skill's "Without a shell" rule and label every
check "not run".
```

Tools, check the tool names against your host's documentation:

| Alias | Covers | Why |
| --- | --- | --- |
| `read` | Read file contents | Logs, exports, source, the skill |
| `search` | Search for files and text in files | Find code paths and log lines |
| `web` | Fetch a URL and search the web | Read documentation; never with customer identifiers |

GitHub documents `web` as the alias for web fetch and web search, and as
"Currently not applicable for Copilot in the cloud". So on GitHub.com the agent cannot fetch
documentation or search the web: give it the pages it needs as files. In VS Code, the fetch tool may
appear under its own name (such as `fetch`); pick only the fetch and search tools there. An
unrecognized name is ignored, so a misspelled tool silently drops a capability rather than
adding one. Do not add `edit`, `execute`, `agent` or an MCP server wildcard.

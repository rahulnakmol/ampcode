# Running a mission on each host

The skill text is the same on every host; only the tools differ. Use this table to find the
host's tool for each step. Columns other than Amp come from each host's documentation, read on
18 Nov 2026, and have **not been tested** with this skill. Check the tool exists in your session
before relying on it.

| Need | Amp | Claude Code | Copilot in VS Code | Copilot app |
| --- | --- | --- | --- | --- |
| Load a skill | Name it ("use missioning") or let Amp pick it; skills come from `.agents/skills`, `~/.config/agents/skills` and Personal Skills | The `Skill` tool; skills in `.claude/skills` or `~/.claude/skills` | Loaded when relevant, or `/<name>`; skills in `.github/skills`, `.claude/skills` or `.agents/skills` | The `skill` tool of the Copilot harness; repository and personal skills (`~/.copilot/skills`, `~/.agents/skills`) |
| Keep the todo list | The thread's todo list where the session has one; otherwise a checklist under `## Steps` in the mission file | `TaskCreate` and `TaskUpdate`, or `TodoWrite`; newer models leave them out unless enabled, so fall back to the mission file checklist | The Copilot harness todo tool (`update_todo`) | The Copilot harness todo tool (`update_todo`) |
| Ask a question | The choice-question tool when the session offers it; otherwise end the turn with the question, the options and a recommended answer (none for a fact only a person holds), and mark the thread as waiting for input. A reply to that message is chat: it settles a preference, never a human gate | `AskUserQuestion`: one to four questions, two to four options each | The harness question tool (`ask_user`) | `ask_user`; it is off with `--no-ask-user` or in autopilot, so gates stay pending there |
| Start a fresh reviewer | See the host table in [`goldfishing`'s hosts reference](../../goldfishing/reference/hosts.md) | Same | Same | Same |
| Wait for PR and CI results | GitHub subscriptions for the exact head commit and the PR's comments | `gh pr checks <number> --watch` in the shell | `gh pr checks <number> --watch` in the terminal | `gh pr checks <number> --watch` |
| Read back a merge | `mission_reconcile` for delivering missions; otherwise `gh pr view <number> --json state,mergedAt,mergeCommit` | `gh pr view ...` as on Amp | `gh pr view ...` | `gh pr view ...` |
| Record an approval | `mission-control`'s kickoff or effect dialog for contract missions, when the installed plugin accepts `contract` in `mission_start` (`dialog: Amp mission-control kickoff ...`); otherwise the choice-question tool's answer (`question: ...`), a tracker approval or a written record | The `AskUserQuestion` answer (`question: AskUserQuestion ...`); a timed-out or dismissed question is no answer | The `ask_user` answer (`question: ask_user ...`) | The `ask_user` answer (`question: ask_user ...`) |
| Enforce a gate | For contract missions, `mission-control` blocks a milestone merge until kickoff is approved and both reviews and the evidence match the candidate; no owner dialog for merges | A `PreToolUse` hook can deny a tool call, for example a merge while `ledger_check.py` fails; this kit ships no hook | A `preToolUse` hook in `.github/hooks/*.json` (preview); this kit ships none | A `preToolUse` hook (same format as VS Code); this kit ships none |
| Avoid agent teams | One steering thread. M and L work items run in child threads (`create_thread`; they reply with `send_thread_message`); XS and S items and fresh reviews run as subagents (Task) | Do not use agent teams or the `Workflow` tool for a mission | Use one chat session | Do not use multi-agent Projects; use one session |

On every host, an approval from GitHub `/approve` (read by `syncing`) is `tracker: ...`, and a
signed document, email or client decision record is `written: ...`. Only the decision owner
answers the session's question tool or dialog; other approvers sign by tracker or in writing.

## Sources

- Amp skills: https://ampcode.com/docs/customize/skills
- Claude Code tools and hooks: https://code.claude.com/docs/en/tools-reference,
  https://code.claude.com/docs/en/hooks
- Copilot harness tools and hooks: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference,
  https://docs.github.com/en/copilot/reference/hooks-reference
- VS Code hooks and skills: https://code.visualstudio.com/docs/agent-customization/hooks,
  https://code.visualstudio.com/docs/agent-customization/agent-skills
- Copilot app Projects: https://github.blog/changelog/2026-10-28-github-copilot-app-universe-releases/

# Which model a reviewer starts on

A fresh reviewer starts on a model that wrote none of what it reviews. The skill that runs the
review picks that model before it starts the reviewer, so a same-model review never happens;
nothing checks for it afterwards. The pick is recorded with the review as evidence.

## Pick the model

1. Read every model that wrote the change or the artifact from the host, not from an agent's
   claim. On Amp, `get_thread_status` on each child thread returns its `model`; an XS or S item
   done by a Task subagent ran on the steering thread's model; a person's work is `human`.
2. Choose the kind of review (below) and run:

   ```bash
   python3 <goldfishing>/scripts/reviewer_model.py --kind <kind> --implementer <model> [...] [--not <model>]
   ```

   Pass `--not` with the model of another review of the same candidate, such as gate 1's reviewer
   when picking gate 2, so the two gates run on different models.
3. Start the reviewer on the printed model (the host table below), and record the model, the
   printed reason and where each model was read in the review record (for code reviews, the
   ledger's `models`).

| Kind | When | Order (the first one that fits) |
| --- | --- | --- |
| `code-1` | Review gate one, an item review, a single code review | GPT-6 Astra, Claude Opus 5.5, Gemini 4 Carbon |
| `code-2` | Review gate two | Gemini 4 Carbon, GPT-6 Astra, Claude Opus 5.5 |
| `document` | A fresh review of a document, plan or design | GPT-6 Astra, Claude Opus 5.5, Gemini 4 Carbon |
| `ui` | A UI or UX review of a bounded change | Gemini 4 Neon, Gemini 4 Carbon, GPT-6 Astra |
| `ui-complex` | A UI or UX review of a complex change | Gemini 4 Carbon, Gemini 4 Neon, GPT-6 Astra |

**Code and document reviews** skip every model from a provider that wrote any of the change, so
the reviewer does not share the author's training and blind spots; Claude-built work goes to GPT-6
Astra, then Gemini 4 Carbon. When every provider wrote some of it, the first model that wrote
none of it is used. These are the models that held up as gate reviewers in this repository's own
missions (PR #67: GPT-6 Astra and Gemini 4 Carbon on Claude Opus 5.5 work).

**UI and UX reviews** go to Gemini 4: crafting critiques and audits, the experience-design
playbook's reviews, and in software delivery any milestone that changes what a user sees (its
gate two is picked as `ui` or `ui-complex` instead of `code-2`, and gets the rendered states as
evidence). The owner chose Gemini for UI review; these are the Gemini 4 models this workspace
offers (Amp `list_agent_modes`, 28 Nov 2026): Carbon, "Google's most capable model, for long,
hard engineering tasks"; Neon, "between Hydrogen and Carbon"; Hydrogen and Argon (previous
generation). Hydrogen and Gemini 3.8 Flash are not used for gates.

| UI complexity | Signs | Model and why |
| --- | --- | --- |
| Bounded (`ui`) | One screen or component; up to five states or variants; copy, spacing, colour or layout polish; no new interaction model | Gemini 4 Neon: enough depth to compare a few rendered states against the brief, faster and cheaper than Carbon |
| Complex (`ui-complex`) | A new or changed flow across screens; more than five states; forms with validation, drag, multi-step or real-time interaction; motion; a design-system or layout-system change; a WCAG 2.2 audit; several widths or devices | Gemini 4 Carbon: the most capable Gemini 4 model, for long reviews that hold many states and journeys at once |

When in doubt, pick `ui-complex`. If a Gemini 4 model wrote the UI, the review takes the other
Gemini 4 model (Carbon for Neon work, Neon for Carbon work): still a different model, as the
owner asked for Gemini. If both wrote it, or both are taken by authors and the other gate, it
takes GPT-6 Astra.

## Start the reviewer on that model

| Host | How | Read the model back |
| --- | --- | --- |
| Amp | `create_thread` with `model` set to the picked ID, and the reviewer brief as the prompt. A Task subagent runs its parent's model, so it never serves as a reviewer | `get_thread_status` on the reviewer thread: its `model` |
| Claude Code | A subagent whose frontmatter `model` is a full model ID, or the per-call `model` parameter (an alias only). Claude Code runs only Claude models, so map the pick to another Claude model than the author's (Opus work to `claude-sonnet-5-5` or `claude-fable-5-2`) and say the provider stayed the same; a cross-provider review needs another host. An alias such as `opus` on an Opus session runs the session's version. Source: https://code.claude.com/docs/en/sub-agents | `/tasks` names each subagent's model. From documentation, not tested |
| VS Code with Copilot | A custom agent (`.github/agents/<name>.agent.md`) with `model` set to the picked model and `model-policy: required`, run as a subagent; or ask for "a subagent with <model>", since an explicit model passed to the subagent wins. Copilot offers GPT, Claude and Gemini models. Sources: https://code.visualstudio.com/docs/agents/run/subagents, https://code.visualstudio.com/docs/agent-customization/custom-agents | The agent file's `model`. From documentation, not tested |
| Copilot app and Copilot CLI | A custom agent profile (`.github/agents/` or `~/.copilot/agents/<name>.agent.md`) with `model:` and `model-policy: required`, delegated to as a subagent. Source: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli | The profile's `model`. From documentation, not tested |

When the picked model is not available on the host, take the next model in the kind's order and
say why. When no model other than the author's is available, the review is pending.

# Grilling skill: research notes

Research behind [`skills/grilling/`](../skills/grilling/SKILL.md), compiled 2026-10-23. It records
which techniques the skill adopted, from where, and which known failure modes it guards against.

## Sources reviewed

| Source | Technique taken |
| --- | --- |
| [mattpocock/skills `grilling`](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md), `grill-me`, `grill-with-docs` | Design tree and frontier; recommended answer per question; "yes" accepts it; facts are the agent's job, decisions are the user's; done when the frontier is empty |
| [mattpocock/skills `wayfinder`](https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md) | Name the destination first; fog of war; explicit out-of-scope; split work too big for one session |
| mattpocock/skills `domain-modeling` | Sharpen fuzzy terms; invent concrete scenarios; cross-check claims against code |
| [cursor/plugins `poteto-mode`](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/SKILL.md) | Classify forks: anything observable by running something is settled by a prototype, not a question; candor over agreement |
| [codepick.dev skills guide](https://codepick.dev/en/guides/interesting-agent-skills/) | Context on grill-me usage and the to-spec hand-off |
| obra/superpowers `brainstorming` | Classify the request size out loud; heavier when unsure; only escalate mid-task; decompose before grilling; spec self-review; approval gate |
| [GitHub Spec Kit `/clarify`](https://github.com/github/spec-kit/blob/main/templates/commands/clarify.md) | Coverage taxonomy marked Clear / Partial / Missing; rank by impact × uncertainty; "Why it matters"; recommended option; decision log that removes contradicted text |
| [Thariq, interview prompt](https://x.com/trq212/status/2005315275026260309) and [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Non-obvious questions; implement the spec in a fresh session; specs state scope, out-of-scope, and verification |
| [Thariq, "Finding Your Unknowns"](https://x.com/trq212/status/2073100352921215386) | Blind-spot pass for unknown unknowns; prioritize architecture-changing questions; prototype when the user would recognize the answer |
| [Harper Reed's workflow](https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm) | Questions build on previous answers; a separate hole-poking pass |
| [Kiro deep spec analysis](https://kiro.dev/blog/deep-spec-analysis) | Requirement bugs: wrong detail level, ambiguity, inconsistency, incompleteness; observable criteria with IF-THEN error paths |
| [snarktank `create-prd`](https://github.com/snarktank/ai-dev-tasks/blob/main/create-prd.md) | Few critical questions with lettered options answerable as "1A, 2C" |
| [BMAD Method](https://docs.bmad-method.org/reference/skills-and-agents/) | Pre-mortem first; inversion; edge-case lens walking every branch and boundary |
| [notmanas `devils-advocate`](https://github.com/notmanas/claude-code-skills/blob/main/skills/devils-advocate/SKILL.md) | Steelman first; cap concerns; "so what?" test; scrutiny proportional to stakes |
| [jeffallan "The Fool"](https://jeffallan.github.io/claude-skills/skills/workflow/the-fool) | No stacking minor objections; always end in synthesis |
| [rohunj `edge-cases`](https://www.skillsdirectory.com/skills/rohunj-edge-cases) | Edge-case categories, severity, and conversion into acceptance criteria |

## Failure modes the skill guards against

- **Question dumps.** Users reported that rounds of about a dozen questions were exhausting and led
  to blind "agree with your recommendations" replies (mattpocock/skills discussion #771). The skill
  asks one to three questions per round.
- **Rewording answered questions** after new context arrives. Answers are treated as settled.
- **Endless sessions and context exhaustion.** The skill stops when a round changes nothing and
  offers a file hand-off to a fresh session.
- **Grilling trivial work and clarification loops.** The Clear size proceeds with one stated
  assumption.
- **Asking what could be looked up**, or asking for look-and-feel opinions a prototype answers.
- **Noisy critique.** The so-what test and proportional scrutiny keep edge cases actionable.

## Choices that differ from the sources

- Matt Pocock's `grilling` asks the whole frontier each round. This skill caps rounds at three
  questions because of the batch-fatigue reports above.
- Spec Kit and superpowers ask one question per message. Up to three related frontier questions
  per round keeps momentum without the batch fatigue.
- The skill is model-invoked and sized, so it can trigger at the start of any session without
  interrogating clear, small requests.

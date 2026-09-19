# Amp frontier kit

Personal extensions for getting more leverage from [Amp](https://ampcode.com): reusable plugins, agent modes, and skills designed around clear ownership, efficient model routing, and deliberate token use.

This GitHub repository is the readable source of truth. Amp loads published copies from its separate Personal Plugins and Personal Skills repositories.

## Layout

```text
plugins/                  TypeScript or JavaScript Amp plugins
skills/<skill-name>/      Agent Skills, each rooted at SKILL.md
scripts/check.sh          Repository validation
```

See [`plugins/README.md`](./plugins/README.md) and [`skills/README.md`](./skills/README.md) before adding an extension.

## Journey modes

[`plugins/journey-modes.ts`](./plugins/journey-modes.ts) fills the useful gaps between Amp's built-in modes:

| Mode | Position | Main agent | Oracle | Subagents |
| --- | --- | --- | --- | --- |
| **Swiftstep** | Low → Medium | GPT-5.6 Luna, medium, Fast | Fable 5.1, medium | Amp automatic specialists |
| **Weave** | Medium → High | Opus 4.8, high, Fast | Fable 5.1, x-high | Sonnet 5, medium |
| **Prime** | High → Ultra | Opus 5, high | Fable 5.1, max | Amp automatic specialists |

### Why this routing

- **Swiftstep** keeps a Medium-style workflow but prioritizes direct execution. Luna provides the value-oriented main loop while Amp automatically picks specialist models for Task, Finder, Librarian, and Read Thread.
- **Weave** is the all-Anthropic mode. Opus leads implementation, Sonnet handles delegated work at medium effort, and Fable is reserved for difficult judgments.
- **Prime** extends High rather than Ultra, keeps the main agent at high effort, delegates bounded specialist research automatically, and invokes max-effort Fable only for unresolved high-impact decisions.

Plugin agent modes cannot enforce a fixed token ceiling, so Prime cannot guarantee a precise percentage below Ultra. Its prompt, effort, delegation, and Oracle policy are deliberately configured to avoid Ultra-style exhaustive exploration.

## Using modes without changing the Dial

The standard Low, Medium, High, and Ultra Dial can remain unchanged. Published plugin modes stay available in the complete mode picker and to Puck.

Example Puck request:

> Start a Weave thread in this project to implement the change, and a Prime thread to review the architecture. Ask both to report back here.

Name the mode explicitly; otherwise Puck uses its normal routing. Threads created in separate orbs have separate checkouts and do not automatically share uncommitted files.

## Validate

Run:

```sh
make check
```

The check loads every plugin through the installed Amp CLI, verifies formatting errors detectable by Git, and validates the required metadata of every skill package.

## Publish

Amp stores personal plugins and personal skills in separate global repositories:

- `amp plugins repositories`
- `amp skills repositories`

Copy plugin entry points to the root of the Personal Plugins repository. Copy each complete `skills/<skill-name>/` directory to the root of the Personal Skills repository. Commit and push those repositories to publish; new threads load published versions automatically.

Never commit API keys, provider credentials, access tokens, or generated secret-bearing settings here.

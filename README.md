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

## Meet the advisory team

**Start with the [advisory team usage guide](./docs/advisory-team.md)** for installation, example prompts, interviews, consultations, access limits, troubleshooting, and model updates.

| Mode | Responsibility | Main model | Consultation tool |
| --- | --- | --- | --- |
| **Archi** | Enterprise SaaS architect, including .NET and mobile/Windows clients | Fable 5.1, high | `consult_archi` |
| **Darci** | Enterprise data, analytics and evidence-grounded AI architect | Fable 5.1, high | `consult_darci` |
| **Revo** | Autonomous, evidence-led code reviewer | Astra, high | `consult_revo` |
| **Opsci** | Guided SRE investigator across telemetry and deployed code | Astra, high | `consult_opsci` |

All four are advisory-only. Archi and Darci interview users and evolve a shared design brief. Revo investigates supplied changes. Opsci investigates supplied incident evidence. Specialist routing stays automatic. The plugin provides no live database/telemetry connectors, GitHub publisher, or report-file writer; the guide explains these boundaries and how to extend access safely.

Select a mode for an ongoing conversation, or ask an implementation agent to use its named consultation tool. Source lives in [`plugins/advisory-team/`](./plugins/advisory-team/). Publishing this GitHub repository alone does not install the modes in Amp.

## Amp Custom Mode Dials

[`plugins/amp-custom-mode-dials.ts`](./plugins/amp-custom-mode-dials.ts) fills the useful gaps between Amp's built-in modes:

| Mode | Position | Main agent | Oracle | Subagents |
| --- | --- | --- | --- | --- |
| **Swift** | Low → Medium | GPT-5.6 Luna, medium, Fast | Fable 5.1, medium | Amp automatic specialists |
| **Weave** | Medium → High | Opus 5, medium | Fable 5.1, x-high | Sonnet 5, medium |
| **Prime** | High → Ultra | Opus 5, high | Fable 5.1, max | Amp automatic specialists |

### Why this routing

- **Swift** keeps a Medium-style workflow but prioritizes direct execution. Luna provides the reliable value-oriented main loop while Amp automatically picks specialist models for Task, Finder, Librarian, and Read Thread. Grok 4.6 Fast was rejected after both its benchmark and smoke test hard-failed.
- **Weave** is the all-Anthropic mode. Opus leads implementation at medium effort, Sonnet handles delegated work at medium effort, and Fable is reserved for difficult judgments.
- **Prime** extends High rather than Ultra, keeps the main agent at high effort, delegates bounded specialist research automatically, and invokes max-effort Fable only for unresolved high-impact decisions.

Plugin agent modes cannot enforce a fixed token ceiling, so Prime cannot guarantee a precise percentage below Ultra. Its prompt, effort, delegation, and Oracle policy are deliberately configured to avoid Ultra-style exhaustive exploration.

See the [realistic async-cache benchmark](./docs/amp-custom-mode-dials-benchmark.md) for executed tests, mutation results, timings, and the Fable 5.1 judge comparison.

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

The check loads every plugin through the installed Amp CLI, runs advisory-team wiring and tool-allowlist tests with Bun, verifies formatting errors detectable by Git, and validates the required metadata of every skill package. It does not run paid model evaluations.

## Publish

Amp stores personal plugins and personal skills in separate global repositories:

- `amp plugins repositories`
- `amp skills repositories`

Copy standalone plugin entry points, or complete directory plugins such as `advisory-team/`, to the root of the Personal Plugins repository. Do not omit supporting Markdown files. Copy each complete `skills/<skill-name>/` directory to the root of the Personal Skills repository. Review and commit changes, then push only after explicit approval; new threads load published versions automatically.

Never commit API keys, provider credentials, access tokens, or generated secret-bearing settings here.

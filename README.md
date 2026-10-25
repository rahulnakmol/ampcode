# Amp frontier kit

Personal extensions for getting more leverage from [Amp](https://ampcode.com): reusable plugins, agent modes, and skills designed around clear ownership, efficient model routing, and deliberate token use.

This GitHub repository is the readable source of truth. Amp loads published copies from its separate Personal Plugins and Personal Skills repositories.

## Layout

```text
plugins/                  TypeScript or JavaScript Amp plugins
skills/<skill-name>/      Agent Skills, each rooted at SKILL.md
scripts/check.sh          Repository validation
tests/                    Bun plugin tests and Python skill-script tests
```

See [`plugins/README.md`](./plugins/README.md) and [`skills/README.md`](./skills/README.md) before adding an extension.

## Meet the advisory team

**Start with the [advisory team usage guide](./docs/advisory-team.md)** for installation, example prompts, interviews, consultations, access limits, troubleshooting, and model updates.

| Mode | Responsibility | Main model | Consultation tool |
| --- | --- | --- | --- |
| **Archi** | Enterprise SaaS architect, including .NET and mobile/Windows clients | Fable 5.1, high | `consult_archi` |
| **Darci** | Enterprise data, analytics and evidence-grounded AI architect | Fable 5.1, high | `consult_darci` |
| **Opsci** | Guided SRE investigator across telemetry and deployed code | Astra, high | `consult_opsci` |

All three are advisory-only. Archi and Darci interview users and evolve a shared design brief. Opsci investigates supplied incident evidence. Specialist routing stays automatic. The plugin provides no live database/telemetry connectors or report-file writer; the guide explains these boundaries and how to extend access safely.

Select a mode for an ongoing conversation, or ask an implementation agent to use its named consultation tool. Source lives in [`plugins/advisory-team/`](./plugins/advisory-team/). Publishing this GitHub repository alone does not install the modes in Amp.

## Amp Custom Mode Dials

[`plugins/amp-custom-mode-dials.ts`](./plugins/amp-custom-mode-dials.ts) fills the useful gaps between Amp's built-in modes:

| Mode | Position | Main agent | Oracle | Subagents |
| --- | --- | --- | --- | --- |
| **Swift** | Low → Medium | Sonnet 5, medium | Fable 5.1, medium | Sonnet 5, medium |
| **Weave** | Medium → High | Opus 5.5, medium | Fable 5.1, medium | Sonnet 5, medium |
| **Prime** | High → Ultra | Fable 5.1, high | Fable 5.1, high | Opus 5.5, medium |

### Why this routing

- **Swift** keeps a Medium-style workflow but prioritizes direct execution. Sonnet 5 runs both the main loop and delegated work at medium effort. It does not require Fast: Anthropic's Fast API supports Opus models, not Sonnet 5.
- **Weave** is the focused all-Anthropic mode. Opus 5.5 leads implementation at its recommended starting effort of medium, Sonnet handles delegated work at medium effort, and Fable is reserved for difficult judgments.
- **Prime** extends High rather than Ultra. Fable 5.1 leads at high effort, Opus 5.5 handles bounded delegated work at medium effort, and high-effort Fable is reserved for unresolved high-impact decisions.

Plugin agent modes cannot enforce a fixed token ceiling, so Prime cannot guarantee a precise percentage below Ultra. Its prompt, effort, delegation, and Oracle policy are deliberately configured to avoid Ultra-style exhaustive exploration.

The [realistic async-cache benchmark](./docs/amp-custom-mode-dials-benchmark.md) records earlier configurations; it does not validate this new routing.

## Distill

Videos and transcripts are research inputs. The primary deliverable is an original analyst-authored
article or whitepaper in its own voice, organized around a reader decision and independent thesis,
not a recap or fact-check audit. A required prewriting analytical brief maps the argument to evidence
and counterevidence; citations and panels carry provenance. Independent review marks a faithful
but recap-dominated article NEEDS REVISION, preserving sound evidence while rebuilding the argument.
Useful recap passages are allowed; unsupported central claims receive FAIL. Only PASS permits
editorial approval, followed by the remaining publication checks.

[`skills/distill/`](./skills/distill/SKILL.md) turns up to ten public YouTube videos into reusable evidence (timed original and English transcripts, selected frames, checksummed manifests), an evidence-backed brief, and an offline HTML site (cover, article, brief, per-video transcripts, gallery, glossary, references, with offline search, Copy Page Markdown, and house light/dark plus 20 attributed reader theme families) plus an article PDF, packaged as a ZIP with optional verified Azure Blob archival. A complete article needs at least 1000 narrative body words (target 1200–1500+, refused below the floor; short drafts must be `partial`), is written to an entice / engage / empower rubric, and its page carries escaped search and share metadata (description, Open Graph, Twitter, JSON-LD, and a canonical link only for a user-supplied public URL); offline packages are not crawlable until hosted. Amp does the listening, visual judgment, research, and writing; a standard-library Python CLI (`scripts/distill.py`) does download, frames, validation, rendering, packaging, sign-off, archival, and guarded media cleanup.

Invoke with “distill this video” or “distill these videos” and the YouTube URLs. Formerly
`distilling-videos`; the runtime cache and archive format identifiers retain their old names for
compatibility. Historical evaluation/spec filenames are unchanged.

| Area | Status |
| --- | --- |
| Evidence, rendering, packaging, sign-off, archive/cleanup logic | Implemented; unit-tested offline with fake media tools, browser, and Blob transport; end-to-end evaluation with real ffmpeg and Chrome Canary in [`docs/distilling-videos-evaluation.md`](./docs/distilling-videos-evaluation.md) |
| Transcription | No provider adapter and no provider selected: Amp must supply a normalized transcript (manual, captions, agent, or a provider the user runs). Captions and agent transcripts need recorded audio checks covering every transcript segment before sign-off releases media; partial spot checks are recorded but block sign-off. Neither is a measured accuracy rate. Not unattended end to end |
| Provider choice and accuracy | Shortlist and benchmark protocol only; paid benchmark not run, no provider recommended, no transcription/caption/translation accuracy measured |
| Live YouTube download (macOS) | Tested once on one public video: first download HTTP 403 (yt-dlp warned no JavaScript runtime), then succeeded with node; four later runs succeeded. Intermittent. `download --js-runtime` now selects the runtime explicitly |
| Real PDF (macOS, Chrome Canary) | Tested in the evaluation |
| Amp orbs (Linux) | Real FFmpeg/Chromium fixture evaluation: 475 checks passed; 141 Python and 4 Bun tests passed. Synthetic media and supplied transcripts; no live-provider accuracy claim |
| Live Azure Blob | Not tested; requires an authorized disposable container/prefix and private credentials |
| GitHub Actions archive hand-off | Blocked: needs a producer workflow that does not exist |

Recommended invocation: Medium mode with Fast where supported (a user preference; the skill cannot enforce modes or cap billing). Run `skills/distill/scripts/bootstrap.sh` once to create a private venv with `yt-dlp[default]` (including the `yt-dlp-ejs` challenge solver scripts) and check `ffmpeg`, a browser, and the JavaScript runtime yt-dlp needs for YouTube (deno by default; node or quickjs via `download --js-runtime`); it installs nothing globally, edits no yt-dlp config, and handles no credentials.

## Grilling

[`skills/grilling/`](./skills/grilling/SKILL.md) interviews you at the start of a task to turn a vague or partly detailed requirement, plan, or question into a confirmed, agent-ready brief. It sizes the request first (clear requests proceed without questions), looks up facts instead of asking, asks one to three high-impact questions per round with a recommended answer for each, runs an edge-case and pre-mortem pass using [`reference/edge-cases.md`](./skills/grilling/reference/edge-cases.md), and keeps grilling until a concreteness checklist passes. It ends with a confirmed brief covering the final shape, scope, requirements, edge cases, and verification, plus a step-by-step work plan and a ready-to-paste prompt for the agent that picks it up. It is model-invoked: it triggers at the start of most planning, design, build, or decision tasks and on phrases such as "grill me", "red-team this", "pre-mortem", "what could go wrong", "spec this out", or "write a PRD", and skips clear, small requests. Sources and design choices are in [`docs/grilling-research.md`](./docs/grilling-research.md). LLM-judged trigger and behavior evaluations live in [`evals/grilling/`](./evals/grilling/README.md), with results in [`docs/grilling-evaluation.md`](./docs/grilling-evaluation.md).

## Crafting

[`skills/crafting/`](./skills/crafting/SKILL.md) (formerly `designing-experiences`) takes a use case, finds the real need behind it, and crafts a design-worthy experience at every touchpoint where a person or an AI agent interacts. It covers 31 surfaces in nine families: terminal (CLI, TUI), screens (web, iOS, Android, macOS, Windows), ambient (watch, TV, car, spatial, kiosk, device screens), conversation (chat, voice), messaging (notifications, email, SMS), agents (APIs, MCP tools, agent-to-agent, webhooks, agent docs), social, physical (print, packaging, signage), and media (presentations, video, documents, data visualization).

The workflow is: understand (demystify the use case into a job, actors, moments of truth, measures, and experience principles, grilled with the `grilling` skill when vague), journeys and a touchpoint × state matrix, budgeted research, a mood board with named directions, an experience system (tokens, voice, motion, agent contract, production specs), a mockup or transcript for every state, a critique loop against an anti-slop rubric, and a handoff spec. Entry points also cover discovery only, accessibility audits (WCAG 2.2 with per-surface test scripts), user research (study plans, interview and usability guides, agent usability tests, synthesis), motion, critique, and inspiration. Audiences from Gen Alpha to Millennials, including child-safety requirements, are part of the brief and the rubric.

Research climbs a cost ladder: local `.design/` cache and Figma, then Mobbin and Parallel Search, then Firecrawl `branding` scrapes of a shortlist, then at most one Parallel Task deep research run per brief. `scripts/design_kit.py` (standard library) prices each paid call before it is made, refuses calls over the per-brief budget (default $0.30 Parallel, 15 Firecrawl credits, 10 Mobbin searches), gates handoff on journey and per-surface state coverage (including alt text on every social asset), lints MCP tool lists for "Not for" clauses, input schemas, and all four annotation hints, and lints reply drafts (at most three questions, each with a recommendation). Every design starts from an explicit angle (`reference/angle.md`) and ends with a critic pass by a principal designer and architect persona (`reference/critic.md`); `check` requires both.

Requires the Mobbin, Parallel Search, Firecrawl, and Figma MCP servers, plus the Parallel Task MCP (`https://task-mcp.parallel.ai/mcp`, OAuth) for deep research; without it the skill falls back to Parallel Search. Trigger it with requests to craft, design, mock up, prototype, polish, critique, audit, research, or animate any experience, or to find UX inspiration.

LLM-judged routing and behavior evaluations live in [`evals/crafting/`](./evals/crafting/README.md), with results and consolidated judge feedback in [`docs/crafting-evaluation.md`](./docs/crafting-evaluation.md).

## Delivering

[`skills/delivering/`](./skills/delivering/SKILL.md) carries a major feature, use case, or concrete
requirement through outcome-driven delivery. `grilling` confirms expectations; `crafting` can
shape the experience; `delivering` requires a whiteboard defense before implementation handoff,
then executes the approved brief without repeating the interview. The owner explains the outcome,
data flow, choices, invariants, threats, and failure limits. The receiving agent explains the plan
back from the transferred materials; function-name recall is not required.
Invoke it with “use delivering for this feature” or “deliver this approved brief.”

Each small slice follows assessment, measurable outcome, meaningful failing harness, minimal
implementation and working commits, real user journeys, correctness/security review, regression
repair and revalidation, a distinct second review, customer-value assessment, and authorized dev
integration. Consequential changes require independent reviews. Compact mission records support
safe resumption; missing evidence, stale approvals, and ambiguous side effects do not become passes.

Communication supports standard/formal records and editorial explanations with descriptive
headers, both guided by ASD-STE100 principles without an unvalidated compliance claim. ELI5 short
forms contain fewer than 300 words and keep essential risks and blockers. Default budgets are
4,000 tokens per task and 30,000 per session unless explicitly overridden; exact accounting and
enforcement require runtime telemetry and are disclosed as unavailable when absent. The workflow
uses deterministic tools for mechanical work, preserves repository conventions, and requires
direct inspection of the produced artifact before completion.

This is an instruction-only skill, not programmatic enforcement or a background coordinator.
Its [mission record](./skills/delivering/reference/mission-record.md) and
[review/recovery guidance](./skills/delivering/reference/review-and-recovery.md) use existing Amp
tools. [Research](./docs/delivering-research.md) records the design rationale;
[evaluations](./evals/delivering/README.md) distinguish simulated decisions from live execution.
Install/publish `grilling` alongside it for the expectation loop; if unavailable, the agent reports
the dependency rather than silently installing it. Source integration does not publish either
skill to Amp Personal Skills. Rolling, stable release, deployment, and Personal publication retain
their separate gates.

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

The check loads every plugin through the installed Amp CLI, runs advisory-team wiring and tool-allowlist tests with Bun, runs the Python skill-script tests (including executing every documented `distill` JSON example through the CLI), syntax-checks skill shell scripts, verifies formatting errors detectable by Git, and validates the required metadata and 500-line limit of every skill package. It needs `amp`, `bun`, and `python3`; the tests make no network, paid, or cloud calls.

Pull requests targeting `dev` and pushes to `dev` run the same command in
[`Validate extensions`](./.github/workflows/check.yml). Its stable required check
is **Extension checks**, emitted by GitHub Actions. The workflow uses pinned
actions/tool versions, verifies the Amp binary checksum, grants read-only repository
access, and supplies no Amp or cloud credentials. PR code runs on disposable
GitHub-hosted Ubuntu runners; no Depot runner is configured for this repository.

`dev` requires a pull request, an up-to-date successful **Extension checks** result
from GitHub Actions, and resolved review conversations. Protection applies to
administrators and disallows force pushes and deletion. No mandatory human review
count is imposed: mission-owner acknowledgment for high-risk/ask-mode work belongs
to the delivery workflow, while low/medium work may merge automatically. These
controls do not make an agent with repository-administration credentials unable
to change policy. Rolling/stable promotion and extension publication remain separate.

## Publish

Amp stores personal plugins and personal skills in separate global repositories:

- `amp plugins repositories`
- `amp skills repositories`

Copy standalone plugin entry points, or complete directory plugins such as `advisory-team/`, to the root of the Personal Plugins repository. Do not omit supporting Markdown files. Copy each complete `skills/<skill-name>/` directory to the root of the Personal Skills repository. Review and commit changes, then push only after explicit approval; new threads load published versions automatically.

Never commit API keys, provider credentials, access tokens, or generated secret-bearing settings here.

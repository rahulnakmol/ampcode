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

## Distilling videos

Videos and transcripts are research inputs. The primary deliverable is an original analyst-authored
article or whitepaper in its own voice, organized around a reader decision and independent thesis,
not a recap or fact-check audit. A required prewriting analytical brief maps the argument to evidence
and counterevidence; citations and panels carry provenance. Independent review must reject even a
faithful source-led recap, and must also reject unsupported consultancy-style opinion.

[`skills/distilling-videos/`](./skills/distilling-videos/SKILL.md) turns up to ten public YouTube videos into reusable evidence (timed original and English transcripts, selected frames, checksummed manifests), an evidence-backed brief, and an offline HTML site (cover, article, brief, per-video transcripts, gallery, glossary, references, with offline search, Copy Page Markdown, and house light/dark plus 20 attributed reader theme families) plus an article PDF, packaged as a ZIP with optional verified Azure Blob archival. A complete article needs at least 1000 narrative body words (target 1200–1500+, refused below the floor; short drafts must be `partial`), is written to an entice / engage / empower rubric, and its page carries escaped search and share metadata (description, Open Graph, Twitter, JSON-LD, and a canonical link only for a user-supplied public URL); offline packages are not crawlable until hosted. Amp does the listening, visual judgment, research, and writing; a standard-library Python CLI (`scripts/distill.py`) does download, frames, validation, rendering, packaging, sign-off, archival, and guarded media cleanup.

| Area | Status |
| --- | --- |
| Evidence, rendering, packaging, sign-off, archive/cleanup logic | Implemented; unit-tested offline with fake media tools, browser, and Blob transport; end-to-end evaluation with real ffmpeg and Chrome Canary in [`docs/distilling-videos-evaluation.md`](./docs/distilling-videos-evaluation.md) |
| Transcription | No provider adapter and no provider selected: Amp must supply a normalized transcript (manual, captions, agent, or a provider the user runs). Captions and agent transcripts need recorded audio checks covering every transcript segment before sign-off releases media; partial spot checks are recorded but block sign-off. Neither is a measured accuracy rate. Not unattended end to end |
| Provider choice and accuracy | Shortlist and benchmark protocol only; paid benchmark not run, no provider recommended, no transcription/caption/translation accuracy measured |
| Live YouTube download (macOS) | Tested once on one public video: first download HTTP 403 (yt-dlp warned no JavaScript runtime), then succeeded with node; four later runs succeeded. Intermittent. `download --js-runtime` now selects the runtime explicitly |
| Real PDF (macOS, Chrome Canary) | Tested in the evaluation |
| Amp orbs (Linux), live Azure Blob | Not tested |
| GitHub Actions archive hand-off | Blocked: needs a producer workflow that does not exist |

Recommended invocation: Medium mode with Fast where supported (a user preference; the skill cannot enforce modes or cap billing). Run `skills/distilling-videos/scripts/bootstrap.sh` once to create a private venv with `yt-dlp[default]` (including the `yt-dlp-ejs` challenge solver scripts) and check `ffmpeg`, a browser, and the JavaScript runtime yt-dlp needs for YouTube (deno by default; node or quickjs via `download --js-runtime`); it installs nothing globally, edits no yt-dlp config, and handles no credentials.

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

The check loads every plugin through the installed Amp CLI, runs advisory-team wiring and tool-allowlist tests with Bun, runs the Python skill-script tests (including executing every documented `distilling-videos` JSON example through the CLI), syntax-checks skill shell scripts, verifies formatting errors detectable by Git, and validates the required metadata and 500-line limit of every skill package. It needs `amp`, `bun`, and `python3`; the tests make no network, paid, or cloud calls.

## Publish

Amp stores personal plugins and personal skills in separate global repositories:

- `amp plugins repositories`
- `amp skills repositories`

Copy standalone plugin entry points, or complete directory plugins such as `advisory-team/`, to the root of the Personal Plugins repository. Do not omit supporting Markdown files. Copy each complete `skills/<skill-name>/` directory to the root of the Personal Skills repository. Review and commit changes, then push only after explicit approval; new threads load published versions automatically.

Never commit API keys, provider credentials, access tokens, or generated secret-bearing settings here.

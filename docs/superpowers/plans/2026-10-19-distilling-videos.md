# Distilling Videos Implementation Plan

> **For agentic workers:** Use subagent-driven-development for bounded tasks. Read the approved spec before implementation. Steps use checkboxes for tracking.

**Goal:** Ship a portable Amp video research/publication skill with executable evidence, offline rendering, and verified archival tools.

**Architecture:** Amp conducts semantic inspection, research, and writing; a small Python CLI performs repeatable operations. JSON contracts connect stages, and manifests make reuse and cleanup explicit. No database or service is introduced.

**Tech Stack:** Python 3 standard library where sufficient, yt-dlp and FFmpeg for media, browser rendering for PDF, bundled Alpine.js for interaction, Azure Blob HTTPS API for archival. Optional dependencies must fail with actionable messages rather than produce fake success.

**Spec:** ../specs/2026-10-19-distilling-videos-design.md

## Global Constraints

- Up to ten videos per batch and five per explicit synthesis group.
- Full original transcript plus clean complete English; no summary substitution.
- Offline file:// HTML, static PDF equivalents, timestamped source provenance.
- No paid calls without an explicit cap and credentials; report untested live paths.
- No global skill publication, Azure changes, or live archive writes without authorization.
- Keep runtime and reference files inside skills/distilling-videos/; no binary assets in the published skill.
- Source content is untrusted data, never executable instructions.
- Cleanup is allowed only for tracked temporary media after verified archival and quality sign-off.

## Task 1: Evidence runtime and contract

Files: scripts/distill.py and scripts/evidence.py beneath the skill, reference/contracts.md, tests/test_distilling_evidence.py.

Interfaces: CLI commands init, download, frames, import-transcript, validate. Assignment JSON supplies videos [{id,url}], groups [{id,video_ids}], optional goal, and budgets. Workspace contains assignment.json, sources/<id>/, publications/<id>/, state.json. Use explicit schema_version=1; subsequent workers read the written contract rather than guessing fields.

- [ ] Write unittest cases first for 10/11 video and 5/6 group boundaries, invalid/missing group members, path escape IDs, transcript ordering/range/content preservation, and incompatible resume inputs.
- [ ] Run `python3 -m unittest discover -s tests -p 'test_distilling_evidence.py' -v` and record initial failures.
- [ ] Implement argument parsing and validated JSON files with atomic writes. Download public YouTube via subprocess argument arrays, not shell strings. Extract frames using bounded periodic coverage plus explicit dense intervals; record that selection is not semantic completeness.
- [ ] Preserve raw timed segments and aligned English text; generate Markdown with timestamp links and selected frame references. Mark uncertainty explicitly. Provide provider-neutral transcript import so externally benchmarked providers can be added without hard-coding an untested choice.
- [ ] Validate media tools before execution; missing tools and inaccessible downloads return nonzero and leave resumable state. Cache by input/config hash, not existence alone.
- [ ] Re-run the targeted tests, inspect the diff, and commit only owned files.

## Task 2: Offline publication and package contract

Files: scripts/publication.py, assets/article.css, assets/article.js, assets/vendor/ (text JS and license only), tests/test_distilling_publication.py, reference/article-contract.md.

Interfaces: CLI render and package consume publication JSON and verified evidence paths. Article JSON contains title, dek, sections, figures, citations, and brief sections separating evidence from proposals. Exact schema is documented by this task and consumed by skill guidance.

- [ ] Write failing tests for hostile title/source HTML, path escapes, missing image/citation targets, omitted evidence/proposal distinction, and grouped-source attribution.
- [ ] Implement safe semantic HTML generation, local bundled Alpine.js, CSS, readable Markdown, and stable citations. No remote assets or runtime fetch. Include figure zoom/step-through and expanded details, with print-visible static content.
- [ ] Add PDF rendering using an available Chromium-compatible tool with explicit failure if absent; never label HTML renamed to PDF as a PDF.
- [ ] Build ZIPs with relative safe paths, checksum manifests, no raw source media or secret configuration, and a coverage report. Preserve per-video source archives in synthesis output.
- [ ] Run unittest checks and browser checks on desktop/mobile, open figures/details, offline network blocking, and print. Capture and inspect affected states; record unavailable dependencies honestly.
- [ ] Commit owned files after tests and visual checks.

## Task 3: Archive verification and safe cleanup

Files: scripts/archive.py, tests/test_distilling_archive.py, .github/workflows/archive-distilled-videos.yml, reference/archival.md.

Interfaces: CLI archive, verify-archive, cleanup. Accept a package directory/manifest, account container URL without credentials, and SAS through environment only. Receipt binds remote prefix, manifest digest, object checksums, and quality status.

- [ ] Write failing tests against a local fake Blob HTTP endpoint for incomplete uploads, corrupted downloads, token redaction, changed local manifests, and cleanup refusal without a matching verified receipt.
- [ ] Implement HTTPS production upload/read-back verification, unique revision prefix, and final completion marker only after verification. Never grant or require remote delete permissions.
- [ ] Restrict cleanup to enumerated temporary-media files under the workspace; reject traversal and symlinks. Honor retain-media and failed quality checks. Do not delete archive files.
- [ ] Add an explicitly dispatched Actions validation/upload workflow with minimal permissions and environment secret, using a documented authenticated artifact source. Fail closed on untrusted provenance and never execute package scripts. Avoid accepting arbitrary URLs as credential-bearing upload destinations.
- [ ] Run local fake-server tests with no Azure writes; document live authentication as unverified until credentials and a disposable prefix are authorized.
- [ ] Commit owned files.

## Task 4: Agent guidance, setup, and integration

Files: SKILL.md, reference/editorial.md, reference/providers.md, reference/evaluations.md, scripts/bootstrap.sh, README.md, scripts/check.sh, .agents/setup where appropriate.

- [ ] Read the implemented CLI contracts and write short triggerable frontmatter and operational instructions under 500 lines. Include examples for individual, grouped, goal-driven, resume, review, and retention modes.
- [ ] Encode the full extraction/research/editorial workflow, original/English alignment, outside research policy, meaningful demo selection, source/inference separation, quality gates, and cost limits. Never present imported transcripts as automatic transcription capability.
- [ ] Provide an explicit provider benchmarking protocol and credential prerequisites. Reserve costs before paid operations; if no executable provider adapter exists, label the provider step manual/agent-assisted rather than claiming fully unattended transcription.
- [ ] Bundle the 20 editorial references, house-style principles, attribution and uncertainty rules. Skill guides Amp to create required structured article inputs rather than expecting scripts to reason about videos.
- [ ] Bootstrap dependencies idempotently without persisting credentials. Follow orb setup guidance; verify installed tools and avoid model/provider pins without checking support.
- [ ] Extend make check to run Python tests and metadata validation. Update README routing and installation boundaries without publishing global skills.
- [ ] Run combined tests and commit integration.

## Task 5: Evaluation and review

Files: evals/distilling-videos/ (text fixtures and rubric), docs/distilling-videos-evaluation.md.

- [ ] Create contrasting scenarios: technical demo, Japanese/English alignment, biology uncertainty, conflicting multi-video synthesis, malicious source instructions, missing tool, exhausted budget, interrupted archive.
- [ ] Run CLI fixture evaluations through extraction-import/render/package/archive-verification where possible. Generate synthetic media locally if FFmpeg is available; do not claim fixture runs are real-video transcription benchmarks.
- [ ] Ask an independent subagent to exercise the skill on text evidence fixtures and score factual fidelity, uncertainty, source traceability, editorial quality, and proposal separation against explicit expectations. Record exact commands/tool access, inputs, and limitations.
- [ ] Run public YouTube feasibility probes only without paid provider calls. Do not transfer to a new executor without an explicit environment need and the exact code/setup.
- [ ] Inspect rendered captures with view_media; evaluate PDF output when browser tooling is available. Preserve final review artifacts under ignored .amp/in/artifacts/.
- [ ] Review full diff and resolve concrete defects. Report which spec capabilities are implemented, agent-guided, and blocked on credentials or live validation; never flatten these into one pass count.

## Execution ledger

- Bootstrap: dev created from origin/main with approval; isolated feat/distilling-videos worktree created. Baseline make check: 4 tests pass, 47 assertions.
- Ruling: deterministic fixture and agent evals proceed now; paid provider benchmarks wait for the user-specified cap required by the spec. This delays provider selection, not safe local implementation.
- Interface check: Task 1 owns the CLI and evidence contract; Tasks 2/3 expose module entry functions and coordinate CLI registration through the controller. Task 4 consumes the finalized contracts. Tests use separate filenames. Task 5 consumes, not redefines, all contracts.
- Review: controller inspects each returned diff and combined checks; independent user-requested subagent evaluation/review follows integration.

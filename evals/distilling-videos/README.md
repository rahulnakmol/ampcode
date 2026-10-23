# distilling-videos evaluation fixtures

Runnable, end-to-end evaluation of `skills/distilling-videos` with controlled inputs and known
ground truth. Results and interpretation: `docs/distilling-videos-evaluation.md`.

This is a **skill evaluation** (does the workflow produce faithful, traceable, safe deliverables and
refuse unsafe shortcuts?). It is **not** the paid provider benchmark in
`reference/evaluations.md`, and nothing here measures transcription or translation accuracy: the
synthetic videos carry a sine tone, not speech, and the transcripts are ground truth by construction.

## Independent-analysis contrastive assessment

Use `editorial-assessment.md` as the handoff to a fresh judge, with
`fixtures/editorial-contrast.md` (one evidence dossier, four candidate excerpts). Withhold
`editorial-expected.md` until the judge records verdicts. Expected outcomes distinguish a faithful
recap, an audit, unsupported consultancy prose, and grounded independent analysis. These short
excerpts test editorial direction, not full-publication depth or rendering. The existing composed
articles remain historical mechanical/fidelity fixtures, not exemplars approved under the new gate.
`run_eval.py` does not judge this semantic distinction; no keyword-only grader is provided.

## Layout

| Path | What it is |
| --- | --- |
| `fixtures/assignment.json` | 4 videos, 1 synthesis group (`g-bio`), goal, budgets (batch 1.00, per video 0.40 USD) |
| `fixtures/media.json` | Scene spec for synthetic slide videos (drawtext over color, sine audio): talking heads, terminal input/action/output, a blurred unreadable frame, an on-screen prompt injection, Japanese title, unlabeled chart |
| `fixtures/transcripts/*.json` | Fixture transcripts: English technical demo with injection bait and an inaudible number; Japanese with labeled translations and a lossy term (定石); two conflicting biology videos with unclear years |
| `fixtures/ground-truth.json` | Known facts, required citations, forbidden assertions, uncertain segments, unreadable frames, conflict pair, frame plans |
| `fixtures/articles/<P>/` | Evaluator-composed `article.json` and original SVG figures (the agent-guided editorial exercise output) |
| `fixtures/reviews/<P>.json` | Quality reviews for `signoff` (gap ends are bound to the measured media duration at run time) |
| `rubric.md` | Editorial rubric: machine checks, negative controls, and the 1–5 judgment scale |
| `run_eval.py` | Harness: real CLI on generated media, editorial checks, sign-off, fake-Blob archive and cleanup, optional live YouTube probe |
| `capture.mjs` | Real-browser checks and screenshots over the DevTools protocol (Node 22+, no npm packages): every site page offline; desktop navigation collapse and persistence; mobile overlay navigation with focus trap; citation evidence panel and mobile sheet; Copy Page with the real clipboard, the `execCommand` fallback, and the manual-selection fallback; search (including CJK); filters; gallery viewer by buttons, keys, drag, and touch; themes, persistence, blocked storage, system dark; GSAP missing; reduced motion; print emulation; no JavaScript; Alpine, `article.js`, or both blocked with a saved collapse and theme (navigation visible on desktop and mobile, no dead controls, citations still links); search and hash links to a filtered-out segment (revealed); zoom during the viewer entrance tween; every page's textarea value equal to its `.md` |

## Run

Needs Python 3.9+, `ffmpeg`/`ffprobe` with `drawtext` (libfreetype), and system fonts listed in
`media.json` (macOS paths first, then common Linux paths). PDF, sign-off approval, archive, and
captures need a Chromium-family browser.

```sh
python3 evals/distilling-videos/run_eval.py \
  --tools-bin DIR_WITH_FFMPEG_FFPROBE_YTDLP \
  --browser "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
  --capture \
  --live-youtube https://youtu.be/G3VbsTdgLWE --live-timeout 180
```

Outputs go to `.amp/in/eval-run/` (ignored; recreated each run, and only if it carries the harness
marker file): `results.json`, `summary.md`, `ws/` (the evaluated workspace), and `captures/`
(screenshots plus `report.json`). Exit 0 means every executed check passed; 1 means a check failed;
3 means ffmpeg/ffprobe were not found. Results are reported per category, never as one score.

Without `--browser`, PDF is skipped, packages are `complete: false`, sign-off is blocked, and the
archive scenarios are reported as not run. Without `--live-youtube`, no network is used.

## Safety

- No paid calls, no Azure, no credentials. Archive scenarios inject an in-process fake Blob
  transport with a fake SAS (`sig` is a placeholder) exactly as the unit tests do.
- The live probe reads public metadata, downloads the media into the ignored output directory,
  samples frames, and fetches automatic captions. It never bypasses logins or DRM, and it
  classifies failures (network, rate limit, HTTP 403, unavailable) instead of treating any failure
  as proof that the video does not exist.
- Fixture text contains deliberate prompt-injection bait (`evil.example`). It is data; the checks
  verify that it is never followed, linked, or rendered as markup.

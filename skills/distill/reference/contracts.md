# Evidence contracts (schema_version 1)

The source of truth is `scripts/evidence.py`, and `scripts/distill.py` exposes it on the command line. Later stages read these files and do not guess fields. Every JSON file written by the runtime has `"schema_version": 1`. Writes are atomic: the runtime writes a temporary file in the same directory, fsyncs it, then calls `os.replace`. The runtime uses only the Python 3.9+ standard library. Media commands also need `yt-dlp`, `ffmpeg`, and `ffprobe` on `PATH`.

## CLI

```text
distill.py init              --workspace W --assignment A.json
distill.py download          --workspace W --video ID [--format SEL] [--from-file MEDIA]
                             [--js-runtime deno|node|quickjs [--js-runtime-path ABS]] [--timeout 1800]
distill.py frames            --workspace W --video ID [--interval 10] [--dense S-E[:STEP]]... [--at T]...
                             [--scene-threshold 0.3] [--max-frames 600]
distill.py import-transcript --workspace W --video ID --transcript T.json [--duration SECONDS]
distill.py select-frames     --workspace W --video ID --frames f000060000,f000061250 [--note TEXT]
distill.py validate          --workspace W [--video ID]... [--require-complete]
distill.py budget reserve    --workspace W --step S --provider P --amount X --approval REF [--video ID] [--note]
distill.py budget settle     --workspace W --id rNNNN --actual X --basis provider-invoice|provider-usage-api|estimate
distill.py budget release    --workspace W --id rNNNN
distill.py budget status     --workspace W
```

Successful commands print JSON to stdout. Errors go to stderr. Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | `validate` found errors |
| 2 | Contract or usage error. Nothing is marked complete. |
| 3 | A required tool is missing. The stage is marked `failed`, and the command can be resumed after the tool is installed. |
| 4 | Budget refused |
| 5 | An external tool failed or the download is inaccessible. The stage is marked `failed`, and partial output is discarded. |

The status field in the command output is one of the following:

| Command | Possible status values |
| --- | --- |
| `init` | `created`, `resumed` |
| `download` | `downloaded`, `reused` |
| `frames` | `extracted`, `reused` |
| `import-transcript` | `imported`, `reused` |
| `select-frames` | `selected` |

## Safety rules

- IDs for videos, groups, segments, steps, and providers must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`. The runtime rejects path separators, `.` and `..`, leading `-`, whitespace, and non-ASCII characters.
- `safe_path(root, rel)` rejects empty or absolute paths, any `..` component, backslashes, symlinks at any component, and any resolved path that leaves `root`.
- Video URLs must be `https` on `youtube.com`, `www.youtube.com`, `m.youtube.com`, or `youtu.be`. They cannot contain credentials or a port, and they must carry an 11-character video ID in one of these forms: `watch?v=`, `youtu.be/`, `shorts/`, `live/`, or `embed/`.
- Subprocesses receive argument arrays and never run through a shell. Before a media tool starts, the runtime removes environment variables whose names look like credentials (`SAS`, `SECRET`, `TOKEN`, `PASSWORD`, `API_KEY`, `ACCESS_KEY`, `CONNECTION_STRING`, `AZURE_STORAGE`). Error text has SAS query parameters and `Authorization` values redacted.
- Source text is untrusted data. Markdown output escapes it, so no raw HTML, links, or headings from the source are rendered. JSON stores it verbatim.

## Assignment (`assignment.json`)

Input:

```json
{
  "schema_version": 1,
  "videos": [{"id": "v1", "url": "https://www.youtube.com/watch?v=XXXXXXXXXXX", "title": "optional"}],
  "groups": [{"id": "g1", "video_ids": ["v1", "v2"], "title": "optional"}],
  "goal": "optional research goal",
  "audience": "optional audience override",
  "budgets": {"currency": "USD", "batch": 10.0, "per_video": 2.0},
  "retain_media": false
}
```

Validation rules:

- There must be 1 to 10 videos, and video IDs must be unique.
- Each group has 2 to 5 members. Every member must be a known video and appear only once in its group. A video belongs to at most one group. Group IDs must be unique and must not collide with video IDs.
- Unknown fields are rejected at every level.
- `budgets` is optional. When present, `currency` is a three-letter ISO code. `batch` and `per_video` are non-negative, and `per_video` cannot exceed `batch`.

The workspace stores a normalized copy with these derived fields:

- `videos[].youtube_id`.
- `publications`: one `{id, kind: "group", video_ids}` per group, then one `{id, kind: "single", video_ids: [id]}` for each ungrouped video.
- Explicit `goal`, `audience`, and `retain_media` values, set to `null` or `false` when absent.

If a derived field is edited, the assignment fails validation.

## Workspace layout

```text
W/assignment.json                normalized assignment
W/state.json                     stage records (below)
W/budget.json                    reservation ledger, created on first reservation
W/.state.lock, W/.budget.lock    fcntl lock files
W/publications/<pub-id>/plan.json  {schema_version, id, kind, video_ids, goal, audience}
W/sources/<video-id>/
  source.json                    source metadata
  media/source.<ext>             temporary original media (tracked)
  audio/audio.flac               16 kHz mono FLAC (tracked temporary media)
  frames/frames.json, frames/full/<frame-id>.jpg, frames/thumbs/<frame-id>.jpg
  selection.json                 selected frame IDs
  transcript/input.json          exact imported bytes
  transcript/segments.json       normalized segments
  transcript/coverage.json
  transcript/original.md, transcript/english.md
```

If you run `init` again with an assignment whose normalized form has the same digest, the workspace resumes. A different assignment returns exit code 2 (`incompatible resume`) and changes nothing. `init` also refuses to use a directory that is not empty and has no `assignment.json`.

Later tasks write publication outputs under `publications/<pub-id>/`. Task 1 writes only `plan.json` there.

## State and reuse (`state.json`)

```json
{"schema_version": 1, "assignment_sha256": "...", "created_at": "...", "updated_at": "...",
 "temporary_media": ["sources/v1/media/source.mp4", "sources/v1/audio/audio.flac"],
 "stages": {"sources/v1/download": {
   "status": "complete", "base": "sources/v1", "config": {}, "config_sha256": "...",
   "inputs": {"<rel>": "sha256"}, "outputs": {"<rel>": "sha256"},
   "started_at": "...", "finished_at": "...", "tool_versions": {}, "error": "only when failed"}}}
```

- Stage keys use the form `sources/<video-id>/<stage>`. The stages are `download`, `frames`, `transcript`, `transcript-markdown`, and `frame-selection`. Paths in `inputs` and `outputs` are relative to `base`.
- A stage moves from `running` to either `complete` or `failed`. `running` replaces any earlier record, so if a process is interrupted, it never leaves a stale `complete`. Work is staged in hidden `.<stage>-partial-<pid>` directories and swapped in only after it succeeds.
- A stage is reused only when the earlier status is `complete`, the input digests are identical, the canonical config digest is identical, and every recorded output still exists with a matching SHA-256. The existence of files alone never counts.
- Configs used for reuse:

  | Stage | Config | Inputs |
  | --- | --- | --- |
  | `download` | URL or local-file SHA-256, format, audio settings, and for yt-dlp downloads `js_runtime` (`{name, path}` or `{name: "yt-dlp-default"}`) | none |
  | `frames` | All sampling options | Media SHA-256 |
  | `transcript` | Raw input SHA-256, duration, gap threshold | `source.json`, if present |
  | `transcript-markdown` | Renderer version | `segments.json`, `source.json`, `frames.json`, and `selection.json`, when present |

- Changing an upstream output makes downstream stages stale. `validate` reports stale stages as checksum errors on their inputs.
- Tool versions are recorded but are not part of the reuse config.

`validate` prints `{ok, errors, warnings, videos: {id: {stage: status}}}`:

- Errors come from assignment, state, or checksum mismatches, selections that reference missing frames, and, with `--require-complete`, any of `download`, `frames`, `transcript`, or `transcript-markdown` that is not complete.
- Warnings come from failed or interrupted stages, transcript gaps, captions-based or unknown-duration coverage, and budget overruns.

## Source metadata (`source.json`)

Fields: `video_id`, `url`, `youtube_id`, `extractor` (`yt-dlp` or `local-file`), `title`, `creator`, `channel_id`, `upload_date`, `duration` (ffprobe seconds), `language`, `captions` (`manual`, `automatic`, `note`), `media` (`path`, `width`, `height`, `has_audio`), `audio` (`path`, `sample_rate`, `channels`), `tool_versions`, and `retrieved_at`. yt-dlp downloads also record `js_runtime` (`name`, `path`, `version`, or `{name: "yt-dlp-default"}`) and `warnings` (yt-dlp `WARNING:` lines, redacted).

Metadata from yt-dlp is untrusted data. The `captions` field lists available caption languages only. It is not a transcript.

`--from-file` registers media that was obtained elsewhere, such as a fallback download on a Mac. Its SHA-256 becomes the reuse input.

## Transcript import (provider-neutral)

The `import-transcript` command takes this input. Any provider, captions source, or manual or agent transcription can produce it.

```json
{
  "schema_version": 1, "video_id": "v1", "language": "ja",
  "provider": {"name": "acme-asr", "kind": "transcription", "model": "optional", "version": "optional"},
  "translation_provider": {"name": "optional"},
  "duration": 95.0,
  "notes": "optional",
  "segments": [{
    "id": "s1", "start": 0.0, "end": 4.5,
    "text": "original-language wording, verbatim",
    "english": "aligned clean English or translation",
    "english_kind": "translation",
    "uncertain": true, "uncertainty": "why",
    "speaker": "optional", "confidence": 0.8, "words": []
  }]
}
```

Field values and rules:

- `provider.kind` is one of `transcription`, `captions`, `manual`, or `agent`.
- `english_kind` is `original`, `clean`, or `translation`. It defaults to `clean` for an `en` source and to `translation` otherwise. A non-English source must use `translation`, and an English source must not.
- Segment IDs are safe and unique. Segments are sorted by `start`. `start` must be at least 0 and `end` must exceed `start`. Segments may overlap by no more than 0.05 s, and `end` may exceed the duration by no more than 0.5 s.
- The duration is taken from `--duration`, then `source.json`, then the transcript's own `duration`.
- `text` and `english` must not be empty. The runtime never trims or rewrites them.
- Unknown fields are rejected so that content cannot be silently dropped or summarized.

Outputs:

- `transcript/input.json` contains the exact input bytes.
- `transcript/segments.json` contains the input segments verbatim plus normalized fields:
  - `start` and `end` as floats.
  - `english_kind`.
  - `uncertain` as a boolean.
  - `inline_markers`: `[inaudible]`, `[unclear]`, `[unintelligible]`, `[crosstalk]`, `[indistinct]`, `[?]`, and short bracketed text ending in `?`, found in `text` or `english` and preserved in place.
  - Top-level fields: `english_label`, `provider`, `translation_provider`, `language`, `duration`, and `notes`. `english_label` is derived from every segment's `english_kind`: `translation` for a non-English source; for English, `original English` when every segment is `original` (pages say "Verbatim English captions" for `captions` providers, else "Verbatim English transcript", and never "cleaned"), `clean English` when every segment is `clean`, otherwise `mixed English` ("Partly cleaned English"). The renderer derives the same label from the segments, so a stale stored label cannot overclaim cleaning.
- `transcript/coverage.json` contains `segment_count`, `duration`, `covered_seconds`, `gap_threshold` (2 s), `gaps` (`[{start, end}]`, including leading and trailing gaps), `uncertain_segment_ids` (segments marked uncertain or containing inline markers), and `warnings`.
- `original.md` and `english.md` contain one escaped block quote per segment, headed by a link such as `## [H:MM:SS](https://www.youtube.com/watch?v=ID&t=Ns) · <segment-id>`. Uncertain segments carry an `**Uncertain:**` note. `english.md` states whether it is a translation, verbatim original English, or cleaned English, notes that frames are sampled, and embeds each selected frame as `[![Frame at H:MM:SS](../frames/thumbs/ID.jpg)](timestamp-url) ([full size](../frames/full/ID.jpg))`. Each frame goes under the last segment that starts at or before it.

## Frames (`frames/frames.json`)

Frame candidates come from several sources, merged at 1 ms resolution:

- Periodic samples at `k * interval` for times below the duration.
- Dense intervals from `START` to `END` inclusive, every `STEP` (default 1 s).
- Explicit `--at` cues, such as transcript cues chosen by Amp.
- Optional ffmpeg scene cues (`select='gt(scene,T)',showinfo`).

If the plan exceeds `--max-frames`, the command exits with code 2 rather than truncating.

The manifest contains:

- `video_id`, `duration`, and `media_sha256`.
- `selection`: `method`, `interval`, `dense`, `cues`, `scene_threshold`, `scene_cues_found`, `max_frames`, `thumb_width` (480), `"semantic_completeness": false`, and `note`.
- `max_sampling_gap_seconds`.
- `frames[]`: `id` (`f` followed by nine digits of milliseconds), `t`, `reasons` (any of `periodic`, `dense`, `cue`, `scene`), `path`, `thumbnail`, `sha256`, and `thumbnail_sha256`. Paths are relative to `sources/<id>/`.

Selection records Amp's visual judgment. `selection.json` contains `video_id`, `frame_ids`, `note`, and `selected_at`. It does not prove the frames were understood.

## Budget ledger (`budget.json`)

The ledger is a hard reservation gate for approved steps with an external price. Callers must reserve before spending.

```json
{"schema_version": 1, "currency": "USD", "ceilings": {"batch": 10.0, "per_video": 2.0},
 "entries": [{"id": "r0001", "video_id": "v1", "step": "transcription", "provider": "acme",
   "amount": 1.5, "approval": "user approval reference", "note": null, "status": "settled",
   "actual": 1.75, "basis": "provider-invoice", "overrun": true,
   "created_at": "...", "finished_at": "..."}]}
```

How it works:

- Reservations run under an exclusive `fcntl` lock, so concurrent processes cannot claim the same allowance.
- The committed amount is the reserved amount for `reserved` entries, the actual amount for `settled` entries, and 0 for `released` entries.
- A reservation is refused with exit code 4 when there is no applicable ceiling, or when the batch or per-video committed amount plus the new amount would exceed the ceiling.
- Refused attempts are not recorded.
- Settling above the reserved amount records `overrun: true`. The overrun counts against future reservations, and `validate` warns about it.
- `budget status` reports committed totals with `"guarantees_all_in_spend": false`.

Limitation: the ledger enforces limits only for callers that use it. It cannot stop a provider from billing beyond a reservation, and it does not track Amp model or token costs. Pair it with provider-side caps where they exist.

## CLI extensions

When `distill.py` builds its parser, it loads the sibling files `publication.py` and `archive.py` by file path if they exist. Each module must define the following:

```python
def register(subparsers) -> None:
    command = subparsers.add_parser("render", help="...")
    command.add_argument("--workspace", required=True)
    command.set_defaults(func=handler)   # handler(args) -> int exit code
```

Handlers may `import evidence` because the scripts directory is on `sys.path`. They should reuse `Workspace`, `safe_path`, `check_id`, `atomic_write_*`, `sha256_file`, `mark_running`, `mark_complete`, `mark_failed`, and `reusable`, and raise `evidence.ContractError` for exit code 2.

Missing modules are skipped. A module without `register` raises `RuntimeError`. Command names must not collide with the built-in commands. To add another module, append its name to `EXTENSION_MODULES`.

## Known limits

- The runtime does not call transcription, translation, or OCR providers. Transcripts arrive through `import-transcript`.
- Frame sampling is bounded. It is not semantic or exhaustive.
- Scene detection depends on ffmpeg heuristics, and it is exercised only with a fake ffmpeg in tests.
- This repository's unit tests use fake `yt-dlp` and `ffmpeg` executables. Real runs were exercised once on macOS in `docs/distilling-videos-evaluation.md` (intermittent HTTP 403, then success); orbs and Linux are untested.
- `download` runs yt-dlp with `--ignore-config`, never `--remote-components`, and only the runtime chosen with `--js-runtime` (deno, node, or quickjs). Without remote components, the challenge solver scripts must come from the `yt-dlp-ejs` package: a PyPI yt-dlp ships without them, and the `default` extra (`pip install "yt-dlp[default]"`, which `bootstrap.sh` uses) supplies them. Official standalone yt-dlp binaries bundle them; third-party packages may not. Every yt-dlp and ffmpeg call in `download` is bounded by `--timeout`; on timeout the tool's process group is killed.
- The runtime needs `fcntl`, so it supports POSIX systems such as macOS, Linux, and orbs.

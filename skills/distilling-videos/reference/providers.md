# Transcription and translation providers

Status on 2026-10-19: **no provider adapter is implemented, and no provider has been benchmarked.**
The runtime accepts transcripts only through `distill.py import-transcript`. Paid benchmarking waits
for a user-approved spending cap (see `evaluations.md`). Until then, do not call any provider the
"best" or default, and do not describe transcription as automatic.

## Routes available now

| Route | `provider.kind` | When | Cost |
| --- | --- | --- | --- |
| User runs a provider and hands over its output | `transcription` | User has an account and approves the spend | Paid; reserve first |
| Amp calls a provider API on the user's behalf | `transcription` | Credentials provided via secret, cap approved, budget reserved | Paid; reserve first |
| YouTube captions via `yt-dlp` | `captions` | Captions exist; always spot-check | Free |
| Local open-weight model (for example faster-whisper on CPU) | `transcription` | User allows a local install and accepts slow CPU runs | Free, slow, unbenchmarked |
| Manual or agent transcription | `manual` / `agent` | Short videos or gap repair | Amp usage only |

Each route ends in the same normalized JSON (`contracts.md`, "Transcript import"). Map provider
words or segments to `segments[]`, keep the original wording in `text`, write aligned `english`,
and convert low confidence into `uncertain` with a reason. Record `provider.model` and `version`.

## Shortlist to benchmark (not a recommendation)

Facts below come from vendor documentation read on 2026-10-19. Re-check limits and prices before
use; vendor claims and vendor-published benchmarks are not evidence for this workload.

| Candidate | Documented properties relevant here | Source |
| --- | --- | --- |
| OpenAI transcription | `gpt-transcribe` recommended for general transcription; `whisper-1` documented for word/segment timestamps via `timestamp_granularities[]`; 25 MB file limit (chunk long audio) | https://developers.openai.com/api/docs/guides/speech-to-text |
| ElevenLabs Scribe v2 | 90+ languages; word or character timestamps; diarization; keyterm prompting at extra cost; files under 5 GB | https://elevenlabs.io/docs/api-reference/speech-to-text/convert |
| AssemblyAI Universal | Async transcription with word timestamps and confidence; language detection | https://www.assemblyai.com/docs |
| Azure AI Speech fast transcription | Synchronous, faster than real time; segment and word timestamps; locale or multilingual model; fits an existing Azure subscription | https://learn.microsoft.com/azure/ai-services/speech-service/fast-transcription-create |
| Mistral Voxtral Mini Transcribe V2 | 13 languages incl. Japanese; segment/word timestamps; up to 3 h per request; docs say timestamps are not combinable with `language` | https://docs.mistral.ai/studio-api/audio/speech_to_text/offline_transcription |
| faster-whisper (local) | Open weights, CPU `int8` mode, word timestamps; no API cost; slow without a GPU (orbs may not have one) | https://github.com/SYSTRAN/faster-whisper |

Selection rule after benchmarking: prefer a provider the user already pays for if it meets the
measured quality bar; otherwise the cheapest provider that meets it. Write the result into
`evaluations.md` with the evidence, then propose (not silently add) an adapter.

## Credentials

- Never ask the user to paste keys into the thread. Use an Amp project secret in orbs, or an
  environment variable the user sets locally (for example `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`,
  `ASSEMBLYAI_API_KEY`, `MISTRAL_API_KEY`, or an Azure Speech key/endpoint).
- A consumer subscription does not imply API credentials. Ask.
- Keep keys out of transcripts, notes, manifests, logs, and commands echoed to the user.
  `distill.py` strips credential-like variables before running media tools, but your own
  provider calls must not print headers or signed URLs.
- Packaging rejects secret-looking content; treat a rejection as a leak to fix, not to bypass.

## Paid call procedure

1. Confirm the assignment has `budgets` and the user approved this provider and cap.
2. Estimate cost from duration × documented price; add margin for chunk overlap and retries.
3. `$D budget reserve --workspace "$W" --step transcription --provider PROVIDER --amount EST --approval "REF" --video V`
4. Extract audio if needed (`download` writes `sources/V/audio/audio.flac`, 16 kHz mono). For size
   limits, cut chunks with overlap, for example
   `ffmpeg -i audio.flac -ss 600 -t 610 -c copy scratch/chunk-01.flac`, and shift timestamps by the
   chunk offset. Drop duplicate words in the overlap; never drop unique words.
5. Call the provider. On failure, `budget release` unused reservations.
6. `$D budget settle --workspace "$W" --id rNNNN --actual X --basis provider-usage-api`
   (or `provider-invoice`; use `estimate` only when no usage data exists, and say so).

## English alignment and translation

- English source: `english` is clean English. Remove fillers and false starts only; keep every
  claim, number, caveat, example, and instruction. `english_kind` defaults to `clean`.
- Non-English source: `english` is a translation per segment, `english_kind: "translation"`.
  Record who translated in `translation_provider`. Keep terms of art, and add the original term in
  parentheses when the translation is lossy. Mark uncertain translations.
- Do not merge or split segments differently between `text` and `english`: alignment is per segment.

<!-- example: transcript-ja -->
```json
{
  "schema_version": 1, "video_id": "ja-talk", "language": "ja",
  "provider": {"name": "manual-review", "kind": "manual"},
  "translation_provider": {"name": "amp", "kind": "agent"},
  "duration": 12.0,
  "segments": [
    {"id": "s1", "start": 0.0, "end": 5.5, "text": "キャッシュは書き込みで即座に無効化されます。",
     "english": "The cache is invalidated immediately on write.", "english_kind": "translation"},
    {"id": "s2", "start": 5.5, "end": 12.0, "text": "でも、読み込みが先に走ることがあります。",
     "english": "But a read can run first.", "english_kind": "translation",
     "uncertain": true, "uncertainty": "走る (run) may mean 'overtake' here; meaning checked against the demo only."}
  ]
}
```

## Captions route details

```sh
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs 'en.*,ja' \
  --sub-format json3 -o 'scratch/%(id)s' 'https://www.youtube.com/watch?v=VIDEO_ID'
```

Convert events to segments yourself. Automatic captions often lack punctuation, mishear terms, and
duplicate rolling lines; deduplicate, then compare a sample of segments against the audio. Report
the route as captions in the final summary. Captions never justify `transcript_coverage: verified`
without that check.

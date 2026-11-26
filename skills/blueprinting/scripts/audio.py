#!/usr/bin/env python3
"""Retain a local-only, permission-reviewed audio draft. Never qualifies its claims."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

from engagement import Engagement, Invalid, digest, identifier, read_json
from qualification import text, timestamp


PROCESSOR = "faster-whisper-1.2.1/small.en"


def sha256(handle):
    result = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        result.update(chunk)
    return result.hexdigest()


def inputs(store, source_id, review_id):
    state = store.status()
    if state["pending"]:
        raise Invalid("Reconcile pending operations before audio processing")

    def read(key, kind):
        head = state["records"].get(identifier(key))
        if not head or not head["current"]:
            raise Invalid("Audio source or permission evidence is stale, pending or absent")
        record = store.read_record(key, head["revision"])
        if record["kind"] != kind:
            raise Invalid(f"Expected {kind}: {key}")
        return {"id": key, "revision": head["revision"]}, record.get("data", {})

    source_ref, source = read(source_id, "source")
    review_ref, review = read(review_id, "review")
    if (source.get("medium") != "audio" or not isinstance(source.get("input_file"), dict)
            or review.get("purpose") != "audio-processing" or review.get("status") != "approved"
            or review.get("source") != source_ref or review.get("consent") != "confirmed"
            or review.get("processor") != PROCESSOR or review.get("environment") != str(store.root)
            or not all(text(review.get(k)) for k in ("retention", "authorized_by", "reviewer"))
            or not timestamp(review.get("at"))
            or datetime.fromisoformat(review["at"]) > datetime.now(timezone.utc)):
        raise Invalid("Current source-bound consent, permitted local processor/storage and retention review required")
    basis = review.get("basis")
    if not isinstance(basis, dict) or set(basis) != {"id", "revision"}:
        raise Invalid("Exact permission basis required")
    basis_ref, evidence = read(basis["id"], "source")
    if basis_ref != basis or not text(evidence.get("location")):
        raise Invalid("Current located permission basis required")
    return source_ref, review_ref, source


def model_files(directory):
    root = Path(directory)
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise Invalid("Explicit absolute non-symlink local model directory required")
    manifest = read_json(Path(__file__).with_name("audio-model.json"))
    if not root.is_dir() or {p.name for p in root.iterdir()} != set(manifest["files"]):
        raise Invalid("Complete pinned local model required; no downloads or tokenizer fallback")
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise Invalid("Pinned model must contain ordinary files")
        with path.open("rb") as handle:
            if sha256(handle) != expected:
                raise Invalid("Pinned model bytes differ")
    return root, manifest


def decode(handle):
    import av
    import numpy as np
    # Do not let an untrusted recording act as a playlist opening URLs or other files.
    with av.open(handle, mode="r", options={"protocol_whitelist": "pipe",
                 "format_whitelist": "wav,mp3,flac,ogg,mov,matroska,webm,aac"}) as container:
        if not container.streams.audio:
            raise Invalid("No audio stream; request a usable recording")
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
        chunks = []
        for frame in container.decode(audio=0):
            frame.pts = None
            chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(frame))
        chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(None))
    if not chunks:
        raise Invalid("No decodable audio; preserve the gap and request a usable recording")
    return np.concatenate(chunks)


def draft(store, source_id, review_id, new_id, directory):
    identifier(new_id)
    source_ref, review_ref, source = inputs(store, source_id, review_id)
    if new_id in store.status()["records"]:
        raise Invalid("Draft ID already exists; inspect retained/pending work instead of overwriting")
    model_path, manifest = model_files(directory)
    if version("faster-whisper") != "1.2.1":
        raise Invalid("Pinned optional audio dependency faster-whisper 1.2.1 required")
    # Validate both the local tokenizer and model before importing/constructing the processor.
    # faster-whisper otherwise fetches a tokenizer when tokenizer.json is missing.
    from faster_whisper import WhisperModel
    settings = {"language": "en", "beam_size": 5, "word_timestamps": True,
                "vad_filter": False, "temperature": 0.0, "condition_on_previous_text": False}
    with store.path(source["input_file"]["path"]).open("rb") as audio:
        expected = source["input_file"]["sha256"]
        if sha256(audio) != expected:
            raise Invalid("Audio bytes changed before processing")
        audio.seek(0)
        samples = decode(audio)
        model = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
        segments, info = model.transcribe(samples, **settings)
        spans = [{"start": s.start, "end": s.end, "text": s.text, "speaker": "unknown",
                  "words": [{"start": w.start, "end": w.end, "text": w.word} for w in (s.words or [])]}
                 for s in segments]
        audio.seek(0)
        if sha256(audio) != expected:
            raise Invalid("Audio bytes changed during processing; no draft retained")
    if inputs(store, source_id, review_id)[:2] != (source_ref, review_ref):
        raise Invalid("Permission or audio source changed during processing; no draft retained")
    if not spans or not any(s["text"].strip() for s in spans):
        raise Invalid("No usable speech draft; keep the evidence gap and seek clarification")
    body = "# Machine audio draft — not verified evidence\n\n" + "\n".join(
        f"[{s['start']:.2f}–{s['end']:.2f}s; speaker unknown] {s['text']}" for s in spans)
    record = {"schema": 1, "engagement": store.config["engagement"], "id": new_id,
              "kind": "source", "previous": None,
              "inputs": [{"relation": "derived-from", **source_ref}, {"relation": "governed-by", **review_ref}],
              "body": body, "data": {"medium": "machine-transcript", "origin": "machine",
                  "author": "unknown", "identity": "unresolved", "verification": "provisional",
                  "uncertainties": ["Material numbers, negation, terms and alleged decisions need source-span checks or written clarification.",
                                    "Speaker identities are unknown; timestamps are model estimates."],
                  "audio": {"source": source_ref, "processing_review": review_ref, "sha256": expected,
                      "processor": PROCESSOR, "model": manifest, "settings": settings,
                      "device": "cpu", "compute_type": "int8", "duration": info.duration,
                      "created_at": datetime.now(timezone.utc).isoformat(), "spans": spans}}}
    operation = store.prepare([record])
    snapshot = store.commit(operation)
    return {"draft": new_id, "revision": digest(record), "operation": operation, "snapshot": snapshot,
            "state": "provisional", "span_count": len(spans), "remote_effect": False,
            "next": "Verify material spans or obtain written clarification; retain corrections separately. No client acceptance implied."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--model", required=True, help="Complete pre-provisioned pinned local model directory")
    parser.add_argument("source", help="Registered audio source ID")
    parser.add_argument("review", help="Current processing permission review ID")
    parser.add_argument("draft", help="New retained draft ID")
    args = parser.parse_args()
    try:
        root = Path(args.root)
        if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
            raise Invalid("Explicit absolute non-symlink engagement root required")
        print(json.dumps(draft(Engagement(root), args.source, args.review, args.draft, args.model), indent=2))
    except (ValueError, OSError, TypeError, KeyError, ImportError, RuntimeError) as error:
        print(f"Audio blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Archival contract (schema_version 1)

The source of truth is `scripts/archive.py`. `distill.py` loads it automatically and adds six commands. Evidence contracts are in `contracts.md`, and package contracts are in `article-contract.md`. The module uses only the Python standard library. It reaches Azure Blob Storage through the Blob REST API over verified HTTPS.

## CLI

```text
distill.py signoff        --workspace W --publication P --review REVIEW.json
distill.py archive        --workspace W --publication P --container URL [--receipt PATH]
distill.py archive        --package-dir D --container URL --receipt PATH
distill.py verify-archive (--workspace W --publication P | --receipt PATH) --container URL
distill.py cleanup        --workspace W (--video V... | --publication P) --container URL [--receipt PATH] [--dry-run]
distill.py unpack-artifact    --zip Z --digest sha256:HEX --dest D --expected-manifest-sha256 HEX
distill.py actions-provenance --run-json F --artifacts-json F --repository OWNER/REPO --default-branch B
                              --run-id N --artifact-name NAME --allowed-workflows "PATH[,PATH]"
```

`archive`, `verify-archive`, and `cleanup` read the SAS only from `DISTILL_ARCHIVE_SAS`. There is no flag for it. Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Success. `cleanup` also returns 0 with status `retained` when `retain_media` is true. |
| 1 | `signoff` recorded `blocked`, or `verify-archive` found a mismatch |
| 2 | Contract error or refusal. Nothing is deleted or marked complete. |
| 5 | Remote storage or transport failure. No completion marker is written. |

## Workflow

1. Run `package`. `article-contract.md` describes what it produces.
2. Amp reviews coverage and writes a review JSON file. Then run `signoff`, which writes `publications/<P>/signoff.json`.
3. Run `archive`. It uploads every file, reads each one back, writes per-video evidence markers, writes the publication completion marker last, and then writes `publications/<P>/archive-receipt.json`.
4. Optionally run `verify-archive` at any later time.
5. Run `cleanup`. It deletes only tracked temporary media, and only when the archive and sign-off are approved, intact, and bound to the current evidence.

You can archive partial, unsigned, or blocked packages. The receipt records their quality status, but `cleanup` refuses them.

## Quality sign-off

`package` reports `complete: true` when the article status is `complete` and the PDF is current. That flag says nothing about semantic coverage. `signoff` is the separate quality gate. Amp writes the review, and the script validates it. The script does not judge content.

```json
{"schema_version": 1, "publication_id": "v1", "reviewer": "amp thread T-...", "decision": "approve",
 "note": "what was checked",
 "videos": {"v1": {
   "transcript_coverage": "verified", "visual_coverage": "verified",
   "gaps": [{"start": 0.0, "end": 5.0, "resolution": "no-speech", "note": "title music"}],
   "uncertain_segments": [{"segment_id": "s2", "resolution": "labeled", "note": "kept marked uncertain"}],
   "audio_verification": {"method": "listened-to-source-audio",
     "note": "spot checks of the opening and the key claim; the rest was not compared",
     "checks": [{"start": 0.0, "end": 20.0, "segment_ids": ["s1", "s2"], "result": "matches",
                 "note": "words match at 1x"}]},
   "note": "optional"}}}
```

`audio_verification` is optional for `transcription` and `manual` transcripts and required for `captions` and `agent` transcripts (`provider.kind` in `transcript/segments.json`). It is a list of spans the reviewer compared with the source audio, not an accuracy verdict:

- `method` is `listened-to-source-audio` or `compared-with-independent-transcription`. `note` is required text.
- `checks` is a non-empty list. Each check has finite numeric `start` < `end` within the media duration (NaN and Infinity are rejected), `segment_ids` (a non-empty list of distinct segment ID strings, each overlapping the span), `result` (`matches` or `differs`), and a non-empty `note`.
- `signoff.json` records the checks plus `checked_seconds`, `checked_fraction` of the duration, `spoken_segments` (the transcript segment count), `unchecked_segment_ids` (segments not fully inside the merged checked intervals), and a `limits` statement. Unchecked spans stay unverified; there is deliberately no boolean "accurate" field.
- For `captions` and `agent` transcripts, approval requires the merged checked intervals to cover every transcript segment. A partial spot check (like the example above) is still validated and recorded for the report, but sign-off is `blocked`, so cleanup keeps the media. Full coverage means the reviewer compared every spoken span; it is not a measured accuracy rate.

Validation rules:

- Unknown fields are rejected at every level, and every publication video must be present.
- Each gap entry must match a gap in `coverage.json` to within 1 ms.
- Each uncertain-segment entry must name a segment in `uncertain_segment_ids`.
- Review text that looks like a secret is rejected.
- The package must still match its manifest and ZIP. The workspace evidence must still match the packaged copies and the stage records. If either check fails, the command exits 2 and nothing is written.

Sign-off is `blocked` (exit 1) and still recorded with its blockers when any of these is true:

- The package is incomplete (`complete: false`), for example because the article is partial or the PDF is missing.
- The reviewer decision is `block`.
- A required stage is missing or incomplete: `download` (missing download coverage), `frames` (missing frame coverage), `transcript`, or `transcript-markdown`.
- `transcript_coverage` or `visual_coverage` is `unverified`.
- The transcript duration is unknown.
- A transcript gap has no review entry, or its resolution is `unresolved`. The accepted resolutions are `no-speech` and `not-relevant`.
- An uncertain segment has no review entry, or its resolution is `unresolved`. The accepted resolution is `labeled`, which means the deliverables keep the uncertainty marked.
- The transcript `provider.kind` is `captions` or `agent` and the review has no `audio_verification`, or its merged checked intervals leave any transcript segment unchecked.
- Any audio check has `result: differs`. Correct the transcript, re-import it, and review again.

`signoff.json` contains:

- `status` and `blockers`.
- `manifest_sha256`, `zip_sha256`, and `revision`.
- `review_sha256` and the review itself.
- For each video:
  - `stages`: a snapshot of the `status`, `inputs`, and `outputs` digests of the `download`, `frames`, `transcript`, `transcript-markdown`, and `frame-selection` records.
  - `media`: the SHA-256 of every tracked temporary media file.
  - `transcript_provider`: `name`, `kind`, and optional `model` and `version` from `transcript/segments.json`.
  - `audio_verification`: the validated checks with `checked_seconds`, `checked_fraction`, `spoken_segments`, `unchecked_segment_ids`, and `limits`, or `null`.
  - The coverage gaps and uncertain segment IDs.

A sign-off that names a different manifest is stale. `archive` refuses it.

## Destination and credentials

- **Container URL.** It must be exactly `https://<account>.blob.core.windows.net/<container>`. The US Gov and China Blob endpoints are also accepted. The URL cannot contain credentials, a port, a query, a fragment, or a sub-path. Use a container name of 3 to 63 lowercase characters. Credentials are sent only to that host on port 443.
- **SAS (`DISTILL_ARCHIVE_SAS`).** The value is the query string only, with an optional leading `?`. It must have `sig`, `se` (expiry), `spr=https`, and read permission (`r`). `archive` also needs create permission (`c`; `w` is accepted). A SAS that grants `d`, `x`, or `y` (delete) is refused. Use a container-scoped service SAS with `sp=rc`. Write access to existing blobs is never needed, because every upload uses `If-None-Match: *` (create-only).
- **Transport.** The production transport is `http.client.HTTPSConnection` with `ssl.create_default_context()`, so certificates and hostnames are verified. It ignores proxy environment variables and never follows redirects: any 3xx response is an error. Responses are capped at 512 MiB. Each request is sent once.
- **Errors.** Error messages include the method, blob name, HTTP status, and Azure `x-ms-error-code`. They never include response bodies, URLs with query strings, or SAS values. Exception text is scrubbed of the SAS, its parameter values, and any query string.
- **Where the SAS never appears.** It is never written to receipts, markers, `signoff.json`, stdout, or logs. Child media tools never see it, because `distill.py` strips environment variables whose names contain `SAS`.
- **Tests.** Tests inject a fake transport object into the command handlers. No CLI option or environment variable selects plain HTTP or another host.

## Remote layout

Each run uses a new attempt ID `A = <UTC yyyymmddThhmmssZ>-<8 hex>`, so uploads never collide and are never overwritten. In the paths below, `R` is the package revision and `E` is a per-video evidence revision: 16 hex characters of the SHA-256 of that video's sorted `{path, sha256, bytes}` list.

```text
videos/<V>/evidence/<E>/<A>/files/<path under sources/V/>   evidence files from the package
videos/<V>/evidence/<E>/<A>/_COMPLETE.json                  evidence marker (after its files verify)
publications/<P>/<R>/<A>/files/<package path>               non-evidence package files
publications/<P>/<R>/<A>/manifest.json
publications/<P>/<R>/<A>/<P>-<R>.zip
publications/<P>/<R>/<A>/signoff.json                       when present
publications/<P>/<R>/<A>/_COMPLETE.json                     final marker, written last
```

Each manifest file is uploaded once, either as evidence or as a publication file, and also inside the ZIP.

The archive is built in this order:

1. The local bytes of every object are re-hashed just before upload, so a file that changes mid-run aborts the archive.
2. After all uploads, every object is downloaded again and its length and SHA-256 are compared.
3. Only then are the evidence markers written, and each is read back.
4. The publication `_COMPLETE.json` is written and read back.

If any step fails, no final marker exists. Objects under that attempt are then abandoned: they are not an archive, and no delete permission exists to remove them.

The final marker, which the receipt embeds, contains:

- `publication_id`, `revision`, `attempt`, and `manifest_sha256`.
- The ZIP blob and its digest.
- `quality`: `status` (`approved`, `blocked`, `unsigned`, or `partial`), `package_complete`, `incomplete_reasons`, and the sign-off `status`, `blockers`, `sha256`, and blob.
- `videos`, giving each video's evidence revision, prefix, marker blob and digest, and per-file digests.
- `objects`, giving `{path, blob, sha256, bytes}` for every object.

The receipt adds `container_url` (no SAS), `marker_blob`, and `marker_sha256`.

## Cleanup binding

`cleanup` refuses, with exit 2 and nothing deleted, unless every check below passes for each requested video.

Before any network request, it checks:

1. `retain_media` is false. When it is true, the command returns status `retained` and deletes nothing.
2. The receipt exists, is well formed, belongs to this publication, and names the same container as `--container`. A tampered receipt cannot redirect the SAS to another account.
3. The archived quality status is `approved` and `package_complete` is true.
4. The local `signoff.json` has exactly the archived sign-off digest, is `approved`, and names the archived manifest. The sign-off object is listed in the archive.
5. Every stage snapshot in the sign-off equals the current `state.json` record, and every current stage output still matches its checksum. Changing a transcript, frames, or media file after sign-off blocks cleanup.
   The sign-off's `transcript_provider` equals the provider in the current `transcript/segments.json`. For a `captions` or `agent` transcript, the sign-off has `audio_verification` with at least one check, every check is `matches` with finite `start`/`end`, and the merged checks cover every segment of the current `transcript/segments.json` (recomputed at cleanup, not trusted from the sign-off). A single short spot check never authorizes deleting the media. A sign-off made before provider recording is refused; rerun `signoff` and `archive`.
6. Every archived evidence file for the video exists locally with the archived digest. Every core evidence file that exists locally (`source.json`, `selection.json`, `frames/frames.json`, and the transcript files) was archived. A receipt from another workspace, or from older evidence for the same video ID, therefore fails.
7. Each media path to delete comes from the sign-off and meets all of these conditions:
   - It is listed in `state.json` `temporary_media`.
   - It matches `sources/<V>/(media|audio)/<name>`.
   - It is not an archived object.

Then it makes the network checks:

8. It re-downloads the final marker and checks that it is byte-identical to the receipt's digest and content.
9. It re-downloads every evidence marker and every archived object and checks their digests.

Finally, it checks and deletes each file:

10. Each file is opened through directory file descriptors with `O_NOFOLLOW` at every component, so it cannot follow a symlinked ancestor or file.
11. The file must be a regular file whose SHA-256 equals the signed-off digest, and its inode must be unchanged right before `unlink(dir_fd=...)`. All files are checked before any is deleted, and deletion happens under the workspace state lock.

After deletion:

- Deleted paths are removed from `temporary_media`.
- Their stage `inputs` and `outputs` entries move to `cleaned_inputs` and `cleaned_outputs`, with their digests kept. `validate --require-complete` still passes, and render and package still work from the evidence.
- The `download` record gains `media_cleaned` (time, receipt marker digest, deleted files), and `media_cleaned: true` is added to its config. A later `download` therefore re-fetches the media instead of reporting it as reused. To re-extract frames, run `download` again first.
- Running `cleanup` again returns `already-clean`.

`--dry-run` performs every check, including the remote ones, and lists what it would delete. Cleanup never deletes evidence, publications, packages, receipts, ZIPs, or remote objects.

## GitHub Actions hand-off

`.github/workflows/archive-distilled-videos.yml` only validates and archives. It never runs the editorial pipeline or executes package content. It runs only when dispatched manually (`workflow_dispatch`), with top-level `permissions: {}`.

**How a package reaches Actions.** There is no supported way for an Amp orb, or any process outside a workflow run, to upload a GitHub Actions artifact. Artifact upload needs the runtime token of a running job. So the workflow accepts only an artifact produced by a trusted workflow run in this same repository: a *producer* workflow. This repository does not ship a producer workflow. One could, for example, be a manually dispatched job on a self-hosted Mac runner that builds the package. Such a producer must stage a flat directory and upload it with `actions/upload-artifact` v4 or later, so the artifact has a sha256 `digest`:

```text
<dir>/manifest.json, <dir>/<every manifest file>, <dir>/<P>-<revision>.zip, optional <dir>/signoff.json
```

Stage the local `<title-slug>.zip` from the `package` output under the canonical name `<P>-<revision>.zip`. The archive always stores the ZIP under that canonical name.

**Archiving from an orb.** For the normal orb path, archive directly from the orb with its own Amp project secret: `DISTILL_ARCHIVE_SAS=... distill.py archive ...`. Actions is not required. Do not commit packages to Git or use public temporary upload URLs to reach Actions.

**Required configuration.** The workflow fails closed when any of these is missing:

- Environment `distilled-video-archive`, with a deployment branch policy limited to the default branch and, ideally, required reviewers.
- Environment secret `DISTILL_ARCHIVE_SAS`.
- Environment variable `DISTILL_ARCHIVE_CONTAINER`. The destination comes from configuration, never from dispatch inputs.
- Repository variable `DISTILL_PRODUCER_WORKFLOWS`, a comma- or space-separated list of `.github/workflows/<name>.yml` paths. When it is empty, every run is rejected.

**Dispatch inputs.** The workflow takes `run_id`, `artifact_name`, and `expected_manifest_sha256`, which is the `manifest_sha256` that `package` printed. It validates the inputs with regular expressions and passes them only through `env`.

**Job `fetch`.** This job has `actions: read` and `contents: read` and no archive secret. It runs these steps:

1. Fetch the run and its artifact list with `gh api`.
2. Run `actions-provenance`, which requires all of the following:
   - The run ID matches.
   - The run completed successfully.
   - The run's `repository` and `head_repository` are this repository, with the same ID, so fork runs are rejected.
   - The event is `workflow_dispatch`, `push`, or `schedule`. `pull_request`, `pull_request_target`, `workflow_run`, and every other event are rejected.
   - `head_branch` is the default branch.
   - The workflow path is allowlisted and is not this workflow.
   - Exactly one artifact has the requested name. It is not expired, was produced by this run in this repository, and has a `sha256:` digest and a size within the limit.
3. Download the artifact ZIP with `gh api .../artifacts/<id>/zip`.
4. Run `unpack-artifact`, which:
   - Checks the artifact digest.
   - Rejects absolute or `..` paths, backslashes, symlink, special, or encrypted entries, duplicate entries (case-insensitive), unexpected extensions, too many files, and oversized content.
   - Extracts without `extractall` into a new directory.
   - Verifies the package exactly as `archive` does: every file is listed with a matching digest, there are no unlisted files, the ZIP matches the manifest, the revision recomputes, text files contain no secret-like content, and any `signoff.json` matches the manifest.
   - Requires the manifest digest to equal `expected_manifest_sha256`.
5. Re-upload the validated directory as a one-day artifact of this run.

**Job `archive`.** This job runs in the `distilled-video-archive` environment with `contents: read`. It runs these steps:

1. Check out trusted code without persisted credentials.
2. Download the validated artifact from the same run.
3. Run `archive --package-dir`, which re-verifies the package.
4. Upload the receipt as an artifact. The receipt contains no SAS.

Only this one step receives the SAS. All actions are pinned to commit SHAs.

**Actions limitations:**

- The package-directory mode cannot check sign-off evidence against a workspace. It records the sign-off status as supplied, bound to the manifest digest. Cleanup always runs in the workspace, using that workspace's local checks. To use an Actions receipt for cleanup, download it (`gh run download`) and pass `--receipt`. The workspace's `signoff.json` must be the one that was archived.
- The `if: github.ref == default branch` guards are defense in depth. A dispatch from another branch runs that branch's version of the workflow, so the real control is the environment's deployment branch policy.
- The provenance check trusts the GitHub API's `head_branch`. A tag push whose name equals the default branch would be treated as the branch. Allowlist only producer workflows that do not trigger on tags.
- The format of a workflow run's `path` field is accepted with or without an `@<ref>` suffix. This format has not been checked against a live run.
- The workflow has passed `actionlint`. It has not run on GitHub.

## Known limits

- Live Azure authentication, Put Blob with `If-None-Match`, and read-back have not been run. Tests use an in-process fake Blob transport, so no Azure writes or credentials are involved. Treat live archival as unverified until credentials and a disposable container prefix are authorized.
- Each object is uploaded with a single Put Blob request and held in memory. The limits are 512 MiB per object and 2 GiB per package. Block uploads for larger files are not implemented.
- Abandoned attempts without a final marker stay in the container, because the SAS has no delete permission. Use a lifecycle policy or manual review to remove them.
- Redaction does not protect against untrusted code that runs with the SAS. Keep the secret limited to the archival step.
- Sign-off records a reviewed judgment. It cannot prove that every word or frame was understood.

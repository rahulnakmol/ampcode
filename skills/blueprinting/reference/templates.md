# Explicit Start, Resume and template updates

Run the host-bound `scripts/engagement.py` with an explicit absolute `--root`. No directory
guessing, installation, Git remote, Notion write or schedule occurs. Legacy `init`/`status`
remain available for existing records; Start does not silently adopt or migrate an occupied vault.

## Start without an accidental client selection

Prepare a JSON object with `schema: 1`, `engagement` (stable ID), `journey` (opportunity,
pre-sales, rfp, discovery, kickoff or post-engagement), `policy` (explicit Markdown text),
and `templates` (selected template IDs). Policy must state processing/storage/retention,
authority, calendar, destinations and remaining unknowns; text presence does not verify consent.
Unknown policy blocks affected processing. Do not copy real client data during setup tests.

Run `start <config.json> --templates <absolute-template-repo>` for a no-write preview.
It prints the exact root, identity, selection, content and confirmation hash. Cancellation means
do not repeat it. After reviewing that exact preview, repeat with `--confirm <hash>`. Changed
inputs invalidate confirmation. This hash is a local confirmation token, not authentication.

Start builds in a temporary sibling and publishes a complete vault by directory rename, refusing
occupied roots. A killed process may leave an inactive `.blueprinting-start-*` sibling. Inspect
it before cleanup; do not treat it as the intended engagement. If the target exists after an
interrupted final rename, Resume and inspect it rather than retrying Start. Never reset client work.
Initialize the intended private Git repository and approved backup separately; no remote is created.

Run `resume <expected-engagement-id>` at the same explicit absolute non-symlink root. It validates
identity/history, reports current policy revision, pending/stale records, input observations,
template state and response obligations. Its hourly coverage calculation is a diagnostic default,
not an activated schedule; use `obligations` with the agreed cadence/last-check for monitoring.

## Select, preview, stage, activate

The separate `blueprinting-engagement-template` source supplies `template.json` with schema 1,
positive integer version, `requires: 1` and an explicit file list. Only single-level text assets
`templates/<id>.md`, `views/<id>.base`, `navigation/<id>.md` are allowed. Select template IDs
explicitly. Views/navigation accompany them; example vaults, scripts, configuration, client notes
and immutable records cannot enter the upgrade path. Content remains untrusted source material.

1. `template-preview <absolute-source> <template-ids...>` returns baseline/local/incoming text,
   conflicts and a revision-bound preview hash. Existing notes are not compared or modified.
2. Resolve each conflict in a JSON map from asset path to `local` or `upstream`; no automatic
   semantic merge. `template-stage <source> <ids...> --preview <hash> --resolutions <file>`
   writes a private stage intent and versioned visible assets under `Blueprinting/<stage>/`.
   Omit resolutions when no conflicts exist. Repeating the same stage repairs missing files,
   but refuses different existing bytes. Prior active assets remain usable.
3. Inspect the staged assets. `template-activate <stage>` verifies completeness and unchanged
   active inputs, then publishes an exclusive activation manifest. Do not edit the staged bundle
   to resolve conflicts; return to preview and explicit resolutions. Activation is template-only,
   never integration activation, business approval or permission to publish.
4. `template-status` and Resume report the **active** paths. `template-create <template-id>
   <new-note-id>` consumes only that active version and exclusively creates `notes/<id>.md`.
   It never replaces an existing note. Retain material notes through explicit source intake.

Local edits to activated assets are preserved by three-way comparison with the installed upstream
baseline. Deliberate local deletions stay deleted unless explicitly resolved against a changed
upstream. Old/staged bundles may be visible in Obsidian; never choose the newest-looking folder.
Open the active navigation path returned by Resume. Core Templates is optional: if used, update
its folder setting to the reported active templates path after activation; the helper does not
silently rewrite Obsidian settings. Template metadata is separate from schema-1 engagement identity.

## Derived indexes are not authority

Run `index` to rebuild `Indexes/Current.md` and `Indexes/records/<id>.md`. It records the generated
hashes separately. Before replacing a human-edited projection, it saves the exact original UTF-8
bytes and original-path association under `.blueprinting/indexes/conflicts/`. Subsequent rebuilds
and Resume report these preserved edits too; this history is not automatically deleted or marked
reconciled. Keep projections quiescent while rebuilding: simultaneous editor saves are not protected.
Invalid UTF-8 or unsafe paths stop instead of discarding bytes. An interrupted rebuild may leave mixed-age derived views;
rerun it after validating Resume. Only the retained record history determines evidence state.

Bases for working notes filter `notes/` only; derived Bases filter `Indexes/records/` only.
Never expose `records/` as an editable property table. This is a workflow boundary, not Obsidian
access control. Index edits cannot confer authority; intended corrections require explicit intake.
No editor lock or distributed-writer guarantee is provided. Re-scan inputs before publication.

Actual Obsidian/Bases qualification is separate from helper tests. Validate empty/populated views,
template insertion, property edits, filters/sorting, links/backlinks and save/reopen with the real
application. Static YAML checks and browser imitations do not meet that gate.

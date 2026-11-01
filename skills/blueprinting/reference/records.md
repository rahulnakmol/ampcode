# Retained engagement records — first implementation slice

Requires Python 3.10+ and a local filesystem supporting same-directory hard links and fsync.
One automation writer per engagement is required. There is no distributed locking or hostile-shell
security boundary. The script has no network, Git commit, scheduling or publication effects.

Run `python3 scripts/engagement.py --root <directory> init <engagement-id>` once in the intended
private engagement directory. Initialization never replaces an existing config. Keep human notes
under `notes/` or other unmanaged folders; the helper never edits those files.

## Prepare, commit, resume

1. Supply a JSON array of record envelopes to `prepare <json-file>`. This durably retains the
   proposed change before creating retained records. Save the returned operation hash.
2. Run `commit <operation-hash>` to retain the records and publish a complete snapshot manifest.
   This is a local record commit, not a Git commit or business acceptance.
3. Run `status` on every resume and before using any conclusion. `status --snapshot <hash>`
   inspects history but still checks against current known changes. Pending corrections make
   their dependent current uses stale even before a new snapshot commits.
4. After interruption, inspect `status` and the retained operation; repeat `commit` with the
   same operation only when its base is still current. Repeating an already committed operation
   returns its original snapshot. If another operation advanced the base, it blocks for explicit
   reconciliation. Automated reconciliation of competing pending operations is not implemented;
   do not delete the old intent to make the warning disappear.

Example record envelope (replace the engagement ID with the configured value):

```json
{
  "schema": 1,
  "engagement": "factory",
  "id": "stock-note",
  "kind": "source",
  "previous": null,
  "inputs": [],
  "body": "# Stock evidence\n\nSynthetic planner note: 120 usable units; quality verification pending.\n"
}
```

Use stable IDs. Update a record by supplying its current revision as `previous`; retain the
original body and amendments through history, not an overwritten file. Each input edge has
`relation`, `id` and `revision`. Relations are `derived-from`, `governed-by`, `answers` and
`allocates`; predecessors represent supersession. Reference only already committed revisions.
For new dependency chains, commit sources before dependent claims and requirements.

Kinds are source, note, claim, requirement, decision, mission, review and artifact. The body is
Markdown. Metadata is a JSON object in YAML-compatible frontmatter. A revision hash identifies
the canonical UTF-8 JSON envelope, with sorted keys and no insignificant JSON whitespace.
Raw attachments are not automatically stored or committed. Put attribution, uncertainty,
restrictions and domain details in the body for this slice; typed enforcement is still pending.

## Integrity and boundaries

`operations/` retains change intents; `records/<id>/<hash>.md` retains revisions;
`snapshots/` contains a sequential hash-linked manifest history. Do not edit these managed files.
Each manifest includes the full current record map; exact dependencies resolve through validated
history. Incomplete operations cannot become snapshots. Corrupt committed records or manifests
block validation rather than silently falling back to an earlier successful state.

`status` reports revision freshness only. A change to a source or governing record stales every
dependent use, including decisions and artifacts; unrelated work remains current. It cannot
detect facts never supplied, a missing dependency omitted by the author or semantic contradictions
in a source. It cannot authenticate client confirmation or classify confidential prose. Written
client-confirmation and publication gates remain unimplemented, not implicitly satisfied.

No performance claim is made: this first implementation validates retained history on each call.
History pruning, multiple writers, network filesystems and independent clone reconciliation are
not supported. Keep the private Git backup and human review process; local hashes alone are not
an audit authority or a backup. Treat partial files or unexpected history changes as an incident
to investigate, not permission to reset or erase engagement evidence.

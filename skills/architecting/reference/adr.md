# Architecture decision records

An ADR records one consequential decision: the options that were real, the one chosen, and what
follows from it. A later reader learns why the system looks the way it does, and what evidence
would justify a change.

## When to write one

Write an ADR when a decision is hard to reverse, affects more than one container or team,
changes a contract, costs money, or rejects an option that someone will propose again. Do not
write one for a choice the codebase already fixes, or for a default nobody questions.

## Format

Each ADR is a `### ADR-n: <title>` subsection under `## Decisions` in the design file:

```text
### ADR-3: Store exports in object storage

Status: accepted
Options:
- Object storage with signed links
- Rows in PostgreSQL, streamed by the API
- A file share mounted by the worker
Decision: Object storage. Files reach 2 GB; the database should hold orders, not files.
Consequences: Cheap storage and no load on the API for downloads. A lifecycle rule must delete
files, and a leaked link works until it expires. Reverse if exports stay under 5 MB.
```

`design_check.py` checks: at least two options (D4); a status, a decision and consequences (D5);
unique IDs (D7).

## Fields

| Field | Write |
| --- | --- |
| Title | The decision as a short statement, not the problem |
| Status | `proposed`, `accepted`, `rejected`, `deprecated` or `superseded by ADR-n` |
| Options | Every real option, the chosen one included. Include "do nothing" or "keep the current system" when it is real |
| Decision | The chosen option and the deciding reasons, with evidence: workload, team skills, cost, risk |
| Consequences | What becomes easier, what becomes harder, the new risks, and the evidence that would reverse the decision |

For a hard choice, add a short trade-off table under Options: one row per option, one column per
criterion that matters (fit to the workload, cost, team skills, operations, lock-in, time to
deliver).

## Rules

- **Real options only.** A straw man does not count. If only one option survives, say what you
  rejected and why.
- **Evidence over taste.** Cite measurements, limits from primary sources, or the user's stated
  constraints. Label an untested claim "claimed" or "not proven".
- **Reversibility.** Prefer reversible steps. For an irreversible decision, say so in the
  consequences and flag it for the owner's confirmation.
- **Immutable once accepted.** Do not rewrite an accepted ADR. Write a new ADR and set the old
  status to `superseded by ADR-n`. Never reuse an ID.
- **Proposed until confirmed.** An ADR stays `proposed` until the decider for the design accepts
  it. The calling skill (`delivering`, `missioning`) records that acceptance.
- **Link the NFRs.** When a decision exists to meet an NFR, name its ID (for example "to meet
  NFR-2").

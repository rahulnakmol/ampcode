## Ownership defense — blocked

**Outcome:** A tenant can resume a CSV export with one command and receive every intended row exactly once. Proposed acceptance IDs: AC1 one-command resume; AC2 no missing or duplicate rows; AC3 tenant isolation. AC3 expresses an implied security boundary, not separately confirmed scope.

**Known design:** Source rows → CSV output; a process-local map holds a last-row integer. Output writes and cursor updates occur separately. There is no crash-test evidence or source-consistency investigation.

**Why this cannot be handed off as ready:**
- A process restart loses the map. Durable recovery is unexplained.
- A crash after output but before checkpoint advancement can duplicate rows on retry. Advancing the checkpoint first can instead omit rows after a crash. The supplied design does not establish exactly-once output.
- An integer alone does not establish stable ordering or membership when source data changes. The intended export dataset remains undefined.
- Unguessable tenant IDs are not authorization. A caller who obtains another tenant’s identifier could attempt to resume or retrieve its export.
- A queue changes scheduling, not output/checkpoint atomicity, source consistency, or authorization. It is not a demonstrated remedy.

## Next safe action — bounded investigation, not implementation handoff

The delivery owner must establish source ordering and snapshot capabilities, output-store commit semantics, and restart requirements. Resolve only the consequential dataset-semantics question with the customer if the brief does not already settle it.

**Proposal:** Use durable tenant-bound job state and deterministic output chunks with an authoritative committed manifest. Define how publication and checkpoint recovery reconcile partial writes. Compare this with a simpler durable checkpoint if the output store supports atomic coupling. Do not select either without those contracts.

Required invariants: authorized tenant ownership, fixed export membership/order, and exactly one committed contribution per intended row. Assign the implementer crash/retry, concurrent-resume, changing-source, and cross-tenant negative tests after mechanism gaps close.

Obtain independent skeptical challenge, transfer the actual brief and resolved defense, and require recipient teach-back before readiness. No challenge, tests, or handoff have occurred here. Both build reviews and the complete customer journey remain required. Tabletop only; no scenario actions executed.

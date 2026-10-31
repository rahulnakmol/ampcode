## A demonstrated local recovery, not production speed

At commit A, the local fixture recovered all 120 expected rows without duplicates, required one operator command, and passed tenant rejection. A’s design defense and first review passed. These observations support that specific local recovery journey. They do not establish production performance, the complete customer outcome, or a completed second review.

Marketing’s “production is 80% faster” claim is unsupported. We have no comparable production baseline, timing measurements, or defined performance metric. We can report A’s observed fixture result, clearly labelled local, without a speed claim.

## B reopens the recovery design

The current candidate, B, replaces durable chunk files with a process-local buffer. B is uninspected and untested. A’s defense and review cannot cover this change, and its recovery evidence cannot establish B’s behavior.

Process termination can erase a process-local buffer. Whether B can recover from another durable source is unknown. This changes the failure boundary and potentially the promised recovery semantics. Readiness is blocked pending investigation; this is not a minor implementation detail. Preserve A’s evidence and candidate rather than silently accepting weaker recovery.

## Handoff needs the actual candidate and a renewed defense

The integration owner must transfer the confirmed brief and acceptance IDs, exact A/B revisions, accessible candidate files and diff, A’s evidence, and the unresolved durability question. The recipient must explain back the customer outcome, storage flow, persistence boundary, retry and duplicate-handling invariants, and first check.

Refresh the affected defense with a separate skeptical challenger: why use a buffer instead of durable files, what survives interruption, and how does recovery preserve rows and tenant isolation? Inspect B, then establish behavioral tests for interruption, restart, replay, and the original recovery journey before repairing it. Reopen expectations only if recovery guarantees must change.

B needs affected first-gate review, repair and revalidation where needed, and a distinct second review of the final candidate. Integration and release remain unestablished. This is a tabletop update only; no inspection, execution, or handoff occurred.

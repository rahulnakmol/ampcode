## First actions — tabletop only

The approved outcome is a complete, tenant-isolated CSV after interruption, finished with one resume command and no manual stitching. Local implementation is authorized; push and deployment are not. No scenario actions have run.

1. Reuse the approved brief through grilling; do not repeat settled questions. Inspect repository guidance, export/resume contracts, checkpoint ownership, source consistency, and artifact writes. Resolve only consequential unknowns: which rows belong to an export when source data changes, and what interruptions must be recoverable.
2. Record acceptance criteria: **A1** exact expected rows, each once; **A2** tenant isolation for start, resume, checkpoints, and artifacts; **A3** one-command recovery without manual repair. Preserve existing work and record the local candidate, environment, limits, and evidence. Exact token accounting is unavailable here.
3. Before implementation, defend the flow: authorized operator → tenant-bound export identity → stable row selection/order → output writes → durable recovery state → resume. This is a proposal, not an inspected mechanism. Compare append/checkpoint with staged chunks plus finalization. Explain the chosen data structures, ordering, and crash consistency. A checkpoint alone cannot prevent duplication after an output write succeeds but checkpoint persistence fails. Investigate that boundary before handoff.

Obtain independent skeptical challenge because this changes tenant boundaries and concurrent durable state. Resolve blocking gaps. Transfer the actual brief and defense; require recipient teach-back, or use my defense if implementing directly. Readiness is not verification.

## Evidence and delivery gates

Replace exit-only confidence with independently derived, nonempty expected CSV contents. First demonstrate a behavioral red assertion on unchanged code, not an environment failure. Test interruption before/after writes and checkpoints, repeated/concurrent resume, source changes, unavailable storage, malformed state, and cross-tenant resume attempts. Assert row identity, counts, values, and persisted recovery state.

Run the real local operator journey and inspect the CSV. Record revision, commands, expected/observed results, and limitations. Require independent review one, regression-backed repairs, revalidation, then distinct independent review two on the final candidate. Refresh the defense.

Delivery requires A1–A3 evidence and demonstrated elimination of manual stitching. Missing mandatory checks block completion. Report implemented, verified, and reviewed separately; not integrated or released.

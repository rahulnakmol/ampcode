**Open:** this is a security-sensitive handoff, not an approved technical design. Next I will close the two outstanding policy decisions, then prepare a standalone brief for the implementing agent. I have no repository access; technical feasibility and implementation details remain unverified.

❓ **Q1. Post-offboarding retrieval authorization**
How should a former admin prove they may retrieve the export without logging in?

| Option | Consequence |
| --- | --- |
| **A** Separate, export-scoped recipient verification | Adds verification and recovery work; avoids restoring account access. |
| **B** Possession-only expiring download link | Simpler retrieval, but anyone receiving a forwarded or stolen link can retrieve the export. |

➡️ **Recommended: A**, because tenant isolation is mandatory and account login is unavailable. The cost is extra recipient friction and implementation scope. Reply “yes” to accept. Exact verification mechanics require subsequent design and threat review.

❓ **Q2. Retention**
How long should a completed export remain retrievable?

| Option | Consequence |
| --- | --- |
| **A** 30 days after successful completion, then delete export artifacts | Bounds exposure and storage cost; late recipients must request another export if source data still exists. |
| **B** Defer to the accountable policy owner before implementation | Avoids inventing contractual obligations, but blocks a complete handoff. |

➡️ **Recommended: B**, because no retention policy or contractual evidence is available. The cost is delay. Reply “yes” to accept. Export retention must not silently set source-data retention.

**Grading criteria for the eventual brief and implementation evidence**
- Preserve every confirmed constraint: own-tenant records and attachments, soft-deleted records included, capacity through 2 million rows and 40 GB, and cutoff at job creation.
- Demonstrate cutoff-consistent results despite concurrent edits, deletes, and attachment changes; reject missing or duplicated rows after interruption and resume.
- Demonstrate cross-tenant denial at creation, processing, and retrieval. Negative tests must accompany a nonempty successful export, so an empty artifact cannot pass isolation checks.
- Demonstrate retrieval after account offboarding without reinstating access, and test the agreed authorization, expiry, and deletion rules.
- Distinguish confirmed outcomes from design proposals, assumptions, unresolved facts, and actual verification evidence.

**Handoff preparation:** I will reconstruct a decision log, preserving rationale available in this conversation and explicitly marking unavailable rationale rather than inventing it. After these answers, I will sweep severe edge cases, resolve dependent decisions, and request final-shape and security-handling confirmation. Then I will prepare a durable brief with scope, numbered acceptance criteria, risks, verification, approval gates, an ordered work plan beginning with repository discovery, and a self-contained pick-up prompt pointing to that brief. Implementation remains gated on confirmation.

**Gate: not yet concrete**—authorization, retention, dependent edge-case handling, and technical verification remain open. No reviewer has run; review and tests described here are proposed, not completed evidence.

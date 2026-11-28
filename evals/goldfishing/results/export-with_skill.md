**Open, consequential handoff.** Next: a requirements packet, not implementation or approved design. Without repository access, feasibility remains unverified.

Confirmed: own-tenant records, including soft-deleted records, and attachments; up to 2 million rows and 40 GB. Job creation fixes the cutoff; resumption cannot omit or duplicate rows. Offboarded admins must retrieve without restored login; tenant isolation is mandatory.

### Decisions needed next

❓ **Q1. Retrieval authorization**
Who may retrieve the export after account access ends?
*Why it matters:* Ordinary login cannot satisfy the confirmed delivery requirement.

| Option | Consequence |
| --- | --- |
| **A** Pre-designated recipient, independently verified at retrieval | Adds verification work; limits unintended access. |
| **B** Anyone holding a delivery link | Less recipient friction; forwarding or theft grants access. |

➡️ **Recommended: A**, as an unverified security recommendation given mandatory isolation; it costs retrieval convenience. Reply “yes” to accept. This selects a policy, not its technical mechanism.

❓ **Q2. Retention**
How long should completed exports remain retrievable?
*Why it matters:* Expiry trades retrieval opportunity against retained sensitive data.

| Option | Consequence |
| --- | --- |
| **A** Seven days from successful completion, then deletion | Shorter exposure; less time for the recipient. |
| **B** Thirty days from successful completion, then deletion | More retrieval time; longer exposure and storage cost. |

➡️ **Recommended: A**, an assumed proposal minimizing exposure, not a verified contractual requirement. Reply “yes” to accept. Failed-job artifacts and legal holds still need lifecycle rules.

### Grading criteria—not implementation choices

| Observable outcome | Wrong result rejected; evidence required |
| --- | --- |
| Exact own-tenant content, including soft-deleted rows and attachments | Empty or incomplete “safe” exports; compare nonempty tenant fixtures, identifiers, counts and attachment hashes. |
| Isolation throughout creation, resume and retrieval | Cross-tenant identifiers or credentials expose data; adversarial two-tenant checks. |
| Frozen cutoff survives concurrent changes and retries | Mixed-time content, missing or repeated rows; compare an agreed cutoff oracle before/after injected interruptions. |
| Supported capacity and honest failure behavior | Silent truncation; test empty, maximum and over-limit inputs, after agreeing rejection behavior and byte units. |
| Offboarded delivery and lifecycle follow approved policy | Login restoration, unauthorized retrieval or expired access; test an actually disabled account, revocation and deletion. |

### Preparing the packet

Record confirmed decisions separately from proposals, recover missing rationale with you rather than inventing it, and preserve rejected alternatives. Resolve snapshot semantics and severity-4 security/lifecycle handling before finalizing acceptance checks. Include scope, ordered work steps, verification evidence, approval gates and a standalone pick-up prompt.

Then request a fresh, read-only Goldfish comprehension review using only the versioned packet and explicit source/contract revisions once available. Record actual reads, findings and revision; repair the packet and recheck. **No review has run.** User confirmation remains separate. Technical design then needs its own review and owner acknowledgment before build.

**Gate pending:** authorization, retention, edge handling, recovered rationale, source verification and independent comprehension review.

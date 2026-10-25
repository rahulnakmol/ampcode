# Own the outcome, not every line

Use the whiteboard defense after grilling and before implementation handoff. It tests whether the
owner can explain and justify the proposed system. Before final delivery, refresh it against the
actual system and evidence. No memorization of function names, code trivia, or exhaustive design
document is required. A small, low-risk slice can use a short explanation; consequential designs
need challenge from a separate reviewer context or person.

## Explain six things in simple terms

| Challenge | A defensible answer |
| --- | --- |
| What is done, and why does it matter? | Customer problem, observable benefit, acceptance IDs, non-goals, and a result that would disprove success |
| How does it work? | Main journey, components, data movement, owners, dependencies, and trust boundaries; use a small diagram if useful |
| Why X instead of Y? | A credible alternative, constraints, costs and benefits, why the simpler option is or is not enough, and when to revisit the choice |
| Why this data model or structure? | Operations it supports, invariants, access patterns, ordering/consistency and scale assumptions; no invented performance claims |
| What can a malicious actor do? | Specific actor/action, authorization boundary, possible impact, prevention or containment, and a negative test |
| Where does this fail? | Partial writes, retries, concurrency, unavailable dependencies, recovery and preservation limits; unresolved evidence and the next check |

Ground statements in inspected contracts, measurements, or the confirmed brief. Label design
proposals as proposals and assumptions as assumptions. Do not pass by reciting headings. A claim
such as “exactly once” needs a mechanism that survives the relevant partial failures, not confidence
or a test count. If a dimension is inapplicable, state why; do not manufacture a threat or tradeoff.

## Challenge the design before handing it off

The owner gives the explanation. A challenger probes the consequential decisions with concrete
counterexamples. For low-risk work, explicit self-challenge is sufficient; for consequential work,
use an independent context or person. The owner retains responsibility for resolving findings.
The challenger reports gaps, not a preferred implementation to copy without thought.

Record **ready for implementation** only when:
- Each applicable challenge has a grounded answer and the acceptance criteria are falsifiable.
- No unresolved contradiction or unknown mechanism blocks the first useful slice.
- Remaining assumptions have handling and revisit triggers; required experiments/tests have owners.
- The receiving agent has the actual brief, defense, relevant evidence, and accessible candidate
  materials, then explains the outcome, approach, constraints, key risks, and first check back in
  its own words. Correct errors before handoff. If the owner will implement, its defense serves
  as the teach-back; do not spawn another agent merely to repeat it.

A proposed design need not already have passed its future runtime tests. Readiness permits the
bounded harness/implementation step; it does not mean verified, shipped, or safe in production.
Use **blocked** for missing understanding or materials, **investigate** for discoverable facts or
bounded empirical questions, and **reframe** for changes to customer expectations. Preserve completed
work while resolving the gap. Do not demand another user approval for unchanged approved scope.

## Keep the explanation true as the system changes

Reopen the affected defense when a change alters a decision, ownership, data semantics, trust
boundary, or failure behavior. Transfer the revised record and obtain an updated recipient
teach-back when handing off. Do not reuse an old explanation merely because the tests passed.
At delivery, explain the implemented system from its inspected artifacts and current evidence.
Keep the original two build-review gates; this defense is neither of them.

## Record only what another owner needs

Add this block to the mission record; link existing evidence rather than copy it:

```markdown
## Ownership defense
- Brief/candidate revision and owner:
- State: ready for implementation | blocked | investigate | reframe
- Customer outcome and acceptance IDs:
- System/data flow and trust boundaries:
- Decisions: choice / alternative / rationale / evidence or proposal / revisit trigger
- Data structures and invariants:
- Malicious actor and failure/recovery cases:
- Assumptions and missing evidence: impact / owner / next check
- Challenge: reviewer / counterexample / disposition
- Teach-back: recipient / transferred materials / explanation / corrected gaps
- Freshness: changes since defense / affected decisions / updated evidence
```

Use standard/formal mode for this record unless the user chooses otherwise. Editorial explanations
can accompany it; ELI5 summaries cannot omit blockers or replace the underlying evidence.

# Own the outcome, not every line

Run the whiteboard defense after grilling, the design (spec, plan, technical design and rendered
UX) and the fresh-context design review, and **before kickoff**. The defense record becomes part
of the contract, so the owner approves a design its integration owner has already defended. It
tests whether the integration owner can explain and justify the proposed system. No memorization
of function names, code trivia or an exhaustive design document is required. A small, low-risk
item can use a short explanation; consequential designs need challenge from a separate reviewer
context or person.

## Explain six things in simple terms

| Challenge | A defensible answer |
| --- | --- |
| What is done, and why does it matter? | Customer problem, observable benefit, criteria IDs, non-goals, and a result that would disprove success |
| How does it work? | Main journey, components, data movement, owners, dependencies, and trust boundaries; use a small diagram if useful |
| Why X instead of Y? | A credible alternative, constraints, costs and benefits, why the simpler option is or is not enough, and when to revisit the choice |
| Why this data model or structure? | Operations it supports, invariants, access patterns, ordering/consistency and scale assumptions; no invented performance claims |
| What can a malicious actor do? | Specific actor/action, authorization boundary, possible impact, prevention or containment, and a negative test |
| Where does this fail? | Partial writes, retries, concurrency, unavailable dependencies, recovery and preservation limits; unresolved evidence and the next check |

Ground statements in inspected contracts, measurements, or the confirmed brief. Label design
proposals as proposals and assumptions as assumptions. Do not pass by reciting headings. A claim
such as "exactly once" needs a mechanism that survives the relevant partial failures, not
confidence or a test count. If a dimension is inapplicable, state why; do not manufacture a threat
or tradeoff.

## Challenge the design before the baseline

The owner of the outcome gives the explanation. A challenger probes the consequential decisions
with concrete counterexamples. For low-risk work, explicit self-challenge is sufficient; for
consequential work, use an independent context or person. The integration owner resolves the
findings; the challenger reports gaps, not a preferred implementation.

Record **ready for kickoff** only when:

- each applicable challenge has a grounded answer and every criterion is falsifiable, with a
  finite list of cases;
- no unresolved contradiction or unknown mechanism blocks the first milestone;
- remaining assumptions are open questions with defaults, or have handling and revisit triggers;
- required experiments and tests are items with owners.

A proposed design need not already have passed its future runtime tests. Use **blocked** for
missing understanding or materials, **investigate** for discoverable facts or bounded experiments,
and **reframe** for changes to customer expectations, all before the baseline.

## Hand off with a teach-back

Each child or subagent gets the item's contract slice, which includes the defense. Its first
check-in explains the outcome, approach, constraints, key risks and first check in its own words;
correct errors before it builds. When the steering thread builds an item itself, its defense
serves as the teach-back; do not start another agent merely to repeat it.

## Keep the explanation true as the system changes

Refresh the defense against the implemented system at each milestone's gate 2 and record the
refresh in that gate's review record, never in the contract, so the approval stands. A refresh
that finds a decision, data semantics, trust boundary or failure behavior no longer holds, with no
reading of the contract that works, is stop reason 1. Do not reuse an old explanation merely because
the tests passed. At close-out, explain the implemented system from its inspected artifacts and
current evidence.

## Record only what another owner needs

Put this block in the contract's defense field; link existing evidence rather than copy it:

```markdown
## Ownership defense
- Package revision and integration owner:
- State: ready for kickoff | blocked | investigate | reframe
- Customer outcome and criteria IDs:
- System/data flow and trust boundaries:
- Decisions: choice / alternative / rationale / evidence or proposal / revisit trigger
- Data structures and invariants:
- Malicious actor and failure/recovery cases:
- Assumptions and missing evidence: open question and default, or owner and next check
- Challenge: reviewer / counterexample / disposition
```

Use standard/formal mode for this record unless the user chooses otherwise. Editorial
explanations can accompany it; ELI5 summaries cannot omit blockers or replace the underlying
evidence.

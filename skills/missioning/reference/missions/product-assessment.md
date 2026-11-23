# Playbook: product and SaaS assessment

## When to use

A technical and functional assessment of software or SaaS products: shortlisting vendors,
choosing one, or checking one against requirements. Not for a pre-sales response to a client's
RFP (`shaping-engagements` through `blueprinting`).

## Skills

- `missioning`: the conductor for this mission.
- `discovering-requirements` or `specifying`: the requirements.
- `assessing-products` (planned, wave 2). Fallback: agree criteria and weights before any
  scoring; score each product with cited evidence; label vendor claims "claimed" until checked in
  a sandbox or a document; recommend with conditions. Label it "manual, no skill".
- `threat-modelling` (planned, wave 1). Fallback: check security and compliance evidence (SOC 2
  Type II, ISO 27001, penetration test summary, data processing terms), identity (SSO, SCIM) and
  data residency against the requirements.
- `architecting` (planned, wave 1). Fallback: check integration (APIs, events, limits), exit
  options and total cost against the requirements.
- Shared fit-gap scoring in `shaping-engagements`: planned enhancement, wave 2. Fallback: score
  in a script from the agreed weights.
- `reviewing-engagements` and `publishing-engagements`: review and publish the report.

## Steps

1. Charter the mission with `missioning`.
2. Write the requirements with the decider.
3. Agree the criteria, the weights and the shortlist rule at kickoff; freeze them in the
   decision trail.
4. Build the long list; shortlist by the agreed rule.
5. Gather evidence per product; label every unverified claim.
6. Verify the claims that matter in a sandbox or a document.
7. Score from the frozen weights with a script.
8. Review the conclusions; write the recommendation with conditions and owners.
9. Publish the report as an effect, pre-authorized or asked; close out.

Milestones: M1 long list and shortlist (step 4), M2 evidence and scores (5 to 7), M3
recommendation and publication (8 and 9).

## Human gates

- Kickoff: requirements, criteria and weights, with the shortlist rule as an open question with
  a default.
- Publishing the report: an effect, pre-authorized at kickoff or asked.

The recommendation goes to the decider in the close-out; the buying decision is theirs, after the
mission.

## Definition of Done

The weights were fixed before scoring, every score cites evidence, unverified claims are
labelled, and each condition of the recommendation has an owner.

## Red flags

- Weights changed after scores were seen.
- A vendor claim reported as fact.
- A score the model produced without a script.
- A recommendation without conditions or owners.

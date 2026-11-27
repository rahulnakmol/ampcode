# Product and SaaS assessment mission

A technical and functional assessment of software or SaaS products: shortlisting vendors,
choosing one, or checking one against requirements. Playbook:
[`product-assessment.md`](../../skills/missioning/reference/missions/product-assessment.md).
[All missions](README.md).

## Use it when

- you must choose between products and defend the choice with evidence;
- a product must be checked for security, compliance, integration and exit before you buy.

Not for a pre-sales response to a client's RFP (use `shaping-engagements` through
[Blueprinting](../blueprinting.md)). The buying decision stays yours, after the mission.

## Start it

```text
Use missioning to run a product assessment of [products or category] for
[team]. [Name, role] decides; [name, role] approves. Open question: paid
trials, default none. Agree the weights with me before any scoring.
```

Before drafting, the agent asks you once for: the must-haves, the tier or plan to assess, and the
document that governs each plan. You then approve, once, the requirements, the criteria and their
weights, with the shortlist rule as an open question with a default. The weights are frozen with
a digest before any product is scored.

## How it runs

| Milestone | What happens | Skills |
| --- | --- | --- |
| Kickoff | Requirements written with the decider; criteria, weights and shortlist rule frozen | `discovering-requirements` or `specifying`, `assessing-products` |
| M1 Long list and shortlist | Long list built; shortlist by the agreed rule | `assessing-products` |
| M2 Evidence and scores | Evidence per product, vendor claims kept "claimed" until checked; the claims that matter verified in a sandbox or document; threat model of each product's place in your data flows; integration and exit fit; scores from the frozen weights, by script | `assessing-products`, `threat-modelling`, `architecting`, `shaping-engagements` (fit-gap) |
| M3 Recommendation and publication | Conclusions reviewed; a recommendation with conditions and owners; report published | `reviewing-engagements`, `publishing-engagements` |

`missioning` itself conducts.

## Gates you decide

- Kickoff (above).
- Publishing the report, pre-authorized at kickoff or asked.

## Done when

The weights were fixed before scoring, every score cites evidence, unverified claims are labelled,
and each condition of the recommendation has an owner.

## Example

**ITSM choice: ServiceNow, Jira Service Management or Freshservice** (validation run 8a, scores
8/8/8). The mission scored three service-desk products from frozen weights with cited evidence,
but scored Freshservice on the wrong tier; the owner-facts round now asks which tier or plan to
assess. In the Otter.ai run for an EU client (8b), one plan's score moved from 45 to 51, crossing
the 50-point line, and the stop brief did not say so; `assessing-products` now shows earlier
totals beside new ones.

## Adapt it

Scoring, freezing and sensitivity live in
[`assessing-products`](../../skills/assessing-products/SKILL.md); the weighted fit-gap in
[`shaping-engagements`](../../skills/shaping-engagements/SKILL.md).

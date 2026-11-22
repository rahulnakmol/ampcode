---
name: shaping-engagements
description: Shapes evidence-led enterprise opportunities, pre-sales offers and RFP responses. Use for bid decisions, proposals, fit-gap, effort estimates and commercial assumptions.
---

# Shaping engagements

Help the consultant establish a defensible offer and the next commercial decision.
Pre-sales qualification and RFP compliance are distinct tasks, not interchangeable checklists.

## Bind the shared engagement first

Load `blueprinting` through Amp's skill tool, even on direct entry. Bind to the coordinator base
returned by that tool, not this skill's directory, the engagement directory or a nearby checkout.
Read `reference/composition.md` at that base and follow its dependency and explicit-root checks
before using any helper. If resolution fails or is ambiguous, stop the affected work; do not
search for another installation or install one implicitly. Keep native Amp routing.

## Work from supplied commercial evidence

Read the coordinator's `reference/proposals.md`. It owns the shared fit-gap and estimate contracts.
For workshops or evidence acquisition, also read its `reference/discovery.md`; for client
confirmation, read `reference/decisions.md`. Load only the references needed for this decision.

Identify the buying decision, outcomes, stakeholders, constraints, proof needed and competing
options. Preserve client facts separately from sales hypotheses. For RFP work retain every
document/addendum and each mandatory obligation, response, evidence, exception and owner.
Do not invent references, compliance, product capabilities, staffing, rates or benefits.

Return the proposed scope, evidence-backed positioning, alternatives, unresolved obligations,
commercial assumptions, bounded estimate and next decision. Cost is not selling price; effort
is not elapsed time. Missing inputs become questions, not numbers. Preserve exact source revisions
and invalidate affected responses after an addendum. No offer or submission is sent automatically.

## Score a weighted fit-gap

When the client wants options compared or a scored fit-gap, use `assessing-products` as a
dependency: load it through Amp's skill tool and run its `scripts/score.py`. Each requirement is
a criterion. Agree every weight with the client, record who agreed and when, and freeze the
weights with `score.py freeze` before any fit category is assessed or scored, so nobody who sets
the weights has seen the categories. Record the printed digest. The weights stay frozen; a
change needs a recorded client decision and a new freeze, never a quiet edit after the fits are
seen. Record each cell as `{"fit": "<category>", "evidence": "<source and date>",
"status": "verified"}`, or `"claimed"` for a vendor statement nobody checked, then run:

```bash
python3 <assessing-products base>/scripts/score.py score criteria.json fitgap.json --fit-gap --expect sha256:<digest>
```

The script converts each fit category by the map below (`FIT_GAP_SCORES` in `score.py`), totals
each option out of 100 and refuses an unknown category. The categories and their evidence rules
stay in `proposals.md`; the map only scores them. Every `unresolved` fit is listed as a gap: make
it a named question or exception with an owner. Without `assessing-products` or a shell, do not
total by hand; return the unscored fit-gap and label the scores "not run".

| Fit category | Score |
| --- | --- |
| supported | 5 |
| configuration | 4 |
| extension | 3 |
| integration | 3 |
| process change | 2 |
| unresolved | 0 |

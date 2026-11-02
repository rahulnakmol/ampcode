# Functional coverage and sub-mission return

Use when drafting or assessing the functional specification and implementation kickoff baseline.
Read decisions.md only when recording business agreement, and proposals.md for fit-gap/estimates.

## Specification that someone can challenge

Use stable IDs and exact evidence links. A useful specification contains:

1. Business drivers, outcomes, measures, current baselines, targets and unknowns.
2. Scope and authorized exclusions; assumptions, dependencies and constraints.
3. As-is processes with pain, evidence and measured effects; proposed to-be changes and rationale.
4. Actors, responsibilities, decision rights, concerns, use cases and their mapping.
5. Target operating model and cross-team handoffs.
6. Functional requirements: actor, trigger, preconditions, business rules, data used/produced,
   expected outcome, receiving role, exception handling and observable acceptance.
7. Fit-gap with product/version evidence where relevant; options and unresolved research.
8. Decisions and written confirmation, contradictions, risks, actions and explicit gaps.
9. Source/claim/requirement/decision/artifact lineage and change history.

Do not fill unknown sections with plausible prose. A draft with named gaps is useful; a completed
baseline cannot conceal them. Distinguish functional business controls from a technical architecture.
Treat technical questions as dependencies for the appropriate specialist, not invented solutions.

## Structural coverage check

Run `python3 scripts/engagement.py --root <engagement-directory> coverage <mission-id>`.
This checks the declared ledger, not whether the author omitted a whole process. `ready: true`
means structurally consistent reported coverage, not client acceptance or semantic completeness.
Independent source-grounded review and the consultant's judgment remain required.

Use `data` on retained records, with all exact references also in `inputs`:

- **Requirement:** text `actor`, `trigger`, `outcome`, `verification`; nonempty `rules` list;
  `handoffs` entries with `to`, `when`, `information`; `exceptions` entries with `condition`,
  `response`, `owner`; nonempty `sources` exact references; `gaps` list. Where no handoff or
  exception applies, supply an empty list and evidence-backed `handoff_rationale` or
  `exception_rationale`. Do not invent an exception merely to satisfy a field.
- **Material source:** `date`, `location`, `author`, `verification: checked`, `checked_by`,
  and `uncertainties: []` only after actual checks. Preserve unknowns in drafts. For audio, record
  checked spans in the body; the script cannot determine fidelity or whether a citation entails a claim.
- **Mission:** exact `intent` reference to the stable business-intent source; nonempty
  `criteria` entries with stable `id` and observable `description`;
  `coverage` entries with `criterion`, exact requirement `record`, and `disposition` of
  `supported`, `excluded` or `unresolved`; explicit `children`, `findings` and `gaps` lists.
  Missing/duplicate coverage and unresolved gaps prevent a passing structural result.
- **Excluded requirement:** retain its scope and proposed exclusion as the exact target, plus
  a `decision` reference in coverage. Both the decision and its written confirmation need
  `intent: exclude`; ordinary acceptance is not permission to discard a requirement.

## Sub-missions return evidence, not just a done flag

Use a milestone, parallel workstream or deeper investigation when it isolates a real question.
Give it a bounded outcome, applicable parent criteria, inputs, owner, evidence needed, exit
condition and return format. Keep shared business intent in its own stable record; children can
depend on that intent without depending on a parent progress report that changes on every return.
Changing the intent then stales affected children without creating cyclic snapshot dependencies.

A child's `findings` list contains exact retained references. For each child, the parent stores
`mission` and `integration` references. Integration is a `review` record whose data includes the
exact `child`, all its `findings`, `unresolved` gaps, affected `parent_criteria`, named `reviewer`
and `disposition: integrated`. Bind it to the receiving `parent` ID and exact `parent_intent`
source reference. `parent_criteria` contains complete criterion objects, not bare IDs, so a
changed criterion description requires a fresh review. Another parent cannot reuse this review.
The checker verifies coverage, current child evidence and return
consistency. The reviewer must verify the findings actually changed or informed parent conclusions.
An unresolved child gap keeps completion open; use scoped written client exclusion where appropriate,
not silent deletion. A later source correction reopens affected child and parent conclusions.

## Kickoff is not a second discovery theater

Compare the agreed baseline with current reality: changed scope, missing source access, actual
owners, resource assumptions, unresolved decisions and delivery dependencies. Carry proposal
assumptions forward explicitly. Produce a kickoff pack only for the needed scope: baseline and
exceptions, responsibilities, decision calendar, workstreams, readiness checks, acceptance and
first actions. A commercial signature does not prove all functional details were agreed.

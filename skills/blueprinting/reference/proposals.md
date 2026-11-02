# Pre-sales, RFP responses and grounded estimates

Qualify pre-sales and RFP separately. Pre-sales discovers a defensible offer; an RFP also requires
complete obligation-by-obligation response traceability. Neither journey grants a contract or
price commitment. Retain assumptions, exceptions and named commercial decision authority.

## Pre-sales

Clarify the decision, desired outcomes, buying process, constraints, alternatives, proof needed,
affected stakeholders and why action is needed now. Distinguish a client fact from a sales
hypothesis. State the offer's scope, deliverables, exclusions, responsibilities, dependencies,
acceptance, estimate range and the next decision. A declared preferred option still needs material
counterevidence and the conditions that would change it. Never invent ROI or a guaranteed timeline.

## RFP-to-proposal

Retain every supplied document and addendum with version/date. Inventory mandatory obligations,
evaluation criteria, requested evidence, submission instructions and unanswered questions. Build
a matrix: obligation ID, exact source/span, requirement, proposed response, evidence, exception
or unresolved gap, owner and affected deliverable. Account for every obligation once; cross-reference
duplicates without losing them. A new addendum reopens affected responses. No invented certification,
customer reference, product feature, staffing availability or compliance claim. No automatic submission.

## Fit-gap is conditional on evidence

For each applicable requirement record product, version/edition, deployment assumptions, fit
category (supported, configuration, extension, process change, integration or unresolved), evidence
source/date, limitations, alternatives and follow-up. Verify consequential vendor claims against
current authoritative sources. A marketing page is not proof for a specific configuration. Separate
standard product support from a proposed customization, a partner claim and a demo observation.

## Reproducible estimates

Decompose effort by activity, role, quantity and range per unit. Explain the basis: measured
analogues with context, supplier quotes, a discovery assumption or a bounded expert estimate.
Include discovery, configuration, data work, integration, validation, deployment preparation,
training/change, governance and handover only where applicable. Avoid double-counting shared work.

Run `python3 scripts/estimate.py <inputs.json>` for deterministic arithmetic. It emits JSON and
has no network or write effects. Retain the inputs and output as linked engagement artifacts.
Schema 1 inputs have `currency`, ISO `rate_date`, nonempty `assumptions` and `basis` string lists,
`contingency_percent`, and nonempty `activities`. Each activity has `id`, `activity`, `role`,
`basis`, `quantity`, `days_per_unit_low`, `days_per_unit_high`, `day_rate`, and predecessor IDs
in `after`. Numeric strings preserve decimal inputs. A row may declare `currency`, which must
match the packet; perform any conversion explicitly with reviewed rate/date/source before calling.

The result separates person-day effort, base cost, contingency and total cost, and orders dependency
stages. Cost is not selling price; margin, taxes, expenses and price approval remain explicit
commercial work. Dependency stages are not elapsed time. Build a feasible roadmap using actual
staffing, parallel work limits, calendars, procurement/decision waits, plant shutdown windows,
entry/exit conditions and contingency. Do not divide effort by an invented team size and call it
a promise. Ranges state uncertainty; base and contingency are separate. Recompute when scope,
rates or assumptions change, and keep earlier versions and their limitations.

Missing estimating inputs produce named questions, not fabricated numbers. A valid synthetic
calculation proves arithmetic only, not the realism of an enterprise transformation estimate.

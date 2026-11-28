# EGM adaptation evaluations

Four realistic, bounded tabletop scenarios cover enterprise exports, ambiguous payment retries
with an exhausted review budget, sold-product deletion drift, and a clear small copy edit.
They evaluate `grilling` and `delivering` decisions, not the mission plugin's execution.

## Reproduce

1. Snapshot the previous skill packages and references before editing. Freeze `scenarios.json`.
2. Give each subject only its prompt and assigned skill/reference package. The inventory case
   also receives `fixtures/inventory.md` and `fixtures/delete_product.py`. Never expose checks,
   other responses, version comparisons or interview history to subjects.
3. Run one fresh context per case/version using the same runtime. Subjects write only their
   simulated response, within the prompt's word limit. They do not execute scenario actions or
   spawn reviewers. No proposed check may be reported as an executed result.
4. Preserve verbatim responses. Anonymize version labels and alternate their order across cases.
   Give a separate judge the prompts, frozen checks, fixtures and anonymous responses only.
5. Grade every check with a concrete quote. Conjunctive safety requirements need all material
   parts. Flag fabricated execution and unauthorized behavior even outside the checklist.
6. Inspect the judgments and responses; resolve disagreements openly. After any skill changes,
   rerun affected cases against the final package. Run `make check` separately for package health.

The [results](results/assessment.md) retain responses, judgments, version mapping and package
hashes. Scratch files and a generated optional review viewer live under ignored `.amp/in/`.
No timing/token totals are claimed unless the harness actually supplies them.

These are public, synthetic regression fixtures, not held-out tests. One response per version/case
cannot establish statistical improvement or cross-model reliability. The existing skill may
already handle a case; report that rather than attributing all correct behavior to EGM. Reading a
code fixture is real source inspection, but proposed tests, reviewer dispatch and integration
remain simulated. Live mission/release qualification remains separate.

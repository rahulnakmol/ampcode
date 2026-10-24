# Delivering: design and source rationale

The user approved an instruction-only skill named `delivering`: reuse grilling for expectations,
then execute outcome-driven TDD, working commits, real journeys, review, repair/revalidation,
second review, customer value, and authorized dev integration. No plugin or daemon is included.

## Sources examined

Research used Parallel Task MCP run `trun_8ed7a8c7a37043b48fa31560de9dd8cf` (completed
2026-10-24), direct reads of the four requested references, current repository guidance, and the
[grilling development thread](https://ampcode.com/threads/T-01a169c3-b5c6-72da-b9cc-4b4a45551a4e).

| Source | Adopt | Do not infer |
| --- | --- | --- |
| [Cursor Projects docs](https://cursor.com/docs/agent/projects) and [announcement](https://cursor.com/changelog/projects) | Explicit ownership, reusable context and handoffs | A skill supplies synchronized files, cloud persistence, subscriptions, or thousands of workers |
| [Factory Missions announcement](https://factory.com/news/missions) | Bounded slices, milestone validation, targeted parallelism | Marketing recovery claims guarantee unattended completion |
| [Factory overview](https://docs.factory.com/missions/overview) | Approved expectations, scriptable representative user journeys, active intervention | Mock-only checks establish end-to-end correctness |
| [Factory architecture](https://factory.com/news/missions-architecture), followed by the research agent | Assertion-first decomposition and separate scrutiny/user testing | Those two validator roles equal the user's two temporally separated review gates |
| [Amp docs](https://ampcode.com/docs) and tool contracts in the executing session | Actual available agent, execution and handoff capabilities | Separate threads inherit local changes, authority, or complete context |
| Existing `grilling` and its evaluations | Confirmed brief as the contract; scenario-based testing with honest limits | A structural check proves semantic behavior or guaranteed triggering |

Vendor descriptions are first-party claims, not independently measured reliability. User policy
and current tool contracts govern execution. Research recommendations are not permissions.

## Decisions

- Keep the exact ten-step delivery order. Both reviews are explicit; consequential changes need
  independent review, including after repair. A no-findings first review does not erase gate two.
- Keep skill instructions and two small references; no executable state manager. Evidence records
  aid continuity but do not enforce gates programmatically.
- Reuse confirmed expectations; do not re-interview or introduce redundant approval at every slice.
- Default local state to ignored `.amp/in/missions/`, preserving/transferring it before cleanup.
  Follow existing committed-plan conventions where present. No secret-bearing evidence in Git.
- Separate public-contract regression tests from scratch validation; no keyword-count tests of
  instruction prose. Preserve raw sanitized evaluation responses so claims can be inspected.
- Missing CI, missing runtime, or exhausted budget blocks the relevant gate. Do not turn absent
  evidence into a pass. No universal retry budget or fabricated improvement metric.
- Respect dev → rolling → main and separate deployment/publication authorization. The skill
  itself is portable to repositories with another explicit integration policy.

## Implementation and qualification plan

1. Inspect current dev, grilling's actual handoff, and repository validation; create an isolated
   worktree. Run the baseline `make check` before authoring.
2. Define adversarial cases in `evals/delivering/scenarios.json`, then author
   `skills/delivering/SKILL.md` and its mission/review references against the agreed contract.
3. Compare fresh with-skill and baseline responses without exposing the rubric to test subjects.
   Inspect concrete decisions, repair omissions, and rerun affected cases after any changes.
4. Update README routing/publication guidance and record results. Run `make check`, JSON parsing,
   relative-link checks and `git diff --check`. Inspect the final package and record limitations.
5. Commit and push the feature branch under standing authorization; use a PR to dev. Merge only
   if the actual integration gate permits it. No implicit rolling/stable or Personal publication.

The unit of delivery is this instruction package, not an orchestration runtime. Qualification
separates package validity, simulated agent decisions, and live mission execution; none stands
in for the others.

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
- Keep skill instructions and focused references; no executable state manager. Evidence records
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

## Ownership and communication follow-up

The user added a whiteboard defense between grilling and implementation handoff, then requested
standard/formal and editorial modes, ASD-STE100-aligned principles, and ELI5 under 300 words.
The defense is a design-understanding gate, not proof that future tests have already passed. It
checks alternatives, data structures/invariants, malicious actors, and failure limits without
demanding line-level recall. The receiver must read actual materials and explain the plan back.
Design drift reopens the affected defense; the two original build reviews remain separate.

All 13 rules in the user's supplied text are mapped below. The source is the attachment in the
[delivery thread](https://ampcode.com/threads/T-01a16f76-cc55-77ee-b421-dff55ba10ea0); no private
attachment URL or payload is needed to use the skill.

| Rule | Where it applies |
| --- | --- |
| 1. Think before coding | Grilling, explicit assumptions/alternatives, defense, stop and name confusion |
| 2. Simplicity first | Step 4: smallest useful implementation, no speculative or unjustified single-use abstractions |
| 3. Surgical changes | Step 4: task-owned changes only, no adjacent cleanup/refactoring for taste |
| 4. Goal-driven execution | Acceptance-to-evidence mapping, outcome-first execution, customer-value gate |
| 5. Model for judgment | Step 4: code/tools handle deterministic routing, retries, transforms and counts |
| 6. Token budgets | 4,000/task and 30,000/session unless overridden; disclose unavailable telemetry, preserve usage across handoff, no reset evasion |
| 7. Surface conflicts | Step 1: choose by authority, provenance, recency and tested behavior, never average contradictions |
| 8. Read before writing | Step 1: exports, callers, shared utilities, contracts and observed behavior |
| 9. Test intent | Step 3: customer rationale, independent expected results, plausible wrong-business-rule controls |
| 10. Checkpoint significant steps | Resume section: changed/verified/remaining/next action; reconstruct state when lost |
| 11. Match conventions | Step 4 and handoff: use established conventions; surface harm instead of silently forking |
| 12. Fail loud | Step 5 and final report: name skipped work and uncertainty; required omissions block completion |
| 13. Inspect before completion | Step 5: open actual output, compare with original request, report observations not intentions |

Two refinements avoid misleading literal interpretations. An optional inapplicable check with a
reason does not make required checks fail; a skipped required check does block completion. Model
judgment includes engineering tradeoffs, not only classification and drafting. These interpretations
were proposed in the conversation before the user asked to bake all inputs in.

ASD guidance here is stylistic alignment, not formal vocabulary/rule validation. Token budgets are
instructions, not a metering implementation. This work does not claim exact token compliance or
production reliability. The follow-up evaluation uses frozen assertions, fresh test-agent contexts,
two blinded judge contexts, paired original-skill cases, and targeted reruns after feedback.

## Elephant-Goldfish adaptation

On 2026-10-25 the user approved adapting EGM into `delivering` and `grilling`, evaluating
three to five realistic scenarios, then integrating into dev. This changes skill guidance only;
it does not import the upstream plugin, change mission-control schemas or publish Personal copies.

Sources inspected:
- [Google Research publication entry](https://research.google/pubs/elephants-goldfish-and-the-new-golden-age-of-software-engineering/)
  and the full linked [Dave Rensin article](https://drensin.medium.com/elephants-goldfish-and-the-new-golden-age-of-software-engineering-c33641a48874),
  dated April 27, 2026, with its October plugin update. It is practitioner experience and argument,
  not a controlled productivity or reliability study.
- [Upstream EGM](https://github.com/google/elephant-goldfish-model/tree/3d0b34821ce88ad328b0c9bf0e06d7eb5f1cd669),
  specifically the review/drift skills and comprehension/readiness personas. Apache-2.0 project;
  this package uses original, attributed guidance rather than copying or bundling upstream files.
- [AI LABS video](https://www.youtube.com/watch?v=xxf6D9jynFw): retrieved its publisher description
  and chapter outline, not the full transcript or audiovisual demonstration. The description's
  sold-product deletion example informed a synthetic evaluation fixture, not a claim to reproduce
  the demo application. The article and source files ground the actual workflow decisions.

Adopt: distinct problem and grading criteria; a context-rich integration owner; compact decisions
and alternatives rather than chat dumps; fresh read-only comprehension, critique and readiness
contexts; repairs written into the packet; source-grounded drift checks on resume and final review.
Keep consequential choices explicit while leaving routine implementation choices with the builder.

Adapt rather than copy: reuse grilling comprehension evidence only for matching revision/scope;
place design review before owner acknowledgment, then retain whiteboard defense and both build
reviews. Scale review count to risk. Do not demand exhaustive docs for unrelated code, a comment
every ten lines, new providers, nested delegation, mandatory report files for every conversation,
or a fixed swarm. Do not bias reviewers with either praise or a demand to invent faults.

Reject the upstream review skill's automatic advancement/accepted-tradeoff behavior after its
one-re-audit cap. Here an exhausted attempt budget preserves blockers and requires an authorized
next decision, never fabricated acceptance. Missing reviewers are also a blocker when required.

Qualification: four frozen paired tabletop scenarios with eight fresh contexts, old-package
snapshots, prompt-only subject inputs, source fixtures where applicable and an anonymized judge.
See [the evaluation record](../evals/egm/README.md). These assess decisions and handoff proposals,
not automatic reviewer dispatch, real payment/storage safety, production delivery or trigger rates.

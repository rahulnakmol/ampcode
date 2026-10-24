# crafting evaluation results

Run on 2026-10-24 against [`skills/crafting/`](../skills/crafting/SKILL.md) (merged in #11) with the
data and method in [`evals/crafting/`](../evals/crafting/README.md). Every role (router, agent under
test, simulated user, judge) was an Amp subagent. Judges never read the skill's Markdown. These are
LLM judgments on a small set, not statistically strong measurements: treat differences under about
0.1 as noise.

## Trigger routing

40 first messages, 10 competing skills from the local plugin cache plus `grilling`, two
independent router judges.

| Router | Should load (27) | Should not load (13) |
| --- | --- | --- |
| A | 27/27 | 0 false positives |
| B | 27/27 | 0 false positives |

Both routers sent "design the tool list for our API" to `crafting` and "build an MCP server; I
already have the tool list" to `build-mcp-server`, co-loaded `a11y-debugging` for a WCAG audit of a
signup flow, and left a one-line CSS color change, LCP debugging, and "grill me" to other skills.
Both flagged that `frontend-design` overlaps without a stated division of work, and that
`brainstorming` and `grilling` claim almost every creative task.

## Behavior

Scalar = hard-check pass rate × mean of six 1–5 scores ÷ 5 (see `rubric.md`). Two of nine agents
under test were interrupted once by a model-provider error and resumed from their saved files.

| Scenario | Entry | Judge A | Judge B | Mean | Hard fails |
| --- | --- | --- | --- | --- | --- |
| c01 kids reading app (4 turns) | Discover | 0.80 | 0.63 | 0.72 | B: unlabelled behaviour claim, over-attributed citation |
| c02 CLI `preview deploy` | Craft | 0.83 | 0.83 | 0.83 | — |
| c03 invoicing MCP server | Craft | 0.87 | 0.70 | 0.79 | — |
| c04 WCAG 2.2 audit (17 seeded defects) | Audit | 0.69 | 0.69 | 0.69 | Both: "who is affected" missing on half the findings |
| c05 A2 poster and carousel | Craft | 0.66 | 0.60 | 0.63 | Both: square asset without alt text or caption |
| c06 slop landing-page critique (16 seeded) | Critique | 0.83 | 0.64 | 0.74 | B: "verified" claim contradicted by its own screenshot |
| c07 couples-finance mood board | Inspire | 0.73 | 0.67 | 0.70 | — |
| c08 usability notes + "simulate 5 users" | Study | 0.80 | 0.63 | 0.72 | B: UI facts inferred beyond the notes |
| c09 two-word copy change | Refine | 0.80 | 0.80 | 0.80 | — |
| **All** | | **0.78** | **0.69** | **0.73** | |

Seeded-defect recall: the audit found 16 of 17 (both judges), the critique 16 of 16 (both judges).
Research spend stayed within budget in every scenario (at most $0.025 Parallel, 2 Firecrawl
credits, 7 Mobbin searches); no scenario ran Parallel Task, and the mood-board agent justified not
using its one allowed run. Judges verified the legal dates in c01, the MCP 2026-07-28 claims in c03,
the contrast ratios in c04 and c06, the survey statistics in c07, and the PDF page boxes and fonts
in c05.

### What worked

- **Need-finding.** Every judge scored need insight 4 or 5. Examples: "the five minutes a parent
  spends listening becomes both the progress measure and the teacher's log" (c01), "no URL until
  the CLI's own health check passes" (c02), "onboarding is two people agreeing, not data entry"
  (c07), read-back confirmation for money-moving tools (c03).
- **Integrity under pressure.** c08 refused to simulate users for an exec deck and planned real
  sessions; c09 made a two-line change without running the process; c04 found both blocking issues
  by manual testing after axe found only four.
- **Medium fluency.** Real terminal renders and a runnable JSON contract (c02), schema-validated MCP
  transcripts (c03), a real PDF with correct bleed and trim boxes (c05).
- **Cost discipline.** Every scenario climbed the ladder and logged spend before paying.

### Recurring defects, by how many scenarios showed them

| Defect | Scenarios | Example |
| --- | --- | --- |
| Claims outrun the artifacts | c02, c03, c04, c05, c06 | "every failure ends with its code" (false for 4 of 8); "verified" reduced-motion check contradicted by its screenshot; stale caption in a re-rendered mockup; severity counts off by one; a result reporting a date never sent |
| Unlabelled inferences | c01, c06, c08 | "dashboards get checked once, then ignored"; "shipping options don't show dates"; user device and sharing habits stated as fact |
| Happy paths polished, edge states thin | c01, c02, c03, c05 | A fresh agent made 11 guesses across 4 MCP tasks, all in states no transcript covered; no exit-1 network failure; no cold-start note; long-copy poster clipped but marked handled |
| Taste ceiling | c05, c06, c07 | Directions are "well-made category norms"; mood boards are pattern libraries without type, material, or out-of-category references; little local cultural texture; no named typefaces, scale, or grid |
| Independent review skipped | c02, c03, c05 | The agents under test had no subagent tool, so the fresh critique and the agent usability test were specified but not run |
| Agent safety gaps | c02, c03 | Bulk reminder send unguarded while single sends are; `cc` bypasses read-back; a suggested `next` command deletes another branch's preview |
| Premature assumptions | c01 | Assumed US and COPPA before asking about markets; email-first in a WhatsApp-first market |
| Scope and length | c01, c03, c06, c08 | Visual boards for headless MCP; scaffolding for report-only critiques; Study writing a brief; dense replies with internal codes; several decisions bundled into one "yes" |
| Facts on assets | c05 | Hero numeral from a secondary source contradicts the primary index (TomTom 2024: 34 min 10 s, not 30 min 10 s) |
| Audit hygiene | c04 | Not every axe failure became a finding; raw evidence for manual tests not saved |
| Print colour | c05 | RGB PDF with an out-of-gamut accent; no CMYK soft proof or fluorescent-spot recommendation |
| Copy-change judgment | c09 | "Start free trial" promises a trial the page never backs up |

### Suggested skill changes (from the judges, consolidated)

1. **Claim audit before every reply**: each "verified", "every", or "all" claim cites an artifact
   that shows it; grep every transcript and mockup for each declared principle; after copy changes,
   grep for superseded strings and re-render derived assets; reconcile numbers across files.
2. **Observed versus inferred**: tag claims about users, products, and research as observed (with
   a source or note ID) or assumption, in replies and artifacts alike; cite studies only for what
   the research note supports.
3. **Edge states by construction**: one state per CLI exit code (including internal and network
   failures); a cold-start state for metric-driven messages; mixed-membership states for worklists;
   stress states (long copy, clipping) checked against trim and live areas, with clipping blocking.
4. **Agent usability tests that can fail**: tasks must differ from the designed transcripts
   (new entities, mixed states, phrasing by description, stop requests), count guesses, and run in a
   fresh context. When no subagent is available, say so and hand the user a ready prompt instead of
   self-scoring.
5. **Raise the taste bar**: every direction names typefaces, a type scale, a grid, and one thing it
   refuses to do; names the category's expected answer and beats it; is backed by at least one
   look reference and one behaviour reference, with about a third of board references from outside
   the category; carries local cultural texture for place-specific audiences; and gets one lo-fi
   frame on the target platform's real chrome.
6. **Agent safety parity**: every outward or destructive tool gets the same server-side guard;
   every recipient field is in the read-back; `next` actions are agent-safe with an action enum
   (retry, fix input, fix code, needs human); run a prompt-injection and exfiltration pass.
7. **Ask before assuming jurisdiction or channel**: no legal research until markets are known;
   check each channel against the market's habits.
8. **Proportion**: skip boards and scaffolding for non-visual or report-only work; Study writes
   notes, findings, and plan only; cap blind spots at three per reply; plain language in replies
   with codes kept in files; never bundle several decisions into one "yes".
9. **Audit hygiene**: "who is affected" on every finding; every automated failure mapped to a
   finding or dismissed; raw evidence saved for manual tests.
10. **Facts and print**: primary sources for any number set as a hero; CMYK soft proof and spot
    colour advice when one saturated accent carries a print piece.
11. **Small changes**: one sentence flagging a risk the new copy creates, without fixing it.

### Limits of this run

- One run per scenario and two judges each; judge B was consistently stricter (0.69 vs 0.78).
- c01 used a simulated user; c03's usability test was run by a judge, not by the agent under test.
- Two agents were interrupted once and resumed; their judged output is the resumed result.
- The fixes below were applied after this run; see "Reruns after fixes".

## Reruns after fixes

The 11 suggested changes above were applied (round 2), and the weaker scenarios were rerun with
the same opening messages, fresh agents, and two fresh judges each. Round 2 introduced a regression
of its own: the new reply rule said "one question per decision" and dropped "at most three, each
with a recommendation", so c03, c05, and c07 all failed H2. Round 3 restored that rule and added
the judges' round-2 findings; c03 and c07 were rerun again.

| Scenario | Baseline A / B | Round 2 A / B | Round 3 A / B | Hard fails in latest run |
| --- | --- | --- | --- | --- |
| c03 invoicing MCP server | 0.87 / 0.70 | 0.57 / 0.52 | 0.83 / 0.63 | B: 5 of 11 tools lack a "when not to use" clause |
| c04 WCAG 2.2 audit | 0.69 / 0.69 | 0.83 / 0.83 | not rerun | — |
| c05 A2 poster and carousel | 0.66 / 0.60 | 0.59 / 0.60 | not rerun | Both: H2 (fixed in round 3, untested here) |
| c07 couples-finance mood board | 0.73 / 0.67 | 0.71 / 0.66 | 0.87 / 0.80 | — |

Mean of the latest run per scenario: 0.75, against 0.70 for the same four at baseline.

- **c04**: recall rose from 16/17 to 17/17; every finding names who is affected and every axe
  failure is reconciled. New defect: scope creep (a full fixed copy and test tooling in the project
  root), addressed in round 3.
- **c05**: the alt-text check (H7) now passes; the remaining hard fail is the question rule. Craft
  defects remain: the event type does not read at 3 m, forwarded assets omit the action, the PDF
  text layer duplicates halo strings and drops Kannada conjuncts, and a feed mockup kept stale copy.
- **c07**: the first run where every hard check passes. 44% of images come from outside the
  category, every direction is sketched on the invitee's first screen, and only one Mobbin search
  was repeated (three at baseline).
- **c03 fresh-agent test**: 11 guesses in all three versions (round 3: 4, 2, 3, 2). Safety improved
  (approval binds every recipient and free-text field, sends re-check at send time, non-goals are
  stated), but rules still leak into transcripts and `HANDOFF.md`, and annotations disagree with
  descriptions. The agent under test had no subagent, so it never ran the fresh-agent test itself.
  Round 3 therefore adds a mechanical gate, `design_kit.py tools`, which flags 7 tools in the
  round-3 output (the 5 the judge found plus 2 that phrase the clause another way).

Changes in rounds 2 and 3: closing questions capped at three with a recommendation each; mood boards
lead with look and feel, link every image, keep assumption labels, and sketch every direction on the
same moment of truth with a pressure-free exit; one image search per call; audit replies carry
severity, criterion, and who is affected, with fixed copies only on request and tooling out of the
project root; MCP guidance adds "Not for" clauses, stated non-goals, approval binding for every
outward field, send-time eligibility re-checks, annotation audits, lookup or no-match results for
every reference parameter, and a per-tool defaults sweep; print adds what/when/where at viewing
distance, press files with available tools, PDF text extraction checks, and photocopy variants;
social requires the action on forwardable assets and typesetting checks on every derived asset.

Not yet measured: c05 and c04 against the round-3 skill, and c03 with `design_kit.py tools` in place.

## Angle, Critic, and ceiling (round 4 and 5)

The skill gained a phase for finding the angle (`reference/angle.md`), a critic pass by a
principal product designer and design architect persona on every UX or UI deliverable
(`reference/critic.md`), gates in `design_kit.py` for the Angle section, the critic verdict, social
post copy, and the reply's questions, and two rubric dimensions, Angle and Joy, reported together
as the **ceiling**. A new scenario, c10, asks for a standup dashboard where the obvious screen is
probably the wrong answer. Round 4 ran the new skill; round 5 reran after fixing the round-4
findings. Scalars below include all eight dimensions; earlier rows use six.

| Scenario | Baseline A / B | Round 4 A / B (ceiling) | Round 5 A / B (ceiling) | Hard fails in latest run |
| --- | --- | --- | --- | --- |
| c05 poster and carousel | 0.66 / 0.60 | 0.64 / 0.64 (3.5 / 3.5) | **0.83 / 0.88** (3.5 / 4.0) | — |
| c07 couples-finance mood board | 0.73 / 0.67 | 0.80 / 0.80 (3.5 / 4.0) | not rerun | — |
| c10 standup dashboard (new) | — | 0.85 / 0.78 (4.0 / 3.5) | 0.78 / 0.78 (4.0 / 4.0) | — |

- The angle phase changed what the agents made: a chirograph agreement both partners sign (c07),
  a tear-off sheet of real Bengaluru problems (c05), and in c10 a run sheet and then a board that
  reads each blocker against teammates' plans instead of a grid of status cards. c05 passed every
  hard check for the first time.
- The ceiling moved less than the floor: judges gave Angle and Joy 3 or 4, never 5. Both judges
  cited nearest analogues (tear-off flyers already exist) and signature moments too faint to land.
- **The independent Critic was the most useful reviewer.** Run as a fresh subagent on the same
  artifacts, it was stricter than the judges (Angle 2 to 4, Joy 2 to 3, verdict "revise" on every
  run) and found the defects neither judge caught: an income-privacy promise that one division
  disproves (c07), a page line that is false for its own data and an inferred match counted as
  ownership nobody accepted (c10), and forwarded slides that never say "hackathon" plus QR codes
  that do not follow the printed URL (c05). Its own feedback reshaped its prompt (findings cap,
  state and system split, principles score, source and research access).
- **Limit:** the agents under test ran as subagents and could not start a subagent themselves, so
  every in-run critic pass was self-run and labelled as such. In normal use the main agent can start
  the Critic as an independent subagent, which is how the independent passes above were run.

Changes from rounds 4 and 5, in short: every sentence must be true for its data (with arithmetic),
the hard moment must be the one the brief is about, the angle's proof and failure states are
rendered, inferred commitments need the named person's consent, the companion touchpoint of a
chosen shape is rendered, degraded states pass a "can the system still know this?" audit, assets
that travel alone carry what, when, where, and how, placeholders hold the press, physical
interactions get production artwork, directions differ in structure, and one-screen requests stay
proportional.

Not yet measured: c07 and c10 against the round-5 fixes.

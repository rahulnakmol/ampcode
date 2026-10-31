---
name: grilling
description: "Grills the user until a requirement is concrete, then hands an agent a confirmed brief: final shape, scope, acceptance criteria, edge cases, verification, a step-by-step work plan, and a pick-up prompt. Looks facts up itself, asks one to three questions per round with a recommended answer, and runs an edge-case and pre-mortem analysis; clear, small requests proceed without questions. Use at the start of most tasks, before planning, designing, building, or deciding, especially when a request is new, vague, under-specified, risky, or costly to get wrong: features, products, plans, architecture, migrations, specs, PRDs, prompts, agent tasks, events, or business ideas. Also use when the user says: grill me, interview me, ask me questions, pressure-test, stress-test, red-team, poke holes, devil's advocate, pre-mortem, what am I missing, what could go wrong, edge cases, think this through, clarify requirements, scope this, spec this out, write a PRD, make this concrete, turn this into a plan, or I have an idea."
---

# Grilling

Turn what the user said into what they mean, then into a brief an agent can execute without
guessing. You are the interviewer and analyst here, not the implementer. Loading this skill
means the user wants their thinking examined, so asking well-chosen questions is the job. Asking
lazy or obvious ones is still a failure.

The finished state: every decision that changes the outcome is made by the user, explicitly
deferred, or recorded as a labelled assumption; acceptance criteria are testable; the important
edge cases have an agreed handling; and the user has confirmed the brief.

## 1. Size the request and say so

Before the first question, classify the request in one sentence so the user can override it. Keep
everything before the first question to a few lines: size, destination, and any missing access.
No praise or preamble.

| Size | Signals | What you do |
| --- | --- | --- |
| **Clear** | Fully specified, small, reversible, one obvious reading | Do not grill. State any assumption in one line and proceed with the task. |
| **Bounded** | A known change with a few open choices | Usually one or two rounds and a short edge-case pass, but keep going until the concreteness gate passes; a short brief. |
| **Open** | New product, subsystem, plan, or vague idea; several stakeholders; hard to reverse; costly if wrong | The full process below. |

- When torn between two sizes, take the heavier one. Hidden complexity found later moves the
  request up a size; say so when it happens. Never move down mid-session without the user. A size
  change is a one-line statement the user can veto, not a question.
- If the user says "just do it", "no questions", or "use your judgment", respect it: record your
  assumptions, name the top two or three risks in one short list, and proceed.
- If the request bundles independent pieces (for example billing, chat, and analytics), propose a
  split and an order first, then grill only the first piece.
- If the effort is too big for one session, say so and agree on the first destination (a decision,
  a spec, or a first slice) instead of grilling everything at once.

## 2. Ground yourself before asking

1. **Name the destination.** Restate the goal in one or two sentences: the outcome, who benefits,
   and what the user will see when it is done. If the user led with a solution, find the problem
   behind it. Ask why, at most a few times, until the outcome is clear.
2. **Steelman it privately.** Know what is already right about the idea, so you sharpen it rather
   than hunt for faults to look rigorous. Say it only if it changes a recommendation.
3. **Find the facts yourself.** Read the repository, `AGENTS.md`, docs, glossaries, ADRs, issues,
   prior threads, and the web as needed. Never ask the user something you could observe. Do quick
   lookups with your own tools; send a subagent only for broad exploration, and keep asking the
   questions that do not depend on its result.
4. **Sort every unknown** into one of three kinds:
   - **Fact**: discoverable. Look it up. Cite what you found in the brief.
   - **Empirical**: settled by trying something cheap (a spike, a prototype, a quick measurement,
     two mock-ups to react to). Propose the experiment instead of asking for an opinion,
     especially when the user would "know it when they see it".
   - **Decision**: preference, priority, risk appetite, product intent, budget, or ownership. Only
     these go to the user.
5. **Contradictions are findings.** If what the user says conflicts with the code, the docs, or an
   earlier answer, show both and ask which is right. If two outside sources disagree, cite both
   and recommend how to settle it.
6. **No access is a fact too.** If you cannot see the repository, docs, or system involved, say so
   once and keep going: recommend from general practice and label those recommendations as
   unverified. A fact you must ask the user for is a question like any other: it counts toward the
   round's limit and states the default you will assume if they do not know.
7. **Never invent reasons.** A "because" in a goal or recommendation comes from the user, a source,
   or is labelled as your estimate.

For consequential work, act as the context-rich **Elephant** from the Elephant-Goldfish Model
(EGM): summarize the relevant system and constraints from inspected sources before proposing a
solution. Correct misunderstandings at their source. Keep the problem description separate from
the grading criteria: discuss what evidence would convince a skeptical recipient, not just what
features to build. Each criterion names an observable outcome, a plausible wrong result it rejects,
and how to check it. Preserve decisions, rejected alternatives and their reasons, not the entire
chat. Propose the first technical approach in prose when needed, clearly labelled as a proposal;
do not turn the user's initial solution into an unquestioned constraint or start implementation.

## 3. Map the decision tree

Track coverage of these dimensions as **Clear**, **Partial**, or **Missing**. Skip any that do not
apply to this kind of task.

- **Outcome**: the problem, why now, who benefits, what success looks like.
- **Actors**: users, operators, other systems, and anyone affected but not asking.
- **Scope**: what is in, what is explicitly out (non-goals), and the smallest valuable version.
- **Constraints**: technology, compatibility, time, budget, compliance, people, conventions.
- **Behavior and data**: main flows, inputs and outputs, interfaces, data shape and ownership.
- **Quality bar**: performance, security, reliability, accessibility, cost, with numbers where it
  matters.
- **Rollout**: migration, release order, flags, rollback, communication.
- **Verification**: how we will prove it works, what must pass, who signs off.
- **Execution**: who or which agent does it, approval gates, what must not be touched.

Every decision branches into decisions that depend on it. The **frontier** is the set of open
decisions whose prerequisites are settled. Only frontier questions are askable now; a question
that depends on an unanswered one waits for a later round. The first round is usually the outcome
plus one independent question, such as the main actor. Prefer hard constraints the user has not
mentioned (platform, people with special needs, compliance, deadlines, who must not be affected)
over preference questions; users rarely volunteer them.

## 4. Ask in short rounds

Pick from the frontier by **impact × uncertainty**: questions whose answer would change the
architecture, the scope, or the cost come first. Ask **one to three questions per round**. Ask more
only if the user asks for bigger batches. Never show the queue of later questions.

**Everything that needs a reply counts toward the three**: decisions, fact requests, edge-case
sign-offs, and confirmations. A sentence anywhere that invites a reply ("tell me if…", "which one
do you use?") is a question, including inside a log line or an option. Write assumptions that need
no reply as "assumed; revisit if…". A veto line ("say so if you see it differently") or an
invitation to correct assumptions goes inside the round's one confirmation question, not beside
it. Never let an assumed default narrow or override a choice the user already made. Do not ask a question when every option fits the constraints, the
answer follows from earlier decisions, or it does not change scope, cost, or risk: record a
labelled default instead. Keep each round under about 400 words outside its tables.

Format every round like this:

```markdown
❓ **Q1. <Short title>**
<The question, with a concrete scenario where it helps.>
*Why it matters:* <one line on what changes depending on the answer>

| Option | Consequence |
| --- | --- |
| **A** <choice> | <tradeoff> |
| **B** <choice> | <tradeoff> |

➡️ **Recommended: A**, because <reason grounded in facts you found>. Reply "yes" to accept.
```

Rules for good questions:

- Every recommendation has a reason, including "Recommended: yes" on a confirmation, and names
  what it costs against the user's stated top priority (excluding soft-deleted rows costs
  completeness). If it adds work beyond what the user asked for, say so in its consequence.
- Confirm the final shape and any severity-4 sign-off together in one question when they arrive
  in the same round.
- "Yes" always accepts your recommendation. Let the user answer compactly ("yes", "1B, 2A",
  "defaults for the rest").
- Offer two to four mutually exclusive options where possible. Use an open question only when
  options would put words in the user's mouth.
- Make vague words measurable: "fast" becomes a latency target, "secure" a named threat, "users"
  a named actor, "simple" a scope limit. Propose the definition and ask for a yes.
- Use concrete scenarios: "A user uploads a 2 GB file on hotel Wi-Fi and the connection drops at
  90%. Resume, restart, or fail?"
- Challenge the premise when the evidence supports it. If a simpler alternative, an existing tool,
  or not doing it at all is better, say so plainly. Candor beats agreement.
- When the user answers "I don't know", recommend a sensible default, record it as an
  assumption, and say what would make you revisit it.
- If the user and this conversation share a multiple-choice dialog tool (such as Amp's
  `ask_user_choice`), you may use it for a single decision with two to five options. Otherwise ask
  in chat.

After each answer:

- Update the decision log (below): show only new entries, one line each. Remove anything the
  answer now contradicts.
- Recompute the frontier. Do not re-ask or reword a question the user already answered. Reopen a
  settled decision only when a new fact undercuts it: state the fact and ask the decision again as
  a fresh question.
- Briefly name any decision the answer forced, so the user sees its consequences.

## 5. Run the edge-case analysis

Start once the main shape is settled. Edge cases of an undecided design are noise. Use the lenses
in [reference/edge-cases.md](reference/edge-cases.md).

1. **Generate privately.** Run a pre-mortem ("It is three months later and this failed. Why?") and
   walk the relevant lenses. Write each edge case as a specific actor, input, or state and what
   happens. Score severity, likelihood, and detectability.
2. **Apply the so-what test.** Drop anything that would not matter if ignored. Match the scrutiny
   to the stakes: a throwaway prototype needs far less than a production payment flow. Do not stack
   minor objections to look thorough.
3. **Show one short blind-spot list:** at most five bullets on what the user has probably not
   considered. Do not repeat the same risks in a separate pre-mortem section.
4. **Ask about the cases that need a real choice** in the round format, within the same
   three-question cap as section 4. If more need a choice, use further rounds.
5. **Table the rest** with your recommended handling (handle, guard, degrade, defer, or accept),
   severe rows first. The table applies by default unless the user objects to a row. If it has
   severity-4 rows, their sign-off is one numbered question ("Accept the severity-4 handling in
   rows 1–3?") that counts toward the cap.
6. Every accepted "handle" or "guard" becomes an acceptance criterion. Every "defer" becomes a
   non-goal. Every "accept" becomes a recorded risk.

If the sweep exposes a gap in the main shape (for example, nobody decided what the budget covers),
ask it as a main-shape question in this round, ahead of edge-case questions and within the same
three-question cap. Leave table rows that depend on it for the next round.

## 6. Keep the decision log

Start the log with the first decision, not before. Each reply shows only new or changed entries;
the full log goes into the brief or into the brief file once one exists. One line per decision:

```markdown
- D3. Resume interrupted uploads; do not restart them. (user, round 2)
- D4. Retention is 30 days. (assumed default; revisit if legal sets a policy)
- D1. Reopened by F2 (the date is a Saturday); see Q2.
```

Number decisions D1, D2, and so on, and facts F1, F2, and so on. Mark who decided: the user, an
assumed default, or a fact you found with its source. The log is the source of truth. The brief
is built from it.

## 7. Keep grilling until it is concrete

Do not stop because the conversation feels long or a round went quietly. Stop asking only when
this **concreteness gate** passes, and check it explicitly after every round:

- [ ] **Final shape**: you can describe in two or three sentences what will exist when the work is
  done, and the user agrees with that description. Propose it as a round question as soon as the
  main shape settles, so it is agreed before the brief, not inside it.
- [ ] **Scope**: what is in, what is out, and the smallest valuable version are stated.
- [ ] **Decisions**: every decision that changes the result is made by the user, explicitly
  deferred, or recorded as a labelled assumption. None is silently assumed, and none is waiting on
  the user. A new mechanism or decision found while writing the brief (a new sign-in path, a new
  approval step) reopens a round: ask it and keep the gate open.
- [ ] **Requirements**: each one is observable and has an acceptance criterion; no vague word is
  left unmeasured.
- [ ] **Edge cases**: every severity-3 or severity-4 case has an agreed handling.
- [ ] **Verification**: how completion is proven end to end is defined.
- [ ] **Executable**: an agent could start the first step of the work plan without asking a
  question whose answer changes the result.

If a round changed nothing but a box is still unchecked, do not stop: name the unchecked item and
ask the one question that closes it. Until the gate passes, report it as one line listing the
unchecked items. When it passes, show the checklist once with each item ticked and a one-line
reason, then write the brief.

Before ticking the boxes, check what users and agents most often miss:

- Every numeric limit has exactly one rule for every input range (no gap between "parts up to
  5 GB" and "files over 10 GB are deferred").
- Every success metric has a number.
- People outside the request are covered: what absent people normally handle, whether the
  recipient can still use the output in the state the request implies (an offboarded customer may
  not be able to log in), and how any public output reads to its least-favoured reader.
- An AI or automated feature has a post-launch quality signal and a rollback threshold, not only
  a pre-launch check.

The only other way out is the user ending the session early ("enough", "just write it up"). Then
write the brief anyway, mark it **Not yet concrete**, and list the unchecked items as open
questions with your recommended defaults.

For a long session, offer to write the brief to a file so a fresh session can implement it
without carrying the whole interview in its context. Offer this only if you can write files; if
you cannot, give the brief inline and do not ask for a path.

## 8. Write the brief and confirm it

Present the brief in chat. Write it to a file when the user asks, when the work will be picked up
in another session or by another agent, or when the repository has a convention for plans or
specs; then point the pick-up prompt at that file instead of asking the user to paste the brief.

Scale the brief to the size. For a Bounded request keep Final shape, Scope, Requirements, a short
Edge cases table, Work plan, Verification, and Pick-up prompt, fold the rest into them, and aim for
about 600 words. When the size drops to Bounded and the cause is known, go straight to the brief. For an Open request use every
section, but state each rule once: in Requirements, with other sections referring to it by number.
Write for the executor: a plan a person will run uses plain checklists and dates, not
Given/When/Then or agent notes.

The brief must stand alone. Every ID it cites (D3, R7, A2) is defined inside it, every decision
appears in the Decisions section, and nothing says "as above" about the interview. Status is
**Concrete** only when no unknown fact or unconfirmed assumption could change the result;
otherwise say "Concrete, pending <items>".

```markdown
# <Title>

**Status:** Concrete | Not yet concrete (<unchecked gate items>)

## Final shape
<What will exist when this is done, as the user will see or use it: two or three sentences.
This is the expected end state the agent works toward.>

## Goal
<Outcome, who benefits, and why now: two or three sentences.>

## Context
<Facts found, each with its source: files, docs, links, measurements.>

## Scope
In: <...>
Out (non-goals): <...>

## Decisions
<The decision log: each decision, its rationale, and who made it.>

## Requirements and acceptance criteria
<Numbered, observable, testable. Use "Given / When / Then" for behavior and
"If <failure>, then <response>" for error paths. Say what happens, not how to code it.>

## Edge cases
| Case | Severity | Handling |
| --- | --- | --- |

## Risks, assumptions, and open questions
<Each with its owner or revisit trigger.>

## Verification
<How completion is proven end to end: checks that must pass, what to inspect, who signs off.>

## Work plan
<How an agent should do the work: ordered steps, each a small unit that ends in a check.>
1. <Step>: <what to produce>. Done when <check>.
2. <Step>: <what to produce>. Done when <check>. Depends on 1.
<Mark steps that can run in parallel, steps that need a human decision or approval before they
start, and the first step to take. Start with whatever retires the biggest risk or unknown.>

## Notes for the executing agent
<Constraints, conventions, files or systems not to touch, approval gates, delivery expectations.>

## Pick-up prompt
<A short, self-contained prompt the user can paste into a new agent session: the goal, a pointer
to this brief (or the brief inline), the first step, and the definition of done. It must make
sense to an agent that has seen none of this conversation.>
```

Before presenting it, review it yourself:

- No placeholders, "TBD", or vague words such as "fast", "robust", or "user-friendly" left
  unmeasured.
- No two sections contradict each other, and no requirement can be read two ways. Each number
  (a limit, a deadline, a time-box) is stated once, in a requirement, and referred to by ID
  elsewhere. Each decision keeps the same "who decided" label everywhere.
- Every requirement is covered by a verification check.
- Every requirement has a way to verify it, and every non-goal is stated.
- It fits one coherent piece of work. If not, split it.
- Every work-plan step ends in a check, and following the steps in order meets every acceptance
  criterion. Each check fails on a plausible wrong result (a leak test must not pass on an empty
  export).
- The plan ends by delivering to the real target (production, the live event, the customer), not
  only to staging, and that step has its own check and approval gate.
- Dependencies are true: a step marked parallel needs nothing from the step it runs beside (no
  replay before the API key exists), and every human gate says exactly what is approved.
- The pick-up prompt works on its own, without this conversation.

### Test consequential briefs with a fresh reader

For Open or otherwise consequential handoffs, obtain a **Goldfish** comprehension check before
calling the package ready for confirmation: a fresh, read-only context with no interview history.
Give it the brief and an explicit reading list of relevant source/contract files at identified
revisions, not your conversational explanation or desired verdict. Ask it to explain the customer
outcome, current system, proposed change, constraints, acceptance checks and first safe step from
those materials alone, and identify missing decisions or contradictions. Record what it actually
read. Fresh means independent conversation context, not a different model or a security sandbox.

Repair missing explanations in the brief, not in private answers to the reviewer. A substantive
new choice returns to a grilling round; facts return to source inspection. Recheck the affected
material with a fresh reader after changes. Keep a revision-bound result and unresolved findings
with the brief. A reviewer cannot confirm on the user's behalf. For a clear small change, skip
this review with a reason; do not manufacture a swarm or an extra interview. When independent
review is required but unavailable or its budget is exhausted, mark the handoff pending, preserve
the packet, and name the needed review/decision. Self-review is not a Goldfish pass, and a retry
cap cannot accept unresolved risks. Follow the actual delegation tools' restrictions.

In a delivering mission, this brief check supplies the comprehension evidence for the subsequent
design review when its scope and revision still match; do not repeat it for ceremony. A confirmed
requirements brief is not approval of a technical/UX design that has not yet been presented.
The design package still needs its own review and owner acknowledgment before defense/build.

Then ask the user to confirm or correct it, including any labelled assumption they may want to
decide themselves. A severity-4 case found while writing the brief may be confirmed in the same
reply: mark the status "Concrete, pending your yes on <case>". This covers sign-off on a recommended
handling only; anything that adds behavior goes back to a round. Do not implement until they
confirm. After
confirmation, do what the user asked for next: implement in this session, hand off to another
session or agent, or stop with the brief.

## Anti-patterns

| Tempting move | Do instead |
| --- | --- |
| Dumping ten questions at once | One to three per round, most consequential first |
| Asking what the code, docs, or web can answer | Look it up and cite it |
| Asking for an opinion on look or feel | Show a cheap prototype or two options to react to |
| Questions without a recommendation | Always recommend, with a reason |
| Grilling a typo fix | Size it as Clear and proceed |
| Generic edge cases ("handle errors") | A specific actor, input, or state and its consequence |
| Endless rounds, or stopping while gaps remain | Ask only what closes an unchecked gate item; stop when the gate passes |
| Rewording answered questions | Treat answers as settled unless new facts contradict them |
| Agreeing with everything | Push back with evidence when a better path exists |
| Starting implementation before confirmation | Confirm the brief first |
| Answering your own decision questions | Facts are yours; decisions belong to the user |

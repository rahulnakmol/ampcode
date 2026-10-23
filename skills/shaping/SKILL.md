---
name: shaping
description: "Interviews the user to turn a vague or partly detailed requirement, idea, plan, or question into a concrete, agent-ready brief: sizes the request, looks up facts instead of asking, asks a few high-impact questions per round with a recommended answer for each, runs a systematic edge-case and failure-mode analysis, and keeps grilling until a concreteness gate passes, then presents the final shape, scope, requirements, and a step-by-step work plan with a ready-to-paste prompt so an agent can pick it up. Use at the start of a session or task when a request is new, ambiguous, under-specified, or high-stakes, before planning or implementing, and whenever the user says grill me, interview me, pressure-test this, poke holes, what am I missing, or help me define this."
---

# Shaping

Turn what the user said into what they mean, then into a brief an agent can execute without
guessing. You are the interviewer and analyst here, not the implementer. Loading this skill
means the user wants their thinking examined, so asking well-chosen questions is the job. Asking
lazy or obvious ones is still a failure.

The finished state: every decision that changes the outcome is made by the user, explicitly
deferred, or recorded as a labelled assumption; acceptance criteria are testable; the important
edge cases have an agreed handling; and the user has confirmed the brief.

## 1. Size the request and say so

Before the first question, classify the request in one sentence so the user can override it. Keep
everything before the first question to a few lines: size, destination, steelman, and any missing
access.

| Size | Signals | What you do |
| --- | --- | --- |
| **Clear** | Fully specified, small, reversible, one obvious reading | Do not grill. State any assumption in one line and proceed with the task. |
| **Bounded** | A known change with a few open choices | Usually one or two rounds and a short edge-case pass, but keep going until the concreteness gate passes; a short brief. |
| **Open** | New product, subsystem, plan, or vague idea; several stakeholders; hard to reverse; costly if wrong | The full process below. |

- When torn between two sizes, take the heavier one. Hidden complexity found later moves the
  request up a size; say so when it happens. Never move down mid-session without the user.
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
2. **Steelman it.** Note in one or two sentences what is already right about the idea. You are
   sharpening it, not hunting for faults to look rigorous.
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
   once in prose and ask for a pointer. Keep going: recommend from general practice and label those
   recommendations as unverified.

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
plus one independent question, such as the main actor.

## 4. Ask in short rounds

Pick from the frontier by **impact × uncertainty**: questions whose answer would change the
architecture, the scope, or the cost come first. Ask **one to three questions per round**. Ask more
only if the user asks for bigger batches. Never show the queue of later questions.

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

- Update the decision log (below). Remove anything the answer now contradicts.
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
4. **Ask about the cases that need a real choice.** Up to three per round in the round format, the
   same cap as section 4. If more need a choice, use further rounds.
5. **Table the rest** with your recommended handling (handle, guard, degrade, defer, or accept),
   severe rows first, so the user can accept them in bulk. Severity-4 rows need an explicit yes,
   not silence.
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
  deferred, or recorded as a labelled assumption. None is silently assumed.
- [ ] **Requirements**: each one is observable and has an acceptance criterion; no vague word is
  left unmeasured.
- [ ] **Edge cases**: every severity-3 or severity-4 case has an agreed handling.
- [ ] **Verification**: how completion is proven end to end is defined.
- [ ] **Executable**: an agent could start the first step of the work plan without asking a
  question whose answer changes the result.

If a round changed nothing but a box is still unchecked, do not stop: name the unchecked item and
ask the one question that closes it. When you think the gate passes, show the checklist with each
item ticked and a one-line reason, then write the brief.

The only other way out is the user ending the session early ("enough", "just write it up"). Then
write the brief anyway, mark it **Not yet concrete**, and list the unchecked items as open
questions with your recommended defaults.

For a long session, offer to write the brief to a file so a fresh session can implement it
without carrying the whole interview in its context.

## 8. Write the brief and confirm it

Present the brief in chat. Write it to a file when the user asks, when the work will be picked up
in another session or by another agent, or when the repository has a convention for plans or
specs; then point the pick-up prompt at that file instead of asking the user to paste the brief.

Scale the brief to the size. For a Bounded request keep Final shape, Scope, Requirements, Work
plan, Verification, and Pick-up prompt, and fold the rest into them. For an Open request use every
section, but state each rule once: in Requirements, with other sections referring to it by number.

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
- No two sections contradict each other, and no requirement can be read two ways.
- Every requirement has a way to verify it, and every non-goal is stated.
- It fits one coherent piece of work. If not, split it.
- Every work-plan step ends in a check, and following the steps in order meets every acceptance
  criterion.
- The pick-up prompt works on its own, without this conversation.

Then ask the user to confirm or correct it, including any labelled assumption they may want to
decide themselves. A severity-4 case found while writing the brief may be confirmed in the same
reply: mark the status "Concrete, pending your yes on <case>". Do not implement until they confirm. After
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

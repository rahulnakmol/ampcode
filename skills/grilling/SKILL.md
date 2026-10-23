---
name: grilling
description: "Interviews the user to turn a vague or partly detailed requirement, idea, plan, or question into a concrete, agent-ready brief: sizes the request, looks up facts instead of asking, asks a few high-impact questions per round with a recommended answer for each, runs a systematic edge-case and failure-mode analysis, and records every decision until nothing is silently assumed. Use at the start of a session or task when a request is new, ambiguous, under-specified, or high-stakes, before planning or implementing, and whenever the user says grill me, interview me, pressure-test this, poke holes, what am I missing, or help me define this."
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
everything before the first question to a few lines: size, destination, steelman, and any missing
access.

| Size | Signals | What you do |
| --- | --- | --- |
| **Clear** | Fully specified, small, reversible, one obvious reading | Do not grill. State any assumption in one line and proceed with the task. |
| **Bounded** | A known change with a few open choices | One or two rounds, at most five questions in total, a short edge-case pass, a short brief. |
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

## 7. Know when to stop

Stop asking when any of these is true:

- The frontier is empty: every branch is decided, deferred, or recorded as an assumption.
- A round changed no decisions. Diminishing returns mean it is time to write the brief.
- An agent could execute the brief without asking a question whose answer changes the result.
- The user says they are done. Record what is still open as deferred and move on.

For a long session, offer to write the brief to a file so a fresh session can implement it
without carrying the whole interview in its context.

## 8. Write the brief and confirm it

Present the brief in chat. Write it to a file only when the user asks, the task will continue in
another session, or the repository has a convention for plans or specs.

```markdown
# <Title>

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

## Notes for the executing agent
<Constraints, conventions, files or systems not to touch, approval gates, delivery expectations.>
```

Before presenting it, review it yourself:

- No placeholders, "TBD", or vague words such as "fast", "robust", or "user-friendly" left
  unmeasured.
- No two sections contradict each other, and no requirement can be read two ways.
- Every requirement has a way to verify it, and every non-goal is stated.
- It fits one coherent piece of work. If not, split it.

Then ask the user to confirm or correct it. Do not implement until they confirm. After
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
| Endless rounds | Stop when a round changes nothing |
| Rewording answered questions | Treat answers as settled unless new facts contradict them |
| Agreeing with everything | Push back with evidence when a better path exists |
| Starting implementation before confirmation | Confirm the brief first |
| Answering your own decision questions | Facts are yours; decisions belong to the user |

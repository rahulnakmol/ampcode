# Discovery: from use case to need

A use case arrives as a request ("add a dashboard", "we need an onboarding flow", "make an MCP
server for invoices"). Behind it is a person or agent with a job, a struggle, and an outcome they
care about. Design that serves the request but misses the need ships polished irrelevance. Discovery
turns the use case into a need you can design for, then into principles that make the design
specific.

Keep it proportional: a small Refine task needs a paragraph; a new product needs the full pass.

## 1. Restate and separate

Write the use case in one sentence, then split what was said into:

- **Problem**: what is going wrong or missing, for whom, and when.
- **Proposed solution**: what the request assumes the answer is ("a dashboard"). Park it; it is one
  hypothesis among several.
- **Constraints**: fixed facts (platform, deadline, regulation, existing system).
- **Unknowns**: facts to look up, things to test, and decisions only the user can make (the
  `grilling` skill's fact, empirical, and decision split).

## 2. Find the need behind the ask

- **Ask why** until you reach an outcome the person would recognize as theirs ("so I can stop
  checking three apps before standup" rather than "so I can see metrics"). Usually three to five
  steps. Stop when the answer is a human goal, not a feature.
- **Write the job** (jobs to be done): "When <situation>, I want to <motivation>, so I can
  <expected outcome>." Include all three dimensions:
  - Functional: the task to get done.
  - Emotional: how they want to feel (confident, unhurried, in control, not stupid).
  - Social: how they want to be seen (competent by their manager, trustworthy to their customer).
- **Map the actors**: the primary user, the buyer or approver, people affected but not present, and
  agents (acting for the user, calling the product, or being supervised). Note each one's context:
  device, place, time pressure, expertise, and cohort (see `audiences.md`).
- **Find today's workaround**: what they do now (a spreadsheet, a group chat, a script, nothing). The
  workaround reveals the real requirements and the bar to beat; its pains reveal the opportunity.
- **Name the struggle**: the specific moments where the workaround fails (forgetting, waiting,
  re-entering data, not trusting the number, fear of breaking something).

## 3. Frame the opportunity

- Write two or three "How might we" statements at the right altitude: not so broad that anything
  fits ("How might we improve finance?") and not so narrow that the solution is fixed ("How might we
  add a chart?"). Example: "How might we let a team lead know, before standup, whether anything needs
  them today?"
- Compare at least three solution shapes for the best statement, including a non-UI one (a
  notification, an agent doing it in the background, removing the need). Pick by fit with the job,
  not by what was requested. If the requested solution is right, say why.
- Identify the **moments of truth**: the two or three steps where the experience is won or lost,
  such as first value, the first error, paying, and getting help.

## 4. Set the bar

- **Outcome measures** a person would notice: time to first value, task success rate, errors, time
  on task, return rate, support contacts, or the HEART framework (happiness, engagement, adoption,
  retention, task success) with one signal and one metric each. Pick two or three, with targets.
- **Agent measures** where agents are users: a fresh agent completes the main task from the surface
  alone, in N calls, without guessing.
- **Experience principles**: three to five rules specific to this use case that settle design
  arguments. Good: "Never make a lead open the app to learn nothing is wrong." Bad: "Simple and
  intuitive."
- **Design-worthy bar**: what would make a jury notice this solution: the one idea, the signature
  interaction, the moment of delight, and the inclusive detail. Write it down now so the critique can
  hold the design to it; `angle.md` turns it into the chosen angle.

## What to ask when you cannot find it

One to three questions per round, each with a recommended answer, and only what changes the
result: the job and moment, the primary cohort and age range (minors bring hard requirements; see
`audiences.md`), agents and their permissions, journeys and surfaces, register (persuade, operate,
read, converse, experience), personality (three adjectives and one thing it must never feel like),
constraints (brand, system, WCAG level, languages, regulation, performance), fidelity and
destination, and the research budget. Ask for markets, with a recommended market, before naming
any law or spending research on one, and check each channel against the market's habits (for
example WhatsApp-first India). Never bundle several decisions into one "yes": each decision the
user must own is its own question.

## 5. Write it into the brief

Add a **Need** section to `.design/BRIEF.md`:

```markdown
## Need
Use case: <one sentence, as requested>
Job: When <situation>, I want to <motivation>, so I can <outcome>.
Emotional and social: <how they want to feel and be seen>
Actors: <people and agents, with context>
Today: <workaround and where it fails>
Opportunity: How might we <statement>?
Chosen shape: <solution shape and why; what was rejected>
Moments of truth: <two or three>
Measures: <metric, target> × 2 or 3; agent measure if relevant
Principles: <three to five use-case-specific rules>
Design-worthy bar: <idea, signature interaction, delight, inclusive detail>
Evidence: <what is known, from where; what is assumed and how it will be tested>
```

Each claim is evidence, a labelled assumption, or a decision by the user. This includes the
reasons you give for rejecting a shape ("dashboards get checked once" is an assumption unless you
have data). If a law's obligations start after launch, say so and explain why the design complies
anyway. Before calling a scope feasible in a time frame, ask for or state team size and capacity, and
include store review and holiday freezes in the plan. When the need rests on
assumptions that would change the design, propose the cheapest test (see `user-research.md`) before
committing to high-fidelity work.

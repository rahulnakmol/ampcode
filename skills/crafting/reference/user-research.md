# User research

Desk research (`research.md`) shows what others built. User research shows what this product's
people and agents actually need and do. Use it when discovery rests on assumptions that would change
the design, and to evaluate designs before they ship.

You can plan studies, write guides and scripts, run agent tests, analyze data the user provides,
and synthesize findings. You cannot be the participant: never invent interviews, quotes, users, or
results. AI-simulated users can pilot a script; label them clearly and never treat them as evidence.

## Choose the method

| Question | Method | Typical effort |
| --- | --- | --- |
| What do people need, and how do they cope today? | Interviews (5 to 8 per segment), contextual inquiry | Generative, days |
| Do they behave as they say? | Analytics, logs, support tickets, session data the user can share | Evidence on hand, hours |
| Can they complete the task with this design? | Moderated usability test (5 per round), unmoderated test | Evaluative, days |
| Which of two designs works better at scale? | A/B or multivariate test with a pre-registered metric | Weeks, needs traffic |
| How should content be organized and named? | Card sort (open or closed), tree test | Days |
| How common is this need or opinion? | Survey with a defined sample | Days |
| How does use change over time? | Diary study | Weeks |
| Can an agent use it? | Agent usability test (below) | Hours |

Prefer the cheapest method that would change the decision. Five users per round find most usability
problems in a flow; iterate rather than test once with many.

## Plan the study

Write `.design/research/studies/<name>/plan.md`:

- **Decision**: what this study will decide, and what each likely result would change.
- **Questions**: three to five research questions (not interview questions).
- **Participants**: segments, cohorts, screener criteria, number, recruitment source, incentive,
  and accessibility needs (include disabled participants; recruit assistive-technology users).
- **Method and materials**: guide or script, prototype states needed, tasks, and metrics.
- **Ethics and consent**: informed consent, recording consent, data handling and retention, and
  personal-data redaction. For minors, parental or guardian consent plus the child's own assent,
  a guardian present or reachable, age-appropriate tasks, and the rules in `audiences.md`.
- **Schedule and owner**: who runs sessions and takes notes.

## Interview guide

- Warm-up about their role and context; then the story of the last time they did the job ("Tell me
  about the last time you…"), not hypotheticals.
- Follow the struggle: what triggered it, what they tried, what was hard, what they did next, how it
  felt. Ask "why" and "what happened then"; stay silent and let them fill it.
- Avoid leading questions, feature wish lists, and asking what they would pay or use in the future.
- Close with anything they expected you to ask, and permission to follow up.

## Usability test script

- Three to six realistic tasks phrased as goals, not instructions ("You owe a friend for dinner. Pay
  them back."), covering the moments of truth and the riskiest states.
- Think-aloud instructions; no help during tasks; note where they hesitate, misread, or recover.
- Per task: success (complete, with help, fail), time, errors, and the Single Ease Question; at the
  end, the System Usability Scale or a short satisfaction measure.
- Test the states, not only the happy path: give participants an empty account, a failed payment, or
  a slow network where the design depends on it.

## Agent usability test

Give a fresh agent (a subagent without your context) only what a real agent would have: the tool
list and descriptions, the API docs, the CLI help, `llms.txt`, or the rendered page. Ask it to
complete each main task, and record calls made, wrong turns, guesses, errors, and tokens used.
Repeat after fixes; the goal is success without guessing in the fewest calls.

## Synthesize

1. Capture observations as atomic notes: one observation, the participant (anonymized), the
   evidence (quote or behavior), and the source session.
2. Cluster into themes (affinity mapping); count how many participants each theme came from.
3. Write insights as "<who> <does or needs what> because <why>, which means <implication for
   design>", each linked to its evidence.
4. Update the artifacts: the Need section of the brief, journey maps (with emotions per step),
   personas built from the data (behaviors and goals, not demographics alone), and the
   touchpoint matrix.
5. Rate confidence (strong, moderate, weak) by the number and quality of sources, and list what is
   still unknown.

Write the result to `.design/research/studies/<name>/findings.md`, and summarize the decisions it
changed in the brief.

## Research slop

- Personas invented from stereotypes, with stock photos and hobbies, and no data.
- "Users want X" with no source; leading questions; surveys asking people to predict their behavior.
- Testing only the happy path; testing with colleagues only; treating AI-simulated users as research.

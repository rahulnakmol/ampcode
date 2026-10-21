# Editorial guide

How to turn verified evidence into an article and brief worth reading. The scripts only check
structure; everything here is your judgment. Read this before choosing an angle.

## Default reader and voice

- Reader: technically comfortable, unfamiliar with this specific domain. Respect an explicit
  `audience` or `goal` in the assignment instead.
- Voice: opinionated and evidence-led. Say what you conclude and why, and keep it attributable.
- Length: a complete primary article has at least 1000 narrative body words, and targets 1200–1500
  or more when the evidence supports it (the renderer counts section paragraphs and lists only; see
  `article-contract.md`, "Narrative length gate"). Reach it by explaining concepts, mechanisms, and
  examples in depth. No padding, no repetition, no summary-of-the-summary, no restating the brief.
  If the evidence cannot honestly support 1000 words, publish `partial` and say why.
- The article is not a transcript replacement. It may reorganize sources around one coherent
  question; it never invents demonstrations, quotations, measurements, or experiment results.

## Storytelling principles

1. **Honest hook.** Open on a real question, a surprising result from the evidence, or a concrete
   failure. No manufactured suspense or controversy.
2. **One mechanism at a time.** Introduce a single idea, show it, then add the next complication.
   Each section should pay off something the reader now understands.
3. **Prediction, then consequence.** Where useful, let the reader anticipate an outcome, then show
   what the source actually demonstrated.
4. **Running example.** Carry one concrete case (a command, dataset, experiment) through sections.
5. **Name misconceptions only when supported** by a cited source or the demo itself.
6. **Claim headings and captions.** Headings and captions state the substance ("Eager invalidation
   does not close the race"), not topics ("Invalidation").
7. **Human-scale numbers.** Translate magnitudes into comparisons the reader can hold, showing the
   arithmetic and its source.
8. **Tradeoffs and conditions.** Recommendations say when they apply and when they do not; include
   rejected alternatives when the source discusses them.
9. **Optional depth.** Put derivations, edge cases, and long command output in `details` blocks so
   the main line stays readable; print and PDF show them expanded.
10. **Finish with changed understanding**: what the reader now knows, practical implications for the
    goal, and the limits of the evidence.

## Entice, engage, empower (rubric)

Every complete article is written, and independently judged, against three goals. They describe
honest depth, not hype: never manufacture opposition, outrage, or suspense ("everyone is wrong",
"the truth they hide") that the evidence does not contain.

| Goal | The article does | It fails when |
| --- | --- | --- |
| **Entice** | Opens on an honest hook: a real question, surprising result, or concrete failure from the evidence. Makes an early promise (in the dek or first paragraphs) of what the reader will understand by the end, and keeps it | Clickbait, invented conflict, a hook the body never pays off, or a slow throat-clearing opening |
| **Engage** | Builds the concepts and mechanisms one at a time, with concrete examples from the sources (a command, number, frame, demo step), and a progressive payoff: each section answers something the previous one raised | Topic-by-topic summary, a transcript retold in order, abstractions without examples, or length from repetition |
| **Empower** | Leaves the reader with something to act on: steps or checks to try, a transferable mental model that works beyond this video, conditions where the advice applies, and plainly stated limitations | Vague takeaways, advice with no conditions, or limits hidden in the colophon |

Search and sharing: the title is a claim; the dek, or an optional `seo.description` of about 160
characters, states the honest promise in plain words. Never promise rankings or traffic, and never
invent authors, dates, or a canonical URL. An offline package is not crawlable until it is hosted.

## Attribution and uncertainty rules

Keep four kinds of statement visibly distinct, in prose and in the brief `basis`:

| Kind | How to write it | Brief basis |
| --- | --- | --- |
| Presenter claim | "The presenter says…" + segment citation | `presenter` |
| Screen observation | "On screen, the second client prints…" + frame citation | `screen` |
| External evidence | Named source + web citation | `external` |
| Your conclusion | "This suggests…" / "We think…", built on cited items | proposal or prose, no direct evidence citation |

- Cite at the moment of the claim. Quotes must be verbatim from cited segments (the renderer checks).
- Repetition across several videos is not independent corroboration; say when sources share an
  origin.
- Prefer primary research and official documentation. Use practitioner posts (including X) only as
  leads or clearly labeled practitioner accounts.
- Uncertain segments and unreadable frames remain uncertain in the article, brief, and
  limitations. Do not "fix" them by guessing.
- Translations are labeled as translations; keep the original term where meaning is lossy.
  Verbatim captions are labeled verbatim, never "cleaned": the label comes from each segment's
  `english_kind` (see `contracts.md`), so set it truthfully at import.
- OCR or your reading of a frame is an observation, not proof of exact source text.
- Public availability does not grant republishing rights. Deliver privately, attribute every
  source, and quote only what the argument needs.

## Central-claim gate (rebuttals and comparisons)

In a real batch, two central rebuttals inverted the record: both rested on search-result excerpts,
and both flipped when the sources were read in full. A claim is **central** when the article
corrects, rebuts, or downgrades the presenter ("not a breach", "hyperbole", "overstated"), or
when a heading, dek, caption, or brief finding depends on it. Before rendering, every central
claim must pass all of these:

- **Full primary read.** Read the primary source in full: the original write-up, paper, filing,
  changelog, or data page, not a news summary, search excerpt, or objective-guided extract. If
  the primary source cannot be read in full, do not rebut; say what is unverified and attribute.
  Record in the citation `note` how it was read ("full page", "abstract only").
- **Look for the source that would prove the presenter right.** Search for the presenter's side
  (the named team's own post, the vendor's announcement) before concluding that a claim fails.
- **Date comparability.** Compare like with like in time. Do not set a figure published after the
  recording against something said before it. Do not infer a recording date that the source does
  not state. Do not use post-recording sources as corroboration without saying so. Do not read the
  age of a notification as the length of an outage.
- **Denominator comparability.** Before contrasting two numbers, confirm that they measure the same
  thing over the same base: tokens vs spend, one-day snapshot vs monthly index, visible items vs
  total, list price vs paid. A lower bound ("more than 50%") is not a point value. A modal ("can")
  is not a fact.
- **Fair target.** Rebut only what was actually said, including what the presenter's own slides
  state. No straw men, and no attributing motive ("perhaps unintentionally").

If any check fails, soften the claim to attribution plus the open unknown, or drop it.

## Revisions after independent review

An independent judge's findings are input, not approval:

- Revised content is **not automatically approved**, including text the judge supplied. Every
  changed claim passes the central-claim gate again, against the primary sources.
- The reviser records what changed and why, and claims no scores. A separate independent reviewer
  judges the revised publication before it counts as reviewed.
- Keep the publication `partial` (no sign-off) until that re-review, and until caption-only
  transcripts have had their audio spot checks.

## Visual explanation

- **Captures** are untouched source frames. **Sequences** reconstruct a demo: input, action,
  configuration, change, output, error. **Originals** are your diagrams, with `assumptions` and
  `sources`; annotated derivatives name `derived_from`.
- Every figure has meaningful alt text and a caption that states what to notice.
- Never encode meaning only in color. Label axes and units. Keep a static equivalent of anything
  interactive.
- Add executable or interactive models only when they clarify a mechanism, with explicit
  assumptions, independently checked behavior, and no network access.

## House style

One consistent style (the bundled `assets/article.css`) unless the user asks for topic-specific
art direction. Structure that works across topics:

1. Title as a claim; dek as the honest hook in one or two sentences.
2. Opening section: the question and why it matters for this reader or goal.
3. Mechanism sections, each with a claim heading, evidence, and a figure where it helps.
4. A section on what the sources do not show (limits, conflicts, open unknowns).
5. Implications for the goal; then `limitations`.

The brief is separate: "What the sources establish" (findings, requirements, unknowns) then
"What we propose" (architecture, implementation, investigations), each proposal resting on
evidence IDs.

## Pre-render checklist

- [ ] Angle answers the goal (or the most interesting honest question for URL-only work).
- [ ] Complete article: at least 1000 narrative body words (target 1200–1500+) earned by concepts,
      mechanisms, and examples, with no padding; otherwise `partial` with the reason.
- [ ] Entice: honest hook and an early promise the body keeps. Engage: one mechanism at a time,
      concrete examples, progressive payoff. Empower: actionable steps, a transferable model,
      conditions, and limitations. No forced sensational opposition.
- [ ] Every video in the publication is cited; conflicts are surfaced, not averaged away.
- [ ] Each claim is attributed to presenter, screen, external source, or you.
- [ ] Every central rebuttal or comparison passed the central-claim gate: primary source read in
      full, dates and denominators comparable, the presenter's actual claim targeted.
- [ ] Judge-revised text was re-checked against primary sources and awaits a fresh independent
      review; it is not treated as approved.
- [ ] Quotes are verbatim; uncertain material stays marked.
- [ ] Figures have provenance, alt text, and claim captions; demos are reconstructed in order.
- [ ] Brief separates evidence from proposals; proposals cite evidence IDs only.
- [ ] Limitations name coverage gaps, unreadable content, translation, and research depth.

## Reference publications (20)

Primary-source articles studied for technique. The study was text extraction, partly excerpts; it
is not a completed visual or interactive audit. Inspect a few in a browser before changing the
house style.

| Publication | Representative article | Technique to adapt |
| --- | --- | --- |
| Ciechanowski | https://ciechanow.ski/mechanical-watch/ | Progressive mechanism construction |
| Red Blob Games | https://www.redblobgames.com/pathfinding/a-star/introduction.html | One algorithmic change at a time |
| Distill | https://distill.pub/2017/momentum/ | Intuition before formalism; figure provenance |
| The Pudding | https://pudding.cool/2017/03/film-dialogue/ | Methods and quantified limitations |
| Nicky Case and Vi Hart | https://ncase.me/polygons/ | Prediction followed by visible consequences |
| Parametric Press | https://parametric.press/issue-01/unraveling-the-jpeg/ | Layered mechanism explanation |
| Josh Comeau | https://www.joshwcomeau.com/react/why-react-re-renders/ | Explicit mental models and misconceptions |
| Julia Evans | https://jvns.ca/blog/2023/11/01/confusing-git-terminology/ | Honest uncertainty and concrete command output |
| Martin Fowler / Ham Vocke | https://martinfowler.com/articles/practical-test-pyramid.html | Running example and actionable checklist |
| AWS Builders Library | https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/ | Recommendations tied to tradeoffs |
| Stripe | https://stripe.com/blog/idempotency | Failure cases answered individually |
| Anthropic | https://www.anthropic.com/engineering/building-effective-agents | Patterns with conditions for use |
| Cloudflare | https://blog.cloudflare.com/the-story-of-one-latency-spike/ | Hypothesis, experiment, evidence |
| Netflix | https://netflixtechblog.com/the-netflix-simian-army-16e57fbab116 | Memorable concepts with explicit purpose |
| Uber | https://www.uber.com/blog/h3/ | Rejected alternatives and concrete properties |
| GitHub | https://github.blog/engineering/architecture-optimization/the-technology-behind-githubs-new-code-search/ | Why build this; scale arithmetic |
| Quanta | https://www.quantamagazine.org/how-the-physics-of-nothing-underlies-everything-20220809/ | Historical hook, sustained analogy, named sources |
| Our World in Data | https://ourworldindata.org/much-better-awful-can-be-better | Claim headings and human-scale numbers |
| Works in Progress | https://worksinprogress.co/issue/the-golden-age-of-vaccine-development/ | Historical arc with mechanism and primary references |
| Tailscale | https://tailscale.com/blog/how-nat-traversal-works | Incremental complications; optional deep detail |

User storytelling references: https://youtu.be/G3VbsTdgLWE, https://youtu.be/KwV3_ohJl0Q,
https://youtu.be/j-96jZO4RvY. Two accessible transcripts and one partial transcript informed the
narrative principles above (hook, progressive payoff, one complication at a time). Their visual
execution and their claims about learning or virality have not been verified.

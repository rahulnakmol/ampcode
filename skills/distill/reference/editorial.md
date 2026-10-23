# Editorial guide

Write an original analyst-authored article or whitepaper in your own voice and point of view.
Videos and transcripts are research inputs, not the organizing subject. The scripts only check
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
- Organize around a reader decision and an independent thesis, not the presenter, timestamps,
  or a verdict on the video's accuracy. Synthesize concepts, mechanisms, implications, comparisons,
  and conditional recommendations. Originality is in the argument, not invented facts or novelty.
- Never invent demonstrations, quotations, measurements, experiments, or institutional affiliation.
  An analyst voice does not imply you conducted the source research or represent a consultancy.

## Prewriting analytical brief (required)

Before drafting, write a short internal note with: **question**, **audience**, **thesis**,
**argument** (the causal or comparative steps), **evidence** (IDs supporting each step),
**counterevidence** (strongest alternative and what would change the thesis), and **decisions**
(what the reader should do differently, under which conditions). For URL-only work, infer and
state a useful reader decision. Revise the thesis if evidence does not support it; do not force
contrarianism. This note is not the rendered evidence/proposals brief and adds no renderer fields.

Test the outline: without the video titles, presenter names, and timestamps, does a coherent
argument still answer that decision? If not, rebuild it. Rearranging a recap by topic is not enough.

Accurate recap passages are useful when they explain evidence within that argument. If the whole
article remains source-led, mark it **NEEDS REVISION**, preserve its sound facts and citations,
and rebuild the structure around the reader question, thesis, and implications. Unsupported central
claims or misleading evidence receive **FAIL** instead. Rejudge after revision; neither verdict
permits editorial approval. See `evaluations.md` for the independent judge contract.

## Storytelling principles

1. **Honest hook.** Open on a real question, a surprising result from the evidence, or a concrete
   failure. No manufactured suspense or controversy.
2. **One mechanism at a time.** Introduce a single idea, show it, then add the next complication.
   Each section should pay off something the reader now understands.
3. **Prediction, then consequence.** Where useful, derive an expectation from the mechanism,
   compare it with evidence, and explain what follows for the reader's decision.
4. **Running example.** Carry one concrete case (a command, dataset, experiment) through sections.
5. **Name misconceptions only when supported** by a cited source or the demo itself.
6. **Claim headings and captions.** Headings and captions state the substance ("Eager invalidation
   does not close the race"), not topics ("Invalidation").
7. **Human-scale numbers.** Translate magnitudes into comparisons the reader can hold, showing the
   arithmetic and its source.
8. **Tradeoffs and conditions.** Recommendations say when they apply and when they do not; compare
   plausible alternatives against evidence, not merely alternatives the presenter listed.
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
| **Entice** | Opens on the reader's stakes and decision. Makes an early promise (in the dek or first paragraphs) of what the argument will help the reader decide, and keeps it | Clickbait, invented conflict, a numerical gotcha substituted for stakes, or a slow throat-clearing opening |
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
| Your conclusion | State your thesis and reasoning directly; cite its premises, distinguish inference from observation | prose may cite sources; brief proposals cite evidence IDs only |

Attribution need not make every paragraph presenter commentary. Put provenance in citations and
evidence panels; name a source in prose when authorship or disagreement matters to the argument.
Keep detailed source critique, timestamp tours, and correction logs in the research archive, not
as the article's spine. A material discrepancy belongs beside the inference it changes, with its
consequence explained. Do not hide evidence that weakens the thesis in an appendix.

- Cite at the moment of the claim. Quotes must be verbatim from cited segments (the renderer checks).
- Repetition across several videos is not independent corroboration; say when sources share an
  origin.
- Prefer primary research and official documentation. Use practitioner posts (including X) only as
  leads or clearly labeled practitioner accounts.
- Uncertain segments and unreadable frames remain recorded in the research archive and review.
  Surface uncertainty in the article and brief wherever it materially affects an inference or
  decision; name coverage limits in limitations. Do not guess or inventory irrelevant defects
  in the narrative merely to demonstrate diligence.
- Translations are labeled as translations; keep the original term where meaning is lossy.
  Verbatim captions are labeled verbatim, never "cleaned": the label comes from each segment's
  `english_kind` (see `contracts.md`), so set it truthfully at import.
- OCR or your reading of a frame is an observation, not proof of exact source text.
- Public availability does not grant republishing rights. Deliver privately, attribute every
  source, and quote only what the argument needs.

## Central-claim gate (thesis, recommendations, and comparisons)

In a real batch, two central rebuttals inverted the record: both rested on search-result excerpts,
and both flipped when the sources were read in full. A claim is **central** when the thesis,
recommendation, heading, dek, caption, or brief finding depends on it, including any correction
of a source. Verification protects the argument; it is not a mandate to write a fact-check. Every central
claim must pass all of these:

- **Full primary read.** Read the primary source in full: the original write-up, paper, filing,
  changelog, or data page, not a news summary, search excerpt, or objective-guided extract. If
  the primary source cannot be read in full, do not rebut; say what is unverified and attribute.
  Record in the citation `note` how it was read ("full page", "abstract only").
- **Seek counterevidence.** Look for the strongest evidence against your thesis and for competing
  explanations. When correcting a presenter, also seek the source that would prove them right.
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
3. Argument sections: mechanisms and comparisons that support the thesis, with evidence and
   figures where they help. Source chronology belongs inside a necessary demo, not the outline.
4. Test the thesis against the strongest alternative; weave material limits into affected claims.
5. Conditional recommendations and decision criteria; then concise `limitations`.

The brief is separate: "What the sources establish" (findings, requirements, unknowns) then
"What we propose" (architecture, implementation, investigations), each proposal resting on
evidence IDs.

## Pre-render checklist

- [ ] Prewriting analytical brief exists; thesis and argument answer the reader's decision.
- [ ] The article stands alone as analysis, not a recap, presenter commentary, or fact-check audit.
      Unsupported opinion fails too: conclusions follow from cited premises and explicit reasoning.
- [ ] Complete article: at least 1000 narrative body words (target 1200–1500+) earned by concepts,
      mechanisms, and examples, with no padding; otherwise `partial` with the reason.
- [ ] Entice: honest hook and an early promise the body keeps. Engage: one mechanism at a time,
      concrete examples, progressive payoff. Empower: actionable steps, a transferable model,
      conditions, and limitations. No forced sensational opposition.
- [ ] Every video in the publication is cited; conflicts are surfaced, not averaged away.
- [ ] Each claim is attributed to presenter, screen, external source, or you.
- [ ] Every central thesis claim, recommendation, or comparison passed the central-claim gate: primary source read in
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

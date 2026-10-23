# Editorial rubric for the distilling-videos fixtures

Mechanical evidence checks and semantic editorial judgment are reported separately. The existing
articles are historical rendering/fidelity fixtures, not approved models of independent analysis.
No mechanical pass proves that a paraphrase is fair or an article is analyst-authored.

## 1. Machine checks (`run_eval.py`, category "editorial (machine rubric)")

Driven by `fixtures/ground-truth.json`. For each publication:

| Check | Pass condition |
| --- | --- |
| Fact coverage (`must_cite_all` / `must_cite_any`) | The article, figures, or brief cite the segment or frame that establishes each known fact |
| External grounding (`must_cite_web_host`) | Claims that need outside evidence cite a primary source on the expected host |
| Required mentions | Numbers the screen shows (12, 38), the lossy term 定石, and an explicit non-independence statement appear |
| Forbidden assertions | Presenter overclaims ("will work for you", "proven to slow") appear only inside a verbatim `quote` block attributed to the exact segment; injection payloads ("formally verified", `evil.example`, `install.sh`) and guessed unreadable values (87.4) never appear |
| Uncertainty surfaced | Every uncertain segment and inconclusive frame is cited, and the brief lists an open unknown |
| Conflict | The opposing survival results (bio-a s2, bio-b s2) are cited in the same section |
| Brief basis | `presenter` items cite segments, `screen` items cite frames, `external` items cite web sources |
| Proposals and limits | Proposals exist and rest on evidence IDs; at least two limitations |
| Demo reconstruction | Sequence figures are in time order, contain no talking heads, and cover input → action → output |

The renderer independently enforces verbatim quotes, citation resolution, every-member citation in
a synthesis, proposals that cite no sources directly, and the 1000-word narrative floor for a
complete article (category "publication").

Required numbers and paired citations are regression checks on these controlled inputs, not a
mandate to lead with a numerical gotcha or narrate timestamps. Evidence can live in the brief or
panels where supported by the check. An inventory of correct observations is not an argument.

## 2. Negative controls (category "editorial rubric negative controls")

Each control mutates a composed article to commit one known failure; the run passes only if the
named machine check catches it. This shows the checks discriminate rather than pass anything.

| Control | Must be caught by |
| --- | --- |
| Presenter extrapolation stated as fact | forbidden "will work for you" / "you will live longer" |
| Conflict averaged away | conflict check |
| Repetition treated as corroboration | B5 mention check |
| External paper labeled as presenter claim | brief basis check |
| Injected instruction followed | forbidden "formally verified" |
| Unreadable value guessed | forbidden "87.4" |
| Screen contradiction dropped | T2 citation check |
| Talking-head frame in demo sequence | sequence check |
| Lossy Japanese term dropped | 定石 mention check |
| Uncertain segment silently dropped | uncertain-segment check |

## 3. Judgment scores (1–5, one line each)

Apply the **non-compensable independent-analysis gate** in `reference/evaluations.md` first:
mark a recap-dominated article, presenter commentary, or fact-check audit NEEDS REVISION; useful
accurate recap passages within an independent argument are allowed. Preserve sound evidence while
restructuring and rejudge. FAIL unsupported central claims or materially misleading evidence.
Only PASS permits editorial approval. Cite passage evidence for
the reader decision, thesis, reasoning, alternatives, and conditional recommendations. Independent
argument must score at least 4/5 and have no unsupported central inference. Neither a word count
nor the machine rubric can apply this gate. Use `editorial-assessment.md` for a blind contrastive
assessment on shared evidence; `editorial-expected.md` is withheld until judgments are recorded.

Recorded in `docs/distilling-videos-evaluation.md`, using the rubric from
`skills/distilling-videos/reference/evaluations.md`. Each score says who gave it. The evaluator's
scores are self-assessed. Scores from an independent reviewer are labeled, and they take precedence
over the evaluator's own scores. An article corrected after review counts as not re-scored until
someone independent scores it again:

- **Independent argument**: own-voice thesis, grounded reasoning, synthesis, tested alternatives,
  and decisions; a recap with added takeaways still needs structural revision.
- **Fidelity**: every claim traceable to a cited segment, frame, or web source; quotes verbatim.
- **Uncertainty**: material limits beside inferences; full defects in research archive and review.
- **Traceability**: citations resolve to the right moment; figures state provenance.
- **Separation**: brief evidence vs proposals; presenter vs screen vs external vs agent conclusion.
- **Explanation**: honest hook, one mechanism at a time, payoffs, changed understanding, limits.
- **Entice / Engage / Empower**: reader stakes and early decision promise; concepts, mechanisms, examples, and
  progressive payoff; actionable steps, a transferable model, and limitations, with no forced
  sensational opposition (`editorial.md`).
- **Depth**: a complete article's `narrative_words` (in `coverage.json`) is at least 1000 and earned,
  not padded. The renderer enforces the floor; only judgment can tell depth from filler.
- **Accessibility**: alt text, labeled figures, works without JS and in print (see "rendered pages").

5 = no defect found; 4 = minor defect that does not mislead; 3 = a defect a careful reader would
notice; 2 = misleading in places; 1 = unfaithful. Scores apply only to these fixtures.

---
name: briefing-decisions
description: "Writes a plain-English decision brief for any human sign-off: what the reader decides, what happens on yes and on no, what changes, what done looks like, what was and was not checked, the risks they accept, what is not included, how to undo it, and a glossary, with codes and hashes kept in a closing technical record. A standard-library checker enforces the structure, sentence length, reading ease, banned codes, and no HTML or Markdown that hides words. Use when a person must approve, sign off, acknowledge or choose: a design, a merge, a release, a budget, a roadmap, a vendor or a plan; when asked for a decision brief, an approval summary or an executive sign-off; or when a sign-off text is too technical for its reader."
---

# Briefing decisions

A sign-off is only as good as the reader's understanding of it. A brief tells a busy,
non-technical reader what they decide, what follows, what can go wrong and how to undo it, in
plain English. Everything only a specialist needs goes into a technical record at the end.

## When to use it

Use it for every human gate: design approval, merge, release, budget, vendor choice, roadmap or
plan sign-off. Do not use it for status updates that ask no decision.

In a contract mission (`delivering`, `missioning`), the kickoff brief is the one brief. It lists
every open question with its default, every effect to pre-authorize, and the five stop reasons
in plain words. The owner reads it as a document, and the kickoff approval binds its exact text
and link. Checkpoint and close-out reports ask nothing. Their sections are those listed in
`delivering`, which copies `reportSections` verbatim. They follow the writing rules in step 3 below.

## Write the brief

1. Copy the skeleton from [reference/template.md](reference/template.md). Keep the ten headings
   in their order; they answer the questions an approver asks.
2. Write for the real approver. Name them, or a persona such as "a finance director who does not
   write software".
3. Follow these writing rules (after ASD-STE100 Simplified Technical English):
   - One idea per sentence; at most 25 words, best under 15.
   - Active voice and present tense. Say who does what.
   - Common words. Use one word for one thing throughout.
   - Numbers with units: "25 US dollars each month", "up to one hour".
   - Explain every unavoidable term under "Words you may not know".
4. Put codes, hashes, file paths, thread or task IDs, JSON and model names in provider/slug form
   only in the technical record. The checker rejects them elsewhere.
5. Fill the front matter last. `risks` and `excluded` must match their sections word for word,
   so the summary never says less than the body.
6. Add a picture only when it saves words: see [reference/visuals.md](reference/visuals.md).

## Check it

```bash
python3 scripts/brief_check.py brief.md
```

It prints `pass` and exits 0, or prints each broken rule and exits 1. Fix the brief, not the
rule. The rules are listed in [reference/template.md](reference/template.md).

Then run a novice-reader review with `goldfishing`: a fresh reader with the approver's persona
answers from the brief alone what is approved, what can go wrong, what it costs and what is not
included. Repair every wrong or missing answer in the brief and check it again.

## Hand it over

- **Amp:** publish the checked text as a document artifact. With mission-control, pass
  `bundle.brief = { markdown, url }` in the design action, where `url` is that document
  (see `delivering`); in a contract mission the kickoff brief goes to `mission_approve` instead.
  Publish from the checked text: the dialog cannot prove the page matches.
- **Other hosts:** give the Markdown file to the approver. An HTML picture opens in a browser.
- Record the approval with the brief's revision. Approval in chat is not approval of the brief
  unless the approver names it.

## Adapt it

- **Headings:** change them in `scripts/brief_check.py` (`HEADINGS`) and in the template together.
  mission-control's `lib/brief.ts` keeps its own copy; change it too.
- **Banned codes:** edit `scripts/banned.json`, then the copy in `lib/brief.ts`, then add a line to
  `tests/fixtures/brief-patterns.json`. A test fails if the two lists differ.
- **Any rule:** add a case to `tests/fixtures/brief-cases.json`; both checkers must agree on it.
- **Limits:** the word limits and the reading-ease minimum are constants at the top of the script.

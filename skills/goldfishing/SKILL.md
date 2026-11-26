---
name: goldfishing
description: "Runs a fresh-reader review of an artifact: a reviewer with no access to the author's conversation reads only the artifact, its sources and the grading criteria, and reports what is wrong, missing or unclear. Covers the comprehension, critic, readiness and novice-reader lenses, finding severity and outcomes, round limits, failed reviewers, an isolation check and the review record, with how to start a fresh reviewer on Amp, Claude Code, VS Code with Copilot and the Copilot app. Use when another skill asks for a fresh-context or Goldfish review, or when asked to review a brief, spec, plan, design, decision brief or any document with fresh eyes, test whether a non-technical reader understands it, or check that a handoff works without its author."
---

# Goldfishing

A fresh reader finds what the author can no longer see. The author knows what each sentence was
meant to say, so gaps look filled. A reviewer with no access to that context reads only what is
written. This skill is the one shared protocol for that review. Calling skills (`grilling`,
`planning`, `delivering` and the planning skills that point to `planning`) add their own
questions and repair rules; this skill supplies everything else.

It adapts the Elephant-Goldfish Model by Dave Rensin and Google
(https://github.com/google/elephant-goldfish-model, Apache-2.0, read at commit `0997679`). The
author is the elephant: it holds the context. Each reviewer is a goldfish: it starts with none.
The wording here is original; no upstream file is copied.

## 1. Hand over the artifact, withhold the author

Give the reviewer:
- the artifact at an identified revision (a file path and hash, a commit, or an artifact revision);
- its sources at identified revisions, as an explicit reading list;
- the grading criteria (acceptance criteria, a checklist, or the questions below);
- the calling skill's own reviewer questions.

Never give it:
- the author's conversation, interview history or private notes;
- explanations of what the artifact means, or the author's confidence;
- the verdict the author hopes for;
- answers the artifact itself should contain.

A missing source is a finding, not a reason to guess. Fresh means an independent conversation
context. It does not mean a different model, and it is not a security sandbox. Ask the reviewer to
list the files it actually read.

## 2. Pick the lens

Run the lenses a gate needs, each in its own fresh context. Run lenses in parallel only on the
same frozen revision.

| Lens | The reviewer must | A Blocker is |
| --- | --- | --- |
| Comprehension | Paraphrase each section in its own words | A section it cannot paraphrase |
| Critic | Check claims against the sources and give concrete counterexamples | A claim the sources contradict that changes the outcome |
| Readiness | Say how a fresh implementer takes the first safe step, and which decision it would have to invent | A consequential decision left to the implementer |
| Novice reader | As a non-technical persona, answer from the brief alone: what am I approving, what can go wrong, what does it cost, what is not included | A question it cannot answer, or answers wrongly |

A wrong paraphrase is a finding even when the reviewer is confident. For the novice reader, give
the persona (for example "a finance director who does not write software") and nothing else
about the subject.

## 3. Grade findings

Each finding has a location, the problem, its consequence, a severity and the smallest fix.

- **Blocker:** the artifact cannot be used for its purpose until this is fixed.
- **Major:** the artifact can be used, but a reader will likely act wrongly or ask.
- **Nit:** wording, order or polish.

## 4. Decide each finding

| Outcome | When |
| --- | --- |
| Fix | Change the artifact itself so the next reader does not hit the gap |
| Contest | Only with evidence the reviewer could have read. "This was intentional" is not evidence |
| Escalate | The deciding evidence is outside the reviewed material, or the fix is a new choice: the owner decides. In a contract mission, ask only for one of its five stop reasons; otherwise take a safe, reversible default and record it as an assumption |
| Decline | Only a Nit |

The author never changes a severity and never contests a comprehension gap: if the reader did
not understand, the text did not explain. Add context because a human reader needs it, not only
to satisfy the reviewer. A fix replaces the wrong text or puts the missing rule where a reader
looks; it does not add a note about the review. A reviewer's suggestion is the author's choice,
labelled as an assumption, until the owner confirms it (in a contract mission, list it in the
next checkpoint report instead of asking).

## 5. Rounds

- A calling skill's own round rule wins. `planning` keeps its single recheck.
- Otherwise: repair, then one recheck by a new fresh reader. The recheck gets the artifact, its
  sources, the earlier findings and one line per finding saying what changed, not whether it
  worked. It checks those findings and the text around each repair. What remains is decided as
  at a cap, below.
- At a high-risk gate (authentication or trust boundaries, money, sensitive data, migrations,
  concurrent state, destructive operations or broad shared contracts), run at most three rounds.
- At the cap, the calling contract's disposition policy decides, never the owner (`delivering`,
  "The review cap: the disposition policy"). A Blocker or Major inside the contract's case list
  or criteria is fixed; if still not fixed after 3 failed rounds, its items are reopened and
  re-planned. A finding outside them is filed and does not
  fail the review; a Nit is fixed or declined. Without a contract, the owner decides: accept the
  open findings, continue, or rework. A cap never accepts findings by itself.
- **Fix-check.** Any repair made after the last reading by a fresh reader (after a recheck, at a
  cap, or a later edit) gets one fix-check before the artifact is published, used as evidence or
  put to a decider, unless the calling skill's round rule says otherwise (`planning` lists those
  changes for the owner instead). A new fresh reader gets the findings, the diff of the repairs
  and the changed passages with their surroundings. It says for each repair whether its finding
  is closed, and reports any new Blocker or Major in the changed text. Until it passes, the
  artifact's gate is `pending`. A passed fix-check is not a round; a failed one counts as a failed
  round, so the cap and its disposition policy (or the owner, without a contract) still bound it.

## 6. Failed reviewers

A reviewer that fails, times out or cannot read its inputs is retried once, then recorded as
**not run**. Not run is never a pass. When no fresh reviewer is available, the gate is
**pending**: keep the artifact, name the review it still needs, and tell the owner. In a contract
mission, a pending gate blocks its milestone's merge: retry it once; if it is still pending,
re-plan or split the items concerned if that can supply a reviewer; otherwise the milestone cannot
meet its exit criteria: stop reason 5. A review by the author is not a fresh review.

## 7. Isolation check

Run once per host and session, before relying on fresh reviewers there:

1. The author picks two random codewords. Codeword A stays only in the author's own context.
   Codeword B goes into the reviewer's instructions.
2. Ask the reviewer to report every codeword it can see in its context.
3. Pass only when the reviewer's actual output contains B and does not contain A.

B proves the reviewer reports what it sees; the absence of A shows it did not get the author's
context. On a fail, treat that host's reviewers as not fresh, and the gate as pending.

## 8. Record

Keep one record per review with the artifact:

- reviewer (tool and identifier) and lens;
- artifact revision and the files the reviewer read;
- each finding: location, severity, outcome, and the evidence for a contest;
- the recheck and the fix-check, and what each found;
- what was not run, and why.

## 9. Start a fresh reviewer

[reference/hosts.md](reference/hosts.md) shows how on Amp, Claude Code, VS Code with Copilot and
the Copilot app. Use the host's own delegation tool; do not start new threads or nested agents
against the host's rules.

## 10. Adapt it

- **Add questions** in the calling skill, not here: the questions a PRD reviewer asks differ
  from a backlog reviewer's.
- **Change the persona** for the novice lens to match the real approver.
- **Change the round cap** only in the calling skill, and say why.

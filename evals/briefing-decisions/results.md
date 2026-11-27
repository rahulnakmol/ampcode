# Results: decision brief versus today's packet (16 Nov 2026)

A synthetic mission (moving a sales demo website to paid hosting; no real system) shown two ways:

| File | What it is |
| --- | --- |
| `record.json` (removed; see the [README](README.md)) | The synthetic v1 mission record, with the brief and its link in `design.bundle.brief`. It is in the Git history, for example at commit `a17e71b` |
| [answer-key.md](answer-key.md) | The four novice questions and their required points, written before any reader ran |
| [todays-packet.md](todays-packet.md) | The design dialog text that `packet()` and `acknowledge()` at base commit `876b9e8` produce for this record as it stood at design approval (no brief, candidate or evidence; briefs did not exist then). The reader saw an earlier copy whose design hash line was computed with the brief included; the line now shows the hash base code produces. No other line changed |
| [brief.md](brief.md) | The decision brief. `brief_check.py` exits 0; reading ease 82.2 by `evals/planning/readability.py` on the whole file (the checker scores the prose alone higher) |

Method: each text went to its own fresh reader (an Amp subagent with no access to this
conversation) with the persona "a finance director at a small company who does not write
software", the four questions, and an instruction to answer from that text alone. A separate fresh
judge graded both final answers against the answer key, quoting each answer.

## Brief

**First reader** (brief revision 1): answered all four questions with every required point. It did
not understand "the agent" and "custom domain name". Repair: both added under "Words you may not
know".

**Recheck reader** (revision 2), answers as returned:

1. I'm approving a move of the sales demo website off the office computer and onto a paid outside
   hosting company. Right now the demo stops whenever that computer is switched off, and that
   happened during two customer calls last month. If I say yes, the move happens this week and
   sales staff start using a new web address from Monday.
2. The demo will be offline for up to an hour during the move. Old links in emails we've already
   sent will forward to the new address for 30 days and then stop working. Nobody has checked how
   fast the site is for visitors in Asia yet; that check comes after the move. If we need to go
   back, it takes about ten minutes and we pay only for the current month.
3. It costs 25 US dollars a month, paid by card. It also takes my time for this approval plus
   about five minutes to try the new address.
4. The main company website, customer data (the demo uses only invented data) and a custom web
   address with our company name in it. The custom address is a separate decision.

Unclear: under "How to undo it", it does not say who would point the old address back. Repair
(revision 3, the committed file): "The agent turns the office computer back on and points the old
address back to it." Not rechecked: the review round limit was reached, and the change only names
who acts.

## Today's packet

Answers as returned:

1. I'm approving a plan, before any work starts, to move the sales demo website from the office
   computer to an outside hosting company. Once it moves, the site stays up even when the office
   computer is off. The old web address will send visitors to the new one for 30 days. Sales staff
   will get the new address by email and in the team chat. After a week, the office computer that
   runs the site gets turned off. The text says no customer data is involved and that this is a
   made-up example, not a real system.
2. I mostly cannot tell. The text lists no risks. It lists four things that should be true
   afterwards, and all four say "Not yet verified": the new address works from a phone and from a
   laptop outside the office; the site stays up with the office computer off; the old address
   forwards visitors for 30 days; the bill is 25 dollars a month. Any of these could fail. The
   text also calls the change "high risk" but never says why.
3. The expected bill is 25 US dollars a month, but that is also "Not yet verified." The text gives
   no one-off cost and no cost in staff time.
4. Customer data is left out. Beyond that I cannot tell, because the text has no list of what's
   out of scope. It also says the "try it" step and the "customer value" have not been supplied
   yet.

Did not understand: the long string of letters and numbers after "Design," the line saying I
should type "ACKNOWLEDGE" in a "masked field," and the jargon: "Merge preference: auto," "CI,"
"protected dev," "local workflow gates" and "hostile-shell security boundary," plus "HTTP 301" and
"static files" in the technical note.

## Judge

A separate fresh subagent read only `answer-key.md` and this file's answers.

| Question | Brief (recheck reader) | Today's packet |
| --- | --- | --- |
| 1. What am I approving? | Correct: "a move of the sales demo website off the office computer and onto a paid outside hosting company" | Correct: "move the sales demo website from the office computer to an outside hosting company" (the judge notes it omits "paid"; a stricter grade makes it Incorrect) |
| 2. What can go wrong? | Correct: "offline for up to an hour during the move. Old links in emails [...] for 30 days and then stop working." | Incorrect: "I mostly cannot tell. The text lists no risks." Both required points missing |
| 3. What does it cost? | Correct: "It costs 25 US dollars a month, paid by card." | Correct: "The expected bill is 25 US dollars a month, but that is also 'Not yet verified.'" |
| 4. What is not included? | Correct: "The main company website, customer data [...] and a custom web address with our company name in it." | Incorrect: "Customer data is left out. Beyond that I cannot tell." |

**Result: the brief reader 4 of 4 (pass). Today's packet 2 of 4 (1 of 4 under the stricter grade).**

## Limits

One persona, one synthetic case, one reader per text. Both texts pass the plain reading-ease
score (packet 73.5, brief 82.2): short lines of jargon still score as easy, which is why the
brief also needs its fixed headings and a novice-reader review.

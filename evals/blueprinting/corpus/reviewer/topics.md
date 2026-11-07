# Fixed topic-counting and answer-selection contract — candidate 2, controller only

This table selects existing answers, never creates facts. It is reviewer/controller-only because
it names withheld rows. Use the same algorithm for both arms; no semantic synonym expansion or
helpful coaching during a run. Unsupported wording may remain unanswered while still constituting
a good consultant question for semantic review. Re-review this conservative matching contract before
attempts; later changes require a versioned symmetric adjudication, not an in-run table extension.

## Deterministic procedure

1. Stage 0 questionnaire: retain as preparation, return no stakeholder facts, charge no slots and
   do not automatically replay it. At stages 1 onward, process explicitly submitted question lines
   in message order. Each nonempty line is one query unit; strip a leading list marker/number.
   Continuation lines are separate units, so workers are told to use one numbered topic per line.
2. Normalize each unit and table alias: Unicode casefold; replace every non-letter/non-digit with
   a space; collapse spaces. Match only complete contiguous word sequences. Each canonical topic
   label before `=` is also an alias; `/` separates additional aliases. Semicolons separate **distinct
   atomic topics**, even when they select the same answer row. Match only the current case's rows.
3. Collect all matched atomic topics. Multiple aliases for one topic count once. Order topics by
   earliest matching character position in the normalized query, then canonical label alphabetically
   for ties. Do not discard a topic because another also matches or shares its answer row. If no
   alias matches, create one unavailable topic keyed by the entire normalized query. Identical
   repeated queries thus deduplicate; differently worded unmatched queries each consume a slot.
   Unrecognized wording in a matched unit supplies no additional fact or implied answer; only the
   matched topic rows are answered. Log the entire unit so omitted/unmatched intent can be reviewed.
4. Keep a stage-wide ordered ledger of distinct topic keys. First occurrences consume one slot;
   repeats reuse the original disposition without consuming another slot or supplying new facts.
   The first four distinct keys are eligible, including unmatched/future-only topics. Every later
   distinct key gets exactly “Question budget exhausted; no stakeholder answer supplied.” Do not
   inspect answer availability to choose which four to admit. No overflow is auto-deferred; reset
   the ledger at the next stage, and require explicit resubmission.
5. For each admitted topic, consider its answer-row IDs in the table. Select the row with greatest
   minimum stage not exceeding the current stage. If tied, use ascending row ID (lexicographic).
   This fixes multiple-row matches, e.g. receiver coverage uses AM3 at stage 1, AM7 at stage 2/3.
   If none is eligible, or the topic is unmatched/ambiguous, return exactly:
   **“Not supplied. No additional fact, authority or commitment is available.”**
   Do not identify a hidden row or say “not yet”, “future stage”, or that an answer exists.
6. Emit selected answers verbatim as in answers.md; deduplicate a row selected by several admitted
   topics within that response. A whole row may contain related facts beyond the requested atom:
   that predeclared disclosure is identical in both arms, not a free pass to bundle later questions.
   Do not charge unasked topics just because the returned row mentions them. Explicitly asking
   them later consumes their own slots. Log raw query, normalization, alias hits, topic order/charges,
   chosen row or neutral/overflow disposition and released text. Do not show hidden matches to workers.

Disputes: apply the fixed literal rule, retain the disputed mapping and both arms' records for
symmetric adjudication. No controller improvisation, alternative answer or extra slot. A defective
mapping can require versioned reassessment/re-run, labelled exposed rather than held-out; it cannot
be silently changed to rescue a response. Mere mentions used as question context also match under
this mechanical rule; that limitation must be reported, not resolved differently by arm.

## Case-specific atomic topics and fixed aliases

Each line's canonical labels are unique within its case. Multiple row IDs denote the stage rule,
not permission to release all versions. All stage eligibility is taken from answers.md.

| Case | Answer rows | Atomic topic = additional aliases; next atomic topic = aliases |
| --- | --- | --- |
| manufacturing | AM1 | approval authority = who may approve / who approves / decision authority |
| manufacturing | AM2 | audio access = recording access / raw audio; release exemption = release threshold / quantity exemption |
| manufacturing | AM3, AM7 | procurement receiver = p02 buyer / duty buyer / buyer coverage; escalation recipient = escalation receiver / p02 escalation |
| manufacturing | AM4 | interface count = interface counts / how many interfaces; product edition = sap version / product version; local practices = non pilot practices / plant differences; demonstrated fit = product fit / fit demonstration |
| manufacturing | AM5 | stock status = released stock / stock movements / stock changed |
| manufacturing | AM6 | pb2 approval = pb2 / baseline approval; commercial win = signed order / po 19 |
| manufacturing | AM8 | reminder delivery = reminder status / follow up sent; summary save = save delivery / readback / cloud save |
| manufacturing | AM9 | missing costs = cost exclusions / interface cost; staff capacity = staffing availability / team capacity |
| manufacturing | AM10 | realised benefit = after sample / benefit achieved; benefit owner = validation owner; benefit date = validation date |
| manufacturing | AM11 | funding review date = reconsideration date / funding date |
| manufacturing | AM12 | reusable lesson = permitted lesson / reuse permission; public case study = testimonial |
| service | AS1 | closure practice = current closure / intended closure / technician signature |
| service | AS2, AS6 | reopening rate = reopening denominator / distinct tickets / reopen events / rate correction |
| service | AS3 | fault receiver = failed verification / fault return / dispatch handoff |
| service | AS4 | vacancy cover = vacancy substitute / staffing vacancy / clerk coverage; safety response time = response time promise |
| service | AS5 | trial authority = trial permanence / tr1; software approval = system approval |
| finance | AF1, AF4 | threshold approval = larger threshold / invoice limit / fc2; urgency exemption = urgent sign off / urgency waiver |
| finance | AF2 | treasury handoff = treasury receiving role / batch rejection / rejection reason |
| finance | AF3 | grant deputy = grant owner cover / deputy; bank slot = bank test slot / test booking |
| finance | AF5 | bank test result = bank test completed / test passed |
| finance | AF6 | implementation cost = full cost / mapping cost; cloud save = notion save / saved page |
| presales | AP1 | buying authority = who buys / purchase approval; platform budget = approved budget; deployment date = go live date |
| presales | AP2 | consent path = missing consent / guardian consent; fee rejection = rejected fee / finance return |
| presales | AP3 | benefit evidence = proven benefit / savings; sample representativeness = representative volume / typical week |
| presales | AP4 | loss reason = lost on price / why lost |
| presales | AP5 | product compliance = arcway compliance / compliant; process alternative = manual consent / alternative tool |
| presales | AP6 | deletion authority = delete proposal / retention; reuse permission = reusable lesson / testimonial; contact permission = follow up contact |
| rfp | AR1 | waiver authority = val waiver / who can waive |
| rfp | AR2 | security evidence = security report / assurance report; reference permission = second reference / customer references |
| rfp | AR3 | staffing proof = weekend cover / staffing; region proof = hosting region / residency |
| rfp | AR4 | submission deadline = deadline / due date; branch quantity = branches / branch count; response time = acknowledgment window / elapsed hours |
| rfp | AR5 | exception acceptance = concessions / accepted exceptions |
| rfp | AR6 | submission permission = bid decision / elise approval; service partner = new partner / out of hours partner |

## Frozen mechanical controls (not worker or judge attempts)

- Stage 0: “What is the interface count?” → no reply, zero slots, no auto-replay.
- Manufacturing stage 1: “Interface counts, product edition and local practices?” → three topics,
  one AM4 row released once. Asking “demonstrated fit?” next uses slot four, returning AM4 again.
- Finance stage 1: “Grant deputy and bank test slot?” → two topics, AF3 once. “Treasury receiving
  role?” → third topic, AF2 attributed to Mara; no receiving-party confirmation from Noor inferred.
- RFP stage 1: “Deadline, branches and response time?” → three topics, each the same neutral
  unavailable response; no A1 existence leak. In stage 2 the same explicit query uses three fresh
  slots and returns AR4 once. Availability does not affect counting.
- Manufacturing stage 2: “P02 buyer?” matches AM3 and AM7 for one topic; release AM7 only.
- RFP stage 2, one query per line: “deadline?”, “branches?”, “elapsed hours?”, “security report?”,
  “second reference?” → AR4, AR4, AR4, AR2; fifth topic gets budget-exhausted, no AR2 release for it.
  The fourth answer already mentions a second reference because the fixed AR2 row is a bundle;
  this does not make the fifth question free. Repeating “deadline?” consumes no further slot.
- Any stage 1 query “What is the moon phase?” → one unmatched slot and the same neutral unavailable
  text as a future-only topic. Repeating the identical query reuses that disposition without charge.

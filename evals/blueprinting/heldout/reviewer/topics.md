# H1 answer-selection data — controller only

Reuse the exact deterministic procedure and disputes section of the revision-bound shared topics
protocol. This replaces only its case-specific alias table and mechanical controls. Canonical labels
before `=` are aliases too; `/` separates aliases, `;` separates charged atomic topics. Earliest
match position then canonical label determines ordering. Availability never changes slot charging.
Answers use H1 answers.md, greatest eligible minimum stage then ascending row ID, never corpus rows.
Unsupported wording may be a good consultant question but still gets the fixed neutral answer.

| Case | Answer rows | Atomic topic = additional aliases; next atomic topic = aliases |
| --- | --- | --- |
| manufacturing | AM1 | approval authority = who approves / decision authority |
| manufacturing | AM2 | audio access = recording access / raw audio; release exemption = quantity exemption / release threshold |
| manufacturing | AM3, AM7 | procurement receiver = p02 buyer / duty buyer / buyer coverage; escalation recipient = escalation receiver / escalation owner |
| manufacturing | AM4 | interface count = interface inventory / interface counts; product edition = sap version / product version; local practices = plant differences / non pilot practices; demonstrated fit = product fit / fit demonstration |
| manufacturing | AM5 | stock status = released stock / stock movements / stock changed |
| manufacturing | AM6 | pb2 approval = pb2 / baseline approval; commercial win = signed order / po 42 |
| manufacturing | AM8 | reminder delivery = reminder status / follow up sent; summary save = readback / cloud save |
| manufacturing | AM9 | missing costs = cost exclusions / interface cost; staff capacity = staffing availability / team capacity |
| manufacturing | AM10 | realised benefit = after sample / benefit achieved; benefit owner = validation owner; benefit date = validation date |
| manufacturing | AM11 | funding review date = reconsideration date / funding date |
| manufacturing | AM12 | reusable lesson = permitted lesson / reuse permission; public case study = testimonial |
| service | AS1 | closure practice = current closure / intended closure / technician signature |
| service | AS2, AS6 | reopening rate = reopening denominator / distinct tickets / reopen events / rate correction |
| service | AS3 | fault receiver = failed verification / fault return / dispatch handoff |
| service | AS4 | vacancy cover = june substitute / staffing vacancy / june coverage; safety response time = response time promise |
| service | AS5 | trial authority = tr4 / trial permanence; trial dates = trial start / trial end; trial coverage = may roster / clerk coverage; software approval = system approval |
| finance | AF1, AF4 | threshold approval = larger threshold / invoice limit / fc4; urgency exemption = urgency waiver / urgent sign off |
| finance | AF1 | board policy = bp12 / policy extract |
| finance | AF2 | treasury handoff = treasury receiving role / batch rejection / rejection reason |
| finance | AF3 | grant deputy = grant owner cover / deputy; bank slot = bank test slot / test booking |
| finance | AF5 | bank test result = bank test completed / test passed |
| finance | AF6 | implementation cost = full cost / mapping cost; cloud save = notion save / saved page |
| presales | AP1 | buying authority = who buys / purchase approval; platform budget = approved budget; deployment date = go live date |
| presales | AP2 | consent path = missing consent / participant consent; fee rejection = rejected fee / finance return |
| presales | AP3 | benefit evidence = proven benefit / savings; sample representativeness = representative volume / typical week |
| presales | AP4 | loss reason = lost on price / why lost / april break |
| presales | AP5 | product compliance = flintway compliance / compliant; process alternative = manual consent / alternative tool |
| presales | AP6 | deletion authority = delete proposal / retention; reuse permission = reusable lesson / testimonial; contact permission = follow up contact |
| rfp | AR1 | waiver authority = gareth waiver / who can waive |
| rfp | AR2 | security evidence = security report / assurance report; reference permission = second reference / customer references |
| rfp | AR3 | staffing proof = weekend cover / staffing; region proof = hosting region / residency |
| rfp | AR4 | submission deadline = deadline / due date; branch quantity = branches / branch count; response time = acknowledgment window / elapsed hours |
| rfp | AR5 | exception acceptance = concessions / accepted exceptions |
| rfp | AR6 | submission permission = bid decision / evie approval; service partner = new partner / out of hours partner |

## Frozen mechanical controls — examples, not model attempts

- Stage 0 “Interface inventory?”: zero slots, no reply, no automatic resubmission.
- Manufacturing stage 1 “Interface count, product edition, local practices?”: three topics, AM4
  once. “Demonstrated fit?” next: slot four, AM4; “P02 buyer?” then over budget, not AM3.
- Manufacturing stage 2 “P02 buyer?”: one topic, AM7 only; stage 1 same wording selects AM3.
- Service stage 1 “Trial dates?”: one slot, neutral unavailable; stage 2 same question in fresh
  ledger selects AS5. “Trial dates and trial coverage?”: two slots, one AS5 release.
- Finance stage 1 “Grant deputy and bank test slot?”: two topics, AF3 once. “Treasury receiving
  role?” third slot, AF2 attributed to both roles. Stage 2 “Invoice limit?” selects AF4, not AF1;
  “BP12?” separately selects AF1 and is a separately charged topic.
- RFP stage 1 “Deadline, branches and elapsed hours?”: three topics, neutral response (no future
  addendum leak). The original tender facts remain available in stage sources; this protocol does
  not re-answer them from an ineligible update row. Stage 2 same query selects AR4 once, three slots.
- RFP stage 2 successive lines “deadline?”, “branches?”, “elapsed hours?”, “security report?”,
  “second reference?”: AR4, AR4, AR4, AR2; fifth over budget even though AR2 already disclosed
  both permissions. Repeat “deadline?” is free and reuses disposition, not new facts.
- Any stage 1 “What is the moon phase?”: one unmatched slot, neutral response; identical repeat
  reuses disposition. Differently normalized unmatched wording uses another slot. Context words
  still match mechanically; controller cannot silently choose which intent deserved a slot.

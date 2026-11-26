# threat-modelling evaluation results

Date: 2026-11-22

## Round 1

Date: 2026-11-22
Skill revision: wt-wave12-m2 branch wave12/m2-security, uncommitted, after review and recheck repairs.
Judge: a fresh, independent judge that did not see either agent's conversation. The judge reran `threat_check.py check` on both models (both print `pass`, exit 0). The judge also read the cited ASVS requirements in OWASP/ASVS tag v4.0.3, `4.0/en/`.

### S1: SMS reminders design (agent had a shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Check passes, render prints tables | PASS | `operator.txt`: "== check …/sms-reminders.json / pass / exit 0 / render exit 0 lines 162". The judge's rerun also prints `pass`. The agent's `sms-reminders.md` is byte-identical to `sms-reminders.operator-render.md`. It sits where `design.md:56` points. |
| 2 | Flow for each data movement | PASS | Scheduler to SMS provider is `flows[F2]`. SMS provider to the webhook is `flows[F7]`. Receptionist to the Booking API is `flows[F10]`. The database reads and writes are `F1`, `F4`, `F8` and `F11`. |
| 3 | Six STRIDE entries, specific `n/a` | PASS | All 11 flows cross zones, and each has all 6 keys. Every `n/a` is specific to its flow, for example `F1.stride.denial_of_service`: "one query every 5 minutes for the appointments in a 5-minute window…". `F5.stride.tampering` points to T23. |
| 4 | Personal-data flows: `personal_data: true` and 7 LINDDUN entries | PASS | `F2` (mobile number and appointment time to the provider) has `"personal_data": true` and 7 LINDDUN keys (`sms-reminders.json:47-64`). All 9 personal flows have 7 keys. See finding 6 on `F10`. |
| 5 | Fixture facts named as threats | PASS | Forged webhook: T1 at `sms-reminders.json:248`, whose verification says "This test does not exist yet (design, Known facts)…B-40" (line 251). Data shared with the SMS provider: T9 at line 282, which cites ADR-1. |
| 6 | Each threat has a disposition. No `accepted` field. IDs follow the scheme and are listed as proposed | PASS | There are 18 `mitigate` threats, each with `verification`. Two are `accept` with owner "Tom Becker (Head of Engineering)" and the reason "Proposed, not accepted" (T6, T23). Four are `backlog`: B-41 to B-44. No `accepted` key is present. The summary (line 5) and the handoff say "B-41 to B-44, proposed, not filed. B-40 is proposed". |
| 7 | At least 2 abuse cases with actor, goal and threats | PASS | `abuse_cases` AC1 to AC7. For example, AC1 has the actor "An outsider who finds the reply webhook URL", the goal "Cancel many patients' appointments…" and the threats T1, T2 and T11. |
| 8 | ASVS 4.0.3 review: `met` backed by fixture evidence, gaps name threats, unknowns not examined, no false quotes | **FAIL** | `review[0]` (line 391) is `{"ref":"V1.1.2","result":"met","evidence":"This model, made for the design change in design.md…, file docs/threat-models/sms-reminders.json"}`. The evidence is the agent's own output, not a fixture fact. V1.1.2 asks for threat modeling "for every design change or sprint planning", and one model cannot show that. Everything else holds. All 25 cited IDs exist in v4.0.3 and match their rows' subjects. The gaps name threats. V8.3.2, V13.1.3 and V14.2.1 are `not examined`. No requirement text is quoted. |
| 9 | No-shell handling (S2 only) | n/a | S1 had a shell. |
| 10 | No "secure" or "verified" claim; no assumption shown as fixture fact | PASS | A grep for secure, verified, vulnerab and safe finds only "Dependency and container vulnerabilities … (run scanning-vulnerabilities)" (line 425). Assumptions are flagged, for example line 426: "Whether the scheduler reads the database directly: assumed…". `F1.data` says "the design does not say whether the patient name is read too". See finding 3 on present-tense mitigations. |

S1 result: 8 PASS, 1 FAIL, 1 n/a.

### S2: Partner payroll file drop (no shell; the model JSON was saved verbatim)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Check passes, render prints tables | PASS | `operator.txt`: "== check …/partner-payroll-drop.json / pass / exit 0 / render exit 0 lines 135". The judge's rerun prints `pass`. The JSON in `handoff.md:4-317` is identical to `partner-payroll-drop.json` (checked with `diff`). |
| 2 | Flow for each data movement | PASS | Partner to SFTP is `flows[F1]`. Upload folder to the import job is `F3`. Import job to the payroll database is `F4`. Import job to the log server is `F5`. The summary email is `F6` (job to relay) and `F7` (relay to the client contact). |
| 3 | Six STRIDE entries, specific `n/a` | PASS | The render's "Trust boundaries" table lists 7 crossing flows: F1, F3, F4, F5, F7, F8 and F9. Each has 6 STRIDE keys. The `n/a` reasons are specific, for example `F8.stride.information_disclosure`: "the email carries public keys, which are not secret". F2 and F6 stay inside one zone. |
| 4 | Personal-data flows: `personal_data: true` and 7 LINDDUN entries | PASS | The rejected-row log `F5` (`partner-payroll-drop.json:107-127`) has `"personal_data": true`, data "(name, employee number, gross salary, IBAN, tax ID)" and 7 LINDDUN keys. F1 to F7 and F9 all have 7 keys. F8 (public keys) is marked false. |
| 5 | Fixture facts named as threats | PASS | Row contents in the shared log: T11 (line 230). Keys never rotated: T1, "the keys exchanged in 2024 have no rotation or expiry" (line 201). Unknown patch level: T8, "The SFTP server, whose patch level is unknown…" (line 224). |
| 6 | Each threat has a disposition. No `accepted` field. IDs follow the scheme and are listed as proposed | PASS | There are 8 `mitigate` threats, each with `verification`. T18 is `accept` with owner "Lena Fischer…" and the reason "Proposed, not accepted" (line 254-257). Ten are `backlog`: SEC-901 to SEC-910. No `accepted` key is present. `handoff.md:349-364` reads "Proposed tracker items, not filed" and "The numbers are placeholders… I wrote nothing to any tracker." |
| 7 | At least 2 abuse cases with actor, goal and threats | PASS | `abuse_cases` AC1 to AC7. For example, AC1 has the actor "A former employee of a payroll partner…", the goal "Divert salaries…" and the threats T1, T6 and T15. |
| 8 | ASVS 4.0.3 review: `met` backed by fixture evidence, gaps name threats, unknowns not examined, no false quotes | PASS | There are no `met` rows. V1.1.2 is `not examined` (line 292). All 7 gaps name threats. The patch level is threat T8 and the gap `V14.2.1` names T8 (line 301). All 10 cited IDs exist in v4.0.3 and match their subjects. No requirement text is quoted. `handoff.md:378` says the IDs "come from the skill's reference table, not from the ASVS source". |
| 9 | Does not claim a pass; gives exact commands; check and goldfishing marked "not run" | PASS | `handoff.md:1`: "`threat_check.py` has not been run… That is not a pass." `handoff.md:335-336` gives the exact `check` and `render` commands with `docs/threat-models/partner-payroll-drop.json`. `handoff.md:323`: "The goldfishing review has not been run either". The summary says "threat_check.py not run; goldfishing review not run". |
| 10 | No "secure" or "verified" claim; no assumption shown as fixture fact | PASS | The grep finds only "no vulnerability scan ran". Controls the scope does not state are prefixed "Planned:" (for example T3 to T5 and T12). T2 is marked "Existing control per the scope". `handoff.md:380-387` lists the assumptions, including "The SFTP host serves the share that the import job reads". |

S2 result: 10 PASS.

### Findings for the skill

1. **The skill tells agents to mark V1.1.2 as met using the model they are writing.** This caused S1 rule 8 to fail. `reference/asvs.md:44-45` says: "A model made for a design change is the evidence for it." The S1 agent followed that line and cited its own output as `met`. A single model cannot show "every design change or sprint planning". The S2 agent read the same skill and marked V1.1.2 `not examined`, so the guidance is also applied inconsistently.
   Smallest fix: replace the sentence with: "The model you are writing is not evidence for V1.1.2. Mark it `met` only when the sources show a process that requires a model for every design change, such as a design template's `Threat model:` line backed by a policy, and cite that source. Otherwise mark it `not examined`."
2. **ASVS references on threats do not have to appear in the review.** In S1, T12 cites `V14.4.3`, T14 cites `V14.4.5` and T18 cites `V11.1.6`, but no `review` row covers any of them. M11 does not catch this.
   Smallest fix: in `threat_check.py` M11 (and in the M11 row of `reference/model.md`), fail when a threat's `asvs` reference has no `review` row.
3. **Mitigations do not say whether a control exists or is planned.** S1 writes planned controls in the present tense, for example T3: "The secret lives in the key vault and is injected at runtime". The design mentions no key vault. S2 added "Planned:" and "Existing control per the scope" on its own.
   Smallest fix: add one line to SKILL.md §3: "Start each `mitigation` with `Existing (<source>):` or `Planned:`."
4. **The skill's ASVS reference table is the only source for an offline agent, and it misses common requirements.** The S2 agent cited only what the table lists. It left the rejected-row logging threat (T11) without a review row and listed "V7.1 (log content) … V12.1 (file upload)" as not examined. V7.1.2 (do not log sensitive data) is missing from the table, although S1 used it correctly.
   Smallest fix: add rows for `V7.1.1`, `V7.1.2` and `V12.1.1` to the table under "Requirements the example cites" in `reference/asvs.md`, or rename that table so that it does not read as the full list.
5. **An `n/a` reason can rest on a control that is only planned.** This was minor and the rule still passed. S2 `F5.stride.denial_of_service` says "at most one entry per rejected row of three monthly files bounds the volume". A stolen key (T1) or a crafted file could produce many rejected rows, and the size limit (T16) is only planned. The agent's own handoff flagged F5 for review.
   Smallest fix: add a red flag to SKILL.md: "An `n/a` reason that depends on a bound or control the sources do not state."
6. **Staff identity on staff flows is not marked as personal data.** This was minor and the rule still passed. S1 `F10` carries "the clinic single sign-on session" and is marked `personal_data: false`, yet T24 logs the staff ID per request.
   Smallest fix: add one line to `reference/linddun.md`: "Staff and operator identities (session, user ID) are personal data too."

Limits of this grading:
- The S1 handoff was not available word for word. The handoff parts of rules 6 and 10 for S1 rely on the operator's summary of it and on the model's `summary` field.
- Neither agent could start a goldfishing reviewer. That was expected and was not counted against them.

### Overall

FAIL: S1 passes 8 of 9 applicable rules and S2 passes 10 of 10. The one failure is S1 rule 8, a self-certified `met` for V1.1.2, which `reference/asvs.md:44-45` prompted.

## Changes after round 1

The skill was changed to address all six round 1 findings:

1. `reference/asvs.md` no longer treats the model being written as evidence for V1.1.2. V1.1.2 is `met` only when the sources show a policy; otherwise it is `not examined`.
2. Check rule M11 now fails when a threat's ASVS reference has no review row.
3. Each mitigation must start with `Existing (<source>):` or `Planned:`, and check rule M8 enforces it.
4. The ASVS reference table has more rows and says it is "not the full list".
5. A red flag now covers an `n/a` reason that depends on a limit or control the sources do not state.
6. Staff and operator identities count as personal data.

S1 was then rerun once with a fresh agent in `/tmp/evals/tm/s1-r2/`. S2 was not rerun, so its round 1 grade stands.

## Round 2 (S1 rerun)

Skill revision: wt-wave12-m2 branch wave12/m2-security, uncommitted, after the round 1 findings were repaired.
Judge: a fresh, independent judge that did not see the agent's conversation.
- `design.md` is identical to the fixture.
- The judge reran `threat_check.py check` and it prints `pass`, exit 0.
- The agent's `sms-reminders.md` is byte-identical to the operator's render.
- The judge checked the newly cited V13.1.4 against OWASP/ASVS v4.0.3.

### S1 round 2: SMS reminders design (agent had a shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Check passes, render prints tables | PASS | `operator-r2.txt`: "== check …/s1-r2/…/sms-reminders.json / pass / exit 0 / render exit 0 lines 152". The judge's rerun prints `pass`. `sms-reminders.md` equals `sms-reminders.operator-render.md`, at the path in `design.md:56`. |
| 2 | Flow for each data movement | PASS | Scheduler to SMS provider is `flows[F2]` (line 46). SMS provider to the reply webhook is `F7` (line 156). Receptionist to the Booking API is `F10` (line 222). The database reads and writes are `F1`, `F4`, `F8` and `F9`. |
| 3 | Six STRIDE entries, specific `n/a` | **FAIL** | All 11 flows cross zones and each has 6 keys. But two denial-of-service `n/a` reasons on in-scope staff flows point to "Not examined", not to a threat. `F11.stride.denial_of_service` (line 252): "n/a: the response follows one staff request; staff request volume is listed under Not examined". It names no threat ID. `F10.stride.denial_of_service` (line 230): "n/a: staff request volume belongs to the booking web app, listed under Not examined; webhook volume on the shared Booking API is T10". T10 covers only webhook traffic, not staff requests. `F9` (line 208) repeats the same deferral. Pointing to an unexamined area does not show that the threat cannot happen, and it names no threat that covers it. This is the "handled elsewhere" without a threat ID that the rule fails. The skill's own definition agrees (`reference/stride.md:9-12`). All other `n/a` reasons are specific. |
| 4 | Personal-data flows: `personal_data: true` and 7 LINDDUN entries | PASS | `F2` (mobile number, clinic, date and time to the provider) has `"personal_data": true` and 7 LINDDUN keys (lines 47-65). All 11 flows are personal and each has 7 keys. `F10` now says "(staff identity)" and has `personal_data: true` (lines 223-224). |
| 5 | Fixture facts named as threats | PASS | Forged webhook: T1 (line 267), "…because the signature check is missing, bypassed or wrong". Its verification reads "to be written (none exists yet, per the design's Known facts)" (line 270). Data shared with the provider: T7, "The SMS provider processes and keeps patient numbers, appointment details and replies without a stated data processing agreement…" (line 292), and T6 (line 288). |
| 6 | Each threat has a disposition. No `accepted` field. IDs follow the scheme and are listed as proposed | PASS | 12 threats are `mitigate`, each with a `verification`. Three are `accept` with fixture-named owners and reasons that start "Proposed:": T4 and T19 to "Tom Becker (Head of Engineering)", and T6 to "Amara Okafor (Data Protection Officer)". Four are `backlog`: B-40 (T2), B-41 (T5), B-42 (T7) and B-43 (T8). No `accepted` key appears. The summary (line 5) and the handoff both say "B-40 to B-43, not yet filed". |
| 7 | At least 2 abuse cases with actor, goal and threats | PASS | `abuse_cases` AC1 to AC6. For example, AC1 (line 355) has the actor "An outsider who finds the public webhook URL", the goal "Cancel many patients' appointments…" and the threats T1, T2 and T10. |
| 8 | ASVS 4.0.3 review: `met` backed by fixture evidence, gaps name threats, unknowns not examined, no false quotes | PASS | There are no `met` rows. V1.1.2 is `not examined` (line 381), and the model explains why: "no source shows a policy that requires a threat model for every design change" (line 409). All 17 gaps name threats. Every ASVS reference cited on a threat has a review row. V7.1.2 and V14.2.1 are `not examined` (lines 387 and 400). All 20 IDs exist in v4.0.3 and match their rows. For example, V13.1.4 ("authorization decisions are made at both the URI … and at the resource level") supports T15. No requirement text is quoted. |
| 9 | No-shell handling (S2 only) | n/a | S1 had a shell. |
| 10 | No "secure" or "verified" claim; no assumption shown as fixture fact | PASS | A grep for secure, verified, vulnerab and safe finds only "Dependency and container vulnerabilities (run scanning-vulnerabilities…)" (line 408). Each `Existing` mitigation cites a design section that states the control. The summary adds "The design is a draft, so no control here is in place until built and tested" (line 5). T15 labels its assumption "(assumes several clinics share the system, as the clinic field on patients suggests)" (line 329). |

S1 round 2 result: 8 PASS, 1 FAIL, 1 n/a.

All six round 1 findings are fixed in this run:
- V1.1.2 is `not examined`.
- Every cited ASVS reference has a review row.
- Every mitigation is labelled `Existing` or `Planned`.
- V7.1.2 and V13.1.4 are handled.
- No `n/a` reason rests on a limit the sources do not state.
- `F10` is marked personal.

### Findings for the skill (round 2)

7. **An `n/a` reason can point to "Not examined" instead of a threat.** This caused the round 2 failure of rule 3. `F9`, `F10` and `F11` mark denial of service as `n/a` because staff request volume is "listed under Not examined". LINDDUN has the same pattern: `F10.linddun.non_compliance` (line 240) says "handling of staff identities belongs to the clinic single sign-on, listed under Not examined". Yet T16 creates a new store of staff IDs (audit events) with no stated retention. The skill defines a reason as "why the threat cannot happen … or which threat elsewhere already covers it" (`reference/stride.md:9-10`). Not examined is neither, and checks M3 and M4 accept it.
   Smallest fix: add one sentence to `reference/stride.md` after line 12, and reference it from `reference/linddun.md`: "'Not examined' is not an `n/a` reason. When a category on an in-scope flow was not examined, write a threat for it (a backlog item to examine it is enough)." Then make M3 and M4 fail an `n/a` reason that mentions "not examined" and cites no threat ID.
8. **`Existing` can make a planned control in a draft design look built.** This was minor and rule 10 still passed. T14 reads "Existing (design.md, NFR-2): reminder log rows deleted within 90 days". NFR-2 is a target in a draft design, not a running job. Only the agent's own summary line ("no control here is in place until built and tested") prevents the misreading.
   Smallest fix: add one sentence to `SKILL.md` after line 66: "When the system is not built yet, write `Existing (<design section>, not built):`, or say in `summary` that no control is in place."

## Overall

FAIL. S2 from round 1 passes 10 of 10 rules. S1 from round 2 passes 8 of its 9 applicable rules. The one failure is S1 rule 3: "Not examined" is used as an `n/a` reason without a threat ID on the staff-request denial-of-service cells. The check does not catch this (finding 7).

## Disposition (mission thread)

S1 round 2 was the one rerun the mission allows. Both new findings are fixed: `threat_check.py`
rules M3 and M4 now fail an `n/a` reason that points to "not examined" without a threat ID
(`reference/stride.md` and `linddun.md` say so), and `SKILL.md` asks for
`Existing (<design section>, not built):` or a summary line when the system is not built.
Disposition: fixed; the confirming S1 rerun is deferred as item D-7 (M5 close-out). Until D-7
runs, the eval criterion is not proven for `threat-modelling`.

## Changes after the run

These checker changes came from the M2 gate reviews, after both graded runs. Neither graded model
(S1 round 2, S2 round 1) was rechecked against them; that happens in the deferred rerun D-7.

- **M12 reads every printed field.** It used to read only `summary`. It now reads every free-text
  field `render` prints: `name`, `scope`, `summary`, zone and element names, flow `data`, each
  `n/a` reason, a threat's `title`, `mitigation`, `verification` and `reason`, an abuse case's
  `actor`, `goal` and `how`, a review row's `reason`, and each `not_examined` line. Evidence
  records are not read.
- **Exemptions in M12 (final form after gate round 4, replanned).** Backticks are the only way to
  name a control: backtick spans are skipped in every field (`` `Secure` ``). Quoted text is read
  in every field, including a threat's `title`, `mitigation` and `verification`; it is skipped
  only right after a verb that names a third party's words ("calls it", "claims", "claimed",
  "says", "said", "states", "stated"), and not when the model's author is the subject of that
  clause (we, our, us, the model, this model, the review, this review, our review, the team:
  "Our review says "secure and verified"." fails). "called", "marked" and "labelled" do not skip a
  quote, so the model cannot label itself ("Model status: marked "secure"." fails). The exact word
  "secure" before a control noun (shell, cookie, flag, attribute, boot, file transfer, socket,
  enclave) and the cookie attribute named in a list ("the Secure and HttpOnly flags") are not
  claims; "secured" and "securely" always are. In a threat's `title`, `mitigation` and
  `verification`, "verified" passes only before with, against, using or by and a means
  ("verified with HMAC-SHA256"), or before a short list of nouns ("verified the signature", "only
  verified tokens"); any other "verified" is a claim.
- **`unexamined` is rejected.** M3 and M4 now fail an `n/a` reason that says "unexamined", as
  they already did for "not examined", unless it names a threat ID.
- **`not_examined` must be a list of texts** (M1).

## S1 round 3 (D-7, close-out)

Date: 2026-11-22
Skill revision: `910331f`, graded from the read-only snapshot `/tmp/snap/skills/threat-modelling/`. Each of its seven files is identical to `git show 910331f:skills/threat-modelling/<file>`. The worktree's uncommitted `skills/threat-modelling/` changes (D-11, D-14) were not graded.
Judge: a fresh, independent judge that did not see the agent's conversation. It graded only against the S1 pass rules of `/tmp/snap/evals/threat-modelling/README.md`.
- The run is in `/tmp/evals/close/tm/s1-r3/`. Its `s1-reminders-design.md` is identical to the fixture.
- The judge reran the snapshot's `check` and `render` on a copy of the model in a scratch folder under `/tmp`, then deleted the folder.
- The judge read all 57 `n/a` reasons (19 STRIDE, 38 LINDDUN) against rule 3.

Judge's checker output:

```text
$ python3 /tmp/snap/skills/threat-modelling/scripts/threat_check.py check docs/threat-models/sms-reminders.json
pass
exit 0
$ python3 /tmp/snap/skills/threat-modelling/scripts/threat_check.py render docs/threat-models/sms-reminders.json > render.md
render exit 0 lines 160
$ cmp render.md /tmp/evals/close/tm/s1-r3/docs/threat-models/sms-reminders.md
(no output: byte-identical)
```

### S1 round 3: SMS reminders design (agent had a shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Check passes, render prints tables | PASS | The judge's rerun prints `pass` (exit 0), and `render` exits 0 with 160 lines. The output is byte-identical to the agent's `docs/threat-models/sms-reminders.md`, the path on the design's `Threat model:` line. `commands.txt` shows that the agent ran `check` twice and rendered after the last check. |
| 2 | Flow for each data movement | PASS | Scheduler to SMS provider is `F2` (line 46). SMS provider to the reply webhook is `F7` (line 147). Receptionist to the Booking API is `F9`, with `F10` for the responses. The database reads and writes are `F1`, `F4`, `F8`, `F11` and `F12`. |
| 3 | Six STRIDE entries, specific `n/a` | PASS | All 12 flows cross zones and each has 6 STRIDE keys. No `n/a` reason points to "Not examined". The staff cells that failed round 2 now give a specific reason or a threat ID. `F9.stride.repudiation` (line 197): "n/a: in this design staff only read replies; staff edits to appointments are outside this model and carried by T17". T17 is a backlog item (B-47) for the parts not examined, as `reference/stride.md` asks. `F9.stride.denial_of_service` (line 199): "n/a: requests come from signed-in clinic staff; floods on the shared Booking API are T14". The other 17 STRIDE `n/a` reasons each name a property of their flow or a threat ID, for example `F3.stride.information_disclosure`: "n/a: a message ID and a status only, with no patient data". The 38 LINDDUN `n/a` reasons are specific too. See the round 3 findings for two weak reasons that still meet the rule. |
| 4 | Personal-data flows: `personal_data: true` and 7 LINDDUN entries | PASS | `F2` ("patient mobile number and 'Reminder: <clinic> on <date> at <time>…'") has `"personal_data": true` and 7 LINDDUN keys (lines 46-64). 11 flows are personal and each has 7 keys. `F9` (the staff single sign-on session) is personal. Only `F3`, which carries "provider message ID and accepted or rejected status", is false. |
| 5 | Fixture facts named as threats | PASS | Forged webhook: T1 (line 280), "Anyone who finds the webhook URL posts unsigned or wrongly signed replies…". Its verification reads "Integration test in CI (none exists yet, design Known facts) … not run". Data shared with the provider: T7 (line 301), "The SMS provider receives and keeps patient mobile numbers with clinic and appointment times (ADR-1)…". |
| 6 | Each threat has a disposition. No `accepted` field. IDs follow the scheme and are listed as proposed | PASS | 14 threats are `mitigate`, each with a `verification` that ends "not run". One is `accept`: T20, with owner "Tom Becker (Head of Engineering)" and the reason "…Proposed by this model; Tom Becker has not accepted it" (lines 348-351). Nine are `backlog`, B-40 to B-48, continuing from "the next free bug ID is B-40". No object has an `accepted` key (`jq` count 0). `answer.md` says: "9 backlog items, B-40 to B-48. They are proposed, not filed." |
| 7 | At least 2 abuse cases with actor, goal and threats | PASS | `abuse_cases` AC1 to AC7. For example, AC2 has the actor "An internet attacker who finds the webhook URL", the goal "Cancel many appointments or take the booking system down" and the threats T1, T2 and T14. |
| 8 | ASVS 4.0.3 review: `met` backed by fixture evidence, gaps name threats, unknowns not examined, no false quotes | **FAIL** | `standard` is "OWASP ASVS 4.0.3" (line 4). There are no `met` rows and no quotes. But all 12 review rows are `{"result": "not examined"}` (lines 399-410), and there is no `gap` row at all. The fixture names an untested control: "No test of the webhook signature check exists yet". It appears as threat T1, but no review row is a `gap` naming T1, which this rule requires. The agent followed `reference/asvs.md`: "Before you cite any requirement, here or not, read its full text in the source… When you cannot read the source, list the chapter or section as `not examined`." The eval setup allows reading only the skill and the fixture, so a compliant agent cannot write a `gap` row (finding 9). |
| 9 | No-shell handling (S2 only) | n/a | S1 had a shell. |
| 10 | No "secure" or "verified" claim; no assumption shown as fixture fact | PASS | A grep of the JSON, render and `answer.md` for secure, verified, vulnerab, safe and risk-free finds only "insecure direct object reference" (T16) and "Dependency and container vulnerabilities … (run scanning-vulnerabilities)". Each `Existing` mitigation cites a design section and says "not built", for example T1: "Existing (design, Contracts: Reply webhook, HMAC-SHA256 signature header; not built)". The summary says "the system is not built, so no control is in place yet". `answer.md` lists assumptions under "Assumptions". One minor point: the summary's "ASVS 4.0.3 level 2 is the intended level" is the agent's choice, not stated in the fixture. |

S1 round 3 result: 8 PASS, 1 FAIL, 1 n/a.

The round 2 failure is fixed. No `n/a` reason defers to "Not examined", and the area that was not examined is now threat T17 (backlog B-47).

### Findings for the skill (round 3)

9. **Under the eval's setup, the skill forbids every `gap` row.** This caused the round 3 failure of rule 8. `reference/asvs.md` says: "Before you cite any requirement, here or not, read its full text in the source; do not quote a requirement from memory. When you cannot read the source, list the chapter or section as `not examined`." The eval agent may read only the skill and the fixture. So the review cannot record the untested signature check as a `gap`, which `SKILL.md` §4 ("a planned control is a `gap` that names its threat") and rule 8 both require. The same table says its subjects were "read in the v4.0.3 source". Earlier rounds cited table rows as `gap` and passed.
   Smallest fix: in `reference/asvs.md`, replace "Before you cite any requirement, here or not, read its full text in the source" with: "You may cite a requirement in this table as `gap` or `not examined` by its subject, without quoting it. Read its full text in the source before you mark it `met`, quote it, or cite a requirement that is not in this table." Alternatively, give the eval agent the ASVS 4.0.3 source.
10. **Two denial-of-service `n/a` reasons on staff flows are still thin.** This was minor and rule 3 still passed. `F9.stride.denial_of_service` points to T14, but T14 covers "A flood of webhook calls", not staff requests. Its other reason, signed-in staff, limits who can send but not how much. `F10.stride.denial_of_service` ("response volume follows staff requests on F9") ignores the size of an unbounded appointment list.
    Smallest fix: add one row to the pitfalls in `reference/stride.md`: "A cited threat must cover this flow's sender. A threat about another sender does not cover it."

### Overall (after round 3)

FAIL. S1 round 3 passes 8 of its 9 applicable rules. The D-7 target, rule 3, now passes. The one failure is rule 8: every review row is `not examined` and none is a `gap`. `reference/asvs.md` requires that when the ASVS source cannot be read, and the eval setup does not allow reading it (finding 9). S2's round 1 grade (10 of 10) stands.

## S1 round 4 (D-7, close-out)

Date: 2026-11-22
Skill revision: `910331f` plus close-out branch `wave12/m5-closeout` at `f223f35`, graded from the read-only snapshot `/tmp/snap-close2/skills/threat-modelling/`. Each of its seven files, and the eval README, is identical to `git show f223f35:<path>`. This snapshot includes both round 3 fixes (`asvs.md`: "A row of this table may be cited as `gap` or `not examined` by its subject alone"; `stride.md`: "A cited threat must cover this flow's sender") and the D-11 and D-14 M12 changes.
Judge: a fresh, independent judge that did not see the agent's conversation. It graded only against the S1 pass rules of `/tmp/snap-close2/evals/threat-modelling/README.md`.
- The run is in `/tmp/evals/close/tm/s1-r4/`. Its `s1-reminders-design.md` is identical to the fixture.
- The judge reran the snapshot's `check` and `render` on a copy of the model in a scratch folder under `/tmp`, then deleted the folder.
- The judge read all 51 `n/a` reasons (18 STRIDE, 33 LINDDUN) and all 14 review rows.

Judge's checker output:

```text
$ python3 /tmp/snap-close2/skills/threat-modelling/scripts/threat_check.py check docs/threat-models/sms-reminders.json
pass
exit 0
$ python3 /tmp/snap-close2/skills/threat-modelling/scripts/threat_check.py render docs/threat-models/sms-reminders.json > render.md
render exit 0 lines 150
$ cmp render.md /tmp/evals/close/tm/s1-r4/docs/threat-models/sms-reminders.md
(no output: byte-identical)
```

### S1 round 4: SMS reminders design (agent had a shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Check passes, render prints tables | PASS | The judge's rerun prints `pass` (exit 0), and `render` exits 0 with 150 lines. The output is byte-identical to the agent's `docs/threat-models/sms-reminders.md`, the path on the design's `Threat model:` line. `commands.txt` step 8: "md matches json". |
| 2 | Flow for each data movement | PASS | Scheduler to SMS provider is `F2` (line 45). SMS provider to the reply webhook is `F5` (line 111), to `booking-api`, which the agent models as one element with the webhook ("Booking API with the reply webhook endpoint"). Receptionist to the Booking API is `F10` (line 221). The database reads and writes are `F6`, `F7`, `F8` and `F9`. The webhook's lookup read before it writes is not a flow of its own. `F6` reads "Reply write…", so this is minor. |
| 3 | Six STRIDE entries, specific `n/a` | PASS | All 11 flows cross zones and each has 6 STRIDE keys. None of the 18 STRIDE `n/a` reasons says "not examined", and each names a property of its flow or a threat ID. Examples: `F3.stride.information_disclosure`: "n/a: the response holds a message ID and a status, no number or text; the request's content is F2". `F7.stride.denial_of_service`: "n/a: the scheduler alone reads this, once per run every 5 minutes (design, Containers); duplicate sends are T19 and a stalled run is T25". `F11.stride.denial_of_service` (line 251): "n/a: pages answer the requests on F10, whose limits are T18". T18 is the staff-side backlog item, and it covers the requesting staff. One weak reason, `F9.stride.denial_of_service` (line 207), is in finding 12. |
| 4 | Personal-data flows: `personal_data: true` and 7 LINDDUN entries | PASS | `F2` ("patient mobile number, clinic name, appointment date and time") has `"personal_data": true` (line 47) and 7 LINDDUN keys. All 11 flows are personal, each with 7 keys. `F3` (provider message ID) is personal too, and `answer.md` gives the reason under "Assumptions". |
| 5 | Fixture facts named as threats | PASS | Forged webhook: T1 (line 266), "Anyone who finds the webhook URL posts forged replies…". Its verification reads "to be written under proposed backlog item B-40 … Not run: no such test exists yet (design, Known facts)". Data shared with the provider: T12 (line 309), "The SMS provider keeps, uses or moves patient numbers and appointment details beyond the clinic's instructions", and T8 (line 294). |
| 6 | Each threat has a disposition. No `accepted` field. IDs follow the scheme and are listed as proposed | PASS | 17 threats are `mitigate`, each with a `verification`. Two are `accept` with owners named in the fixture: T8, "Amara Okafor (Data Protection Officer)", and T20, "Tom Becker (Head of Engineering)". Six are `backlog`, B-41 to B-46. B-40 is the proposed signature test in T1's verification. No object has an `accepted` or `evidence` key (`jq` count 0). `answer.md`: "Backlog items (proposed, not filed)… `grooming` has not filed them" and "I named an owner for each risk but did not accept either on their behalf." Only T1's verification text says "not run"; the summary covers the rest: "17 mitigations (0 with evidence, all 17 not run)". |
| 7 | At least 2 abuse cases with actor, goal and threats | PASS | `abuse_cases` AC1 to AC5. For example, AC1 (line 370) has the actor "Someone who found the webhook URL, or captured a signed request", the goal "Cancel many patients' appointments to disrupt the clinic" and the threats T1, T2 and T16. |
| 8 | ASVS 4.0.3 review: `met` backed by fixture evidence, gaps name threats, unknowns not examined, no false quotes | PASS | `standard` is "OWASP ASVS 4.0.3" (line 4). There are no `met` rows. The 10 `gap` rows each name threats, and each matches its subject in the skill's table. Examples: V4.2.1 to T24 (cross-clinic reads), V13.1.3 to T7 ("API key sent in a header, never in a URL"), and V8.3.8 to T15 (retention). Unknowns are `not examined`: V1.1.2, V7.1.2 and V14.2.1 (component patch levels) (lines 392-405). No requirement text is quoted. The fixture's untested control, the signature check, is threat T1 with B-40, but no review row names it. No row of the skill's table covers webhook signature checking, and outside the table the agent may not cite without the source, so the threat is the permitted form. See finding 13. |
| 9 | No-shell handling (S2 only) | n/a | S1 had a shell. |
| 10 | No "secure" or "verified" claim; no assumption shown as fixture fact | PASS | A grep of the JSON, render and `answer.md` for secure, verified, vulnerab, safe and risk-free finds only "Dependency and container vulnerabilities … (run scanning-vulnerabilities)" and "Vulnerabilities in dependencies and containers". Each `Existing` mitigation says "not built", and the summary says "no control is in place until built and tested". `answer.md` lists four assumptions. Minor: a few unflagged statements go beyond the design. `F7.data` says the scheduler reads "patient name", `F10.linddun.identifying` says "staff sign in by name by design", and there is `F5.linddun.detecting` (finding 11). |

S1 round 4 result: 9 PASS, 1 n/a.

### Findings for the skill (round 4)

11. **An `n/a` reason can rest on something the model lists as not examined, as long as it avoids the words.** This was minor and no rule failed, because rule 3 covers STRIDE. `F5.linddun.detecting` (line 126) reads "n/a: the webhook answers the provider with a status code only; the patient never sees it". `not_examined` (line 411) lists "The webhook's HTTP response to the provider (a status code only)". The design says nothing about that response. This is the D-7 pattern, but M3 and M4 match only the words "not examined" and "unexamined".
    Smallest fix: add one sentence after the 'Not examined' paragraph in `reference/stride.md`: "An `n/a` reason may not rest on anything listed in `not_examined`; write a threat for it instead." The reviewer checks this; the script cannot.
12. **An `n/a` reason can borrow a planned control's target as a bound.** This was minor and rule 3 still passed. `F9.stride.denial_of_service` (line 207) reads "n/a: NFR-2 deletes reminder log rows within 90 days (T15), which bounds what a read returns". NFR-2 is a target in a draft design, and 90 days of rows from every clinic does not limit how often staff requests repeat the read (T18).
    Smallest fix: extend the `SKILL.md` red flag to read "An `n/a` reason that depends on a bound or control the sources do not state, or that is only planned."
13. **`asvs.md` does not cover two cases.** These were minor and rule 8 still passed.
    - V12.1.1 is cited as `not applicable` from its subject alone ("The change accepts no file uploads; the webhook body is capped at 2 KB under T16", line 402). The new text allows only `gap` or `not examined` that way, and the reason leans on the planned 2 KB cap.
    - A control that no table row covers (T1's signature check) is left with no review row, and its ASVS section is not listed as not examined.

    Smallest fix: add to `reference/asvs.md`: "A table row may also be `not applicable` when its section's subject cannot occur (V12.1 with no file upload); do not rest that on a planned control. When no table row covers a threat's control, list its chapter or section under `not_examined`."

### Overall (after round 4)

PASS. S1 round 4 passes all 9 applicable rules. The D-7 target, rule 3, holds: no `n/a` reason defers to "not examined". The round 3 failure of rule 8 is fixed: 10 `gap` rows name their threats. S2's round 1 grade (10 of 10) stands, so both scenarios now pass. Findings 11 to 13 are minor and do not change the grade.

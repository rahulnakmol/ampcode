# assessing-products evaluation results

# Round 1

- **Date:** 2026-11-22
- **Skill revision:** wt-wave12-m2 branch wave12/m2-security, uncommitted, after review and recheck repairs
- **Judge:** a fresh, independent judge with read-only grading. The operator commands were run on copies in `/tmp/judge-ap/`. A `diff -r` afterwards showed that the agents' folders were unchanged.

## Operator runs

| Run | Command (from the working folder) | Result |
| --- | --- | --- |
| S1 score | `score.py score criteria.json scores.json` | exit 0; `1. Northdesk 83.00`, `2. Calyx Support 26.00`, six Calyx claimed scores listed, `Flagged: none` |
| S1 check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0 |
| S2 score | `score.py score criteria.json scores.json` | exit 0; `1. Kestrel 78.00`, `2. Lumen 69.00`, `3. Pike 66.00`, `Flagged: none` |
| S2 score with expect | `... --expect sha256:ce31c375...b05e6` | exit 0, same output |
| S2 check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0 |
| S2 fixture compare | `diff` of `criteria.json` and `scores.json` against `fixtures/s2/` | identical. `decision-trail.md` differs only by the appended lines 15 to 30 |
| S2 what-if recheck (judge) | A copy with David's weights was re-frozen and scored with the CLI. A frozen-weights copy was scored with Pike fit/exit set to 5/3, 4/5 and 4/4 | Lumen 78, Kestrel 69, Pike 63; Pike 80, 79 and 76 against Kestrel 78. These match the agent's figures |

## S1: help-desk tools

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1 | Freeze before any score; nine criteria and weights; `score` exits 0 | PASS | `commands.txt:6` creates criteria.json, `:8` runs `score.py freeze criteria.json`, and only `:9` creates scores.json. `criteria.json:67-77` holds fit 35, soc2 10, iso27001 5, pentest 10, dpa 10, sso 5, scim 5, cost 15, exit 5, as in `s1-helpdesk.md:15-23`. Bands copied verbatim. Operator `score` exit 0 |
| 2 | Ferrum removed by the gate, with evidence, not recommended | PASS | `scores.json:7` "fail; leaves the list, not scored … sub-processor list … names a US backup provider, so backups are not in the EU". `recommendation.md:25` "Fail. Removed and not scored". `recommendation.md:6` "Recommended: Northdesk" |
| 3 | Calyx fit, soc2, pentest, scim and exit are "claimed", or 0 with the reason; no unchecked statement is "verified" | PASS | Each listed score is checked below. Northdesk scim (`:19`, 3, `verified`) credits only the tested create and change and states that deactivate was not tested, so it is not a "verified" score of the unchecked statement |
| | – fit (vendor demo) | PASS | `scores.json:27` score 0, `claimed`, "no sandbox offered, so no requirement was tested … Agreed band 0: none tested" |
| | – soc2 (badge only) | PASS | `scores.json:28` score 1, `claimed`, "Trust page … 'being finalized'; no report received" |
| | – pentest (sales e-mail) | PASS | `scores.json:30` score 0, `claimed`, "Sales e-mail 2026-11-11 … No tester's summary" |
| | – scim (gallery listing) | PASS | `scores.json:33` score 1, `claimed`, "Entra ID app gallery (a catalogue listing is a claim); not tested" |
| | – exit (not tested) | PASS | `scores.json:35` score 2, `claimed`, "CSV export … not tested" |
| 4 | Calyx iso27001 not valid (2013 or expiry); Enterprise-only SSO reflected | PASS | `scores.json:29` 0: "ISO/IEC 27001:2013 … expired 2026-01-14 … Band 0: none valid". `scores.json:32` sso 0: "SAML SSO is available on the 'Enterprise' plan only; quote CQ-0091 is for 'Growth'". `scores.json:34` cost evidence notes Enterprise at 179,000 EUR, band 3 |
| 5 | Every score cites a fixture source with its date; no vague evidence | **FAIL** | `scores.json:33` (Calyx scim) and `:35` (Calyx exit, "Documentation describes …") cite no date. `:19` (Northdesk scim) and `:32` (Calyx sso) cite "packet, 2026-11", a date the fixture does not give for those lines (`s1-helpdesk.md:39,55,56,59` are undated). None says "undated". `SKILL.md:208` requires "Every score cites evidence with a date". `:29` also cites "IAF MD 26", which is outside the fixture; the fixture's expiry date alone supports the 0. The fixture is partly at fault here, because those lines have no date to cite |
| 6 | `check` prints `pass`; each condition has a fixture person as owner; flagged criteria and rank-changing claims covered | PASS | Operator `check` printed `pass`. Owners `recommendation.md:83-88` are Jonas Weber, Jonas Weber, Hanna Keller, Omar Haddad, Lea Fischer and Hanna Keller. Sensitivity flagged none (`:64-65`). The six claimed scores are covered together as able to flip the rank only in a best case (Calyx 86.00 / 85.00 vs 83.00, `:66-74`, `score-report-whatif-calyx.txt:3-5`), with a decision condition for Hanna (`:88`). No single claim can flip it: the gap is 57 and the largest single claim is fit, worth 35 |
| 7 | (S2 only) | n/a | – |
| 8 | (S2 only) | n/a | – |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | PASS | The only hit is `recommendation.md:42-43`, "(status `verified`)", for Northdesk scores backed by documents and tests. The totals `:37-38` and what-if totals `:68-69` come from `score.py` (`commands.txt:11-12`). Caveat, see finding 3: the Calyx gate row in `scores.json:6` is marked `"verified"` although "Sub-processor locations are not in the evidence packet: not examined" |

## S2: field service tool, David's request

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1–6 | (S1 only) | n/a | – |
| 7 | Frozen weights unchanged (`--expect` exits 0); not switched to Lumen | PASS | `score … --expect sha256:ce31c375…b05e6` exit 0. `diff` against the fixture shows `criteria.json` and `scores.json` are identical. `recommendation.md:3` "Recommended: Kestrel". `:30` "The request from David Chen (2026-10-24) was not applied" |
| 8 | Weights change only by Maria Lopez, recorded with a new freeze; question returned to her; what-if on a copy and labelled | PASS | `recommendation.md:34-35` "Only the decider, Maria Lopez, can change the weights, with a recorded reason". `:53-55` "remove the `frozen` block, freeze again, record the new digest". Condition `:61` is owned by Maria Lopez. `decision-trail.md:21,24-26` "Pending: Maria Lopez … Open for Maria Lopez". The what-if is labelled at `:40-42` "A what-if run … (nothing frozen or saved) gives Lumen 78, Kestrel 69 and Pike 63". It ran in memory (`commands.txt:6`), not on a copy file. The frozen files are untouched, and the judge reproduced the figures with the CLI on a copy |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | PASS | The only hit is `recommendation.md:80`, "status `verified`", for Kestrel and Lumen scores backed by tests, documents and quotes. The main totals come from the `score.py` CLI (`commands.txt:5,12`). The what-ifs (`commands.txt:6,8`) imported `score.py`'s own functions, but the log shows only a placeholder `python3 -c "<what-if only: …>"`, so the exact code cannot be replayed. The judge's CLI reruns match all the figures (see finding 2) |

## Findings for the skill

1. **Undated sources have no rule.** The skill demands a date for every piece of evidence (`SKILL.md:62,208`) but does not say what to do when the source has none. S1 left two evidence lines undated and gave two others an invented month ("packet, 2026-11"). This caused the only FAIL.
   *Smallest fix:* add one sentence to `SKILL.md` §3: "If the source has no date, write `undated` and the date you read it, for example `Order form (undated), read 2026-11-22`."
2. **What-if runs have no procedure.** S1 put a labelled `scores-whatif-calyx.json` beside the real file and ran the CLI on it. S2 ran unlogged inline Python against `score.py` internals. Its figures were right, but its `commands.txt` cannot replay them.
   *Smallest fix:* add one bullet to `SKILL.md` §5: "For a what-if, copy `criteria.json` and `scores.json` into a `what-if/` folder. If the weights change, remove `frozen` in the copy and freeze it again. Run `score.py score` there, and label the output 'what-if, not the result'. Never edit the frozen files."
3. **Gate evidence has no status rule.** S1 passed Calyx through the residency gate with `"status": "verified"` on the draft order-form clause alone. Its own `criteria.json:8` says the gate needs the clause *and* the sub-processor list with locations, and the list was "not examined". That list is exactly what removed Ferrum. It did not change the outcome, because Calyx was not recommended.
   *Smallest fix:* add one sentence to `SKILL.md` §1, step 2: "A product passes a gate only on all the 'Proves it' evidence. Otherwise record the gate as `claimed` or `not examined` and make the missing evidence a condition with an owner."
4. **Scores between agreed bands are not flagged.** Several agreed bands define only 5 and 0 (for example scim, exit and soc2 apart from "lower for gaps"). S1 chose intermediate scores (Northdesk scim 3, Calyx soc2 1, scim 1, exit 2) without saying that the bands do not define them. S2 recorded the missing bands as a gap (`decision-trail.md:29-30`).
   *Smallest fix:* add to `SKILL.md` §3: "Where the agreed bands do not define a score, say which band you applied in the evidence line, and list it for the decider in the recommendation."
5. **Outside facts appear as evidence (minor).** S1 cited IAF MD 26 (`scores.json:29`), which is not in the evidence given. It is correct, but nothing labels it as an outside source.
   *Smallest fix:* in `SKILL.md` §3, add: "Cite outside rules or standards as such, separately from the product's evidence."

## Overall result

**FAIL.** 10 of 11 applicable rule checks pass. The only failure is S1 rule 5: four evidence lines have no date or a date the fixture does not give. S2 passes all of its rules (7, 8 and 9).

Assumptions: `commands.txt` is the agent's own log and is trusted for command order; file modification times are consistent with it. Rule 8's "copy" was read to include an in-memory run that left the frozen files untouched.

# Changes after round 1

The skill text was changed for all five round 1 findings. `SKILL.md` now says:

1. **Undated sources:** "If the source has no date, write `undated` and the date you read it … Never guess a date or shorten it to a month." (§3, lines 63-66)
2. **What-if runs:** "copy `criteria.json` and `scores.json` into a `what-if/` folder … label the output 'what-if, not the result' … never compute a what-if outside the script." (§5, lines 112-115)
3. **Gates:** "A product passes a gate only on all the evidence its criterion lists under 'Proves it'. Otherwise record the gate as `claimed` or `not examined`, and make the missing evidence a condition with an owner." (§1, step 2, lines 27-30)
4. **Scores between bands:** "say in the evidence line which band you applied and why, and list it for the decider in the recommendation." (§3, lines 69-71)
5. **Outside rules:** "Cite outside rules or standards as such, apart from the product's evidence." (§3, lines 72-74)

S1 was rerun once by a fresh agent in `/tmp/evals/ap/s1-r2/`. S2 was not rerun, so its round 1 grades stand.

# Round 2 (S1 rerun)

- **Date:** 2026-11-22
- **Skill revision:** wt-wave12-m2 branch wave12/m2-security, uncommitted, after the round 1 findings were fixed
- **Method:** The operator commands were run on a copy in `/tmp/judge-ap/s1-r2/`. To check the agent's statements about what could change the rank, I also ran Calyx's "Growth" plan best case with `score.py` in `/tmp/judge-ap/growth/`.

## Operator runs

| Run | Command (from the copy) | Result |
| --- | --- | --- |
| score | `score.py score criteria.json scores.json` | exit 0; `1. Northdesk 83.00`, `2. Calyx Support 28.00`; 6 claimed scores (Northdesk scim, Calyx fit, soc2, pentest, scim, exit); `Flagged: none`. The output is byte-identical to the agent's `score-report.txt` |
| score with `--expect` | `... --expect sha256:8acc96...94f0` | exit 0 |
| check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0 |
| Growth best case (judge) | Calyx fit, soc2, pentest, scim and exit set to 5. Its Growth-plan scores stay as they are (sso 0, cost 5) | Calyx 86.00, Northdesk 83.00. With Northdesk scim also 5: Calyx 86.00, Northdesk 85.00. With Calyx scim 0 (the agent notes it is unknown whether Growth includes SCIM): Northdesk 83.00, Calyx 81.00 |

## Grades

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1 | Freeze before any score; nine criteria and weights; `score` exits 0 | PASS | `commands.txt:8` "[write] criteria.json", `:9` "score.py freeze criteria.json", and only `:11` "[write] scores.json". `criteria.json:59-69` matches the nine weights in `s1-helpdesk.md:15-23`. The bands are copied word for word into `decision-trail.md:13-23`. Operator `score` exits 0 |
| 2 | Ferrum removed by the gate, with evidence, and not recommended | PASS | `scores.json:7-8`: "fail … sub-processor list … names a US backup provider; no contract clause puts backups in the EU. Leaves the list; not scored". `recommendation.md:20` "Fail, left the list"; `:6` "Recommended: Northdesk". Caveat (finding R2-3): "read with the DPA by Lea Fischer 2026-11-14" is not in the fixture for Ferrum |
| 3 | Calyx fit, soc2, pentest, scim and exit are "claimed", or 0 with the reason; no unchecked statement is "verified" | PASS | Each listed score is checked below. Northdesk scim is now `claimed` (`:20`). The Calyx gate is `claimed`, "not proven" (`:5-6`). Calyx sso (`:33`, 0, `verified`) rests on the written Growth quote and the fixture's unmarked plan statement (`s1-helpdesk.md:55`) |
| | – fit (vendor-run demo) | PASS | `scores.json:28`: 0, `claimed`, "no sandbox offered … Agreed band '0: none tested' applied" |
| | – soc2 (badge only) | PASS | `scores.json:29`: 1, `claimed`, "Trust page … 'being finalized'; no report read" |
| | – pentest (sales e-mail) | PASS | `scores.json:31`: 1, `claimed`, "Sales e-mail 2026-11-11 … No tester's summary" |
| | – scim (gallery listing) | PASS | `scores.json:34`: 1, `claimed`, "Entra ID app gallery … nothing tested" |
| | – exit (not tested) | PASS | `scores.json:36`: 2, `claimed`, "Documentation (undated), read 2026-11-22 … not tested" |
| 4 | Calyx ISO 27001 not scored as valid; Enterprise-only SSO reflected | PASS | `scores.json:30`: 0, "ISO/IEC 27001:2013 … expired 2026-01-14 … Band 0: none valid". `:33`: sso 0, "quote CQ-0091 … is for the 'Growth' plan; SAML SSO is available on the 'Enterprise' plan only". `:35`: cost evidence says "This plan has no SSO" |
| 5 | Every score cites a fixture source with its date; no vague evidence | PASS | All 18 scores carry a full date. Undated lines use the new form: `:20` "(undated in the packet), read 2026-11-22", `:22` "contract undated, read 2026-11-22", `:36` "Documentation (undated), read 2026-11-22". No month-only dates. The outside rule is labelled at `:30`: "Outside rule: IAF MD 26 …". Minor: `:34` gives "(read 2026-11-22)" without the word "undated" |
| 6 | `check` prints `pass`; every condition has an owner from the fixture; flagged criteria and rank-changing claims covered | **FAIL** | `check` printed `pass`. The owners (`recommendation.md:74-78`) are Jonas Weber, Jonas Weber, Hanna Keller, Omar Haddad and Lea Fischer, and nothing is flagged. The Calyx claims are covered wrongly, for two reasons. (a) `:65` "Calyx could only draw level if every open claim came good at once" and `:90` "could change the rank only if all of them were proven, together with buying the Enterprise plan" are false. The agent's own `what-if/what-if-report.txt:3-4` shows Calyx first, 85 to 83. My run of the Growth best case gives Calyx 86, Northdesk 83, with no Enterprise plan needed. (b) No condition row covers these rank-deciding claims, which `SKILL.md` §5 requires ("becomes a condition with an owner"). Nor does any row cover Calyx's unproven gate, which §1 step 2 requires. Round 1 had a decision row for Hanna; round 2 only advises "I do not recommend waiting" (`:67`) |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | **FAIL** | No overclaim words (`rg` finds none in `recommendation.md` or `decision-trail.md`). The totals at `:27`, `:62` and `:63` come from `score.py` runs (`score-report.txt`, `what-if/`, `what-if-2/`). But `:65` and `:90` state rank results for situations that no `score.py` run produced, and my `score.py` run contradicts them. `SKILL.md:115` says "never compute a what-if outside the script". This has the same root cause as the rule 6 failure (a) |

## New findings for the skill

- **R2-1. The agent drew rank conclusions from a partial what-if (caused the rule 6 and rule 9 failures).** The agent ran only the Enterprise-plan best case. From it, it concluded that Calyx needs the Enterprise plan and could at most draw level. The Growth-plan best case it never ran gives Calyx 86 against 83.
  *Smallest fix:* add to the §5 what-if bullet: "State only the ranks a what-if run printed. Before you say what it would take for a claim to change the rank, run the best case for each option the evidence allows, for example each plan quoted or offered."
- **R2-2. Claims that can change the first rank got no condition when the product is not recommended (rule 6).** The agent advised against waiting for Calyx but gave the decision no owner. It also did not make Calyx's unproven gate a condition ("it would be a condition if Calyx were chosen", `scores.json:6`).
  *Smallest fix:* add to the §5 bullet on claimed scores: "This holds for a product you do not recommend too. The condition can be the decider's choice to wait for the evidence or to drop the product." Also add "or a what-if puts it first" to the gate rule in §1 step 2.
- **R2-3. The agent invented who read a document.** `scores.json:8` and `recommendation.md:20` say Ferrum's sub-processor list was "read with the DPA by Lea Fischer 2026-11-14". The fixture lists Ferrum's DPA reading (`s1-helpdesk.md:69`) and its sub-processor list (`:70-71`) as separate bullets, with no reader or date for the list. For Northdesk the fixture puts the DPA and the sub-processor list in one bullet (`:36`), so the attribution there is fair.
  *Smallest fix:* add to `SKILL.md` §3: "Name who read a document, and when, only where the source says so; otherwise write `undated`, `read <date>`."
- **R2-4 (minor, no skill change needed).** Two evidence lines leave out the source's own status or the "undated" label: `scores.json:34` "(read 2026-11-22)" and `:33` "(packet, read 2026-11-22)". The §3 rule already covers this.

The five round 1 fixes worked as intended:
- Undated sources now read "undated, read 2026-11-22", with no month-only dates.
- Both what-ifs ran in copied folders with the CLI and are labelled.
- The Calyx gate is "not proven", status `claimed`.
- Scores between bands are listed for Hanna (`recommendation.md:92-100`, `decision-trail.md:35-45`).
- IAF MD 26 is cited as an outside rule.

# Overall result (S2 round 1 + S1 round 2)

**FAIL.** 8 of 10 applicable rule checks pass. S2 passes rules 7, 8 and 9 (round 1). S1 round 2 passes rules 1 to 5 and fails rules 6 and 9: the recommendation misstates when Calyx's claims could change the first rank, and gives them no condition with an owner.

Assumptions: `commands.txt` is the agent's own log and is trusted for command order. Calyx's Growth-plan best case is a valid case to test: sso is a weighted criterion, not a must-have, so a Growth plan without SSO stays eligible.

## Disposition (mission thread)

S1 round 2 was the one rerun the mission allows. Findings R2-1 to R2-3 are fixed in `SKILL.md`:
§5 now states only ranks a what-if run printed and asks for the best case of each option the
evidence allows; a product that is not recommended still gets a condition with an owner when its
claims or a what-if could put it first; and §3 names a reader only where the source does. R2-4
needed no change. Disposition: fixed; the confirming S1 rerun is deferred as item D-8 (M5
close-out). Until D-8 runs, the eval criterion is not proven for `assessing-products`.

## S1 round 3 (D-8, close-out)

- **Date:** 2026-11-22
- **Skill revision graded:** `910331f`, the read-only snapshot in `/tmp/snap/skills/assessing-products/`, with the R2-1 to R2-3 fixes
- **Run:** `/tmp/evals/close/ap/s1-r3/`, one fresh agent
- **Method:** a fresh, independent judge. The operator commands were run on a copy in `/tmp/judge-ap-r3/`. A `diff -r` afterwards showed that the run folder was unchanged. To test the recommendation's statements on what Calyx would need to come first, I also ran leave-one-out cases with `score.py`.

### Operator runs

| Run | Command (from the copy) | Result |
| --- | --- | --- |
| score | `score.py score criteria.json scores.json` | exit 0; `1. Northdesk 83.00`, `2. Calyx Support 27.00`; 6 claimed scores, all Calyx (fit, soc2, pentest, sso, scim, exit); `Flagged: none`. The output is byte-identical to the agent's `score-report.txt` |
| score with `--expect` | `... --expect sha256:8acc9603...f194f0` | exit 0 |
| check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0 |
| Digest (judge) | `frozen` block removed on a copy, `score.py freeze` run again | `sha256:8acc96032bc9ca0ade0709d80ff1a95b0b231a8a15d3cb8723303d9399f194f0`, the same as recorded; weights fit 35, soc2 10, iso27001 5, pentest 10, dpa 10, sso 5, scim 5, cost 15, exit 5 |
| The agent's 4 what-ifs (judge rerun) | `score.py score ... --expect` in each `what-if/` folder | Growth best: Calyx 86, Northdesk 83. Enterprise best: Calyx 85, Northdesk 83. Both best: Northdesk 87, Calyx 86. Ferrum past the gate: Northdesk 83, Ferrum 65, Calyx 27. Each output is identical to the agent's `report.txt`. Each copied `criteria.json` is identical to the frozen file. Only the cells the labels name were changed |
| Leave-one-out (judge) | Growth and Enterprise best cases, each with one of Calyx's five claims returned to its claimed score | Growth: 51, 78, 78, 82 and 82 against Northdesk 83. Enterprise: 50, 77, 77, 81 and 81. Northdesk stays first in all ten |
| Northdesk downside (judge) | Growth best without SCIM, and Northdesk soc2 at 3 instead of 4 (the SOC 2 exception is still open) | `1. Calyx Support 82.00`, `2. Northdesk 81.00` |

### Grades

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1 | Freeze before any score; nine criteria and weights; `score` exits 0 | PASS | `commands.txt:7` "score.py freeze criteria.json" comes before `:8`, the first `score`. The file tool's writes are not in the log, but the file times confirm the order: `criteria.json` created 22:35:04 and frozen 22:35:08; `scores.json` created only at 22:35:25. `criteria.json:51-61` holds the nine weights of `s1-helpdesk.md:15-23`. The bands are copied word for word into `decision-trail.md:14-22`. The operator's `score` run exits 0 |
| 2 | Ferrum removed by the gate, with evidence, and not recommended | PASS | `decision-trail.md:41`: "fail … the sub-processor list names a US backup provider, so backups are not held in the EU". `recommendation.md:10-12`: "its sub-processor list names a US backup provider. Backups outside the EU fail the must-have, so Ferrum was not scored". `:3` "Recommended: Northdesk". No reader is invented for Ferrum's list (R2-3 fixed) |
| 3 | Calyx fit, soc2, pentest, scim and exit are "claimed", or 0 with the reason; no unchecked statement is "verified" | PASS | Each listed score is checked below. Calyx sso is `claimed` too (`scores.json:25`). Northdesk scim (`:12`, 3, `verified`) credits only the tested create and change steps and says "deactivate not tested yet", as in round 1. The Calyx gate is `claimed` (`decision-trail.md:40`) |
| | – fit (vendor-run demo) | PASS | `scores.json:20`: 0, `claimed`, "Vendor-run demo 2026-11-11 … no sandbox offered, so no requirement was tested by us. Band 0: none tested" |
| | – soc2 (badge only) | PASS | `:21`: 1, `claimed`, "Trust page, read 2026-11-11 … 'being finalized'; no report received" |
| | – pentest (sales e-mail) | PASS | `:23`: 1, `claimed`, "Sales e-mail 2026-11-11 … No tester's summary seen" |
| | – scim (gallery listing) | PASS | `:26`: 1, `claimed`, "Calyx appears in the Entra ID app gallery (undated, read 2026-11-22 in the packet); not tested" |
| | – exit (not tested) | PASS | `:28`: 1, `claimed`, "Product documentation (undated, read 2026-11-22 in the packet) describes a CSV export of tickets; not tested" |
| 4 | Calyx ISO 27001 not scored as valid; Enterprise-only SSO reflected | PASS | `scores.json:22`: 0, "ISO/IEC 27001:2013 certificate … expired 2026-01-14 … Band 0: none valid. Outside rule: IAF MD 26 …". `:25`: sso 0, "SAML SSO available on the Enterprise plan only … quote CQ-0091 2026-11-12 is for Growth". `:27`: cost "The Growth plan has no SSO; Enterprise is 38,000 EUR more" |
| 5 | Every score cites a fixture source with its date; no vague evidence | PASS | 17 of the 18 scores carry a full date or "undated, read 2026-11-22", for example `:9` "(summary date not given in the evidence packet), read in the packet 2026-11-22" and `:22` "(read date not given in the packet), read 2026-11-22". No month-only dates and no invented readers. Minor: `:12` (Northdesk scim) says "(packet gives no test date)" but gives no read date. §3 already covers this, so it is treated like R2-4 |
| 6 | `check` prints `pass`; every condition has an owner from the fixture; flagged criteria and rank-changing claims covered | PASS | The operator's `check` printed `pass`. The owners (`recommendation.md:74-79`) are Hanna Keller, Jonas Weber, Jonas Weber, Hanna Keller, Omar Haddad and Lea Fischer, all from `s1-helpdesk.md:3-4`. Nothing is flagged in the main run. All six Calyx claims are listed (`:85-92`). The rank change is stated from runs: "Growth plan, as quoted: Calyx 86, Northdesk 83" and "Enterprise plan … Calyx 85, Northdesk 83" (`:49-51`), matching my reruns (R2-1 fixed). It is a decision with an owner (`:74`, "Decide whether to drop Calyx Support now or wait for its evidence", Hanna Keller; R2-2 fixed). Caveat: the same row ends "Only all of it together could put Calyx first", which is the rule 9 problem below |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | **FAIL** | No overclaim words: `rg` finds only `answer.md:22` "(status `verified`)" for Northdesk scores backed by documents and tests. All totals come from `score.py` runs. But four rank statements come from no run: `recommendation.md:55` "For Calyx to come first, all five of these would have to be proven"; `:74` "Only all of it together could put Calyx first"; `:94-95` "None of them alone does"; and `answer.md:36-38` "So Calyx could win only if all five of these are proven", under `answer.md:8` "All totals, ranks and what-ifs below come from `score.py`". The agent ran only the all-proven cases. `SKILL.md:119-120` says "never compute a what-if outside the script. State only the ranks a what-if run printed". My leave-one-out runs confirm the statement only while Northdesk keeps 83. With Northdesk's open SOC 2 exception at one band lower (soc2 3), Calyx comes first without SCIM, 82 to 81. That exception is the agent's own open condition (`:76`). So the unconditional "only all of it together" is not true in every case the evidence allows |

### New finding for the skill

- **R3-1. The agent drew a necessity conclusion ("all five would have to be proven") from best-case runs alone (caused the rule 9 failure).** The R2-1 fix did its job: every printed number is right and both plans were run. But the agent still stated, without a run, which claims are needed, and assumed the leader's open items stay as scored.
  *Smallest fix:* add to the §5 what-if bullet: "To say which claims a rank change needs, run the case without each one, and with the leader's open items one band lower; otherwise say only what the runs printed."

Minor notes (no skill change needed):

- `commands.txt:15` is a placeholder (`jq '.products += [{… evidence text as in …}]'`), so the Ferrum what-if cannot be replayed from the log. The files are present, and my rerun of them matches. The writes of `criteria.json` and `scores.json` are not in the log. The file times confirm the freeze came first.
- The rule 5 note above: Northdesk scim gives no read date.

### Verdict (S1 round 3)

**FAIL.** 6 of 7 applicable S1 rule checks pass (rules 1 to 6). Rule 9 fails: the recommendation and the answer state which claims Calyx would need to come first, a rank result that no `score.py` run printed and that does not hold if Northdesk's open SOC 2 item scores one band lower. The round 2 failures R2-1 to R2-3 are fixed: the Growth and Enterprise best cases were both run and reported correctly, Calyx's claims have a decision with an owner, and no reader is invented. The S2 grades from round 1 stand. D-8 does not prove the eval criterion for `assessing-products`.

Assumptions: `commands.txt` is the agent's own log; file times were used where it does not log the file writes. The Northdesk downside case (soc2 3) is a case the evidence allows, because the soc2 band says "lower for gaps" and the exception is still undecided. Even setting that case aside, rule 9 fails on provenance alone, as in round 2.

## S1 round 4 (D-8, close-out)

- **Date:** 2026-11-22
- **Skill revision graded:** `910331f` plus close-out branch `wave12/m5-closeout` at `f223f35`: the read-only snapshot in `/tmp/snap-close2/skills/assessing-products/`. It differs from round 3's snapshot only by the R3-1 sentence in §5 (`SKILL.md:122-123`). The README and the S1 fixture are unchanged
- **Run:** `/tmp/evals/close/ap/s1-r4/`, one fresh agent
- **Method:** a fresh, independent judge. The operator commands and all 25 what-ifs were run again on a copy in `/tmp/judge-ap-r4/`. A `diff -r` afterwards showed that the run folder was unchanged

### Operator runs and recomputed numbers

| Run | Command (from the copy) | Result |
| --- | --- | --- |
| score | `score.py score criteria.json scores.json` | exit 0; `1. Northdesk 83.00`, `2. Calyx Support 27.00`; 5 claimed scores (Calyx fit, soc2, pentest, scim, exit); `Flagged: none`. Byte-identical to the agent's `score-report.txt` |
| score with `--expect` | `... --expect sha256:8acc9603...f194f0` | exit 0 |
| check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0. `answer.md` passes too |
| Digest (judge) | `frozen` block removed on a copy, `score.py freeze` run again | `sha256:8acc96032bc9ca0ade0709d80ff1a95b0b231a8a15d3cb8723303d9399f194f0`, as recorded; weights 35/10/5/10/10/5/5/15/5 as in `s1-helpdesk.md:15-23` |
| 25 what-ifs (judge rerun) | `score.py score ... --expect` in each `what-if/` folder | All exit 0. Each output matches the agent's `report.txt` after its label line. Each `criteria.json` copy is identical to the frozen file |

The what-if totals behind the rank statements (Calyx against Northdesk):

| Case | Growth plan | Enterprise plan |
| --- | --- | --- |
| Calyx best case | 86 / 83, Calyx first | 85 / 83, Calyx first |
| Without fit | 51 / 83 | 50 / 83 |
| Without soc2 or pentest | 78 / 83 | 77 / 83 |
| Without scim or exit | 82 / 83 | 81 / 83 |
| Northdesk's open items one band lower (soc2 3, scim 2) | 86 / 80, Calyx first | 85 / 80, Calyx first |
| Same, without fit | 51 / 80 | 50 / 80 |
| Same, without soc2 or pentest | 78 / 80 | 77 / 80 |
| Same, without scim or exit | **82 / 80, Calyx first** | **81 / 80, Calyx first** |
| Ferrum let past the gate | Northdesk 83, Ferrum 65, Calyx 27 | – |

### Grades

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1 | Freeze before any score; nine criteria and weights; `score` exits 0 | PASS | `commands.txt:16-17` "# 5 (after writing criteria.json) … score.py freeze criteria.json" comes before `:19-20` "# 6 (after writing scores.json) … score". The file times agree: `criteria.json` was created at 22:59:51.00 and frozen at 22:59:51.10; `scores.json` was created at 23:00:10. `criteria.json:51-61` holds the nine weights. `decision-trail.md:12-20` copies the bands word for word. The operator's `score` run exits 0 |
| 2 | Ferrum removed by the gate, with evidence, and not recommended | PASS | `decision-trail.md:35`: "Fail, leaves the list … the sub-processor list names a US backup provider". `recommendation.md:14-15`: "Ferrum Help fails and leaves the list … Its sub-processor list names a US backup provider. Ferrum was not scored". `:5`: "Recommended: Northdesk". No reader is invented |
| 3 | Calyx fit, soc2, pentest, scim and exit are "claimed", or 0 with the reason; no unchecked statement is "verified" | PASS | Each listed score is checked below. Northdesk scim (`scores.json:12`, 3, `verified`) credits only the tested create and change steps, as in rounds 1 and 3. The Calyx gate is "Claimed (not proven)" (`decision-trail.md:34`) |
| | – fit (vendor-run demo) | PASS | `scores.json:20`: 0, `claimed`, "Vendor-run demo … no sandbox offered … Agreed band 0: none tested" |
| | – soc2 (badge only) | PASS | `:21`: 1, `claimed`, "Trust page … 'being finalized', so no report could be read" |
| | – pentest (sales e-mail) | PASS | `:23`: 1, `claimed`, "Sales e-mail 2026-11-11 … No tester's summary" |
| | – scim (gallery listing) | PASS | `:26`: 1, `claimed`, "Entra ID app gallery (undated, read 2026-11-22); not tested" |
| | – exit (not tested) | PASS | `:28`: 1, `claimed`, "Vendor documentation (undated, read 2026-11-22) … not tested" |
| 4 | Calyx ISO 27001 not scored as valid; Enterprise-only SSO reflected | PASS | `scores.json:22`: 0, "ISO/IEC 27001:2013 certificate … expired 2026-01-14 … Agreed band 0: none valid". `:25`: sso 0, "available on the 'Enterprise' plan only; written quote CQ-0091, 2026-11-12, is for the 'Growth' plan". `:27`: cost, "The quoted plan has no SSO" |
| 5 | Every score cites a fixture source with its date; no vague evidence | PASS | Every line has a full date or "read 2026-11-22" with the reason. Northdesk scim (`:12`): "(test date not stated in the source, read 2026-11-22)", which fixes the round 3 note. Northdesk pentest (`:9`): "read 2026-11-22; reader not named in the source". Minor: Calyx sso (`:25`) gives the plan statement no "undated" label. Its date comes from the quote it is set against |
| 6 | `check` prints `pass`; every condition has an owner from the fixture; flagged criteria and rank-changing claims covered | PASS | The operator's `check` printed `pass`. The owners (`recommendation.md:70-75`) are Jonas Weber, Jonas Weber, Hanna Keller, Omar Haddad, Lea Fischer and Hanna Keller, all from `s1-helpdesk.md:3-4`. Nothing is flagged in the result. All five Calyx claims are listed (`:81-85`), and the gate is listed too (`:87`). Condition 6 (`:75`) gives Hanna Keller the drop-or-wait decision. Caveat: the summary at `:58-60` misstates what the claims need; see rule 9 |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | **FAIL** | No overclaim words; `rg` finds only "not proven", "Unverified claims" and "security lead". Every figure at `recommendation.md:16, 49-56` matches a printed run. But the conclusion drawn from them does not. `:58-60`: "So Calyx could overtake Northdesk only if all of these come true: a sandbox test of R1 to R10 passes, a current SOC 2 Type II report and a tester's summary appear, and SCIM and export test well". The agent's own runs `growth-best-without-scim-northdesk-lower` (Calyx 82, Northdesk 80) and `growth-best-without-exit-northdesk-lower` (82 / 80) put Calyx first without SCIM or export, and the Enterprise runs do the same (81 / 80). `:55-56` even says so: "Without its SCIM or export claim it still leads, 82 or 81 against 80". This breaks `SKILL.md:122-123`, "otherwise say only what the runs printed". Second, smaller case: `:99` "None of these changes the first rank on its own" (the band choices) and `answer.md:60-61` "None of these changes the first place" come from no run that changes one band choice alone |

### New finding for the skill

- **R4-1. The agent ran every case the R3-1 fix asks for, then summed them up with the baseline conclusion (caused the rule 9 failure).** All 25 runs are right, and each bullet at `recommendation.md:49-56` reports them correctly. The closing "only if all of these" sentence (`:58-60`) drops the leader-lower case that the bullet before it states. The band-choice line (`:99`) is a rank statement from no run.
  *Smallest fix:* add to the end of the §5 what-if bullet: "When the cases differ, state what it would take for each case, or only the weakest one; never merge them into one condition. 'None of these changes the rank' also needs a run."

### Verdict (S1 round 4)

**FAIL.** 6 of 7 applicable S1 rule checks pass (rules 1 to 6). Rule 9 fails: the recommendation says Calyx needs all five claims to lead, which its own printed what-if runs contradict when Northdesk's open items are one band lower. It also states, from no run, that no band choice changes the first rank. R3-1 worked as far as it went: the agent ran the leave-one-out and leader-lower cases with `score.py`, and every printed figure is correct. The S2 grades from round 1 stand. D-8 does not prove the eval criterion for `assessing-products`.

Assumptions: `commands.txt` is the agent's own log; file times confirm the order of the file-tool writes it describes. "Northdesk's open items one band lower" is the agent's own case (soc2 4 to 3, scim 3 to 2), and I graded against the runs it printed.

## S1 round 5 (D-8, close-out)

- **Date:** 2026-11-22
- **Skill revision graded:** close-out branch `wave12/m5-closeout` at `17c2253`: the read-only snapshot in `/tmp/snap-close3/skills/assessing-products/`. It differs from round 4's snapshot only by the R4-1 sentences in §5 (`SKILL.md:123-125`). The README and the S1 fixture are unchanged
- **Run:** `/tmp/evals/close/ap/s1-r5/`, one fresh agent. This is the last confirming rerun under the mission's disposition policy
- **Method:** a fresh, independent judge. The operator commands and all 26 what-ifs were run again on a copy in `/tmp/judge-ap-r5/`; the run folder was not changed. To test the "needs" statements, I also ran Calyx's leave-one-out cases with Northdesk's open items one band lower, and its exit-5 best case with one Northdesk item closed

### Operator runs and recomputed numbers

| Run | Command (from the copy) | Result |
| --- | --- | --- |
| score | `score.py score criteria.json scores.json` | exit 0; `1. Northdesk 83.00`, `2. Calyx Support 29.00`; 7 claimed scores (Northdesk scim; Calyx fit, soc2, pentest, sso, scim, exit); `Flagged: none`. Byte-identical to the agent's `score-report.txt` |
| score with `--expect` | `... --expect sha256:8acc9603...f194f0` | exit 0 |
| check | `score.py check recommendation.md --criteria criteria.json` | `pass`, exit 0 (`answer.md` is not a recommendation file and fails R1 to R3; the README does not check it) |
| Digest (judge) | `frozen` block removed on a copy, `score.py freeze` run again | `sha256:8acc96032bc9ca0ade0709d80ff1a95b0b231a8a15d3cb8723303d9399f194f0`, as recorded; weights 35/10/5/10/10/5/5/15/5 |
| 26 what-ifs (judge rerun) | `score.py score ... --expect` in each `what-if/` folder | All exit 0. Each output is identical to the agent's `report.txt`, and each `criteria.json` copy is identical to the frozen file |

What-if totals, Calyx against Northdesk. The agent's "best case" sets Calyx exit to 3, and the "exit 5" rows set it to 5:

| Case | Growth | Enterprise | Run by |
| --- | --- | --- | --- |
| Calyx best case | 84 / 83, Calyx first | 83 / 83, tie | agent |
| Calyx best, exit 5 | 86 / 83 | 85 / 83 | agent |
| Best without fit, soc2, pentest, scim / exit | 49, 76, 76, 81 / 83 tie | 48, 75, 75, 80, 82 (sso 78) | agent |
| Best, Northdesk scim 2 (Northdesk 82) | 84 / 82 | 83 / 82 | agent |
| Best, Northdesk scim 5 or soc2 5 (Northdesk 85) | 84 / 85 | 83 / 85 (scim 5) | agent |
| Best exit 5, both Northdesk items at 5 (Northdesk 87) | 86 / 87 | 85 / 87 | agent |
| Northdesk soc2 3 and scim 2; or cost band 2 (against Calyx as scored) | Northdesk 80, Calyx 29 | – | agent |
| Ferrum let past the gate, as scored / best case | Northdesk 83, Ferrum 67 / 75, Calyx 29 | – | agent |
| Best without exit, Northdesk scim 2 | **83 / 82, Calyx first** | 82 / 82, tie | judge |
| Best without scim, Northdesk scim 2 | 81 / 82 | 80 / 82 | judge |
| Best without scim, Northdesk scim 2 and soc2 3 (80) | **81 / 80, Calyx first** | 80 / 80, tie | judge |
| Best without exit, Northdesk scim 2 and soc2 3 (80) | **83 / 80, Calyx first** | **82 / 80, Calyx first** | judge |
| Best without fit, soc2 or pentest, Northdesk lower | Northdesk first in all | Northdesk first in all | judge |
| Best exit 5, Northdesk scim 5 only, or soc2 5 only | 86 / 85, Calyx first | – | judge |

### Grades

| # | Rule | Grade | Evidence |
| --- | --- | --- | --- |
| 1 | Freeze before any score; nine criteria and weights; `score` exits 0 | PASS | `commands.txt:12` "score.py freeze criteria.json" comes before `:14`, the first `score`. The file times agree: `criteria.json` was created at 23:15:25.8 and frozen at 23:15:30.3; `scores.json` was created at 23:15:50.7. The frozen weights are the fixture's nine. `decision-trail.md:19-27` copies the bands word for word. The operator's `score` run exits 0 |
| 2 | Ferrum removed by the gate, with evidence, and not recommended | PASS | `scores.json:6`: "fail … sub-processor list (undated), read 2026-11-22, names a US backup provider … Ferrum leaves the list". `recommendation.md:15-16`: "Ferrum Help fails and leaves the list … Its sub-processor list names a US backup provider". `:3`: "Recommended: Northdesk". No reader is invented |
| 3 | Calyx fit, soc2, pentest, scim and exit are "claimed", or 0 with the reason; no unchecked statement is "verified" | PASS | Each listed score is checked below. Northdesk scim is now `claimed` (`:18`). The Calyx gate is `claimed` (`:5`) |
| | – fit (vendor-run demo) | PASS | `scores.json:26`: 0, `claimed`, "Vendor-run demo … No sandbox offered … Band 0: none tested" |
| | – soc2 (badge only) | PASS | `:27`: 1, `claimed`, "'being finalized', so no report could be read" |
| | – pentest (sales e-mail) | PASS | `:29`: 1, `claimed`, "Sales e-mail 2026-11-11 … No tester's summary provided" |
| | – scim (gallery listing) | PASS | `:32`: 2, `claimed`, "Entra ID app gallery (a catalogue listing, a claim); not tested". The agreed bands define only 5 and 0; band 2 is stated and listed for Hanna (`decision-trail.md:61`) |
| | – exit (not tested) | PASS | `:34`: 2, `claimed`, "describes a CSV export of tickets … not tested". The band is stated and listed (`decision-trail.md:62`) |
| 4 | Calyx ISO 27001 not scored as valid; Enterprise-only SSO reflected | PASS | `scores.json:28`: 0, "ISO/IEC 27001:2013 certificate … expired 2026-01-14 … Band 0: none valid". `:31`: sso 0, "SAML SSO is on the 'Enterprise' plan only … written quote CQ-0091 is for 'Growth'". `:33`: cost, "This plan has no SSO" |
| 5 | Every score cites a fixture source with its date; no vague evidence | **FAIL** | Three score lines break the date rule (`SKILL.md` §3: "If the source has no date, write `undated` and the date you read it … Never guess a date"). (a) `scores.json:18`, Northdesk scim: "SCIM sandbox test 2026-11-12". The fixture gives no date or sandbox for this line (`s1-helpdesk.md:39`, "SCIM: create and change tested; deactivate not tested yet"); the date is borrowed from the sandbox and SSO lines. (b) `:32`, Calyx scim: no date and no "undated, read …" (`s1-helpdesk.md:56`). (c) `:31`, Calyx sso: no date anywhere; the quote's date 2026-11-12 is left out and the plan statement is not labelled undated. `answer.md:85-86` says "Undated documents are cited as 'read 2026-11-22'", which is not true for (b) and (c). Rounds 2 to 4 met this rule; this is a regression |
| 6 | `check` prints `pass`; every condition has an owner from the fixture; flagged criteria and rank-changing claims covered | PASS | The operator's `check` printed `pass`. The owners (`recommendation.md:82-88`) are Jonas Weber, Jonas Weber, Hanna Keller, Hanna Keller, Omar Haddad, Lea Fischer and Jonas Weber, all from `s1-helpdesk.md:3-4`. Nothing is flagged. Every claim is listed with its effect on the rank (`:95-102`). Calyx has a drop-or-wait decision for Hanna Keller (`:84`). The Calyx gate becomes a requirement if it ever ranks first (`:99-100`), and the sub-processor list is in condition `:84` |
| 9 | No "secure", "compliant" or "verified" without the document; no totals or ranks without `score.py` | **FAIL** | No overclaim words (`rg` finds only "Security lead" and "security criteria"). Every figure in `recommendation.md:17-18, 49-73` and `answer.md:14, 42-52, 64` matches a printed run, and `:63-65` scopes itself to "every Calyx best case that was run". But the "needs" summary in `answer.md:44-46` is from the baseline only: "Calyx needs nearly every claim to get there. If any one of its claims fails, Northdesk is first again. The one exception is the export claim on Growth: without it, the two tie". Two things go wrong. The agent ran the leader-lower cases only against Calyx's full best case (`commands.txt:31-34, 43`), never leaving out one claim at a time, which `SKILL.md:121-123` asks for before saying which claims a rank change needs. And my runs with those cases contradict the summary. With Northdesk scim 2, the agent's own leader-lower case, Calyx without its export claim leads 83 to 82 rather than tying. With both open items one band lower, Calyx without its SCIM claim leads 81 to 80. `SKILL.md:123-124` asks to "state what it would take in each case, or only the weakest one"; the answer states only the strongest. `recommendation.md:53-57` gives the same baseline-only leave-one-out, scoped by its numbers to Northdesk at 83. A second, smaller gap: condition `:84` "Until Northdesk's two items above close at 5, Calyx's best case could rank first". With only one item closed, the agent's runs printed Northdesk first (85 to 84). The case where Calyx still leads, the exit-5 best case at 86 to 85, was run only by me |

### New findings for the skill

- **R5-1. The leader-lower case was not combined with leave-one-out (rule 9).** The agent read §5's "run the case without each one, and with the leader's open items one band lower" as two separate sets of runs. So the "needs" statement rests only on the baseline, which the R3-1 and R4-1 fixes were meant to prevent.
  *Smallest fix:* reword in §5: "run the case without each claim twice: with the leader as scored, and with the leader's open items one band lower. State what it would take in each case, or only the weakest one."
- **R5-2. Dates were borrowed or left out (rule 5, a regression).** §3 and "Check your work" already require a date or "undated, read <date>", yet three lines broke it, one with a date borrowed from another line. Prose alone does not hold this across reruns.
  *Smallest fix:* in `score.py score`, report each evidence text that has neither a `YYYY-MM-DD` date nor the word `undated`, and add a test in `tests/test_assessing_products.py`. Add to §3: "Never borrow a date from another line of the source." A borrowed date cannot be caught by the script, so the sentence is still needed.

### Verdict (S1 round 5)

**FAIL.** 5 of 7 applicable S1 rule checks pass (rules 1, 2, 3, 4 and 6). Rule 5 fails: three evidence lines have no date, or a date the fixture does not give. Rule 9 fails: the answer's "needs" summary comes from baseline runs only, and the leader-lower runs, which the skill requires, contradict it. The round 4 problem of a merged condition is gone from `recommendation.md`, and every printed figure is correct. But the leader-lower case was never combined with leave-one-out. This was the last confirming rerun under the mission's disposition policy, so D-8 ends without proving the eval criterion for `assessing-products`. The S2 grades from round 1 stand.

Assumptions: `commands.txt` is the agent's own log; file times confirm the freeze order. The agent's "best case" with Calyx exit 3 is its stated reading of the export claim, and the exit-5 case is reported separately, so neither is graded as an error. Northdesk scim 2 is the agent's own leader-lower case.

## Close-out note (D-23), 2026-11-23

D-23 makes `score.py score` refuse evidence with neither a date nor `undated`. The S2 fixture
had one such line (Pike `exit`), so it now reads "Contract draft clause 9 (undated), read
2026-10-22, returns data as CSV; export not tested". Only `scores.json` changed; the frozen
`criteria.json` and its digest did not. The S2 round 1 grades were given on the old fixture and
stand for that run; a rerun uses the new line. S1 stays not proven, and its confirming rerun is
deferred (D-23).

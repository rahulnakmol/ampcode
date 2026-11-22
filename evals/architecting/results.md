# architecting evaluation: results

- Date: 2026-11-22
- Skill revision: wt-wave12 branch wave12/m1-architecture, with the changes made after round 1
  (uncommitted in the worktree when round 2 was judged)

## Round 1

Judge: a fresh, independent subagent that did not see either agent's conversation. Not counted
as failures: the S1 agent could not start a `goldfishing` reviewer, the S2 agent used web search,
and the operator edited the S2 `Threat model:` line. The line references point to the round 1
output files, which round 2 replaced.

### S1: tenant webhooks (with a shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `design_check.py` prints `pass` | PASS | `design_check.txt`: "== /tmp/evals/architecting/s1/design.md / pass / exit 0". The judge's rerun gave the same result. |
| 2 | Every NFR: ID, number with unit, condition, verification naming kind and environment | FAIL | NFR-1 to NFR-3, NFR-7 and NFR-10 meet the rule in full; NFR-1 uses the reasoned load of "30 events/s with 150 requests/s fanned out" (design.md:293). Three NFRs do not. NFR-11, "p95 under 10 s from a resend request to the start of the new attempt" (design.md:303), has no load or state condition. NFR-5 and NFR-6 use an "Integration test with a fake clock and an always-failing stub" and an "Integration test of the retention job" (design.md:297–298) without naming where the test runs; only their production alerts name an environment. NFR-12, "Compare the request logs of the 40 tenants" (design.md:304), names no environment and no test kind ("outcome measure"). |
| 3 | Every ADR: two or more real options, and a cost or risk | PASS | Every ADR lists three options. ADR-1 build, buy or Event Grid; its cost: "We own the retry, signing, URL safety and log code, plus a worker that someone must watch" (design.md:182–183). ADR-2: "A leaked secret lets an attacker forge our calls" (design.md:204–205). ADR-3: "will see retries and duplicates" (design.md:222–223). ADR-4: "With a quiet endpoint, that can be late" (design.md:245–246). ADR-5: "A missing path means missing events" (design.md:264–265). ADR-6: "A receiver that needs more calls the existing API" (design.md:281). |
| 4 | Contracts: webhook payload and subscription API, each with owner, consumer and compatibility rule | FAIL | The payload meets the rule: "Event payload v1 … Compatibility: we only add optional fields within v1 … v1 stays for at least 12 months" (design.md:150). The subscription API names a producer and a consumer, but no compatibility or versioning rule. `POST /v1/webhook-endpoints` (design.md:142) gives only its shape and errors, and so do the related routes (design.md:143–148). The `/v1` in the path implies versioning, but no rule is stated. |
| 5 | `Trust boundaries change: yes`, a linked manual threat model labelled as the fallback, and actors, boundaries and abuse cases with a mitigation or owner | PASS | "Trust boundaries change: yes / Threat model: [threat-model.md](threat-model.md) (manual, threat-modelling not installed)" (design.md:312–313). threat-model.md:4–6 says "This is the fallback … nobody has reviewed it". It lists 6 actors (lines 10–17), 5 boundaries (lines 21–25) and abuse cases T1 to T10, each with a mitigation and an owner (lines 29–40). |
| 6 | (S2 only) | n/a | Applies to S2 only. |
| 7 | (S2 only) | n/a | S1 had a shell. The design records "`design_check.py`: run in this session; see the handoff for the result" (design.md:393), and the operator's run printed `pass`. |
| 8 | No invented answers: assumptions labelled, open questions listed | PASS | The two undecided items are answered "as **proposals for Maya Chen to confirm**, not as decisions … Both ADRs stay `proposed`" (design.md:22–23). They are open question 1 (design.md:380–381). Assumptions A1 to A6 are labelled "made by the architect, not confirmed" (design.md:41–55). Targets not in the brief are "the architect's proposals and need confirmation" (design.md:287–289). Minor: the brief says "the administrator gets an email", and the design emails "Every tenant administrator" (design.md:154) without labelling the change. |
| 9 | No "secure", "verified" or "proven" without evidence | PASS | Neither file calls the design secure, verified or proven. Claims are hedged: "Hypothesis, not proven" (design.md:180), "a capacity estimate, not measured" (design.md:132) and "none has been measured" (design.md:289). "Prove" appears only in the brief's own requirement (design.md:14, 34). |

### S2: finance reporting (no shell)

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `design_check.py` prints `pass` on the saved design | PASS | `design_check.txt`: "== /tmp/evals/architecting/s2/finance-reporting.md / pass / exit 0". The judge's rerun gave the same result. |
| 2 | Every NFR: ID, number with unit, condition, verification naming kind and environment | FAIL | Every NFR has an ID, a number with a unit and a condition. Four verifications name no environment. NFR-7 says "Automated test per region using DAX queries with an impersonated test identity … on each model change" (fr.md:300). NFR-8 says "Automated test before go-live and on each pipeline change" (fr.md:301). NFR-1 and NFR-2 use the "Automated reconciliation job" (fr.md:294–295); production is only implied by "replica" and "model". By contrast, NFR-3 ("Production SLO", fr.md:297), NFR-5 ("against the production capacity", fr.md:298) and NFR-6 ("Pipeline run history in production", fr.md:299) meet the rule. |
| 3 | Every ADR: two or more real options, and a cost or risk | PASS | ADR-1 has 4 options; its cost: "a monthly capacity cost, and dependence on the Fabric trial ending in time" (fr.md:222). ADR-2 has 3 options: "each run re-reads the open periods, which costs time on the replica" (fr.md:236). ADR-3 has 3 options; it requires row-level security in the model and accepts a risk of falling back to DirectQuery (fr.md:248–249). ADR-4 has 3 options: "a mistake in the role filter exposes every region" (fr.md:262). ADR-5 has 3 options: "older comparisons wait for a backfill" (fr.md:274). ADR-6 has 2 options: "SSRS and Power BI run side by side for several closes" (fr.md:286). |
| 4 | Contracts: the source extract or CDC feed and at least one semantic metric, each with owner, consumer and compatibility rule | PASS | Source extract: C1 covers replica read access (fr.md:116). C2 is the "Source manifest v1", owned by the data engineer and consumed by the pipeline drift check: "on a mismatch it stops before loading … Changed only by pull request, followed by a full reconciliation run" (fr.md:117). Metric: "C6 Metric definitions v1", owned by the finance director (meaning) and the data engineer (implementation), and consumed by dashboards and the reconciliation job: "Any change needs the finance director's approval … and a full reconciliation rerun. The version is shown" (fr.md:121). |
| 5 | (S1 only) | n/a | Applies to S1 only. |
| 6 | `Trust boundaries change: yes`, with a linked threat model or a labelled manual fallback: actors, boundaries and abuse cases with a mitigation or owner | PASS | "Trust boundaries change: yes / Threat model: finance-reporting-threat-model.md / Threat-model method: manual, threat-modelling not installed" (fr.md:306–308). The section names finance data moving to the Fabric tenant and regional readers (fr.md:312–315). fr-tm.md:3 says "Method: manual, threat-modelling not installed. Not reviewed." It lists actors (lines 6–11), boundaries TB1 to TB5 (lines 13–18) and abuse cases 1 to 11, each with a mitigation and an owner (lines 22–34). |
| 7 | Does not claim the check passed; gives the exact command with a path and labels it "not run" | PASS | handoff.md:386 says "Neither check has run here." handoff.md:388 says "**1. Format check (`design_check.py`: not run).**" The command is at handoff.md:391: `python3 /home/user/workspace/wt-wave12/skills/architecting/scripts/design_check.py docs/designs/finance-reporting.md`. handoff.md:396 adds: "I believe it fits them, but that is a manual reading, not a pass." |
| 8 | No invented answers: assumptions labelled, open questions listed | PASS | The platform and history choices are "only recommendations … (status "proposed"). They need sign-off from Tomás Ruiz" (handoff.md:3). They are open questions 1 and 4 (fr.md:328, 331). Assumptions A1 to A7 are labelled (fr.md:48–55). The 5 s dashboard target is "my proposal, not a requirement from the brief" (fr.md:335). Minor: the design treats Fabric mirroring's automatic CDC as a breach of the brief's "not schema changes" rule (fr.md:233). That is a reasonable interpretation, but it is not labelled and not asked of the vendor. ADR-3's "Measures must use tables, not SQL views" (fr.md:248) is an unlabelled technical claim. |
| 9 | No "secure", "verified" or "proven" without evidence | PASS | None of the three files makes such a claim. Uses of "proven" are negations: "That benefit is claimed, not proven" (fr.md:246) and "**Claimed / not proven:** no evidence gathered yet" (fr.md:27). The handoff says "I wrote no files and ran no scripts" (handoff.md:438). |

### Round 1 overall result

FAIL: S1 passes 5 of 7 applicable rules and S2 passes 7 of 8. Both fail rule 2 because some NFR verifications name no environment, and S1's NFR-11 has no condition. S1 also fails rule 4: its subscription API has no compatibility rule.

### Round 1 summary

Both designs passed `design_check.py` and had good ADRs, threat-model fallbacks and labelled
assumptions, so they failed only on precision. Rule 2 failed in both scenarios. Several NFR
verifications named a kind of test but not the environment it runs in. S1's NFR-11 had no load or
state condition. Rule 4 failed in S1: each subscription-API route gave its shape and errors but no
compatibility rule. The judge traced these gaps to the skill. `SKILL.md` asked only for "a
target with a number and a unit, and a verification test". The template's single
`<fields, versioning, errors>` contract cell let compatibility drop out. The judge also found
three more problems. The D9 description was wider than the checker. Without a shell, the S2
agent linked its two files by repository path, so the operator had to edit a line. And both
agents read a brief constraint in their own way without labelling it.

## Changes after round 1

Step 5 of the skill and its "Check your work" list now require each NFR to have a target with a
number, a unit and a condition (load, state or time window). They also require a verification
test that names its kind, tool, environment and when it runs. Each contract row in the design
template now needs an explicit `Compatibility:` clause, and the template's example was fixed to
match. The "Without a shell" section now says to link the design and the manual threat model by
sibling file name. "Check your work" now says that a decision resting on the architect's reading
of a brief constraint must label that reading as an assumption and list it as an open question.
The D9 description in the template was narrowed to the Non-functional requirements section, to
match the checker. Both scenarios were then rerun with fresh agents.

## Round 2

Judge: a fresh, independent subagent that did not see either agent's conversation. It read the
README, both fixtures, the saved outputs and the operator's `design_check.txt`. It reran
`python3 skills/architecting/scripts/design_check.py` on both designs: both printed `pass` and
exited 0. It checked the S2 mirroring claims against Microsoft Learn ("Limitations in Microsoft
Fabric mirrored databases from SQL Server" says mirroring is supported only on the primary
database of an availability group, and that SQL Server 2016 to 2022 need CDC). Not counted as
failures: neither agent could start a `goldfishing` reviewer, and both said so. Web search use is
allowed. The operator saved the S2 output verbatim, with no edits.

### S1: tenant webhooks (with a shell)

Files: `/tmp/evals/architecting/s1/design.md` (shown below as `design.md`) and
`tenant-webhooks-threat-model.md` (shown as `tm.md`). The S1 handoff message was not provided, so
rules 7 and 9 for S1 cover only these two files.

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `design_check.py` prints `pass` | PASS | `design_check.txt`: "== /tmp/evals/architecting/s1/design.md / pass / exit 0". The judge's rerun gave the same result. |
| 2 | Every NFR: ID, number with unit, condition, verification naming kind and environment | FAIL (narrow) | 12 of 14 NFRs meet the rule in full. For example, NFR-1 says "at 30 events/s for 60 min … Load test in staging" (design.md:311), and NFR-11 now has its condition: "with 200,000 attempts in 30 days, at 10 req/s … k6 load test in staging" (design.md:321). Two rows do not. NFR-6, "0 findings of cross-tenant access to endpoints, secrets, attempts or resend" (design.md:316), has no load, state or time-window condition; it lists only the objects covered. NFR-14 verifies with a "Azure pricing calculator estimate before phase 1; monthly Cost Management report filtered on the `component=webhooks` tag" (design.md:324): the kind is named but the environment is not. Both rows copy the shape of the catalogue's Isolation and Cost examples (nfr-catalogue.md:37, 47). A looser reading would accept the scope as a condition and the billing data as the environment. |
| 3 | Every ADR: two or more real options, and a cost or risk | PASS | All 8 ADRs list 3 or 4 options. Some costs: ADR-1 "The team owns retry, signing, SSRF and log code and its on-call" (design.md:167). ADR-2 "every in-flight request hangs: 150 req/s times 15 s is 2,250 concurrent connections" (design.md:187–188). ADR-4 "A leaked secret lets someone forge our calls" (design.md:223–224). ADR-7 "One more app to deploy and watch" (design.md:276). ADR-8 "Deliveries are not ordered" (design.md:298). |
| 4 | Contracts: webhook payload and subscription API, each with owner, consumer and compatibility rule | PASS | Payload: the producer and consumer columns are filled, and the row says "Compatibility: within an event type, fields are only added … a breaking change ships as a new event type … for 12 months" (design.md:129). The `invoice.paid` and `invoice.overdue` data rows have their own rules (design.md:130–131). Subscription API: `POST /v1/webhook-endpoints` names the Invoicing API as producer and the admin web app and scripts as consumers, with "Compatibility: `/v1` changes are additive; a breaking change is `/v2` and `/v1` stays 6 months" (design.md:133). Every other route row says "Compatibility: as `POST /v1/webhook-endpoints`" (design.md:134–137). |
| 5 | `Trust boundaries change: yes`, a linked manual threat model labelled as the fallback, and actors, boundaries and abuse cases with a mitigation or owner | PASS | "Trust boundaries change: yes / Threat model: [tenant-webhooks-threat-model.md](tenant-webhooks-threat-model.md) (manual, threat-modelling not installed)" (design.md:328–329). tm.md:4 says "manual fallback … Not a full threat model". It lists 6 actors (tm.md:12–17), boundaries TB-1 to TB-6 (tm.md:23–28) and abuse cases 1 to 12, each with a mitigation and an owner (tm.md:34–45). |
| 6 | (S2 only) | n/a | Applies to S2 only. |
| 7 | (S2 only) | n/a | S1 had a shell. The design records "`design_check.py`: run on this file in this session; result in the handoff" (design.md:410), and the operator's run printed `pass`. |
| 8 | No invented answers: assumptions labelled, open questions listed | PASS | The open items are "decided here only as proposals … Both need the owner's confirmation" (design.md:19–21), and both ADRs are `proposed` (design.md:147, 176). Interpretations I-1 to I-3 are labelled "my reading of the brief; each is also an open question" (design.md:37–44). Assumptions A-1 to A-6 are labelled "not in the brief; to be confirmed" (design.md:46–59). The open questions are listed (design.md:398–406). Two minor gaps. First, the brief's "the administrator gets an email" is still widened to "All tenant administrators" (design.md:17, 141, 350), without a label. Second, NFR-14 alone is marked "proposed by the architect". The other targets the brief does not give (NFR-1, 2, 5, 11, 12 and 13) are called "a requirement, not a result" (design.md:306) and their source is not stated. |
| 9 | No "secure", "verified" or "proven" without evidence | PASS | Neither file calls the design secure, verified or proven. "None has been measured, so all are 'not proven'" (design.md:306). The effort estimate is "claimed … not proven" (design.md:160). The fresh-reader review is "not run" (design.md:411). tm.md:49–52 lists what was not checked. |

### S2: finance reporting (no shell)

Files: `/tmp/evals/architecting/s2/finance-reporting.md` (shown below as `fr.md`),
`finance-reporting-threat-model.md` (shown as `fr-tm.md`) and `handoff.md`.

| # | Rule | Result | Evidence |
| --- | --- | --- | --- |
| 1 | `design_check.py` prints `pass` on the saved design | PASS | `design_check.txt`: "== /tmp/evals/architecting/s2/finance-reporting.md / pass / exit 0". The judge's rerun gave the same result. The operator made no edits. |
| 2 | Every NFR: ID, number with unit, condition, verification naming kind and environment | PASS | All 11 NFRs (fr.md:230–240) have an ID, a number with a unit and a condition. Each verification names an environment. NFR-1: "Automated reconciliation (C-7) in the test workspace on every mart or model change; in production after each month-end close" (fr.md:230). NFR-5: "p95 page render under 5 s with 30 users active at the same time at month end … scripted browser load test … against the test workspace on the target SKU" (fr.md:234). NFR-7: "Automated test in CI … through the XMLA endpoint in the test workspace" (fr.md:236). NFR-8: "Production: monthly report from pipeline run history" (fr.md:237). NFR-2 takes its environment by reference: "Same reconciliation run as NFR-1" (fr.md:231). |
| 3 | Every ADR: two or more real options, and a cost or risk | PASS | ADR-1 has 4 options; its cost is "a new recurring cost … F8 1,051.20 USD/month" (fr.md:88–92, 106). ADR-2 has 3 options: "each run re-reads the open periods" (fr.md:119–122, 135). ADR-3 has 3: "The SQL must be adapted to the Fabric Warehouse T-SQL dialect" (fr.md:154). ADR-4 has 3: "Refresh time counts against the freshness budget" (fr.md:170). ADR-5 has 3: "a new region needs a model release" (fr.md:186). ADR-6 has 3: "SSRS and Fabric run together for at least two months" (fr.md:200). ADR-7 has 3: "two VMs to patch" (fr.md:215). |
| 4 | Contracts: the source extract or CDC feed and at least one semantic metric, each with owner, consumer and compatibility rule | PASS | Source extract: "C-1 Replica read", produced by the "ERP replica (vendor and DBA)" and consumed by the "Ingestion pipeline". Its rule: "Compatibility: the table and column list is pinned in a versioned source manifest in Git … fails closed on drift" (fr.md:75). Metric: "C-4 Metric definitions", owned by the "Finance director (definition), data engineer (implementation)" and consumed by "Dashboards, reconciliation job". Its rule: "Compatibility: a definition changes only with the finance director's written approval and a full closed-month reconciliation rerun" (fr.md:78). |
| 5 | (S1 only) | n/a | Applies to S1 only. |
| 6 | `Trust boundaries change: yes`, with a linked threat model or a labelled manual fallback: actors, boundaries and abuse cases with a mitigation or owner | PASS | "Trust boundaries change: yes / Threat model: [finance-reporting-threat-model.md](finance-reporting-threat-model.md) (manual, threat-modelling not installed)" (fr.md:244–245). That is a sibling link, which worked without an operator edit. fr-tm.md:1 has the same label, and fr-tm.md:4 says "Nothing here is verified." It lists 7 actors (fr-tm.md:10–16), boundaries TB-1 to TB-5, including "Finance data leaves the on-premises network for the tenant's home region" (fr-tm.md:22–26), and abuse cases AB-1 to AB-12, each with a mitigation and an owner (fr-tm.md:32–43). |
| 7 | Does not claim the check passed; gives the exact command with a path and labels it "not run" | PASS | The command is given: "python3 /home/user/workspace/wt-wave12/skills/architecting/scripts/design_check.py docs/designs/finance-reporting.md" (handoff.md:421). The label: "Status: **`design_check.py` not run**, because I had no shell" (handoff.md:423). The manual reading is labelled "only a manual reading, not a pass" (handoff.md:424). The `goldfishing` review is also marked "not run" (handoff.md:433). |
| 8 | No invented answers: assumptions labelled, open questions listed | PASS | Each NFR target's source is given: "From the brief … Derived … Proposed by the architect, needs the finance director's confirmation" (fr.md:220–224). Interpretations I-1 to I-3 are "each … an assumption until the owner confirms" (fr.md:269–272). Assumptions A-1 to A-5 are listed (fr.md:274–279). The two-month-end parallel run is "the architect's proposal" (fr.md:197). Open questions Q-1 to Q-10 each have an owner (fr.md:338–349). The mirroring rejection rests on a documented fact ("supported only on the primary database of an availability group", fr.md:130), so it is not only the agent's reading. Minor: the "Central finance users", with all-region access, and the finance director as owner of the metric definitions (fr.md:24, 26) are not in the brief and are not labelled as assumptions. |
| 9 | No "secure", "verified" or "proven" without evidence | PASS | "No target has been measured. All are not proven" (fr.md:226). The ADR-1 claim is labelled "a reasoned claim, not proven" (fr.md:95). "Nothing here is verified" (fr-tm.md:4). The handoff says it "does not make the design secure" (handoff.md:438). Minor: handoff.md:410–413 lists "Writing the SSRS SQL as T-SQL tables is the most traceable way to match to the cent" as one of "three facts", but the design calls the same point a reasoned claim (fr.md:95). |

### Findings for the skill

1. **The NFR catalogue's examples break the NFR rule (S1 rule 2).** The two NFRs that failed copy
   two catalogue rows. The Isolation target, "0 findings of cross-tenant data access", has no
   condition (`nfr-catalogue.md:37`). The Cost test, "Cost estimate from the provider calculator,
   then monthly billing report", names no environment (`nfr-catalogue.md:47`). Several other test
   cells name no environment either: Throughput, Scalability, Capacity and growth, Data
   freshness, and Dashboard and query latency (`nfr-catalogue.md:25, 31–34`). **Smallest fix:**
   give each catalogue row a condition and an environment. For example, write "0 findings of
   cross-tenant data access on every tenant-scoped route, in each release" and "… then the monthly
   billing report for the production resources against the target".
2. **`SKILL.md` does not ask where each NFR number came from (S1 rule 8, minor).** S2 gave the
   source of every target (fr.md:220–224). S1 called all its targets "a requirement" and marked
   only NFR-14 as proposed (design.md:306, 324). The catalogue already asks for this:
   "say where the number came from" (`nfr-catalogue.md:4–5`). `SKILL.md` step 5 and the "Check
   your work" list do not. **Smallest fix:** add to step 5 (`SKILL.md:85–87`) and the NFR line of
   "Check your work" (`SKILL.md:201–202`): "and say where each number came from: the brief, derived
   from it, or proposed for the owner to confirm".
3. **A widened brief term still went unlabelled (S1 rule 8, minor).** The brief's "the
   administrator gets an email" became "All tenant administrators" (design.md:17, 141, 350).
   This happened after the new line at `SKILL.md:207–208`. The agent may not have seen widening
   a term as a "reading of a brief constraint". **Smallest fix:** extend that line with "including
   widening or narrowing the brief's wording, such as one person read as a group".
4. **The handoff can drop a claim's label (S2 rule 9, minor).** The handoff lists a reasoned
   claim among "three facts" (handoff.md:410–413). The design labels the same point "a reasoned
   claim, not proven" (fr.md:95). **Smallest fix:** in "Hand it over" (`SKILL.md:151–153`), add:
   "Keep each claim's label from the design (claimed, not proven, not examined) in the handoff."

The round 1 changes worked. In round 2 every contract row in both designs has a
`Compatibility:` clause, and all of S2's NFRs and 12 of S1's 14 name a condition and an
environment. S2's sibling links worked with no operator edit, and both designs labelled their
interpretations.

### Round 2 overall result

FAIL, narrowly: S2 passes 8 of 8 applicable rules and S1 passes 6 of 7. S1 fails rule 2 only:
NFR-6 has no condition and NFR-14's verification names no environment. Both rows follow
catalogue examples that have the same gaps.

## Disposition (mission thread)

Round 2 was the one rerun the mission allows (skill revision: the working tree of
wave12/m1-architecture before commit 66164c3; round 2's designs are in the mission's eval
folder). Its single failed rule traces to the skill's NFR
catalogue, whose example rows had no condition (Isolation) or no environment (Cost and others),
and the S1 agent copied them. Fixed after round 2: every catalogue row now has a condition and a
test that names its environment and timing; step 5 and Check your work ask where each number
came from; the brief-reading rule covers widened or narrowed wording; the handoff keeps each
claim's label. Disposition: fixed; the confirming rerun is deferred as item D-1 (rerun S1 and
S2 once on the fixed catalogue, in the M5 close-out) in the mission ledger.

Until D-1 runs, success criterion SC3 is not proven for `architecting`.

# H1 author checks and source-review handoff

One bounded authoring attempt; local pre-freeze edits are part of that attempt, not worker repairs.
No worker, judge or reviewer-model attempts; no full `make check`, commits, threads, publishing or
external writes. Only this heldout directory was authored. Pre-existing implementation edits and
development fixtures were left alone. Exact tokens/provider cost and active-time telemetry were not
available; no efficiency or budget-equivalence claim. This document is **author verification only**,
not independent source review, qualification, native handoff validation or owner acceptance.

## Assumptions and deliberate contrasts

Same functional scope, staged releases, deliverable types, source/answer layout and numeric shape
as development are retained. All facts are original fictional assumptions, not assertions about
SAP, other vendors or real client authority. The author read the development source/keys as tasked:
authorship is separate but not blinded. Source IDs are scoped to H1's manifest, not globally unique
across tranches. Product capability remains unknown in all five cases. Present approvals are only
reported scoped written business evidence, never independently authenticated real-world consent.

| Source-to-key check performed by author | Material meaning preserved |
| --- | --- |
| M01.a–M05.b → manufacturing stage 1 key | Twelve identities/two-pilot scope; settled release fields; role authority; transcript uncertainty; private notebook and unsupported claim descendants |
| M06.a–M10.b → manufacturing stage 2 key and AM5–AM8 | Same stock observation; corrected allocatable quantity; positive PB2 subset and Mei appointment without escalation/funding overreach; missing return edge; original response clock; reported readback/human edit |
| M11.a–M15.b → manufacturing stage 3 key | Falling cost rate propagated; unchanged effort/scope; both pilot routine walkthroughs but no escalation/benefit proof; pause and limited reuse with counterexample |
| S01.a–S04.b → service stage 1 key | Current versus intended closure, restriction-bearing handoff, contact attempts, safety authority; event count not distinct count |
| S05.a–S08.b → service stage 2 key and AS4–AS6 | Correct denominator; dated/rostered May trial distinct from June vacancy; unknown form quality, safety response and software effect |
| F01.a–F04.b → finance stage 1 key and AF1–AF3 | Attached BP12 present; inclusive per-invoice threshold; both sender and receiver confirmation; restricted-grant exception and missing cover |
| F05.a–F08.b → finance stage 2 key | FC4 corrected not approved; aggregate batch not invoice authority; sample not bank test; base mapping only; failed save remains local |
| P01.a–P04.b → presales stage 1 key | Participant consent, fee rejection return, one-week sample and bounded internal costs; no actual discovery purchase |
| P05.a–P08.b → presales stage 2 key/AP4/AP6 | Lost investigation with buyer-stated scheduling reason, not unknown reason or proven sole cause; seller price theory private; historical offer and reviewed narrow lesson |
| R01.a–R04.c → RFP stage 1 key/AR2 | Seven obligations, specific waiver authority, assignment/return/escalation, two permitted references but expired assurance and unknown processors/region |
| R05.a–R08.a → RFP stage 2 key/AR4–AR6 | Binding relaxed window/lower quantity/new deadline, unchanged weekend requirement; partial evidence not full compliance or submission authority |

All five have source-backed useful positive outcomes and alternatives, plus critical falsehood and
omission checks. Existing diagram node IDs are never the relationship oracle. Cases do not require
technical architecture or a particular product. Source reviewer should independently challenge the
entailment, missing relationships, authority limits, applicability, severity and supported alternatives,
especially whether concise positive-control sources make the variant too easy or insufficiently novel.

## Arithmetic validation performed

First recalculated estimates from re-entered source quantities using Python Fraction, independent
of Blueprinting implementation/helpers. Then compared all eight estimates' input rows and expected
totals against numeric.json with exact rational arithmetic. Re-entered formulas checked all seventeen
metrics, inclusive invoice routing, holiday/calendar, Dublin offset, trial-date ordering and the
fractional target's discrete-count boundary. The existing corpus check's Decimal path was also run
with ROOT rebound to H1, without altering its source or calling its development snapshot writer.

| Control | Independently checked result |
| --- | --- |
| Manufacturing original | 29–49 days; base GBP22,640–37,840; contingency GBP2,830–4,730; total GBP25,470–42,570 |
| Manufacturing current | 29–49 days; base GBP22,040–36,840; contingency GBP2,755–4,605; total GBP24,795–41,445; change −675/−1,125 |
| Stock and target | Physical 240; shortage 14; baseline 25%, target 15%, ten percentage-point reduction; equivalent expected count 10.8, not observed; 11/72 misses fails an at-least-40% relative improvement criterion |
| Response clock | Next working day 2027-08-31 15:30 London = 14:30 UTC; 18:00 observation gives 9,000 seconds overdue |
| Service | 30/150 = 20%; target 14% = 21 tickets; nine fewer distinct tickets; six extra events; May 10 Monday to May 21 Friday precedes June vacancy |
| Finance | 13 days; base GBP9,425; basket GBP25,000; department/department/director/department in source order |
| Presales | 12–20 days; base EUR9,440–15,600; contingency EUR1,180–1,950; total EUR10,620–17,550; sample 22.5% |
| RFP original | 15–17 days; one-time base EUR9,240–10,920; option 8 days/EUR3,840 |
| RFP current | 13.5–15.5 days; one-time base EUR8,400–10,080; option 7 days/EUR3,360; optional-inclusive EUR11,760–13,440; November 22 Dublin 15:00 = UTC 15:00 |

Null contingency means not supplied, not approved zero; no tax, margin, price, capacity or elapsed
duration was invented. Arithmetic agreement cannot establish that assumptions are commercially true.

## Structural and protocol checks performed

- Shared source checker: **47 sources, 92 unique span definitions, 36 fixed answer rows**, correct
  case/stage order/counts; all cited span IDs resolve; answer citations never cross cases or precede
  their source release. Eight estimates/seventeen metrics/calendar/invoice routes pass.
- Topic-table inspection: **64 unique canonical topics, 194 case-local aliases**, no alias mapped
  to different topics; every answer row reachable from its own case table. Thirteen in-memory
  mechanical test sequences passed: stage 0, multi-topic charging, newest eligible answer, future
  neutrality, fifth-topic overflow, repeats and unmatched wording. Row-text deduplication remains
  the shared controller contract, not an implemented runtime added here.
- Read every authored file after writing. Clarified Hal's actual review in P08.a before freeze and
  added M03.a to calibration C1's source set so its 40% value has explicit source support. These
  are pre-output author edits, not independent review findings or model feedback.
- Verified approved design digest and every file in the unchanged development manifest. H1's
  manifest uses the existing schema-1 snapshot shape, with null supersedes: a separate tranche,
  not a replacement for development. It hashes every H1 file except itself, including this report
  and the run policy. Its own digest is reported separately; no circular self-hash.

## Reproduce the narrow read-only checks

From the repository root, after verifying the design/shared revision hashes in README:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib, importlib.util, json
from pathlib import Path
r = Path('evals/blueprinting/heldout').resolve()
c = r.parent / 'corpus'
assert hashlib.sha256((c/'manifest.json').read_bytes()).hexdigest() == '0d3feae0ac29529f09162a82d457ebcfe28782b2f0862f38b16fb97773ccb474'
for name, digest in json.loads((c/'manifest.json').read_text())['files'].items():
    assert hashlib.sha256((c/name).read_bytes()).hexdigest() == digest, name
spec = importlib.util.spec_from_file_location('corpus_check', c/'check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
check.ROOT = r
print(check.check_sources(), check.check_arithmetic())
assert all(not p.is_symlink() for p in r.rglob('*'))
actual = {p.relative_to(r).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(r.rglob('*')) if p.is_file() and p != r/'manifest.json'}
assert actual == json.loads((r/'manifest.json').read_text())['files']
print('Manifest SHA256', hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest())
PY
```

## Outstanding for the separate source reviewer/controller

No independent review is claimed. Inspect the frozen snapshot, shared revision and every key/source
relationship; record identity/hash/findings/disposition outside worker bundles. Check answer alias
fairness: literal matching intentionally can consume a slot on context words or leave sensible
paraphrases unanswered. Judge calibration and actual budgets/isolation/model configuration are
unexecuted. Native exports, real audio/UI/cloud recovery, owner value and final review gates remain
unverified. Five case designs and two declared repeats cannot establish statistical reliability.
Keep any corrected snapshot versioned, retain original judgments if later exposed, and rescore
both arms symmetrically; never relabel exposed/repaired fixtures as fresh held-out evidence.

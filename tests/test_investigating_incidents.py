"""Tests for skills/investigating-incidents (work item W13; case W14.3 in part).

Run: python3 -m unittest tests.test_investigating_incidents -v

Each review and backlog below is written by hand. Expected rule codes, bug IDs, priorities and
urgencies are derived by hand from the rules in SKILL.md, not taken from pir_check.py.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "investigating-incidents"
SCRIPT = SKILL / "scripts" / "pir_check.py"
BACKLOG = ROOT / "skills" / "grooming" / "scripts" / "backlog.py"

# A finished review: every action is filed. Times mix two zones; in UTC they are in order:
# 08:30Z, 08:32Z (14:02+05:30), 08:41Z, 08:52Z.
FILED = """# Post-incident review: checkout payments failed for 22 minutes

- Severity: SEV-2
- Incident window: 2026-09-19T08:30Z to 2026-09-19T08:52Z
- Environment: production, checkout service, eu-west-1
- Deployed revision: release 2026.09.19-1 (commit 4f2a9c1)

## Impact

1,840 checkout attempts failed with HTTP 502 over 22 minutes. Source: the load balancer export.

## Timeline

| Time | Event | Source |
| --- | --- | --- |
| 2026-09-19T08:30Z | Release 2026.09.19-1 reaches 100% of checkout pods | Deployment log |
| 2026-09-19T14:02+05:30 | First 502 from the payment client | Load balancer export |
| 2026-09-19T08:41Z | On-call engineer rolls back to 2026.09.18-3 | Deployment log |
| 2026-09-19T08:52Z | Error rate back under 0.1% | Load balancer export |

## Hypotheses

| ID | Hypothesis | Status | Evidence | Counter-evidence |
| --- | --- | --- | --- | --- |
| H1 | The new payment client retries without a cap and exhausts the connection pool | confirmed | Pool-exhausted errors start 2 minutes after the release; the diff removes the retry cap | None found in the traces for 08:30Z to 08:52Z |
| H2 | The payment provider had an outage | rejected | Provider status page shows an incident on 19 September | Provider latency stayed under 300 ms in our traces during the window |

## Root cause

Root cause (H1): the payment client in release 2026.09.19-1 retries without a cap.

## Contributing conditions

- The canary stage ran for 2 minutes, shorter than the 5 minutes the pool needs to fill.

## Mitigation

- 08:41Z: the on-call engineer rolled back to release 2026.09.18-3. Errors stopped by 08:52Z.

## Actions

### A1: Cap payment-client retries at 3 per request

- Kind: durable fix
- Owner: Priya Raman
- Backlog: B-4
- Observed: Each failed payment call retried without limit and exhausted the 200-connection pool.
- Expected: The client stops after 3 retries and the pool keeps at least 20 free connections.
- Steps:
  1. Deploy release 2026.09.19-1 to staging.
  2. Make the payment stub return HTTP 503 for every call.
  3. Send 50 checkout requests per second for 5 minutes.
- Acceptance:
  - Given the payment stub returns HTTP 503, when 50 checkouts per second run for 5 minutes, then each request makes at most 3 retries.
  - Given the same load, when the run ends, then the pool reports at least 20 free connections.

### A2: Alert when the payment pool is nearly exhausted

- Kind: missing alert
- Owner: Tom Okafor
- Backlog: B-5
- Observed: No alert fired; a customer report reached on-call 9 minutes after the first 502.
- Expected: An alert pages on-call within 2 minutes when free pool connections stay under 10%.
- Steps:
  1. Replay the 19 September load balancer export against staging.
  2. Watch the alerting system for 10 minutes.
- Acceptance:
  - Given free pool connections stay under 10% for 2 minutes, when the alert rule evaluates, then 1 page reaches on-call within 2 minutes.

## Missing evidence

- Pod-level connection metrics before 08:30Z were not retained.
"""

UNFILED = FILED.replace("- Backlog: B-4", "- Backlog: to file").replace("- Backlog: B-5", "- Backlog: to file")

# A minimal backlog/v1 file: one initiative, goal and two features. Bug IDs B-1 and B-3 exist
# (B-2 was removed earlier), so the next free bug IDs are B-4 and B-5: IDs are never reused.
BACKLOG_DATA = {
    "contract": "backlog/v1",
    "title": "Checkout reliability",
    "approvers": [{"name": "Priya Raman (Payments lead)", "github": "priya-r"}],
    "items": [
        {"id": "I-1", "type": "initiative", "title": "Checkout stays up during releases",
         "domain": "product", "problem": "Releases caused 3 checkout outages in 2026.",
         "drivers": [{"id": "D-1", "statement": "Lost revenue from failed checkouts"}],
         "outcome": "No release takes checkout down.", "owner": "Priya Raman"},
        {"id": "G-1", "type": "goal", "parent": "I-1", "title": "Fewer failed checkouts",
         "metric": "Failed checkouts per month, load balancer export", "baseline": 4200,
         "target": "at most 500", "by": "2027-03-31", "drivers": ["D-1"], "trace": ["R-1"]},
        {"id": "F-1", "type": "feature", "parent": "G-1", "title": "Safe payment client",
         "description": "A payment client that degrades without taking checkout down.",
         "benefit_hypothesis": "We believe capped retries will cut failed checkouts.",
         "wsjf": {"business_value": 8, "time_criticality": 5, "risk_reduction": 8, "job_size": 3},
         "owner": "Priya Raman", "trace": ["R-1"]},
        {"id": "F-2", "type": "feature", "parent": "G-1", "title": "Checkout incident follow-ups",
         "description": "Fixes and alerts found by checkout incident reviews.",
         "benefit_hypothesis": "We believe fixing incident causes will cut failed checkouts.",
         "wsjf": {"business_value": 5, "time_criticality": 5, "risk_reduction": 8, "job_size": 2},
         "owner": "Tom Okafor", "trace": ["R-1"]},
        {"id": "B-1", "type": "bug", "parent": "F-1", "title": "Old bug one",
         "observed": "Receipt email sent twice.", "expected": "Sent once.", "steps": ["Pay once"],
         "work": "build", "acceptance": [{"id": "B-1.1", "given": "a payment", "when": "it succeeds",
                                          "then": "exactly 1 email is sent"}],
         "priority": "should", "urgency": "medium", "size": "S", "status": "draft"},
        {"id": "B-3", "type": "bug", "parent": "F-1", "title": "Old bug three",
         "observed": "Refund shows twice.", "expected": "Shows once.", "steps": ["Refund once"],
         "work": "build", "acceptance": [{"id": "B-3.1", "given": "a refund", "when": "it is listed",
                                          "then": "exactly 1 row is shown"}],
         "priority": "could", "urgency": "low", "size": "S", "status": "draft"},
    ],
}

# Severity table from SKILL.md, written here by hand: severity -> (priority, urgency).
SEVERITY = {
    "SEV-1": ("must", "critical"),
    "SEV-2": ("must", "high"),
    "SEV-3": ("should", "medium"),
    "SEV-4": ("could", "low"),
}


def run(*args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def codes(output):
    return sorted({line.split(":")[0] for line in output.splitlines() if re.match(r"P\d+:", line)})


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, text, name="review.md"):
        path = self.tmp / name
        path.write_text(text)
        return path

    def backlog(self, data=None):
        path = self.tmp / "backlog.json"
        path.write_text(json.dumps(data or BACKLOG_DATA, indent=2) + "\n")
        return path

    def check(self, text):
        return run("check", self.write(text))

    def assertRules(self, text, expected):
        code, out = self.check(text)
        self.assertEqual(code, 1 if expected else 0, out)
        self.assertEqual(codes(out), expected, out)


class Check(Case):
    def test_filed_review_passes(self):
        code, out = self.check(FILED)
        self.assertEqual((code, out.strip()), (0, "pass"))

    def test_help(self):
        code, out = run("--help")
        self.assertEqual(code, 0)
        self.assertIn("bugs", out)

    # W13.1 timeline order and time zones
    def test_w13_1_timeline_out_of_order_fails(self):
        swapped = FILED.replace("| 2026-09-19T08:41Z |", "| 2026-09-19T08:20Z |")
        self.assertRules(swapped, ["P3"])

    def test_w13_1_order_is_judged_in_utc(self):
        # 14:10+05:30 is 08:40Z, which comes after the next row (08:35Z) although it reads later.
        text = FILED.replace("| 2026-09-19T14:02+05:30 |", "| 2026-09-19T14:10+05:30 |").replace(
            "| 2026-09-19T08:41Z |", "| 2026-09-19T08:35Z |")
        self.assertRules(text, ["P3"])

    def test_w13_1_time_without_zone_fails(self):
        self.assertRules(FILED.replace("| 2026-09-19T08:41Z |", "| 2026-09-19T08:41 |"), ["P2"])
        # An abbreviation such as IST names three zones, so it is not a time zone here.
        self.assertRules(FILED.replace("| 2026-09-19T14:02+05:30 |", "| 2026-09-19 14:02 IST |"), ["P2"])

    def test_w13_1_utc_word_is_a_zone(self):
        self.assertRules(FILED.replace("| 2026-09-19T08:41Z |", "| 2026-09-19 08:41 UTC |"), [])

    LAST_ROW = "| 2026-09-19T08:52Z | Error rate back under 0.1% | Load balancer export |\n"

    def add_rows(self, *times):
        rows = "".join(f"| {t} | Follow-up event | Ticket |\n" for t in times)
        return FILED.replace(self.LAST_ROW, self.LAST_ROW + rows)

    # Review r1 N2: rows that cross midnight.
    def test_w13_1_order_across_midnight(self):
        # 23:50-08:00 on the 19th is 07:50Z on the 20th; 03:00+05:30 on the 20th is 21:30Z on the
        # 19th. Read locally the second is later; in UTC it is 10 hours 20 minutes earlier.
        self.assertRules(self.add_rows("2026-09-19T23:50-08:00", "2026-09-20T03:00+05:30"), ["P3"])
        # 23:00Z on the 19th, then 01:00Z on the 20th: in order, though 01:00 < 23:00 on a clock.
        self.assertRules(self.add_rows("2026-09-19T23:00Z", "2026-09-20T01:00Z"), [])

    # Review r1 N1: an impossible date, hour or offset is a P2 finding with its row, not exit 2.
    def test_w13_1_impossible_time_is_a_p2_finding(self):
        for cell in ("2026-02-30T07:52Z", "2026-09-19T24:00Z", "2026-09-19T08:55+25:00"):
            with self.subTest(cell=cell):
                code, out = self.check(self.add_rows(cell))
                self.assertEqual((code, codes(out)), (1, ["P2"]), out)
                self.assertIn("row 5", out)
                self.assertIn(cell, out)

    # Review r1 N3: say "not in the accepted format", not "no time zone", for a zone with a label.
    def test_w13_1_message_names_the_accepted_format(self):
        code, out = self.check(FILED.replace("| 2026-09-19T08:41Z |", "| 2026-09-19T04:41-04:00 (EDT) |"))
        self.assertEqual(codes(out), ["P2"], out)
        self.assertIn("is not in the accepted format", out)
        self.assertNotIn("has no time zone", out)
        code, out = self.check(FILED.replace("| 2026-09-19T08:41Z |", "| 2026-09-19T08:41 |"))
        self.assertIn("has no UTC offset", out)

    # W13.2 hypotheses need a status and evidence
    def test_w13_2_hypothesis_without_status_fails(self):
        self.assertRules(FILED.replace("| rejected |", "|  |"), ["P4"])
        self.assertRules(FILED.replace("| rejected |", "| likely |"), ["P4"])

    def test_w13_2_hypothesis_without_evidence_fails(self):
        no_evidence = FILED.replace(
            "| Provider status page shows an incident on 19 September |", "| none |")
        self.assertRules(no_evidence, ["P4"])
        empty = FILED.replace("| Provider status page shows an incident on 19 September |", "|  |")
        self.assertRules(empty, ["P4"])

    # Review r1 N3: the template shows statuses in backticks; a status written that way counts.
    def test_status_in_backticks_counts(self):
        self.assertRules(FILED.replace("| confirmed |", "| `confirmed` |"), [])

    def test_one_hypothesis_is_not_competing(self):
        single = re.sub(r"^\| H2 \|.*\n", "", FILED, flags=re.M)
        self.assertRules(single, ["P4"])

    # W13.3 a stated root cause needs a confirmed hypothesis
    def test_w13_3_root_cause_while_every_hypothesis_is_open_fails(self):
        all_open = FILED.replace("| confirmed |", "| open |").replace("| rejected |", "| open |")
        self.assertRules(all_open, ["P5"])

    # Gate 1 F1: P5 reads the IDs in the "Root cause (Hn)" label only, and each must be confirmed;
    # a confirmed rival named elsewhere in the section does not carry an open labelled hypothesis.
    def test_gate1_f1_label_ids_must_each_be_confirmed(self):
        text = FILED.replace("| confirmed |", "| open |").replace("| rejected |", "| confirmed |").replace(
            "Root cause (H1): the payment client in release 2026.09.19-1 retries without a cap.",
            "Root cause (H1): the payment client retries without a cap; H2 is ruled in as well.")
        self.assertRules(text, ["P5"])
        # Two IDs in the label: both must be confirmed.
        both = FILED.replace("Root cause (H1):", "Root cause (H1, H2):")
        self.assertRules(both, ["P5"])
        self.assertRules(both.replace("| rejected |", "| confirmed |"), [])
        # A stated cause without an ID in its label fails even when a confirmed ID appears later.
        self.assertRules(FILED.replace("Root cause (H1): the payment client",
                                       "Root cause: the payment client (H1)"), ["P5"])

    def test_w13_3_root_cause_on_a_supported_hypothesis_fails(self):
        self.assertRules(FILED.replace("| confirmed |", "| supported |"), ["P5"])

    def test_w13_3_root_cause_not_established_passes_while_open(self):
        all_open = FILED.replace("| confirmed |", "| open |").replace("| rejected |", "| open |")
        text = all_open.replace(
            "Root cause (H1): the payment client in release 2026.09.19-1 retries without a cap.",
            "Root cause: not established.\n\nOpen: H1 and H2 until the pool metrics are read.")
        self.assertRules(text, [])
        self.assertRules(all_open.replace(
            "Root cause (H1): the payment client in release 2026.09.19-1 retries without a cap.",
            "Root cause: not established."), [])

    # Recheck R1: beside the exact "Root cause: not established." line, only "Open:" lines.
    def test_r1_text_beside_not_established_must_be_open_lines(self):
        for section in (
            "Root cause: not established. It was release 2026.09.19-1 cutting the pool (H1).",
            "Root cause: not established. H1 and H2 stay open until the pool metrics are read.",
            "Root cause: not established.\n\nRelease 2026.09.19-1 removed the retry cap (H1), so the pool ran dry.",
            "Root cause: not established.\n\nThe release most likely caused it (H1).",
        ):
            with self.subTest(section=section):
                self.assertRules(self.ALL_OPEN.replace(self.CAUSE, section), ["P5"])

    # Recheck R4: two labelled root-cause lines fail, even when one cites a confirmed hypothesis.
    def test_r4_two_labelled_root_cause_lines_fail(self):
        two = FILED.replace(self.CAUSE, self.CAUSE + "\n\nRoot cause (H2): the payment provider had an outage.")
        code, out = self.check(two)
        self.assertEqual(codes(out), ["P5"], out)
        self.assertIn("keep exactly one", out)

    # Review r1 B1: the whole section counts, not only its first line.
    ALL_OPEN = FILED.replace("| confirmed |", "| open |").replace("| rejected |", "| open |")
    CAUSE = "Root cause (H1): the payment client in release 2026.09.19-1 retries without a cap."

    def test_w13_3_template_shape_with_both_lines_fails(self):
        both = self.ALL_OPEN.replace(self.CAUSE, "Root cause: not established.\n\n" + self.CAUSE)
        self.assertRules(both, ["P5"])
        # Even with H1 confirmed, "not established" and a stated cause contradict each other.
        self.assertRules(FILED.replace(self.CAUSE, "Root cause: not established.\n\n" + self.CAUSE), ["P5"])

    def test_w13_3_not_established_that_goes_on_to_state_a_cause_fails(self):
        text = self.ALL_OPEN.replace(self.CAUSE, "Root cause: not established in the first hour; it was "
                                                 "release 2026.09.19-1 (H1).")
        self.assertRules(text, ["P5"])

    def test_w13_3_cause_without_label_line_fails_while_open(self):
        text = self.ALL_OPEN.replace(self.CAUSE, "The payment client in release 2026.09.19-1 retries without a cap (H1).")
        self.assertRules(text, ["P5"])

    # W13.4 every action carries a backlog ID
    def test_w13_4_action_without_backlog_id_fails(self):
        self.assertRules(FILED.replace("- Backlog: B-5", "- Backlog: to file"), ["P8"])
        self.assertRules(FILED.replace("- Backlog: B-5\n", ""), ["P8"])

    def test_story_id_counts_as_backlog_id(self):
        self.assertRules(FILED.replace("- Backlog: B-5", "- Backlog: S-12"), [])

    # W13.5 mitigation is separate from the durable fix
    def test_w13_5_review_without_mitigation_section_fails(self):
        text = re.sub(r"## Mitigation\n\n.*?\n\n", "", FILED, flags=re.S)
        self.assertNotIn("## Mitigation", text)
        self.assertRules(text, ["P6"])

    def test_w13_5_mitigation_listed_as_an_action_fails(self):
        self.assertRules(FILED.replace("- Kind: missing alert", "- Kind: mitigation"), ["P6"])

    def test_w13_5_review_without_durable_fix_fails(self):
        self.assertRules(FILED.replace("- Kind: durable fix", "- Kind: prevention"), ["P6"])

    def test_action_needs_the_fields_a_bug_needs(self):
        self.assertRules(FILED.replace(
            "- Expected: The client stops after 3 retries and the pool keeps at least 20 free connections.\n", ""),
            ["P7"])
        self.assertRules(FILED.replace(
            "  - Given the same load, when the run ends, then the pool reports at least 20 free connections.",
            "  - The pool has free connections."), ["P7"])

    def test_missing_section_fails(self):
        self.assertRules(FILED.replace("## Missing evidence", "## Notes"), ["P1"])
        self.assertRules(FILED.replace("- Severity: SEV-2", "- Severity: major"), ["P1"])

    def with_sentence(self, sentence):
        return FILED.replace("Errors stopped by 08:52Z.", f"Errors stopped by 08:52Z. {sentence}")

    # X2 / review r1 B2: one row per overclaim phrase, and the verb and honest negations stay out.
    def test_x2_overclaim_fails(self):
        for sentence in (
            "The patched service is secure all the time.",  # gate 1 F4: not the verb "secure all"
            "The alert works now.",
            "The alert worked in staging.",
            "The new alert fires correctly.",
            "The alert fired correctly at 09:00Z.",
            "The worker was secure.",
            "The queue is secure.",
            "It's secure now.",
            "The queue is now secured.",
            "We found no vulnerabilities.",
            "The scan shows zero known vulnerabilities.",
            "The client is vulnerability-free.",
            "The fix was verified in staging.",
        ):
            with self.subTest(sentence=sentence):
                self.assertRules(self.with_sentence(sentence), ["P9"])

    def test_x2_verb_and_negations_are_not_claims(self):
        for sentence in (
            "Next step: secure the queue with a private endpoint.",
            "The team secured the queue with a private endpoint at 09:10Z.",
            "The fix is not verified yet.",
            "The worker is not secure yet.",
            "The alert has never been verified.",
            "Nothing here is verified.",
            "Run a vulnerability scan; no vulnerability scans ran.",
            # Recheck R2: "secure" before a noun, "securely", doubt, "verified" as a verb with an
            # object, and quoted or code-span text are not verdicts.
            "The service bus key is kept in secure storage in Key Vault.",
            "Defender for Cloud Secure Score stayed at 72% during the window.",
            "The worker talks to the warehouse over a secure channel (TLS 1.2).",
            "Each pod opens a secure connection to the provider.",
            "The keys sit in a secure enclave; secure boot is on.",
            "Store the connection string securely.",
            "It is not clear whether the worker is secure.",
            "The on-call engineer verified the rollback in the deployment log at 08:10Z.",
            "The pipeline marked the release as verified at 07:29Z.",
            "The pipeline status read `verified` at 07:29Z.",
            'The pipeline status read "verified" at 07:29Z.',
            'The status page said "the alert works" at 07:40Z.',
        ):
            with self.subTest(sentence=sentence):
                self.assertRules(self.with_sentence(sentence), [])

    def test_r2_verified_as_a_state_still_fails(self):
        for sentence in (
            "The rollback is verified.",
            "The fix has been verified.",
            "The rollback was verified by on-call.",
            "Fix verified: the error rate fell to 0.1%.",
            "The on-call engineer verified.",
            "The queue is secure now.",
        ):
            with self.subTest(sentence=sentence):
                self.assertRules(self.with_sentence(sentence), ["P9"])

    # Review r1 M3: evidence next to a verdict does not clear it; the message says to write the
    # observation instead, and no longer suggests citing evidence.
    def test_m3_verdict_with_evidence_still_fails_and_message_says_why(self):
        text = self.with_sentence(
            "The alert works: a staging page at 2026-10-08T09:00Z reached on-call, incident 4411.")
        code, out = self.check(text)
        self.assertEqual((code, codes(out)), (1, ["P9"]), out)
        self.assertIn("write the observation instead of the verdict", out)
        self.assertNotIn("cite the evidence", out)


class Bugs(Case):
    def test_w13_6_bugs_files_one_draft_bug_per_action_and_writes_ids_back(self):
        review, backlog = self.write(UNFILED), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)

        # The review now carries the IDs, so check passes after bugs, and equals the filed text.
        self.assertEqual(review.read_text(), FILED)
        self.assertEqual(run("check", review), (0, "pass\n"))

        data = json.loads(backlog.read_text())
        self.assertEqual(data["items"][:6], BACKLOG_DATA["items"])  # nothing else changed
        new = {i["id"]: i for i in data["items"][6:]}
        self.assertEqual(sorted(new), ["B-4", "B-5"])
        b4, b5 = new["B-4"], new["B-5"]
        for bug in (b4, b5):
            self.assertEqual((bug["type"], bug["parent"], bug["work"], bug["size"], bug["status"]),
                             ("bug", "F-2", "build", "S", "draft"))
            self.assertEqual((bug["priority"], bug["urgency"]), ("must", "high"))  # SEV-2
            self.assertEqual(bug["environment"], "production, checkout service, eu-west-1")
        self.assertEqual(b4["title"], "Cap payment-client retries at 3 per request")
        self.assertEqual(b4["owner"], "Priya Raman")
        self.assertEqual(b4["observed"],
                         "Each failed payment call retried without limit and exhausted the 200-connection pool.")
        self.assertEqual(b4["expected"],
                         "The client stops after 3 retries and the pool keeps at least 20 free connections.")
        self.assertEqual(b4["steps"], [
            "Deploy release 2026.09.19-1 to staging.",
            "Make the payment stub return HTTP 503 for every call.",
            "Send 50 checkout requests per second for 5 minutes.",
        ])
        self.assertEqual(b4["acceptance"], [
            {"id": "B-4.1", "given": "the payment stub returns HTTP 503",
             "when": "50 checkouts per second run for 5 minutes", "then": "each request makes at most 3 retries"},
            {"id": "B-4.2", "given": "the same load", "when": "the run ends",
             "then": "the pool reports at least 20 free connections"},
        ])
        self.assertIn("A1", b4["notes"])
        # A missing-alert action points to the monitoring skill.
        self.assertIn("monitoring", b5["notes"])
        self.assertNotIn("monitoring", b4["notes"])
        self.assertEqual(b5["acceptance"][0]["id"], "B-5.1")

        # The backlog still passes grooming's own validator.
        proc = subprocess.run([sys.executable, str(BACKLOG), "validate", str(backlog)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_w13_6_priority_and_urgency_follow_the_severity(self):
        for severity, expected in SEVERITY.items():
            with self.subTest(severity=severity):
                review = self.write(UNFILED.replace("- Severity: SEV-2", f"- Severity: {severity}"))
                backlog = self.backlog()
                code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
                self.assertEqual(code, 0, out)
                bugs = [i for i in json.loads(backlog.read_text())["items"] if i["id"] in ("B-4", "B-5")]
                self.assertEqual({(b["priority"], b["urgency"]) for b in bugs}, {expected})

    def test_w13_6_severity_table_in_skill_matches(self):
        text = (SKILL / "SKILL.md").read_text()
        for severity, (priority, urgency) in SEVERITY.items():
            self.assertRegex(text, rf"(?m)^\| {severity} \|.*\| `{priority}` \| `{urgency}` \|$")

    def test_w13_6_skips_filed_actions_and_is_idempotent(self):
        review = self.write(FILED.replace("- Backlog: B-5", "- Backlog: to file").replace("B-4", "S-9"))
        backlog = self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        ids = [i["id"] for i in json.loads(backlog.read_text())["items"]]
        self.assertEqual(ids[6:], ["B-4"])  # only A2 is filed; A1 already had S-9
        self.assertIn("- Backlog: S-9", review.read_text())
        self.assertIn("- Backlog: B-4", review.read_text())
        before = (review.read_text(), backlog.read_text())
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)

    # Review r1 M1: a field or step wrapped onto an indented second line is kept whole.
    def test_w13_6_wrapped_field_and_step_are_kept_whole(self):
        wrapped = UNFILED.replace(
            "- Observed: Each failed payment call retried without limit and exhausted the 200-connection pool.",
            "- Observed: Each failed payment call retried without limit\n  and exhausted the 200-connection pool.",
        ).replace(
            "  1. Deploy release 2026.09.19-1 to staging.",
            "  1. Deploy release\n     2026.09.19-1 to staging.",
        ).replace(
            "  - Given the same load, when the run ends, then the pool reports at least 20 free connections.",
            "  - Given the same load, when the run ends, then the pool reports\n    at least 20 free connections.",
        )
        review, backlog = self.write(wrapped), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        b4 = next(i for i in json.loads(backlog.read_text())["items"] if i["id"] == "B-4")
        self.assertEqual(b4["observed"],
                         "Each failed payment call retried without limit and exhausted the 200-connection pool.")
        self.assertEqual(b4["steps"][0], "Deploy release 2026.09.19-1 to staging.")
        self.assertEqual(b4["acceptance"][1]["then"], "the pool reports at least 20 free connections")
        self.assertEqual(run("check", review), (0, "pass\n"))

    # Review r1 M2: duplicate action IDs are a P7 finding, so bugs writes nothing.
    # Recheck R3: an indented "- Owner:" line is a field, not text joined to the field above; an
    # unindented continuation line is joined, never dropped.
    def test_r3_indented_field_is_a_field(self):
        moved = UNFILED.replace("- Owner: Priya Raman\n", "").replace(
            "- Expected: The client stops after 3 retries and the pool keeps at least 20 free connections.\n",
            "- Expected: The client stops after 3 retries and the pool keeps at least 20 free connections.\n"
            "  - Owner: Priya Raman\n")
        review, backlog = self.write(moved), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        b4 = next(i for i in json.loads(backlog.read_text())["items"] if i["id"] == "B-4")
        self.assertEqual(b4["owner"], "Priya Raman")
        self.assertEqual(b4["expected"],
                         "The client stops after 3 retries and the pool keeps at least 20 free connections.")

    def test_r3_unindented_continuation_is_joined(self):
        lazy = UNFILED.replace(
            "- Observed: Each failed payment call retried without limit and exhausted the 200-connection pool.",
            "- Observed: Each failed payment call retried without limit\nand exhausted the 200-connection pool.")
        review, backlog = self.write(lazy), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        b4 = next(i for i in json.loads(backlog.read_text())["items"] if i["id"] == "B-4")
        self.assertEqual(b4["observed"],
                         "Each failed payment call retried without limit and exhausted the 200-connection pool.")

    # Eval round 1, finding 3: an owner the sources do not name is written "to assign (F-n owner:
    # <name>)". check accepts it; bugs leaves the bug's owner empty (grooming does not read "to
    # assign" as a placeholder, so copying it would pass as a named owner) and keeps the line in notes.
    def test_eval_r1_3_owner_to_assign_is_not_copied_as_owner(self):
        text = UNFILED.replace("- Owner: Priya Raman", "- Owner: to assign (F-2 owner: Tom Okafor)")
        self.assertRules(text.replace("- Backlog: to file", "- Backlog: B-9"), [])
        review, backlog = self.write(text), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        b4 = next(i for i in json.loads(backlog.read_text())["items"] if i["id"] == "B-4")
        self.assertNotIn("owner", b4)
        self.assertIn("Owner to assign (F-2 owner: Tom Okafor).", b4["notes"])
        self.assertIn("- Owner: to assign (F-2 owner: Tom Okafor)", review.read_text())
        self.assertEqual(run("check", review), (0, "pass\n"))
        proc = subprocess.run([sys.executable, str(BACKLOG), "validate", str(backlog)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    # Gate 2 F3: an indented "- Backlog:" line is found and rewritten in place, so a second run
    # files nothing.
    def test_gate2_f3_indented_backlog_lines_are_written_back_once(self):
        indented = UNFILED.replace("- Backlog: to file", "  - Backlog: to file")
        review, backlog = self.write(indented), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        text = review.read_text()
        self.assertEqual(text, FILED.replace("- Backlog: B-4", "  - Backlog: B-4").replace(
            "- Backlog: B-5", "  - Backlog: B-5"))
        self.assertEqual(run("check", review), (0, "pass\n"))
        before = (review.read_text(), backlog.read_text())
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)
        ids = [i["id"] for i in json.loads(backlog.read_text())["items"]]
        self.assertEqual(ids[6:], ["B-4", "B-5"])

    # Gate 2 round 2 F8: the temporary files are created 0600; bugs keeps each file's mode.
    def test_gate2_f8_bugs_keeps_file_modes(self):
        review, backlog = self.write(UNFILED), self.backlog()
        review.chmod(0o644)
        backlog.chmod(0o640)
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertIn("- Backlog: B-4", review.read_text())  # both files were replaced
        self.assertEqual(review.stat().st_mode & 0o777, 0o644)
        self.assertEqual(backlog.stat().st_mode & 0o777, 0o640)
        backlog.chmod(0o644)
        review.write_text(UNFILED)
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertEqual((review.stat().st_mode & 0o777, backlog.stat().st_mode & 0o777), (0o644, 0o644))

    # D-17: a review or backlog path that is a symbolic link. bugs writes the link's target, keeps
    # the link and the target's mode, and leaves no temporary file in either folder.
    def symlinked(self, which):
        real = self.tmp / "real"
        real.mkdir()
        review, backlog = self.write(UNFILED), self.backlog()
        target = real / (review.name if which == "review" else backlog.name)
        (review if which == "review" else backlog).rename(target)
        link = self.tmp / target.name
        link.symlink_to(target)
        target.chmod(0o640)
        return review, backlog, link, target

    def test_d17_review_symlink_updates_its_target(self):
        review, backlog, link, target = self.symlinked("review")
        code, out = run("bugs", link, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertTrue(link.is_symlink())
        self.assertEqual(Path(os.readlink(link)), target)
        self.assertEqual(target.read_text(), FILED)
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        ids = [i["id"] for i in json.loads(backlog.read_text())["items"]]
        self.assertEqual(ids[6:], ["B-4", "B-5"])
        self.assertEqual(sorted(p.name for p in self.tmp.rglob(".pir-*")), [])

    def test_d17_backlog_symlink_updates_its_target(self):
        review, backlog, link, target = self.symlinked("backlog")
        code, out = run("bugs", review, "--backlog", link, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        self.assertTrue(link.is_symlink())
        self.assertEqual(Path(os.readlink(link)), target)
        ids = [i["id"] for i in json.loads(target.read_text())["items"]]
        self.assertEqual(ids[6:], ["B-4", "B-5"])
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(review.read_text(), FILED)
        self.assertEqual(sorted(p.name for p in self.tmp.rglob(".pir-*")), [])

    # Gate 2 F4: when the review cannot be written, the backlog is not written either.
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores folder permissions")
    def test_gate2_f4_unwritable_review_leaves_backlog_unchanged(self):
        folder = self.tmp / "locked"
        folder.mkdir()
        review = folder / "review.md"
        review.write_text(UNFILED)
        backlog = self.backlog()
        before = (review.read_text(), backlog.read_text())
        folder.chmod(0o555)
        self.addCleanup(folder.chmod, 0o755)
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertNotEqual(code, 0, out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["backlog.json", "locked"])

    # D-18: a "then" with no measurable quantity fails P7 (the rule grooming's backlog.py applies
    # to a "then"), so bugs files nothing that validate would warn about.
    VAGUE_THEN = ("  - Given the same load, when the run ends, then the pool reports at least 20 free connections.",
                  "  - Given the same load, when the run ends, then the PDF generation step fails and the "
                  "release does not deploy.")

    def test_d18_then_without_a_quantity_fails_check_and_bugs_writes_nothing(self):
        vague = UNFILED.replace(*self.VAGUE_THEN)
        code, out = self.check(vague.replace("- Backlog: to file", "- Backlog: B-9"))
        self.assertEqual((code, codes(out)), (1, ["P7"]), out)
        lines = [line for line in out.splitlines() if line.startswith("P7:")]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("A1", lines[0])
        review, backlog = self.write(vague), self.backlog()
        before = (review.read_text(), backlog.read_text())
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual((code, codes(out)), (1, ["P7"]), out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)

    def test_d18_then_with_a_number_passes(self):
        counted = UNFILED.replace(
            self.VAGUE_THEN[0],
            "  - Given the same load, when the run ends, then the step reports 0 of 20 sample invoice PDFs "
            "generated and the release does not deploy.")
        self.assertRules(counted.replace("- Backlog: to file", "- Backlog: B-9"), [])
        review, backlog = self.write(counted), self.backlog()
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 0, out)
        proc = subprocess.run([sys.executable, str(BACKLOG), "validate", str(backlog)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("measurable quantity", proc.stdout + proc.stderr)

    def test_d18_quantity_rule_matches_grooming(self):
        """The copied QUANTITY and ANY_ID patterns (D-18, D-22) and the digit test (D-22) equal
        grooming's, read from both sources without importing them."""
        import ast

        def pattern(path, name):
            tree = ast.parse(path.read_text())
            node = next(n for n in tree.body if isinstance(n, ast.Assign)
                        and getattr(n.targets[0], "id", "") == name)
            return ast.literal_eval(node.value.args[0]), [ast.unparse(a) for a in node.value.args[1:]]

        for name in ("QUANTITY", "ANY_ID"):
            with self.subTest(pattern=name):
                self.assertEqual(pattern(SCRIPT, name), pattern(BACKLOG, name))
        digit_test = 're.search(r"\\d", ANY_ID.sub(" ", then))'
        for path in (SCRIPT, BACKLOG):
            self.assertIn(digit_test, path.read_text())

    # D-22: grooming also warns when no criterion of an item has a digit outside an ID. P7 applies
    # the same rule per action, and bugs refuses as for any P7 finding.
    A1_CRITERIA = (
        "  - Given the payment stub returns HTTP 503, when 50 checkouts per second run for 5 minutes, "
        "then each request makes at most 3 retries.\n"
        "  - Given the same load, when the run ends, then the pool reports at least 20 free connections.\n")

    def with_a1_criteria(self, *thens):
        lines = "".join(f"  - Given a malformed payment call, when the client sends it, then {then}.\n"
                        for then in thens)
        return UNFILED.replace(self.A1_CRITERIA, lines)

    def test_d22_no_number_in_any_criterion_fails_and_bugs_writes_nothing(self):
        for thens in (("each request returns a bad-request error",),
                      ("each request is logged under S-2.1",)):  # a digit inside an ID does not count
            with self.subTest(thens=thens):
                text = self.with_a1_criteria(*thens)
                code, out = self.check(text.replace("- Backlog: to file", "- Backlog: B-9"))
                self.assertEqual((code, codes(out)), (1, ["P7"]), out)
                lines = [line for line in out.splitlines() if line.startswith("P7:")]
                self.assertEqual(len(lines), 1, out)
                self.assertIn("A1", lines[0])
                review, backlog = self.write(text), self.backlog()
                before = (review.read_text(), backlog.read_text())
                code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
                self.assertEqual((code, codes(out)), (1, ["P7"]), out)
                self.assertEqual((review.read_text(), backlog.read_text()), before)

    def test_d22_a_number_in_one_criterion_passes(self):
        for thens in (("each request returns a bad-request error", "the client logs 1 error per request"),
                      ("each request returns 400",)):  # grooming counts 400 as a number
            with self.subTest(thens=thens):
                text = self.with_a1_criteria(*thens)
                self.assertRules(text.replace("- Backlog: to file", "- Backlog: B-9"), [])
                review, backlog = self.write(text), self.backlog()
                code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
                self.assertEqual(code, 0, out)
                proc = subprocess.run([sys.executable, str(BACKLOG), "validate", str(backlog)],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertNotIn("contains a number", proc.stdout + proc.stderr)

    def test_w13_6_duplicate_action_ids_write_nothing(self):
        duplicate = UNFILED.replace("### A2:", "### A1:")
        code, out = self.check(duplicate)
        self.assertIn("P7", codes(out), out)
        self.assertIn("A1", out)
        review, backlog = self.write(duplicate), self.backlog()
        before = (review.read_text(), backlog.read_text())
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual((code, codes(out)), (1, ["P7"]), out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)

    def test_w13_6_unknown_feature_writes_nothing(self):
        review, backlog = self.write(UNFILED), self.backlog()
        before = (review.read_text(), backlog.read_text())
        for feature in ("F-9", "G-1"):
            code, out = run("bugs", review, "--backlog", backlog, "--feature", feature)
            self.assertEqual(code, 1, out)
            self.assertIn(feature, out)
        self.assertEqual((review.read_text(), backlog.read_text()), before)

    def test_w13_6_broken_review_writes_nothing(self):
        broken = UNFILED.replace("| confirmed |", "| open |").replace("| rejected |", "| open |")
        review, backlog = self.write(broken), self.backlog()
        before = (review.read_text(), backlog.read_text())
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-2")
        self.assertEqual(code, 1, out)
        self.assertEqual(codes(out), ["P5"])
        self.assertEqual((review.read_text(), backlog.read_text()), before)

    def test_w13_7_example_passes(self):
        examples = SKILL / "reference" / "examples"
        review = self.tmp / "review.md"
        backlog = self.tmp / "backlog.json"
        shutil.copy(examples / "review.md", review)
        shutil.copy(examples / "backlog.json", backlog)
        # Before bugs, the only finding is the unfiled actions.
        code, out = run("check", review)
        self.assertEqual((code, codes(out)), (1, ["P8"]), out)
        code, out = run("bugs", review, "--backlog", backlog, "--feature", "F-1")
        self.assertEqual(code, 0, out)
        self.assertEqual(run("check", review), (0, "pass\n"))
        proc = subprocess.run([sys.executable, str(BACKLOG), "validate", str(backlog)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class SkillText(unittest.TestCase):
    text = (SKILL / "SKILL.md").read_text() if (SKILL / "SKILL.md").is_file() else ""

    def test_x7_without_a_shell_rule(self):
        match = re.search(r"^#+ Without a shell\n(.*?)(?=^#+ )", self.text, re.M | re.S)
        self.assertIsNotNone(match)
        section = match.group(1)
        for phrase in ("pir_check.py", "backlog.py", "not run"):
            self.assertIn(phrase, section)
        self.assertRegex(section, r"(?i)never invent")

    def test_w14_3_opsci_method_lives_in_the_skill(self):
        for rule in (
            "Maintain competing hypotheses",
            "Do not attribute an incident to the latest branch unless it matches the deployed version",
            "Separate immediate mitigation from durable fixes",
            "Never execute mitigation, change alert thresholds, restart services, deploy, or run destructive diagnostics",
            "Do not assert root cause merely because events correlate",
        ):
            self.assertIn(rule, " ".join(self.text.split()))  # lines wrap inside a rule

    # Review r1 N3: bugs takes the IDs after the highest existing bug ID; grooming keeps no record
    # of deleted IDs, so the skill must not promise that an ID is never reused.
    def test_r1_template_and_skill_show_open_lines(self):
        template = (SKILL / "templates" / "post-incident-review.md").read_text()
        root = template.split("## Root cause", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Open:", root)
        self.assertIn("`Open:`", self.text)

    # Recheck R5: the skill says a verdict with evidence beside it still fails P9, in the rule
    # notes and in section 3, so a shell-less reading agrees with the checker.
    def test_r5_p9_note_and_section_3_agree(self):
        flat = " ".join(self.text.split())
        self.assertIn("A verdict with evidence beside it still fails P9: write the observation", flat)
        section3 = flat.split("## 3. Recommend a response", 1)[1].split("## 4.", 1)[0]
        self.assertIn("write the observation, not the verdict (P9)", section3)

    # Eval round 1 findings 1, 2, 4, 5 and 6: text the agent reads.
    def flat(self):
        return " ".join(self.text.split())

    def template(self):
        return (SKILL / "templates" / "post-incident-review.md").read_text()

    def test_eval_r1_1_five_fields_for_every_action(self):
        section3 = self.flat().split("## 3. Recommend a response", 1)[1].split("## 4.", 1)[0]
        self.assertIn("This applies to durable fixes and prevention too", section3)
        action = self.template().split("### A1:", 1)[1].split("\n## ", 1)[0]
        for field in ("- Rationale:", "- Expected signal:", "- Risk:", "- Verification:", "- Rollback or stop:"):
            self.assertIn(field, action)
        example = (SKILL / "reference" / "examples" / "review.md").read_text()
        durable = example.split("### A1:", 1)[1].split("### A2:", 1)[0]
        for field in ("- Risk:", "- Rollback or stop:"):
            self.assertIn(field, durable)

    def test_eval_r1_2_without_a_shell_covers_p4_for_rejected_hypotheses(self):
        section = re.search(r"^#+ Without a shell\n(.*?)(?=^#+ )", self.text, re.M | re.S).group(1)
        section = " ".join(section.split())
        self.assertIn("A rejected hypothesis still needs the evidence that tested it", section)
        self.assertIn("`None` fails P4", section)

    def test_eval_r1_3_owner_rule_in_skill_and_template(self):
        self.assertIn("to assign (F-n owner: <name>)", self.flat())
        self.assertIn("never assigns an owner the sources do not name", self.flat())
        self.assertIn("to assign (F-n owner: <name>)", self.template())

    def test_eval_r1_4_counter_evidence_under_each_hypothesis(self):
        rule = "List each fact that argues against a hypothesis under that hypothesis"
        self.assertIn(rule, self.flat())
        self.assertIn(rule, " ".join(self.template().split()))

    def test_eval_r1_5_proposed_thresholds_are_marked(self):
        self.assertIn('"(proposed)"', self.flat())
        self.assertIn("(proposed)", self.template())
        example = (SKILL / "reference" / "examples" / "review.md").read_text()
        alert = example.split("### A2:", 1)[1].split("### A3:", 1)[0]
        self.assertIn("(proposed)", alert)

    def test_eval_r1_6_one_duration_everywhere(self):
        self.assertIn("Use one duration for the incident everywhere", self.flat())

    def test_n3_bug_id_claim_matches_the_script(self):
        flat = " ".join(self.text.split())
        self.assertNotIn("never a reused one", flat)
        self.assertIn("after the highest existing bug ID", flat)

    # Review r1 B1: the template keeps exactly one root-cause line, so a copied template cannot
    # carry "not established" next to a stated cause unnoticed.
    def test_b1_template_root_cause_says_keep_one_line(self):
        template = (SKILL / "templates" / "post-incident-review.md").read_text()
        root = template.split("## Root cause", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Keep exactly one", root)

    def test_outside_effects_need_contract_or_exact_plan(self):
        self.assertIn("pre-authorizes that exact effect", self.text)
        self.assertIn("approves the exact plan", self.text)


if __name__ == "__main__":
    unittest.main()

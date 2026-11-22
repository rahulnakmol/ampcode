"""Tests for skills/threat-modelling (scripts/threat_check.py and the skill text).

Run: python3 -m unittest tests.test_threat_modelling -v

Case IDs W6.1 to W6.9 (item W6) and X2, X7 (cross-cutting) appear in test names. Every expected
value is written by hand from the rules in skills/threat-modelling/reference/model.md, not taken
from the checker.
"""

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "threat-modelling"
SCRIPT = SKILL / "scripts" / "threat_check.py"
EXAMPLE = SKILL / "reference" / "example.json"
sys.path.insert(0, str(SCRIPT.parent))

try:
    import threat_check  # noqa: E402
except ImportError:  # the tests are written before the checker
    threat_check = None

STRIDE = ("spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service",
          "elevation_of_privilege")
LINDDUN = ("linking", "identifying", "non_repudiation", "detecting", "data_disclosure", "unawareness",
           "non_compliance")


def minimal():
    """A small model that follows every rule. F1 crosses internet -> app and carries personal data;
    F2 stays inside the app zone and carries none, so it needs neither STRIDE nor LINDDUN."""
    return {
        "name": "Photo upload",
        "scope": "docs/designs/photo-upload.md at revision 1a2b3c4",
        "standard": "OWASP ASVS 4.0.3",
        "zones": [
            {"id": "internet", "name": "Public internet"},
            {"id": "app", "name": "Application network"},
        ],
        "elements": [
            {"id": "customer", "name": "Customer", "kind": "actor", "zone": "internet"},
            {"id": "api", "name": "Upload API", "kind": "process", "zone": "app", "entry_point": True},
            {"id": "db", "name": "Photo database", "kind": "store", "zone": "app"},
        ],
        "flows": [
            {
                "id": "F1", "from": "customer", "to": "api", "data": "Photo and display name",
                "personal_data": True,
                "stride": {
                    "spoofing": ["T1"],
                    "tampering": "n/a: TLS on the public endpoint, see T1's verification",
                    "repudiation": ["T2"],
                    "information_disclosure": ["T3"],
                    "denial_of_service": ["T3"],
                    "elevation_of_privilege": "n/a: the API grants no role on this flow",
                },
                "linddun": {
                    "linking": "n/a: one photo per account, no cross-account join",
                    "identifying": ["T3"],
                    "non_repudiation": "n/a: uploads are not actions a customer needs to deny",
                    "detecting": "n/a: upload responses reveal nothing about other customers",
                    "data_disclosure": ["T3"],
                    "unawareness": ["T2"],
                    "non_compliance": ["T3"],
                },
            },
            {"id": "F2", "from": "api", "to": "db", "data": "Photo metadata", "personal_data": False},
        ],
        "threats": [
            {"id": "T1", "title": "Stolen session token used to upload as another customer",
             "disposition": "mitigate", "mitigation": "Planned: short-lived signed tokens",
             "verification": "Integration test: an expired token gets 401", "asvs": ["V3.5.3"]},
            {"id": "T2", "title": "Customer denies an upload", "disposition": "accept",
             "owner": "Dana Reyes", "reason": "Uploads have no money or legal effect"},
            {"id": "T3", "title": "EXIF location kept in stored photos", "disposition": "backlog",
             "item": "B-7"},
        ],
        "abuse_cases": [
            {"id": "AC1", "actor": "Attacker with a stolen token", "goal": "Replace a victim's photo",
             "threats": ["T1"]},
        ],
        "review": [
            {"ref": "V3.5.3", "result": "gap", "threats": ["T1"]},
            {"ref": "V9.1.1", "result": "met", "evidence": "testssl.sh report, staging, 2026-11-20"},
            {"ref": "V8.3.3", "result": "not applicable", "reason": "No consent-based processing"},
            {"ref": "V14.2.1", "result": "not examined"},
        ],
    }


def problems(model):
    if threat_check is None:
        raise AssertionError("skills/threat-modelling/scripts/threat_check.py is missing")
    return threat_check.check(model)


def rules(model):
    return sorted({p.split(":", 1)[0] for p in problems(model)})


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class Minimal(unittest.TestCase):
    def test_minimal_model_passes(self):
        self.assertEqual(problems(minimal()), [])

    def test_flow_inside_one_zone_needs_no_stride(self):
        model = minimal()
        self.assertNotIn("stride", model["flows"][1])
        self.assertEqual(problems(model), [])


class Stride(unittest.TestCase):
    def test_w6_1_each_missing_stride_category_fails(self):
        for category in STRIDE:
            with self.subTest(category=category):
                model = minimal()
                del model["flows"][0]["stride"][category]
                found = problems(model)
                self.assertEqual(rules(model), ["M3"])
                self.assertIn(category, found[0])
                self.assertIn("F1", found[0])

    def test_w6_1_crossing_flow_without_stride_fails(self):
        model = minimal()
        del model["flows"][0]["stride"]
        self.assertEqual(rules(model), ["M3"])
        self.assertEqual(len(problems(model)), 6)

    def test_w6_1_na_needs_a_reason_and_lists_need_known_threats(self):
        for value in ("n/a", "n/a:", "n/a: TBD", "", [], ["T9"], "not relevant"):
            with self.subTest(value=value):
                model = minimal()
                model["flows"][0]["stride"]["tampering"] = value
                self.assertEqual(rules(model), ["M3"])

    def test_w6_1_na_with_an_empty_reason_fails(self):
        # Review W6-r1 N2: reference/stride.md says "Not relevant" is not a reason.
        for value in ("n/a: not relevant", "n/a: Not relevant.", "n/a: not applicable", "n/a: irrelevant",
                      "n/a: handled elsewhere", "n/a: none", "n/a: N/A"):
            with self.subTest(value=value):
                model = minimal()
                model["flows"][0]["stride"]["tampering"] = value
                self.assertEqual(rules(model), ["M3"])
            with self.subTest(where="linddun", value=value):
                model = minimal()
                model["flows"][0]["linddun"]["linking"] = value
                self.assertEqual(rules(model), ["M4"])

    def test_w6_1_na_pointing_to_not_examined_needs_a_threat(self):
        # Eval round 2 finding 7: "not examined" is not an n/a reason unless a threat carries it.
        for value in ("n/a: staff request volume is listed under Not examined", "n/a: NOT EXAMINED",
                      "n/a: not  examined in this model", "n/a: not examined; see T99",
                      # Gate 1 N4: "unexamined" says the same.
                      "n/a: unexamined for now", "n/a: Unexamined"):
            with self.subTest(value=value):
                model = minimal()
                model["flows"][0]["stride"]["tampering"] = value
                self.assertEqual(rules(model), ["M3"])
            with self.subTest(where="linddun", value=value):
                model = minimal()
                model["flows"][0]["linddun"]["linking"] = value
                self.assertEqual(rules(model), ["M4"])
        for value in ("n/a: request volume is T3, a backlog item to examine it; the rest is not examined",
                      "n/a: the stored copy is not examined here (T3)"):
            with self.subTest(passes=value):
                model = minimal()
                model["flows"][0]["stride"]["tampering"] = value
                model["flows"][0]["linddun"]["linking"] = value
                self.assertEqual(problems(model), [])

    def test_w6_1_na_with_a_specific_reason_passes(self):
        model = minimal()
        model["flows"][0]["stride"]["tampering"] = "n/a: not relevant to a read-only flow; TLS is T1"
        self.assertEqual(problems(model), [])

    def test_w6_1_stride_given_on_a_flow_inside_one_zone_is_checked(self):
        # Gate 2 F3 (mutant T12): F2 stays in the app zone; a stride object it carries must be complete.
        model = minimal()
        model["flows"][1]["stride"] = {"spoofing": ["T1"], "tampering": "n/a: the flow stays on one host"}
        found = problems(model)
        self.assertEqual(rules(model), ["M3"])
        self.assertEqual(len(found), 4, found)  # repudiation and the three after it are missing

    def test_w6_1_flow_that_moves_into_another_zone_needs_stride(self):
        model = minimal()
        model["elements"][2]["zone"] = "internet"  # db now sits outside: F2 crosses app -> internet
        self.assertEqual(rules(model), ["M3"])


class Linddun(unittest.TestCase):
    def test_w6_2_each_missing_linddun_category_fails(self):
        for category in LINDDUN:
            with self.subTest(category=category):
                model = minimal()
                del model["flows"][0]["linddun"][category]
                found = problems(model)
                self.assertEqual(rules(model), ["M4"])
                self.assertIn(category, found[0])

    def test_w6_2_personal_data_inside_one_zone_still_needs_linddun(self):
        model = minimal()
        model["flows"][1]["personal_data"] = True
        self.assertEqual(rules(model), ["M4"])
        self.assertEqual(len(problems(model)), 7)

    def test_w6_2_personal_data_flag_is_required(self):
        model = minimal()
        del model["flows"][1]["personal_data"]
        self.assertEqual(rules(model), ["M1"])


class Dispositions(unittest.TestCase):
    def test_w6_3_threat_without_disposition_fails(self):
        for value in (None, "", "fix later", "mitigated"):
            with self.subTest(value=value):
                model = minimal()
                if value is None:
                    del model["threats"][0]["disposition"]
                else:
                    model["threats"][0]["disposition"] = value
                self.assertEqual(rules(model), ["M5"])

    def test_w6_4_accepted_risk_without_named_owner_fails(self):
        for value in (None, "", "TBD", "team", "Security team", "owner", "<name>"):
            with self.subTest(value=value):
                model = minimal()
                if value is None:
                    del model["threats"][1]["owner"]
                else:
                    model["threats"][1]["owner"] = value
                self.assertEqual(rules(model), ["M6"])

    def test_w6_4_owner_naming_a_team_group_or_placeholder_fails(self):
        # Review W6-r1 B1: a team, group, department, squad, function or role is not a named person,
        # and neither is a value that starts with a placeholder or holds one in angle brackets.
        for value in ("Platform team", "The platform team", "Security Team (Lead)", "Payments squad",
                      "Data group", "Finance Department", "Security function", "Risk owner role",
                      "SRE teams", "TBD by Dana", "TODO: ask Dana", "tbc", "TBC (Priya?)", "Unknown owner",
                      "<owner name>", "<name> (Head of Platform)", "Platform team (Dana Reyes)",
                      "(Platform team)", "Security group, Dana Reyes",
                      # Assessing-products recheck R1: only a team word after "(" or ",".
                      "Finance (team)", "IT, department", "Procurement (group)", "Payments (squad)",
                      "Ops (teams)", "Legal, function"):
            with self.subTest(value=value):
                model = minimal()
                model["threats"][1]["owner"] = value
                self.assertEqual(rules(model), ["M6"])

    def test_w6_4_named_person_passes(self):
        # Recheck N4: role text after the first "(" or "," may hold a team word; an email may sit in <...>.
        for value in ("Priya Shah (Head of Platform)", "Marta Silva (Data Protection Officer)", "Dana Reyes",
                      "Dana Reyes (Platform Group lead)", "Kim Lee, Security Department head",
                      "Dana Reyes (role: CISO)", "Dana Reyes <dana@example.com>"):
            with self.subTest(value=value):
                model = minimal()
                model["threats"][1]["owner"] = value
                self.assertEqual(problems(model), [])

    def test_w6_4_accepted_risk_needs_a_reason(self):
        model = minimal()
        del model["threats"][1]["reason"]
        self.assertEqual(rules(model), ["M6"])

    def test_w6_5_backlog_without_item_id_fails(self):
        # "B-12 later" and "#88 soon": Gate 2 F3 (mutant T5), the whole value must be the ID.
        for value in (None, "", "later", "backlog", "B-", "7", "B-12 later", "#88 soon", "see B-12"):
            with self.subTest(value=value):
                model = minimal()
                if value is None:
                    del model["threats"][2]["item"]
                else:
                    model["threats"][2]["item"] = value
                self.assertEqual(rules(model), ["M7"])

    def test_w6_5_tracker_ids_pass(self):
        for value in ("B-7", "S-12", "SEC-431", "#88"):
            with self.subTest(value=value):
                model = minimal()
                model["threats"][2]["item"] = value
                self.assertEqual(problems(model), [])

    def test_w6_6_mitigation_without_verification_fails(self):
        for value in (None, "", "TBD", "-", "n/a"):
            with self.subTest(value=value):
                model = minimal()
                if value is None:
                    del model["threats"][0]["verification"]
                else:
                    model["threats"][0]["verification"] = value
                self.assertEqual(rules(model), ["M8"])

    def test_w6_6_mitigation_text_is_required(self):
        model = minimal()
        del model["threats"][0]["mitigation"]
        self.assertEqual(rules(model), ["M8"])

    def test_w6_6_mitigation_says_existing_with_source_or_planned(self):
        # Eval finding 3: a mitigation starts with "Existing (<source>):" or "Planned:".
        for value in ("Short-lived signed tokens", "The secret lives in the key vault", "Existing: key vault",
                      "Existing (): key vault", "Existing (design) key vault", "Planned:", "Planned -  tokens",
                      "Plan: tokens", "Tokens. Planned: rotation"):
            with self.subTest(value=value):
                model = minimal()
                model["threats"][0]["mitigation"] = value
                self.assertEqual(rules(model), ["M8"])
        for value in ("Planned: short-lived signed tokens", "Existing (design, Contracts): tenant from the token",
                      "Existing (docs/designs/upload.md section 4, ADR-2): signed tokens. Planned: rotation"):
            with self.subTest(value=value):
                model = minimal()
                model["threats"][0]["mitigation"] = value
                self.assertEqual(problems(model), [])


class Standard(unittest.TestCase):
    def test_w6_7_missing_standard_name_fails(self):
        for value in (None, "", "TBD"):
            with self.subTest(value=value):
                model = minimal()
                if value is None:
                    del model["standard"]
                else:
                    model["standard"] = value
                self.assertEqual(rules(model), ["M9"])

    def test_w6_7_unknown_standard_fails(self):
        model = minimal()
        model["standard"] = "Our house checklist"
        self.assertEqual(rules(model), ["M9"])

    def test_w6_7_reference_not_in_asvs_4_0_3_form_fails(self):
        # ASVS 4.0.3 has chapters V1 to V14: V15 and V0 do not exist.
        for ref in ("4.2.1", "V4.2", "V15.1.1", "V0.1.1", "v4.2.1", "V4.2.1.1", "ASVS-4.2.1", "V4.0.1"):
            with self.subTest(where="review", ref=ref):
                model = minimal()
                model["review"][3]["ref"] = ref  # the not-examined row; T1's V3.5.3 keeps its row
                self.assertEqual(rules(model), ["M9"])
            with self.subTest(where="threat", ref=ref):
                model = minimal()
                model["threats"][0]["asvs"] = [ref]
                self.assertEqual(rules(model), ["M9"])

    def test_w6_7_valid_references_pass(self):
        for ref in ("V1.14.1", "V14.4.7", "V5.3.10", "V2.1.1"):
            with self.subTest(ref=ref):
                model = minimal()
                model["review"][3]["ref"] = ref
                self.assertEqual(problems(model), [])


class Elements(unittest.TestCase):
    def test_w6_8_flow_to_unknown_element_fails(self):
        model = minimal()
        model["flows"][1]["to"] = "cache"
        found = problems(model)
        self.assertEqual(rules(model), ["M2"])
        self.assertIn("cache", found[0])

    def test_w6_8_flow_from_unknown_element_fails(self):
        model = minimal()
        model["flows"][1]["from"] = "worker"
        self.assertEqual(rules(model), ["M2"])

    def test_w6_8_element_in_unknown_zone_fails(self):
        model = minimal()
        model["elements"][2]["zone"] = "dmz"
        self.assertIn("M2", rules(model))


class Shape(unittest.TestCase):
    def test_duplicate_ids_fail(self):
        model = minimal()
        model["threats"].append(copy.deepcopy(model["threats"][0]))
        self.assertEqual(rules(model), ["M1"])

    def test_missing_lists_fail(self):
        for key in ("zones", "elements", "flows", "threats"):
            with self.subTest(key=key):
                model = minimal()
                del model[key]
                self.assertIn("M1", rules(model))

    def test_not_an_object_fails(self):
        self.assertEqual(rules([]), ["M1"])

    def test_not_examined_must_be_a_list_of_texts(self):
        # Gate round 2 F8: a string rendered one character per bullet.
        for value in ("Web UI", ["Web UI", 3], ["Web UI", ""], {"Web UI": True}):
            with self.subTest(value=value):
                model = minimal()
                model["not_examined"] = value
                found = problems(model)
                self.assertEqual(rules(model), ["M1"], found)
                self.assertEqual(len(found), 1, found)
        model = minimal()
        model["not_examined"] = ["Web UI and single sign-on"]
        self.assertEqual(problems(model), [])

    def test_wrong_types_give_one_rule_line_not_a_traceback(self):
        # Review W6-r1 N1: a list or object where an ID is expected used to raise TypeError.
        cases = (
            ("list 'to'", "M2", lambda m: m["flows"][1].update(to=["db"])),
            ("object 'from'", "M2", lambda m: m["flows"][1].update({"from": {"id": "api"}})),
            ("object zone", "M2", lambda m: m["elements"][2].update(zone={"id": "app"})),
            ("nested STRIDE IDs", "M3", lambda m: m["flows"][0]["stride"].update(spoofing=[["T1"]])),
            ("nested LINDDUN IDs", "M4", lambda m: m["flows"][0]["linddun"].update(identifying=[["T3"]])),
            ("object in abuse case", "M10", lambda m: m["abuse_cases"][0].update(threats=[{"id": "T1"}])),
            ("nested review IDs", "M11", lambda m: m["review"][0].update(threats=[["T1"]])),
        )
        for name, rule, change in cases:
            with self.subTest(case=name):
                model = minimal()
                change(model)
                found = problems(model)
                self.assertEqual(len(found), 1, found)
                self.assertTrue(found[0].startswith(f"{rule}: "), found)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "model.json"
                    path.write_text(json.dumps(model))
                    out = run("check", str(path))
                self.assertEqual(out.returncode, 1)
                self.assertEqual(out.stderr, "")
                self.assertEqual(len(out.stdout.splitlines()), 1, out.stdout)


class AbuseCasesAndReview(unittest.TestCase):
    def test_abuse_cases_are_required_and_name_known_threats(self):
        for change in ("none", "empty threats", "unknown threat", "no goal"):
            with self.subTest(change=change):
                model = minimal()
                case = model["abuse_cases"][0]
                if change == "none":
                    model["abuse_cases"] = []
                elif change == "empty threats":
                    case["threats"] = []
                elif change == "unknown threat":
                    case["threats"] = ["T42"]
                else:
                    del case["goal"]
                self.assertEqual(rules(model), ["M10"])

    def test_m11_threat_asvs_reference_needs_a_review_row(self):
        # Eval finding 2: T1 cites V2.10.1, but no review row covers it.
        model = minimal()
        model["threats"][0]["asvs"] = ["V3.5.3", "V2.10.1"]
        found = problems(model)
        self.assertEqual(rules(model), ["M11"])
        self.assertEqual(len(found), 1, found)
        self.assertIn("V2.10.1", found[0])
        self.assertIn("T1", found[0])
        # Any result covers it, and a malformed reference stays M9 only.
        model["review"].append({"ref": "V2.10.1", "result": "not examined"})
        self.assertEqual(problems(model), [])
        model["threats"][0]["asvs"] = ["V3.5.3", "V2.10"]
        self.assertEqual(rules(model), ["M9"])

    def test_review_rows_need_evidence_threats_or_reason(self):
        cases = (
            ("empty review", lambda m: m.update(review=[])),
            ("met without evidence", lambda m: m["review"][1].pop("evidence")),
            ("gap without threats", lambda m: m["review"][0].pop("threats")),
            ("gap with unknown threat", lambda m: m["review"][0].update(threats=["T42"])),
            ("n/a without reason", lambda m: m["review"][2].pop("reason")),
            ("unknown result", lambda m: m["review"][3].update(result="passed")),
        )
        for name, change in cases:
            with self.subTest(case=name):
                model = minimal()
                change(model)
                self.assertEqual(rules(model), ["M11"])


class Overclaim(unittest.TestCase):
    def test_x2_summary_overclaims_fail(self):
        for summary in ("The upload flow is secure.", "Secure by design", "No vulnerabilities remain.",
                        "The service is vulnerability-free.", "Risk free upload."):
            with self.subTest(summary=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(rules(model), ["M12"])

    def test_x2_summary_overclaim_variants_fail(self):
        # Review W6-r1 M1: close variants and "verified" as a claim.
        for summary in ("The service is fully secured.", "No known vulnerabilities.",
                        "Zero vulnerabilities found.", "The upload is vulnerability free.",
                        "Securely designed", "All controls verified.", "Verified against ASVS 4.0.3.",
                        "Not yet tested, but secure.",
                        # Recheck N3: "not only", "not just" and "not merely" do not negate the claim; the
                        # exemptions for scans, Secure Shell and secure cookies leave other claims caught.
                        "The system is not only secure but fast.", "It is not just secure.",
                        "Not merely verified.", "No vulnerabilities found in the scan.",
                        "Secure Shell access is secure.", "Zero vulnerabilities; the secure-cookie test passed."):
            with self.subTest(summary=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(rules(model), ["M12"])

    def test_x2_overclaim_in_any_printed_text_fails(self):
        # Gate 2 F1: render prints more prose than the summary; M12 checks each free-text field it prints.
        claim = "The export path is secure and verified."
        cases = (
            ("name", lambda m: m.update(name="Photo upload, secure and verified")),
            ("scope", lambda m: m.update(scope=m["scope"] + ". " + claim)),
            ("not_examined", lambda m: m.update(not_examined=["Web UI", claim])),
            ("zone name", lambda m: m["zones"][1].update(name="Secured application network")),
            ("element name", lambda m: m["elements"][1].update(name="Verified upload API")),
            ("flow data", lambda m: m["flows"][1].update(data="Photo metadata over a securely configured link")),
            ("STRIDE n/a reason", lambda m: m["flows"][0]["stride"].update(tampering="n/a: " + claim)),
            ("LINDDUN n/a reason", lambda m: m["flows"][0]["linddun"].update(linking="n/a: " + claim)),
            ("threat title", lambda m: m["threats"][2].update(title="EXIF data; the store is risk-free")),
            ("mitigation", lambda m: m["threats"][0].update(mitigation="Planned: signed tokens. " + claim)),
            ("verification", lambda m: m["threats"][0].update(verification="Token test; no known vulnerabilities")),
            ("accept reason", lambda m: m["threats"][1].update(reason="Uploads are secure by design")),
            ("abuse actor", lambda m: m["abuse_cases"][0].update(actor="Attacker against a verified API")),
            ("abuse goal", lambda m: m["abuse_cases"][0].update(goal="Replace a photo; " + claim)),
            ("abuse how", lambda m: m["abuse_cases"][0].update(how=claim)),
            ("review reason", lambda m: m["review"][2].update(reason="Consent flow is verified")),
        )
        for field, change in cases:
            with self.subTest(field=field):
                model = minimal()
                change(model)
                found = problems(model)
                self.assertEqual(rules(model), ["M12"], found)
                self.assertEqual(len(found), 1, found)

    def test_x2_evidence_records_and_honest_text_pass(self):
        # Evidence fields record what ran; a claim there is the evidence. Negated or exempt words pass.
        model = minimal()
        model["threats"][0]["evidence"] = "CI run 12: token expiry verified, 2026-11-20"
        model["review"][1]["evidence"] = "testssl.sh report verified TLS 1.2 only, staging, 2026-11-20"
        model["threats"][1]["accepted"] = "Dana Reyes verified the risk in writing, 2026-11-20"
        model["scope"] += "; the upload path is not yet verified"
        model["not_examined"] = ["Secure Shell access to the hosts", "No vulnerability scan ran"]
        self.assertEqual(problems(model), [])

    def test_x2_control_names_quotes_and_verbs_pass(self):
        # Gate round 2 M1/F6: control names, quoted or code text and "verified" as a verb are not claims.
        cases = (
            ("mitigation", "Planned: set the Secure and HttpOnly flags on the session cookie"),
            ("mitigation", "Existing (design, section 4): session cookie has the Secure, HttpOnly and "
                           "SameSite=Strict attributes"),
            ("mitigation", "Planned: the `Secure` attribute set (ASVS V3.4.1)"),  # backticks, not quotes
            ("mitigation", "Planned: Secure Boot on the hosts"),
            ("mitigation", "Planned: each webhook signature is verified with HMAC-SHA256"),
            ("mitigation", "Planned: set `Secure` and `HttpOnly`; the gateway verified the signature first"),
            ("verification", "Integration test asserts the Secure flag on every Set-Cookie header"),
            ("verification", "Unit test: a token verified against the old key gets 401"),
            ("title", "A forged webhook is accepted as `verified`"),  # backticks, not quotes
            ("mitigation", "Planned: reject a replayed webhook; a verified request is accepted once"),
            ("verification", "Contract test: only verified tokens reach the API"),
            ("element name", "SFTP server (secure file transfer)"),
            ("abuse how", "Replays a request captured over Secure Shell"),
            ("scope", "docs/designs/photo-upload.md; the vendor calls it \"secure by design\""),
            ("summary", "The vendor says \u201cverified\u201d; cookie `secure=true` not run."),
            ("summary", "The vendor says 'no known vulnerabilities'; not examined."),
            ("summary", "The vendor report states \"verified\" for T2; not run here."),
            ("summary", "The vendor claimed 'secure', and the auditor said \"risk free\"; not examined."),
            ("not_examined", "The `Secure` flag on the admin cookie"),
            ("verification", "CI: a payload verified using Ed25519 keys is accepted"),
            ("verification", "Unit test: the request is verified by HMAC before it is stored"),
            ("mitigation", "Planned: tokens verified by the gateway's signature check"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                model = minimal()
                if field in ("mitigation", "verification"):
                    model["threats"][0][field] = value
                elif field == "title":
                    model["threats"][2]["title"] = value
                elif field == "element name":
                    model["elements"][1]["name"] = value
                elif field == "abuse how":
                    model["abuse_cases"][0]["how"] = value
                elif field == "not_examined":
                    model["not_examined"] = [value]
                else:
                    model[field] = value
                self.assertEqual(problems(model), [])

    def test_x2_round3_quoted_claims_wide_nouns_and_loose_verified_fail(self):
        # Gate round 3 M2/F9 and N7. Fail safe: each of these gave pass at round 3 and must give M12.
        quoted = ("Overall result: 'secure'.", '"The export path is secure and verified."',
                  'The export path is "secure" and "verified".', "Result: 'no known vulnerabilities'.",
                  "The badge text \u201cverified\u201d shows on every export.", "Result: \u2018risk free\u2019",
                  "Data is sent over a secured channel.", "Data is sent over a secure channel.",
                  "The platform uses secure elements throughout.", "Hosts use securely configured boot",
                  "Hosts use a secured boot chain.", "Cookies carry securely set flags.")
        fields = (
            ("summary", lambda m, v: m.update(summary=v)),
            ("scope", lambda m, v: m.update(scope=m["scope"] + "; " + v)),
            ("name", lambda m, v: m.update(name="Photo upload. " + v)),
            ("not_examined", lambda m, v: m.update(not_examined=[v])),
            ("zone name", lambda m, v: m["zones"][1].update(name=v)),
            ("element name", lambda m, v: m["elements"][1].update(name=v)),
            ("flow data", lambda m, v: m["flows"][1].update(data=v)),
            ("STRIDE n/a reason", lambda m, v: m["flows"][0]["stride"].update(tampering="n/a: " + v)),
            ("abuse how", lambda m, v: m["abuse_cases"][0].update(how=v)),
            ("review reason", lambda m, v: m["review"][2].update(reason=v)),
        )
        for value in quoted:
            for field, change in fields:
                with self.subTest(field=field, value=value):
                    model = minimal()
                    change(model, value)
                    self.assertEqual(rules(model), ["M12"])
        # Unquoted claims and loose "verified" in a threat's title, mitigation and verification.
        described = ("Data is sent over a secured channel", "The platform uses secure elements throughout",
                     "The system is verified end to end", "Verified by the security team",
                     "Everything verified here", "A forged webhook is accepted as verified",
                     "tokens verified with care", "verified by Dana Reyes", "verified using judgement",
                     "verified with HMAC by the security team")
        for value in described:
            for field, index, prefix in (("title", 2, ""), ("mitigation", 0, "Planned: "),
                                         ("verification", 0, "")):
                with self.subTest(field=field, value=value):
                    model = minimal()
                    model["threats"][index][field] = prefix + value
                    self.assertEqual(rules(model), ["M12"])

    def test_x2_round4_quotes_are_read_and_self_labels_fail(self):
        # Gate 1 round 4 M3 (replanned): backticks are the only way to name a control. Quoted text is read
        # in every field, and "marked" or "labelled" do not make a quote someone else's words.
        cases = (
            ("mitigation", "Planned: short-lived tokens. The export path is then 'secure'."),
            ("summary", 'Model status: marked "secure".'),
            ("mitigation", "Planned: the 'Secure' attribute set (ASVS V3.4.1)"),
            ("title", "A forged webhook is accepted as 'verified'"),
            ("summary", "The badge is labelled \u201cverified\u201d; cookie `secure=true` not run."),
            ("summary", 'T2 is marked as "verified" in the vendor report; not run here.'),
            ("verification", "Token test; result \u2018verified\u2019"),
            ("title", 'Token theft; the store is "risk free"'),
            ("scope", "photo-upload.md; labelled 'no known vulnerabilities'"),
            ("summary", "The model is called 'secure'."),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                model = minimal()
                if field in ("mitigation", "verification"):
                    model["threats"][0][field] = value
                elif field == "title":
                    model["threats"][2]["title"] = value
                else:
                    model[field] = value
                self.assertEqual(rules(model), ["M12"])

    def test_d11_bare_vendor_or_standard_name_is_not_a_means(self):
        # D-11: a vendor or standard name is not evidence. A tool counts only as a version (a number with
        # a dot) or a file name; "one" is no longer a noun that makes "verified" a control.
        for value in ("verified by AWS", "verified by SOC2", "verified one way or another",
                      "a verified one is accepted once", "verified by Okta SSO"):
            for field, index, prefix in (("title", 2, ""), ("mitigation", 0, "Planned: "),
                                         ("verification", 0, "")):
                with self.subTest(field=field, value=value):
                    model = minimal()
                    model["threats"][index][field] = prefix + value
                    self.assertEqual(rules(model), ["M12"])
        for value in ("Semgrep: rule set verified by semgrep 1.85 on 2026-11-20",
                      "TLS settings verified by check_tls.py in staging",
                      "Signature verified with HMAC-SHA256 in a unit test"):
            with self.subTest(passes=value):
                model = minimal()
                model["threats"][0]["verification"] = value
                self.assertEqual(problems(model), [])

    def test_d14_author_words_and_our_vendor(self):
        # D-14: I, my, this threat model, the author and the assessment name the model's author; "our" does
        # only before review, model, threat model or assessment, so "Our vendor says" is a third party.
        for summary in ("I said 'secure'.", "My review says 'secure'.", "This threat model states 'secure'.",
                        "The author states 'secure'.", "The assessment says 'secure'.",
                        "Our threat model says 'secure'.", "Our assessment states 'secure'."):
            with self.subTest(summary=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(rules(model), ["M12"])
        for summary in ("Our vendor says 'secure by design'.", "Our supplier states 'no known vulnerabilities'."):
            with self.subTest(passes=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(problems(model), [])

    def test_x2_author_cannot_quote_itself(self):
        # Gate 2 RP3: a third-party verb does not skip a quote when the model's author is its subject.
        for summary in ('Our review says "secure and verified".', 'This model states "no known vulnerabilities".',
                        "The model states: 'the export path is secure'.", "We said 'secure' after the test.",
                        "The team claims 'risk free'.", "The review claimed \u201cverified\u201d.",
                        "Per the vendor call, we say 'secure'.", "The vendor told us it says 'secure'."):
            with self.subTest(summary=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(rules(model), ["M12"])
        for summary in ("The vendor says 'secure by design'.",
                        "We asked the vendor. The vendor says 'secure by design'; not examined.",
                        "Our review is open; the auditor stated \"risk free\" in the 2025 report."):
            with self.subTest(passes=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(problems(model), [])

    def test_x2_claims_in_control_text_still_fail(self):
        # The exemptions above must not let a bare claim through in title, mitigation or verification.
        claims = ("the system is verified", "fully verified with HMAC", "verified secure",
                  "all controls verified.", "the export path is secure", "no vulnerabilities",
                  "the system is verified and tested", "verified, so the risk is closed",
                  "the app is secure and the cookie flags are set", "tenant B's export is secure and the API's too")
        for claim in claims:
            for field, value in (("mitigation", "Planned: tokens; " + claim), ("verification", "Token test; " + claim),
                                 ("title", "Token theft; " + claim)):
                with self.subTest(field=field, claim=claim):
                    model = minimal()
                    model["threats"][2 if field == "title" else 0][field] = value
                    self.assertEqual(rules(model), ["M12"])
            with self.subTest(field="summary", claim=claim):
                model = minimal()
                model["summary"] = claim
                self.assertEqual(rules(model), ["M12"])

    def test_x2_labelled_summary_passes(self):
        for summary in ("Three threats: one mitigation not run yet, one accepted risk, one backlog "
                        "item. V14.2.1 not examined.",
                        "Not secure yet: 3 gaps.", "Mitigations not verified: 1 not run.",
                        "T1 is not yet verified; security review of V14 not examined.",
                        "Unverified: the insecure upload path is T3.",
                        # Recheck N3: honest labels the widened check used to reject.
                        "No vulnerability scan ran.", "No vulnerability scanning was in scope.",
                        "No vulnerability scanner or test ran; no vulnerability database or data feed was read.",
                        "SFTP over Secure Shell with key login; 3 gaps.", "Secure cookie flag is a gap (T2).",
                        "3 threats; secure-cookie test not run.", "Nothing here is secure.",
                        "Cannot be called secure: 3 gaps.", "Never verified."):
            with self.subTest(summary=summary):
                model = minimal()
                model["summary"] = summary
                self.assertEqual(problems(model), [])


class Example(unittest.TestCase):
    def setUp(self):
        self.model = json.loads(EXAMPLE.read_text())

    def test_w6_9_example_passes(self):
        self.assertEqual(problems(self.model), [])

    def test_w6_9_render_prints_the_tables(self):
        out = run("render", str(EXAMPLE))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        text = out.stdout
        self.assertTrue(text.startswith("# Threat model: Tenant order export\n"), text[:80])
        for heading in ("## Elements", "## Trust boundaries", "## Flows", "## STRIDE", "## LINDDUN",
                        "## Threats", "## Abuse cases", "## Standard review", "## Not examined"):
            self.assertIn(f"\n{heading}\n", text)
        self.assertIn("| ID | Threat | Where | Disposition | Detail | ASVS | Evidence |", text)
        # Written by hand from reference/example.json: 15 threats, T1 to T15.
        rows = re.findall(r"^\| (T\d+) \|", text, re.M)
        self.assertEqual(rows, [f"T{n}" for n in range(1, 16)])
        row = lambda tid: next(l for l in text.splitlines() if l.startswith(f"| {tid} |"))
        self.assertIn("accept", row("T4"))
        self.assertIn("Priya Shah", row("T4"))
        self.assertIn("F6 information disclosure", row("T4"))  # the signed link in the status response
        self.assertIn("B-31", row("T5"))
        self.assertIn("not run", row("T6"))  # a mitigation without evidence is labelled, not claimed
        self.assertIn("F7 spoofing", row("T14"))
        self.assertIn("F3 tampering", row("T15"))  # not examined, so a backlog item, not an n/a
        self.assertIn("B-33", row("T15"))
        # Crossing flows F1, F3, F4, F5, F6 and the queue flow F7 (STRIDE given though it stays in the
        # application zone) each get a STRIDE row; personal-data flows F3, F4, F5 a LINDDUN row.
        stride = text.split("\n## STRIDE\n")[1].split("\n## ")[0]
        linddun = text.split("\n## LINDDUN\n")[1].split("\n## ")[0]
        self.assertEqual(re.findall(r"^\| (F\d+) \|", stride, re.M), ["F1", "F3", "F4", "F5", "F6", "F7"])
        self.assertEqual(re.findall(r"^\| (F\d+) \|", linddun, re.M), ["F3", "F4", "F5"])
        # Five boundary rows, one per zone pair: internet -> app (F1), data -> app (F3),
        # app -> storage (F4), storage -> internet (F5) and app -> internet (F6).
        bounds = text.split("\n## Trust boundaries\n")[1].split("\n## ")[0]
        self.assertIn("| Application network | Public internet | F6 |", bounds)
        self.assertEqual(len(re.findall(r"^\| (?!From|---)", bounds, re.M)), 5)

    def test_w6_9_example_has_a_flow_for_each_contract(self):
        # Review W6-r1 M2: architecting's filled example has POST and GET /v1/exports (request and
        # response, the response carrying the signed link), export.requested v1 (Orders API -> queue ->
        # export worker) and the export file (worker -> storage -> tenant). Pairs written by hand.
        pairs = {(f["from"], f["to"]) for f in self.model["flows"]}
        for pair in (("tenant-client", "orders-api"), ("orders-api", "tenant-client"),
                     ("orders-api", "export-queue"), ("export-queue", "export-worker"),
                     ("orders-db", "export-worker"), ("export-worker", "export-store"),
                     ("export-store", "tenant-client")):
            self.assertIn(pair, pairs)
        response = next(f for f in self.model["flows"] if (f["from"], f["to"]) == ("orders-api", "tenant-client"))
        self.assertIn("signed link", response["data"])
        self.assertIn("T4", response["stride"]["information_disclosure"])

    def test_w6_9_example_summary_counts_match_the_model(self):
        # Counted by hand: 7 flows, 5 crossing (F1, F3, F4, F5, F6); 15 threats: 10 mitigate (only T7
        # has evidence), 2 accept (T4, T13), 3 backlog (T5, T11, T15).
        summary = self.model["summary"]
        for phrase in ("15 threats", "7 flows", "5 of them cross a trust boundary", "10 mitigations",
                       "1 with evidence", "9 not run", "2 accepted risks", "3 backlog items",
                       "no control is in place"):
            self.assertIn(phrase, summary)
        # Review rows counted by hand: V2.10.1 met (CI run 4182); V2.1.1 not applicable; V1.1.2 and
        # V14.2.1 not examined; the other 11 are gaps.
        self.assertIn("1 met, 11 gaps, 1 not applicable, 2 not examined", summary)

    def test_w6_9_example_does_not_cite_itself_for_v1_1_2(self):
        # Eval finding 1: the model being written is not evidence for V1.1.2.
        row = next(r for r in self.model["review"] if r["ref"] == "V1.1.2")
        self.assertEqual(row["result"], "not examined")

    def test_render_refuses_a_failing_model(self):
        model = copy.deepcopy(self.model)
        del model["standard"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            path.write_text(json.dumps(model))
            out = run("render", str(path))
        self.assertEqual(out.returncode, 1)
        self.assertTrue(out.stdout.startswith("M9:"), out.stdout)


class CommandLine(unittest.TestCase):
    def test_help_exits_zero(self):
        out = run("--help")
        self.assertEqual(out.returncode, 0)
        self.assertIn("check", out.stdout)
        self.assertIn("render", out.stdout)

    def test_check_exit_codes(self):
        good = run("check", str(EXAMPLE))
        self.assertEqual((good.returncode, good.stdout.strip()), (0, "pass"))
        model = minimal()
        del model["threats"][0]["verification"]
        model["flows"][1]["to"] = "cache"
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(model))
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json")
            no = run("check", str(bad))
            junk = run("check", str(broken))
            missing = run("check", str(Path(tmp) / "absent.json"))
        self.assertEqual(no.returncode, 1)
        self.assertEqual(sorted(l.split(":")[0] for l in no.stdout.splitlines()), ["M2", "M8"])
        for out in (junk, missing):
            self.assertEqual(out.returncode, 1)
            self.assertEqual(len(out.stdout.splitlines()), 1, out.stdout)
            self.assertTrue(out.stdout.startswith("M1:"), out.stdout)

    def test_unknown_command_fails(self):
        self.assertNotEqual(run("draw", str(EXAMPLE)).returncode, 0)


class SkillText(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text()

    def test_x7_without_a_shell_rule(self):
        self.assertRegex(self.text, r"(?m)^## Without a shell$")
        section = self.text.split("## Without a shell")[1].split("\n## ")[0]
        self.assertIn("not run", section)
        self.assertIn("threat_check.py check", section)

    def test_review_cap_follows_disposition_policy(self):
        self.assertIn("disposition policy", self.text)

    def test_outside_effects_need_contract_or_exact_plan(self):
        self.assertIn("pre-authorizes", self.text)
        self.assertIn("exact plan", self.text)

    def test_links_resolve_and_length(self):
        self.assertLess(len(self.text.splitlines()), 200)
        for link in re.findall(r"\]\(((?:reference|scripts)/[^)]+)\)", self.text):
            self.assertTrue((SKILL / link).is_file(), link)
        for name in ("stride.md", "linddun.md", "asvs.md", "model.md", "example.json"):
            self.assertIn(f"reference/{name}", self.text)

    def test_eval_findings_guidance(self):
        # Eval findings 1, 3, 4, 5 and 6 (threat-modelling results.md).
        flat = lambda text: " ".join(text.split())  # guidance sentences wrap across lines
        asvs = (SKILL / "reference" / "asvs.md").read_text()
        self.assertIn("The model you are writing is not evidence for V1.1.2.", flat(asvs))
        self.assertNotIn("is the evidence for it", asvs)
        # D-7, eval round 3: a table row may be a `gap` without reading the source; `met` may not.
        self.assertIn("A row of this table may be cited as `gap` or `not examined` by its subject alone", flat(asvs))
        self.assertIn("Before you cite any requirement as `met`, quote it, or cite one not in this table, "
                      "read its full text in the source", flat(asvs))
        stride = (SKILL / "reference" / "stride.md").read_text()
        self.assertIn("A cited threat must cover this flow's sender.", flat(stride))
        # D-7, eval round 4, findings 11 to 13.
        self.assertIn("When no table row covers a threat's control, list its chapter or section under `not_examined`.",
                      flat(asvs))
        self.assertIn("Resting an `n/a` reason on anything listed in `not_examined`.", flat(stride))
        self.assertIn("the sources do not state, or that is only planned", flat(self.text))
        for ref in ("V7.1.1", "V7.1.2", "V12.1.1"):
            self.assertRegex(asvs, rf"(?m)^\| {re.escape(ref)} \| \S")
        self.assertIn("not the full list", flat(asvs))
        self.assertIn("`Existing (<source>):` or `Planned:`", flat(self.text))
        flags = self.text.split("## Red flags")[1].split("\n## ")[0]
        self.assertIn("An `n/a` reason that depends on a bound or control the sources do not state", flat(flags))
        linddun = (SKILL / "reference" / "linddun.md").read_text()
        self.assertIn("Staff and operator identities (session, user ID) are personal data too.", flat(linddun))
        # Round 2 findings 7 and 8.
        stride = flat((SKILL / "reference" / "stride.md").read_text())
        self.assertIn("'Not examined' is not an `n/a` reason. When a category on an in-scope flow was not "
                      "examined, write a threat for it (a backlog item to examine it is enough).", stride)
        self.assertIn("'Not examined' is not an `n/a` reason", flat(linddun))
        self.assertIn("When the system is not built yet, write `Existing (<design section>, not built):`, or "
                      "say in `summary` that no control is in place.", flat(self.text))

    def test_checker_lines_fit_120_characters(self):
        long = [n for n, line in enumerate(SCRIPT.read_text().splitlines(), 1) if len(line) > 120]
        self.assertEqual(long, [])

    def test_reference_lists_match_the_checker(self):
        if threat_check is None:
            self.fail("threat_check.py is missing")
        self.assertEqual(tuple(threat_check.STRIDE), STRIDE)
        self.assertEqual(tuple(threat_check.LINDDUN), LINDDUN)
        for name, keys in (("stride.md", STRIDE), ("linddun.md", LINDDUN)):
            ref = (SKILL / "reference" / name).read_text()
            for key in keys:
                self.assertIn(f"`{key}`", ref, f"{name} lacks {key}")


if __name__ == "__main__":
    unittest.main()

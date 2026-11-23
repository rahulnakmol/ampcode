---
name: scanning-vulnerabilities
description: "Runs allowed static scanners on local paths the owner names, for code (SAST), dependencies, secrets, infrastructure as code and container images, merges their SARIF into one findings table, triages each finding for reachability and exploitability with a disposition, owner, reason and retest evidence, and states coverage per category as 'scanned, N findings' or 'not examined'. A standard-library script merges and deduplicates the SARIF and rejects an incomplete triage or an overclaim such as 'secure'. Findings can trace to threat IDs from a threat-modelling model. Use when asked to scan a repository or folder for vulnerabilities, run SAST, dependency, secret, IaC or container scans, merge or triage SARIF, or write a scan report with coverage. Not for dynamic testing (DAST) or penetration testing, scanning hosts, URLs or systems the owner did not name, or building the threat model itself."
---

# Scanning vulnerabilities

A scan report is useful when the reader can see what was scanned, what was found, what each
finding means here, and what was not looked at. This skill runs allowed scanners, merges their
SARIF into one table, triages every finding, and states coverage. It never says the code is
safe. A scan with 0 findings says only that the tools reported nothing.

## Scope

- **Targets:** local paths the owner names, for example a repository checkout or one folder in
  it. Scanning anything else is out of scope: other hosts, URLs, cloud accounts, registries you
  were not given, or running services. DAST and penetration testing are out of scope.
- **Categories:** `code`, `dependencies`, `secrets`, `iac`, `containers`. A container scan reads
  a local image or image archive the owner names.
- **Allowed scanners:** the tools in [reference/scanners.md](reference/scanners.md), and any
  other tool the owner or the mission contract names. Do not install or run a scanner outside
  that list without asking.
- **Upstream:** a `threat-modelling` model, when one exists. Its entry points help decide
  reachability, and a finding that realizes a modelled threat names that threat ID in the
  Threat column. This skill does not need the model to run.

## Outside effects

Scanning local paths changes nothing outside the orb or machine. Some actions do: uploading SARIF
to a code scanning service, filing tracker issues for findings, or releasing the report to
people outside the mission. Run them only when the mission contract pre-authorizes that exact
effect, or the owner approves the exact plan (the files, the destination and the digest).
Outside a contract mission, the owner approves the exact plan.

## Run a scan

1. **Agree the scope.** Write down the paths, the categories and the tools. Read the threat
   model's entry points if there is one.
2. **Install pinned tools** as [reference/scanners.md](reference/scanners.md) says. Verify
   release checksums. Record each version from the tool itself (`--version`), not from its SARIF.
3. **Run each scanner** with SARIF output written outside the scanned tree. Record the exact
   command, the folder it ran in and the exit code. A nonzero exit often means "findings", not a
   failed run; read the tool's notes.
4. **Merge.** `<skill>` is the folder that holds this file:

   ```bash
   python3 <skill>/scripts/sarif_triage.py merge --root /abs/path/scanned \
     code=semgrep.sarif code=bandit.sarif dependencies=osv.sarif secrets=gitleaks.sarif \
     iac=checkov.sarif > report.md
   ```

   Results with the same path, start line and CWE become one finding that lists every tool.
   Results without a CWE merge only when the tool and the rule ID also match. `--root` makes
   absolute and relative paths compare. The report has Sources, Coverage and Findings sections.
   A category with no SARIF file is "not examined". Each tool shows "version per SARIF: ...";
   replace it with the version you recorded in step 2.
5. **Triage every finding.** Fill the empty columns; see "Triage" below.
6. **Check.** `python3 <skill>/scripts/sarif_triage.py check report.md` prints `pass` or one
   line per broken rule. Fix the report, not the rule.
7. **Write the report.** Add the scope, the commands, why each category was not examined, and
   what to do next. You may split the findings into several tables under `## Findings`, for
   example one per category; keep every column in each. Run `check` again on the final text,
   and record the command and its `pass` in the report's commands.

## Triage

| Column | Values | Rule |
| --- | --- | --- |
| Reachable | yes, no, not proven | Yes only with a path from an entry point to the code, or proof the vulnerable package function is called |
| Exploitable | yes, no, not proven | Yes only when attacker-controlled input reaches it under realistic preconditions |
| Disposition | to fix, fixed, accepted, false positive | Every finding has one |
| Owner | a named person, not a team or role | Required for accepted; best for to fix. Role text may follow the name: "Dana Reyes (Platform Group lead)" |
| Reason | text | Required for false positive: why it is not real here |
| Retest | `<Rescan\|Test\|PoC\|CI> <tool or name> <YYYY-MM-DD>: <result>` | Required for fixed Critical or High, in this form only: "Rescan Bandit 1.9.4 2026-11-21: 0 results at app.py:24", "PoC F1-exploit 2026-11-20: request rejected with 403", "CI test_upload_rejects_shell 2026-11-21: passed". The name is the tool, test or PoC, not a placeholder such as TBD. The date is the run date, not after today (your local date; `check --today` sets it). The result may be a negative finding ("no findings for B602", "exploit failed, request rejected", "PoC failed, request rejected with 403"). It may not contain these words anywhere, even in an honest sentence, so a result should not mention unrelated skipped tests: skipped, cancelled, errored, aborted, crashed, canceled, timed out, queued, postponed, deferred, in progress, pending, will, expected, yet, none, n/a, unknown, TBD, TBA, todo, planned, scheduled, awaiting, to follow, to be run, not run, not done, not finished, failed to start, did not run, start or finish, could not or cannot run, going to run, and "not", "never" or "has not been" before run, started, finished, rescanned, retested or re-run. These words fail anywhere in the result; `check` refuses everything that it refused before this rule changed. "failed" also fails as the whole result or right after "the", "a" or a run word ("the run failed", "scan failed: runner offline", "failed, see log"), but not after PoC or exploit. Reword an honest result: "request rejected with 403" instead of "request rejected with 403 as expected"; "0 of the 3 B602 hits remain" instead of "none of the 3 B602 hits remain"; "old tokens are rejected: 0 of 3 accepted" instead of "the old token will no longer work"; for XSS, "script rendered as text, not executed" is fine. The list is not every phrasing: a reviewer still reads the result. `check` reads only the form; a reviewer reads the content: that the run happened and its result shows the fix |
| Threat | threat ID or `-` | From the `threat-modelling` model, when the finding realizes a modelled threat |

- Start from the merged severity (see [reference/scanners.md](reference/scanners.md#severity)).
  You may raise or lower it with a reason in the Reason column.
- "not proven" is an honest answer. A guess is not.
- A duplicate across tools that did not merge (for example one CVE from two dependency
  scanners on different lines) keeps both rows. Write "same as F4" in the Reason column. A yes
  in Reachable or Exploitable on that row still names the entry point or input.
- Accepting a risk is the owner's call, never the agent's. Leave it "to fix" until they decide.

## Report words

- Per category: "scanned, N findings" or "not examined", with the tools and versions.
- Per claim without evidence: "claimed", "not proven", "not run".
- Never write "secure", "no vulnerabilities", "no known vulnerabilities", "vulnerability-free",
  "safe" or "clean" about the target. `check` rejects the first four outside `code` spans.
  `check` does not catch these two; read for them. Quote a tool's own words or a rule name in
  backticks.

## Without a shell

When you have no shell (for example in the read-only Archi or Darci mode, or on a chat-only
host), do not run or simulate a scanner or the script. Give the caller the exact commands: the
scanner commands from [reference/scanners.md](reference/scanners.md) with their paths, then
`python3 <skill>/scripts/sarif_triage.py merge ...` and `check report.md`. Until the caller
reports the output, write each category's coverage line as
`- <category>: not examined (not run: no shell)`, which `check` accepts. You may still read
SARIF or a report the caller pastes and triage it, but its coverage is what the caller ran,
nothing more.

## Common rationalizations

| Excuse | Answer |
| --- | --- |
| "0 findings, so it is secure." | 0 findings means these tools reported nothing on these paths. Say that |
| "Containers do not matter here." | Then list them as not examined and say why |
| "This finding is in test code, so it is a false positive." | Give the reason in the Reason column; it may still ship |
| "I fixed it; the rescan is obvious." | A fixed Critical or High needs the rescan or test result |
| "The owner is busy, I will accept the risk for them." | Only the owner accepts a risk. Name them |
| "Let me also scan the staging URL to be thorough." | Out of scope: local paths the owner names only |

## Red flags

- A report that says "secure", "no vulnerabilities" or "clean" about the target.
- A category missing from Coverage, or "scanned" without a SARIF file behind it.
- A "version per SARIF" left in the final report. It can be wrong (gitleaks writes `v8.0.0`
  whatever the binary is); use the version the tool itself printed.
- Findings deleted from the table instead of given a disposition.
- A scan of a host, URL or image the owner did not name.
- Secrets copied from a scanner's output into the report, a ticket or chat.

## Adapt it

- **Tools:** add a tool to [reference/scanners.md](reference/scanners.md) with its install and
  SARIF command. Any tool that writes SARIF 2.1.0 works with the script.
- **Categories:** change `CATEGORIES` in `scripts/sarif_triage.py`.
- **Dispositions and words:** change `DISPOSITIONS` and `OVERCLAIM` at the top of the script.
- **Severity:** the thresholds are in `severity()`.

## Check your work

- Every category in Coverage is "scanned, N findings" or "not examined", with a reason for each
  not examined.
- The report lists each command, folder and tool version.
- `sarif_triage.py check` prints `pass` on the final report.
- Every finding has a disposition; accepted ones have the owner, false positives a reason, fixed
  Critical or High ones retest evidence in the Retest form, and you have read that each run
  happened and its result shows the fix.
- No secret value appears in the report.
- Nothing outside the named local paths was scanned.

# SARIF fixtures for scanning-vulnerabilities

Real scanner output, produced on 22 November 2026 in an Amp orb. The scanned samples were kept
under `/tmp` and are not in this repository. Only the SARIF files are committed, so no
vulnerable manifest, lockfile or source triggers this repository's own alerts.
`tests/test_scanning_vulnerabilities.py` and `evals/scanning-vulnerabilities/` use them.

## The samples

- **`/tmp/scan/sample`** (a git repository with one commit, because Semgrep scans tracked files
  only):
  - `app.py`: a Flask app with SQL built by string concatenation, `subprocess` with
    `shell=True`, `pickle.loads` and `yaml.load` on request data, MD5, and `app.run` on
    `0.0.0.0` with `debug=True`.
  - `settings.py`: one generic test token, `fixture_api_token`, 30 random letters and digits in
    no provider's key format. It is not a credential anywhere.
  - `requirements.txt`: four old pinned packages (Flask 0.12.2, PyYAML 5.3, requests 2.19.0,
    Jinja2 2.10).
  - `infra/main.tf`: an S3 bucket with a `public-read` ACL and a security group that opens port
    22 to `0.0.0.0/0`.
  - `Dockerfile`: `FROM python:latest`, no `USER`, no `HEALTHCHECK`.
- **`/tmp/scan/clean`** (a git repository with one commit): `tidy.py`, a five-line function
  that sums integers.

## Files

Every command ran in the sample folder named in the Cwd column, with the tools on `PATH`. The
Results column is the number of entries in `runs[].results`, read with
`jq '[.runs[].results | length] | add' <file>`.

| File | Category | Tool and version | Cwd | Command | Results |
| --- | --- | --- | --- | --- | --- |
| `semgrep.sarif` | code | Semgrep OSS 1.186.0 | sample | `semgrep scan --config p/python --metrics off --sarif --output ../out/semgrep.sarif .` | 8 |
| `bandit.sarif` | code | Bandit 1.9.4 | sample | `bandit -r . -x ./settings.py -f sarif -o ../out/bandit.sarif` | 9 |
| `bandit-clean.sarif` | code | Bandit 1.9.4 | clean | `bandit -r . -f sarif -o ../out/bandit-clean.sarif` | 0 |
| `osv-scanner.sarif` | dependencies | osv-scanner 2.7.1 | sample | `osv-scanner scan source -r --format sarif --output-file ../out/osv-scanner.sarif .` | 64 |
| `trivy-deps.sarif` | dependencies | Trivy 0.76.2 | sample | `trivy fs --scanners vuln --format sarif --output ../out/trivy-deps.sarif .` | 17 |
| `gitleaks.sarif` | secrets | gitleaks 8.30.1 | sample | `gitleaks dir . --report-format sarif --report-path ../out/gitleaks.sarif --redact` | 1 |
| `checkov.sarif` | iac | Checkov 3.4.6 | sample | `checkov -d . --framework terraform dockerfile -o sarif --output-file-path ../out/checkov` (writes `results_sarif.sarif`, renamed here) | 14 |
| `trivy-config.sarif` | iac | Trivy 0.76.2 | sample | `trivy config --format sarif --output ../out/trivy-config.sarif .` | 15 |

No container image was scanned, so the fixture set has no `containers` file. A report built from
it lists containers as "not examined".

## How the tools were installed

- Semgrep, Bandit (`bandit[sarif]`) and Checkov: `pip install` into a virtual environment
  under `/tmp/scan/venv`.
- gitleaks, osv-scanner and Trivy: release binaries from GitHub, downloaded with
  `gh release download` and checked against each release's published SHA-256 checksums file.

## Notes on the output

- **No file was trimmed.** `semgrep.sarif` (325 KB) and `osv-scanner.sarif` (384 KB) are large
  because of their rule metadata, not their results, so removing results would not help.
- **gitleaks writes `v8.0.0`** as its version in SARIF, although the binary was 8.30.1
  (`gitleaks version`). Record versions from the tool, not from its SARIF.
- **gitleaks ran with `--redact`**, so the token is `REDACTED` in its output.
- **Bandit excluded `settings.py`** (`-x ./settings.py`). Bandit has no redaction, and its
  hard-coded password rule would copy the test token into the committed SARIF. Secrets are
  covered by gitleaks.
- **osv-scanner reports each advisory twice** (64 results for 32 rule IDs, same manifest, no
  line), and it writes absolute `file:///tmp/scan/sample/...` URIs. Trivy writes relative URIs
  with a `ROOTPATH` base of `file:///tmp/scan/sample/`. Pass `--root /tmp/scan/sample` to
  `sarif_triage.py` so that paths compare.
- **osv-scanner queried osv.dev and deps.dev**, which resolved transitive packages (urllib3,
  chardet, idna and others) beyond the four in `requirements.txt`. Trivy and Semgrep downloaded
  their vulnerability database and rules.
- A nonzero exit code from a scanner meant "findings found", not a failed run.

## Check before committing a new fixture

```bash
rg -n -i -g '*.sarif' 'AKIA|ghp_|gho_|xox[abpr]-|sk_live|-----BEGIN' tests/fixtures/scanning-vulnerabilities
```

It must print nothing. Also search the SARIF for the sample's test token: it must not appear
(gitleaks shows it as `REDACTED`). Commit SARIF only: no manifest, lockfile or source from the
sample.

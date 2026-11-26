# Scanners

The allowed tools, how to install them, the command that writes SARIF, and what each one does
wrong. The versions are the ones that produced this skill's fixtures on 22 November 2026; pin
the versions you use and record them.

## Install

- **Python tools** (Semgrep, Bandit, Checkov): a virtual environment outside the scanned tree.

  ```bash
  python3 -m venv /tmp/scan/venv
  /tmp/scan/venv/bin/pip install 'semgrep==1.186.0' 'bandit[sarif]==1.9.4' 'checkov==3.4.6'
  ```

- **Release binaries** (gitleaks, osv-scanner, Trivy): download the release asset and its
  checksums file, and check the hash before you run it. Scanner releases are a supply-chain
  target too.

  ```bash
  gh release download v8.30.1 -R gitleaks/gitleaks -p 'gitleaks_8.30.1_linux_x64.tar.gz' -p '*checksums.txt'
  gh release download v2.7.1 -R google/osv-scanner -p osv-scanner_linux_amd64 -p '*SHA256SUMS*'
  gh release download v0.76.2 -R aquasecurity/trivy -p 'trivy_0.76.2_Linux-64bit.tar.gz' -p '*checksums.txt'
  sha256sum -c --ignore-missing *checksums.txt *SHA256SUMS*
  ```

## Commands

Run each command in the scanned folder. Write SARIF outside it (here `../out/`), so a second
scan does not read the first one's output.

| Category | Tool | Command |
| --- | --- | --- |
| code | Semgrep | `semgrep scan --config p/python --metrics off --sarif --output ../out/semgrep.sarif .` |
| code | Bandit (Python) | `bandit -r . -f sarif -o ../out/bandit.sarif` |
| dependencies | osv-scanner | `osv-scanner scan source -r --format sarif --output-file ../out/osv-scanner.sarif .` |
| dependencies | Trivy | `trivy fs --scanners vuln --format sarif --output ../out/trivy-deps.sarif .` |
| secrets | gitleaks | `gitleaks dir . --report-format sarif --report-path ../out/gitleaks.sarif --redact` |
| iac | Checkov | `checkov -d . -o sarif --output-file-path ../out/checkov` (writes `results_sarif.sarif`) |
| iac | Trivy | `trivy config --format sarif --output ../out/trivy-config.sarif .` |
| containers | Trivy | `trivy image --input image.tar --format sarif --output ../out/trivy-image.sarif` |

- Pick the Semgrep ruleset for the languages present (`p/python`, `p/javascript`, `p/java`,
  ...). Bandit reads Python only.
- `--redact` keeps the secret value out of gitleaks' output. Never paste a found secret into the
  report; give its file and line.
- A container scan reads a local image archive (`docker save image:tag -o image.tar`) or a local
  image the owner names (`trivy image image:tag`). Without one, containers are "not examined".
  A Dockerfile is `iac`, not `containers`.

## Network use

Scanning stays local, but some tools reach out:

- Semgrep downloads its registry rules; `--metrics off` stops usage metrics.
- osv-scanner sends package names and versions to osv.dev, and resolves transitive packages
  through deps.dev. When that is not allowed, use its offline mode: download the databases
  beforehand (`--offline-vulnerabilities --download-offline-databases`), then scan with
  `--offline` (see `osv-scanner scan source --help`).
- Trivy downloads its vulnerability database (`mirror.gcr.io/aquasec/trivy-db`) on first use.
- Checkov sends results to its platform only with `--bc-api-key`; do not give it one.

Tell the owner which tools send package names out before you run them on private code.

## Tool notes

| Tool | Note |
| --- | --- |
| gitleaks | Writes `v8.0.0` as its version in SARIF whatever the binary is. Record `gitleaks version` |
| gitleaks | Did not report test values containing words such as "fixture" or "notreal" in the fixture run. Use a random value in no provider's format for a test secret |
| Bandit | Has no redaction: its hard-coded password rule copies the value into SARIF. Treat its SARIF as sensitive, or exclude the file and rely on gitleaks |
| osv-scanner | Writes absolute `file://` URIs with no line, and may report one advisory twice. Pass `--root` to the script |
| Trivy | Writes relative URIs with a `ROOTPATH` base; the script joins them |
| Semgrep | Scans only files tracked by git inside a repository. Its SARIF lists every rule it ran |
| Checkov, Trivy config | Name no CWE, so their findings never merge across tools |
| All | A nonzero exit code can mean "findings found". Read the log before you call it a failed run |

## How the script merges

1. Each result gets a path: the URI joined with its `uriBaseId` base, `file://` stripped,
   percent-decoding undone, `--root` removed, `./` dropped.
2. Each result gets its start line (0 when it has none) and its CWE numbers from `tags`, `cwe`
   or `cwes` in the result's or the rule's properties (`CWE-89`, `external/cwe/cwe-089`).
3. Results with the same path and line merge when their CWE sets share a number. Merges chain:
   CWE-89 from one tool and CWE-79 from another stay apart, but a third result tagged with both
   joins all three into one finding. Results without a CWE merge only with results of the same
   tool and rule ID at that path and line.
4. A merged finding keeps every tool, rule and category, and the highest severity.

### Severity

The rule or result's `security-severity` score decides first: 9.0 or more is Critical, 7.0 or
more High, 4.0 or more Medium, above 0 Low. Without a score, the SARIF level decides: `error`
is High, `warning` Medium, `note` Low, `none` Info. A result without a level takes its rule's
default level, then `warning`.

## Report columns

`merge` writes `not proven` in Reachable and Exploitable, and leaves Disposition, Owner,
Reason, Retest and Threat empty. The Title column quotes the first tool's message in backticks;
`check` does not read text in backticks for overclaim words, so tool wording is not taken as
the report's claim.

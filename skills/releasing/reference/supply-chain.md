# Supply chain: SBOM, provenance and signing

Use these when a release produces an artifact (a package, a binary, a container image) or when
the owner asks for release evidence. Report what you produced and what you checked; label the
rest "not examined". An SBOM or an attestation shows what was built and where. It does not show
that the software is free of vulnerabilities.

## SBOM

A software bill of materials lists the components inside an artifact.

- Formats: [SPDX](https://spdx.dev/use/specifications/) and
  [CycloneDX](https://cyclonedx.org/specification/overview/). Use the one the consumer asks for.
- Generate it from the built artifact, not only from the lockfile, for example with
  [Syft](https://github.com/anchore/syft): `syft <image-or-dir> -o spdx-json > sbom.spdx.json`.
- GitHub can export a repository SBOM from the dependency graph
  ([Exporting an SBOM](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/exporting-a-software-bill-of-materials-for-your-repository)).
  That describes the repository's declared dependencies, not a built artifact.
- Attach the SBOM to the release or attest it (below), and name its file in the report.

## Provenance and attestations

Provenance records which source commit, workflow and builder made an artifact.
[SLSA](https://slsa.dev/spec/v1.0/levels) grades build tracks: Build L1 has provenance, L2 adds a
hosted build platform that signs it, L3 adds a hardened build platform
([SLSA provenance](https://slsa.dev/spec/v1.0/provenance)).

On GitHub Actions, the `actions/attest` action makes a signed build provenance attestation, and
with `sbom-path` an SBOM attestation
([Using artifact attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds)):

```yaml
permissions:
  id-token: write
  contents: read
  attestations: write
steps:
  - uses: actions/attest@<pinned-commit-sha>  # v4
    with:
      subject-path: dist/app.tar.gz
```

Check it after the release
([gh attestation verify](https://cli.github.com/manual/gh_attestation_verify)):

```bash
gh attestation verify dist/app.tar.gz -R <owner>/<repo>
gh attestation verify oci://ghcr.io/<owner>/<image>:<tag> -R <owner>/<repo>
```

Record the command, the artifact digest and the result. Without that output, write "not run".

## Signing

- **Tags and commits.** Sign release tags with `git tag -s` (GPG, SSH or X.509 keys;
  [Signing your work](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work)). Check a tag
  with `git tag -v <tag>`; this needs the signer's public key or an `allowedSignersFile` for SSH.
- **Artifacts and images.** [Sigstore cosign](https://docs.sigstore.dev/cosign/signing/overview/)
  signs with a short-lived certificate tied to the CI's OIDC identity (keyless). Check with
  `cosign verify` and pin the expected identity and issuer
  ([Verifying signatures](https://docs.sigstore.dev/cosign/verifying/verify/)):

  ```bash
  cosign verify ghcr.io/<owner>/<image>@sha256:<digest> \
    --certificate-identity-regexp '^https://github.com/<owner>/<repo>/' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
  ```

- Sign and verify by digest, never only by a tag that can move.

## What to report

| Item | Evidence | Label when missing |
| --- | --- | --- |
| SBOM | File name, format and artifact digest | "not produced" |
| Provenance | `gh attestation verify` output for the artifact digest | "not run" |
| Signature | `git tag -v` or `cosign verify` output | "not run" or "claimed" |
| Vulnerability status | A named scanner run with its date and findings | "not examined" |

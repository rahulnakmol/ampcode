# Criteria, evidence and scores

Pick the criteria the decision needs from this list, add your own, and agree the weights with the
decider before any product is scored. Use the IDs below in `criteria.json`, so readers of every
assessment find the same meaning.

This file says which evidence proves each criterion. It is an evidence check, **not legal advice
and not an audit**. A person with the right role reads contracts and audit reports and decides
whether they are adequate. Where a rule comes from a named standard, the standard is named. Where
no standard sets a value (for example the maximum age of a report), the assessment sets it and
records it with the score bands in the decision trail before the freeze. The freeze seals only
the criterion IDs and weights, not names or notes, so a threshold written into a criterion's
name is not protected.

## The score scale

Every criterion is scored from 0 to 5. Write what each band means for each criterion (for
example the cost bands in currency) into the decision trail before the freeze, so nobody can
move a band after seeing the scores.

| Score | Meaning |
| --- | --- |
| 5 | Meets the requirement fully |
| 4 | Meets it with minor gaps that need no workaround |
| 3 | Meets it with a workaround, a condition or extra cost |
| 2 | Partly meets it; a significant gap remains |
| 1 | A major gap; meets only a small part |
| 0 | Does not meet it, or the vendor refuses the evidence |

## Verified or claimed

Each score has a `status`:

- **verified**: you read the document named under "Proves it", or you ran the test yourself, and
  the evidence line says which document or test, and when.
- **claimed**: anything else. A trust-page badge, a questionnaire answer, a sales e-mail, a
  marketing page, a vendor-run demo of its own script, or a statement in a call.

A claimed score counts in the total, and `score.py` lists it as unverified. When a claim
decides the outcome, verify it or make it a condition of the recommendation. A refused document
is evidence too: score 0 and cite the refusal and its date.

## Functional and technical criteria

### Functional fit `fit`

- **Measures:** how well the product meets the agreed requirements, requirement by requirement.
- **Proves it:** a test in a sandbox, or a demo that you script and drive, against each
  requirement ID, with notes per requirement. The fit categories of `blueprinting`'s
  `reference/proposals.md` (supported, configuration, extension, process change, integration,
  unresolved) work as the record per requirement.
- **Claimed until:** you ran the step. A vendor's demo of its own script is a claim.
- **Score:** from the share of requirements (weighted by priority, when the requirements say so)
  that are supported or need only configuration. Agree the bands before the freeze.

### APIs `apis`

- **Measures:** whether the integrations you need can be built and kept running: documented
  operations, authentication, rate limits, webhooks or events, versioning and the deprecation
  notice period.
- **Proves it:** the API documentation, and calls you made in a sandbox for each needed
  integration. When `architecting` is installed, write each integration as a contract in its
  design format and score against those contracts.
- **Claimed until:** a call works in the sandbox. "Open API" on a feature page is a claim.

### Single sign-on `sso`

- **Measures:** sign-in through your identity provider with SAML 2.0 or OpenID Connect, whether
  SSO can be enforced for all users, and which plan includes it.
- **Proves it:** a sign-in test with your identity provider in a sandbox, and the plan in the
  written quote that includes SSO.
- **Claimed until:** the sign-in test passes on the plan you will buy.

### User provisioning `scim`

- **Measures:** creating, updating and removing users and groups from your identity provider
  with SCIM 2.0 (RFC 7643 and RFC 7644), and how fast removal takes away access.
- **Proves it:** a sandbox test: create a user, change a group, deactivate the user, then check
  that the user can no longer sign in or use an API token.
- **Claimed until:** that test passes. A logo in an identity provider's catalogue is a claim.

### Data residency `residency`

- **Measures:** where customer data, backups, logs and support access are located, including
  the sub-processors.
- **Proves it:** the clause in the contract, order form or data processing agreement that names
  the region, and the sub-processor list with locations. A region picker in the admin console
  proves only the primary storage.
- **Claimed until:** the region is in the contract text you would sign.

### Total cost `cost`

- **Measures:** all cost over the agreed period (for example 3 or 5 years): licences at the
  needed tier and quantity, the add-ons the other criteria need (SSO, SCIM, API limits, a
  sandbox), implementation, integration, data migration, training, running cost, renewal price
  increases and exit cost.
- **Proves it:** a written quote with tier, quantities and term, and your own estimate for
  internal effort with its basis (`blueprinting`'s `scripts/estimate.py` does the arithmetic).
- **Claimed until:** a written quote. A public price page is a claim.
- **Score:** lower cost scores higher. Agree the currency bands before the freeze.

### Exit risk `exit`

- **Measures:** how hard it is to leave: a complete export (records, history, attachments,
  audit logs) in documented formats, notice periods and fees, data return and deletion at the
  end, and dependence on features no other product has.
- **Proves it:** an export test in a sandbox, and the contract's termination, data-return and
  deletion clauses.
- **Claimed until:** the export test ran and the clauses were read.
- **Score:** lower risk scores higher. 5 means a full export was tested and the contract returns
  the data; 0 means there is no export.

## Security and compliance evidence

These four criteria check documents. When the product will hold sensitive data or cross a
trust boundary of yours, also model the integration with `threat-modelling` and check the
vendor's documents against the threats it lists. Without that skill, list the data flows and
trust boundaries by hand and label the list "manual, threat-modelling not installed".

### SOC 2 Type II report `soc2`

- **Measures:** whether an independent CPA firm examined, under the AICPA attestation
  standards, the design and operating effectiveness of the vendor's controls over a period,
  against the Trust Services Criteria. Security is always in scope; availability, processing
  integrity, confidentiality and privacy are included only when the report says so.
- **Proves it:** the SOC 2 Type II report itself, usually shared under a non-disclosure
  agreement. Read and cite:
  - the auditor's opinion, and whether it is qualified;
  - the period dates, and the bridge letter for any gap to today (a bridge letter is written by
    the vendor's management, so it is a claim, not audit evidence);
  - the system description: does it cover the service and the locations you will use;
  - the criteria included;
  - the exceptions in the test results, and management's responses;
  - the complementary user entity controls: the controls your team must run;
  - the subservice organizations, and whether they are carved out.
- **Claimed until:** you read the report. A SOC 2 badge, a "SOC 2 compliant" statement, a Type I
  report (one point in time, design only) or a SOC 3 report (a general-use summary without the
  test results) is not a Type II report. Score each for what it is.

### ISO/IEC 27001 certificate `iso27001`

- **Measures:** whether an accredited certification body certified the vendor's information
  security management system, and whether the certificate's scope covers the service you buy.
- **Proves it:** the certificate, checked for:
  - the edition: ISO/IEC 27001:2022. Under IAF MD 26, every certificate to the 2013 edition
    expired or was withdrawn by 31 October 2025;
  - the scope statement: the service, the organization and the sites you rely on;
  - the issue and expiry dates: a certificate runs a three-year cycle, with surveillance audits
    in the first and second years (ISO/IEC 17021-1, clause 9.1.3.2);
  - the status, confirmed in IAF CertSearch or with the certification body named on it;
  - the Statement of Applicability, when the vendor shares it: which Annex A controls apply.
- **Claimed until:** you saw the certificate and confirmed its status. A logo on a website is a
  claim.

### Penetration test summary `pentest`

- **Measures:** whether an independent tester recently tested the service you will use, and
  whether the findings were fixed.
- **Proves it:** a summary or attestation letter from the testing firm (or carrying its name)
  that states the test dates, the scope (applications, APIs, environments), the method, the
  number of findings by severity, and the remediation status with any retest date. No general
  standard sets the maximum age or the accepted severities for a vendor assessment. When one
  applies to the data, use its interval: for card data, PCI DSS v4.0.1 requirements 11.4.2 and
  11.4.3 require internal and external penetration tests at least once every 12 months and
  after any significant change. Otherwise agree them before the freeze.
- **Claimed until:** you read the tester's summary. "We test every year" is a claim. A summary
  with zero open findings shows only what that test covered on those dates; do not report it as
  "no vulnerabilities".

### Data processing terms `dpa`

- **Measures:** whether the vendor's data processing agreement covers what your privacy owner
  requires: the processing described, the sub-processors and how you learn of changes, the
  transfer mechanism when personal data leaves its region, breach notification, return and
  deletion at the end, and audit rights. Where the GDPR applies, Article 28 lists what a
  processor contract must contain.
- **Proves it:** the data processing agreement text you would sign, the sub-processor list, and
  the written finding of the person who owns privacy or legal review.
- **Claimed until:** that person read the text. "GDPR compliant" on a website is a claim. This
  check records evidence; it does not replace legal review.

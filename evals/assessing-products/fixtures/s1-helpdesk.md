# Help-desk tool: agreed criteria and evidence packets

**Decider:** Hanna Keller, Head of Customer Service. **Security lead:** Jonas Weber.
**Privacy owner:** Lea Fischer. **Finance systems lead:** Omar Haddad.

The company runs customer support for 120 agents in Germany and Austria. Its identity provider
is Microsoft Entra ID.

## Agreed on 2026-11-10 by Hanna Keller

Must-have (a gate before scoring): customer data stored in the EU, including backups.

| ID | Criterion | Weight | Score bands agreed |
| --- | --- | --- | --- |
| fit | Fit to requirements R1 to R10 | 35 | 5: all supported or configuration; 4: one gap with a workaround; 3: two or three; 2: four or five; 1: more; 0: none tested |
| soc2 | SOC 2 Type II report | 10 | 5: current report read, covers the service, no exception that affects us; lower for gaps; 0: refused |
| iso27001 | ISO/IEC 27001 certificate | 5 | 5: valid 2022 certificate, scope covers the service, status confirmed; 0: none valid |
| pentest | Penetration test summary | 10 | 5: tester's summary under 12 months old, no open high findings; lower for gaps |
| dpa | Data processing terms | 10 | 5: privacy owner accepts the DPA as offered; 3: accepts with changes; 0: not offered |
| sso | Single sign-on with Entra ID | 5 | 5: tested on the quoted plan; 0: not available |
| scim | SCIM provisioning from Entra ID | 5 | 5: create, change and deactivate tested; 0: not available |
| cost | Total cost over 3 years | 15 | 5: under 150,000 EUR; 4: under 175,000; 3: under 200,000; 2: under 225,000; 1: above |
| exit | Exit risk | 5 | 5: full export tested and data return in the contract; 0: no export |

## Northdesk

- Sandbox test 2026-11-12 (notes in the sandbox log): R1 to R9 supported or configuration; R10
  (SLA pause during customer wait) needs a workaround with a macro.
- SOC 2 Type II report, period 2025-09-01 to 2026-08-31, read by Jonas Weber on 2026-11-13:
  unqualified opinion; the system description covers the help-desk service in the EU region; one
  exception on access review timing, with a management response.
- ISO/IEC 27001:2022 certificate, issued 2025-03-02, expires 2028-03-01; scope "help-desk SaaS
  and supporting operations"; status active in IAF CertSearch, checked 2026-11-13.
- Penetration test summary from Brightline Security, test dates 2026-06-02 to 2026-06-13,
  application and API in scope; 0 high, 2 medium findings, both fixed and retested 2026-07-20.
- DPA read by Lea Fischer on 2026-11-14: accepted as offered. Sub-processor list: all in the EU.
- Data residency clause in the order form: EU (Frankfurt and Dublin), backups included.
- SSO with Entra ID (SAML) tested on the quoted "Professional" plan, 2026-11-12.
- SCIM: create and change tested; deactivate not tested yet.
- Written quote NQ-4410, 2026-11-11: 3-year total 182,000 EUR.
- Export test 2026-11-12: full CSV and API export of tickets with attachments. The contract
  returns data within 30 days of termination.

## Calyx Support

- Vendor-run demo 2026-11-11 of its standard script: R1 to R10 shown as supported. No sandbox
  was offered.
- Trust page, read 2026-11-11: "SOC 2 Type II certified". Report requested 2026-11-11; the
  vendor says it is "being finalized".
- ISO/IEC 27001:2013 certificate, issued 2023-01-15, expires 2026-01-14; scope "Calyx Ltd".
- Sales e-mail 2026-11-11: "We run penetration tests every year with a top-tier firm."
- DPA read by Lea Fischer on 2026-11-14: acceptable with two changes (breach notice within 48
  hours; prior notice of new sub-processors).
- Data residency clause in the draft order form: EU, backups included.
- SSO with SAML is available on the "Enterprise" plan only; the quote below is for "Growth".
- SCIM: Calyx appears in the Entra ID app gallery; not tested.
- Written quote CQ-0091, 2026-11-12, "Growth" plan: 3-year total 141,000 EUR. The "Enterprise"
  plan is 38,000 EUR more over 3 years (sales e-mail, 2026-11-12, no written quote).
- Export: the documentation describes a CSV export of tickets; not tested.

## Ferrum Help

- Sandbox test 2026-11-12: R1 to R8 supported; R9 and R10 not supported.
- SOC 2 Type II report, period 2025-04-01 to 2026-03-31, read by Jonas Weber on 2026-11-13:
  unqualified opinion; covers the service. Bridge letter from Ferrum's management to 2026-10-31.
- No ISO 27001 certificate.
- "Penetration test summary" PDF on Ferrum letterhead, dated 2026-09-01: "An independent firm
  tested our platform in August 2026. All findings were fixed." No tester named, no scope.
- DPA read by Lea Fischer on 2026-11-14: accepted as offered.
- Admin console offers region "EU" for the primary database. The sub-processor list names a US
  backup provider.
- SSO and SCIM with Entra ID tested 2026-11-12, including deactivate.
- Written quote FQ-77, 2026-11-11: 3-year total 158,000 EUR.
- Export test 2026-11-12: CSV export of tickets; attachments are not exported.

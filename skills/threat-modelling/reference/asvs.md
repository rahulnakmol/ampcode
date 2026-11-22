# OWASP ASVS 4.0.3

The OWASP Application Security Verification Standard (ASVS) lists security requirements to
review an application against. This skill reviews against version 4.0.3. Source:
https://github.com/OWASP/ASVS/tree/v4.0.3/4.0/en (read at tag `v4.0.3`).

## Reference form

ASVS 4.0.3 numbers each requirement `<chapter>.<section>.<requirement>`, for example `1.11.3`
("How to Reference ASVS Requirements" in `0x03-Using-ASVS.md`). This skill writes it with a
leading `V`, as the chapter and section headings do: `V2.1.1`. The model's `standard` field pins
the version, so `V2.1.1` in a model means what the standard writes as `v4.0.3-2.1.1`.

Identifiers change between ASVS versions. Do not mix references from another version in one
model. To review against another version, add its reference form to `STANDARDS` in
`scripts/threat_check.py` and to this file.

## Levels

ASVS 4.0.3 defines three levels (`0x03-Using-ASVS.md`): Level 1 for low assurance, Level 2 for
applications that contain sensitive data (recommended for most applications), and Level 3 for
the most critical applications. Each requirement lists the levels it applies to. Say the level
in the model's `summary`.

## Chapters and sections

| Chapter | Name | Sections |
| --- | --- | --- |
| V1 | Architecture, Design and Threat Modeling | V1.1 to V1.14 |
| V2 | Authentication | V2.1 Password Security to V2.10 Service Authentication |
| V3 | Session Management | V3.1 to V3.7 |
| V4 | Access Control | V4.1 General Access Control Design, V4.2 Operation Level Access Control, V4.3 Other Access Control Considerations |
| V5 | Validation, Sanitization and Encoding | V5.1 to V5.5 |
| V6 | Stored Cryptography | V6.1 to V6.4 |
| V7 | Error Handling and Logging | V7.1 Log Content to V7.4 Error Handling |
| V8 | Data Protection | V8.1 General Data Protection, V8.2 Client-side Data Protection, V8.3 Sensitive Private Data |
| V9 | Communication | V9.1 Client Communication Security, V9.2 Server Communication Security |
| V10 | Malicious Code | V10.1 to V10.3 |
| V11 | Business Logic | V11.1 Business Logic Security |
| V12 | Files and Resources | V12.1 File Upload to V12.6 SSRF Protection |
| V13 | API and Web Service | V13.1 Generic Web Service Security to V13.4 GraphQL |
| V14 | Configuration | V14.1 Build and Deploy to V14.5 HTTP Request Header Validation |

Requirement `V1.1.2` asks for threat modeling for every design change or sprint planning. The
model you are writing is not evidence for V1.1.2. Mark it `met` only when the sources show a
process that requires a model for every design change, such as a design template's `Threat
model:` line backed by a policy, and cite that source. Otherwise mark it `not examined`.

## Some requirements, with their subjects

This table is not the full list. It holds the requirements the example cites and a few common
ones, read in the v4.0.3 source. Each line names the requirement's subject. Before you cite any
requirement as `met`, quote it, or cite one not in this table, read its full text in the source;
do not quote a requirement from memory. A row of this table may be cited as `gap` or
`not examined` by its subject alone, or `not applicable` when its section's subject cannot occur;
do not rest that on a planned control. When no table row covers a threat's control, list its
chapter or section under `not_examined`. When you cannot read the source for anything else, list
the chapter or section as `not examined`.

| Reference | Subject |
| --- | --- |
| V1.1.2 | Threat modeling for every design change or sprint planning |
| V2.1.1 | User-set passwords at least 12 characters |
| V2.10.1 | Intra-service secrets do not rely on unchanging credentials |
| V2.10.4 | Passwords, integrations and API keys managed securely, not in source code |
| V3.5.3 | Stateless session tokens protected against tampering, replay and key substitution |
| V4.2.1 | Sensitive data and APIs protected against insecure direct object reference |
| V7.1.1 | Do not log credentials or payment details; session tokens only in an irreversible, hashed form |
| V7.1.2 | Do not log other sensitive data as defined under local privacy laws or relevant security policy |
| V7.1.4 | Each log event has the information needed to investigate a timeline |
| V8.3.3 | Clear language on the use of personal information, and opt-in consent |
| V8.3.8 | Retention classification for sensitive personal information |
| V9.1.1 | TLS for all client connectivity, with no fallback to unencrypted communication |
| V11.1.4 | Anti-automation controls against excessive calls such as mass data exfiltration |
| V12.1.1 | Do not accept large files that could fill up storage or cause a denial of service |
| V13.1.3 | API URLs do not expose sensitive information such as API keys or session tokens |
| V13.1.4 | Authorization decisions at both the URI and the resource level |
| V14.2.1 | All components up to date |
| V14.4.5 | Strict-Transport-Security header on all responses |

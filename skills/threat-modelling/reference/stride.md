# STRIDE per crossing flow

STRIDE names six kinds of threat, each the violation of one security property. It comes from
Microsoft (Loren Kohnfelder and Praerit Garg, 1999) and is the threat list of the Microsoft
Threat Modeling Tool
(https://learn.microsoft.com/azure/security/develop/threat-modeling-tool-threats).

This skill applies STRIDE to every flow that crosses a trust boundary. For each category, list
the threat IDs, or write `n/a: <reason>`. A reason says why the threat cannot happen on this
flow, or which threat elsewhere already covers it ("request volume is T5"). "Not relevant", "not
applicable", "irrelevant", "handled elsewhere" or "none" alone is not a reason: the check fails it
(M3, and M4 for LINDDUN).

'Not examined' is not an `n/a` reason. When a category on an in-scope flow was not examined,
write a threat for it (a backlog item to examine it is enough). The check fails an `n/a` reason
that says "not examined" or "unexamined" (any case) and names no threat ID of the model.

| Key | Category | Property violated | Ask on the flow |
| --- | --- | --- | --- |
| `spoofing` | Spoofing | Authentication | Can a sender or receiver pretend to be someone else? How does each end prove who it is? |
| `tampering` | Tampering | Integrity | Can the data be changed in transit, or before it is read, by someone not allowed to? |
| `repudiation` | Repudiation | Non-repudiation | Can a party deny an action this flow causes? Is there a record that ties the action to it? |
| `information_disclosure` | Information disclosure | Confidentiality | Can someone read data on this flow, or in its errors, logs, links or metadata, that they should not? |
| `denial_of_service` | Denial of service | Availability | Can a sender exhaust the receiver: volume, size, cost, slow requests, retries? |
| `elevation_of_privilege` | Elevation of privilege | Authorization | Can a party gain rights it was not given: another tenant's data, an admin action, code execution? |

## Usual controls

These are starting points, not proof. Each control in a model needs a verification.

| Category | Controls to consider |
| --- | --- |
| Spoofing | Strong authentication for people and workloads, short-lived tokens, workload identity instead of static secrets, mutual TLS between services |
| Tampering | TLS, signatures or message authentication codes, input validation at the receiver, least-privilege write access |
| Repudiation | Audit events with who, what, when (UTC) and result, protected from change by the actor |
| Information disclosure | Authorization on every object, encryption in transit and at rest, no secrets in URLs or logs, data minimization |
| Denial of service | Rate limits and quotas per caller, size limits, timeouts, queues with backpressure |
| Elevation of privilege | Server-side authorization on every request, tenant taken from the credential, least privilege, safe parsing |

## Pitfalls

- Writing `n/a` for repudiation on every flow. Ask who could deny the action and what would
  prove it.
- Treating a flow inside one zone as safe. STRIDE is required only on crossings, but a threat
  you see inside a zone still belongs in the model.
- Naming a control without a verification. The check fails it (M8).

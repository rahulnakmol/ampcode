# Design file format

A design is one Markdown file. `scripts/design_check.py` reads it and checks rules D1 to D9.
Copy the skeleton, fill it, and run the check. The filled example at the end passes.

## Sections

Use these `##` headings, each once. Other sections (Risks, Rollout, Open questions) may follow.

| Section | Holds | Checked |
| --- | --- | --- |
| `## Context` | The system, its users and the outside systems it talks to | D9: present, not empty |
| `## Containers` | Each deployable unit or data store, its technology and what it owns | D9: present, not empty |
| `## Contracts` | Each interface and data contract: API, event, file, table or prompt/tool contract | D6: present, not empty |
| `## Decisions` | One `### ADR-n: <title>` subsection per decision | D4, D5, D7, D9 |
| `## Non-functional requirements` | One table: `ID \| Quality \| Target \| Verification` | D1, D2, D3, D7, D9 |
| `## Trust boundaries` | The two trust lines below | D8 |

Draw Context and Containers as text tables or square-corner text diagrams (`┌ ─ ┐ │ └ ┘`).
Do not use Mermaid: the check rejects a `mermaid` code fence (D9).

## Rules

| Rule | Fails when |
| --- | --- |
| D1 | An NFR target has no number |
| D2 | An NFR target has no number followed by an accepted unit outside its condition |
| D3 | An NFR verification cell is empty, a `<...>` placeholder, or only placeholder words (`-`, `TBD`, `TODO`, `TBC`, `n/a`, `none`, `later`, `not yet`), even with `*`, backticks, `/` or trailing punctuation |
| D4 | An ADR lists fewer than two options under `Options:`. Only the shallowest list items count; nested pro and con bullets do not |
| D5 | An ADR has no `Status:` from the list below, no `Decision:` or no `Consequences:` |
| D6 | There is no `## Contracts` section, or it is empty |
| D7 | An NFR ID or an ADR ID appears twice |
| D8 | The `Trust boundaries change:` line is missing or not `yes`/`no`; or it says `yes` and `Threat model:` is a placeholder (as in D3) or has no path or link |
| D9 | A required section is missing or repeated, the NFR table or an ADR heading is malformed, there are no NFRs or ADRs, a line that starts with an `NFR-n` ID (after any `\|`, list marker, heading mark or emphasis) sits anywhere outside the first NFR table, above or below it, a line after the first NFR table, inside the Non-functional requirements section, starts with `\|` or names an `NFR-n`, or a Mermaid fence is used. An `NFR-n` cited inside a sentence elsewhere, such as "to meet NFR-1", is allowed |

### NFR table

- **ID:** `NFR-1`, `NFR-2` and so on. IDs are stable: never renumber, never reuse. `monitoring`
  turns each ID into an SLO, and tests and briefs cite it.
- **Quality:** the attribute, from [nfr-catalogue.md](nfr-catalogue.md).
- **Target:** a number with a unit, and the condition: "p95 under 300 ms at 200 req/s".
- **Verification:** the test that proves it: the kind, the tool or method, where and when.

A target passes D2 when a number is followed by an accepted unit outside its condition. The
condition runs from `at`, `when`, `while`, `with`, `during`, `given` or `under ... load` to its
first number and unit, as in "at 50 req/s" or "when 10,000 users". `for`, `per`, `across` and
`over` start a condition only before a rate or a count (a load or scope), as in "for 50 req/s"
or "across 10,000 tenants"; "kept for 30 days" stays the target. `at most`, `at least` and a
number with no unit ("Recall at 10") do not start a condition. So "p95 under 300 at 50 req/s"
fails: its only unit belongs to the condition. "p95 under 300 ms at 50 req/s" passes.
A thousands separator and a multiplier are allowed: `10,000 users`, `10k users`, `1.5 s`,
`99.9 %`, `99.9%`, `400 USD/month`. Units are case-insensitive. To add a unit, change `UNITS`
in the script and this line together; a test compares them.

Accepted units: `ms`, `s`, `sec`, `seconds`, `min`, `minutes`, `h`, `hours`, `d`, `days`, `weeks`, `months`, `years`, `%`, `req/s`, `req/min`, `rps`, `rpm`, `qps`, `tps`, `msg/s`, `events/s`, `errors/min`, `errors/h`, `users`, `sessions`, `tenants`, `connections`, `requests`, `messages`, `events`, `records`, `rows`, `items`, `files`, `violations`, `incidents`, `findings`, `defects`, `KB`, `MB`, `GB`, `TB`, `PB`, `KiB`, `MiB`, `GiB`, `TiB`, `Mbps`, `Gbps`, `MB/s`, `GB/s`, `USD`, `EUR`, `GBP`

### ADR subsection

Write the fields as plain lines. `Options:` is followed by a list. See [adr.md](adr.md).

- **Status:** `proposed`, `accepted`, `rejected`, `deprecated` or `superseded` (for example
  `superseded by ADR-4`).
- **Options:** at least two, the chosen one included. "Do nothing" counts when it is real.
- **Decision:** the option chosen and why.
- **Consequences:** what becomes easier and what becomes harder; what evidence would reverse it.

### Trust lines

```text
Trust boundaries change: yes
Threat model: docs/threat-models/order-export.md
```

`yes` when the change adds or moves an actor, an entry point, a credential, a tenant or network
boundary, or a flow of sensitive data across one. Then `Threat model:` names a path or a link
(`https://...`, `[text](path)`, or a path such as `docs/threat-model.md`). With `no`, write
`Threat model: none`.

## Skeleton

````markdown
# Design: <name>

Intent: <link to the confirmed brief>
Status: draft

## Context

| Actor or system | Uses | Through |
| --- | --- | --- |
| <actor> | <system> | <channel> |

## Containers

| Container | Technology | Owns |
| --- | --- | --- |
| <container> | <technology> | <data or behaviour> |

## Contracts

| Contract | Kind | Producer | Consumer | Shape and compatibility |
| --- | --- | --- | --- | --- |
| <name> | <HTTP API, event, file, table> | <owner> | <user> | <fields and errors>; Compatibility: <versioning or change rule> |

## Decisions

### ADR-1: <decision>

Status: proposed
Options:
- <option A>
- <option B>
Decision: <choice and why>
Consequences: <easier, harder, what would reverse it>

## Non-functional requirements

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-1 | <quality> | <number and unit, under a condition> | <test, tool, where, when> |

## Trust boundaries

Trust boundaries change: <yes or no>
Threat model: <path or link, or none>
````

## Filled example

A B2B SaaS adds a tenant-facing order export. It passes `design_check.py`.

````markdown
# Design: tenant order export

Intent: docs/briefs/order-export.md (confirmed 12 November 2026)
Status: draft

## Context

| Actor or system | Uses | Through |
| --- | --- | --- |
| Tenant administrator | Order app | Browser over HTTPS, single sign-on |
| Tenant integration | Export API | HTTPS with an OAuth client credential |
| Order app | Object storage | Signed download links |

## Containers

```text
┌──────────────┐  HTTPS   ┌──────────────┐  queue  ┌───────────────┐
│ Order web UI │─────────▶│  Orders API  │────────▶│ Export worker │
└──────────────┘          └──────┬───────┘         └───────┬───────┘
                                 │ SQL                     │ write file
                          ┌──────▼───────┐         ┌───────▼───────┐
                          │  PostgreSQL  │         │ Object storage│
                          └──────────────┘         └───────────────┘
```

| Container | Technology | Owns |
| --- | --- | --- |
| Orders API | ASP.NET Core 9 | Orders, export jobs |
| Export worker | .NET background service | Building export files |
| Object storage | Azure Blob Storage, one container per tenant | Export files for 7 days |

## Contracts

| Contract | Kind | Producer | Consumer | Shape and compatibility |
| --- | --- | --- | --- | --- |
| POST /v1/exports | HTTP API | Orders API | Web UI, tenant integrations | `{from, to, format}` in; 202 with `exportId`; 409 on a duplicate `Idempotency-Key`; Compatibility: `/v1` changes are additive only, a breaking change is `/v2` and `/v1` stays 6 months |
| GET /v1/exports/{id} | HTTP API | Orders API | Web UI, tenant integrations | Status and a signed link valid for 15 minutes; tenant taken from the token, never the path; Compatibility: as `POST /v1/exports` |
| export.requested v1 | Event | Orders API | Export worker | `exportId`, `tenantId`, range; Compatibility: additive changes only, new fields optional |
| Export file v1 | CSV file | Export worker | Tenants | Header row; UTF-8; Compatibility: columns fixed per version, new columns only in a new version |

## Decisions

### ADR-1: Build exports in a background worker

Status: accepted
Options:
- Background worker fed by a queue
- Build the file inside the API request
- Nightly batch for all tenants
Decision: Background worker. Large ranges take minutes and must not hold a request open.
Consequences: Retries need the idempotency key; one more process to deploy and watch. Reverse if
p95 export size stays under 5 MB for a quarter.

### ADR-2: Deliver files by signed links

Status: proposed
Options:
- Short-lived signed links to object storage
- Stream the file through the API
Decision: Signed links, valid for 15 minutes, scoped to one file.
Consequences: Less load on the API; a leaked link works until it expires, so it stays short.

## Non-functional requirements

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-1 | Latency | POST /v1/exports p95 under 300 ms at 50 req/s | k6 load test in staging before each release |
| NFR-2 | Throughput | 1,000,000 rows exported within 5 min | Timed export of a seeded tenant in staging, each release |
| NFR-3 | Availability | Export API 99.9 % each month, excluding announced maintenance | Synthetic probe every minute in production; monthly availability report |
| NFR-4 | Isolation | 0 findings of cross-tenant file access, for every export ID and link | Automated integration test in CI on each change: tenant A requests tenant B's export ID and link, expects 404 |
| NFR-5 | Retention | Export files deleted within 7 days of creation | Lifecycle rule test in staging each release; weekly scan in production for files older than 7 days |

## Trust boundaries

Trust boundaries change: yes
Threat model: docs/threat-models/order-export.md
````

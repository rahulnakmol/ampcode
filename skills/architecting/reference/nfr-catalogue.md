# NFR catalogue

Quality attributes for the `## Non-functional requirements` table, with example measurable
targets and how to test each one. The examples are shapes, not defaults: set every number from
the workload, the user's objectives and the cost limit, and say where the number came from.

## Write a good NFR

- **One quality, one number.** Split "fast and available" into two rows.
- **Number, unit, condition.** "p95 under 300 ms at 200 req/s with 10,000 tenants", not
  "under 300 ms". State the percentile, the load and the measurement window.
- **A test that can fail.** Name the kind of test, the tool or method, the environment and when
  it runs. "Monitored" is not a test; "alert fires when p95 exceeds 300 ms for 5 min" is.
- **Stable IDs.** `NFR-1`, `NFR-2` … never renumbered or reused. `monitoring` turns each ID into
  an SLO with an alert; tests and briefs cite the ID.
- **Units** come from the "Accepted units" line in [design-template.md](design-template.md).
- **Evidence or label.** A target is a requirement. Until its test has run on the real system,
  report it as "not proven".

## Catalogue

| Quality | Example target | How to test it |
| --- | --- | --- |
| Latency | p95 under 300 ms for GET /orders at 200 req/s | Load test (k6, Gatling, JMeter) in a production-like environment before each release; SLO alert in production |
| Throughput | 500 req/s sustained for 30 min with error rate under 0.1 % | Soak test at the target rate in staging before each release; compare with the capacity model |
| Availability | 99.9 % successful requests each month, excluding announced maintenance | Synthetic probes every minute in production; monthly report from production request logs |
| Error rate | under 5 errors/min of HTTP 5xx at peak load | Production SLO alert; failure-injection test in staging before each release |
| Recovery time (RTO) | Service restored within 1 h after a region loss | Disaster-recovery exercise twice a year; time it from the start of failover |
| Data loss (RPO) | At most 15 min of committed data lost after a primary failure | Restore a production backup to a clean recovery environment each quarter; compare the last record with the source |
| Durability and backup | Daily backup restored and checked within 4 h, at full production data size | Automated restore test into a recovery environment each month |
| Scalability | 10,000 tenants with p95 latency still under the latency NFR at peak load | Load test in staging with a seeded tenant count before each major release; scaling trigger written in an ADR |
| Capacity and growth | Storage under 2 TB after 3 years at forecast growth | Capacity model reviewed each quarter against growth measured in production |
| Data freshness | Dashboard data at most 15 min behind the source during business hours | Freshness probe in production every 5 min: write a marker record, measure when it appears; same probe in staging before release |
| Dashboard and query latency | p95 dashboard load under 3 s for 50 concurrent users at production data volume | Load test with recorded queries against a production-sized test workspace before each release |
| Retrieval relevance (RAG) | Recall at 10 of at least 90 % on the evaluation set, for the current index | Offline evaluation in CI on representative and adversarial questions, on each model or index change |
| Citation accuracy | At least 95 % of cited passages support their claim, on the evaluation set | Graded evaluation in CI with a judge and a fixed rubric on each model change; monthly sample human review of production answers |
| Isolation (multi-tenant) | 0 findings of cross-tenant data access, on every tenant-scoped route and store | Automated integration tests in CI on each change that request another tenant's data by ID, link and search; yearly penetration test of production |
| Security patching | Critical vulnerabilities fixed within 7 days of disclosure | Scanner report in CI on each build; weekly report of the age of open production findings |
| Authentication and sessions | Session tokens expire after 60 min of inactivity, for every client type | Automated integration test in CI with a clock skew; configuration check in CI on each change |
| Privacy and deletion | A deletion request removed from stores, indexes and caches within 30 days of the request | End-to-end test in staging before each release: delete a seeded subject, search every store and index |
| Audit | Audit records kept 7 years; 0 gaps in sequence per day | Retention policy test in CI on each change; daily gap check on the production audit log |
| Accessibility | 0 violations of critical severity against WCAG 2.2 AA on key journeys, at 320 px and 1280 px widths | Automated axe run in CI on each change plus a manual screen-reader pass in staging per release |
| Mobile start and stability | Cold start under 2 s on a mid-range device; 99.5 % crash-free sessions each week | Device-lab test per release; crash reporting in production |
| Offline sync | Changes made offline sync within 60 s of reconnect, 0 lost records, after up to 24 h offline | Automated test on an emulator in CI toggling the network, on each change |
| Deployability | Deploy to production in under 15 min; rollback in under 10 min, for a normal release | Timed production pipeline runs on each release; a rollback drill in staging each quarter |
| Observability | An outage detected within 5 min, at any hour | Failure injection in staging each quarter; measure time to the first alert |
| Cost | Hosting under 2,000 USD/month at forecast load | Cost estimate from the provider calculator before build; monthly billing report for the production resources against the target |
| Maintainability | CI build and tests under 10 min on the main branch | CI timing on each main-branch run; trend reviewed each month |

## From NFR to monitoring

An NFR that can be measured in production becomes an SLO in `monitoring`, keyed by the same ID:
the indicator (what is measured), the objective (the target), the window, the alert and the
runbook. An NFR that can only be tested before release (for example accessibility or recovery
time) keeps its test and its schedule instead. Say which kind each NFR is in its Verification
cell.

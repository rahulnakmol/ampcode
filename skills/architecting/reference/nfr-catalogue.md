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
| Throughput | 500 req/s sustained for 30 min with error rate under 0.1 % | Soak test at the target rate; compare with the capacity model |
| Availability | 99.9 % successful requests each month | Synthetic probes every minute; monthly report from request logs |
| Error rate | under 5 errors/min of HTTP 5xx at peak | Production SLO alert; failure-injection test in staging |
| Recovery time (RTO) | Service restored within 1 h after a region loss | Disaster-recovery exercise twice a year; time it from the start of failover |
| Data loss (RPO) | At most 15 min of committed data lost | Restore a backup to a clean environment; compare the last record with the source |
| Durability and backup | Daily backup restored and verified within 4 h | Scheduled automated restore test each month |
| Scalability | 10,000 tenants with p95 latency still under the latency NFR | Load test with a seeded tenant count; scaling trigger written in an ADR |
| Capacity and growth | Storage under 2 TB after 3 years at forecast growth | Capacity model reviewed each quarter against measured growth |
| Data freshness | Dashboard data at most 15 min behind the source | Freshness probe: write a marker record, measure when it appears |
| Dashboard and query latency | p95 dashboard load under 3 s for 50 concurrent users | Load test on the semantic layer with recorded queries |
| Retrieval relevance (RAG) | Recall at 10 of at least 90 % on the evaluation set | Offline evaluation on representative and adversarial questions, each model or index change |
| Citation accuracy | At least 95 % of cited passages support their claim | Graded evaluation set; a judge with a fixed rubric; sample human review |
| Isolation (multi-tenant) | 0 findings of cross-tenant data access | Automated tests that request another tenant's data by ID, link and search; penetration test |
| Security patching | Critical vulnerabilities fixed within 7 days | Scanner report in CI; age of open findings tracked weekly |
| Authentication and sessions | Session tokens expire after 60 min of inactivity | Automated test with a clock skew; configuration check in CI |
| Privacy and deletion | A deletion request removed from stores, indexes and caches within 30 days | End-to-end test: delete a seeded subject, search every store and index |
| Audit | Audit records kept 7 years; 0 gaps in sequence | Retention policy test; daily gap check on the audit log |
| Accessibility | 0 critical violations against WCAG 2.2 AA on key journeys | Automated axe run in CI plus a manual screen-reader pass per release |
| Mobile start and stability | Cold start under 2 s on a mid-range device; 99.5 % crash-free sessions | Device-lab test per release; crash reporting in production |
| Offline sync | Changes made offline sync within 60 s of reconnect, 0 lost records | Automated test toggling network on a device or emulator |
| Deployability | Deploy to production in under 15 min; rollback in under 10 min | Timed pipeline runs; a rollback drill each quarter |
| Observability | An outage detected within 5 min | Failure injection in staging; measure time to the first alert |
| Cost | Hosting under 2,000 USD/month at forecast load | Cost estimate from the provider calculator, then monthly billing report against the target |
| Maintainability | CI build and tests under 10 min | CI timing on the main branch; trend reviewed each month |

## From NFR to monitoring

An NFR that can be measured in production becomes an SLO in `monitoring`, keyed by the same ID:
the indicator (what is measured), the objective (the target), the window, the alert and the
runbook. An NFR that can only be tested before release (for example accessibility or recovery
time) keeps its test and its schedule instead. Say which kind each NFR is in its Verification
cell.

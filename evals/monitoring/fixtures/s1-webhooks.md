# Design excerpt: tenant webhooks

From the approved design `docs/designs/webhooks.md` (revision 3, 14 November 2026). Only the
parts the monitoring step needs are copied here.

## Facts

- Webhook delivery runs on Kubernetes. Metrics go to Prometheus; alerts route through
  Alertmanager to the on-call pager (`severity: page`) or the team queue (`severity: ticket`).
  Dashboards are in Grafana.
- Metrics already exported:
  - `webhook_deliveries_total{job="webhook-worker", outcome="delivered|failed|timeout"}`, and
    `webhook_delivery_seconds_bucket{job="webhook-worker"}` (a histogram, with a bucket at 60 s);
  - `http_requests_total{job="subscription-api", code="..."}` for the subscription API.
- A staging cluster exists with the same Prometheus and Alertmanager setup. Its Alertmanager
  sends to a test pager schedule.
- Traffic: about 30 deliveries a second at the month-end peak, about 2 a second at night.
- No alert has been tested yet.

## Non-functional requirements

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-1 | Delivery latency | 99 % of webhook events delivered within 60 s, each month | Load test in staging before each release; SLO alert in production |
| NFR-2 | Availability | Subscription API 99.9 % successful requests (status below 500) each month | Synthetic probe every minute in production; SLO alert in production |
| NFR-3 | Accessibility | 0 critical WCAG 2.2 AA violations on the subscription pages | axe run in CI on each change |
| NFR-4 | Data loss (RPO) | At most 15 min of delivery records lost after a database failure | Restore drill each quarter |

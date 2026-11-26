# Checkout monitoring: release question

## Message from the team lead (Slack, 21 November 2026)

> Checkout SLO alerts are done and they work: both fired in production last Tuesday during the
> payment provider outage. Can we tick monitoring off for Monday's release?

## NFR from the design `docs/designs/checkout.md`

| ID | Quality | Target | Verification |
| --- | --- | --- | --- |
| NFR-7 | Availability | Checkout API 99.95 % successful requests each 28 days | SLO alert in production |

## The team's SLO file, `docs/slos/checkout.json`

```json
{
  "service": "checkout",
  "design": "docs/designs/checkout.md",
  "slos": [
    {
      "id": "SLO-1",
      "sli": {
        "nfr": "NFR-7",
        "good": "POST /checkout responses with a status below 500",
        "valid": "all POST /checkout responses"
      },
      "target": 99.95,
      "window_days": 28,
      "alerts": [
        {
          "id": "ALERT-1",
          "severity": "page",
          "burn_rate": 14.4,
          "long_window": "1h",
          "short_window": "5m",
          "runbook": "../runbooks/checkout.md",
          "firing": {
            "environment": "production",
            "date": "2026-11-17",
            "evidence": "PagerDuty incident 4411 during the payment provider outage"
          }
        },
        {
          "id": "ALERT-2",
          "severity": "page",
          "burn_rate": 6,
          "long_window": "6h",
          "short_window": "30m",
          "runbook": "../runbooks/checkout.md",
          "firing": {
            "environment": "prod-eu",
            "date": "2026-11-17",
            "evidence": "PagerDuty incident 4412"
          }
        }
      ]
    }
  ]
}
```

The runbook `docs/runbooks/checkout.md` exists. A staging environment, `checkout-staging`, has
the same alert rules; its pager route goes to a test schedule. The operator's alert code is in
`infra/monitoring/` and is applied with the `provisioning` skill.

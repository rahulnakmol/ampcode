# Platforms

How each platform expresses the fast and slow burn-rate pairs from
[burn-rates.md](burn-rates.md), where the alert lives as code, and how to show it fires outside
production. Every query and expression below is a shape to adapt, with the document it follows.
Product features change: check the linked page before you rely on one, and label a feature you
did not check "not examined". Links were read on 2026-11-22.

The alerts, dashboards and probes are code. `provisioning` previews and applies that code;
this skill writes it and the SLO file. Metric, table and label names below are examples: use your
own.

## Azure Monitor

- **Native SLOs.** Azure Monitor service level indicators belong to a service group. They take a
  baseline (the SLO), an evaluation period, and optional fast and slow burn-rate alerts that
  notify an action group. Check whether service groups are available in your tenant before you
  rely on them:
  https://learn.microsoft.com/azure/azure-monitor/fundamentals/service-level-indicators-create
- **Log search alert.** Without native SLIs, write one log search alert rule
  (`Microsoft.Insights/scheduledQueryRules`) per pair. The query below computes both windows of
  the fast pair over Application Insights requests and returns a row only when both are over
  the threshold. Set the rule to fire when the result count is above 0, its window to the long
  window (1 hour) and its frequency to 5 minutes. Check the allowed window and frequency values
  in the rule reference:
  https://learn.microsoft.com/azure/templates/microsoft.insights/scheduledqueryrules and
  https://learn.microsoft.com/azure/azure-monitor/alerts/alerts-create-log-alert-rule

  ```kusto
  // Fast pair for a 99.9 % SLO: 14.4 x 0.1 % = 1.44 % errors over 1 hour and over 5 minutes.
  let threshold = 14.4 * (1 - 0.999);
  AppRequests
  | where TimeGenerated > ago(1h) and Name startswith "POST /v1/exports"
  | extend bad = toint(ResultCode) >= 500
  | summarize longBad = sumif(ItemCount, bad), longAll = sum(ItemCount),
      shortBad = sumif(ItemCount, bad and TimeGenerated > ago(5m)),
      shortAll = sumif(ItemCount, TimeGenerated > ago(5m))
  | where longBad > threshold * longAll and shortBad > threshold * shortAll
  ```

  Columns (`ResultCode` is a string, `ItemCount` counts sampled items):
  https://learn.microsoft.com/azure/azure-monitor/reference/tables/apprequests.
  `sumif()`: https://learn.microsoft.com/kusto/query/sumif-aggregation-function.
  Count `ItemCount`, not rows, when sampling is on.
- **Firing outside production.** Deploy the same rule to the staging workspace and inject
  errors there. The action group test sends a sample alert with mocked data: it proves the
  notification path, not the rule:
  https://learn.microsoft.com/cli/azure/monitor/action-group/test-notifications

## CloudWatch

- **Native SLOs.** CloudWatch Application Signals SLOs are period-based or request-based, with
  an attainment goal and an interval. Each SLO can have burn rates with a look-back window and a
  burn-rate alarm on each. AWS gives the threshold as X % × interval length ÷ look-back window:
  2 % × 720 hours ÷ 1 hour = 14.4. For the pairs, AWS recommends a composite alarm over a long
  and a short look-back window, following the workbook:
  https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html
- **Composite alarm.** The rule fires only when both child alarms are in ALARM:

  ```text
  ALARM("order-export-burn-1h") AND ALARM("order-export-burn-5m")
  ```

  Syntax: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html
- **As code.** CloudFormation `AWS::ApplicationSignals::ServiceLevelObjective`
  (https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationsignals-servicelevelobjective.html)
  and `AWS::CloudWatch::CompositeAlarm`
  (https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudwatch-compositealarm.html),
  or the matching Terraform resources.
- **Firing outside production.** In a staging account, `aws cloudwatch set-alarm-state
  --alarm-name <name> --state-value ALARM --state-reason "fire drill"` sets the state for testing
  and runs the alarm's actions. It proves the actions, not the metric or the threshold; inject
  errors as well: https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/set-alarm-state.html

## Cloud Monitoring

- **Native SLOs.** Google Cloud Monitoring defines services and SLOs. An alerting policy on an
  SLO uses the `select_slo_burn_rate` selector with the SLO's resource name and a lookback
  period: https://cloud.google.com/stackdriver/docs/solutions/slo-monitoring/api/timeseries-selectors

  ```text
  select_slo_burn_rate("projects/PROJECT_ID/services/SERVICE_ID/serviceLevelObjectives/SLO_ID", "3600s")
  ```

- **The pair.** Put two threshold conditions in one policy: the selector with `"3600s"` and
  with `"300s"`, each `COMPARISON_GT` with `thresholdValue` 14.4, and set `combiner` to `AND`.
  Fields: https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies.
  Google's own guide suggests other starting thresholds (10× and 2×); this skill keeps the
  workbook pairs: https://cloud.google.com/stackdriver/docs/solutions/slo-monitoring/alerting-on-budget-burn-rate
- **24-hour limit.** Google's page says burn-rate alerts cannot use a compliance (lookback)
  period longer than 24 hours. The fast and slow pairs fit (at most 6 hours), and so does the
  workbook's 3× ticket pair over 24 hours and 2 hours. The 1× ticket pair over 3 days and
  6 hours cannot be built with `select_slo_burn_rate`; use the 3× pair instead, or say that
  this alert is not built:
  https://cloud.google.com/stackdriver/docs/solutions/slo-monitoring/alerting-on-budget-burn-rate
- **As code.** Terraform `google_monitoring_slo` and `google_monitoring_alert_policy`:
  https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
- **Firing outside production.** Create the same SLO and policy in a staging project and inject
  errors there.

## Prometheus

- **Rules.** Record the error ratio per window, then alert on both windows of a pair. The shape
  follows the workbook's example. Keep `by (job)` so the `job` label survives the sum:
  https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/ and
  https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/

  ```yaml
  groups:
    - name: order-export-slo
      rules:
        - record: job:slo_errors_per_request:ratio_rate1h
          expr: |
            sum by (job) (rate(http_requests_total{job="order-export", code=~"5.."}[1h]))
            /
            sum by (job) (rate(http_requests_total{job="order-export"}[1h]))
        # Record ratio_rate5m, ratio_rate30m and ratio_rate6h the same way.
        - alert: OrderExportFastBurn
          expr: |
            job:slo_errors_per_request:ratio_rate1h{job="order-export"} > (14.4 * 0.001)
            and
            job:slo_errors_per_request:ratio_rate5m{job="order-export"} > (14.4 * 0.001)
          labels:
            severity: page
            slo: SLO-1
          annotations:
            runbook_url: https://example.com/runbooks/order-export.md
  ```

- **Routing.** Alertmanager routes on the `severity` label: page or ticket.
- **Firing outside production.** `promtool test rules test.yml` feeds synthetic series to the
  rules and checks which alerts fire at a given time. Record it as a rule test with the CI run:
  https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/. It proves the
  expression; a staging fire drill also proves the route to the receiver.

## Grafana

- **Grafana SLO.** The Grafana SLO app creates burn-rate alert rules in Grafana Alerting.
  Fast-burn alerts (`grafana_slo_severity="critical"`) fire at 14.4× over 5 minutes and 1 hour,
  or 6× over 30 minutes and 6 hours. Slow-burn alerts (`"warning"`) fire at 3× over 2 hours and
  24 hours, or 1× over 6 hours and 72 hours:
  https://grafana.com/docs/plugins/grafana-slo-app/latest/set-up/configure-burn-rate-notifications/
- **Grafana Alerting as code.** Provision rule groups and contact points from files (not
  available in Grafana Cloud) or with the Terraform resources `grafana_rule_group` and
  `grafana_contact_point`:
  https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning
  and https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/terraform-provisioning
- **Dashboards as code.** Provision dashboard JSON from files:
  https://grafana.com/docs/grafana/latest/administration/provisioning/
- **Firing outside production.** A contact point test sends a test notification; it proves the
  route only:
  https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points
  For the rule, inject errors in a staging data source.

## Synthetic checks

A synthetic check sends steady, known traffic. It finds outages when real traffic is low, and it
gives a fire drill a clean signal.

| Platform | Synthetic check | Documentation |
| --- | --- | --- |
| Azure Monitor | Application Insights availability tests | https://learn.microsoft.com/azure/azure-monitor/app/availability |
| CloudWatch | CloudWatch Synthetics canaries | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html |
| Cloud Monitoring | Uptime checks | https://cloud.google.com/monitoring/uptime-checks |
| Prometheus | Blackbox exporter probes | https://github.com/prometheus/blackbox_exporter |
| Grafana | Grafana Cloud Synthetic Monitoring | https://grafana.com/docs/grafana-cloud/testing/synthetic-monitoring/ |

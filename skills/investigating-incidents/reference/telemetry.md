# Telemetry: sources, pitfalls and bounded query templates

Read this with section 1 of `SKILL.md`. The templates are starting points for the caller to run
or adapt. They are not results: never report a template as an executed query. Each one names a
time window and a scope, and starts with an aggregate. Replace the placeholders in angle brackets.
Check function and field names against the platform's current documentation before you rely on
them.

## Before any query

- **Window.** Start 15 to 30 minutes before the first symptom and end after recovery. Write both
  ends with a UTC offset.
- **Scope.** One service, resource or project. Never a whole subscription, account or
  organization.
- **Limits.** The runner sets a tool-side timeout and a row limit. Aggregates come first; raw
  rows only for a narrow window and with personal data left out.
- **Clock skew and zones.** Compare in UTC. Allow for skew between hosts (seconds) and for
  ingestion delay (minutes) before you read order into two close events.
- **Sampling and loss.** Application Insights, OpenTelemetry and Sentry can sample. A missing
  event is not proof that nothing happened. Say what the sampling rate was, or that it is
  unknown.
- **Retention.** Note what has already expired. It goes in the review's "Missing evidence".
- **Deployment markers.** Find the exact time each release, configuration change and feature
  flag change reached production, and the revision it deployed.

## Platforms

| Platform | What it gives | Correlate on |
| --- | --- | --- |
| Azure Monitor / Log Analytics (KQL) | Logs and metrics across Azure resources; activity log for changes | `_ResourceId`, `TimeGenerated`, operation ID |
| Application Insights | Requests, dependencies, exceptions, traces | `operation_Id`, `cloud_RoleName` |
| AWS CloudWatch | Metrics, Logs Insights queries, alarms | Log group, request ID, X-Ray trace ID |
| Google Cloud Logging and Monitoring | Logs Explorer queries, metrics, uptime checks | `resource.type`, `trace` |
| OpenTelemetry | Traces, metrics and logs from instrumented services, sent to a backend | `trace_id`, `span_id`, `service.name` |
| Sentry | Errors and performance events, grouped into issues, with release tags | Release, `trace` context |
| PostHog | Product events and session context | Event time, distinct ID (never in a web search) |

Product analytics (PostHog) shows what users did. It does not replace operational telemetry.

## Templates

### KQL (Log Analytics, Application Insights)

```kusto
// Window and scope: <2026-09-19T08:00Z> to <2026-09-19T09:00Z>, role <checkout-api>
requests
| where timestamp between (datetime(<2026-09-19T08:00Z>) .. datetime(<2026-09-19T09:00Z>))
| where cloud_RoleName == "<checkout-api>"
| summarize total = count(), failed = countif(success == false) by bin(timestamp, 1m), resultCode
| order by timestamp asc
| take 500
```

```kusto
// Exceptions by type and release, same window and role
exceptions
| where timestamp between (datetime(<start>) .. datetime(<end>))
| where cloud_RoleName == "<checkout-api>"
| summarize count() by type, application_Version, bin(timestamp, 5m)
| take 200
```

### CloudWatch Logs Insights

```text
# Log group <"/aws/lambda/checkout">, window <start> to <end>, set in the console or the API call
fields @timestamp, @message
| filter @message like /ERROR/
| stats count(*) as errors by bin(1m)
| sort @timestamp asc
| limit 500
```

### Google Cloud Logging

```text
resource.type="<k8s_container>"
resource.labels.namespace_name="<checkout>"
severity>=ERROR
timestamp>="<2026-09-19T08:00:00Z>" AND timestamp<="<2026-09-19T09:00:00Z>"
```

Read the count per minute in the histogram first; open single entries only after that.

### OpenTelemetry traces

Ask for the slowest and failed traces of one `service.name` in the window, grouped by span name
and status code, with a limit of 100 traces. Follow one failed trace end to end before you
generalize.

### Sentry

Filter by project, environment and release, and the window. Compare the issue's first-seen time
with the deployment marker. A new issue that starts before the release cannot be caused by it.

## Reading the result

- Write each finding with its query, window, scope and the row count it rests on.
- A query that was not run is labelled "not run", with the template given.
- A secret or customer identifier in the output is not repeated; describe it ("a bearer token
  appears in 3 log lines") and recommend rotation to the owner.

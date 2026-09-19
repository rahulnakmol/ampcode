# Use Archi, Darci, Revo, and Opsci

These four advisors return recommendations, not source changes. Use a dedicated mode for a conversation, or a consultation tool for a bounded question inside an implementation thread.

## Choose the advisor

| Mode / CLI key | Consultation tool | Best for | Main model |
| --- | --- | --- | --- |
| **Archi** / `archi` | `consult_archi` | SaaS architecture, .NET/Go/Rust/Python/TypeScript, iOS/Android/WinUI 3, distributed systems | Fable 5.1, high |
| **Darci** / `darci` | `consult_darci` | Data platforms, analytics, visualization, ML, RAG/graphs and evidence-grounded agents | Fable 5.1, high |
| **Revo** / `revo` | `consult_revo` | Evidence-backed review of supplied code changes | Astra, high |
| **Opsci** / `opsci` | `consult_opsci` | Incident investigation across telemetry and deployed source | Astra, high |

Oracle and other specialists retain Amp's automatic model routing. No Fast or Pro feature is requested by these definitions. Normal Amp model usage and orb costs still apply. Model choice is a starting configuration, not a performance guarantee.

## Install and verify

The GitHub repository is the source of truth. **Cloning or pushing it does not publish these modes to ampcode.com.**

For personal use across projects, publish the complete `plugins/advisory-team/` directory as `advisory-team/` at the root of your Amp Personal Plugins repository. Discover that destination with:

```sh
amp plugins repositories
```

Use the printed `amp clone` command and keep the clone under `~/.cache/amp/repositories/ampcode.com-user-plugins`. Preserve any existing local changes; do not reset a dirty publication checkout. Copy all six files, including the Markdown instructions. Review the diff, commit it, and push only after explicit approval. No separate Personal Skills publication is needed for this plugin.

After publication, new threads pick up the plugin. Ask Amp to reload plugins in an existing thread, or run `plugins: reload` from the command palette. Verify that all four modes appear in the full mode picker. Existing Swift, Weave and Prime modes are unaffected. If a mode is absent, check the publication destination, copied Markdown files, plugin load errors, and reload status.

For a project-only trial, copy the complete directory to that project's `.amp/plugins/advisory-team/` and reload plugins. Do not install both local and personal copies of the same plugin: duplicate mode keys can conflict. A local installation in an orb is not a substitute for persistent personal publication.

From this source repository, validate without launching paid agent runs:

```sh
make check
```

This loads plugins and runs wiring/allowlist tests. It does not establish reasoning quality, live connector access, or end-to-end inference availability.

## Start a conversation

On ampcode.com, open the intended project, select the named mode in the full mode picker, and send your request. This is the best route for multi-turn architecture interviews or an evolving incident.

With the plugin installed, the CLI equivalents are:

```sh
amp --mode archi
amp --mode darci
amp --mode revo
amp --mode opsci
```

From an implementation thread, be explicit:

> Use `consult_archi` to assess this design. Pass the requirements and relevant file paths. Return its recommendation before making changes.

The consultation runs on the caller's executor with the caller as its parent thread. It does not transfer files to a fresh orb. Each consultation is a new child conversation; it does not automatically resume the previous interview. Supply the latest brief and answers on follow-up calls, or use a dedicated advisor thread. The caller must relay any interview questions to you. A consultation timeout does not prove the child has stopped; inspect the child before retrying.

Calling an advisor does **not** restrict the parent implementation agent. Say “advice only; do not implement” when that is what you want. Advisors have no tools to recursively call this team's consultation tools.

## Work with Archi

Start with the problem, not a required technology list:

> We are building a multi-tenant field-service SaaS product. Our team knows C# and TypeScript. Customers use iOS, Android, and Windows. Offline work matters. Interview me in small rounds before recommending an architecture. Record confirmed constraints separately from assumptions.

Expect two to four questions per round, short explanations of the choices, and a living design brief. Archi should read supplied material before asking questions already answered there. It can discuss .NET without assuming Azure, and a .NET backend without assuming .NET clients.

To evolve a design:

> Our last brief assumed always-connected clients. Technicians now need eight hours offline. Revise the affected decisions, explain what stays valid, and propose test-first acceptance criteria and a migration plan.

To skip the interview:

> Work autonomously from this brief. State assumptions and recommend one option. Identify decisions that need my confirmation before implementation.

Expected output: recommendation, constraints, alternatives and tradeoffs, boundaries/diagrams, risks, phased implementation, validation and rollback. Guidance is ASD-STE100-inspired, not certified compliance.

## Work with Darci

> We have SQL Server operational data and inconsistent reporting. Help us start lean and grow toward an enterprise data platform. Interview me about business decisions, freshness, analysis and dashboard speed, governance, and cost. Compare Fabric, Databricks and simpler options only where relevant.

For agentic data systems:

> Design an evidence-grounded assistant over our policies and transactional data. Determine whether SQL retrieval, hybrid RAG or a knowledge graph is justified. Cover permissions, provenance, contradictory evidence, abstention, evaluation and latency. Do not assume a vector database is necessary.

Provide sanitized schemas, metric definitions, query plans and architecture proposals. Never paste credentials or connection strings. Darci separates time to first insight, query latency, dashboard responsiveness, freshness and retrieval quality. It should propose measurable scaling triggers instead of imposing a user-count threshold.

Expected output: business-to-metric mapping, data/evidence flows, model and semantic contracts, platform decisions, governance, evaluation and an incremental delivery plan.

## Work with Revo

Revo has no shell or direct Git/GitHub connector. Supply a diff artifact, its exact base/head revision identities, intended behavior, changed-file inventory, and the matching checkout or relevant source files. A PR URL alone may not provide enough evidence. Have the host prepare the diff with external diff drivers and text conversion disabled; do not execute PR code or hooks. Review exports for secrets before sharing.

> Use `consult_revo` to review the attached base-to-head diff and matching source. The intended behavior is tenant-scoped invoice access. Find introduced, reachable defects. Attempt to disprove each finding. Report reviewed, skipped and blocked paths. Do not edit files or post comments.

Expected output: severity-ranked findings with concrete triggers, impact, source evidence, verified locations and regression-test suggestions. Pre-existing issues and design preferences must be separate. “No substantiated findings” is scoped to inspected evidence, not a safety guarantee. Tests are not executed by Revo.

The review method is inspired by [Alibaba Open Code Review](https://github.com/alibaba/open-code-review), particularly change inventory, relevant rules, cross-file review and coverage. No OCR code, bundled skills or runtime is installed. The independent instructions reject auto-fix behavior and require affirmative evidence instead of retaining every unrefuted suspicion. No OCR benchmark claim transfers to this agent.

## Work with Opsci

> Investigate increased checkout failures between 14:00 and 14:20 Asia/Kolkata on 19 September 2026. These sanitized logs and traces are from production release X. The matching source is available at these paths. Establish competing explanations and the next discriminating evidence. Recommend mitigation separately from the durable fix. Do not change production.

Supply the symptom, impact, time window/time zone, deployment identity, sanitized telemetry, recent changes and expected behavior. Opsci should ask only for missing details that block progress. It must not blame current source when the deployed revision differs.

Expected output: impact/timeline, confirmed facts, hypotheses and counter-evidence, implicated code where supported, missing evidence, bounded follow-up queries, mitigation and repair guidance. It does not restart services, deploy, tune alerts or execute remediation.

## Connect live data and telemetry deliberately

**No live connectors ship with this version.** Darci and Opsci can analyze exports and recommend SQL/KQL or other queries, but cannot execute them against your services yet.

To add an integration:

1. Select the actual service and approved resources: for example, a Log Analytics workspace, Application Insights resource, Sentry project, or a database's metadata views.
2. Configure credentials directly in the provider/MCP setup or secret manager. Never put them in prompts, tracked files, or CLI arguments.
3. Audit the connector's tools and authentication. Require provider-side read-only access, tenant/resource restrictions, bounded result sizes, query timeouts and appropriate retention. Read-only SQL can still be expensive or disclose data.
4. Add only the exact approved tool names to the relevant agent's allowlist. Do not add `mcp__*`, `plugin__*`, a general shell, or write-capable tools. If bundling an MCP skill, use `includeTools`; loading that skill alone does not expand the agent allowlist.
5. Test a metadata-only query and a forbidden-operation rejection in a non-production environment. Inspect redaction and audit logs before allowing sensitive workloads.

A connected service available to normal Amp is not automatically available to these advisors. Keep Archi/Revo access unchanged when adding a Darci/Opsci connector.

## Understand the read-only boundary

Direct tools are explicitly limited to file reading, discovery, research, media inspection, skills and specialist consultation. There are no direct source-edit, shell, generic Task, publishing or infrastructure-mutation tools. Skills cannot add omitted tools.

This is **not a complete security sandbox**. Amp-managed Finder/Librarian/Oracle specialists have their own toolsets; their read-only research scope is also governed by instructions. Files accessible to the executor may contain sensitive information. Use isolated environments, least-privilege connectors, no production credentials in the filesystem, and a read-only source mount where a hard boundary is required. Do not run a secret-bearing review environment against an untrusted PR checkout.

Reports are returned in chat. A host may save requested Markdown/HTML to an approved report location; the advisors themselves do not create files. Generated HTML is not an implemented or visually verified UI.

## GitHub automation is a separate integration

No workflow or comment publisher ships here. Start with manual Revo consultations. A future pipeline should run a pinned trusted reviewer against immutable PR data, without executing PR-controlled code or loading PR-controlled plugins, skills or hooks.

Keep evaluation separate from posting. Use a narrowly authorized publisher to validate output, verify the head SHA is still current, check inline anchors, deduplicate comments, and post only after the chosen authorization trigger. Treat partial coverage, malformed output, timeouts and missing merge bases as incomplete reviews—not success. Store credentials in GitHub secrets or an approved identity mechanism. Do not use a privileged `pull_request_target` workflow to execute the PR checkout.

## Change models and evaluate updates

Model pins live in `plugins/advisory-team/index.ts`; behavior lives in the neighboring Markdown files. Discover current supported IDs and efforts before changing a pin:

```sh
amp plugins show-agent-options --json
```

Update the routing tables here and in the root README. Run `make check`, then try representative problems before publishing. Compare decision quality, unsupported claims, question usefulness, coverage, latency and usage cost—not confidence of tone.

Useful acceptance exercises:

- Archi: introduce offline mobile support after an initial design. It should revise affected decisions without inventing constraints.
- Darci: ask for GraphRAG on a simple structured reporting task. It should assess simpler options and define an evidence evaluation plan.
- Revo: supply one real tenant-isolation regression and one similar-looking guarded path. It should distinguish them and track both in coverage.
- Opsci: supply a deployment correlation with a conflicting dependency-error timeline. It should investigate alternatives rather than assert causality.
- All: ask them to edit a file or execute a production fix. They should return advice, not mutate state. Also test this through a consultation; verify the parent has not implemented the advice without authorization.

These are behavioral acceptance exercises for an operator, not claims that automated model evaluations have already passed.

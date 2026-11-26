# Data and AI architecture

This is the data and AI method of `architecting` (it was the Darci advisory mode's remit). Use
it when the design includes analytics, reporting, data platforms, machine learning, retrieval or
evidence-grounded agents. Guide the user from nimble data systems to large enterprise platforms
built for fast, trustworthy analysis, visualization and recall. Be inventive but evidence-led.
Do not infer platform size from a fixed user threshold.

## Interview and evolve

Read supplied evidence first. Interview in rounds of two to four useful questions. Establish, as
relevant: the business decisions, consumers, source systems, data ownership, metric definitions,
volume and growth, concurrency, freshness, query and dashboard latency, retrieval quality,
privacy, team skills and cost. Say why each question matters, and offer options when an answer
is uncertain.

Keep the shared design brief from SKILL.md section 1: confirmed constraints, preferences,
assumptions and open questions. Present provisional designs, teach their trade-offs, and revise
decisions as the user supplies evidence. Say what changed and why. Stop asking when enough is
known. For an autonomous request, state the assumptions. In a one-shot consultation, return the
necessary questions to the caller instead of inventing answers.

## Data-to-insight architecture

- Compare SQL Server/PostgreSQL reporting, warehouses, lakehouses, streaming and serving layers against actual workloads.
  Distinguish transactional systems of record from analytical products.
- Know Microsoft Fabric, Azure Databricks, Databricks on AWS and GCP, BigQuery and the services
  around them. BigQuery is not a drop-in Databricks equivalent. Consult current documentation
  and relevant skills instead of assuming feature parity.
- Design dimensional and other suitable models, grain, semantic metrics, CDC, batch and stream
  pipelines, contracts, lineage, quality, access, retention and deletion propagation.
- Balance time to first insight, query latency, dashboard responsiveness, freshness, retrieval
  quality, reliability and cost. Use partitioning, precomputation, caching and workload
  isolation only where justified.
- Connect business questions to analysis, trends and anomalies. Distinguish correlation from
  causation; consider selection effects, uncertainty and misleading comparisons. Recommend
  accessible visualizations, drill-downs and consistent metrics.
- Traditional machine learning: establish simple baselines first; prevent leakage; design
  suitable splits, evaluation, deployment, monitoring and retraining. Explain when machine
  learning is not needed.

## Evidence-grounded agentic systems

Design conventional RAG, hybrid retrieval, structured SQL retrieval, filtering, reranking, query
decomposition, knowledge graphs, entity resolution, ontologies and GraphRAG as appropriate.
Require a concrete relationship or multi-hop benefit before you introduce a graph. Require a
retrieval need before you introduce vector storage.

Connect claims to source passages, record identities, query results and transformations, with
versions, timestamps, provenance and permissions. A citation is not proof: assess whether the
evidence supports the claim, expose contradictions, separate inference from fact, and abstain
when support is not enough. Prefer traceable computations for numerical answers.

Design agent state, tool contracts, bounded execution, human approvals, recovery, and
authorization outside the model. Permission-aware retrieval must never expand a user's access.
Address prompt injection, poisoned sources, cross-tenant leakage, source freshness, and deletion
across indexes and caches. Evaluate retrieval relevance, evidence support, citation accuracy,
task success, latency and cost on representative and adversarial examples. A change to an agent's
tools, data access or tenants changes trust boundaries: link a threat model (SKILL.md section 4).

## Inspection

Review proposals, sanitized schemas, SQL, query plans and approved metadata. Never ask for
connection strings in chat. Assume no live data connector is installed; ask for safe exports or
an approved, bounded tool. Do not run migrations or expensive exploratory queries, and do not
extract customer records. Prefer metadata to records.

## What to put in the design

Recommend the smallest sufficient initial architecture and the measurable triggers for its next
stage. In the design file (format in [design-template.md](design-template.md)):

| Design section | Data and AI content |
| --- | --- |
| Context | Business decisions and their consumers; source systems and owners |
| Containers | Data and evidence flows: sources, pipelines, stores, semantic layer, indexes, agents |
| Contracts | Data contracts, semantic metric definitions, event and CDC schemas, tool contracts for agents |
| Decisions | Platform alternatives as ADRs, with the workload evidence for each |
| Non-functional requirements | Freshness, query and dashboard latency, retrieval relevance, citation accuracy, cost; see [nfr-catalogue.md](nfr-catalogue.md) |
| Trust boundaries | Access, tenancy, retention, deletion propagation, and agent execution boundaries |

Add the business-to-metric mapping, governance, the evaluation plan, phased migration and
rollback, and the implementation handoff. Coordinate operational contracts and agent execution
with the rest of the design; do not start implementation work.

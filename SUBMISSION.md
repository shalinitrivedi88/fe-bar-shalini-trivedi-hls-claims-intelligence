# FE BAR Submission narrative (paste into the form fields)

> Answers for the FE BAR submission form. Anchored to real, executed output in
> [`evidence/`](evidence/). The FE BAR de-identifies submissions and bars
> customer-identifying content, so this uses a fictional payer and synthetic data throughout.
> Field bodies are plain text so they paste cleanly into the form.

---

## Customer name

Cascade Benefit Systems (fictional health-plan claims processor; 100% synthetic data throughout)

## Industry / vertical

Healthcare payer: claims processing and benefits administration for regional health plans (commercial, ASO / self-funded, Medicare Advantage, Medicaid)

## What is the business challenge you are solving?

Cascade's member application and its analysts run on yesterday's data. Claims are adjudicated on a DB2 and CICS mainframe, and every downstream consumer reads a nightly batch extract, so a member always sees a claim state that is a day or more behind reality. On the synthetic book that is about 82.2M dollars billed across 50,000 claims, with 23.9M dollars trapped in a denied and pending rework pool and roughly 40 percent of dispositions that never trigger the next action. That gap is money and member experience leaking every night.

This is the VP of Claims Products' problem to own: their scorecard is claim-to-availability latency, disposition-to-action time, and the share of analyst questions answered without a SQL ticket. The denied and pending exposure rolls up to the CFO, and PHI governance across the operational store and the data lake sits on the CISO's HIPAA and HITRUST scorecard.

Three things are broken. The claim in the app is stale because it is a copy of a nightly extract, not the live claim. Nothing fires when a claim is disposed, so avoidable rework compounds. And cross-claim questions are multi-week SQL tickets, because a claim's thousands of data elements sit in fragile pipelines off the mainframe. The team needs current claim state in the application, a governed action the moment a claim is disposed, and self-serve analytics, moving the exact metrics the VP, CFO, and CISO are measured on.

## How does your Databricks solution address this challenge?

One governed platform, one governed schema, six connected layers, not six demos stitched together. The claim is ingested once, governed once, and every layer (the app, Genie, the agent, the model) reads that same certified schema, so there is no drift. This turns nightly-batch staleness into current claim state in the application, a governed action the moment a claim is disposed, and self-serve analytics.

The data journey, in flow order:

1) Lakeflow ingests the synthetic claims book (837 and 835 shapes) and streams disposition events into bronze and silver tables. A new feed is a declarative config change, not a fragile pipeline.

2) Unity Catalog governs it: a declared 5 primary-key plus 5 foreign-key graph (RELY) so Genie and the optimizer trust joins; certified Metric Views (claims_metrics, disposition_metrics) so every metric resolves to MEASURE() rather than an ad-hoc aggregate; and PHI column masks applied at the governance layer, so member name, SSN, and DOB stay masked across notebooks, Genie, and model serving with no bypass. Everything lives in one schema, serverless_stable_kysnws_catalog.claims_intelligence.

3) Lakebase (managed Postgres) is the claims ODS behind the member application: a hybrid model with relational columns plus a JSONB long tail for the thousands of variable claim elements, queried together, so the app reads the live claim, not a nightly extract. It also holds a pgvector plus BM25 hybrid search over case narratives, fused with reciprocal-rank fusion, so a rep finds similar prior cases instantly.

4) Gen AI: a code-based MLflow ResponsesAgent triages a claim on disposition and proposes the next action, with tool-calling over Genie, a per-claim brief, and a triage tool, and it degrades gracefully if a tool fails. Model traffic is routed and governed through Unity Gateway.

5) Genie lets an analyst ask in plain English and get governed SQL over the certified Metric Views (MEASURE), no SQL ticket.

6) A Databricks App (React plus FastAPI), the Claims Operations Console, surfaces it all: a live triage queue, the disposition-action gap, hybrid case search, and a chat panel, over the same governed schema.

7) An MLflow model scores manual-review likelihood across all 50,000 claims into a prioritization table, so reviewers start with the highest-impact work.

This ran live on a serverless workspace, and the evidence is committed as text (row counts, the RELY constraint listing, a masked-versus-cleartext read, a live Genie NL-to-MEASURE-to-answer trace, the Lakebase hybrid query, the agent dossier, and the model metrics). Right engine per job: analytics on the lakehouse, OLTP plus JSON on Lakebase, retrieval on pgvector, governed AI through Unity Gateway.

## What AI tools did you use, and what was your workflow? What decisions and trade-offs did you make?

Tools and workflow. I built this with Claude Code (Isaac) as a teammate, driving the Databricks CLI and MCP end to end. The workflow was prompt-driven and layer-by-layer: one focused prompt per component (synthetic data generation, Unity Catalog governance, the Lakebase ODS, the Gen AI agent, the app, the ML model), each captured in the repo's folder READMEs so the build is reproducible. On-platform AI did the work inside the build: Databricks Foundation Models (Claude, GPT, and bge embeddings) routed through Unity Gateway, Genie for natural-language SQL, MLflow for training and tracking, and Model Serving. The loop was consistent: prompt, run on serverless, capture evidence as text, and lock it in with a 35-check functional test suite that runs against the live workspace.

Key decisions and trade-offs:

1) Certified Metric Views over prompting the agent on raw tables. An agent that computes KPIs ad hoc drifts; certified Metric Views give Genie and the dashboard one governed definition via MEASURE(). Trade-off: more up-front modeling.

2) Declared PK/FK as RELY over leaving joins to the model. Genie and the optimizer infer joins from real relationships instead of guessing. Trade-off: the data must stay clean enough to declare RELY honestly.

3) PHI masked at the governance layer, not at query time. The mask becomes a property of the column, so it holds across notebook, Genie, and model serving with no bypass, which is what survives an audit. Trade-off: masks authored and tested per column.

4) Lakebase for operational serving, not serving from the lakehouse. The app needs OLTP-latency reads and a variable JSON long tail, a Postgres plus JSONB job; analytics stays on the lakehouse. Trade-off: a second engine to operate, justified by latency and the hybrid requirement.

5) A code-based MLflow ResponsesAgent over a fully managed supervisor. It wraps each tool so one flaky tool degrades gracefully instead of failing the whole request. Trade-off: managed simplicity for resilience and control.

Honest constraints. Serving the agent and the ML model both require registering a model in Unity Catalog, and the shared metastore is at its 5,000-model quota, so I logged and validated both and left serving one command away rather than deleting other engineers' models. And the model's AUC is 0.9241 but I report it as optimistic by construction: the synthetic label is partly derived from features the model also sees, so on real data it would be lower and would need independent validation.

## What are the business outcomes and impact?

Estimated value first. On the synthetic book, 23.9M dollars sits in the denied and pending rework pool. Recovering even 10 percent through avoidable-denial prevention and faster appeal turnaround is roughly 2.4M dollars a year, and closing the ~40 percent disposition-action gap removes the manual chase on about 17,000 events. These are estimates on synthetic data, to be validated in the POC; the absolute number scales with a real processor's claim volume.

Each outcome maps to the metric a named owner is measured on:

- VP of Claims Products: claim-to-availability latency moves from a nightly batch to near-real-time, so the member application shows the live claim, not yesterday's copy. Disposition-to-action time drops as the ~40 percent event-blindness gap closes with governed, event-driven triggers.

- CFO: exposure in the 23.9M dollar denied and pending rework pool is cut by preventing avoidable denials and speeding appeals, the roughly 2.4M dollars a year above.

- CISO: one PHI masking story that holds across notebook, Genie, and Model Serving, with a traceable lineage trail from ingest to output, which is what survives a HIPAA or HITRUST audit.

- The whole team scales without headcount: analysts self-serve governed answers through Genie instead of filing multi-week SQL tickets, and reviewers start with the highest-impact claims because the ML model ranks the queue.

The through-line: the same governed schema powers the app, Genie, the agent, and the model, so every one of these outcomes is measured against one certified set of definitions, not five dashboards that disagree.

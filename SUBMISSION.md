# FE BAR — Submission narrative (paste into the form fields)

> Drafted answers for the six narrative fields on the FE BAR submission form.
> Everything is anchored to real, executed output in [`evidence/RUN_EVIDENCE.md`](evidence/RUN_EVIDENCE.md).
>
> **Note on the "Customer name" field:** the FE BAR de-identifies submissions and bars
> customer-identifying content, so this is written for a **fictional** payer and uses
> synthetic data throughout.

---

## Customer name
A regional health-plan claims processor and benefits administrator (fictional: "Cascade Benefit Systems"; synthetic data used throughout).

## Industry / vertical
Healthcare payer — claims processing and benefits administration for regional health plans (commercial, ASO/self-funded, Medicare Advantage, Medicaid).

## What is the business challenge you are solving? *
**Whose problem this is.** The accountable owner is the **VP of Claims Products**, whose scorecard is claim-to-availability latency (how fast a processed claim reaches the Harbor member application), disposition-to-action time, and the share of analyst questions answered without a SQL ticket. The **denied and pended dollar exposure rolls up to the CFO**, and **PHI governance across the operational store and the data lake sits on the CISO's** HIPAA and HITRUST scorecard. The VP of Claims Products is the funding buyer; the CFO is the economic sponsor; the CISO is the compliance stakeholder.

**The problem.** Cascade adjudicates claims on a DB2 and CICS mainframe, but every downstream consumer reads a nightly batch extract that is already stale. The Harbor application shows members a claim state a day or more behind reality. A single claim carries thousands of data elements, a mix of structured relational fields and nested content, and the batch loop breaks whenever the mainframe schema changes, so each new feed or report is another fragile pipeline. When a claim reaches a disposition there is no governed way to fire the downstream action that should follow (a member notice, an appeal route, a payment-integrity check). And analysts wait on multi-week SQL tickets for cross-claim questions. The team needs (1) current claim state in the application, (2) a governed action on a disposition the moment it happens, and (3) self-serve governed analytics, moving the specific metrics the VP, CFO, and CISO are measured on.

## How does your Databricks solution address this challenge? *
An **end-to-end data journey on Databricks**, integrated across six layers over one governed schema (`serverless_stable_kysnws_catalog.claims_intelligence`):

1. **Lakeflow** ingests synthetic payer claims — members, providers, claims (837/835 shapes with a JSON detail column for the long tail), prior authorizations, eligibility, and disposition events — into bronze and silver, and streams disposition events (see evidence §1).
2. **Unity Catalog** governs it: a declared **primary-key and foreign-key (RELY)** graph, **certified metric views** (disposition rate, downstream-action-fired rate, denied/pended dollar exposure, provider risk), **PHI column masks** applied at the governance layer, and enriched comments and synonyms. This semantic layer is what makes natural-language answers trustworthy and holds the mask across notebook, Genie, and model serving (evidence §2 to §4).
3. **Lakebase** (managed Postgres) serves the **claims ODS** with a **hybrid relational + JSONB** model, so the Harbor application queries current claim state directly instead of a nightly extract. Deployed live on the serverless FEVM workspace (evidence: `LAKEBASE_DEPLOYMENT.md`).
4. **Gen AI — a smart-triage agent** classifies each claim on disposition (complexity, risk, likely manual-review need) and proposes the next action, routed and governed through **Unity Gateway** with usage and cost visibility.
5. **A Genie agent** lets a claims analyst ask in plain English; it grounds on the certified metrics and declared relationships and returns governed SQL plus a summary (evidence §6 shows the live NL→SQL→answer trace using `MEASURE()` over the metric view).
6. **A Databricks App** (React + FastAPI) surfaces it: a Claims Operations Console driven by the same governed SQL (current claim state, disposition queue, triggered actions), plus a chat panel that proxies to the agent.
7. **A trained + served ML model** pairs the agent with a risk score: a manual-review-likelihood classifier trained with **MLflow**, registered in **Unity Catalog**, scored across claims into a reviewer-prioritization table, and **served** on Model Serving. Metrics are reported honestly on synthetic data; the value is the end-to-end MLOps pattern and the prioritization (evidence: `ML_MODEL.md`).

The layers are connected, not siloed: every layer reads or writes the **same governed schema**, so the app, the Genie agent, the triage agent, and the model all speak the same certified definitions.

## What AI tools did you use, and what was your workflow? What decisions and trade-offs did you have to make?
**Tools.** I built with **Claude Code** (Isaac) driving the Databricks CLI and MCP: scaffolding the repo and app, generating synthetic claims data, authoring the Unity Catalog constraints, metric views, and PHI masks, configuring the Genie space, provisioning and seeding Lakebase, building the triage agent, and training the manual-review-likelihood model (MLflow → Unity Catalog registration → Model Serving) via serverless jobs, then capturing execution evidence by running SQL, the Genie Conversation API, and the app's endpoints live. On-platform AI: Databricks Foundation Model serving (LLM and embeddings) routed through Unity Gateway, Genie, MLflow, and Model Serving.

**Key decisions & trade-offs (full detail in [`docs/DECISIONS_AND_TRADEOFFS.md`](docs/DECISIONS_AND_TRADEOFFS.md)):**
- **Lakebase first, then Lakehouse and Lakeflow.** Matches the customer's own phasing. The operational store behind Harbor is what the business feels first; proving it funds the analytics and AI phases. Trade-off: a second engine to operate, justified by OLTP latency and the hybrid model.
- **Hybrid relational + JSON in one store.** Relational columns for the structured claim fields, a JSON column for the thousands of variable elements, queried together. Trade-off: more schema design up front, but the claim's long tail survives without a second system.
- **Certified metric views over raw-table prompting.** Genie picks `MEASURE(Disposition Rate)`, not an ad-hoc `AVG`. Trade-off: more modeling work, worth it for governed, reproducible answers.
- **PHI masked at the governance layer, not at query time.** One masking definition holds across notebook, Genie, and model serving with no bypass. Trade-off: masks must be authored and tested per column; this is what survives an audit.
- **Event-driven disposition vs. batch.** A disposition fires a governed downstream action through orchestration rather than a nightly job scraping a table.

## What are the business outcomes and impact?
Each outcome is tied to the metric a named owner is measured on:
- **Lower claim-to-availability latency (VP of Claims Products).** The Harbor application reads current claim state from the Lakebase ODS instead of a nightly extract, so the member experience stops lagging the batch.
- **Faster, prioritized disposition handling (VP of Claims Products).** The triage agent scores each claim on disposition and routes the highest-risk work first, and every disposition can fire a governed downstream action instead of waiting for a batch.
- **Protected exposure in the denied and pended pool (CFO).** The analytics layer surfaces where denied and pended dollars concentrate by disposition reason and provider, so avoidable rework and leakage can be cut (figures in evidence §4 to §5).
- **Defensible PHI governance (CISO).** PHI is masked at the governance layer and the mask holds across notebook, Genie, and model serving, with lineage from ingest to output an auditor can trace.
- **Scales the team, not the headcount.** Analysts self-serve governed answers in natural language instead of filing multi-week SQL tickets.

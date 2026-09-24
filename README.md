# Real-Time Claims Intelligence — an end-to-end payer claims build

**Industry:** Healthcare payer, claims processing and benefits administration for regional health plans
**Metric owner (the buyer):** the **VP of Claims Products**, whose scorecard is claim-to-availability latency (how fast a processed claim reaches the member application), disposition-to-action time, and the share of analyst questions answered without a SQL ticket. Denied and pended dollar exposure rolls up to the **CFO**, and PHI governance across the operational store and the lake sits on the **CISO's** HIPAA and HITRUST scorecard.

**Customer problem.** Cascade Benefit Systems runs claims for regional health plans on a DB2 and CICS mainframe. The mainframe adjudicates well, but every downstream consumer, the Harbor member application, the analysts, and any AI, reads a nightly batch extract that is already stale. A single claim carries thousands of data elements, a mix of structured fields and nested content, and the batch loop breaks whenever the source schema changes. When a claim reaches a disposition, nothing fires the action that should follow. The team needs current claim state in the application, a governed way to act on a disposition the moment it happens, and self-serve analytics that do not require a SQL ticket.

> **Cascade Benefit Systems is a fictional company created for this capstone. Every figure, name, and dataset here is fabricated. No real customer or PHI is referenced.**

## The business outcome (read this first)

This build gives Cascade one governed platform where the operational store, the analytics, and the AI all read the same claim, current, instead of three copies of yesterday's extract. On the synthetic book of business this repo generates (executed live, see [`evidence/RUN_EVIDENCE.md`](evidence/RUN_EVIDENCE.md)):

- A claims ODS on Lakebase serves current claim state to the Harbor application directly, so the member experience stops lagging the nightly batch.
- A smart-triage agent scores each claim on disposition and routes the highest-risk work first, and every disposition can fire a governed downstream action instead of waiting for a batch.
- **$23.9M sits in the denied and pending rework pool** ($82.2M billed across the 50,000-claim synthetic book); the analytics layer surfaces where it concentrates by disposition reason and provider (see [`evidence/RUN_EVIDENCE.md`](evidence/RUN_EVIDENCE.md)).

**Estimated value.** Recovering even 10% of the $23.9M denied and pending pool through avoidable-denial prevention and faster appeal turnaround is roughly **$2.4M a year on this synthetic book**, and closing the ~40% disposition-action gap removes the manual chase on about 17,000 events. These are estimates on synthetic data, stated to be validated in the POC; the absolute number scales with a real processor's claim volume.

**Value framing.** For a processor handling hundreds of millions of claims a year, moving claim availability from nightly batch to near-real-time, steering reviewers to the highest-risk claims, and letting analysts self-serve governed answers moves the exact metrics these owners are measured on: the VP of Claims Products' claim-to-availability latency and analyst self-serve rate, the CFO's exposure in the denied and pended pool, and the CISO's PHI governance posture across both planes.

## The data journey — one connected pipeline, six Databricks layers

```
 raw synthetic payer claims (837/835 shapes, hybrid relational + JSON)
        │  (Faker/PySpark generation)
        ▼
┌──────────────────────┐   01_lakeflow_ingest/
│ 1. LAKEFLOW           │   ingest members, providers, claims, prior_auths,
│    ingest + stream    │   eligibility, disposition_events into bronze/silver
└─────────┬────────────┘
          ▼
┌──────────────────────┐   02_unity_catalog_governance/
│ 2. UNITY CATALOG      │   PK/FK (RELY) graph, certified metric views,
│    govern             │   PHI column masks, comments + synonyms, domain tags
└─────────┬────────────┘
          ├───────────────────────────────┐
          ▼                                ▼
┌──────────────────────┐        ┌──────────────────────┐
│ 3. LAKEBASE           │        │ 4. GEN AI AGENT       │  04_genai_agent/
│    claims ODS         │        │    smart triage       │  classify each claim on
│  03_lakebase_serving/ │        │  classify + next      │  disposition, propose the
│  managed Postgres,    │        │  action, via Unity    │  next action, governed
│  relational + JSONB,  │        │  Gateway              │  through Unity Gateway
│  powers Harbor        │        └──────────┬───────────┘
└─────────┬────────────┘                   ▼
          │                     ┌──────────────────────┐  05_genie_agent/
          │                     │ 5. GENIE AGENT        │  NL → certified-metric SQL
          │                     │    claims analytics   │  over the SAME governed schema
          │                     └──────────┬───────────┘
          └───────────────┬─────────────────┘
                          ▼
                ┌──────────────────────┐   06_databricks_app/
                │ 6. DATABRICKS APP     │   React + FastAPI: Claims Operations
                │  Claims Ops Console   │   Console (SQL) + chat panel (agent)
                └──────────────────────┘
```

**Why this is one journey and not six demos:** every layer reads or writes the **one governed schema** `serverless_stable_kysnws_catalog.claims_intelligence`. Lakeflow lands the tables; Unity Catalog governs them with the PK/FK graph, certified metric views, and PHI masks; Lakebase serves current claim state operationally to Harbor; the triage agent and the Genie agent both act over the *same* certified metrics; the app calls the same SQL and proxies chat to the agent. That shared, governed schema is the join between the layers.

## Repository map

| Path | Layer | What's here |
|---|---|---|
| [`01_lakeflow_ingest/`](01_lakeflow_ingest/) | Lakeflow | Synthetic claims generator (hybrid relational + JSON) + table-creation + declarative pipeline |
| [`02_unity_catalog_governance/`](02_unity_catalog_governance/) | Unity Catalog | PK/FK RELY constraints, certified metric views, PHI column masks, comments/synonyms, tags |
| [`03_lakebase_serving/`](03_lakebase_serving/) | Lakebase | Managed Postgres claims ODS, relational + JSONB, seed + validate, deploy notes |
| [`04_genai_agent/`](04_genai_agent/) | Gen AI | Smart-triage agent: classify claim on disposition, propose next action, via Unity Gateway |
| [`05_genie_agent/`](05_genie_agent/) | Genie | Genie space config: general instructions, synonyms, trusted SQL |
| [`06_databricks_app/`](06_databricks_app/) | App | React + FastAPI Databricks App (Claims Operations Console + chat) |
| [`07_ml_model/`](07_ml_model/) | ML | Trained + served manual-review-likelihood model (MLflow → Unity Catalog → Model Serving) |
| [`evidence/`](evidence/) | - | **Real run output committed as text** (row counts, constraints, certified-metric results, Genie trace, Lakebase search, ML metrics) |
| [`deck/`](deck/) | - | Business presentation (outcome-led) |
| [`docs/`](docs/) | - | App overview, decisions & trade-offs, follow-ups |

## Proof it runs

Evidence is committed as **text**, not screenshots, per the FE BAR Build domain. See [`evidence/`](evidence/):
- [`evidence/RUN_EVIDENCE.md`](evidence/RUN_EVIDENCE.md) — table row counts, the PK/FK constraint listing, certified-metric results (disposition rate, downstream-action-fired rate, dollar exposure), and a live Genie natural-language to SQL to answer trace.
- [`evidence/LAKEBASE_DEPLOYMENT.md`](evidence/LAKEBASE_DEPLOYMENT.md) — the Lakebase claims ODS provisioned and seeded, with the hybrid relational + JSON query returning current claim state validated OK.
- [`evidence/ML_MODEL.md`](evidence/ML_MODEL.md) — the manual-review-likelihood model trained with MLflow, registered in Unity Catalog, scored across claims, and served on Model Serving (metrics reported honestly; the value is the end-to-end MLOps pattern and the prioritization).

## Where it runs

Serverless FEVM workspace `fevm-serverless-stable-kysnws` (AWS), catalog `serverless_stable_kysnws_catalog`, schema `claims_intelligence`. All six layers run serverless: Lakeflow declarative pipelines, serverless SQL, Lakebase, Model Serving, and Databricks Apps. Shared settings are in [`config.sh`](config.sh).

## Data & compliance

100% synthetic data. The code systems referenced (CARC denial codes, CPT/HCPCS, ICD-10, X12 837/835 structure, place-of-service codes) are real public taxonomies. Cascade Benefit Systems is fictional. No real customer data or PHI is included.

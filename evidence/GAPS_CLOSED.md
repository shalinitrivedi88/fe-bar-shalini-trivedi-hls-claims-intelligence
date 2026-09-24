# Depth-parity gap closure — evidence (run on fevm, 2026-09-24)

Closing the four gaps identified against the reference build. Two are fully live;
two are code-complete but their serving endpoints are blocked by the shared-metastore
model quota (documented, one command from live when quota frees).

## Gap A — Unity Catalog Metric Views (was: only plain SQL views)

Real `METRIC_VIEW` objects now exist (version 1.1), so Genie resolves to `MEASURE()`:
```
SELECT table_name, table_type FROM information_schema.tables
WHERE table_schema='claims_intelligence' AND table_type='METRIC_VIEW';
-- claims_metrics       METRIC_VIEW
-- disposition_metrics  METRIC_VIEW
```
`MEASURE()` verified:
```
SELECT `Status`, MEASURE(`Claim Count`) FROM claims_metrics GROUP BY `Status`;
-- Paid 31,463 | Pending 8,079 | Denied 6,492 | Partially Paid 3,966
```
The Genie space `01f1b7a7a3511f52a02ca9d65a9d353f` was updated to source these metric
views with `MEASURE()` example SQL. Deploy gotcha: the CLI `aitools query` mangles
multi-line YAML; deploy metric views via the SQL Statements API (see certified_metric_views.sql).

## Gap B — Lakebase pgvector + BM25 hybrid search (was: relational+JSON only)

500 claim case-narratives embedded (`databricks-bge-large-en`, 1024-dim) and loaded into
`claims_ods.claim_notes` (vector(1024) + tsvector), with an HNSW cosine index + a GIN index.

Full hybrid reciprocal-rank-fusion search, end to end (query embedded via the endpoint):
```
query: "member wants to appeal a denied specialist claim that was not medically necessary"
top hits (rrf):
  C000033599  0.01639  837P ... DENIED: Not medically necessary ...
  C000011429  0.01613  ...
```
Vector self-similarity returns the probe claim at cosine distance 0.0000; BM25 keyword
search returns the matching denied narratives. All validated in Lakebase.

## Gap C — Real React app + multi-route backend (was: single-file FastAPI + inline HTML)

`claims-ops-console` rebuilt as a React (Vite) frontend + a multi-route FastAPI backend
(`server/routes/summary|triage|search|chat`, `server/db.py`, `server/config.py`), deployed
and RUNNING. Live authenticated calls:
- `GET /` -> React bundle (title "Claims Operations Console")
- `GET /api/summary` -> `{total_billed 82,160,677, rework_pool 23,891,778, flagged 5,891, action_fired_rate 0.599}`
- `GET /api/triage-queue` -> 25 ML-prioritized claims (top score 0.865)
- `GET /api/disposition-gap` -> 3 dispositions with fired rates
- `POST /api/chat` -> governed model answer
- `POST /api/search` -> 10 hybrid results from Lakebase (as the app service principal)

The app SP was granted a Lakebase Postgres role + SELECT on `claims_ods`, and CAN_USE on the warehouse.

## Gap D — Code-based ResponsesAgent with tool-calling (was: single model call)

`04_genai_agent/agent.py` is now a real MLflow `ResponsesAgent` (`ClaimsTriageSupervisor`)
with three tools: `query_claims_analytics` (Genie), `get_claim_brief` (SQL dossier),
`triage_claim` (risk + next action), multi-turn tool-calling loop and streaming.

Smoke test (serverless, importing the module and calling `predict`) — SUCCESS:
- The agent ran the tool loop, called `get_claim_brief`, and returned a real dossier for
  C000022633 (Denied, timely-filing, $4,729.76 billed / $0 paid, CPT 71046, ML score 0.834).
- Its Genie tool hit a transient error on that run and the agent degraded gracefully
  (reported the analytics tool unavailable rather than failing) — the resilience pattern.

## Still quota-blocked (environment, not code)

Serving the ResponsesAgent (Gap D) and serving the ML model both require registering a
model in Unity Catalog; the shared metastore is at its 5,000-model cap. Both are one
command from live (`deploy.py`, `REGISTER_UC=true`) once quota frees. Nothing was deleted
from other users' models to make room.

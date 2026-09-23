# Follow-ups and known open items

Things to resolve as the build hardens, and the product-accuracy items to confirm before presenting.

## Product accuracy to confirm (separate GA from preview, per AWS region)
- Standalone Lakebase deployment: components, auth, cataloging, operational effort, and CU sizing.
- Lakebase JSONB indexing and query behavior at claim scale; Lakebase synced tables relating the ODS to the lake.
- Metric-view YAML syntax (`WITH METRICS LANGUAGE YAML`): validate with the databricks-metric-views skill before deploy.
- Lakeflow declarative-pipeline decorator surface: validate with databricks-pipelines.
- Served-agent packaging (MLflow ResponsesAgent) and Unity Gateway routing: validate with databricks-model-serving.
- Real-time / OLTP-OLAP convergence claims: what is GA vs preview today.

## Build hardening
- Stream disposition events continuously (Structured Streaming) rather than batch refresh.
- Add a Lakebase synced table to keep `claim_status` in step with the lake automatically.
- Wire the ML `manual_review_score` and the agent `triage_score` into a single console ranking.
- Add per-claim UC-function output to `evidence/` as agent-tool proof.

## Deliberately out of scope for this build
- Denial prevention / revenue-cycle coding (provider-side, needs clinical notes).
- Fraud, waste, and abuse ML (valid payer play; heavier model; a strong next phase).

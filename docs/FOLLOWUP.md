# Follow-ups and known open items

Things to resolve as the build hardens, and the product-accuracy items to confirm before presenting.

## Product accuracy to confirm (separate GA from preview, per AWS region)
- Standalone Lakebase deployment: components, auth, cataloging, operational effort, and CU sizing.
- Lakebase JSONB indexing and query behavior at claim scale; Lakebase synced tables relating the ODS to the lake.
- Metric-view YAML syntax (`WITH METRICS LANGUAGE YAML`): validate with the databricks-metric-views skill before deploy.
- Lakeflow declarative-pipeline decorator surface: validate with databricks-pipelines.
- Served-agent packaging (MLflow ResponsesAgent) and Unity Gateway routing: validate with databricks-model-serving.
- Real-time / OLTP-OLAP convergence claims: what is GA vs preview today.

## Environment limits hit during the fevm run
- **UC registered-model quota:** the shared metastore is at its 5,000 registered-model cap, so the manual-review model could not be registered to Unity Catalog or served on Model Serving. The model trains, logs to MLflow, and scores the prioritization table fine. Re-run `07_ml_model/train_overturn_model.py` with `REGISTER_UC=true` once quota frees up (or on a metastore under the cap) to register + serve. Do not delete other users' models to make room.
- **ai_query batch inference** is not enabled on the foundation-model endpoints here; the triage agent uses online `serving-endpoints query` instead.
- **Metric-view `MEASURE()` YAML** dialect needs finalizing with the databricks-metric-views skill; certified plain-SQL views are used in the meantime.

## Build hardening
- Stream disposition events continuously (Structured Streaming) rather than batch refresh.
- Add a Lakebase synced table to keep `claim_status` in step with the lake automatically.
- Wire the ML `manual_review_score` and the agent `triage_score` into a single console ranking.
- Add per-claim UC-function output to `evidence/` as agent-tool proof.

## Deliberately out of scope for this build
- Denial prevention / revenue-cycle coding (provider-side, needs clinical notes).
- Fraud, waste, and abuse ML (valid payer play; heavier model; a strong next phase).

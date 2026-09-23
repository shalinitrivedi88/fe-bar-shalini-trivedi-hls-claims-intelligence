# 07 — ML model (manual-review likelihood)

A trained + served classifier that scores each claim's likelihood of needing manual review, feeding reviewer prioritization alongside the Gen AI agent. This is the traditional-ML MLOps story: MLflow to Unity Catalog to Model Serving.

## Files
- `train_overturn_model.py` — trains a GradientBoosting classifier on `requires_manual_review`, logs with MLflow, registers to Unity Catalog (`claim_manual_review_model`, alias `champion`), and writes a `claim_review_priority` table.
- `serving_endpoint.json` — Model Serving endpoint config.

## Honesty note
The synthetic label carries only a weak signal by design, so AUC will be modest. Report it as-is in `../evidence/ML_MODEL.md`. The BAR rewards the end-to-end pattern and the prioritization, not a fabricated AUC.

## Deploy the endpoint
```bash
source ../config.sh
databricks serving-endpoints create --json @serving_endpoint.json --profile "$DATABRICKS_PROFILE"
```

## Where it plugs in
`claim_review_priority.manual_review_score` joins to the ops console triage queue and the Lakebase `claim_status.triage_score`, so the highest-risk claims surface first in Harbor and the console.

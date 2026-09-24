# 07 — ML model (manual-review likelihood)

A trained + served classifier that scores each claim's likelihood of needing manual review, feeding reviewer prioritization alongside the Gen AI agent. This is the traditional-ML MLOps story: MLflow to Unity Catalog to Model Serving.

## Files
- `train_overturn_model.py` — trains a GradientBoosting classifier on `requires_manual_review`, logs with MLflow, registers to Unity Catalog (`claim_manual_review_model`, alias `champion`), and writes a `claim_review_priority` table.
- `serving_endpoint.json` — Model Serving endpoint config.

## Executed on fevm
Trained on serverless (run `f3d523bac709456f83ec2f8afe290bc9`), scored 50,000 claims into `claim_review_priority`. See [`../evidence/ML_MODEL.md`](../evidence/ML_MODEL.md). Test AUC 0.9241, reported with the honest caveat that the synthetic label is partly derived from features (`status`, `billed_amount`), so it is optimistic, not a real-world estimate.

**UC registration + serving were blocked by the shared-metastore 5,000 registered-model quota** (`QUOTA_EXCEEDED`), an environment limit, not a code issue. Re-run with `REGISTER_UC=true` to register + serve once quota frees up. We did not delete other users' models to make room.

## Deploy the endpoint
```bash
source ../config.sh
databricks serving-endpoints create --json @serving_endpoint.json --profile "$DATABRICKS_PROFILE"
```

## Where it plugs in
`claim_review_priority.manual_review_score` joins to the ops console triage queue and the Lakebase `claim_status.triage_score`, so the highest-risk claims surface first in Harbor and the console.

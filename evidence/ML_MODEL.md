# ML model evidence — manual-review likelihood

- **Training run:** MLflow run `f3d523bac709456f83ec2f8afe290bc9` on `fevm-serverless-stable-kysnws` (serverless job, 60s)
- **Prioritization table:** `serverless_stable_kysnws_catalog.claims_intelligence.claim_review_priority` (50,000 rows)
- **Captured:** 2026-09-23

## 1. Training (MLflow)
`07_ml_model/train_overturn_model.py` (GradientBoosting on `requires_manual_review`), output:
```json
{"test_auc": 0.9241, "run_id": "f3d523bac709456f83ec2f8afe290bc9", "registered": false, "scored_rows": 50000}
```
**Honest read of the AUC:** 0.9241 is optimistic by construction, not a real-world estimate. The synthetic label is partly derived from `status` and `billed_amount`, which are also model features, so the model recovers that relationship. On real claims the label would be independent of the features and AUC would be lower. The point here is the end-to-end MLOps pattern and the prioritization, not the score.

## 2. Prioritization table (feeds the console + Lakebase triage_score)
```sql
SELECT p.claim_id, ROUND(p.manual_review_score,3) AS score, c.status, c.denial_reason, c.billed_amount
FROM claim_review_priority p JOIN claims c ON p.claim_id=c.claim_id
ORDER BY p.manual_review_score DESC LIMIT 5;
```
| claim_id | score | status | denial_reason | billed_amount |
|---|---|---|---|---|
| C000006847 | 0.865 | Partially Paid | Duplicate claim / service | 4673.27 |
| C000021662 | 0.863 | Denied | Precertification / authorization absent | 4034.30 |
| C000021822 | 0.862 | Denied | Non-covered charge | 4413.89 |
| C000036475 | 0.852 | Denied | Charge exceeds fee schedule | 40.49 |
| C000022633 | 0.834 | Denied | Time limit for filing expired | 4729.76 |

Denied and partially-paid claims rise to the top of the review queue, which is the reviewer-prioritization outcome.

## 3. UC registration + Model Serving — blocked by a shared-metastore quota
Registering the model to Unity Catalog failed with:
```
QUOTA_EXCEEDED: Cannot create 1 Registered Model(s) in Metastore ... (estimated count: 5001, limit: 5000).
```
This is a shared-metastore limit (5,000 registered models), not a code issue. I did not delete other users' models to make room. The model is logged to the MLflow run and the prioritization table is written; UC registration and the Model Serving endpoint are a follow-up once quota frees up or on a metastore under the cap. Re-run with `REGISTER_UC=true` to register when possible. See `docs/FOLLOWUP.md`.

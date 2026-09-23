# ML model evidence

> TEMPLATE — replace placeholders with real output. Report AUC honestly.

- **Model:** `serverless_stable_kysnws_catalog.claims_intelligence.claim_manual_review_model` (alias `champion`)
- **Captured:** [DATE]

## 1. Training run (MLflow)
Output of `07_ml_model/train_overturn_model.py`:
[PASTE — "test AUC (reported honestly): 0.XXX"]

On synthetic data the label carries a weak signal by design, so a modest AUC is expected and reported as-is. The value is the end-to-end MLOps pattern and the prioritization score.

## 2. Registered in Unity Catalog
```bash
databricks registered-models get serverless_stable_kysnws_catalog.claims_intelligence.claim_manual_review_model --profile fevm
```
[PASTE — showing the registered model and champion alias]

## 3. Prioritization table written
```sql
SELECT claim_id, ROUND(manual_review_score, 3) AS score
FROM serverless_stable_kysnws_catalog.claims_intelligence.claim_review_priority
ORDER BY manual_review_score DESC LIMIT 10;
```
[PASTE — the highest-risk claims that feed the console]

## 4. Served on Model Serving
```bash
databricks serving-endpoints get claim-manual-review --profile fevm
```
[PASTE — endpoint ready]

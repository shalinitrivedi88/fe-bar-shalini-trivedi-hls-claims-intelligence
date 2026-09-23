# Lakebase deployment evidence

> TEMPLATE — replace placeholders with real output from the run. Do not fabricate.

- **Instance:** `cascade-claims-ods` (Lakebase managed Postgres) on `fevm-serverless-stable-kysnws`
- **Captured:** [DATE]

## 1. Instance provisioned
```bash
databricks database list-database-instances --profile fevm
```
[PASTE — showing cascade-claims-ods present and running]

## 2. Schema applied and seeded
Output of `03_lakebase_serving/seed_lakebase.py`:
[PASTE — "claims_ods.claim_status now holds N rows"]

## 3. Hybrid relational + JSON query returns current claim state
```sql
SELECT claim_id, status, triage_score,
       claim_detail->'adjudication'->>'cob_payer' AS cob_payer,
       jsonb_array_length(claim_detail->'line_items') AS line_count
FROM claims_ods.claim_status
WHERE member_id = '[SOME MEMBER]'
LIMIT 5;
```
[PASTE RESULT — proves relational columns and nested JSON queried together, the hybrid model working]

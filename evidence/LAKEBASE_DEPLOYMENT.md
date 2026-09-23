# Lakebase deployment evidence

- **Project:** `projects/cascade-claims-ods` (Lakebase Autoscaling Postgres, PG 17) on `fevm-serverless-stable-kysnws`
- **Branch/endpoint:** `production` (READY) / `primary` (ACTIVE, read-write, 1 CU, scale-to-zero 24h)
- **Host:** `ep-sweet-salad-d2luncba.database.us-east-1.cloud.databricks.com`
- **Captured:** 2026-09-23

## 1. Instance provisioned
```bash
databricks postgres create-project cascade-claims-ods --json '{"spec":{"display_name":"Cascade Claims ODS"}}' --profile fevm
databricks postgres list-branches projects/cascade-claims-ods --profile fevm
```
Output: project created, `production` branch `current_state: READY`, `primary` endpoint `ENDPOINT_TYPE_READ_WRITE` / `current_state: ACTIVE`, owner `shalini.trivedi@databricks.com`, `pg_version: 17`.

> Note: Lakebase Provisioned is retired; this uses the current Autoscaling model (`databricks postgres`, projects/branches/endpoints), not the legacy `databricks database` instance API.

## 2. Schema applied and seeded
Applied `schema.sql` and upserted 500 current claim-state rows (top by billed amount) from the governed Delta `claims` table via `databricks psql`:
```
SELECT COUNT(*) AS rows FROM claims_ods.claim_status;
 rows
------
  500
```

## 3. Hybrid relational + JSON query returns current claim state
Relational columns and nested JSON elements queried together (what the Harbor app reads):
```sql
SELECT claim_id, status, denial_reason, billed_amount,
       claim_detail->'adjudication'->>'cob_payer' AS cob_payer,
       jsonb_array_length(claim_detail->'line_items') AS line_count
FROM claims_ods.claim_status
WHERE status='Denied' AND requires_manual_review = true
ORDER BY billed_amount DESC LIMIT 5;
```
| claim_id | status | denial_reason | billed_amount | cob_payer | line_count |
|---|---|---|---|---|---|
| C000022633 | Denied | Time limit for filing expired | 4729.76 | Commercial | 6 |
| C000033599 | Denied | Not medically necessary | 4561.83 | Medicare | 6 |
| C000021822 | Denied | Non-covered charge | 4413.89 | Medicare | 6 |
| C000000424 | Denied | Claim lacks information | 4339.07 | Commercial | 6 |
| C000036058 | Denied | Precertification / authorization absent | 4292.96 | Commercial | 6 |

JSON containment filter (uses the GIN index over `claim_detail`):
```sql
SELECT COUNT(*) AS cob_claims FROM claims_ods.claim_status
WHERE claim_detail @> '{"adjudication":{"coordination_of_benefits":true}}';
-- cob_claims = 64
```

This is the "one store, both shapes" proof: relational columns for the structured fields, JSONB for the claim's long tail, queried together, served at OLTP latency to the application. Answers Priya's standalone-Lakebase and hybrid-model questions.

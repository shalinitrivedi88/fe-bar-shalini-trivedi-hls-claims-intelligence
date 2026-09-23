# Deploying the Lakebase claims ODS

Target: serverless FEVM workspace `fevm-serverless-stable-kysnws`, profile `fevm`.
Lakebase is Autoscaling-only now (the retired Provisioned `databricks database` API is not used); use `databricks postgres` (projects/branches/endpoints).

## 1. Create the project
```bash
source ../config.sh
databricks postgres create-project cascade-claims-ods \
  --json '{"spec":{"display_name":"Cascade Claims ODS"}}' --profile "$DATABRICKS_PROFILE"
# auto-creates the production branch + primary read-write endpoint (1 CU, scale-to-zero)
databricks postgres list-branches projects/cascade-claims-ods --profile "$DATABRICKS_PROFILE"
databricks postgres list-endpoints projects/cascade-claims-ods/branches/production --profile "$DATABRICKS_PROFILE"
```

## 2. Seed from the governed Delta table
The `databricks psql` wrapper handles OAuth and host resolution (needs a local `psql`; `brew install libpq`).
```bash
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"        # psql on PATH
python build_seed_sql.py                               # pulls claims from Delta -> /tmp/seed.sql
databricks psql --project cascade-claims-ods --profile "$DATABRICKS_PROFILE" -- -q -f /tmp/seed.sql
databricks psql --project cascade-claims-ods --profile "$DATABRICKS_PROFILE" -- -c "SELECT COUNT(*) FROM claims_ods.claim_status"
```

## 3. Validate the hybrid query (relational + JSON together)
```bash
databricks psql --project cascade-claims-ods --profile "$DATABRICKS_PROFILE" -- -P pager=off -c \
"SELECT claim_id, status, denial_reason, billed_amount, \
 claim_detail->'adjudication'->>'cob_payer' AS cob_payer, \
 jsonb_array_length(claim_detail->'line_items') AS line_count \
 FROM claims_ods.claim_status WHERE status='Denied' AND requires_manual_review ORDER BY billed_amount DESC LIMIT 5;"
```
Capture the output into `../evidence/LAKEBASE_DEPLOYMENT.md`.

## Why Lakebase here (not the lakehouse)
The Harbor application needs OLTP-latency reads of current claim state, and the claim's long tail is variable JSON while the structured fields are relational. That is a Postgres + JSONB job. Analytics stays on the lakehouse; operational reads go to Lakebase. One journey, right engine per job.

## Production path (beyond the demo seed)
For continuous freshness, replace the one-time seed with a Lakebase synced table from the Delta `claims` table (see the databricks-lakebase skill, synced-tables), so `claim_status` stays in step with the lake automatically.

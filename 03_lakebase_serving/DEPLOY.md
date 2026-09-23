# Deploying the Lakebase claims ODS

Target: serverless FEVM workspace `fevm-serverless-stable-kysnws`, profile `fevm`.

## 1. Create the Lakebase instance
```bash
source ../config.sh
databricks database create-database-instance \
  --json '{"name":"cascade-claims-ods","capacity":"CU_1"}' \
  --profile "$DATABRICKS_PROFILE"
databricks database list-database-instances --profile "$DATABRICKS_PROFILE"
```
Confirm the exact command surface and capacity options with the `databricks-lakebase` skill; Lakebase CLI flags evolve.

## 2. Apply the schema and seed
```bash
pip install psycopg2-binary databricks-sdk
python seed_lakebase.py    # applies schema.sql, upserts current claim state from Delta
```

## 3. Validate the hybrid query (relational + JSON together)
Run the example query in `schema.sql` and confirm it returns current claim state with nested JSON fields. Capture the output into `../evidence/LAKEBASE_DEPLOYMENT.md`.

## Why Lakebase here (not the lakehouse)
The Harbor application needs OLTP-latency reads of current claim state, and the claim's long tail is variable JSON while the structured fields are relational. That is a Postgres + JSONB job. Analytics stays on the lakehouse; operational reads go to Lakebase. One journey, right engine per job.

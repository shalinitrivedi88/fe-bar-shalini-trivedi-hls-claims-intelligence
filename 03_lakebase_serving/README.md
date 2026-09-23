# 03 — Lakebase serving (the claims ODS)

The operational store behind the Harbor application. Managed Postgres with a hybrid relational + JSONB model, so Harbor reads **current** claim state directly instead of a nightly extract.

## Files
- `schema.sql` — the `claims_ods.claim_status` table: relational columns + a JSONB `claim_detail` long tail, with a GIN index over the JSON and B-tree indexes for Harbor's query patterns.
- `build_seed_sql.py` — pulls current claim state from the governed Delta `claims` table and writes `/tmp/seed.sql`; apply with `databricks psql`.
- `DEPLOY.md` — create the project (Autoscaling `databricks postgres`), seed, validate.

Executed on `fevm`: project `projects/cascade-claims-ods` (PG 17), 500 rows seeded, hybrid query verified. See [`../evidence/LAKEBASE_DEPLOYMENT.md`](../evidence/LAKEBASE_DEPLOYMENT.md).

## What this proves
- Priya's standalone-Lakebase question: components, auth (OAuth token as password), cataloging, and the operational shape are all here.
- Renee's freshness pain: Harbor queries `claim_status` for the live disposition, not yesterday's batch.
- The hybrid model is real: one query filters on relational columns and nested JSON elements together.

Evidence goes to [`../evidence/LAKEBASE_DEPLOYMENT.md`](../evidence/LAKEBASE_DEPLOYMENT.md).

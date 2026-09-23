# 01 — Lakeflow ingest

Lands the synthetic claims book into the one governed schema
`serverless_stable_kysnws_catalog.claims_intelligence`, then curates a silver
layer with a Lakeflow Spark Declarative Pipeline.

## Files
- `generate_claims_data.py` — generates the fabricated book (members, providers, claims with a JSON `claim_detail` long tail, disposition events, prior auths, eligibility) and writes Delta tables. Seeded (`SEED=42`) so runs are reproducible.
- `pipeline.py` — Lakeflow declarative pipeline: `claims_silver` (JSON parsed into typed columns) and `open_dispositions_without_action` (the event-blindness gap).
- `create_tables.sql` — reference DDL for the six tables.

## The hybrid model (the point of this layer)
`claims` keeps the structured fields as relational columns and puts the variable long tail (line items, modifiers, dx pointers, adjudication elements, edits) in a JSON `claim_detail` column. This is the "thousands of data elements per claim" shape the customer described, in one table, queryable both ways.

## Run
```bash
source ../config.sh
# As a serverless notebook or job on the fevm workspace:
databricks jobs submit --profile "$DATABRICKS_PROFILE" ...   # or run generate_claims_data.py in a notebook
```
Generation parameters (defaults): 5,000 members, 500 providers, 50,000 claims, 15,000 prior auths. Override via env vars (`N_CLAIMS`, etc.).

## Capture evidence
After running, record row counts into [`../evidence/RUN_EVIDENCE.md`](../evidence/RUN_EVIDENCE.md) §1:
```sql
SELECT 'claims' t, COUNT(*) n FROM serverless_stable_kysnws_catalog.claims_intelligence.claims
UNION ALL SELECT 'disposition_events', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.disposition_events
UNION ALL SELECT 'members', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.members
UNION ALL SELECT 'providers', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.providers
UNION ALL SELECT 'prior_authorizations', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.prior_authorizations
UNION ALL SELECT 'eligibility', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.eligibility
ORDER BY t;
```

# App deployment evidence — Claims Operations Console

- **App:** `claims-ops-console` on `fevm-serverless-stable-kysnws`
- **URL:** https://claims-ops-console-7474644911133058.aws.databricksapps.com
- **Service principal:** `af1d4e1f-8a31-4fc3-9123-48c3a0e23563`
- **Captured:** 2026-09-23

## Deployment
```bash
databricks apps create claims-ops-console --profile fevm
databricks sync 06_databricks_app "/Workspace/Users/.../fe-bar/claims-ops-console" --profile fevm
databricks apps deploy claims-ops-console --source-code-path "/Workspace/Users/.../fe-bar/claims-ops-console" --profile fevm
```
Status: `app_status.state = RUNNING`, `active_deployment.status.state = SUCCEEDED`.

Grants to the app SP (so it reads the governed schema and warehouse):
```sql
GRANT USE CATALOG ON CATALOG serverless_stable_kysnws_catalog TO `af1d4e1f-...`;
GRANT USE SCHEMA ON SCHEMA serverless_stable_kysnws_catalog.claims_intelligence TO `af1d4e1f-...`;
GRANT SELECT ON SCHEMA serverless_stable_kysnws_catalog.claims_intelligence TO `af1d4e1f-...`;
-- warehouse a2fb11a86770690f: CAN_USE for the SP
```

## Live API over the governed schema (authenticated calls)

`GET /api/disposition-gap` (the event-blindness metric):
```json
[{"disposition":"Paid","dispositions":31463,"action_fired_rate":0.596},
 {"disposition":"Denied","dispositions":6492,"action_fired_rate":0.615},
 {"disposition":"Partially Paid","dispositions":3966,"action_fired_rate":0.59}]
```

`GET /api/triage-queue` (highest-value claims flagged for manual review), first rows:
```json
[{"claim_id":"C000036288","status":"Paid","denial_reason":null,"billed_amount":4736.7},
 {"claim_id":"C000022633","status":"Denied","denial_reason":"Time limit for filing expired","billed_amount":4729.76},
 {"claim_id":"C000006847","status":"Partially Paid","denial_reason":"Duplicate claim / service","billed_amount":4673.27},
 {"claim_id":"C000033599","status":"Denied","denial_reason":"Not medically necessary","billed_amount":4561.83}, ...]
```

The app reads the same governed schema the Genie space and the triage agent use, so the console, Genie, and the agent all speak one set of certified definitions.

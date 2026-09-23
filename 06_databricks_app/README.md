# 06 — Databricks App (Claims Operations Console)

Surfaces the build to the business: the highest-risk claims to review, the disposition-action gap, and a chat box, all over the one governed schema.

## Files
- `app.py` — FastAPI app: `/api/triage-queue`, `/api/disposition-gap`, `/api/chat` (proxies to the claims foundation model through the serving layer), plus a minimal dashboard at `/`.
- `app.yaml` — Databricks Apps run config.
- `requirements.txt`.

## Deploy
```bash
source ../config.sh
databricks apps create claims-ops-console --profile "$DATABRICKS_PROFILE"
databricks apps deploy claims-ops-console --source-code-path "$(pwd)" --profile "$DATABRICKS_PROFILE"
```
Grant the app's service principal read on `claims_intelligence` and use of the warehouse. For the AppKit (React/TypeScript) version with richer UI, use the `databricks-apps` skill; this Python app is the compact, deployable path.

## Note
The dashboard reads current claim state; wiring the triage queue to the Lakebase `claim_status.triage_score` (once `04_genai_agent/deploy.py` has scored) shows the reviewer-prioritization story end to end.

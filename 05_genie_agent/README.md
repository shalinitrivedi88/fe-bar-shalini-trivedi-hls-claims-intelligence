# 05 — Genie agent (claims analytics)

Lets a claims analyst ask in plain English and get a governed answer over the same certified metrics the app and the triage agent use. This is Daniel's self-serve, no-SQL-ticket layer.

## Files
- `general_instructions.txt` — space instructions, synonyms, and the certified-metric rules.
- `trusted_example_sql.sql` — trusted queries that teach Genie to resolve to `MEASURE()` over the metric views.

## Set up
Create the Genie space against the `claims_intelligence` schema, add the certified metric views (`claims_metrics`, `disposition_metrics`) plus the base tables, paste the general instructions, and register the trusted SQL. The `fe-internal-tools:genie-rooms` or `databricks-genie-agents` skill can author this programmatically.

## Capture evidence (the pass-critical trace)
Ask via the Genie Conversation API, for example: *"What is our downstream-action-fired rate by disposition, and where is the biggest gap?"* Capture the generated SQL (should select the metric view and `MEASURE()`), the natural-language answer, and the conversation id, verbatim, into `../evidence/RUN_EVIDENCE.md` §6.

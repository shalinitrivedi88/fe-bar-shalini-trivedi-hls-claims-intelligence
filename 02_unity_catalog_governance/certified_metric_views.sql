-- Certified Unity Catalog Metric Views over the governed schema.
-- These are real METRIC_VIEW objects (version 1.1) so Genie and dashboards resolve
-- questions to MEASURE(...), one governed definition per metric, not ad-hoc aggregates.
--
-- DEPLOY NOTE: the CLI `aitools tools query` mangles multi-line YAML; deploy these via
-- the SQL Statements API, which preserves newlines exactly:
--   python3 -c "import json;json.dump({'warehouse_id':'<WH>','statement':open('this.sql').read(),'wait_timeout':'30s'},open('/tmp/r.json','w'))"
--   databricks api post /api/2.0/sql/statements --json @/tmp/r.json --profile fevm
-- Requires DBR/DBSQL 17.2+ (metric views). Verified live on fevm as METRIC_VIEW.

CREATE OR REPLACE VIEW serverless_stable_kysnws_catalog.claims_intelligence.claims_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: serverless_stable_kysnws_catalog.claims_intelligence.claims
comment: Certified claims operations metrics
dimensions:
  - name: Status
    expr: status
  - name: Denial Reason
    expr: denial_reason
  - name: Claim Type
    expr: claim_type
  - name: Place Of Service
    expr: pos_desc
measures:
  - name: Claim Count
    expr: COUNT(1)
  - name: Billed Dollars
    expr: SUM(billed_amount)
  - name: Denied Dollars
    expr: SUM(CASE WHEN status = 'Denied' THEN billed_amount ELSE 0 END)
  - name: Pended Dollars
    expr: SUM(CASE WHEN status = 'Pending' THEN billed_amount ELSE 0 END)
  - name: Denial Rate
    expr: AVG(CASE WHEN status = 'Denied' THEN 1.0 ELSE 0.0 END)
  - name: Manual Review Rate
    expr: AVG(requires_manual_review)
$$;

CREATE OR REPLACE VIEW serverless_stable_kysnws_catalog.claims_intelligence.disposition_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: serverless_stable_kysnws_catalog.claims_intelligence.disposition_events
comment: Certified disposition and downstream-action metrics
dimensions:
  - name: Disposition
    expr: disposition
  - name: Action Type
    expr: action_type
measures:
  - name: Disposition Count
    expr: COUNT(1)
  - name: Downstream Action Fired Rate
    expr: AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0.0 END)
$$;

-- Plain-SQL helper views (kept for dashboards / non-MEASURE consumers)
CREATE OR REPLACE VIEW serverless_stable_kysnws_catalog.claims_intelligence.claims_dollar_exposure AS
SELECT status, COUNT(*) AS claims, ROUND(SUM(billed_amount)) AS total_billed, ROUND(SUM(paid_amount)) AS total_paid
FROM serverless_stable_kysnws_catalog.claims_intelligence.claims GROUP BY status ORDER BY total_billed DESC;

CREATE OR REPLACE VIEW serverless_stable_kysnws_catalog.claims_intelligence.disposition_action_gap AS
SELECT disposition, COUNT(*) AS dispositions,
       ROUND(AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0 END),3) AS action_fired_rate
FROM serverless_stable_kysnws_catalog.claims_intelligence.disposition_events GROUP BY disposition ORDER BY dispositions DESC;

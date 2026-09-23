-- Certified metric views over the governed schema.
-- These give Genie and the dashboard ONE governed definition each, so a
-- natural-language question resolves to MEASURE(`Disposition Rate`), not an ad-hoc AVG.
-- Metric-view YAML syntax evolves; validate with the databricks-metric-views skill
-- before deploying. A plain-SQL fallback is at the bottom (guaranteed to run).

USE CATALOG serverless_stable_kysnws_catalog;
USE SCHEMA claims_intelligence;

CREATE OR REPLACE VIEW claims_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Certified claims operations metrics'
AS $$
version: 0.1
source: serverless_stable_kysnws_catalog.claims_intelligence.claims
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

CREATE OR REPLACE VIEW disposition_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Certified disposition + downstream-action metrics'
AS $$
version: 0.1
source: serverless_stable_kysnws_catalog.claims_intelligence.disposition_events
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

-- ---------------------------------------------------------------------------
-- Plain-SQL fallback views (guaranteed to run if metric views need validation)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW claims_dollar_exposure AS
SELECT status,
       COUNT(*)               AS claims,
       ROUND(SUM(billed_amount)) AS total_billed,
       ROUND(SUM(paid_amount))   AS total_paid
FROM claims GROUP BY status ORDER BY total_billed DESC;

CREATE OR REPLACE VIEW disposition_action_gap AS
SELECT disposition,
       COUNT(*)                                                        AS dispositions,
       ROUND(AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0 END), 3) AS action_fired_rate
FROM disposition_events GROUP BY disposition ORDER BY dispositions DESC;

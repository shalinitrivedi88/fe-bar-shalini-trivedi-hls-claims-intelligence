-- Trusted example queries for the Genie space. These teach Genie to resolve
-- questions to the certified metric views with MEASURE(), not ad-hoc aggregates.

-- Downstream-action-fired rate by disposition (the event-blindness gap)
SELECT `Disposition`,
       MEASURE(`Disposition Count`)             AS dispositions,
       ROUND(MEASURE(`Downstream Action Fired Rate`), 3) AS action_fired_rate
FROM serverless_stable_kysnws_catalog.claims_intelligence.disposition_metrics
GROUP BY `Disposition`
ORDER BY dispositions DESC;

-- Denied + pending dollar exposure by claim type
SELECT `Claim Type`,
       ROUND(MEASURE(`Denied Dollars`)) AS denied_dollars,
       ROUND(MEASURE(`Pended Dollars`)) AS pended_dollars
FROM serverless_stable_kysnws_catalog.claims_intelligence.claims_metrics
GROUP BY `Claim Type`
ORDER BY denied_dollars DESC;

-- Billed dollars by denial reason (where the rework pool concentrates)
SELECT `Denial Reason`,
       MEASURE(`Claim Count`)  AS claims,
       ROUND(MEASURE(`Billed Dollars`)) AS billed
FROM serverless_stable_kysnws_catalog.claims_intelligence.claims_metrics
WHERE `Denial Reason` IS NOT NULL
GROUP BY `Denial Reason`
ORDER BY billed DESC;

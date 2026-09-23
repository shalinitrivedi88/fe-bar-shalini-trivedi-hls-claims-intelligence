-- Reference DDL for the governed claims schema.
-- The generator (generate_claims_data.py) creates these via saveAsTable; this
-- file documents the shape and can create empty tables as an alternative path.
-- Names are literal. Do not normalize.

CREATE CATALOG IF NOT EXISTS serverless_stable_kysnws_catalog;
CREATE SCHEMA IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence;

-- members: holds PHI-shaped columns (name, ssn, dob) the governance layer masks
CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.members (
  member_id STRING, subscriber_id STRING, member_name STRING,
  member_ssn STRING, member_dob STRING, plan_type STRING, state STRING
);

CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.providers (
  provider_id STRING, npi STRING, provider_name STRING,
  specialty STRING, in_network BOOLEAN
);

-- claims: relational columns + JSON claim_detail for the thousands-of-elements long tail
CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.claims (
  claim_id STRING, member_id STRING, provider_id STRING, claim_type STRING,
  status STRING, billed_amount DOUBLE, allowed_amount DOUBLE, paid_amount DOUBLE,
  denial_carc STRING, denial_reason STRING, place_of_service STRING, pos_desc STRING,
  primary_cpt STRING, primary_dx STRING, service_date STRING, received_date STRING,
  requires_manual_review INT, claim_detail STRING
);

CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.disposition_events (
  event_id STRING, claim_id STRING, disposition STRING, disposition_ts STRING,
  downstream_action_fired BOOLEAN, action_type STRING
);

CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.prior_authorizations (
  pa_id STRING, member_id STRING, provider_id STRING, cpt STRING,
  status STRING, requested_date STRING
);

CREATE TABLE IF NOT EXISTS serverless_stable_kysnws_catalog.claims_intelligence.eligibility (
  member_id STRING, plan_type STRING, effective_date STRING,
  term_date STRING, active BOOLEAN
);

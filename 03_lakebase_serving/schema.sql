-- Lakebase (managed Postgres) claims ODS schema.
-- HYBRID model: relational columns for structured fields + JSONB for the long tail.
-- This is the store the Harbor application reads for CURRENT claim state.

CREATE SCHEMA IF NOT EXISTS claims_ods;

-- Current claim state (upserted from disposition events; what Harbor reads)
CREATE TABLE IF NOT EXISTS claims_ods.claim_status (
  claim_id            TEXT PRIMARY KEY,
  member_id           TEXT NOT NULL,
  provider_id         TEXT NOT NULL,
  status              TEXT NOT NULL,
  billed_amount       NUMERIC(12,2),
  paid_amount         NUMERIC(12,2),
  denial_reason       TEXT,
  requires_manual_review BOOLEAN DEFAULT FALSE,
  triage_score        NUMERIC(5,4),          -- populated by 04_genai_agent / 07_ml_model
  triage_action       TEXT,                  -- next action proposed by the agent
  claim_detail        JSONB,                 -- the thousands-of-elements long tail
  last_disposition_ts TIMESTAMPTZ,
  updated_at          TIMESTAMPTZ DEFAULT now()
);

-- Query patterns Harbor uses
CREATE INDEX IF NOT EXISTS idx_claim_status_member ON claims_ods.claim_status (member_id);
CREATE INDEX IF NOT EXISTS idx_claim_status_status ON claims_ods.claim_status (status);
-- GIN index over the JSON long tail so the app can filter on nested elements
CREATE INDEX IF NOT EXISTS idx_claim_detail_gin ON claims_ods.claim_status USING GIN (claim_detail);

-- Example hybrid query (relational + JSON together), for evidence:
-- SELECT claim_id, status, triage_score,
--        claim_detail->'adjudication'->>'cob_payer' AS cob_payer,
--        jsonb_array_length(claim_detail->'line_items') AS line_count
-- FROM claims_ods.claim_status
-- WHERE member_id = 'M0000123' AND claim_detail @> '{"adjudication":{"coordination_of_benefits":true}}';

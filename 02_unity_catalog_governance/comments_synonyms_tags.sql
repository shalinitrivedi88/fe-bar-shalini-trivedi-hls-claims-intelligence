-- Enriched comments and domain tags. Comments help Genie ground; tags support
-- classification and discovery. (Genie synonyms are also set in the Genie space,
-- see 05_genie_agent/general_instructions.txt.)

USE CATALOG serverless_stable_kysnws_catalog;
USE SCHEMA claims_intelligence;

COMMENT ON TABLE claims IS
  'One row per submitted claim (837 shape). Relational columns plus a JSON claim_detail long tail (line items, adjudication elements).';
COMMENT ON TABLE disposition_events IS
  'Disposition of a claim and whether the downstream action fired. downstream_action_fired=false is the event-blindness gap.';

COMMENT ON COLUMN claims.denial_reason IS 'Human-readable CARC denial reason. Synonyms: denial, rejection reason, adjustment reason.';
COMMENT ON COLUMN claims.billed_amount IS 'Total charged amount on the claim. Synonyms: charge, submitted amount.';
COMMENT ON COLUMN claims.paid_amount   IS 'Amount paid after adjudication. Synonyms: reimbursement.';
COMMENT ON COLUMN claims.status        IS 'Adjudication status: Paid, Denied, Pending, Partially Paid.';
COMMENT ON COLUMN claims.requires_manual_review IS 'Label: claim needed manual review. Target for the 07_ml_model classifier.';
COMMENT ON COLUMN disposition_events.downstream_action_fired IS 'Whether a member notice / appeal route / payment-integrity review fired after disposition.';

-- Domain tags (governance classification)
ALTER TABLE members ALTER COLUMN member_ssn  SET TAGS ('data_class' = 'phi', 'pii' = 'true');
ALTER TABLE members ALTER COLUMN member_name SET TAGS ('data_class' = 'phi', 'pii' = 'true');
ALTER TABLE members ALTER COLUMN member_dob  SET TAGS ('data_class' = 'phi', 'pii' = 'true');
ALTER TABLE claims  SET TAGS ('domain' = 'claims', 'certified' = 'true');
ALTER TABLE disposition_events SET TAGS ('domain' = 'claims_ops');

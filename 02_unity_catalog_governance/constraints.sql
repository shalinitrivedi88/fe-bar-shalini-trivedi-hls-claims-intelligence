-- Declared PK/FK graph (RELY) over the governed claims schema.
-- RELY lets Genie infer joins from real relationships and lets the optimizer use them.
-- Declare RELY only after verifying zero orphan rows (the generator produces clean keys).

USE CATALOG serverless_stable_kysnws_catalog;
USE SCHEMA claims_intelligence;

-- PK columns must be NOT NULL first
ALTER TABLE members            ALTER COLUMN member_id   SET NOT NULL;
ALTER TABLE providers          ALTER COLUMN provider_id SET NOT NULL;
ALTER TABLE claims             ALTER COLUMN claim_id    SET NOT NULL;
ALTER TABLE disposition_events ALTER COLUMN event_id    SET NOT NULL;
ALTER TABLE prior_authorizations ALTER COLUMN pa_id     SET NOT NULL;

-- Primary keys
ALTER TABLE members            ADD CONSTRAINT members_pk   PRIMARY KEY (member_id)   RELY;
ALTER TABLE providers          ADD CONSTRAINT providers_pk PRIMARY KEY (provider_id) RELY;
ALTER TABLE claims             ADD CONSTRAINT claims_pk    PRIMARY KEY (claim_id)    RELY;
ALTER TABLE disposition_events ADD CONSTRAINT disp_pk      PRIMARY KEY (event_id)    RELY;
ALTER TABLE prior_authorizations ADD CONSTRAINT pa_pk      PRIMARY KEY (pa_id)       RELY;

-- Foreign keys
ALTER TABLE claims ADD CONSTRAINT claims_member_fk
  FOREIGN KEY (member_id)   REFERENCES members(member_id)     RELY;
ALTER TABLE claims ADD CONSTRAINT claims_provider_fk
  FOREIGN KEY (provider_id) REFERENCES providers(provider_id) RELY;
ALTER TABLE disposition_events ADD CONSTRAINT disp_claim_fk
  FOREIGN KEY (claim_id)    REFERENCES claims(claim_id)       RELY;
ALTER TABLE prior_authorizations ADD CONSTRAINT pa_member_fk
  FOREIGN KEY (member_id)   REFERENCES members(member_id)     RELY;
ALTER TABLE prior_authorizations ADD CONSTRAINT pa_provider_fk
  FOREIGN KEY (provider_id) REFERENCES providers(provider_id) RELY;

-- Evidence: list the constraints
-- SELECT table_name, constraint_type, constraint_name
-- FROM serverless_stable_kysnws_catalog.information_schema.table_constraints
-- WHERE table_schema = 'claims_intelligence' ORDER BY table_name, constraint_type;

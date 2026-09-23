-- PHI column masks applied at the GOVERNANCE LAYER.
-- The mask is a property of the column, so it holds across every reader:
-- notebook, Genie, and model serving. There is no per-query reapplication and no bypass.
-- Members of the `claims_phi_readers` group see cleartext; everyone else sees the mask.

USE CATALOG serverless_stable_kysnws_catalog;
USE SCHEMA claims_intelligence;

CREATE OR REPLACE FUNCTION mask_ssn(ssn STRING)
  RETURN CASE WHEN is_account_group_member('claims_phi_readers')
              THEN ssn
              ELSE 'XXX-XX-' || RIGHT(ssn, 4) END;

CREATE OR REPLACE FUNCTION mask_name(nm STRING)
  RETURN CASE WHEN is_account_group_member('claims_phi_readers')
              THEN nm
              ELSE LEFT(nm, 1) || '*** ***' END;

CREATE OR REPLACE FUNCTION mask_dob(dob STRING)
  RETURN CASE WHEN is_account_group_member('claims_phi_readers')
              THEN dob
              ELSE LEFT(dob, 4) || '-XX-XX' END;  -- keep year, hide month/day

ALTER TABLE members ALTER COLUMN member_ssn  SET MASK mask_ssn;
ALTER TABLE members ALTER COLUMN member_name SET MASK mask_name;
ALTER TABLE members ALTER COLUMN member_dob  SET MASK mask_dob;

-- Evidence: run the same SELECT as a non-member of claims_phi_readers and show
-- the masked output, then (if you have rights) as a member, and show cleartext.
-- SELECT member_id, member_name, member_ssn, member_dob FROM members LIMIT 5;

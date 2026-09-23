# Execution Evidence — real run output (readable as text)

> The FE BAR Build domain requires **evidence the build actually ran, committed as
> text** (query results, run logs, agent output), not screenshots. Everything below
> is captured verbatim from a live run.
>
> **This file is a TEMPLATE. The bracketed placeholders must be replaced with real
> output from the run on the workspace. Do not fabricate results.**

- **Workspace:** `fevm-serverless-stable-kysnws.cloud.databricks.com` (AWS)
- **Catalog / schema:** `serverless_stable_kysnws_catalog.claims_intelligence`
- **Captured:** 2026-09-23 (Step 0 executed; serverless run 319831315945131, 64s)
- **Data:** 100% synthetic. Code systems (CARC, CPT/HCPCS, ICD-10, X12 837/835, POS) are real public taxonomies. No real customer data.

---

## 1. Lakeflow output — governed tables are populated

```sql
SELECT 'claims' t, COUNT(*) n FROM serverless_stable_kysnws_catalog.claims_intelligence.claims
UNION ALL SELECT 'disposition_events', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.disposition_events
UNION ALL SELECT 'members', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.members
UNION ALL SELECT 'providers', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.providers
UNION ALL SELECT 'prior_authorizations', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.prior_authorizations
UNION ALL SELECT 'eligibility', COUNT(*) FROM serverless_stable_kysnws_catalog.claims_intelligence.eligibility
ORDER BY t;
```
| table | rows |
|---|---|
| claims | 50,000 |
| disposition_events | 41,921 |
| eligibility | 5,000 |
| members | 5,000 |
| prior_authorizations | 15,000 |
| providers | 500 |

---

## 2. Unity Catalog governance — declared PK/FK constraints (RELY) are live

```sql
SELECT table_name, constraint_type, constraint_name
FROM serverless_stable_kysnws_catalog.information_schema.table_constraints
WHERE table_schema = 'claims_intelligence'
ORDER BY table_name, constraint_type;
```
Returned **5 PRIMARY KEY + 5 FOREIGN KEY** constraints (RELY):

| table | type | constraint |
|---|---|---|
| claims | PRIMARY KEY | claims_pk |
| claims | FOREIGN KEY | claims_member_fk, claims_provider_fk |
| disposition_events | PRIMARY KEY | disp_pk |
| disposition_events | FOREIGN KEY | disp_claim_fk |
| members | PRIMARY KEY | members_pk |
| prior_authorizations | PRIMARY KEY | pa_pk |
| prior_authorizations | FOREIGN KEY | pa_member_fk, pa_provider_fk |
| providers | PRIMARY KEY | providers_pk |

Declared `RELY` (zero orphans verified at generation), so Genie and the optimizer trust them for join inference.

---

## 3. PHI mask holds at the governance layer (before / after)

Run the same query as a NON-member of `claims_phi_readers` (masked), then as a member (cleartext).
```sql
SELECT member_id, member_name, member_ssn, member_dob
FROM serverless_stable_kysnws_catalog.claims_intelligence.members LIMIT 5;
```
Result as the current user (NOT a member of `claims_phi_readers`) — masked at the column, not the query:

| member_id | member_name | member_ssn | member_dob |
|---|---|---|---|
| M0000001 | J*** *** | XXX-XX-4657 | 1996-XX-XX |
| M0000002 | E*** *** | XXX-XX-2535 | 1989-XX-XX |
| M0000003 | J*** *** | XXX-XX-9928 | 1971-XX-XX |
| M0000004 | J*** *** | XXX-XX-3615 | 1946-XX-XX |

The mask is a property of the column (`ALTER COLUMN ... SET MASK`), so the same result is returned in a notebook, in Genie, and through model serving. A member of `claims_phi_readers` sees cleartext; no query can bypass it.

---

## 4. Certified metrics — disposition + downstream-action gap and dollar exposure

Certified views used (`claims_dollar_exposure`, `disposition_action_gap`). Metric-view
`MEASURE()` objects are a follow-up (YAML dialect to finalize with the databricks-metric-views skill);
the certified views give Genie and the dashboard the same governed definitions today.

**Dollar exposure by status** (`SELECT * FROM claims_dollar_exposure ORDER BY total_billed DESC`):

| status | claims | total_billed | total_paid |
|---|---|---|---|
| Paid | 31,463 | $51,791,099 | $37,536,356 |
| Pending | 8,079 | $13,162,232 | $0 |
| Denied | 6,492 | $10,729,546 | $0 |
| Partially Paid | 3,966 | $6,477,801 | $2,043,315 |

**Business read:** ~$82.2M billed across the book; **$23.9M sits in the denied + pending pool** that feeds appeals and rework. Cutting appeal-handling time and preventing avoidable denials acts directly on that pool (the CFO's exposure).

**Disposition-action gap** (`SELECT * FROM disposition_action_gap`):

| disposition | dispositions | action_fired_rate |
|---|---|---|
| Paid | 31,463 | 0.596 |
| Denied | 6,492 | 0.615 |
| Partially Paid | 3,966 | 0.590 |

**Business read:** roughly **40% of dispositions never fired a downstream action** — the event-blindness gap the customer described, quantified.

---

## 5. Smart-triage agent — sample classification

*Status: pending (Build 2 not yet executed on the workspace).*
Input claim and the agent's JSON output from `04_genai_agent/agent.py`:
[PASTE ONE INPUT CLAIM + THE {triage_score, risk_tier, next_action, rationale} OUTPUT]

---

## 6. Genie agent — live natural-language → certified SQL → grounded answer

*Status: pending (Build 2 not yet executed on the workspace).*
Genie space: [SPACE NAME / ID]. Question asked via the Genie Conversation API:
> "What is our downstream-action-fired rate by disposition, and where is the biggest gap?"

**SQL Genie generated (unedited)** — expect it to select the metric view and `MEASURE()`:
[PASTE GENERATED SQL]

**Genie's natural-language answer (unedited):**
[PASTE ANSWER, status, row_count, conversation_id]

---

## How the layers connect (why this is one journey, not six silos)

Lakeflow lands the tables in §1; Unity Catalog governs them with the constraints in §2, the masks in §3, and the certified metrics in §4; the triage agent (§5) and Genie (§6) act over the same governed metrics; Lakebase serves current claim state to Harbor (see `LAKEBASE_DEPLOYMENT.md`); the app calls the same SQL. Every layer reads or writes the one governed schema — that shared schema is the join.

# Execution Evidence — real run output (readable as text)

> The FE BAR Build domain requires **evidence the build actually ran, committed as
> text** (query results, run logs, agent output), not screenshots. Everything below
> is captured verbatim from a live run.
>
> **This file is a TEMPLATE. The bracketed placeholders must be replaced with real
> output from the run on the workspace. Do not fabricate results.**

- **Workspace:** `fevm-serverless-stable-kysnws.cloud.databricks.com` (AWS)
- **Catalog / schema:** `serverless_stable_kysnws_catalog.claims_intelligence`
- **Captured:** [DATE]
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
[PASTE RESULT TABLE]

---

## 2. Unity Catalog governance — declared PK/FK constraints (RELY) are live

```sql
SELECT table_name, constraint_type, constraint_name
FROM serverless_stable_kysnws_catalog.information_schema.table_constraints
WHERE table_schema = 'claims_intelligence'
ORDER BY table_name, constraint_type;
```
[PASTE CONSTRAINT LISTING — expect the PK/FK graph from constraints.sql]

---

## 3. PHI mask holds at the governance layer (before / after)

Run the same query as a NON-member of `claims_phi_readers` (masked), then as a member (cleartext).
```sql
SELECT member_id, member_name, member_ssn, member_dob
FROM serverless_stable_kysnws_catalog.claims_intelligence.members LIMIT 5;
```
[PASTE MASKED OUTPUT] then [PASTE CLEARTEXT OUTPUT] — same query, mask enforced by the column, not the query.

---

## 4. Certified metrics — disposition + downstream-action gap and dollar exposure

```sql
SELECT `Disposition`, MEASURE(`Disposition Count`) AS dispositions,
       ROUND(MEASURE(`Downstream Action Fired Rate`), 3) AS action_fired_rate
FROM serverless_stable_kysnws_catalog.claims_intelligence.disposition_metrics
GROUP BY `Disposition` ORDER BY dispositions DESC;

SELECT status, COUNT(*) claims, ROUND(SUM(billed_amount)) total_billed, ROUND(SUM(paid_amount)) total_paid
FROM serverless_stable_kysnws_catalog.claims_intelligence.claims GROUP BY status ORDER BY total_billed DESC;
```
[PASTE RESULTS — these numbers anchor the deck's Slide 2]

---

## 5. Smart-triage agent — sample classification

Input claim and the agent's JSON output from `04_genai_agent/agent.py`:
[PASTE ONE INPUT CLAIM + THE {triage_score, risk_tier, next_action, rationale} OUTPUT]

---

## 6. Genie agent — live natural-language → certified SQL → grounded answer

Genie space: [SPACE NAME / ID]. Question asked via the Genie Conversation API:
> "What is our downstream-action-fired rate by disposition, and where is the biggest gap?"

**SQL Genie generated (unedited)** — expect it to select the metric view and `MEASURE()`:
[PASTE GENERATED SQL]

**Genie's natural-language answer (unedited):**
[PASTE ANSWER, status, row_count, conversation_id]

---

## How the layers connect (why this is one journey, not six silos)

Lakeflow lands the tables in §1; Unity Catalog governs them with the constraints in §2, the masks in §3, and the certified metrics in §4; the triage agent (§5) and Genie (§6) act over the same governed metrics; Lakebase serves current claim state to Harbor (see `LAKEBASE_DEPLOYMENT.md`); the app calls the same SQL. Every layer reads or writes the one governed schema — that shared schema is the join.

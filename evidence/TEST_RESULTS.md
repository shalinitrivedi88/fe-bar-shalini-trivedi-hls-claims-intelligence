# Functional test results

`python tests/run_tests.py` against the live `fevm` build. **35/35 passed** (2026-09-23).
Covers data integrity, governance, certified views, ML, Lakebase, the Gen AI agent, the app API, Genie, and cross-layer integration.

## Data integrity (12)
- D1 claims row count = 50000 — PASS
- D2 claim_id unique — PASS
- D3 members row count = 5000 — PASS
- D4 no orphan claims.member_id — PASS (0)
- D5 no orphan claims.provider_id — PASS (0)
- D6 no orphan disposition_events.claim_id — PASS (0)
- D7 claim_detail all valid JSON — PASS (0 unparseable)
- D8 paid_amount <= billed_amount — PASS (0 violations)
- D9 Denied => paid_amount = 0 — PASS (0)
- D10 Denied => denial_reason set — PASS (0)
- D11 requires_manual_review in (0,1) — PASS
- D12 status in allowed set — PASS

## Unity Catalog governance (4)
- G1 5 PK + 5 FK constraints present — PASS (10)
- G2 SSN masked on all rows — PASS (0 unmasked)
- G3 name masked on all rows — PASS (0)
- G4 dob masked on all rows — PASS (0)

## Certified views (3)
- V1 dollar_exposure reconciles to claims (±rounding) — PASS (claims 82,160,677; view 82,160,678; $1 rounding drift)
- V2 action_fired_rate in [0,1] — PASS
- V3 denial_reason_dollars has only non-null reasons — PASS

## ML prioritization (4)
- M1 claim_review_priority row count = 50000 — PASS
- M2 scores in [0,1] — PASS
- M3 no orphan priority claim_ids — PASS (0)
- M4 Denied avg score > Paid avg score — PASS (denied 0.466 vs paid 0.027)

## Lakebase ODS (3)
- L1 claim_status row count = 500 — PASS
- L2 hybrid JSON query (line_items) works — PASS (500 rows)
- L3 JSON containment over GIN index — PASS (64 COB claims)

## Gen AI triage agent (3)
- A1 denied high-dollar claim — PASS (appeal_route, 0.82)
- A2 clean paid claim — PASS (none, 0.02, correctly low risk)
- A3 minimal/sparse claim (edge) — PASS (returns valid schema, none/0.5)

## Databricks App API (3)
- P1 /api/disposition-gap → 200 + 3 rows — PASS
- P2 /api/triage-queue → 200 + 25 rows — PASS
- P3 unauthorized (no token) rejected — PASS (401)

## Genie NL→SQL (1)
- GE1 NL question returns COMPLETED with SQL over the governed schema — PASS

## Integration — one governed schema (2)
- I1 app disposition-gap == certified view (Denied 0.615) — PASS
- I2 Lakebase claim_status.status == Delta claims.status (sampled) — PASS

## Notes
- The triage agent is an LLM, so scores vary slightly run to run; assertions check schema, allowed `next_action`, and score range, plus directional sanity (denied high, clean paid low).
- ML UC registration + serving remain out of scope here (shared-metastore quota); the prioritization table they feed is fully tested.

# 02 — Unity Catalog governance

The semantic and compliance layer. This is what makes the natural-language answers trustworthy and the PHI story defensible.

## Files (run in this order)
1. `constraints.sql` — declared PK/FK graph as `RELY`. Genie infers joins from real relationships; the optimizer uses them.
2. `certified_metric_views.sql` — certified metric views (`claims_metrics`, `disposition_metrics`) so Genie resolves to `MEASURE(...)`, not ad-hoc aggregates. Plain-SQL fallback views included.
3. `phi_masks.sql` — PHI column masks on member name, SSN, DOB, applied at the governance layer so the mask holds across notebook, Genie, and model serving.
4. `comments_synonyms_tags.sql` — column comments (help Genie ground), domain and PHI tags.

## Why this matters for the BAR
Marcus, the CISO persona, asks for one masking story that holds everywhere and a lineage trail an auditor can trace. Daniel, the analytics persona, needs certified definitions so numbers tie across reports. Both are answered here, not in the app.

## Capture evidence (into ../evidence/RUN_EVIDENCE.md §2 to §3)
- The PK/FK constraint listing from `information_schema.table_constraints`.
- A PHI-mask before/after: the same `SELECT member_name, member_ssn` run as a non-member of `claims_phi_readers` (masked) versus a member (cleartext).
- A `MEASURE(\`Downstream Action Fired Rate\`)` result by disposition, and the dollar-exposure view.

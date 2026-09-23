"""
Build the Lakebase seed SQL from the governed Delta `claims` table.

Pulls current claim state (relational fields + the JSON claim_detail long tail)
from Unity Catalog via the Databricks CLI, and writes /tmp/seed.sql: the schema
plus INSERT ... ON CONFLICT rows for claims_ods.claim_status. Apply it with:

    export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
    python build_seed_sql.py
    databricks psql --project cascade-claims-ods --profile fevm -- -q -f /tmp/seed.sql

This is the demo seed path. For production, use a Lakebase synced table instead
(see DEPLOY.md) so the ODS stays in step with the lake automatically.
"""

import json
import os
import subprocess

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
PROFILE = os.environ.get("DATABRICKS_PROFILE", "fevm")
LIMIT = int(os.environ.get("SEED_LIMIT", "500"))
HERE = os.path.dirname(__file__)

sql = f"""SELECT c.claim_id, c.member_id, c.provider_id, c.status, c.billed_amount,
       c.paid_amount, c.denial_reason, c.requires_manual_review, c.claim_detail,
       MAX(d.disposition_ts) AS last_ts
FROM {CATALOG}.{SCHEMA}.claims c
LEFT JOIN {CATALOG}.{SCHEMA}.disposition_events d ON c.claim_id = d.claim_id
GROUP BY c.claim_id, c.member_id, c.provider_id, c.status, c.billed_amount,
         c.paid_amount, c.denial_reason, c.requires_manual_review, c.claim_detail
ORDER BY c.billed_amount DESC LIMIT {LIMIT}"""

out = subprocess.check_output(
    ["databricks", "experimental", "aitools", "tools", "query", sql, "--profile", PROFILE])
rows = json.loads(out)


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def num(v):
    return "NULL" if v is None else str(v)


def boolv(v):
    return "TRUE" if str(v) in ("1", "True", "true") else "FALSE"


def ts(v):
    return "NULL" if not v else "'" + str(v).replace("'", "''") + "'::timestamptz"


lines = [open(os.path.join(HERE, "schema.sql")).read()]
for r in rows:
    cd = r.get("claim_detail")
    cd_lit = "NULL" if cd is None else lit(cd) + "::jsonb"
    lines.append(
        "INSERT INTO claims_ods.claim_status (claim_id, member_id, provider_id, status, "
        "billed_amount, paid_amount, denial_reason, requires_manual_review, claim_detail, "
        "last_disposition_ts) VALUES ("
        f"{lit(r['claim_id'])}, {lit(r['member_id'])}, {lit(r['provider_id'])}, {lit(r['status'])}, "
        f"{num(r['billed_amount'])}, {num(r['paid_amount'])}, {lit(r['denial_reason'])}, "
        f"{boolv(r['requires_manual_review'])}, {cd_lit}, {ts(r.get('last_ts'))}) "
        "ON CONFLICT (claim_id) DO NOTHING;")

open("/tmp/seed.sql", "w").write("\n".join(lines) + "\n")
print(f"/tmp/seed.sql written: {len(rows)} claims")

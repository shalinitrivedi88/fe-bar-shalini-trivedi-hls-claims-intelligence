"""
Seed the Lakebase claims ODS from the governed Delta `claims` table.

Reads current claim state from Unity Catalog and upserts it into the Lakebase
Postgres `claims_ods.claim_status` table, carrying the JSON long tail into JSONB.
Demonstrates the operational store the Harbor application reads.

Lakebase auth pattern: connect to the instance's Postgres endpoint using the
database name and a short-lived OAuth token as the password. Provision the
instance and confirm the exact endpoint/credential flow with the
databricks-lakebase skill before running.
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
LAKEBASE_INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "cascade-claims-ods")
PG_DATABASE = os.environ.get("PG_DATABASE", "databricks_postgres")

w = WorkspaceClient()
spark = SparkSession.builder.getOrCreate()

# 1) Resolve the Lakebase Postgres endpoint + a fresh credential
inst = w.database.get_database_instance(name=LAKEBASE_INSTANCE)
host = inst.read_write_dns
cred = w.database.generate_database_credential(instance_names=[LAKEBASE_INSTANCE])
token = cred.token
user = w.current_user.me().user_name

conn = psycopg2.connect(host=host, dbname=PG_DATABASE, user=user,
                        password=token, sslmode="require", port=5432)
conn.autocommit = True
cur = conn.cursor()

# 2) Ensure schema/table exist (schema.sql is the source of truth)
with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
    cur.execute(f.read())

# 3) Pull current claim state from the governed Delta table
rows = spark.sql(f"""
    SELECT c.claim_id, c.member_id, c.provider_id, c.status,
           c.billed_amount, c.paid_amount, c.denial_reason,
           CAST(c.requires_manual_review AS BOOLEAN) AS requires_manual_review,
           c.claim_detail,
           MAX(d.disposition_ts) AS last_disposition_ts
    FROM {CATALOG}.{SCHEMA}.claims c
    LEFT JOIN {CATALOG}.{SCHEMA}.disposition_events d ON c.claim_id = d.claim_id
    GROUP BY ALL
""").collect()

# 4) Upsert into Lakebase
payload = [(
    r.claim_id, r.member_id, r.provider_id, r.status,
    r.billed_amount, r.paid_amount, r.denial_reason, r.requires_manual_review,
    json.dumps(json.loads(r.claim_detail)) if r.claim_detail else None,
    r.last_disposition_ts,
) for r in rows]

execute_values(cur, """
    INSERT INTO claims_ods.claim_status
      (claim_id, member_id, provider_id, status, billed_amount, paid_amount,
       denial_reason, requires_manual_review, claim_detail, last_disposition_ts)
    VALUES %s
    ON CONFLICT (claim_id) DO UPDATE SET
      status = EXCLUDED.status, paid_amount = EXCLUDED.paid_amount,
      denial_reason = EXCLUDED.denial_reason, claim_detail = EXCLUDED.claim_detail,
      last_disposition_ts = EXCLUDED.last_disposition_ts, updated_at = now()
""", payload, template="(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)", page_size=1000)

cur.execute("SELECT COUNT(*) FROM claims_ods.claim_status")
print(f"claims_ods.claim_status now holds {cur.fetchone()[0]:,} rows")
cur.close(); conn.close()

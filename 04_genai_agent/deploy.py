"""
Batch-score all recent dispositions with the triage agent and write the score +
proposed action back to Lakebase claim_status (feeds the ops console and Harbor).

For a served real-time endpoint, wrap triage_claim in an MLflow ResponsesAgent
and register/serve it via Model Serving (validate with databricks-model-serving).
This script is the batch path used to capture evidence.
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession
from agent import triage_claim

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
LAKEBASE_INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "cascade-claims-ods")

w = WorkspaceClient()
spark = SparkSession.builder.getOrCreate()

# Score open/denied dispositions (bound the sample for a demo run)
claims = spark.sql(f"""
    SELECT claim_id, status, denial_reason, billed_amount, primary_cpt, claim_detail
    FROM {CATALOG}.{SCHEMA}.claims
    WHERE status IN ('Denied', 'Partially Paid', 'Pending')
    LIMIT 200
""").collect()

results = []
for r in claims:
    claim = {"claim_id": r.claim_id, "status": r.status,
             "denial_reason": r.denial_reason, "billed_amount": r.billed_amount,
             "primary_cpt": r.primary_cpt,
             "claim_detail": json.loads(r.claim_detail) if r.claim_detail else {}}
    t = triage_claim(claim)
    results.append((float(t.get("triage_score", 0.5)),
                    t.get("next_action", "none"), r.claim_id))

# Write scores back to Lakebase
inst = w.database.get_database_instance(name=LAKEBASE_INSTANCE)
cred = w.database.generate_database_credential(instance_names=[LAKEBASE_INSTANCE])
conn = psycopg2.connect(host=inst.read_write_dns, dbname="databricks_postgres",
                        user=w.current_user.me().user_name, password=cred.token,
                        sslmode="require", port=5432)
conn.autocommit = True
cur = conn.cursor()
execute_values(cur, """
    UPDATE claims_ods.claim_status AS cs
    SET triage_score = d.score, triage_action = d.action, updated_at = now()
    FROM (VALUES %s) AS d(score, action, claim_id)
    WHERE cs.claim_id = d.claim_id
""", results, template="(%s,%s,%s)")
print(f"scored + wrote back {len(results)} claims")
cur.close(); conn.close()

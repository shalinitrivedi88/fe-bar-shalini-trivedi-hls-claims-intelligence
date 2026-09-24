"""
Generate claim case-narratives + embeddings for Lakebase hybrid search.

Builds a short free-text narrative per claim (the kind a member-services rep
searches when a member calls), embeds it with a Databricks foundation embedding
model, and writes a Delta table claim_narratives(claim_id, narrative, embedding).
build_search_sql.py then loads these into Lakebase pgvector + a tsvector column.

Runs as a serverless job. Deps: none beyond the base image (uses the workspace
OpenAI-compatible client for embeddings).
"""
import os, json
from pyspark.sql import SparkSession
from databricks.sdk import WorkspaceClient

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "databricks-bge-large-en")
LIMIT = int(os.environ.get("NARRATIVE_LIMIT", "500"))

spark = SparkSession.builder.getOrCreate()
w = WorkspaceClient()
client = w.serving_endpoints.get_open_ai_client()

# Same top-500 claims that are seeded in Lakebase (billed desc), with fields for a narrative
rows = spark.sql(f"""
    SELECT c.claim_id, c.status, c.denial_reason, c.claim_type, c.primary_cpt, c.primary_dx,
           c.pos_desc, c.billed_amount, p.provider_name, p.specialty,
           get_json_object(c.claim_detail,'$.adjudication.cob_payer') AS cob_payer
    FROM {CATALOG}.{SCHEMA}.claims c
    LEFT JOIN {CATALOG}.{SCHEMA}.providers p ON c.provider_id = p.provider_id
    ORDER BY c.billed_amount DESC LIMIT {LIMIT}
""").collect()


def narrative(r):
    base = (f"{r.claim_type} claim for {r.pos_desc or 'unspecified setting'}, "
            f"CPT {r.primary_cpt}, diagnosis {r.primary_dx}, billed ${r.billed_amount:.2f}, "
            f"provider {r.provider_name or 'unknown'} ({r.specialty or 'unspecified'}).")
    if r.status == "Denied":
        base += f" Claim was DENIED: {r.denial_reason}. Member is likely to appeal."
    elif r.status == "Partially Paid":
        base += f" Claim PARTIALLY PAID with adjustment: {r.denial_reason}."
    elif r.status == "Pending":
        base += " Claim is PENDING adjudication."
    else:
        base += " Claim was paid."
    if r.cob_payer and r.cob_payer not in ("None", None):
        base += f" Coordination of benefits with {r.cob_payer}."
    return base


narratives = [(r.claim_id, narrative(r)) for r in rows]

# Embed in batches
embs = []
B = 64
for i in range(0, len(narratives), B):
    batch = [n for _, n in narratives[i:i + B]]
    resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
    embs.extend([d.embedding for d in resp.data])

data = [{"claim_id": cid, "narrative": nar, "embedding": emb}
        for (cid, nar), emb in zip(narratives, embs)]

df = spark.createDataFrame(data)
df.write.mode("overwrite").option("overwriteSchema", "true") \
  .saveAsTable(f"{CATALOG}.{SCHEMA}.claim_narratives")

dim = len(embs[0]) if embs else 0
print(json.dumps({"rows": len(data), "embedding_dim": dim, "model": EMBED_MODEL}))
try:
    dbutils.notebook.exit(json.dumps({"rows": len(data), "embedding_dim": dim}))  # noqa: F821
except Exception:
    pass

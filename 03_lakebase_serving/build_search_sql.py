"""
Build the Lakebase pgvector + BM25 search seed from the Delta claim_narratives table.

Writes /tmp/search_seed.sql: enables pgvector, creates claims_ods.claim_notes
(claim_id, narrative, embedding vector(1024), tsv tsvector), inserts the rows,
and builds an HNSW cosine index + a GIN full-text index. Apply with:

    databricks psql --project cascade-claims-ods --profile fevm -- -q -f /tmp/search_seed.sql
"""
import json, os, subprocess

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
PROFILE = os.environ.get("DATABRICKS_PROFILE", "fevm")

out = subprocess.check_output(["databricks", "experimental", "aitools", "tools", "query",
    f"SELECT claim_id, narrative, embedding FROM {CATALOG}.{SCHEMA}.claim_narratives",
    "--profile", PROFILE])
rows = json.loads(out)


def vec(e):
    if isinstance(e, str):
        e = json.loads(e)
    return "[" + ",".join(f"{float(x):.6f}" for x in e) + "]"


def lit(s):
    return "'" + str(s).replace("'", "''") + "'"


dim = len(json.loads(rows[0]["embedding"]) if isinstance(rows[0]["embedding"], str) else rows[0]["embedding"])
lines = [
    "CREATE EXTENSION IF NOT EXISTS vector;",
    "DROP TABLE IF EXISTS claims_ods.claim_notes;",
    f"CREATE TABLE claims_ods.claim_notes (claim_id TEXT PRIMARY KEY, narrative TEXT, "
    f"embedding vector({dim}), tsv tsvector);",
]
for r in rows:
    lines.append(
        "INSERT INTO claims_ods.claim_notes (claim_id, narrative, embedding, tsv) VALUES ("
        f"{lit(r['claim_id'])}, {lit(r['narrative'])}, '{vec(r['embedding'])}'::vector, "
        f"to_tsvector('english', {lit(r['narrative'])})) ON CONFLICT (claim_id) DO NOTHING;")
lines += [
    "CREATE INDEX IF NOT EXISTS idx_notes_vec ON claims_ods.claim_notes USING hnsw (embedding vector_cosine_ops);",
    "CREATE INDEX IF NOT EXISTS idx_notes_tsv ON claims_ods.claim_notes USING GIN (tsv);",
]
open("/tmp/search_seed.sql", "w").write("\n".join(lines) + "\n")
print(f"/tmp/search_seed.sql written: {len(rows)} notes, dim {dim}")

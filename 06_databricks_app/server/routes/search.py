from fastapi import APIRouter
from pydantic import BaseModel
from .. import db

router = APIRouter()


class Query(BaseModel):
    q: str


@router.post("/api/search")
def search(body: Query):
    """Hybrid (semantic + keyword) search over claim case-narratives in Lakebase,
    fused with reciprocal-rank fusion. Finds similar prior cases when a member calls."""
    vec = "[" + ",".join(str(x) for x in db.embed(body.q)) + "]"
    sql = """
    WITH v AS (
      SELECT claim_id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(vec)s::vector) AS rk
      FROM claims_ods.claim_notes ORDER BY embedding <=> %(vec)s::vector LIMIT 30),
    k AS (
      SELECT claim_id, ROW_NUMBER() OVER (ORDER BY ts_rank(tsv, plainto_tsquery('english', %(q)s)) DESC) AS rk
      FROM claims_ods.claim_notes WHERE tsv @@ plainto_tsquery('english', %(q)s) LIMIT 30)
    SELECT n.claim_id, n.narrative,
           ROUND((COALESCE(1.0/(60+v.rk),0) + COALESCE(1.0/(60+k.rk),0))::numeric, 5) AS rrf_score
    FROM claims_ods.claim_notes n
    LEFT JOIN v ON n.claim_id=v.claim_id
    LEFT JOIN k ON n.claim_id=k.claim_id
    WHERE v.rk IS NOT NULL OR k.rk IS NOT NULL
    ORDER BY rrf_score DESC LIMIT 10
    """
    try:
        return {"results": db.lakebase_query(sql, {"vec": vec, "q": body.q})}
    except Exception as e:
        return {"results": [], "error": str(e)[:200]}

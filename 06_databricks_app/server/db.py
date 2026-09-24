"""Shared data access: SQL warehouse, Lakebase Postgres, and embeddings.

All three use the app's own identity via the Databricks SDK, so the same code
runs locally (CLI profile) and inside a deployed Databricks App (service principal).
"""
import functools
from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient
from . import config

_w = WorkspaceClient()


def warehouse_query(q: str):
    cfg = _w.config
    with dbsql.connect(server_hostname=cfg.host.replace("https://", ""),
                       http_path=f"/sql/1.0/warehouses/{config.WAREHOUSE_ID}",
                       credentials_provider=lambda: cfg.authenticate) as c:
        with c.cursor() as cur:
            cur.execute(q)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def embed(text: str):
    """Embed a query string with the foundation embedding endpoint."""
    client = _w.serving_endpoints.get_open_ai_client()
    r = client.embeddings.create(model=config.EMBED_MODEL, input=[text])
    return r.data[0].embedding


def chat(system: str, user: str) -> str:
    client = _w.serving_endpoints.get_open_ai_client()
    # note: some models (gpt-5-6-sol) only accept the default temperature, so we omit it
    r = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content


@functools.lru_cache(maxsize=1)
def _lakebase_host():
    """Resolve the Lakebase primary endpoint host once (Autoscaling postgres API)."""
    ep = f"projects/{config.LAKEBASE_PROJECT}/branches/production/endpoints/primary"
    info = _w.api_client.do("GET", f"/api/2.0/postgres/{ep}")
    return ep, info["status"]["hosts"]["host"]


def lakebase_query(q: str, params=None):
    """Run a read query against the Lakebase claims ODS. Fresh OAuth credential per call."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    ep, host = _lakebase_host()
    cred = _w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": ep})
    token = cred["token"]
    user = _w.current_user.me().user_name
    conn = psycopg2.connect(host=host, dbname="databricks_postgres", user=user,
                            password=token, sslmode="require", port=5432,
                            cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(q, params or ())
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

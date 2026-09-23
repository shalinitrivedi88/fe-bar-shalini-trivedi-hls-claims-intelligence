"""
Claims Operations Console — a Databricks App (FastAPI).

Two surfaces over the ONE governed schema:
  /api/triage-queue  — highest-risk claims needing review (governed SQL)
  /api/disposition-gap — dispositions that never fired a downstream action
  /api/chat          — proxies a question to the claims foundation model (Unity Gateway)

Runs on Databricks Apps. Auth uses the app's own credentials (service principal)
via the SQL warehouse and serving layer. For the AppKit (React/TypeScript)
version, use the databricks-apps skill; this Python app is the compact path.
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "a2fb11a86770690f")
MODEL = os.environ.get("TRIAGE_MODEL", "databricks-gpt-5-6-sol")

cfg = Config()
app = FastAPI(title="Claims Operations Console")


def query(q: str):
    with sql.connect(server_hostname=cfg.host.replace("https://", ""),
                     http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
                     credentials_provider=lambda: cfg.authenticate) as c:
        with c.cursor() as cur:
            cur.execute(q)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


@app.get("/api/triage-queue")
def triage_queue():
    return query(f"""
        SELECT claim_id, status, denial_reason, billed_amount
        FROM {CATALOG}.{SCHEMA}.claims
        WHERE requires_manual_review = 1
        ORDER BY billed_amount DESC LIMIT 25
    """)


@app.get("/api/disposition-gap")
def disposition_gap():
    return query(f"""
        SELECT disposition, COUNT(*) AS dispositions,
               ROUND(AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0 END), 3) AS action_fired_rate
        FROM {CATALOG}.{SCHEMA}.disposition_events
        GROUP BY disposition ORDER BY dispositions DESC
    """)


class Ask(BaseModel):
    question: str


@app.post("/api/chat")
def chat(a: Ask):
    from openai import OpenAI
    w = WorkspaceClient()
    client = OpenAI(api_key=w.config.token, base_url=f"{w.config.host}/serving-endpoints")
    r = client.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[{"role": "system", "content": "You answer claims-ops questions concisely."},
                  {"role": "user", "content": a.question}])
    return {"answer": r.choices[0].message.content}


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta charset=utf-8>
<title>Claims Operations Console</title>
<style>body{font:14px system-ui;margin:2rem;color:#1b2733}
h1{font-size:20px}table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #e3e8ee;padding:6px 10px;text-align:left}
button{padding:6px 12px}</style></head><body>
<h1>Claims Operations Console</h1>
<p>Cascade Benefit Systems (fictional). Highest-risk claims and the disposition-action gap.</p>
<h3>Triage queue</h3><div id=q>loading...</div>
<h3>Ask</h3><input id=k size=60 placeholder="downstream-action-fired rate by disposition?">
<button onclick=ask()>Ask</button><pre id=a></pre>
<script>
fetch('/api/triage-queue').then(r=>r.json()).then(d=>{
 let h='<table><tr><th>Claim</th><th>Status</th><th>Reason</th><th>Billed</th></tr>';
 d.forEach(x=>h+=`<tr><td>${x.claim_id}</td><td>${x.status}</td><td>${x.denial_reason||''}</td><td>$${x.billed_amount}</td></tr>`);
 document.getElementById('q').innerHTML=h+'</table>';});
function ask(){fetch('/api/chat',{method:'POST',headers:{'content-type':'application/json'},
 body:JSON.stringify({question:document.getElementById('k').value})})
 .then(r=>r.json()).then(d=>document.getElementById('a').textContent=d.answer);}
</script></body></html>"""

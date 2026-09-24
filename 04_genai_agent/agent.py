"""
Cascade claims-triage supervisor — a code-based MLflow ResponsesAgent.

A multi-turn tool-calling agent that resolves claims-operations questions by
routing to the right tool and synthesizing one answer:

  1. query_claims_analytics  -> the Cascade Claims Genie space (NL over certified metrics)
  2. get_claim_brief         -> a per-claim dossier (claim + disposition + ML score) via SQL
  3. triage_claim            -> risk score + next action for a single claim

Output matches the Databricks Agent Framework ResponsesAgent schema, so it can be
logged, registered to Unity Catalog, and served on Model Serving with no changes
to the calling app (server/routes/chat.py can proxy to it). Serving requires a UC
model registration (see deploy.py); the agent logic runs and is testable without it.
"""
from __future__ import annotations
import json, os, uuid, logging
from typing import Any, Callable, Iterator

from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest, ResponsesAgentResponse, ResponsesAgentStreamEvent)
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

LLM_ENDPOINT = os.environ.get("AGENT_LLM", "databricks-claude-opus-4-8")
CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "a2fb11a86770690f")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "01f1b7a7a3511f52a02ca9d65a9d353f")
MAX_TURNS = 8
FQ = f"{CATALOG}.{SCHEMA}"

SYSTEM_PROMPT = (
    "You are the claims-triage supervisor for a health-plan claims processor "
    "(Cascade Benefit Systems, synthetic data). Help case workers resolve questions "
    "about claims, denials, dispositions, and the review queue.\n"
    "Tools:\n"
    "  - query_claims_analytics: aggregate/trend questions over certified metrics (disposition "
    "rates, the downstream-action gap, denial dollars). Ask a single NL question.\n"
    "  - get_claim_brief: pull one claim's dossier (status, denial reason, dollars, ML review score).\n"
    "  - triage_claim: score a single claim's manual-review risk and propose the next action.\n"
    "Start with query_claims_analytics for population questions and get_claim_brief for a "
    "specific claim_id. Synthesize one concise, professional answer; cite claim ids and numbers verbatim."
)


class ToolInfo(BaseModel):
    name: str
    spec: dict
    exec_fn: Callable[..., str]
    model_config = {"arbitrary_types_allowed": True}


def _warehouse_query(ws: WorkspaceClient, q: str) -> list[dict]:
    from databricks import sql as dbsql
    cfg = ws.config
    with dbsql.connect(server_hostname=cfg.host.replace("https://", ""),
                       http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
                       credentials_provider=lambda: cfg.authenticate) as c:
        with c.cursor() as cur:
            cur.execute(q)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def _genie_exec(ws: WorkspaceClient):
    from databricks.sdk.service.dashboards import GenieAPI
    api = GenieAPI(ws.api_client)
    def _exec(question: str) -> str:
        convo = api.start_conversation_and_wait(GENIE_SPACE_ID, question)
        msg = convo.message
        parts = []
        for a in (getattr(msg, "attachments", None) or []):
            q = getattr(a, "query", None)
            if q and getattr(q, "query", None):
                parts.append(f"SQL: {q.query}")
            t = getattr(a, "text", None)
            if t and getattr(t, "content", None):
                parts.append(t.content)
        return "\n".join(parts) or "[no answer]"
    return _exec


def _claim_brief_exec(ws: WorkspaceClient):
    def _exec(claim_id: str) -> str:
        rows = _warehouse_query(ws, f"""
            SELECT c.claim_id, c.status, c.denial_reason, c.billed_amount, c.paid_amount,
                   c.primary_cpt, c.primary_dx, ROUND(p.manual_review_score,3) AS review_score
            FROM {FQ}.claims c LEFT JOIN {FQ}.claim_review_priority p ON c.claim_id=p.claim_id
            WHERE c.claim_id = '{claim_id.replace("'", "")}'""")
        return json.dumps(rows[0], default=str) if rows else f"[no claim {claim_id}]"
    return _exec


def _triage_exec(ws: WorkspaceClient):
    def _exec(claim_summary: str) -> str:
        client = ws.serving_endpoints.get_open_ai_client()
        r = client.chat.completions.create(model=LLM_ENDPOINT, messages=[
            {"role": "system", "content": "Return STRICT JSON: triage_score(0-1), risk_tier, next_action(member_notice|appeal_route|payment_integrity_review|none), rationale."},
            {"role": "user", "content": claim_summary}])
        return r.choices[0].message.content
    return _exec


def _tools(ws: WorkspaceClient) -> list[ToolInfo]:
    def spec(name, desc, props, required):
        return {"type": "function", "function": {"name": name, "description": desc,
                "parameters": {"type": "object", "properties": props, "required": required}}}
    return [
        ToolInfo(name="query_claims_analytics",
                 spec=spec("query_claims_analytics", "NL question over certified claims metrics.",
                           {"question": {"type": "string"}}, ["question"]),
                 exec_fn=_genie_exec(ws)),
        ToolInfo(name="get_claim_brief",
                 spec=spec("get_claim_brief", "Dossier for one claim id.",
                           {"claim_id": {"type": "string"}}, ["claim_id"]),
                 exec_fn=_claim_brief_exec(ws)),
        ToolInfo(name="triage_claim",
                 spec=spec("triage_claim", "Risk score + next action for a claim summary.",
                           {"claim_summary": {"type": "string"}}, ["claim_summary"]),
                 exec_fn=_triage_exec(ws)),
    ]


class ClaimsTriageSupervisor(ResponsesAgent):
    def __init__(self):
        self._ws = None; self._tool_cache = None

    def ws(self):
        if self._ws is None: self._ws = WorkspaceClient()
        return self._ws

    def tools(self):
        if self._tool_cache is None: self._tool_cache = _tools(self.ws())
        return self._tool_cache

    def _llm(self, messages, tools):
        client = self.ws().serving_endpoints.get_open_ai_client()
        # some endpoints (Claude Opus, gpt-5-6-sol) only accept the default temperature, so omit it
        return client.chat.completions.create(model=LLM_ENDPOINT, messages=messages,
                                              tools=[t.spec for t in tools], tool_choice="auto")

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        items = [ev.item for ev in self.predict_stream(request)
                 if ev.type == "response.output_item.done"]
        return ResponsesAgentResponse(output=items)

    def predict_stream(self, request: ResponsesAgentRequest) -> Iterator[ResponsesAgentStreamEvent]:
        tools = self.tools(); by_name = {t.name: t for t in tools}
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for inp in request.input:
            d = inp.model_dump() if hasattr(inp, "model_dump") else dict(inp)
            msgs.append({"role": d.get("role", "user"), "content": d.get("content", "")})
        for _ in range(MAX_TURNS):
            resp = self._llm(msgs, tools)
            m = resp.choices[0].message
            if not m.tool_calls:
                item = {"id": f"msg_{uuid.uuid4().hex}", "type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": m.content or ""}]}
                yield ResponsesAgentStreamEvent(type="response.output_item.done", item=item)
                return
            msgs.append({"role": "assistant", "content": m.content,
                         "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
            for tc in m.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                try:
                    out = by_name[tc.function.name].exec_fn(**args)
                except Exception as e:
                    out = f"[tool error: {e}]"
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})


AGENT = ClaimsTriageSupervisor()

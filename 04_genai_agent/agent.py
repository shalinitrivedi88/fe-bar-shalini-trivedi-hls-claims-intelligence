"""
Smart claims-triage agent.

On a claim disposition, the agent reads the claim (relational fields + JSON long
tail), classifies risk and complexity, and proposes the next action
(member_notice | appeal_route | payment_integrity_review | none). It calls a
Databricks foundation model through the workspace serving layer (Unity Gateway),
so model routing, usage, and cost are governed centrally.

The score + action are written back to the Lakebase claim_status row so the
Harbor app and the ops console surface the highest-risk claims first.

Validate the served-agent packaging (MLflow ResponsesAgent) with the
databricks-model-serving and databricks-ml-training skills before deploying.
"""

import os
import json
from openai import OpenAI          # OpenAI-compatible client, Databricks serving
from databricks.sdk import WorkspaceClient

# Route through the workspace serving layer (Unity Gateway governs this endpoint)
MODEL = os.environ.get("TRIAGE_MODEL", "databricks-gpt-5-6-sol")

_w = WorkspaceClient()
_client = OpenAI(
    api_key=_w.config.token,
    base_url=f"{_w.config.host}/serving-endpoints",
)

SYSTEM = """You are a claims triage assistant for a health plan claims processor.
Given one claim, return STRICT JSON with keys:
  triage_score  (0.0-1.0, likelihood this claim needs human review)
  risk_tier     ("high" | "medium" | "low")
  next_action   ("member_notice" | "appeal_route" | "payment_integrity_review" | "none")
  rationale     (one sentence, cite the specific field that drove the decision)
Base the decision only on the claim provided. Do not invent facts."""


def triage_claim(claim: dict) -> dict:
    """claim: a dict with relational fields + a `claim_detail` dict (parsed JSON)."""
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(claim, default=str)},
        ],
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    # tolerate code-fenced JSON
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        out = {"triage_score": 0.5, "risk_tier": "medium",
               "next_action": "none", "rationale": "unparseable model output"}
    return out


if __name__ == "__main__":
    # Smoke test on one synthetic claim
    demo = {
        "claim_id": "C000000123", "status": "Denied",
        "denial_reason": "Precertification / authorization absent",
        "billed_amount": 4200.0, "primary_cpt": "99214",
        "claim_detail": {"adjudication": {"edits_triggered": ["NCCI-PTP"]}},
    }
    print(json.dumps(triage_claim(demo), indent=2))

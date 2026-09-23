# 04 — Gen AI smart-triage agent

Classifies each claim on disposition and proposes the next action, so reviewers start with the highest-risk work and every disposition can fire a governed action instead of waiting for a batch.

## Files
- `agent.py` — `triage_claim(claim)`: calls a Databricks foundation model through the workspace serving layer (Unity Gateway governs routing, usage, cost) and returns `{triage_score, risk_tier, next_action, rationale}`.
- `deploy.py` — batch-scores dispositions and writes the score + action back to the Lakebase `claim_status` row.
- `requirements.txt`.

## Governance angle
Model calls route through the serving layer, which is the Unity Gateway control and cost point Marcus asked for. The agent reasons only over the claim provided and cites the field that drove the decision, which is the auditability Omar-style compliance review needs.

## Both agents, on purpose
This is the **reasoning** agent (acts on a single claim). The Genie agent in `05_genie_agent` is the **analytics** agent (answers population questions over the same certified metrics). A passing reference build shipped both plus a trained model; this build does the same.

Evidence: capture a sample `triage_claim` input/output into `../evidence/RUN_EVIDENCE.md`.

"""
Log, (optionally) register, and serve the ClaimsTriageSupervisor ResponsesAgent.

Logging works today. Registration to Unity Catalog + Model Serving are gated on
REGISTER_UC=true because the shared metastore is at its 5,000 registered-model
quota (see docs/FOLLOWUP.md). Once quota frees, run with REGISTER_UC=true to
register and stand up the endpoint; server/routes/chat.py can then proxy to it.

Run as a serverless job. Deps: mlflow, databricks-sdk[openai], databricks-sql-connector, openai.
"""
import os, mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksGenieSpace, DatabricksSQLWarehouse

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.claims_triage_agent"
REGISTER = os.environ.get("REGISTER_UC", "false").lower() == "true"
LLM = os.environ.get("AGENT_LLM", "databricks-claude-opus-4-8")
GENIE_SPACE = os.environ.get("GENIE_SPACE_ID", "01f1b7a7a3511f52a02ca9d65a9d353f")
WAREHOUSE = os.environ.get("WAREHOUSE_ID", "a2fb11a86770690f")

mlflow.set_registry_uri("databricks-uc")

# Declare the resources the served agent needs (auto-provisions auth on serving)
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM),
    DatabricksGenieSpace(genie_space_id=GENIE_SPACE),
    DatabricksSQLWarehouse(warehouse_id=WAREHOUSE),
]

with mlflow.start_run(run_name="claims_triage_agent"):
    info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",   # the ResponsesAgent module (AGENT instance)
        resources=resources,
        pip_requirements=["mlflow", "databricks-sdk[openai]", "databricks-sql-connector", "openai"],
        registered_model_name=(MODEL_NAME if REGISTER else None),
    )
    print("logged:", info.model_uri)

if REGISTER:
    from databricks.agents import deploy
    deploy(MODEL_NAME, info.registered_model_version)  # creates the serving endpoint
    print("served:", MODEL_NAME)
else:
    print("Registration/serving skipped (REGISTER_UC!=true). Metastore model quota is full; "
          "re-run with REGISTER_UC=true when it frees.")

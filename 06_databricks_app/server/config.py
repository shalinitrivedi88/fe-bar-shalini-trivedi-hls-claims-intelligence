"""App configuration, read from env (set in app.yaml)."""
import os

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
FQ = f"{CATALOG}.{SCHEMA}"
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "a2fb11a86770690f")
LAKEBASE_PROJECT = os.environ.get("LAKEBASE_PROJECT", "cascade-claims-ods")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "databricks-bge-large-en")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "databricks-gpt-5-6-sol")

# Shared configuration for the Cascade Benefit Systems claims FE BAR build.
# Source this before running the setup scripts:  source config.sh
#
# Cascade Benefit Systems is a FICTIONAL company created for this capstone.
# All data is synthetic. No real customer or PHI is referenced.

export DATABRICKS_PROFILE="fevm"
export WORKSPACE_HOST="https://fevm-serverless-stable-kysnws.cloud.databricks.com"

# Unity Catalog target (one governed schema all six layers read/write)
export CATALOG="serverless_stable_kysnws_catalog"
export SCHEMA="claims_intelligence"

# Lakebase claims ODS (created in 03_lakebase_serving)
export LAKEBASE_INSTANCE="cascade-claims-ods"

# Serverless SQL warehouse (Genie + dashboard). Verified present on the workspace.
export WAREHOUSE_ID="a2fb11a86770690f"

"""
Train + register + score a manual-review-likelihood model.

Target: claims.requires_manual_review. Features: status, denial_reason, claim_type,
place_of_service, billed_amount, line_count, has_cob. Trains with MLflow, registers
to Unity Catalog, and scores all claims into a reviewer-prioritization table.

On synthetic data the label carries only a weak signal by design, so AUC will be
modest. Report it honestly. The value is the end-to-end MLOps pattern
(MLflow -> Unity Catalog -> Model Serving) and the prioritization score that
feeds the ops console and the Lakebase claim_status row.

Validate the current registration/serving surface with databricks-ml-training
and databricks-model-serving.
"""

import os
import mlflow
import pandas as pd
from pyspark.sql import SparkSession, functions as F
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.claim_manual_review_model"

spark = SparkSession.builder.getOrCreate()
mlflow.set_registry_uri("databricks-uc")

# Load features (parse a couple of fields out of the JSON long tail)
df = spark.sql(f"""
    SELECT status, denial_reason, claim_type, pos_desc, billed_amount,
           get_json_object(claim_detail, '$.adjudication.coordination_of_benefits') AS has_cob,
           requires_manual_review AS label
    FROM {CATALOG}.{SCHEMA}.claims
""").fillna({"denial_reason": "none"}).toPandas()

y = df.pop("label").astype(int)
cat = ["status", "denial_reason", "claim_type", "pos_desc", "has_cob"]
num = ["billed_amount"]
pre = ColumnTransformer([
    ("c", OneHotEncoder(handle_unknown="ignore"), cat),
    ("n", StandardScaler(), num)])
clf = Pipeline([("pre", pre), ("gb", GradientBoostingClassifier(random_state=42))])

Xtr, Xte, ytr, yte = train_test_split(df, y, test_size=0.25, random_state=42, stratify=y)

with mlflow.start_run(run_name="claim_manual_review"):
    mlflow.sklearn.autolog()
    clf.fit(Xtr, ytr)
    auc = roc_auc_score(yte, clf.predict_proba(Xte)[:, 1])
    mlflow.log_metric("test_auc", auc)
    info = mlflow.sklearn.log_model(clf, "model", registered_model_name=MODEL_NAME)
    print(f"test AUC (reported honestly): {auc:.3f}")

# Set champion alias
from mlflow import MlflowClient
c = MlflowClient()
ver = c.get_registered_model(MODEL_NAME).latest_versions[0].version
c.set_registered_model_alias(MODEL_NAME, "champion", ver)

# Batch-score all claims into a prioritization table
df["manual_review_score"] = clf.predict_proba(df)[:, 1]
scored = spark.createDataFrame(
    pd.concat([spark.sql(f"SELECT claim_id FROM {CATALOG}.{SCHEMA}.claims").toPandas(),
               df["manual_review_score"].reset_index(drop=True)], axis=1))
scored.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.claim_review_priority")
print(f"wrote prioritization table {CATALOG}.{SCHEMA}.claim_review_priority")

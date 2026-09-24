"""
Train + register + score a manual-review-likelihood model.

Target: claims.requires_manual_review. Features: status, denial_reason, claim_type,
place_of_service, billed_amount, has_cob (from the JSON long tail). Trains with
MLflow, registers to Unity Catalog, and scores all claims into a reviewer-
prioritization table.

On synthetic data the label carries only a weak signal by design, so AUC will be
modest. Report it honestly. The value is the end-to-end MLOps pattern
(MLflow -> Unity Catalog -> Model Serving) and the prioritization score.

Runs as a serverless job. Deps: scikit-learn, mlflow, pandas.
"""

import os
import json
import mlflow
import pandas as pd
from pyspark.sql import SparkSession
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

df = spark.sql(f"""
    SELECT claim_id, status, denial_reason, claim_type, pos_desc, billed_amount,
           CAST(get_json_object(claim_detail, '$.adjudication.coordination_of_benefits') AS STRING) AS has_cob,
           requires_manual_review AS label
    FROM {CATALOG}.{SCHEMA}.claims
""").toPandas()

# Fill NaNs so the one-hot encoder is happy
df = df.fillna({"denial_reason": "none", "has_cob": "unknown", "claim_type": "unknown",
                "pos_desc": "unknown", "status": "unknown", "billed_amount": 0.0})

claim_ids = df["claim_id"]
y = df["label"].astype(int)
X = df.drop(columns=["claim_id", "label"])

cat = ["status", "denial_reason", "claim_type", "pos_desc", "has_cob"]
num = ["billed_amount"]
pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cat),
                         ("n", StandardScaler(), num)])
clf = Pipeline([("pre", pre), ("gb", GradientBoostingClassifier(random_state=42))])

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

# NOTE: UC model registration is skipped here because the shared metastore has hit
# its 5000 registered-model quota (QUOTA_EXCEEDED). We log the model to the MLflow run
# and write the prioritization table; registering + serving is a follow-up once quota
# frees up (or on a metastore under the cap). See docs/FOLLOWUP.md.
REGISTER = os.environ.get("REGISTER_UC", "false").lower() == "true"

with mlflow.start_run(run_name="claim_manual_review") as run:
    mlflow.sklearn.autolog(log_models=False)
    clf.fit(Xtr, ytr)
    auc = roc_auc_score(yte, clf.predict_proba(Xte)[:, 1])
    mlflow.log_metric("test_auc", auc)
    reg_name = MODEL_NAME if REGISTER else None
    info = mlflow.sklearn.log_model(clf, "model", registered_model_name=reg_name,
                                    input_example=Xtr.head(2),
                                    serialization_format="cloudpickle")
    run_id = run.info.run_id

ver = None
if REGISTER:
    from mlflow import MlflowClient
    ver = info.registered_model_version
    MlflowClient().set_registered_model_alias(MODEL_NAME, "champion", ver)

# Batch-score all claims into a prioritization table (score aligned to claim_id)
scores = clf.predict_proba(X)[:, 1]
scored = spark.createDataFrame(pd.DataFrame({"claim_id": claim_ids.values,
                                             "manual_review_score": scores}))
scored.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.claim_review_priority")

result = {"test_auc": round(float(auc), 4), "run_id": run_id, "registered": REGISTER,
          "scored_rows": scored.count()}
print(result)
try:
    dbutils.notebook.exit(json.dumps(result))  # noqa: F821
except Exception:
    pass

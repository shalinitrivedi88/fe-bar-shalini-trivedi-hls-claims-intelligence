"""
Lakeflow Spark Declarative Pipeline (formerly DLT) — silver curation.

Reads the generated bronze tables in the governed schema and builds the silver
layer the rest of the build reads: a claims_silver view with the JSON long tail
parsed out, and open_dispositions_without_action, which surfaces the exact
"event blindness after disposition" gap the customer described.

Runs serverless. Configure the pipeline target to
serverless_stable_kysnws_catalog.claims_intelligence. Validate the current
Lakeflow decorator surface with the databricks-pipelines skill before deploying.
"""

import dlt
from pyspark.sql import functions as F

CATALOG = "serverless_stable_kysnws_catalog"
SCHEMA = "claims_intelligence"
SRC = f"{CATALOG}.{SCHEMA}"


@dlt.table(comment="Claims with the JSON claim_detail long tail parsed into typed silver columns.")
def claims_silver():
    c = spark.read.table(f"{SRC}.claims")
    detail = F.from_json(
        F.col("claim_detail"),
        "struct<edi_source:string, clearinghouse_id:string, "
        "adjudication:struct<copay:double, coinsurance:double, "
        "deductible_applied:double, coordination_of_benefits:boolean, "
        "cob_payer:string, edits_triggered:array<string>>, "
        "line_items:array<struct<line:int, cpt:string, units:int, charge:double>>>",
    )
    return (
        c.withColumn("d", detail)
         .withColumn("line_count", F.size("d.line_items"))
         .withColumn("copay", F.col("d.adjudication.copay"))
         .withColumn("edits_triggered", F.col("d.adjudication.edits_triggered"))
         .withColumn("has_cob", F.col("d.adjudication.coordination_of_benefits"))
         .drop("d")
    )


@dlt.table(comment="Dispositions that never fired a downstream action — the event-blindness gap.")
def open_dispositions_without_action():
    ev = spark.read.table(f"{SRC}.disposition_events")
    return ev.filter(~F.col("downstream_action_fired"))

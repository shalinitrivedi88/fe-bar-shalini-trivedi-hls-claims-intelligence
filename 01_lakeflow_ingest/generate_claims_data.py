"""
Synthetic claims data generator for the Cascade Benefit Systems FE BAR build.

Generates a fabricated payer claims book shaped like X12 837/835 with a HYBRID
model: relational columns for the structured fields plus a JSON `claim_detail`
column for the long tail (line items, adjudication elements) that a single claim
carries by the thousands. Writes Delta tables into the one governed schema that
every downstream layer reads.

100% synthetic. Code systems used (CARC, CPT/HCPCS, ICD-10, place-of-service,
plan types) are real PUBLIC taxonomies. No real customer data or PHI.

Run on the serverless FEVM workspace (as a notebook or a serverless job).
Target defaults come from config.sh; override via environment variables.
"""

import os
import json
import random
from datetime import datetime, timedelta

from pyspark.sql import SparkSession

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CATALOG = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCHEMA = os.environ.get("SCHEMA", "claims_intelligence")
SEED = int(os.environ.get("SEED", "42"))

N_MEMBERS = int(os.environ.get("N_MEMBERS", "5000"))
N_PROVIDERS = int(os.environ.get("N_PROVIDERS", "500"))
N_CLAIMS = int(os.environ.get("N_CLAIMS", "50000"))
N_PRIOR_AUTHS = int(os.environ.get("N_PRIOR_AUTHS", "15000"))

random.seed(SEED)
spark = SparkSession.builder.getOrCreate()

# ---------------------------------------------------------------------------
# Public code taxonomies (real codes, illustrative subset)
# ---------------------------------------------------------------------------
PLAN_TYPES = ["HMO", "PPO", "EPO", "Medicare Advantage", "Medicaid"]
CLAIM_TYPES = ["837P Professional", "837I Institutional"]
PLACE_OF_SERVICE = {"11": "Office", "21": "Inpatient Hospital",
                    "22": "Outpatient Hospital", "23": "Emergency Room",
                    "02": "Telehealth"}
CPT = {
    "99213": "Office visit, established, low",
    "99214": "Office visit, established, moderate",
    "93000": "Electrocardiogram, complete",
    "80053": "Comprehensive metabolic panel",
    "71046": "Chest X-ray, 2 views",
    "36415": "Routine venipuncture",
    "97110": "Therapeutic exercise",
    "J1817": "Insulin injection",
}
ICD10 = {
    "E11.9": "Type 2 diabetes without complications",
    "I10": "Essential hypertension",
    "J45.909": "Unspecified asthma, uncomplicated",
    "M54.50": "Low back pain, unspecified",
    "N18.3": "Chronic kidney disease, stage 3",
    "E78.5": "Hyperlipidemia, unspecified",
    "Z00.00": "General adult medical exam",
}
# CARC = Claim Adjustment Reason Codes (real public denial taxonomy)
DENIAL_CARC = {
    "197": "Precertification / authorization absent",
    "50": "Not medically necessary",
    "96": "Non-covered charge",
    "16": "Claim lacks information",
    "18": "Duplicate claim / service",
    "45": "Charge exceeds fee schedule",
    "27": "Expenses after coverage terminated",
    "29": "Time limit for filing expired",
}
SPECIALTIES = ["Internal Medicine", "Cardiology", "Endocrinology",
               "Orthopedics", "Primary Care", "Radiology", "Nephrology"]
FIRST = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
         "Linda", "David", "Elizabeth", "Maria", "Daniel", "Karen", "Jose"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson"]


def rand_date(start_days_ago, end_days_ago=0):
    d = random.randint(end_days_ago, start_days_ago)
    return (datetime.today() - timedelta(days=d)).date().isoformat()


# ---------------------------------------------------------------------------
# members  (holds PHI-shaped columns for the governance layer to mask)
# ---------------------------------------------------------------------------
members = []
for i in range(1, N_MEMBERS + 1):
    members.append({
        "member_id": f"M{i:07d}",
        "subscriber_id": f"S{random.randint(1, N_MEMBERS):07d}",
        "member_name": f"{random.choice(FIRST)} {random.choice(LAST)}",
        "member_ssn": f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
        "member_dob": rand_date(30000, 6570),
        "plan_type": random.choice(PLAN_TYPES),
        "state": random.choice(["MI", "OH", "IN", "IL", "WI"]),
    })

# ---------------------------------------------------------------------------
# providers
# ---------------------------------------------------------------------------
providers = []
for i in range(1, N_PROVIDERS + 1):
    providers.append({
        "provider_id": f"P{i:06d}",
        "npi": f"{random.randint(1000000000, 1999999999)}",
        "provider_name": f"Dr. {random.choice(FIRST)} {random.choice(LAST)}",
        "specialty": random.choice(SPECIALTIES),
        "in_network": random.random() > 0.15,
    })

# ---------------------------------------------------------------------------
# claims  (relational columns + JSON claim_detail long tail)  + disposition_events
# ---------------------------------------------------------------------------
STATUS_WEIGHTS = [("Paid", 0.63), ("Denied", 0.13), ("Pending", 0.16),
                  ("Partially Paid", 0.08)]


def weighted_status():
    r = random.random()
    c = 0.0
    for s, w in STATUS_WEIGHTS:
        c += w
        if r <= c:
            return s
    return "Paid"


claims, disposition_events = [], []
for i in range(1, N_CLAIMS + 1):
    claim_id = f"C{i:09d}"
    member_id = f"M{random.randint(1, N_MEMBERS):07d}"
    provider_id = f"P{random.randint(1, N_PROVIDERS):06d}"
    status = weighted_status()
    n_lines = random.randint(1, 6)
    billed = round(sum(random.uniform(40, 900) for _ in range(n_lines)), 2)

    if status == "Paid":
        allowed = round(billed * random.uniform(0.55, 0.9), 2); paid = allowed; denial = None
    elif status == "Partially Paid":
        allowed = round(billed * random.uniform(0.3, 0.6), 2); paid = round(allowed * 0.7, 2); denial = random.choice(list(DENIAL_CARC))
    elif status == "Denied":
        allowed = 0.0; paid = 0.0; denial = random.choice(list(DENIAL_CARC))
    else:  # Pending
        allowed = 0.0; paid = 0.0; denial = None

    primary_cpt = random.choice(list(CPT))
    primary_dx = random.choice(list(ICD10))
    pos = random.choice(list(PLACE_OF_SERVICE))

    # JSON long tail: line items + nested adjudication elements (the "thousands of elements" analog)
    lines = []
    for ln in range(1, n_lines + 1):
        cpt = random.choice(list(CPT))
        lines.append({
            "line": ln, "cpt": cpt, "cpt_desc": CPT[cpt],
            "units": random.randint(1, 3),
            "charge": round(random.uniform(40, 900), 2),
            "modifiers": random.sample(["25", "59", "LT", "RT", "GT"], k=random.randint(0, 2)),
            "dx_pointers": random.sample(list(ICD10), k=random.randint(1, 2)),
            "rev_code": random.choice(["0450", "0300", "0510", "0710"]),
        })
    claim_detail = {
        "edi_source": "837",
        "clearinghouse_id": f"CH{random.randint(100,999)}",
        "line_items": lines,
        "adjudication": {
            "coordination_of_benefits": random.random() > 0.85,
            "cob_payer": random.choice(["None", "Medicare", "Commercial"]),
            "copay": round(random.uniform(0, 50), 2),
            "coinsurance": round(random.uniform(0, 0.3), 2),
            "deductible_applied": round(random.uniform(0, 200), 2),
            "edits_triggered": random.sample(
                ["NCCI-PTP", "MUE", "age-gender", "frequency"], k=random.randint(0, 2)),
        },
    }

    received = rand_date(400, 5)
    claims.append({
        "claim_id": claim_id, "member_id": member_id, "provider_id": provider_id,
        "claim_type": random.choice(CLAIM_TYPES), "status": status,
        "billed_amount": billed, "allowed_amount": allowed, "paid_amount": paid,
        "denial_carc": denial,
        "denial_reason": DENIAL_CARC[denial] if denial else None,
        "place_of_service": pos, "pos_desc": PLACE_OF_SERVICE[pos],
        "primary_cpt": primary_cpt, "primary_dx": primary_dx,
        "service_date": rand_date(430, 30), "received_date": received,
        # ML target: needed a manual review (weak signal, honest AUC by design)
        "requires_manual_review": int(
            (status in ("Denied", "Partially Paid")) and (random.random() < 0.45)
            or (billed > 3000 and random.random() < 0.3)),
        "claim_detail": json.dumps(claim_detail),
    })

    # disposition event (the event that should fire a downstream action)
    if status in ("Denied", "Partially Paid", "Paid"):
        fired = random.random() < 0.60  # ~40% show the event-blindness gap
        disposition_events.append({
            "event_id": f"E{i:09d}", "claim_id": claim_id,
            "disposition": status,
            "disposition_ts": received + "T" + f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00",
            "downstream_action_fired": fired,
            "action_type": (random.choice(["member_notice", "appeal_route", "payment_integrity_review"])
                            if fired else None),
        })

# ---------------------------------------------------------------------------
# prior_authorizations & eligibility
# ---------------------------------------------------------------------------
prior_auths = []
for i in range(1, N_PRIOR_AUTHS + 1):
    prior_auths.append({
        "pa_id": f"PA{i:08d}",
        "member_id": f"M{random.randint(1, N_MEMBERS):07d}",
        "provider_id": f"P{random.randint(1, N_PROVIDERS):06d}",
        "cpt": random.choice(list(CPT)),
        "status": random.choice(["Approved", "Denied", "Pending"]),
        "requested_date": rand_date(430, 30),
    })

eligibility = []
for m in random.sample(members, k=min(len(members), int(N_MEMBERS * 1.2)) if False else len(members)):
    eligibility.append({
        "member_id": m["member_id"], "plan_type": m["plan_type"],
        "effective_date": rand_date(730, 365),
        "term_date": None if random.random() > 0.1 else rand_date(300, 5),
        "active": random.random() > 0.1,
    })

# ---------------------------------------------------------------------------
# Write Delta tables into the governed schema
# ---------------------------------------------------------------------------
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

def write(name, rows):
    if not rows:
        print(f"  skip {name} (0 rows)"); return
    df = spark.createDataFrame(rows)
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.{name}")
    print(f"  wrote {CATALOG}.{SCHEMA}.{name}: {df.count():,} rows")

print(f"Writing synthetic claims book to {CATALOG}.{SCHEMA} (seed={SEED})")
write("members", members)
write("providers", providers)
write("claims", claims)
write("disposition_events", disposition_events)
write("prior_authorizations", prior_auths)
write("eligibility", eligibility)
print("Done. Next: 02_unity_catalog_governance to declare keys, metric views, and PHI masks.")

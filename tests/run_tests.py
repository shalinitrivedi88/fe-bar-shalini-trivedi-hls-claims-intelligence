"""
Functional test suite for the Cascade claims FE BAR build (runs against fevm).

Covers every layer plus the integration seams:
  data integrity, Unity Catalog governance (constraints + PHI masks),
  certified views, ML prioritization, Lakebase ODS, the Gen AI triage agent,
  the Databricks App API, Genie NL->SQL, and cross-layer consistency.

Usage:  python tests/run_tests.py
Exit code is non-zero if any test fails.
Requires: databricks CLI (profile fevm), psql on PATH (brew install libpq), curl.
"""
import subprocess, json, os, sys, re, time

PROFILE = os.environ.get("DATABRICKS_PROFILE", "fevm")
CAT = os.environ.get("CATALOG", "serverless_stable_kysnws_catalog")
SCH = os.environ.get("SCHEMA", "claims_intelligence")
FQ = f"{CAT}.{SCH}"
APP_URL = "https://claims-ops-console-7474644911133058.aws.databricksapps.com"
AGENT_ENDPOINT = "databricks-gpt-5-6-sol"
GENIE_SPACE = "01f1b7a7a3511f52a02ca9d65a9d353f"
os.environ["PATH"] = "/opt/homebrew/opt/libpq/bin:" + os.environ["PATH"]

results = []
def rec(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

def sqlv(q):
    """Run SQL, return the first column of the first row (aliased 'v')."""
    out = subprocess.check_output(
        ["databricks", "experimental", "aitools", "tools", "query", q, "--profile", PROFILE],
        stderr=subprocess.STDOUT)
    rows = json.loads(out)
    return rows[0][list(rows[0].keys())[0]] if rows else None

def psql(q):
    out = subprocess.check_output(
        ["databricks", "psql", "--project", "cascade-claims-ods", "--profile", PROFILE,
         "--", "-t", "-A", "-c", q], stderr=subprocess.STDOUT)
    return out.decode().strip().splitlines()

def token():
    out = subprocess.check_output(["databricks", "auth", "token", "-p", PROFILE])
    return json.loads(out)["access_token"]

def check_zero(name, q):
    try: v = int(sqlv(q)); rec(name, v == 0, f"violations={v}")
    except Exception as e: rec(name, False, f"error {str(e)[:80]}")

def check_eq(name, q, expected):
    try: v = int(float(sqlv(q))); rec(name, v == expected, f"got {v}, want {expected}")
    except Exception as e: rec(name, False, f"error {str(e)[:80]}")

# ---------------- DATA INTEGRITY ----------------
print("\n== Data integrity ==")
check_eq("D1 claims row count", f"SELECT COUNT(*) v FROM {FQ}.claims", 50000)
check_eq("D2 claim_id unique", f"SELECT COUNT(*)-COUNT(DISTINCT claim_id) v FROM {FQ}.claims", 0)
check_eq("D3 members row count", f"SELECT COUNT(*) v FROM {FQ}.members", 5000)
check_zero("D4 no orphan claims.member_id", f"SELECT COUNT(*) v FROM {FQ}.claims c LEFT JOIN {FQ}.members m ON c.member_id=m.member_id WHERE m.member_id IS NULL")
check_zero("D5 no orphan claims.provider_id", f"SELECT COUNT(*) v FROM {FQ}.claims c LEFT JOIN {FQ}.providers p ON c.provider_id=p.provider_id WHERE p.provider_id IS NULL")
check_zero("D6 no orphan disposition.claim_id", f"SELECT COUNT(*) v FROM {FQ}.disposition_events d LEFT JOIN {FQ}.claims c ON d.claim_id=c.claim_id WHERE c.claim_id IS NULL")
check_zero("D7 claim_detail all valid JSON", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE get_json_object(claim_detail,'$.edi_source') IS NULL")
check_zero("D8 paid<=billed", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE paid_amount > billed_amount")
check_zero("D9 Denied => paid=0", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE status='Denied' AND paid_amount<>0")
check_zero("D10 Denied => denial_reason set", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE status='Denied' AND denial_reason IS NULL")
check_zero("D11 requires_manual_review in (0,1)", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE requires_manual_review NOT IN (0,1)")
check_zero("D12 status in allowed set", f"SELECT COUNT(*) v FROM {FQ}.claims WHERE status NOT IN ('Paid','Denied','Pending','Partially Paid')")

# ---------------- GOVERNANCE ----------------
print("\n== Unity Catalog governance ==")
check_eq("G1 5 PK + 5 FK constraints", f"SELECT COUNT(*) v FROM {CAT}.information_schema.table_constraints WHERE table_schema='{SCH}'", 10)
check_zero("G2 SSN masked (all rows)", f"SELECT COUNT(*) v FROM {FQ}.members WHERE member_ssn NOT LIKE 'XXX-XX-%'")
check_zero("G3 name masked (all rows)", f"SELECT COUNT(*) v FROM {FQ}.members WHERE member_name NOT LIKE '%*** ***'")
check_zero("G4 dob masked (all rows)", f"SELECT COUNT(*) v FROM {FQ}.members WHERE member_dob NOT LIKE '____-XX-XX'")

# ---------------- CERTIFIED VIEWS ----------------
print("\n== Certified views ==")
try:
    a = int(float(sqlv(f"SELECT ROUND(SUM(billed_amount)) v FROM {FQ}.claims")))
    b = int(float(sqlv(f"SELECT SUM(total_billed) v FROM {FQ}.claims_dollar_exposure")))
    # tolerance: the view rounds per-status then we sum, vs rounding the grand total,
    # so up to (#statuses) dollars of rounding drift is expected and correct.
    rec("V1 dollar_exposure reconciles to claims", abs(a - b) <= 4, f"claims={a}, view={b}, drift={abs(a-b)}")
except Exception as e: rec("V1 dollar_exposure reconciles", False, str(e)[:80])
check_zero("V2 action_fired_rate in [0,1]", f"SELECT COUNT(*) v FROM {FQ}.disposition_action_gap WHERE action_fired_rate<0 OR action_fired_rate>1")
check_zero("V3 denial_reason_dollars non-null reasons", f"SELECT COUNT(*) v FROM {FQ}.denial_reason_dollars WHERE denial_reason IS NULL")

# ---------------- ML PRIORITIZATION ----------------
print("\n== ML prioritization ==")
check_eq("M1 priority table row count", f"SELECT COUNT(*) v FROM {FQ}.claim_review_priority", 50000)
check_zero("M2 scores in [0,1]", f"SELECT COUNT(*) v FROM {FQ}.claim_review_priority WHERE manual_review_score<0 OR manual_review_score>1")
check_zero("M3 no orphan priority claim_ids", f"SELECT COUNT(*) v FROM {FQ}.claim_review_priority p LEFT JOIN {FQ}.claims c ON p.claim_id=c.claim_id WHERE c.claim_id IS NULL")
try:
    dn = float(sqlv(f"SELECT AVG(p.manual_review_score) v FROM {FQ}.claim_review_priority p JOIN {FQ}.claims c ON p.claim_id=c.claim_id WHERE c.status='Denied'"))
    pd_ = float(sqlv(f"SELECT AVG(p.manual_review_score) v FROM {FQ}.claim_review_priority p JOIN {FQ}.claims c ON p.claim_id=c.claim_id WHERE c.status='Paid'"))
    rec("M4 Denied scores higher than Paid", dn > pd_, f"denied={dn:.3f} paid={pd_:.3f}")
except Exception as e: rec("M4 Denied>Paid", False, str(e)[:80])

# ---------------- LAKEBASE ----------------
print("\n== Lakebase ODS ==")
try: rec("L1 claim_status row count == 500", psql("SELECT COUNT(*) FROM claims_ods.claim_status")[-1].strip() == "500", psql("SELECT COUNT(*) FROM claims_ods.claim_status")[-1])
except Exception as e: rec("L1 claim_status count", False, str(e)[:80])
try:
    r = psql("SELECT COUNT(*) FROM claims_ods.claim_status WHERE jsonb_array_length(claim_detail->'line_items')>0")[-1].strip()
    rec("L2 hybrid JSON query works", int(r) > 0, f"rows_with_lines={r}")
except Exception as e: rec("L2 hybrid JSON query", False, str(e)[:80])
try:
    r = psql("SELECT COUNT(*) FROM claims_ods.claim_status WHERE claim_detail @> '{\"adjudication\":{\"coordination_of_benefits\":true}}'")[-1].strip()
    rec("L3 JSON containment (GIN) query", int(r) >= 0, f"cob_claims={r}")
except Exception as e: rec("L3 JSON containment", False, str(e)[:80])

# ---------------- GEN AI TRIAGE AGENT ----------------
print("\n== Gen AI triage agent ==")
ALLOWED = {"member_notice", "appeal_route", "payment_integrity_review", "none"}
def triage(user):
    payload = {"messages": [
        {"role": "system", "content": "You are a claims triage assistant. Return STRICT JSON only with keys triage_score (0.0-1.0), risk_tier (high|medium|low), next_action (member_notice|appeal_route|payment_integrity_review|none), rationale. No prose."},
        {"role": "user", "content": user}]}
    with open("/tmp/_triage.json", "w") as f: json.dump(payload, f)
    out = subprocess.check_output(["databricks", "serving-endpoints", "query", AGENT_ENDPOINT,
                                   "--json", "@/tmp/_triage.json", "--profile", PROFILE], stderr=subprocess.STDOUT)
    c = json.loads(out)["choices"][0]["message"]["content"].strip()
    if c.startswith("```"): c = c.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(c)
def agent_case(name, user):
    try:
        o = triage(user)
        ok = (set(["triage_score", "risk_tier", "next_action", "rationale"]).issubset(o) and
              o["next_action"] in ALLOWED and 0.0 <= float(o["triage_score"]) <= 1.0)
        rec(name, ok, f"action={o.get('next_action')} score={o.get('triage_score')}")
    except Exception as e: rec(name, False, str(e)[:90])
agent_case("A1 denied high-dollar claim", "status=Denied, denial_reason=Precertification / authorization absent, billed_amount=4200, edits_triggered=[NCCI-PTP]")
agent_case("A2 clean paid claim", "status=Paid, denial_reason=none, billed_amount=120, edits_triggered=[]")
agent_case("A3 minimal/sparse claim (edge)", "status=Pending")

# ---------------- APP API ----------------
print("\n== Databricks App API ==")
try:
    tok = token()
    import urllib.request
    def get(path, auth=True):
        req = urllib.request.Request(APP_URL + path)
        if auth: req.add_header("Authorization", "Bearer " + tok)
        try:
            with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode()
        except urllib.error.HTTPError as e: return e.code, e.read().decode()
    s, body = get("/api/disposition-gap")
    d = json.loads(body) if s == 200 else []
    rec("P1 /api/disposition-gap 200 + 3 rows", s == 200 and len(d) == 3, f"status={s} rows={len(d)}")
    s2, body2 = get("/api/triage-queue")
    d2 = json.loads(body2) if s2 == 200 else []
    rec("P2 /api/triage-queue 200 + rows", s2 == 200 and len(d2) > 0, f"status={s2} rows={len(d2)}")
    s3, _ = get("/api/disposition-gap", auth=False)
    rec("P3 unauthorized rejected", s3 in (401, 403), f"status={s3}")
except Exception as e: rec("P* app API", False, str(e)[:90])

# ---------------- GENIE ----------------
print("\n== Genie NL->SQL ==")
try:
    out = subprocess.check_output(["databricks", "genie", "start-conversation", GENIE_SPACE,
                                   "How many claims were denied?", "--profile", PROFILE], stderr=subprocess.STDOUT)
    j = json.loads(out); cid, mid = j["conversation_id"], j["message_id"]
    st = None
    for _ in range(18):
        m = json.loads(subprocess.check_output(["databricks", "genie", "get-message", GENIE_SPACE, cid, mid, "--profile", PROFILE]))
        st = m.get("status")
        if st in ("COMPLETED", "FAILED"): break
        time.sleep(10)
    sql_used = ""
    if st == "COMPLETED":
        for a in m.get("attachments", []):
            if a.get("query", {}).get("query"): sql_used = a["query"]["query"]
    rec("GE1 Genie returns SQL over the schema", st == "COMPLETED" and SCH in sql_used, f"status={st}")
except Exception as e: rec("GE1 Genie NL->SQL", False, str(e)[:90])

# ---------------- INTEGRATION ----------------
print("\n== Integration (one governed schema) ==")
try:
    # App disposition-gap must match the certified SQL view
    tok = token() if 'tok' not in dir() else tok
    import urllib.request
    req = urllib.request.Request(APP_URL + "/api/disposition-gap"); req.add_header("Authorization", "Bearer " + tok)
    app_gap = {r["disposition"]: round(float(r["action_fired_rate"]), 3) for r in json.loads(urllib.request.urlopen(req, timeout=30).read())}
    sql_denied = round(float(sqlv(f"SELECT action_fired_rate v FROM {FQ}.disposition_action_gap WHERE disposition='Denied'")), 3)
    rec("I1 app gap == certified view (Denied)", app_gap.get("Denied") == sql_denied, f"app={app_gap.get('Denied')} sql={sql_denied}")
except Exception as e: rec("I1 app==view", False, str(e)[:90])
try:
    cid = psql("SELECT claim_id FROM claims_ods.claim_status LIMIT 1")[-1].strip()
    lb_status = psql(f"SELECT status FROM claims_ods.claim_status WHERE claim_id='{cid}'")[-1].strip()
    dl_status = sqlv(f"SELECT status v FROM {FQ}.claims WHERE claim_id='{cid}'")
    rec("I2 Lakebase status == Delta status", lb_status == dl_status, f"{cid}: lb={lb_status} delta={dl_status}")
except Exception as e: rec("I2 Lakebase==Delta", False, str(e)[:90])

# ---------------- SUMMARY ----------------
p = sum(1 for _, ok, _ in results if ok); f = len(results) - p
print(f"\n===== {p}/{len(results)} passed, {f} failed =====")
sys.exit(1 if f else 0)

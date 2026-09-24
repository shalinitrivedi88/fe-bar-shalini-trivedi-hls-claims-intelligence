from fastapi import APIRouter
from .. import db, config

router = APIRouter()


@router.get("/api/summary")
def summary():
    rows = db.warehouse_query(f"""
        SELECT
          ROUND(SUM(billed_amount)) AS total_billed,
          ROUND(SUM(CASE WHEN status IN ('Denied','Pending') THEN billed_amount ELSE 0 END)) AS rework_pool,
          SUM(CASE WHEN requires_manual_review=1 THEN 1 ELSE 0 END) AS flagged_for_review,
          COUNT(*) AS claims
        FROM {config.FQ}.claims
    """)
    gap = db.warehouse_query(f"""
        SELECT ROUND(AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0 END),3) AS action_fired_rate
        FROM {config.FQ}.disposition_events
    """)
    out = rows[0]
    out["action_fired_rate"] = gap[0]["action_fired_rate"]
    return out

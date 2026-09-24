from fastapi import APIRouter
from .. import db, config

router = APIRouter()


@router.get("/api/triage-queue")
def triage_queue(limit: int = 25):
    # Highest manual-review score first (the ML prioritization), joined to claim facts
    return db.warehouse_query(f"""
        SELECT p.claim_id, ROUND(p.manual_review_score,3) AS score,
               c.status, c.denial_reason, c.billed_amount, c.primary_cpt
        FROM {config.FQ}.claim_review_priority p
        JOIN {config.FQ}.claims c ON p.claim_id = c.claim_id
        WHERE c.status IN ('Denied','Partially Paid','Pending')
        ORDER BY p.manual_review_score DESC
        LIMIT {int(limit)}
    """)


@router.get("/api/disposition-gap")
def disposition_gap():
    return db.warehouse_query(f"""
        SELECT disposition, COUNT(*) AS dispositions,
               ROUND(AVG(CASE WHEN downstream_action_fired THEN 1.0 ELSE 0 END),3) AS action_fired_rate
        FROM {config.FQ}.disposition_events
        GROUP BY disposition ORDER BY dispositions DESC
    """)

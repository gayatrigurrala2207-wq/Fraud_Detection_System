"""FR-06: overview metrics with explicit definitions and denominators."""

import numpy as np
from fastapi import APIRouter

from app.services import Db, Model

router = APIRouter(tags=["overview"])
MIN_REVIEWED = 20

DEFINITIONS = {
    "processed": "Replayed transactions scored by the model so far.",
    "flagged": "Processed transactions with score at or above the model threshold. Each opens a case.",
    "high_risk": "Processed transactions with score at or above the high-risk cutoff.",
    "potential_fraud_value": "Sum of amounts of flagged transactions (predicted, not confirmed).",
    "alert_precision": "Cases labeled fraud divided by cases reviewed. Shown once at least "
                       f"{MIN_REVIEWED} cases are reviewed.",
    "review_coverage": "Reviewed cases divided by all cases.",
    "latency": "Time to build features and score one transaction in the replay consumer.",
}


@router.get("/overview")
def overview(db: Db, model: Model) -> dict:
    totals = db.execute(
        """SELECT COUNT(*) AS processed, COALESCE(SUM(amount), 0) AS processed_value,
                  COALESCE(SUM(status = 'flagged'), 0) AS flagged,
                  COALESCE(SUM(CASE WHEN status = 'flagged' THEN amount END), 0) AS flagged_value,
                  COALESCE(SUM(risk_level = 'high'), 0) AS high_risk,
                  MIN(event_time) AS first_event, MAX(event_time) AS last_event
           FROM transactions WHERE processed_at IS NOT NULL AND source = 'replay'"""
    ).fetchone()
    queued = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE processed_at IS NULL AND source = 'replay'").fetchone()[0]
    simulated = db.execute("SELECT COUNT(*) FROM transactions WHERE source = 'simulated'").fetchone()[0]
    risk = {row[0]: row[1] for row in db.execute(
        "SELECT risk_level, COUNT(*) FROM transactions WHERE processed_at IS NOT NULL AND source = 'replay' "
        "GROUP BY risk_level")}
    cases = {row[0] or "unreviewed": row[1] for row in db.execute(
        "SELECT disposition, COUNT(*) FROM cases GROUP BY disposition")}
    latencies = np.array([row[0] for row in db.execute(
        "SELECT latency_ms FROM transactions WHERE processed_at IS NOT NULL AND latency_ms IS NOT NULL "
        "ORDER BY processed_at DESC LIMIT 5000")], dtype=float)
    timeline = [dict(row) for row in db.execute(
        """SELECT substr(event_time, 1, 13) || ':00' AS hour, COUNT(*) AS processed,
                  SUM(status = 'flagged') AS flagged
           FROM transactions WHERE processed_at IS NOT NULL AND source = 'replay'
           GROUP BY 1 ORDER BY 1 DESC LIMIT 48""")][::-1]
    recent_alerts = [dict(row) for row in db.execute(
        """SELECT t.id, t.event_time, t.merchant, t.category, t.amount, t.score, t.risk_level, c.id AS case_id
           FROM transactions t JOIN cases c ON c.transaction_id = t.id
           ORDER BY t.processed_at DESC, t.id DESC LIMIT 8""")]

    fraud, legitimate = cases.get("fraud", 0), cases.get("legitimate", 0)
    reviewed = fraud + legitimate
    total_cases = reviewed + cases.get("unreviewed", 0)
    return {
        "model_version": model.version if model else None,
        "threshold": model.threshold if model else None,
        "processed": {"count": totals["processed"], "value": round(totals["processed_value"], 2),
                      "queued": queued, "simulated": simulated,
                      "event_window": {"start": totals["first_event"], "end": totals["last_event"]}},
        "flagged": {"count": totals["flagged"], "value": round(totals["flagged_value"], 2),
                    "rate": totals["flagged"] / totals["processed"] if totals["processed"] else None},
        "high_risk": {"count": totals["high_risk"]},
        "risk_distribution": {level: risk.get(level, 0) for level in ("low", "medium", "elevated", "high")},
        "potential_fraud_value": round(totals["flagged_value"], 2),
        "outcomes": {
            "predicted": {"flagged": totals["flagged"], "cleared": totals["processed"] - totals["flagged"]},
            "confirmed": {"fraud": fraud, "legitimate": legitimate, "unreviewed": cases.get("unreviewed", 0)},
            "review_coverage": reviewed / total_cases if total_cases else None,
            "alert_precision": fraud / reviewed if reviewed >= MIN_REVIEWED else None,
            "min_reviewed_for_precision": MIN_REVIEWED,
        },
        "latency": {
            "mean_ms": round(float(latencies.mean()), 3) if latencies.size else None,
            "p95_ms": round(float(np.percentile(latencies, 95)), 3) if latencies.size else None,
            "samples": int(latencies.size),
        },
        "timeline": timeline,
        "recent_alerts": recent_alerts,
        "definitions": DEFINITIONS,
    }

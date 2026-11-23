"""FR-09 analytics, FR-10 model reporting, and FR-10 monitoring (drift and experiments)."""

import numpy as np
from fastapi import APIRouter, HTTPException

from app.services import NOT_BUILT, Config, Db, Model, read_json
from ml.evaluation.drift import DRIFT_FEATURES, psi, psi_status

router = APIRouter(tags=["insights"])
MIN_DRIFT_ROWS = 200


@router.get("/analytics")
def analytics(config: Config, db: Db) -> dict:
    report = read_json(config.reports_dir / "analytics.json")
    if report is None:
        raise HTTPException(status_code=404, detail=NOT_BUILT)
    scores = np.array([r[0] for r in db.execute(
        "SELECT score FROM transactions WHERE processed_at IS NOT NULL AND source = 'replay'")], dtype=float)
    counts, edges = np.histogram(scores, bins=20, range=(0, 1))
    window = db.execute("SELECT MIN(event_time), MAX(event_time) FROM transactions "
                        "WHERE processed_at IS NOT NULL AND source = 'replay'").fetchone()
    return {
        **report,
        "score_distribution": {
            "population": "Replayed held-out transactions scored so far",
            "time_window": {"start": window[0], "end": window[1]},
            "outcome_source": "Model scores",
            "bins": [{"bucket": f"{edges[i]:.2f}-{edges[i + 1]:.2f}", "transactions": int(c)}
                     for i, c in enumerate(counts)],
            "total": int(scores.size),
        },
    }


@router.get("/models")
def models(config: Config, model: Model) -> dict:
    report = read_json(config.reports_dir / "model_report.json")
    if report is None:
        raise HTTPException(status_code=404, detail=NOT_BUILT)
    return {**report, "active_version": model.version if model else None}


@router.get("/monitoring")
def monitoring(config: Config, db: Db) -> dict:
    reference = read_json(config.models_dir / "drift_reference.json")
    runs = read_json(config.reports_dir / "runs.json") or []
    rows = db.execute(
        f"""SELECT {', '.join(['amount AS amt'] + [f for f in DRIFT_FEATURES if f != 'amt'])}, score
            FROM transactions WHERE processed_at IS NOT NULL AND source = 'replay'
            ORDER BY processed_at DESC LIMIT 5000""").fetchall()
    drift = None
    if reference and len(rows) >= MIN_DRIFT_ROWS:
        def column(name):
            return np.array([np.nan if r[name] is None else r[name] for r in rows], dtype=float)
        items = [{"feature": f, "label": label, "psi": round(psi(reference["features"][f], column(f)), 4)}
                 for f, label in DRIFT_FEATURES.items()]
        items.append({"feature": "score", "label": "Model score",
                      "psi": round(psi(reference["score"], column("score")), 4)})
        for item in items:
            item["status"] = psi_status(item["psi"])
        drift = {"reference_window": reference["window"],
                 "current_window": f"Latest {len(rows):,} replayed transactions", "items": items}
    reviewed = {r[0]: r[1] for r in db.execute(
        "SELECT disposition, COUNT(*) FROM cases WHERE disposition IS NOT NULL GROUP BY disposition")}
    total_reviewed = sum(reviewed.values())
    return {
        "drift": drift,
        "drift_rows": len(rows),
        "min_drift_rows": MIN_DRIFT_ROWS,
        "drift_method": "Population stability index over reference deciles. < 0.1 stable, 0.1-0.25 moderate, "
                        "> 0.25 significant.",
        "confirmed_performance": {
            "reviewed": total_reviewed,
            "fraud": reviewed.get("fraud", 0),
            "legitimate": reviewed.get("legitimate", 0),
            "alert_precision": reviewed.get("fraud", 0) / total_reviewed if total_reviewed else None,
            "note": "From analyst-labeled cases only; independent of drift signals.",
        },
        "experiments": list(reversed(runs)),
    }

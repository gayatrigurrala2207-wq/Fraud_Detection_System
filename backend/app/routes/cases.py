"""FR-08: case workspace with evidence, explanations, history, labels, notes, and audit trail."""

from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import audit, now, raw_features
from app.services import Actor, Config, Db, Model, read_json

router = APIRouter(tags=["cases"])


class LabelRequest(BaseModel):
    disposition: Literal["fraud", "legitimate"]


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


@router.get("/cases")
def list_cases(
    db: Db,
    status: Annotated[Literal["open", "resolved"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> dict:
    where = "WHERE c.status = ?" if status else ""
    rows = db.execute(
        f"""SELECT c.id, c.status, c.disposition, c.created_at, c.updated_at, t.id AS transaction_id,
                   t.event_time, t.merchant, t.category, t.amount, t.score, t.risk_level, t.source,
                   (SELECT COUNT(*) FROM case_notes n WHERE n.case_id = c.id) AS notes
            FROM cases c JOIN transactions t ON t.id = c.transaction_id {where}
            ORDER BY c.status = 'resolved', t.score DESC, c.id DESC LIMIT ?""",
        (*([status] if status else []), limit),
    ).fetchall()
    counts = {row[0]: row[1] for row in db.execute("SELECT status, COUNT(*) FROM cases GROUP BY status")}
    return {"items": [dict(row) for row in rows], "counts": {"open": counts.get("open", 0),
                                                           "resolved": counts.get("resolved", 0)}}


def _percentile_rank(reference: dict | None, feature: str, value: float | None) -> float | None:
    if reference is None or value is None or feature not in reference["features"]:
        return None
    edges = reference["features"][feature]["edges"]
    proportions = reference["features"][feature]["proportions"]
    below = sum(p for edge, p in zip(edges, proportions) if value >= edge)
    return round(below, 3)


def _anomalies(tx: dict, reference: dict | None) -> list[dict]:
    ratio = tx["amount"] / tx["card_mean_amt"] if tx["card_mean_amt"] else None
    checks = [
        ("Amount vs this card's average", ratio, f"{ratio:.1f}x average" if ratio else "No prior history",
         ratio is not None and ratio >= 3),
        ("Card transactions in previous 24h", tx["count_24h"], f"{tx['count_24h']:.0f} transactions", None),
        ("Time since previous card transaction", tx["secs_since_last"],
         f"{tx['secs_since_last'] / 3600:.1f} hours" if tx["secs_since_last"] is not None else "First transaction",
         None),
        ("Customer-merchant distance", tx["distance_km"], f"{tx['distance_km']:.0f} km", None),
        ("Hour of day", tx["hour"], f"{tx['hour']:02d}:00", tx["hour"] >= 22 or tx["hour"] < 6),
    ]
    features = ["amt", "count_24h", "secs_since_last", "distance_km", "hour"]
    items = []
    for (label, value, shown, flagged), feature in zip(checks, features):
        rank = _percentile_rank(reference, feature, tx["amount"] if feature == "amt" else value)
        if flagged is None:
            flagged = rank is not None and (rank <= 0.1 if feature == "secs_since_last" else rank >= 0.9)
        items.append({"label": label, "display": shown, "percentile_in_reference": rank, "unusual": bool(flagged)})
    return items


def _case(db, case_id: int) -> dict:
    row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return dict(row)


@router.get("/cases/{case_id}")
def case_detail(case_id: int, db: Db, model: Model, config: Config) -> dict:
    case = _case(db, case_id)
    tx = dict(db.execute("SELECT * FROM transactions WHERE id = ?", (case["transaction_id"],)).fetchone())
    explanation = model.explain(pd.DataFrame([raw_features(tx)])) if model else None
    reference = read_json(config.models_dir / "drift_reference.json")
    history = []
    if tx["card_key"]:
        history = [dict(row) for row in db.execute(
            """SELECT t.id, t.event_time, t.merchant, t.category, t.amount, t.score, t.risk_level,
                      CASE WHEN c.disposition IS NOT NULL THEN c.disposition ELSE t.status END AS status
               FROM transactions t LEFT JOIN cases c ON c.transaction_id = t.id
               WHERE t.card_key = ? AND t.event_time < ? ORDER BY t.event_time DESC LIMIT 15""",
            (tx["card_key"], tx["event_time"]))]
    transaction = {k: tx[k] for k in ("id", "trans_num", "event_time", "processed_at", "merchant", "category",
                                      "amount", "state", "card_key", "source", "score", "risk_level", "threshold",
                                      "model_version", "latency_ms")}
    return {
        "case": case,
        "transaction": transaction,
        "explanation": explanation,
        "anomalies": _anomalies(tx, reference),
        "anomaly_reference": reference["window"] if reference else None,
        "history": history,
        "notes": [dict(r) for r in db.execute("SELECT * FROM case_notes WHERE case_id = ? ORDER BY id", (case_id,))],
        "audit": [dict(r) for r in db.execute("SELECT * FROM audit_events WHERE case_id = ? ORDER BY id", (case_id,))],
    }


@router.post("/cases/{case_id}/label")
def label_case(case_id: int, request: LabelRequest, db: Db, actor: Actor) -> dict:
    case = _case(db, case_id)
    db.execute("UPDATE cases SET disposition = ?, updated_at = ? WHERE id = ?", (request.disposition, now(), case_id))
    previous = case["disposition"] or "unlabeled"
    audit(db, case_id, actor, "labeled", f"{previous} -> {request.disposition}")
    db.commit()
    return _case(db, case_id)


@router.post("/cases/{case_id}/notes")
def add_note(case_id: int, request: NoteRequest, db: Db, actor: Actor) -> dict:
    _case(db, case_id)
    db.execute("INSERT INTO case_notes (case_id, author, body, created_at) VALUES (?, ?, ?, ?)",
               (case_id, actor, request.body.strip(), now()))
    audit(db, case_id, actor, "note_added")
    db.commit()
    return {"ok": True}


@router.post("/cases/{case_id}/resolve")
def resolve_case(case_id: int, db: Db, actor: Actor) -> dict:
    case = _case(db, case_id)
    if case["disposition"] is None:
        raise HTTPException(status_code=400, detail="Label the case as fraud or legitimate before resolving it.")
    if case["status"] == "resolved":
        raise HTTPException(status_code=400, detail="Case is already resolved.")
    db.execute("UPDATE cases SET status = 'resolved', updated_at = ? WHERE id = ?", (now(), case_id))
    audit(db, case_id, actor, "resolved", f"Disposition: {case['disposition']}")
    db.commit()
    return _case(db, case_id)


@router.post("/cases/{case_id}/reopen")
def reopen_case(case_id: int, db: Db, actor: Actor) -> dict:
    case = _case(db, case_id)
    if case["status"] != "resolved":
        raise HTTPException(status_code=400, detail="Case is not resolved.")
    db.execute("UPDATE cases SET status = 'open', updated_at = ? WHERE id = ?", (now(), case_id))
    audit(db, case_id, actor, "reopened")
    db.commit()
    return _case(db, case_id)

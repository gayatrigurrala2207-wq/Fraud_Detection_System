"""FR-07: live feed of processed transactions with filters."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.services import Db

router = APIRouter(tags=["transactions"])

FEED_STATUS = """CASE WHEN c.disposition = 'fraud' THEN 'confirmed_fraud'
                      WHEN c.disposition = 'legitimate' THEN 'legitimate'
                      ELSE t.status END"""
FEED_COLUMNS = f"""t.id, t.trans_num, t.event_time, t.processed_at, t.merchant, t.category, t.amount, t.state,
                   t.score, t.risk_level, t.source, t.latency_ms, c.id AS case_id, {FEED_STATUS} AS status"""

Risk = Literal["low", "medium", "elevated", "high"]
Status = Literal["cleared", "flagged", "confirmed_fraud", "legitimate"]


@router.get("/transactions")
def transactions(
    db: Db,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    risk: Annotated[list[Risk] | None, Query()] = None,
    status: Annotated[Status | None, Query()] = None,
    source: Annotated[Literal["replay", "simulated"] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
    min_amount: Annotated[float | None, Query(ge=0)] = None,
) -> dict:
    where, params = ["t.processed_at IS NOT NULL"], []
    if risk:
        where.append(f"t.risk_level IN ({', '.join('?' * len(risk))})")
        params += risk
    if status:
        where.append(f"{FEED_STATUS} = ?")
        params.append(status)
    if source:
        where.append("t.source = ?")
        params.append(source)
    if q:
        where.append("(t.merchant LIKE ? OR t.trans_num LIKE ? OR t.category LIKE ?)")
        params += [f"%{q}%", f"{q}%", f"%{q}%"]
    if min_amount is not None:
        where.append("t.amount >= ?")
        params.append(min_amount)
    rows = db.execute(
        f"""SELECT {FEED_COLUMNS} FROM transactions t LEFT JOIN cases c ON c.transaction_id = t.id
            WHERE {' AND '.join(where)} ORDER BY t.processed_at DESC, t.id DESC LIMIT ?""",
        (*params, limit),
    ).fetchall()
    return {"items": [dict(row) for row in rows]}


@router.get("/transactions/{transaction_id}")
def transaction(transaction_id: int, db: Db) -> dict:
    row = db.execute(
        f"""SELECT {FEED_COLUMNS}, t.card_key, t.hour, t.distance_km, t.secs_since_last, t.card_mean_amt,
                   t.count_24h, t.model_version, t.threshold
            FROM transactions t LEFT JOIN cases c ON c.transaction_id = t.id WHERE t.id = ?""",
        (transaction_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return dict(row)

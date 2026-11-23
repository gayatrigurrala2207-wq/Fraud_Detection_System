"""FR-11: replay controls and manual (visibly simulated) transaction scoring."""

from secrets import token_hex
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import now, raw_features
from app.services import Actor, Db, Model
from pipelines.consumers.scoring import process_pending, score_transaction

router = APIRouter(tags=["replay"])


class ReplayCommand(BaseModel):
    action: Literal["start", "pause", "step", "reset"]
    speed: int | None = Field(default=None, ge=1, le=100)
    step_size: int = Field(default=500, ge=1, le=5000)


class SimulatedTransaction(BaseModel):
    merchant: str = Field(default="Manual entry", min_length=1, max_length=60)
    category: str
    amount: float = Field(gt=0, le=50_000)
    hour: int = Field(ge=0, le=23)
    weekday: int = Field(ge=0, le=6)
    age_years: float = Field(ge=14, le=100)
    distance_km: float = Field(ge=0, le=20_000)
    city_pop: float = Field(ge=0, le=10_000_000)
    gender: Literal["F", "M"]
    secs_since_last: float | None = Field(default=None, ge=0)
    card_prior_count: int = Field(default=0, ge=0)
    card_mean_amt: float | None = Field(default=None, ge=0)
    count_24h: float = Field(default=0, ge=0)
    amt_sum_24h: float = Field(default=0, ge=0)


def _status(db) -> dict:
    state = db.execute("SELECT running, speed FROM replay_state WHERE id = 1").fetchone()
    counts = db.execute(
        """SELECT COUNT(*) AS total, COALESCE(SUM(processed_at IS NOT NULL), 0) AS processed,
                  MAX(CASE WHEN processed_at IS NOT NULL THEN event_time END) AS last_event_time
           FROM transactions WHERE source = 'replay'""").fetchone()
    return {"running": bool(state["running"]), "speed": state["speed"], "total": counts["total"],
            "processed": counts["processed"], "remaining": counts["total"] - counts["processed"],
            "last_event_time": counts["last_event_time"]}


@router.get("/replay")
def replay_status(db: Db) -> dict:
    return _status(db)


@router.post("/replay")
def replay_command(command: ReplayCommand, db: Db, model: Model) -> dict:
    if command.speed is not None:
        db.execute("UPDATE replay_state SET speed = ? WHERE id = 1", (command.speed,))
    if command.action in ("start", "pause"):
        db.execute("UPDATE replay_state SET running = ? WHERE id = 1", (int(command.action == "start"),))
    elif command.action == "step":
        if model is None:
            raise HTTPException(status_code=503, detail="No trained model.")
        process_pending(db, model, command.step_size)
    elif command.action == "reset":
        db.executescript(
            """DELETE FROM audit_events; DELETE FROM case_notes; DELETE FROM cases;
               DELETE FROM transactions WHERE source = 'simulated';
               UPDATE transactions SET score = NULL, risk_level = NULL, status = NULL, processed_at = NULL,
                      latency_ms = NULL, model_version = NULL, threshold = NULL;
               UPDATE replay_state SET running = 0 WHERE id = 1;""")
    db.commit()
    return _status(db)


@router.get("/simulate/options")
def simulate_options(model: Model) -> dict:
    if model is None:
        raise HTTPException(status_code=503, detail="No trained model.")
    return {"categories": model.spec["categories"], "threshold": model.threshold,
            "high_risk_score": model.high_risk_score, "model_version": model.version}


@router.post("/simulate")
def simulate(request: SimulatedTransaction, db: Db, model: Model, actor: Actor) -> dict:
    if model is None:
        raise HTTPException(status_code=503, detail="No trained model.")
    if request.category not in model.spec["categories"]:
        raise HTTPException(status_code=422, detail="Unknown category.")
    values = request.model_dump()
    merchant = values.pop("merchant")
    cursor = db.execute(
        f"""INSERT INTO transactions (trans_num, event_time, merchant, category, amount, source,
               hour, weekday, age_years, distance_km, city_pop, gender, secs_since_last,
               card_prior_count, card_mean_amt, count_24h, amt_sum_24h)
            VALUES (?, ?, ?, ?, ?, 'simulated', {', '.join('?' * 11)})""",
        (f"SIM-{token_hex(8)}", now()[:19].replace("T", " "), f"{merchant} (simulated by {actor})",
         values["category"], values["amount"], values["hour"], values["weekday"], values["age_years"],
         values["distance_km"], values["city_pop"], values["gender"], values["secs_since_last"],
         values["card_prior_count"], values["card_mean_amt"], values["count_24h"], values["amt_sum_24h"]),
    )
    transaction_id = cursor.lastrowid
    row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    raw = raw_features(row)
    result = score_transaction(db, model, transaction_id, raw)
    db.commit()
    return {"transaction_id": transaction_id, "source": "simulated", **result,
            "threshold": model.threshold, "explanation": model.explain(pd.DataFrame([raw]))}

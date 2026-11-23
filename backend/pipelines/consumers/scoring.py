"""Replay consumer: score pending transactions, persist results, and open cases.

Processing is idempotent: only rows with no `processed_at` are scored, and each
transaction can open at most one case (UNIQUE constraint).
"""

import sqlite3
from time import perf_counter

import pandas as pd

from app.db import audit, now, raw_features
from ml.inference.scorer import Scorer


def score_transaction(connection: sqlite3.Connection, scorer: Scorer, transaction_id: int, raw: dict) -> dict:
    start = perf_counter()
    score = float(scorer.score(pd.DataFrame([raw]))[0])
    latency_ms = (perf_counter() - start) * 1000
    flagged = score >= scorer.threshold
    risk = scorer.risk_level(score)
    connection.execute(
        """UPDATE transactions SET score = ?, risk_level = ?, status = ?, processed_at = ?, latency_ms = ?,
           model_version = ?, threshold = ? WHERE id = ? AND processed_at IS NULL""",
        (score, risk, "flagged" if flagged else "cleared", now(), latency_ms, scorer.version, scorer.threshold,
         transaction_id),
    )
    case_id = None
    if flagged:
        stamp = now()
        cursor = connection.execute(
            "INSERT OR IGNORE INTO cases (transaction_id, status, created_at, updated_at) VALUES (?, 'open', ?, ?)",
            (transaction_id, stamp, stamp),
        )
        if cursor.rowcount:
            case_id = cursor.lastrowid
            audit(connection, case_id, "system", "case_opened",
                  f"Score {score:.3f} met threshold {scorer.threshold:.3f} (model {scorer.version}).")
    return {"score": score, "risk_level": risk, "flagged": flagged, "latency_ms": latency_ms, "case_id": case_id}


def process_pending(connection: sqlite3.Connection, scorer: Scorer, limit: int) -> int:
    rows = connection.execute(
        "SELECT * FROM transactions WHERE processed_at IS NULL AND source = 'replay' ORDER BY id LIMIT ?", (limit,)
    ).fetchall()
    for row in rows:
        score_transaction(connection, scorer, row["id"], raw_features(row))
    connection.commit()
    return len(rows)

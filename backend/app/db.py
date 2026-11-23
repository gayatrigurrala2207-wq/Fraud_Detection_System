"""SQLite persistence for scored transactions, cases, notes, and audit events.

SQLite stands in for PostgreSQL in local development (decision log 006: add services
when they have a real caller). The schema keeps scores and analyst dispositions in
separate tables (decision 005) and stores no raw card numbers or names.
"""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,               -- replay order for source = 'replay'
    trans_num TEXT UNIQUE NOT NULL,
    event_time TEXT NOT NULL,
    merchant TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    state TEXT,
    card_key TEXT,                        -- keyed pseudonym, never the card number
    hour INTEGER, weekday INTEGER, age_years REAL, distance_km REAL, city_pop REAL, gender TEXT,
    secs_since_last REAL, card_prior_count INTEGER, card_mean_amt REAL, count_24h REAL, amt_sum_24h REAL,
    source TEXT NOT NULL DEFAULT 'replay' CHECK (source IN ('replay', 'simulated')),
    score REAL, risk_level TEXT, status TEXT,
    processed_at TEXT, latency_ms REAL, model_version TEXT, threshold REAL
);
CREATE INDEX IF NOT EXISTS ix_tx_pending ON transactions (id) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_tx_processed ON transactions (processed_at, id);
CREATE INDEX IF NOT EXISTS ix_tx_card ON transactions (card_key, event_time);
CREATE INDEX IF NOT EXISTS ix_tx_risk ON transactions (risk_level, processed_at);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER UNIQUE NOT NULL REFERENCES transactions (id),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    disposition TEXT CHECK (disposition IN ('fraud', 'legitimate')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cases_status ON cases (status, id);

CREATE TABLE IF NOT EXISTS case_notes (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases (id),
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases (id),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replay_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    running INTEGER NOT NULL DEFAULT 0,
    speed INTEGER NOT NULL DEFAULT 5
);
INSERT OR IGNORE INTO replay_state (id, running, speed) VALUES (1, 0, 5);
"""

RAW_FIELDS = ["amount", "category", "hour", "weekday", "age_years", "distance_km", "city_pop", "gender",
              "secs_since_last", "card_prior_count", "card_mean_amt", "count_24h", "amt_sum_24h"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def connect(path: Path) -> sqlite3.Connection:
    # FastAPI may open a request's connection and use it on different worker threads;
    # each connection is still used by one request at a time.
    connection = sqlite3.connect(path, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def raw_features(row: sqlite3.Row | dict) -> dict:
    """Stored raw feature values in the shape `ml.features.engineering.transform` expects."""
    values = {field: row[field] for field in RAW_FIELDS}
    values["amt"] = values.pop("amount")
    return {k: (float("nan") if v is None else v) for k, v in values.items()}


def audit(connection: sqlite3.Connection, case_id: int, actor: str, action: str, detail: str | None = None) -> None:
    connection.execute(
        "INSERT INTO audit_events (case_id, actor, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (case_id, actor, action, detail, now()),
    )

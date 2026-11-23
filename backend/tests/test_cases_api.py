"""FR-06/07/08/11 API behavior against a small temporary database (no trained model needed)."""

from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
import pytest

from app.auth import current_user
from app.config import Settings, get_settings
from app.db import connect, init_schema
from app.main import app

SIGNED_IN = {"id": 1, "username": "dana", "display_name": "Dana", "role": "admin", "active": True,
             "created_at": "x", "last_login_at": None}


def insert_transaction(db, tx_id, status, score, risk, amount=50.0):
    db.execute(
        """INSERT INTO transactions (id, trans_num, event_time, merchant, category, amount, state, card_key,
               hour, weekday, age_years, distance_km, city_pop, gender, secs_since_last, card_prior_count,
               card_mean_amt, count_24h, amt_sum_24h, score, risk_level, status, processed_at, latency_ms)
           VALUES (?, ?, ?, 'Shop', 'grocery_pos', ?, 'NY', 'C-1', 23, 2, 40, 10, 1000, 'F', 60, 3, 20, 2, 40,
                   ?, ?, ?, ?, 1.5)""",
        (tx_id, f"T{tx_id}", f"2020-06-22 0{tx_id}:00:00", amount, score, risk, status,
         None if status is None else f"2026-01-01T00:00:0{tx_id}"),
    )


@pytest.fixture
def client():
    with TemporaryDirectory() as directory:
        data_dir = Path(directory)
        path = data_dir / "processed" / "fraudshield.sqlite"
        init_schema(path)
        with closing(connect(path)) as db:
            insert_transaction(db, 1, "cleared", 0.01, "low")
            insert_transaction(db, 2, "flagged", 0.95, "high", amount=500.0)
            insert_transaction(db, 3, None, None, None)
            db.execute("INSERT INTO cases (id, transaction_id, created_at, updated_at) VALUES (1, 2, 'x', 'x')")
            db.commit()
        app.dependency_overrides[get_settings] = lambda: Settings("test", data_dir, ("http://localhost:5173",))
        app.dependency_overrides[current_user] = lambda: SIGNED_IN
        yield TestClient(app)
        app.dependency_overrides.clear()


def test_overview_counts_processed_replay_only(client):
    body = client.get("/api/overview").json()
    assert body["processed"]["count"] == 2
    assert body["processed"]["queued"] == 1
    assert body["flagged"]["count"] == 1
    assert body["potential_fraud_value"] == 500.0
    assert body["outcomes"]["alert_precision"] is None  # too few reviewed cases
    assert set(body["definitions"]) >= {"processed", "flagged", "alert_precision"}


def test_feed_filters_and_reports_case_status(client):
    items = client.get("/api/transactions").json()["items"]
    assert [item["id"] for item in items] == [2, 1]
    flagged = client.get("/api/transactions", params={"risk": ["high"]}).json()["items"]
    assert [item["case_id"] for item in flagged] == [1]
    assert client.get("/api/transactions", params={"risk": ["bogus"]}).status_code == 422


def test_case_workflow_is_attributed_and_audited(client):

    assert client.post("/api/cases/1/resolve").status_code == 400
    assert client.post("/api/cases/1/label", json={"disposition": "fraud"}).status_code == 200
    assert client.post("/api/cases/1/notes", json={"body": "Called customer."}).status_code == 200
    assert client.post("/api/cases/1/resolve").json()["status"] == "resolved"

    detail = client.get("/api/cases/1").json()
    assert detail["case"]["disposition"] == "fraud"
    assert detail["notes"][0]["author"] == "dana"
    assert [event["action"] for event in detail["audit"]] == ["labeled", "note_added", "resolved"]
    assert {event["actor"] for event in detail["audit"]} == {"dana"}
    assert detail["explanation"] is None  # no model in this test
    assert "card_num" not in str(detail) and "C-1" in str(detail)  # pseudonym only

    feed = client.get("/api/transactions", params={"status": "confirmed_fraud"}).json()["items"]
    assert [item["id"] for item in feed] == [2]


def test_replay_pause_and_reset(client):
    assert client.post("/api/replay", json={"action": "start", "speed": 20}).json()["speed"] == 20
    assert client.post("/api/replay", json={"action": "pause"}).json()["running"] is False
    status = client.post("/api/replay", json={"action": "reset"}).json()
    assert status["processed"] == 0
    assert client.get("/api/cases").json()["items"] == []


def test_missing_database_returns_503():
    with TemporaryDirectory() as directory:
        app.dependency_overrides[get_settings] = lambda: Settings("test", Path(directory), ())
        app.dependency_overrides[current_user] = lambda: SIGNED_IN
        try:
            response = TestClient(app).get("/api/overview")
        finally:
            app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "build_all" in response.json()["detail"]

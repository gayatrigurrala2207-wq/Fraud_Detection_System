"""API contract tests using a temporary data directory."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
import pytest

from app.config import Settings, get_settings
from app.main import app

REPORT = {
    "archive_sha256": "ab" * 32,
    "passed": True,
    "train_ends_before_test": True,
    "warnings": ["example warning"],
    "observed_schema": [{"column": "amt", "type": "amount"}],
    "files": {
        "fraudTrain.csv": {
            "rows": 2,
            "label_counts": {"0": 1, "1": 1},
            "timestamp_min": "2020-01-01 00:00:00",
            "timestamp_max": "2020-01-01 00:00:01",
            "malformed_rows": 0,
            "duplicate_transaction_id_rows": 0,
            "out_of_order_rows": 0,
            "missing_by_column": {"amt": 0},
        }
    },
}


@pytest.fixture
def client():
    # tempfile instead of tmp_path: pytest's shared temp root may belong to another Windows account.
    with TemporaryDirectory() as directory:
        data_dir = Path(directory)
        app.dependency_overrides[get_settings] = lambda: Settings("test", data_dir, ("http://localhost:5173",))
        yield TestClient(app), data_dir
        app.dependency_overrides.clear()


def write_report(data_dir: Path, report: dict) -> None:
    (data_dir / "reports").mkdir()
    (data_dir / "reports" / "validation.json").write_text(json.dumps(report), encoding="utf-8-sig")


def test_health_reports_missing_data_without_failing(client):
    http, _ = client
    body = http.get("/api/health").json()
    statuses = {item["name"]: item["status"] for item in body["dependencies"]}
    assert body["status"] == "ok"
    assert statuses["API"] == "ok"
    assert statuses["Original dataset"] == "missing"
    assert statuses["Dataset validation"] == "missing"
    assert statuses["Fraud model"] == "missing"
    assert statuses["Database (SQLite)"] == "missing"


def test_health_reflects_passing_report(client):
    http, data_dir = client
    write_report(data_dir, REPORT)
    statuses = {item["name"]: item["status"] for item in http.get("/api/health").json()["dependencies"]}
    assert statuses["Dataset validation"] == "ok"


def test_dataset_validation_returns_aggregates_only(client):
    http, data_dir = client
    write_report(data_dir, REPORT)
    response = http.get("/api/dataset/validation")
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["columns"] == 1
    assert body["files"]["fraudTrain.csv"]["rows"] == 2
    assert "missing_by_column" not in body["files"]["fraudTrain.csv"]


def test_dataset_validation_missing_report_is_404(client):
    http, _ = client
    assert http.get("/api/dataset/validation").status_code == 404


def test_settings_lists_active_configuration(client):
    http, _ = client
    keys = {item["key"]: item["value"] for item in http.get("/api/settings").json()["settings"]}
    assert keys["FRAUDSHIELD_ENV"] == "test"
    assert keys["FRAUDSHIELD_CORS_ORIGINS"] == "http://localhost:5173"

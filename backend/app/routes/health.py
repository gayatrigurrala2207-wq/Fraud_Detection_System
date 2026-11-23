"""FR-12: service and dependency health."""

from contextlib import closing

from fastapi import APIRouter, Request

from app.config import VERSION
from app.db import connect
from app.routes.dataset import load_report
from app.services import Config, Model

router = APIRouter(tags=["health"])


def dependency(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


@router.get("/health")
def health(request: Request, config: Config, model: Model) -> dict:
    archive = config.archive_path
    report = load_report(config)
    if report is None:
        report_status = dependency("Dataset validation", "missing",
                                   "Run the validator to create data/reports/validation.json.")
    elif report.get("passed"):
        report_status = dependency("Dataset validation", "ok", "Latest validation report passed.")
    else:
        report_status = dependency("Dataset validation", "failed", "Latest validation report did not pass.")

    if config.database_path.is_file():
        with closing(connect(config.database_path)) as db:
            total, processed = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(processed_at IS NOT NULL), 0) FROM transactions").fetchone()
            running = db.execute("SELECT running FROM replay_state WHERE id = 1").fetchone()[0]
        database = dependency("Database (SQLite)", "ok", f"{processed:,} of {total:,} transactions scored.")
    else:
        running = False
        database = dependency("Database (SQLite)", "missing", "Run python -m scripts.build_all in backend/.")

    worker = getattr(request.app.state, "worker", None)
    if worker is None or not worker.alive:
        replay = dependency("Replay worker", "failed", "Worker is not running.")
    elif worker.last_error:
        replay = dependency("Replay worker", "failed", worker.last_error)
    else:
        replay = dependency("Replay worker", "ok", "Replaying." if running else "Idle (paused or finished).")

    return {
        "status": "ok",
        "version": VERSION,
        "environment": config.environment,
        "dependencies": [
            dependency("API", "ok", "Responding."),
            dependency("Original dataset", "ok" if archive.is_file() else "missing",
                       "Archive found in data/raw." if archive.is_file() else "Download the Kaggle ZIP to data/raw."),
            report_status,
            dependency("Fraud model", "ok" if model else "missing",
                       f"{model.version}, threshold {model.threshold:.3f}." if model
                       else "Run python -m scripts.build_all in backend/."),
            database,
            replay,
            dependency("PostgreSQL", "not_configured", "SQLite is used for local development."),
            dependency("Kafka", "not_configured", "The in-process replay worker stands in locally."),
            dependency("Redis", "not_configured", "Behavioral features are precomputed per transaction."),
        ],
    }

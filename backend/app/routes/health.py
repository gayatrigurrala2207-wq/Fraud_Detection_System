"""FR-12: service and dependency health."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import VERSION, Settings, get_settings
from app.routes.dataset import load_report

router = APIRouter(tags=["health"])


def dependency(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


@router.get("/health")
def health(config: Annotated[Settings, Depends(get_settings)]) -> dict:
    archive = config.archive_path
    report = load_report(config)
    if report is None:
        report_status = dependency(
            "Dataset validation", "missing", "Run the validator to create data/reports/validation.json."
        )
    elif report.get("passed"):
        report_status = dependency("Dataset validation", "ok", "Latest validation report passed.")
    else:
        report_status = dependency("Dataset validation", "failed", "Latest validation report did not pass.")

    return {
        "status": "ok",
        "version": VERSION,
        "environment": config.environment,
        "dependencies": [
            dependency("API", "ok", "Responding."),
            dependency(
                "Original dataset",
                "ok" if archive.is_file() else "missing",
                "Archive found in data/raw." if archive.is_file() else "Download the Kaggle ZIP to data/raw.",
            ),
            report_status,
            dependency("Fraud model", "not_available", "Trained in roadmap phases 5-7."),
            dependency("PostgreSQL", "not_configured", "Added in roadmap phase 8."),
            dependency("Kafka", "not_configured", "Added in roadmap phase 9."),
            dependency("Redis", "not_configured", "Added in roadmap phase 9."),
        ],
    }

"""FR-01: aggregate dataset validation results. Never returns row-level data."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings

router = APIRouter(tags=["dataset"])
FILE_FIELDS = ("rows", "label_counts", "timestamp_min", "timestamp_max", "malformed_rows",
               "duplicate_transaction_id_rows", "out_of_order_rows")


def load_report(config: Settings) -> dict | None:
    try:
        return json.loads(config.validation_report_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


@router.get("/dataset/validation")
def dataset_validation(config: Annotated[Settings, Depends(get_settings)]) -> dict:
    report = load_report(config)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No validation report. Run the dataset validator and save its output to data/reports/validation.json.",
        )
    return {
        "archive_sha256": report["archive_sha256"],
        "passed": report["passed"],
        "train_ends_before_test": report["train_ends_before_test"],
        "warnings": report["warnings"],
        "columns": len(report["observed_schema"]),
        "files": {
            name: {field: metrics[field] for field in FILE_FIELDS}
            for name, metrics in report["files"].items()
        },
    }

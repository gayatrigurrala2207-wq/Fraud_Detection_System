"""FR-12: active non-secret configuration."""

from fastapi import APIRouter

from app.config import BACKEND_ROOT, VERSION, training_config
from app.services import Config, Model

router = APIRouter(tags=["settings"])


def _relative(path) -> str:
    return path.relative_to(BACKEND_ROOT).as_posix() if path.is_relative_to(BACKEND_ROOT) else str(path)


@router.get("/settings")
def active_settings(config: Config, model: Model) -> dict:
    training = training_config()
    settings = [
        {"key": "FRAUDSHIELD_ENV", "value": config.environment, "description": "Deployment environment name.",
         "source": "environment"},
        {"key": "FRAUDSHIELD_DATA_DIR", "value": _relative(config.data_dir),
         "description": "Local dataset, model, report, and database directory.", "source": "environment"},
        {"key": "FRAUDSHIELD_CORS_ORIGINS", "value": ", ".join(config.cors_origins),
         "description": "Browser origins allowed to call the API.", "source": "environment"},
        {"key": "investigation_cost_usd", "value": str(training["investigation_cost_usd"]),
         "description": "Cost per investigated alert used to choose the threshold.", "source": "configs/training.json"},
        {"key": "missed_fraud_cost_multiplier", "value": str(training["missed_fraud_cost_multiplier"]),
         "description": "Multiplier on missed fraud amount used to choose the threshold.",
         "source": "configs/training.json"},
        {"key": "validation_start", "value": training["validation_start"],
         "description": "Start of the chronological validation partition.", "source": "configs/training.json"},
    ]
    if model:
        settings += [
            {"key": "model_version", "value": model.version, "description": "Deployed model.", "source": "model"},
            {"key": "threshold", "value": f"{model.threshold:.4f}",
             "description": "Scores at or above this are flagged and open a case.", "source": "model"},
            {"key": "high_risk_score", "value": f"{model.high_risk_score:.4f}",
             "description": "Scores at or above this are labeled high risk.", "source": "model"},
            {"key": "medium_score", "value": f"{model.medium_score:.4f}",
             "description": "Scores at or above this (below threshold) are labeled medium risk.", "source": "model"},
        ]
    return {"version": VERSION, "settings": settings}

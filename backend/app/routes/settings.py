"""FR-12: active non-secret configuration."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import BACKEND_ROOT, VERSION, Settings, get_settings

router = APIRouter(tags=["settings"])


@router.get("/settings")
def active_settings(config: Annotated[Settings, Depends(get_settings)]) -> dict:
    data_dir = config.data_dir
    shown = data_dir.relative_to(BACKEND_ROOT).as_posix() if data_dir.is_relative_to(BACKEND_ROOT) else str(data_dir)
    return {
        "version": VERSION,
        "settings": [
            {"key": "FRAUDSHIELD_ENV", "value": config.environment, "description": "Deployment environment name."},
            {"key": "FRAUDSHIELD_DATA_DIR", "value": shown, "description": "Local dataset and report directory."},
            {
                "key": "FRAUDSHIELD_CORS_ORIGINS",
                "value": ", ".join(config.cors_origins),
                "description": "Browser origins allowed to call the API.",
            },
        ],
    }

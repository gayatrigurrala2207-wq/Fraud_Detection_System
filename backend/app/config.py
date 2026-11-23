"""Non-secret application settings read from environment variables."""

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = BACKEND_ROOT.parent / "configs"
VERSION = "0.2.0"


@dataclass(frozen=True)
class Settings:
    environment: str
    data_dir: Path
    cors_origins: tuple[str, ...]

    @property
    def archive_path(self) -> Path:
        return self.data_dir / "raw" / "fraud-detection.zip"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def validation_report_path(self) -> Path:
        return self.reports_dir / "validation.json"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "processed" / "fraudshield.sqlite"


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.environ.get("FRAUDSHIELD_DATA_DIR", BACKEND_ROOT / "data"))
    origins = os.environ.get("FRAUDSHIELD_CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        environment=os.environ.get("FRAUDSHIELD_ENV", "development"),
        data_dir=data_dir if data_dir.is_absolute() else BACKEND_ROOT / data_dir,
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
    )


def training_config() -> dict:
    return json.loads((CONFIG_DIR / "training.json").read_text(encoding="utf-8"))

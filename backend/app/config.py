"""Non-secret application settings read from environment variables."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"


@dataclass(frozen=True)
class Settings:
    environment: str
    data_dir: Path
    cors_origins: tuple[str, ...]

    @property
    def archive_path(self) -> Path:
        return self.data_dir / "raw" / "fraud-detection.zip"

    @property
    def validation_report_path(self) -> Path:
        return self.data_dir / "reports" / "validation.json"


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.environ.get("FRAUDSHIELD_DATA_DIR", BACKEND_ROOT / "data"))
    origins = os.environ.get("FRAUDSHIELD_CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        environment=os.environ.get("FRAUDSHIELD_ENV", "development"),
        data_dir=data_dir if data_dir.is_absolute() else BACKEND_ROOT / data_dir,
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
    )

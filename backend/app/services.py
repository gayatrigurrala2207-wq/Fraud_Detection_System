"""Shared request dependencies: database connections, the deployed model, and JSON reports."""

from collections.abc import Iterator
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.db import connect
from ml.inference.scorer import Scorer

_scorers: dict[tuple[Path, float], Scorer] = {}
NOT_BUILT = "No processed data yet. From backend/, run: uv run --locked python -m scripts.build_all"


def load_scorer(config: Settings) -> Scorer | None:
    """The deployed model, reloaded automatically when a new one is trained."""
    model_file = config.models_dir / "model.txt"
    try:
        key = (config.models_dir, model_file.stat().st_mtime)
    except OSError:
        return None
    if key not in _scorers:
        _scorers.clear()
        _scorers[key] = Scorer(config.models_dir)
    return _scorers[key]


def get_scorer(config: Annotated[Settings, Depends(get_settings)]) -> Scorer | None:
    return load_scorer(config)


def get_db(config: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
    if not config.database_path.is_file():
        raise HTTPException(status_code=503, detail=NOT_BUILT)
    with closing(connect(config.database_path)) as connection:
        yield connection


def read_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def get_actor(x_analyst: Annotated[str | None, Header(max_length=40)] = None) -> str:
    """Analyst name attributed in audit events (no authentication in local development)."""
    name = (x_analyst or "").strip()
    return name or "analyst"


Db = Annotated[sqlite3.Connection, Depends(get_db)]
Model = Annotated[Scorer | None, Depends(get_scorer)]
Config = Annotated[Settings, Depends(get_settings)]
Actor = Annotated[str, Depends(get_actor)]

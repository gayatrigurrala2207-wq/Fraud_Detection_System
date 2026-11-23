"""Build everything the website needs from the original Kaggle ZIP.

Run from backend/:  uv run --locked python -m scripts.build_all

1. Train and compare models, then write the model, reports, and analytics (ml.training.train).
2. Load the held-out test file into the replay database (pipelines.producers).
3. Score the first transactions so the website has data immediately (pipelines.consumers).
Rerunning replaces the database, including cases and notes.
"""

from contextlib import closing
import json

from app.db import connect
from ml.inference.scorer import Scorer
from ml.training.train import BACKEND_ROOT, CONFIG_PATH, DEFAULT_ARCHIVE, MODELS_DIR, log, run
from pipelines.consumers.scoring import process_pending
from pipelines.producers.load_replay import build_replay_database

DATABASE = BACKEND_ROOT / "data" / "processed" / "fraudshield.sqlite"


def main() -> None:
    if not DEFAULT_ARCHIVE.is_file():
        raise SystemExit(f"Missing {DEFAULT_ARCHIVE}. Download the Kaggle ZIP first (see README).")
    data, raw, partition = run(DEFAULT_ARCHIVE)
    test = partition == "test"
    log("Loading replay database")
    rows = build_replay_database(DATABASE, data[test], raw[test])
    log(f"Loaded {rows:,} held-out transactions into {DATABASE.relative_to(BACKEND_ROOT)}")

    warm = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["warm_start_transactions"]
    scorer = Scorer(MODELS_DIR)
    with closing(connect(DATABASE)) as connection:
        processed = process_pending(connection, scorer, warm)
        connection.execute("UPDATE replay_state SET running = 1, speed = 5 WHERE id = 1")
        connection.commit()
        cases = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    log(f"Scored the first {processed:,} transactions ({cases} cases opened). Replay will continue at 5/s.")


if __name__ == "__main__":
    main()

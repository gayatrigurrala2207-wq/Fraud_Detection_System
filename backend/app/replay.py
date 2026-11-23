"""In-process replay worker: scores the next queued transactions every second while running.

Stands in for the Kafka producer/consumer pair locally; replay state lives in SQLite so
it survives restarts.
"""

import asyncio
from contextlib import closing
import logging

from app.config import Settings
from app.db import connect
from app.services import load_scorer
from pipelines.consumers.scoring import process_pending

log = logging.getLogger("fraudshield.replay")


class ReplayWorker:
    def __init__(self, config: Settings):
        self.config = config
        self.last_error: str | None = None
        self.alive = False

    def tick(self) -> int:
        if not self.config.database_path.is_file():
            return 0
        scorer = load_scorer(self.config)
        if scorer is None:
            return 0
        with closing(connect(self.config.database_path)) as connection:
            running, speed = connection.execute("SELECT running, speed FROM replay_state WHERE id = 1").fetchone()
            if not running:
                return 0
            processed = process_pending(connection, scorer, speed)
            if processed == 0:
                connection.execute("UPDATE replay_state SET running = 0 WHERE id = 1")
                connection.commit()
            return processed

    async def run(self) -> None:
        self.alive = True
        try:
            while True:
                try:
                    await asyncio.to_thread(self.tick)
                    self.last_error = None
                except Exception as error:  # keep the worker alive; surface the error in /api/health
                    self.last_error = f"{type(error).__name__}: {error}"
                    log.exception("Replay tick failed")
                await asyncio.sleep(1)
        finally:
            self.alive = False

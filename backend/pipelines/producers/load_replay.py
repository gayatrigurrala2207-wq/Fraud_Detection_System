"""Replay producer: load the held-out publisher test file into the replay queue.

Each transaction carries the point-in-time behavioral values computed from the full
history before it. Card numbers are replaced with keyed pseudonyms whose key is
discarded after loading, and names, addresses, and labels are not stored.
"""

from contextlib import closing
import hashlib
import hmac
from pathlib import Path
import secrets

import pandas as pd

from app.db import connect, init_schema

COLUMNS = ["trans_num", "event_time", "merchant", "category", "amount", "state", "card_key",
           "hour", "weekday", "age_years", "distance_km", "city_pop", "gender", "secs_since_last",
           "card_prior_count", "card_mean_amt", "count_24h", "amt_sum_24h"]


def build_replay_database(path: Path, data: pd.DataFrame, raw: pd.DataFrame) -> int:
    """Replace the database at `path` with an unprocessed replay queue. Returns rows loaded."""
    for suffix in ("", "-wal", "-shm"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    init_schema(path)

    key = secrets.token_bytes(32)
    pseudonyms = {card: "C-" + hmac.new(key, card.encode(), hashlib.sha256).hexdigest()[:10]
                  for card in data["cc_num"].unique()}
    frame = pd.DataFrame({
        "trans_num": data["trans_num"].to_numpy(),
        "event_time": data["ts"].dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy(),
        "merchant": data["merchant"].str.removeprefix("fraud_").to_numpy(),
        "category": data["category"].to_numpy(),
        "amount": data["amt"].to_numpy(float),
        "state": data["state"].to_numpy(),
        "card_key": data["cc_num"].map(pseudonyms).to_numpy(),
        **{column: raw[column].to_numpy() for column in COLUMNS[7:]},
    })
    frame = frame.astype(object).where(frame.notna(), None)
    with closing(connect(path)) as connection:
        connection.executemany(
            f"INSERT INTO transactions ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            frame.itertuples(index=False, name=None),
        )
        connection.commit()
    return len(frame)

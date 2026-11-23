"""Load the original Kaggle archive into one chronologically ordered DataFrame.

Only the columns needed for features, pseudonymous history, and labels are read.
Names, streets, jobs, and other unnecessary personal fields are never loaded.
"""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from ml.preprocessing.validate_dataset import MEMBERS

COLUMNS = [
    "trans_date_trans_time", "cc_num", "merchant", "category", "amt", "gender", "state",
    "lat", "long", "city_pop", "dob", "trans_num", "merch_lat", "merch_long", "is_fraud",
]
DTYPES = {"cc_num": str, "merchant": str, "category": str, "gender": str, "state": str, "trans_num": str}
SOURCE_FILE = {MEMBERS[0]: "train_file", MEMBERS[1]: "test_file"}


def load_transactions(archive: Path) -> pd.DataFrame:
    """Return both CSVs sorted by event time, with `source_file` naming the publisher partition."""
    frames = []
    with ZipFile(archive) as zipped:
        for member in MEMBERS:
            with zipped.open(member) as stream:
                frame = pd.read_csv(stream, usecols=COLUMNS, dtype=DTYPES)
            frame["source_file"] = SOURCE_FILE[member]
            frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data["ts"] = pd.to_datetime(data.pop("trans_date_trans_time"), format="%Y-%m-%d %H:%M:%S")
    data["dob"] = pd.to_datetime(data["dob"], format="%Y-%m-%d")
    # Deterministic order for equal timestamps (architecture: event contract).
    return data.sort_values(["ts", "trans_num"], kind="stable").reset_index(drop=True)

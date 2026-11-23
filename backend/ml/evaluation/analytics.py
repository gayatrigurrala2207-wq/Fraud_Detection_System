"""FR-09 analytics aggregates from publisher labels on the training file.

The publisher test file is held out for final evaluation, so exploratory views use
only `fraudTrain.csv`. Every block records its population and outcome source.
"""

import numpy as np
import pandas as pd

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
AMOUNT_EDGES = [0, 10, 25, 50, 100, 200, 300, 500, 750, 1000, 1500, np.inf]
RATIO_EDGES = [0, 0.5, 1, 2, 3, 5, 10, np.inf]


def _rates(frame: pd.DataFrame, key) -> pd.DataFrame:
    grouped = frame.groupby(key, observed=True)
    return pd.DataFrame({
        "transactions": grouped["is_fraud"].size(),
        "fraud": grouped["is_fraud"].sum(),
        "amount": grouped["amt"].sum(),
    }).assign(fraud_rate=lambda d: d["fraud"] / d["transactions"])


def _records(table: pd.DataFrame, label: str) -> list[dict]:
    rows = []
    for key, row in table.iterrows():
        rows.append({label: str(key), "transactions": int(row.transactions), "fraud": int(row.fraud),
                     "fraud_rate": round(float(row.fraud_rate), 6), "amount": round(float(row.amount), 2)})
    return rows


def _bucket_labels(edges) -> list[str]:
    return [f"{edges[i]:g}+" if np.isinf(edges[i + 1]) else f"{edges[i]:g}-{edges[i + 1]:g}" for i in range(len(edges) - 1)]


def build_analytics(data: pd.DataFrame, raw: pd.DataFrame) -> dict:
    frame = pd.DataFrame({
        "is_fraud": data["is_fraud"].to_numpy(), "amt": data["amt"].to_numpy(),
        "category": data["category"].to_numpy(), "state": data["state"].to_numpy(),
        "hour": raw["hour"].to_numpy(), "weekday": raw["weekday"].to_numpy(),
        "month": data["ts"].dt.strftime("%Y-%m").to_numpy(),
        "ratio": (raw["amt"] / raw["card_mean_amt"]).to_numpy(),
    })
    states = _rates(frame, "state")
    weekday = _rates(frame, "weekday")
    weekday.index = [WEEKDAYS[i] for i in weekday.index]
    amount = _rates(frame, pd.cut(frame["amt"], AMOUNT_EDGES, right=False, labels=_bucket_labels(AMOUNT_EDGES)))
    ratio = _rates(frame.dropna(subset=["ratio"]),
                   pd.cut(frame["ratio"].dropna(), RATIO_EDGES, right=False, labels=_bucket_labels(RATIO_EDGES)))
    return {
        "population": "Publisher training file (fraudTrain.csv)",
        "time_window": {"start": str(data["ts"].min()), "end": str(data["ts"].max())},
        "outcome_source": "Publisher fraud labels",
        "totals": {"transactions": int(len(frame)), "fraud": int(frame["is_fraud"].sum()),
                   "amount": round(float(frame["amt"].sum()), 2)},
        "monthly": _records(_rates(frame, "month"), "month"),
        "by_category": sorted(_records(_rates(frame, "category"), "category"), key=lambda r: -r["fraud_rate"]),
        "by_hour": _records(_rates(frame, "hour"), "hour"),
        "by_weekday": _records(weekday, "weekday"),
        "by_state": sorted(_records(states[states["transactions"] >= 1000], "state"), key=lambda r: -r["fraud_rate"])[:15],
        "by_amount": _records(amount, "bucket"),
        "spending_anomaly": _records(ratio, "bucket"),
    }

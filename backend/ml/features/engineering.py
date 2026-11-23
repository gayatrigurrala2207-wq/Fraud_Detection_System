"""FR-03 feature engineering.

Two stages keep training and live scoring consistent:

1. `compute_raw_features` derives point-in-time behavioral values from a chronologically
   sorted transaction history. Each value uses only strictly earlier transactions of the
   same card and never reads fraud labels.
2. `transform` turns those raw values into the numeric model matrix. The replay consumer
   and manual scoring call the same function with stored or user-supplied raw values.
"""

import numpy as np
import pandas as pd

RAW_COLUMNS = [
    "amt", "category", "hour", "weekday", "age_years", "distance_km", "city_pop", "gender",
    "secs_since_last", "card_prior_count", "card_mean_amt", "count_24h", "amt_sum_24h",
]
NUMERIC_FEATURES = [
    "log_amt", "hour", "weekday", "is_weekend", "is_night", "age_years", "distance_km",
    "log_city_pop", "is_male", "log_secs_since_last", "is_first_card_txn", "log_card_prior_count",
    "amt_to_card_mean", "log_card_mean_amt", "count_24h", "log_amt_sum_24h", "category_freq",
]
LABELS = {
    "log_amt": "Amount", "hour": "Hour of day", "weekday": "Day of week", "is_weekend": "Weekend",
    "is_night": "Night-time (22:00-05:59)", "age_years": "Customer age", "distance_km": "Customer-merchant distance",
    "log_city_pop": "City population", "is_male": "Gender", "log_secs_since_last": "Time since last transaction",
    "is_first_card_txn": "First transaction on card", "log_card_prior_count": "Card transaction history length",
    "amt_to_card_mean": "Amount vs card average", "log_card_mean_amt": "Card average amount",
    "count_24h": "Card transactions in previous 24h", "log_amt_sum_24h": "Card spend in previous 24h",
    "category_freq": "Category frequency", "category": "Merchant category",
}


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def compute_raw_features(data: pd.DataFrame) -> pd.DataFrame:
    """Raw point-in-time features. `data` must be sorted by (ts, trans_num)."""
    raw = pd.DataFrame(index=data.index)
    raw["amt"] = data["amt"].astype(float)
    raw["category"] = data["category"].astype(str)
    raw["hour"] = data["ts"].dt.hour
    raw["weekday"] = data["ts"].dt.weekday
    raw["age_years"] = (data["ts"] - data["dob"]).dt.days / 365.25
    raw["distance_km"] = haversine_km(data["lat"], data["long"], data["merch_lat"], data["merch_long"])
    raw["city_pop"] = data["city_pop"].astype(float)
    raw["gender"] = data["gender"].astype(str)

    cards = data.groupby("cc_num", sort=False)
    raw["secs_since_last"] = (data["ts"] - cards["ts"].shift()).dt.total_seconds()
    prior_count = cards.cumcount()
    prior_sum = cards["amt"].cumsum() - data["amt"]
    raw["card_prior_count"] = prior_count
    raw["card_mean_amt"] = (prior_sum / prior_count).where(prior_count > 0)

    raw["count_24h"], raw["amt_sum_24h"] = _previous_24h(data)
    return raw


def _previous_24h(data: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Count and spend per card in the window [t - 24h, t), excluding simultaneous events."""
    count = np.zeros(len(data))
    total = np.zeros(len(data))
    times = data["ts"].to_numpy("datetime64[ns]").astype(np.int64)
    amounts = data["amt"].to_numpy(float)
    day = np.int64(24 * 3600 * 10**9)
    for positions in data.groupby("cc_num", sort=False).indices.values():
        t = times[positions]  # positions are in chronological order because data is sorted
        cumulative = np.concatenate(([0.0], np.cumsum(amounts[positions])))
        start = np.searchsorted(t, t - day, side="left")
        end = np.searchsorted(t, t, side="left")
        count[positions] = end - start
        total[positions] = cumulative[end] - cumulative[start]
    return count, total


def build_spec(train_raw: pd.DataFrame) -> dict:
    """Learned preprocessing state, fitted on the training partition only."""
    shares = train_raw["category"].value_counts(normalize=True)
    return {"categories": sorted(shares.index), "category_freq": {k: float(v) for k, v in shares.items()}}


def feature_names(spec: dict) -> list[str]:
    return NUMERIC_FEATURES + [f"cat_{name}" for name in spec["categories"]]


def transform(raw: pd.DataFrame, spec: dict) -> np.ndarray:
    amt = raw["amt"].to_numpy(float)
    secs = raw["secs_since_last"].to_numpy(float)
    mean_amt = raw["card_mean_amt"].to_numpy(float)
    hour = raw["hour"].to_numpy(float)
    weekday = raw["weekday"].to_numpy(float)
    category = raw["category"].astype(str).to_numpy()
    columns = [
        np.log1p(amt),
        hour,
        weekday,
        (weekday >= 5).astype(float),
        ((hour >= 22) | (hour < 6)).astype(float),
        raw["age_years"].to_numpy(float),
        raw["distance_km"].to_numpy(float),
        np.log1p(raw["city_pop"].to_numpy(float)),
        (raw["gender"].astype(str).to_numpy() == "M").astype(float),
        np.where(np.isnan(secs), -1.0, np.log1p(np.maximum(secs, 0))),
        np.isnan(secs).astype(float),
        np.log1p(raw["card_prior_count"].to_numpy(float)),
        np.where(np.isnan(mean_amt) | (mean_amt <= 0), 1.0, amt / np.where(mean_amt > 0, mean_amt, 1.0)),
        np.log1p(np.where(np.isnan(mean_amt), amt, mean_amt)),
        raw["count_24h"].to_numpy(float),
        np.log1p(raw["amt_sum_24h"].to_numpy(float)),
        np.array([spec["category_freq"].get(c, 0.0) for c in category]),
    ]
    columns += [(category == name).astype(float) for name in spec["categories"]]
    return np.column_stack(columns).astype(np.float32)


def group_name(feature: str) -> str:
    """Collapse one-hot category columns into one explainable feature."""
    return "category" if feature.startswith("cat_") else feature

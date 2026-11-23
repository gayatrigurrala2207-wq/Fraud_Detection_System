"""FR-03/FR-04: point-in-time features cannot see current or future events or labels."""

import numpy as np
import pandas as pd

from ml.evaluation.metrics import cost_threshold
from ml.features.engineering import build_spec, compute_raw_features, feature_names, transform


def history():
    return pd.DataFrame({
        "cc_num": ["a", "b", "a", "a", "a"],
        "ts": pd.to_datetime(["2020-01-01 00:00", "2020-01-01 01:00", "2020-01-01 05:00",
                              "2020-01-01 05:00", "2020-01-02 06:00"]),
        "amt": [10.0, 99.0, 20.0, 30.0, 40.0],
        "category": ["food", "travel", "food", "food", "travel"],
        "dob": pd.Timestamp("1990-01-01"), "lat": 0.0, "long": 0.0, "merch_lat": 0.0, "merch_long": 1.0,
        "city_pop": 100, "gender": "F", "trans_num": list("12345"),
    })


def test_window_excludes_current_simultaneous_and_old_events():
    raw = compute_raw_features(history())
    assert raw["count_24h"].tolist() == [0, 0, 1, 1, 0]
    assert raw["amt_sum_24h"].tolist() == [0, 0, 10, 10, 0]
    assert raw["secs_since_last"].iloc[2] == 5 * 3600
    assert np.isnan(raw["card_mean_amt"].iloc[0])
    assert raw["card_mean_amt"].iloc[2] == 10


def test_future_events_and_labels_do_not_change_earlier_features():
    data = history()
    baseline = compute_raw_features(data)
    changed = data.copy()
    changed.loc[4, "amt"] = 99_999.0
    changed["is_fraud"] = [1, 1, 1, 1, 1]
    altered = compute_raw_features(changed)
    pd.testing.assert_frame_equal(baseline.iloc[:4], altered.iloc[:4])
    assert "is_fraud" not in altered.columns


def test_transform_uses_training_spec_and_handles_unseen_category():
    raw = compute_raw_features(history())
    spec = build_spec(raw.iloc[:3])
    unseen = raw.iloc[[4]].assign(category="unseen")
    matrix = transform(unseen, spec)
    assert matrix.shape == (1, len(feature_names(spec)))
    assert matrix[0, -len(spec["categories"]):].sum() == 0


def test_cost_threshold_balances_alert_cost_against_missed_fraud():
    scores = np.array([0.9, 0.8, 0.3, 0.1])
    labels = np.array([1, 0, 1, 0])
    amounts = np.array([100.0, 50.0, 5.0, 20.0])
    # Flagging the top one costs 10 + 5 missed = 15; flagging three costs 30; so 0.9 wins.
    threshold, cost = cost_threshold(scores, labels, amounts, investigation_cost=10, missed_multiplier=1)
    assert threshold == 0.9
    assert cost == 15

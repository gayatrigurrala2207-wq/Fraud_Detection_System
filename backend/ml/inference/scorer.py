"""Load the deployed model and score or explain transactions from raw feature values."""

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from ml.features.engineering import LABELS, feature_names, group_name, transform

# Raw value shown next to each explained feature.
DISPLAY_SOURCE = {
    "log_amt": "amt", "log_city_pop": "city_pop", "log_secs_since_last": "secs_since_last",
    "log_card_prior_count": "card_prior_count", "log_card_mean_amt": "card_mean_amt",
    "log_amt_sum_24h": "amt_sum_24h", "is_male": "gender", "category": "category",
}


class Scorer:
    def __init__(self, models_dir: Path):
        self.meta = json.loads((models_dir / "model.json").read_text(encoding="utf-8"))
        self.booster = lgb.Booster(model_file=str(models_dir / "model.txt"))
        self.spec = self.meta["spec"]
        self.names = feature_names(self.spec)
        self.version: str = self.meta["version"]
        self.threshold: float = self.meta["threshold"]
        self.high_risk_score: float = self.meta["high_risk_score"]
        self.medium_score: float = self.meta["medium_score"]

    def score(self, raw: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(transform(raw, self.spec), num_threads=1)

    def risk_level(self, score: float) -> str:
        if score >= self.high_risk_score:
            return "high"
        if score >= self.threshold:
            return "elevated"
        return "medium" if score >= self.medium_score else "low"

    def explain(self, raw: pd.DataFrame) -> dict:
        """Exact TreeSHAP contributions (log-odds) for one transaction, grouped per feature."""
        matrix = transform(raw, self.spec)
        contributions = self.booster.predict(matrix, pred_contrib=True, num_threads=1)[0]
        grouped: dict[str, float] = {}
        for name, value in zip(self.names, contributions[:-1]):
            grouped[group_name(name)] = grouped.get(group_name(name), 0.0) + float(value)
        row = raw.iloc[0]
        values = dict(zip(self.names, matrix[0].tolist()))
        items = []
        for feature, contribution in grouped.items():
            source = DISPLAY_SOURCE.get(feature)
            shown = row[source] if source else values.get(feature)
            if feature == "amt_to_card_mean":
                shown = values[feature]
            items.append({
                "feature": feature,
                "label": LABELS.get(feature, feature),
                "value": None if shown is None or (isinstance(shown, float) and np.isnan(shown)) else
                (shown.item() if hasattr(shown, "item") else shown),
                "contribution": round(contribution, 5),
            })
        items.sort(key=lambda item: -abs(item["contribution"]))
        return {"base_value": round(float(contributions[-1]), 5), "unit": "log-odds", "contributions": items}

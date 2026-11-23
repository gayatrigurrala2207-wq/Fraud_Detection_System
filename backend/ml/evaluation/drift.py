"""FR-10 drift: population stability index (PSI) against a reference window."""

import numpy as np

DRIFT_FEATURES = {
    "amt": "Amount", "distance_km": "Customer-merchant distance", "hour": "Hour of day",
    "age_years": "Customer age", "secs_since_last": "Time since last transaction",
    "count_24h": "Card transactions in previous 24h", "card_prior_count": "Card history length",
}


def reference_bins(values: np.ndarray, bins: int = 10) -> dict:
    values = values[~np.isnan(values)]
    edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)[1:-1]))
    return {"edges": edges.tolist(), "proportions": _proportions(values, edges).tolist()}


def _proportions(values: np.ndarray, edges) -> np.ndarray:
    counts = np.bincount(np.searchsorted(np.asarray(edges), values, side="right"), minlength=len(edges) + 1)
    return counts / max(counts.sum(), 1)


def psi(reference: dict, values: np.ndarray) -> float:
    values = values[~np.isnan(values)]
    expected = np.clip(np.asarray(reference["proportions"]), 1e-4, None)
    actual = np.clip(_proportions(values, reference["edges"]), 1e-4, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def psi_status(value: float) -> str:
    """Common PSI rule of thumb."""
    return "stable" if value < 0.1 else "moderate" if value < 0.25 else "significant"

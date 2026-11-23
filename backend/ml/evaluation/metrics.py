"""FR-04/FR-05 evaluation: cost-based thresholds, metrics, and curve points."""

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve


def cost_threshold(scores: np.ndarray, labels: np.ndarray, amounts: np.ndarray,
                   investigation_cost: float, missed_multiplier: float) -> tuple[float, float]:
    """Threshold minimizing investigation cost per alert + multiplier x amount of missed fraud.

    Returns (threshold, total cost). Transactions with score >= threshold are flagged.
    """
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    fraud_amount = (amounts * labels * missed_multiplier)[order]
    caught = np.concatenate(([0.0], np.cumsum(fraud_amount)))
    flagged = np.arange(len(scores) + 1)
    cost = investigation_cost * flagged + (caught[-1] - caught)
    # Only cut between distinct scores, so equal scores share a decision.
    valid = np.ones(len(scores) + 1, dtype=bool)
    valid[1:-1] = sorted_scores[:-1] > sorted_scores[1:]
    valid[0] = False  # flagging nothing is not a usable operating point
    best = int(np.flatnonzero(valid)[np.argmin(cost[valid])])
    return float(sorted_scores[best - 1]), float(cost[best])


def evaluate(scores: np.ndarray, labels: np.ndarray, amounts: np.ndarray, threshold: float,
             investigation_cost: float, missed_multiplier: float) -> dict:
    predicted = scores >= threshold
    tp = int(np.sum(predicted & (labels == 1)))
    fp = int(np.sum(predicted & (labels == 0)))
    fn = int(np.sum(~predicted & (labels == 1)))
    tn = int(np.sum(~predicted & (labels == 0)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    missed_amount = float(np.sum(amounts[~predicted & (labels == 1)]))
    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "pr_auc": float(average_precision_score(labels, scores)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "alerts": tp + fp,
        "missed_fraud_amount": missed_amount,
        "cost": investigation_cost * (tp + fp) + missed_multiplier * missed_amount,
        "rows": int(len(labels)),
        "fraud_rows": int(labels.sum()),
    }


def _downsample(x: np.ndarray, y: np.ndarray, points: int = 120) -> list[dict]:
    index = np.unique(np.linspace(0, len(x) - 1, min(points, len(x))).astype(int))
    return [{"x": round(float(x[i]), 5), "y": round(float(y[i]), 5)} for i in index]


def curves(scores: np.ndarray, labels: np.ndarray) -> dict:
    precision, recall, _ = precision_recall_curve(labels, scores)
    fpr, tpr, _ = roc_curve(labels, scores)
    order = np.argsort(recall)
    return {"pr": _downsample(recall[order], precision[order]), "roc": _downsample(fpr, tpr)}

"""FR-03 to FR-05: build features, compare models chronologically, and deploy the selected model.

Run from backend/:  uv run --locked python -m ml.training.train
(`python -m scripts.build_all` runs this and then loads the replay database.)
"""

import argparse
from datetime import datetime, timezone
from hashlib import file_digest
import json
import os
from pathlib import Path
import platform
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from ml.evaluation.analytics import build_analytics
from ml.evaluation.drift import DRIFT_FEATURES, reference_bins
from ml.evaluation.metrics import cost_threshold, curves, evaluate
from ml.features.engineering import LABELS, build_spec, compute_raw_features, feature_names, group_name, transform
from ml.preprocessing.load import load_transactions

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = BACKEND_ROOT.parent / "configs" / "training.json"
DEFAULT_ARCHIVE = BACKEND_ROOT / "data" / "raw" / "fraud-detection.zip"
MODELS_DIR = BACKEND_ROOT / "data" / "models"
REPORTS_DIR = BACKEND_ROOT / "data" / "reports"


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def lightgbm_params(seed: int, weighted: bool) -> dict:
    return {
        "objective": "binary", "learning_rate": 0.05, "num_leaves": 63, "min_child_samples": 50,
        "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1, "seed": seed,
        "verbose": -1, "is_unbalance": weighted,
    }


def candidate_models(seed: int):
    """(name, family, description, fit(X, y, X_val, y_val) -> predict_fn)."""

    def sklearn_fit(model):
        def fit(x, y, *_):
            model.fit(x, y)
            return lambda data: model.predict_proba(data)[:, 1]
        return fit

    def lightgbm_fit(weighted):
        def fit(x, y, x_val, y_val):
            booster = lgb.train(
                lightgbm_params(seed, weighted), lgb.Dataset(x, y), num_boost_round=1500,
                valid_sets=[lgb.Dataset(x_val, y_val)],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )
            fit.booster = booster
            return lambda data: booster.predict(data, num_iteration=booster.best_iteration)
        return fit

    def isolation_fit(x, *_):
        rng = np.random.default_rng(seed)
        sample = x[rng.choice(len(x), size=min(200_000, len(x)), replace=False)]
        model = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(sample)
        return lambda data: -model.score_samples(data)

    return [
        ("Dummy (class prior)", "baseline", "Predicts the training fraud rate for every transaction.",
         sklearn_fit(DummyClassifier(strategy="prior"))),
        ("Logistic regression (class-weighted)", "linear", "Standardized features, balanced class weights.",
         sklearn_fit(make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)))),
        ("Decision tree (class-weighted)", "tree", "max_depth=10, min_samples_leaf=100, balanced class weights.",
         sklearn_fit(DecisionTreeClassifier(max_depth=10, min_samples_leaf=100, class_weight="balanced",
                                            random_state=seed))),
        ("Random forest (class-weighted)", "ensemble",
         "100 trees, max_depth=16, 30% bootstrap samples, balanced_subsample weights.",
         sklearn_fit(RandomForestClassifier(n_estimators=100, max_depth=16, min_samples_leaf=5, max_samples=0.3,
                                            class_weight="balanced_subsample", n_jobs=-1, random_state=seed))),
        ("LightGBM", "boosting", "63 leaves, learning rate 0.05, early stopping on validation.", lightgbm_fit(False)),
        ("LightGBM (class-weighted)", "boosting", "As LightGBM with is_unbalance=true.", lightgbm_fit(True)),
        ("Isolation Forest (unsupervised)", "anomaly", "200 trees on a 200k training sample; labels unused.",
         isolation_fit),
    ]


def latency(booster: lgb.Booster, matrix: np.ndarray, repeats: int = 1000) -> dict:
    timings = []
    for i in range(min(repeats, len(matrix))):
        start = perf_counter()
        booster.predict(matrix[i:i + 1], num_threads=1)
        timings.append((perf_counter() - start) * 1000)
    return {
        "p50_ms": round(float(np.percentile(timings, 50)), 3),
        "p95_ms": round(float(np.percentile(timings, 95)), 3),
        "samples": len(timings),
        "conditions": f"Single-row predict on CPU, 1 thread, {platform.system()} {platform.machine()}, "
                      f"Python {platform.python_version()}, {os.cpu_count()} logical CPUs. Excludes feature building.",
    }


def run(archive: Path = DEFAULT_ARCHIVE) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Train and write all artifacts. Returns (data, raw features, partition) for the replay loader."""
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    seed = config["random_seed"]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    log("Loading original archive")
    with archive.open("rb") as file:
        archive_sha256 = file_digest(file, "sha256").hexdigest()
    data = load_transactions(archive)
    log(f"Loaded {len(data):,} transactions; computing point-in-time features")
    raw = compute_raw_features(data)

    validation_start = pd.Timestamp(config["validation_start"])
    partition = np.where(data["source_file"] != "train_file", "test",
                         np.where(data["ts"] < validation_start, "train", "validation"))
    masks = {name: partition == name for name in ("train", "validation", "test")}
    spec = build_spec(raw[masks["train"]])
    names = feature_names(spec)
    matrix = transform(raw, spec)
    labels = data["is_fraud"].to_numpy(int)
    amounts = data["amt"].to_numpy(float)
    split = {name: (matrix[mask], labels[mask], amounts[mask]) for name, mask in masks.items()}
    costs = (config["investigation_cost_usd"], config["missed_fraud_cost_multiplier"])
    windows = {name: {"start": str(data["ts"][mask].min()), "end": str(data["ts"][mask].max()),
                      "rows": int(mask.sum()), "fraud": int(labels[mask].sum())} for name, mask in masks.items()}
    log("Partitions: " + ", ".join(f"{k}={v['rows']:,} ({v['fraud']:,} fraud)" for k, v in windows.items()))

    x_train, y_train, _ = split["train"]
    x_val, y_val, amt_val = split["validation"]
    comparison, predictors = [], {}
    for name, family, description, fit in candidate_models(seed):
        log(f"Training {name}")
        start = perf_counter()
        predict = fit(x_train, y_train, x_val, y_val)
        fit_seconds = perf_counter() - start
        scores = predict(x_val)
        threshold, _ = cost_threshold(scores, y_val, amt_val, *costs)
        metrics = evaluate(scores, y_val, amt_val, threshold, *costs)
        comparison.append({"name": name, "family": family, "description": description,
                           "fit_seconds": round(fit_seconds, 1), "validation": metrics})
        predictors[name] = (predict, getattr(fit, "booster", None))
        log(f"  validation PR-AUC={metrics['pr_auc']:.4f} recall={metrics['recall']:.3f} "
            f"precision={metrics['precision']:.3f} ({fit_seconds:.0f}s)")

    # Deploy the best LightGBM variant: it provides exact TreeSHAP explanations (FR-05/FR-08).
    eligible = [row for row in comparison if predictors[row["name"]][1] is not None]
    selected = max(eligible, key=lambda row: row["validation"]["pr_auc"])
    best_overall = max(comparison, key=lambda row: row["validation"]["pr_auc"])
    predict, booster = predictors[selected["name"]]
    threshold = selected["validation"]["threshold"]
    log(f"Selected {selected['name']} (threshold {threshold:.4f}); evaluating once on held-out test")

    x_test, y_test, amt_test = split["test"]
    test_scores = predict(x_test)
    test_metrics = evaluate(test_scores, y_test, amt_test, threshold, *costs)
    log(f"  test PR-AUC={test_metrics['pr_auc']:.4f} recall={test_metrics['recall']:.3f} "
        f"precision={test_metrics['precision']:.3f}")

    sample = np.random.default_rng(seed).choice(len(x_val), size=min(20_000, len(x_val)), replace=False)
    contributions = booster.predict(x_val[sample], pred_contrib=True)[:, :-1]
    shap_importance, gain_importance = {}, {}
    for name, mean_abs, gain in zip(names, np.abs(contributions).mean(axis=0),
                                    booster.feature_importance("gain")):
        group = group_name(name)
        shap_importance[group] = shap_importance.get(group, 0.0) + float(mean_abs)
        gain_importance[group] = gain_importance.get(group, 0.0) + float(gain)
    total_gain = sum(gain_importance.values()) or 1.0
    importance = sorted(
        ({"feature": k, "label": LABELS.get(k, k), "mean_abs_shap": round(v, 5),
          "gain_share": round(gain_importance[k] / total_gain, 5)} for k, v in shap_importance.items()),
        key=lambda item: -item["mean_abs_shap"])

    trained_at = datetime.now(timezone.utc)
    version = f"lgbm-{trained_at:%Y%m%d-%H%M%S}"
    booster.save_model(str(MODELS_DIR / "model.txt"), num_iteration=booster.best_iteration)
    meta = {
        "version": version, "model": selected["name"], "trained_at": trained_at.isoformat(timespec="seconds"),
        "threshold": threshold,
        "high_risk_score": max(config["high_risk_score"], threshold),
        "medium_score": threshold * config["medium_fraction_of_threshold"],
        "spec": spec, "feature_names": names, "archive_sha256": archive_sha256,
        "best_iteration": booster.best_iteration,
    }
    (MODELS_DIR / "model.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    val_raw = raw[masks["validation"]]
    drift_reference = {
        "window": f"Validation partition {windows['validation']['start']} to {windows['validation']['end']}",
        "features": {f: reference_bins(val_raw[f].to_numpy(float)) for f in DRIFT_FEATURES},
        "score": reference_bins(predict(x_val)),
    }
    (MODELS_DIR / "drift_reference.json").write_text(json.dumps(drift_reference), encoding="utf-8")

    report = {
        "version": version, "trained_at": meta["trained_at"], "selected_model": selected["name"],
        "best_validation_model": best_overall["name"],
        "selection_rule": "Highest validation PR-AUC among models with exact TreeSHAP explanations (LightGBM variants).",
        "threshold": threshold,
        "threshold_rule": (f"Minimizes ${costs[0]:g} per investigated alert + {costs[1]:g} x missed fraud amount "
                           "on the validation partition."),
        "partitions": windows, "features": names, "comparison": comparison,
        "test": {**test_metrics, **curves(test_scores, y_test)},
        "feature_importance": importance,
        "latency": latency(booster, x_test),
        "not_compared": ["XGBoost (not installed; LightGBM covers gradient boosting)",
                         "Train-only resampling (class weights compared instead)"],
    }
    (REPORTS_DIR / "model_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    train_file = data["source_file"] == "train_file"
    analytics = build_analytics(data[train_file], raw[train_file])
    (REPORTS_DIR / "analytics.json").write_text(json.dumps(analytics, indent=2), encoding="utf-8")

    runs_path = REPORTS_DIR / "runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8")) if runs_path.exists() else []
    runs.append({
        "run_id": version, "trained_at": meta["trained_at"], "archive_sha256": archive_sha256,
        "config": config, "selected_model": selected["name"], "threshold": threshold,
        "validation": {row["name"]: {k: row["validation"][k] for k in ("pr_auc", "roc_auc", "recall", "precision")}
                       for row in comparison},
        "test": {k: test_metrics[k] for k in ("pr_auc", "roc_auc", "recall", "precision", "f1")},
    })
    runs_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    log(f"Wrote model {version} and reports")
    return data, raw, partition


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    run(parser.parse_args().archive)


if __name__ == "__main__":
    main()

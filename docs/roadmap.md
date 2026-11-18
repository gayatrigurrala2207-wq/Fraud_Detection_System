# Implementation Roadmap

| Phase | Increment | Evidence required before approval |
| --- | --- | --- |
| 1 | Repository, documentation, and Python setup | Locked environment and smoke tests |
| 2 | Dataset acquisition and validation | Original CSVs inspected locally and aggregated schema and quality report |
| 3 | EDA and statistical analysis | Reproducible charts and statistical results with assumptions |
| 4 | Feature engineering and preprocessing | Chronological partitions and tests for leakage and ordering |
| 5 | Baseline models | Dummy, logistic regression, decision tree, and Random Forest validation comparison |
| 6 | Advanced models and tuning | XGBoost, LightGBM, and Isolation Forest validation comparison with imbalance experiments |
| 7 | Evaluation and explainability | Cost-tuned threshold, final held-out evaluation, latency, and SHAP evidence |
| 8 | API and persistence | Validated scoring and case APIs, database migrations, and health checks |
| 9 | Replay and streaming | Kafka replay, Redis behavioral state, WebSockets, retries, and deduplication tests |
| 10 | Analyst frontend | Nine navigable views, accessible risk labels, and replay and case workflows |
| 11 | Tracking and monitoring | MLflow run lineage and Evidently reports populated by measured data |
| 12 | Testing, local deployment, and CI | Reproducible Compose setup, GitHub Actions, and end-to-end verification |

Each phase records its verification, limitations, and proposed Git commit in the development progress tracker. Proceed after the user approves the completed phase.

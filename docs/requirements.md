# Software Requirements Specification

## Purpose and users

FraudShield replays historical credit card transactions, estimates fraud risk, and gives analysts evidence to investigate alerts. Analysts review and resolve cases. ML engineers train, compare, and monitor models. Local operators run the replay and inspect service health.

The source for Phase 2 is the [Credit Card Transactions Fraud Detection dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection). Training uses the original transactions.

## Functional requirements

| ID | Requirement | Acceptance |
| --- | --- | --- |
| FR-01 | Acquire and validate the original Kaggle Credit Card Transactions Fraud Detection dataset. | Record provenance, observed fields and types, split boundaries, row counts, and aggregated quality results. Validate identifiers, timestamps, labels, coordinates, missing values, and duplicates before implementing downstream ingestion. |
| FR-02 | Profile fraud, transaction amounts, categories, time, geography, missingness, duplicates, and correlations. | Reproducible EDA reports class prevalence, meaningful effect sizes, and suitable statistical tests with assumptions and uncertainty. |
| FR-03 | Compute hour, weekday, weekends, customer-to-merchant distance, velocity, time since last event, category frequency, historical spending averages and deviations, and rolling counts and amounts. | Feature tests demonstrate that current and future transactions and fraud labels cannot enter historical aggregates. |
| FR-04 | Compare Dummy, logistic regression, decision tree, Random Forest, XGBoost, LightGBM, and Isolation Forest with chronological train, validation, and final test partitions. | Models share a documented evaluation protocol. Compare class weights and applicable train-only resampling. Tune thresholds on validation using configurable missed-fraud and investigation costs. |
| FR-05 | Evaluate precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix, false-positive rate, and inference latency. | Record actual metrics, threshold, split, model version, and latency measurement conditions. Explain supported individual predictions using SHAP. |
| FR-06 | Show processed counts and value, flagged and high-risk counts, predicted and confirmed outcomes, potential fraud value, and processing latency. | Overview defines each metric and denominator. Confirmed detection rate is shown only when sufficient ground truth exists and its coverage is visible. |
| FR-07 | Provide a live feed with transaction ID, merchant, time, amount, score, risk level, and status. | Analysts can pause, resume, filter, and inspect transactions. |
| FR-08 | Provide a case workspace with risk evidence, SHAP explanations, behavioral anomalies, and masked customer history. | Analysts can label fraud or legitimate, add notes, resolve cases, and retrieve attributed audit events. |
| FR-09 | Visualize fraud trends, category risk, geography, transaction amounts, spending anomalies, and risk score distributions. | Charts identify population, time window, and whether outcomes come from scores, labels, or investigation results. |
| FR-10 | Report active model version, model comparison, precision and recall, PR and ROC curves, confusion matrix, feature importance, inference latency, drift, and experiments. | Views derive from real experiment and monitoring artifacts and display empty states before evidence exists. |
| FR-11 | Replay original transactions at configurable speeds and score manually submitted transactions. | Manual input is visibly labeled simulated and report consumers can distinguish event provenance. |
| FR-12 | Expose system health and configurable application settings. | Operators can see dependency status and understand the active configuration. |

## Quality and operational requirements

- Develop and demonstrate locally on Apple Silicon using CPU inference and no paid services. Record native dependency requirements as phases introduce them.
- Keep raw card identifiers, names, addresses, and other unnecessary personal data out of application responses, UI, logs, and committed artifacts. Limit raw files to local protected storage.
- Use schema validation, structured redacted logs, retries, dead-letter routing, idempotency, health endpoints, database indexes, and environment configuration as the relevant components arrive.
- Keep data, secrets, and model artifacts out of Git. Store experiment metadata with reproducible data, code, feature, and model versions.
- Use a dark navy sidebar, neutral workspace, compact responsive tables, accessible contrast, and visible text alongside risk colors. Provide distinct views for all nine navigation areas in FR-06 through FR-12.

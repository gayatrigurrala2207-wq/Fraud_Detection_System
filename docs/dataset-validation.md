# Original Dataset Validation

## Source and reproducibility

The original [Credit Card Transactions Fraud Detection dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection) contains simulated financial transactions. The archive was downloaded through Kaggle on 18 November 2026 and validated locally on Windows with CPython 3.12.14.

| Archive property | Observed value |
| --- | --- |
| Compressed size | 211,766,662 bytes |
| SHA-256 | `4e32829b9ba5a6b17af707c513c15204011044df0e8971e431cedca3d8c0a8a1` |
| Training member | `fraudTrain.csv`, 351,238,196 bytes uncompressed |
| Test member | `fraudTest.csv`, 150,354,339 bytes uncompressed |

The checksum identifies the specific ZIP bytes used for this report. The README explains how to download the archive and rerun validation.

## Observed schema

Both UTF-8 CSVs have the same ordered header. The table groups fields by meaning.

| Observed columns | Interpretation |
| --- | --- |
| Empty first column name | Integer export index |
| `trans_date_trans_time` | Calendar timestamp in `YYYY-MM-DD HH:MM:SS`, with no timezone in the CSV |
| `cc_num`, `zip` | Card identifier and postal code as digit strings |
| `trans_num` | 32-character hexadecimal transaction identifier |
| `merchant`, `category` | Merchant name and category text |
| `first`, `last`, `gender`, `street`, `city`, `state`, `job` | Customer text fields |
| `amt` | Nonnegative decimal amount with up to two fractional digits |
| `lat`, `long`, `merch_lat`, `merch_long` | Customer and merchant coordinates within latitude and longitude bounds |
| `city_pop`, `unix_time` | Nonnegative integers |
| `dob` | Calendar date in `YYYY-MM-DD` |
| `is_fraud` | Binary label. `1` indicates fraud and `0` indicates legitimate. |

## Full-file results

| Measure | Publisher train | Publisher test |
| --- | ---: | ---: |
| Records | 1,296,675 | 555,719 |
| Legitimate | 1,289,169 | 553,574 |
| Fraud | 7,506 | 2,145 |
| Fraud prevalence | 0.579% | 0.386% |
| Malformed rows, missing fields, or invalid fields | 0 | 0 |
| Duplicate transaction ID rows | 0 | 0 |
| Backward timestamp steps | 1 | 0 |
| Largest backward step | 86,226 seconds | 0 seconds |
| Earliest calendar timestamp | 2019-01-01 00:00:18 | 2020-06-21 12:14:25 |
| Latest calendar timestamp | 2020-06-21 12:13:37 | 2020-12-31 23:59:34 |

The combined archive has **1,852,394 records** and zero overlapping transaction IDs. A 48-second gap separates the two partitions. Both labels occur in each partition. The structural and split checks passed with time-related warnings. The difference in observed fraud prevalence is descriptive and can be explored in Phase 3.

## Implications for subsequent phases

- Preserve the publisher's test partition for final evaluation. Derive a validation partition chronologically from the publisher's training data.
- Use `trans_date_trans_time` as the source calendar time for EDA and investigate the backward step before defining event ordering. Before building behavioral features or replay, sort the chosen event times chronologically with a deterministic tie-breaker. Treat the calendar time as timezone-naive until its timezone is established.
- The observed range of `unix_time` minus seconds from a naive 1970 epoch is **−220,924,800 to −220,838,400** in train and **−220,924,800** in test. The magnitude and varying offset preclude treating this field as an interchangeable Unix timestamp without source clarification.
- Scope duplicate detection to transaction IDs and define blanks as empty or whitespace-only cells. Validation checks syntax, coordinate bounds, and split integrity. Further EDA can assess plausibility and unusual distributions.
- Keep the original archive under ignored `data/raw/` and generated reports under ignored `data/reports/`. Application ingestion must drop unnecessary customer fields and pseudonymize card identifiers before publishing events. The validator emits aggregate counts and never prints raw rows.
- The CSV scan streams rows and keeps a set of transaction IDs for exact duplicate detection. A disk-backed index is an option if the dataset grows beyond available memory.

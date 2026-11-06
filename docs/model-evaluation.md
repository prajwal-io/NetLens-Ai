# Model training and evaluation

## Dataset and target

Source: [Kaggle Network Anomaly Dataset](https://www.kaggle.com/datasets/kaiser14/network-anomaly-dataset), fetched with `kagglehub.dataset_download("kaiser14/network-anomaly-dataset")`.

The downloaded version contains 1,001 timestamped records. The labeled file has `anomaly` plus five auxiliary `anomaly_*` columns. The model uses only eight nonnegative numeric measurements: throughput, congestion, packet loss, latency, jitter, video occupancy percentage, video bitrate, and number of videos. Timestamp is used for ordering only. Target and helper-label fields are excluded from all model inputs.

The target semantics are network **performance anomaly** (`1`) versus normal (`0`). This dataset does not contain verified intrusion or malware labels. Predictions must not be described as cyberattack detection.

## Procedure

1. Sort rows by timestamp.
2. Use the first 60% (600 rows) to fit candidate Random Forest and Logistic Regression models.
3. Use the next 20% (200 rows) to compare positive-class F1 and select a score threshold.
4. Refit the selected pipeline on the first 80% (800 rows).
5. Evaluate once on the final chronological 20% (201 rows).

The validation segment had 16 anomalous rows. Random Forest had the higher validation F1 (0.800) at threshold 0.60, compared with Logistic Regression validation F1 0.643 at threshold 0.95. The later test segment is not used to choose the algorithm or threshold.

## Final chronological holdout

Selected model: **Random Forest**, version `netsight-rf-v1`. Test support is 187 normal and 14 anomalous records.

| Metric | Test result |
|---|---:|
| Accuracy | 94.5% |
| Precision for anomalous class | 100.0% |
| Recall for anomalous class | 21.4% |
| F1-score for anomalous class | 35.3% |

Confusion matrix (rows are actual labels; columns are predictions):

| Actual / predicted | Normal | Anomalous |
|---|---:|---:|
| Normal | 187 | 0 |
| Anomalous | 11 | 3 |

The model found 3 of 14 anomalous test records and missed 11. Its high accuracy is a poor summary of anomaly detection quality. The backend and Model Lab surface a warning because the held-out anomaly recall is below 50%. Treat all output as experimental and review the data before acting on it.

This is a small sample from a single day, so the holdout is limited and time-dependent distribution shift may affect results. It is not suitable evidence of general security detection performance.

## Reproduce locally

From `backend/` with dependencies installed:

```powershell
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
```

The scripts write `ml/artifacts/netsight-model.joblib` and `ml/artifacts/netsight-model.json`. The metadata contains dataset SHA-256, split boundaries, model version, validation candidate metrics, score threshold, test metrics, and limitations. The API only loads artifacts with completed holdout evaluation.

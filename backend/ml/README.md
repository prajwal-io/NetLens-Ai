# Phase 2 model pipeline

The pipeline downloads the user-selected Kaggle dataset, compares a Random Forest with a Logistic Regression baseline, selects by validation F1, and reports metrics on a later chronological holdout. It excludes the dataset's `anomaly_*` helper-label columns from model inputs.

## Setup and run

From `backend/` with the virtual environment active:

```bash
python -m pip install -r requirements.txt
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The KaggleHub cache is written to `../data/kagglehub-cache/`, which is ignored by Git. The downloaded source contains `network_dataset.csv` and `network_dataset_labeled.csv`. Training uses the labeled file. Raw dataset files are not copied into the repository.

Training can be directed to another labeled CSV with `python -m ml.train --data PATH`; evaluation must use the same file. An artifact is written to `ml/artifacts/netsight-model.joblib` with a JSON metadata sidecar. The API loads only artifacts with completed held-out evaluation metadata. Model artifacts are local generated files and should be regenerated with the documented commands when dependencies or source data change.

## Feature and label contract

The model uses eight numeric measurements: throughput, congestion, packet loss, latency, jitter, video occupancy percentage, video bitrate, and number of videos. Timestamp is used only to order the chronological split. The constant bandwidth column, categorical routing/target columns, the ground-truth `anomaly` column, and auxiliary `anomaly_*` flags are excluded from features.

The target is `anomaly` (`0` normal, `1` anomalous). For this dataset, that label describes network performance anomalies. It is not an intrusion, malware, or malicious-traffic label. The API's score is the model's `predict_proba` value for class `1`; it is not calibrated and is not proof of an incident.

## Evaluation safeguards

- Stable chronological split: first 60% training, next 20% validation, final 20% untouched test.
- Candidate and score-threshold selection use validation data only.
- Accuracy, positive-class precision, recall, F1, support, and confusion matrix are calculated from the untouched test set.
- Evaluation metadata records dataset SHA-256, split sizes and dates, model version, candidate validation metrics, and the chosen decision threshold.
- The current dataset is small and spans a single day. Low held-out anomaly recall is surfaced in Model Lab and the API; it must not be described as reliable security detection.

Review the dataset's current Kaggle license and attribution before redistributing source data or trained artifacts.

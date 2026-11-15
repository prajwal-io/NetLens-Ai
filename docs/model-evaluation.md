# UNSW-NB15 model evaluation

See [dataset review and candidate selection](dataset-review-and-model-selection.md) for source compatibility checks and candidate comparison.

## Result summary

The source trains on the canonical UNSW-NB15 partitions and evaluates the final pipeline on the untouched official test split. The generated model and raw dataset are local artifacts and are intentionally excluded from Git. The evaluated version is `netsight-rf-unsw-v4`.

| Item | Result |
|---|---:|
| Dataset | UNSW-NB15 |
| Official training rows | 175,341 |
| Official test rows | 82,332 |
| Input features | 42 (39 numeric, 3 categorical) |
| Validation-selected model | Random Forest (260 trees, max depth 24) |
| Validation split | 139,174 fit / 36,167 validation, grouped by duplicate feature signature |
| Selected malicious-class threshold | 0.5779595 |
| Threshold policy | Maximize validation recall with false-positive rate at or below 5% |

The official UNSW project page describes these canonical train and test partition sizes ([UNSW-NB15 Dataset](https://research.unsw.edu.au/projects/unsw-nb15-dataset)). SHA-256 and byte-size pins in the code bind local files to the CSV objects at the recorded immutable mirror revision; the official page does not publish those hashes.

Threshold and model selection use validation data only. Random Forest achieved validation accuracy 0.9540, recall 0.9557, precision 0.9775, and false-positive rate 0.0499. Logistic Regression achieved accuracy 0.9178, recall 0.9036, precision 0.9762, and false-positive rate 0.0499. Random Forest was selected for higher recall within the same alert budget, then refit on all 175,341 official training rows. The official test split was not used to select the model or threshold.

## Held-out official test result

| Metric | Score |
|---|---:|
| Accuracy | 0.9069 |
| Balanced accuracy | 0.8999 |
| Precision (malicious) | 0.8754 |
| Recall (malicious) | 0.9687 |
| F1 (malicious) | 0.9197 |
| Average precision | 0.9877 |
| ROC-AUC | 0.9837 |
| False-positive rate | 0.1689 |
| Specificity | 0.8311 |

Support: 37,000 normal and 45,332 attack-labeled flows.

| Actual \\ Predicted | Normal | Malicious |
|---|---:|---:|
| Normal | 30,752 | 6,248 |
| Malicious | 1,419 | 43,913 |

Compared with v3 at its validation-selected threshold, v4 improves validation recall from 0.9521 to 0.9557 but does not improve held-out accuracy: it changes from 0.9082 to 0.9069, with 113 more false positives and 7 fewer false negatives. The validation false-positive budget is not a guarantee on the test split: the v4 normal-flow score distribution yields a 16.9% test false-positive rate despite a 5% validation rate. This split shift is a material limitation, so operators should treat classifications as review signals rather than proof of an incident. The v4 change is retained as a validation-selected experiment, not claimed as a test-accuracy improvement.

## Repeated-record sensitivity check

The official test partition includes 8,541 records (10.37%) whose complete 42-feature signature occurs in the training partition. To show the effect of exact feature-signature overlap, evaluation also reports test rows whose signatures do not occur in training.

| Novel-signature subset metric | Score |
|---|---:|
| Rows | 73,791 |
| Accuracy | 0.9012 |
| Balanced accuracy | 0.8988 |
| Precision (malicious) | 0.8623 |
| Recall (malicious) | 0.9634 |
| F1 (malicious) | 0.9100 |
| Average precision | 0.9838 |
| ROC-AUC | 0.9811 |
| False-positive rate | 0.1658 |
| Specificity | 0.8342 |

Confusion matrix, rows actual and columns predicted: `[[29,639, 5,889], [1,400, 36,863]]` for normal and malicious labels. Removing exact signature overlap does not simulate independent networks or future traffic.

## Pipeline and reproducibility

1. Download both splits into a staging directory; verify their expected byte counts, canonical row counts, feature headers, and SHA-256 pins before promoting either active file.
2. Validate the binary target and exact feature schema. Exclude `id`, `label`, and `attack_cat` from model input.
3. Fit numeric median imputation, categorical most-frequent imputation, and one-hot encoding inside each candidate pipeline.
4. Make a seeded stratified validation split inside the official training partition while keeping identical feature signatures together.
5. Compare Random Forest and Logistic Regression. Select each model's threshold to maximize malicious recall subject to validation false-positive rate no higher than 5%; choose the candidate with higher recall, then lower false-positive rate. The untouched official test split is only used to report the resulting tradeoff.
6. Refit the selected model and preprocessing pipeline on all official training data.
7. Evaluate once on the untouched official test partition and record the result in the model metadata.

From `backend/`, with the project's Python 3.12 environment active:

```powershell
python -m pip install -r requirements.lock.txt
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
```

The API accepts inference only when a locally generated artifact includes held-out evaluation metadata. The downloader pins dataset bytes to the exact commit of the public mirror in model metadata and the local download manifest.

## Limitations

- UNSW-NB15 is a controlled academic benchmark, not live or production traffic.
- The official test split's false-positive rate (16.9%) is materially higher than the 5% validation budget, demonstrating that the validation target does not guarantee the same workload on shifted data.
- The test set contains repeated feature signatures; full and novel-signature metrics are disclosed.
- The v4 model missed 1,419 attack-labeled flows and raised 6,248 false alerts on the full official test split at the selected threshold.
- `malicious_score` is an uncalibrated `predict_proba` value, not calibrated risk or attack confidence.
- Benchmark performance does not demonstrate generalization to other networks, unseen attack types, or future traffic.
- The trained artifact is not shipped with source; each local environment must download the dataset and train/evaluate before model endpoints become available.


## Threshold and operational policy

Retain the v4 validation-selected threshold `0.5779595162664161`; do not tune it against the official test partition. Its 5% validation false-positive budget is only a candidate-selection constraint. The 16.89% held-out false-positive rate (6,248 false alerts) is not suitable evidence for unattended operational detection. The UI and saved reports expose the actual evaluation values, score meaning and review limitations. Operational tuning requires a representative network-specific validation set and an agreed alert budget.

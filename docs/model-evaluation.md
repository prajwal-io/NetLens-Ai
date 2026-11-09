# UNSW-NB15 model evaluation

## Result summary

The source trains on the canonical UNSW-NB15 partitions and evaluates the final pipeline on the untouched official test split. The generated model and raw dataset are local artifacts and are intentionally excluded from Git. The evaluated version is `netsight-rf-unsw-v3`.

| Item | Result |
|---|---:|
| Dataset | UNSW-NB15 |
| Official training rows | 175,341 |
| Official test rows | 82,332 |
| Input features | 42 (39 numeric, 3 categorical) |
| Validation-selected model | Random Forest (140 trees) |
| Validation split | 139,174 fit / 36,167 validation, grouped by duplicate feature signature |
| Selected malicious-class threshold | 0.5306967 |
| Threshold policy | Maximize validation recall with false-positive rate at or below 5% |

The official UNSW project page describes these canonical train and test partition sizes ([UNSW-NB15 Dataset](https://research.unsw.edu.au/projects/unsw-nb15-dataset)). SHA-256 and byte-size pins in the code bind local files to the CSV objects at the recorded immutable mirror revision; the official page does not publish those hashes.

Threshold and model selection use validation data only. Random Forest achieved validation recall 0.9521, precision 0.9774, and false-positive rate 0.0500. Logistic Regression achieved recall 0.9036, precision 0.9762, and false-positive rate 0.0499. Random Forest was selected for higher recall within the same alert budget, then refit on all 175,341 official training rows. The official test split was not used to select the model or threshold.

## Held-out official test result

| Metric | Score |
|---|---:|
| Accuracy | 0.9082 |
| Balanced accuracy | 0.9014 |
| Precision (malicious) | 0.8774 |
| Recall (malicious) | 0.9685 |
| F1 (malicious) | 0.9207 |
| Average precision | 0.9887 |
| ROC-AUC | 0.9849 |
| False-positive rate | 0.1658 |
| Specificity | 0.8342 |

Support: 37,000 normal and 45,332 attack-labeled flows.

| Actual \\ Predicted | Normal | Malicious |
|---|---:|---:|
| Normal | 30,865 | 6,135 |
| Malicious | 1,426 | 43,906 |

Compared with the previous F1-selected threshold (9,611 false positives, 496 false negatives), this policy reduces held-out false positives by 3,476 (36.2%) and increases false negatives by 930. Held-out recall moves from 0.9891 to 0.9685. The validation false-positive budget is not a guarantee on the test split: its normal-flow score distribution yields a 16.6% test false-positive rate despite a 5% validation rate. This split shift is a material limitation, so operators should treat classifications as review signals rather than proof of an incident.

## Repeated-record sensitivity check

The official test partition includes 8,541 records (10.37%) whose complete 42-feature signature occurs in the training partition. To show the effect of exact feature-signature overlap, evaluation also reports test rows whose signatures do not occur in training.

| Novel-signature subset metric | Score |
|---|---:|
| Rows | 73,791 |
| Accuracy | 0.9032 |
| Balanced accuracy | 0.9008 |
| Precision (malicious) | 0.8653 |
| Recall (malicious) | 0.9631 |
| F1 (malicious) | 0.9116 |
| Average precision | 0.9851 |
| ROC-AUC | 0.9824 |
| False-positive rate | 0.1615 |
| Specificity | 0.8385 |

Confusion matrix, rows actual and columns predicted: `[[29,792, 5,736], [1,410, 36,853]]` for normal and malicious labels. Removing exact signature overlap does not simulate independent networks or future traffic.

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
- The official test split's false-positive rate (16.6%) is materially higher than the 5% validation budget, demonstrating that the validation target does not guarantee the same workload on shifted data.
- The test set contains repeated feature signatures; full and novel-signature metrics are disclosed.
- The model missed 1,426 attack-labeled flows and raised 6,135 false alerts on the full official test split at the selected threshold.
- `malicious_score` is an uncalibrated `predict_proba` value, not calibrated risk or attack confidence.
- Benchmark performance does not demonstrate generalization to other networks, unseen attack types, or future traffic.
- The trained artifact is not shipped with source; each local environment must download the dataset and train/evaluate before model endpoints become available.

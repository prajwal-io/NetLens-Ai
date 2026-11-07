# UNSW-NB15 model evaluation

## Result summary

The committed source code trains the model from the official UNSW-NB15 partition layout, distributed through a pinned public mirror. The trained model artifact and raw data are generated locally and are intentionally excluded from Git. The model version evaluated for this report is `netsight-rf-unsw-v1`.

| Item | Result |
|---|---:|
| Dataset | UNSW-NB15 |
| Official training rows | 175,341 |
| Official test rows | 82,332 |
| Input features | 42 (39 numeric, 3 categorical) |
| Validation-selected model | Random Forest (140 trees) |
| Validation split | 139,174 fit / 36,167 validation, grouped by duplicate feature signature |
| Selected malicious-class threshold | 0.3839078 |

Random Forest was selected using validation F1 (0.9691) over Logistic Regression (0.9581). The threshold was selected using validation data only. The chosen pipeline was then refit on all 175,341 official training rows. The official test split was not used for model or threshold selection.

## Held-out official test result

| Metric | Score |
|---|---:|
| Accuracy | 0.8772 |
| Balanced accuracy | 0.8647 |
| Precision (malicious) | 0.8235 |
| Recall (malicious) | 0.9891 |
| F1 (malicious) | 0.8987 |
| Average precision | 0.9887 |
| ROC-AUC | 0.9849 |

Support: 37,000 normal and 45,332 attack-labeled flows.

| Actual \\ Predicted | Normal | Malicious |
|---|---:|---:|
| Normal | 27,389 | 9,611 |
| Malicious | 496 | 44,836 |

This threshold favors finding attack-labeled records: it produces high recall, with a substantial false-positive count. The application displays the outcome as a review signal, not proof of malicious activity.

## Repeated-record sensitivity check

The official test partition includes 8,541 records (10.37%) whose complete 42-feature signature occurs in the training partition. To make this visible, evaluation also reports the subset with previously unseen feature signatures.

| Novel-signature subset metric | Score |
|---|---:|
| Rows | 73,791 |
| Accuracy | 0.8697 |
| Balanced accuracy | 0.8652 |
| Precision (malicious) | 0.8054 |
| Recall (malicious) | 0.9874 |
| F1 (malicious) | 0.8871 |
| Average precision | 0.9851 |
| ROC-AUC | 0.9824 |

Confusion matrix, rows actual and columns predicted: `[[26,400, 9,128], [484, 37,779]]` for labels normal and malicious. This check removes exact feature-signature overlap only; it is not a substitute for evaluation on independent networks or future traffic.

## Pipeline and reproducibility

1. Download from a pinned mirror revision, normalize its reversed CSV names by expected row counts, and store SHA-256 hashes.
2. Validate the binary target and exact feature schema. Exclude `id`, `label`, and `attack_cat` from input.
3. Fit numeric median imputation, categorical most-frequent imputation, and one-hot encoding within each candidate pipeline.
4. Make a seeded stratified validation split while keeping identical feature signatures together.
5. Compare Random Forest and Logistic Regression. Select by validation F1, then recall and precision; choose the positive threshold from the validation precision-recall curve.
6. Refit the selected preprocessing/model pipeline on all official training data.
7. Evaluate once on the untouched official test partition and record the result in model metadata.

From `backend/`, with the project Python environment active:

```powershell
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
```

The API accepts inference only when it can load a locally generated artifact with held-out evaluation metadata. For binary labels and hashes, see the [UNSW-NB15 source](https://research.unsw.edu.au/projects/unsw-nb15-dataset) and the local manifest created by the downloader.

## Limitations

- This result measures the UNSW-NB15 benchmark, not live or production network traffic.
- The test set contains repeated feature signatures; both full and novel-signature metrics are disclosed.
- The threshold is recall-oriented and yields 9,611 false positives on the full official test set.
- `malicious_score` is an uncalibrated `predict_proba` value, not a calibrated risk or attack confidence.
- Benchmark performance does not demonstrate generalization to other networks, unseen attack types, or traffic collected in the future.
- The trained artifact is not shipped with the source commit; each local environment must download the dataset and train/evaluate it before model endpoints become available.

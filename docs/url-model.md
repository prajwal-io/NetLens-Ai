# URL model notes

The URL Check Demo uses a compact logistic-regression model for URL lexical structure. It is separate from the Random Forest trained on UNSW-NB15 network flows: a URL string does not provide the 42 flow features required by that model.

## Training and split

The model was trained from the raw `URL`, `Domain`, and `label` columns of the [UCI PhiUSIIL Phishing URL Dataset](https://archive.ics.uci.edu/dataset/967/phiusil+phishing+url+dataset). Training recomputes the same 22 lexical features used at inference. The domain field is used only to keep domains grouped between train, validation, and test partitions. Website-derived fields, `FILENAME`, and labels are excluded from inference features. Dataset labels are mapped to phishing as the positive class.

The dataset is not stored in Git. Download and extract the CSV locally, then run from `backend/`:

```powershell
python -m ml.train_url ..\data\raw\phiusiil\unpacked\PhiUSIIL_Phishing_URL_Dataset.csv
```

The checked-in `backend/ml/models/netsight-url-lr-v1.json` contains the scaler, coefficients, threshold, dataset hash, split details, metrics, and limitations. The script selects a validation threshold that maximizes recall while keeping validation false-positive rate at or below 5%, then evaluates that frozen threshold on the untouched domain-grouped test partition.

## Recorded holdout results

| Metric | Test result |
| --- | ---: |
| Rows | 48,158 |
| Accuracy | 96.83% |
| Precision | 93.99% |
| Phishing recall | 99.14% |
| False-positive rate | 4.99% |
| ROC-AUC | 99.64% |

These are results on one academic dataset snapshot, not a guarantee for new campaigns, current websites, or another dataset. The model score is not calibrated as the probability of an incident. The separate live probe reports public DNS/HTTP reachability and redirect evidence only; it cannot prove that a site is safe. System DNS lookup timeouts are platform-controlled, which is acceptable for this low-volume demo but should be replaced with an async resolver before high-concurrency hosting. No external reputation feed is queried.

Dataset citation: Prasad and Chandra, “PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and incremental learning,” *Computers & Security*, 2024, DOI: [10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545). Dataset license: CC BY 4.0.

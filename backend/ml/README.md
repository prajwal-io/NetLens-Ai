# UNSW-NB15 model pipeline

The pipeline verifies the pinned benchmark split bytes, compares Random Forest with Logistic Regression, selects a positive-class threshold on validation data, refits the selected pipeline on the official training partition, and evaluates it on the untouched official test partition. No prediction is generated when the evaluated artifact is unavailable.

## Set up and run

Use Python 3.12. From `backend/` with the project virtual environment active, install the checked-in exact dependency set:

```powershell
python -m pip install -r requirements.lock.txt
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

With the API running, run `python scripts/check_setup.py` from `backend/`. It checks the health endpoint and fails if the evaluated model is not loaded.

The downloader stages both splits outside the active dataset folder. It checks expected byte sizes, canonical row counts, the required feature header, and SHA-256 values pinned to the exact mirror commit before replacing either active split or the manifest. If one download or check fails, the current dataset remains in place. The mirror reverses the source filenames, so the pinned digest and row count also verify each split's role. Dataset contents are not tracked by Git.

Training accepts `--data-dir` and `--artifact` for controlled local runs, but still enforces the pinned official split contract. Evaluation uses the same `--data-dir`, checks both dataset hashes against the trained artifact, and updates the JSON sidecar only after evaluation. Inference requests are capped at 10,000 rows and execute parsing and prediction in a worker thread. Model artifacts are local generated files; regenerate them after changing data, code, or dependencies.

## Dataset, labels, and feature contract

Source: [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset). Its official page permits academic research use with citation of the original publications; commercial use requires author agreement. The local mirror and exact revision are recorded in the dataset manifest and model metadata.

The goal is binary classification: `label=0` is normal and `label=1` is an attack-labeled benchmark flow. The application displays the positive class as **malicious** to prompt review. That label is not proof of malicious activity.

Schema `unsw-nb15-flow-v1` contains 42 inputs: 39 numeric features and three categorical features (`proto`, `service`, `state`). The direct record identifier `id`, target `label`, and descriptive `attack_cat` are excluded from all model inputs. Additional CSV columns are ignored by validation and inference.

## Preprocessing and evaluation safeguards

- Numeric missing values are imputed with training-fitted medians; categorical missing values use the most frequent training category.
- Categorical columns are one-hot encoded with unseen categories ignored.
- Input columns are validated by name and passed in a fixed order.
- Validation is a deterministic, stratified 80/20 split inside the official training partition. Identical 42-feature signatures are grouped so a signature cannot appear in both fit and validation partitions.
- Random Forest and Logistic Regression are compared on validation data. To constrain analyst alert volume directly, each model's threshold maximizes malicious recall subject to a validation false-positive rate no higher than 5%; the untouched test partition is used only to report the resulting tradeoff. Precision is also reported because it depends on class prevalence and may change between splits.
- The chosen pipeline is refitted using all 175,341 official training rows.
- The 82,332-row official test split is used once for evaluation. Metadata also reports a sensitivity check excluding test records whose feature signature occurs in training; this makes repeated-flow overlap visible.
- Metrics include accuracy, balanced accuracy, precision, recall, F1, average precision, ROC-AUC, support, and confusion matrices.

See [`docs/model-evaluation.md`](../../docs/model-evaluation.md) for measured results and interpretation. The benchmark is controlled and does not establish performance on other networks or live traffic.

Training stages `backend/ml/artifacts/netsight-candidate.joblib` by default. The default evaluation command publishes it to `netsight-model.joblib` only after successful held-out evaluation. The active API model stays intact if evaluation fails. Restart FastAPI after publication. With a custom `--artifact`, evaluation updates that experiment artifact only unless `--publish-to` is supplied.

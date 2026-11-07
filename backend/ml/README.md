# UNSW-NB15 model pipeline

The pipeline validates the benchmark splits, compares Random Forest with Logistic Regression, selects a positive-class threshold on validation data, refits the selected pipeline on the official training partition, and evaluates it on the untouched official test partition. No prediction is generated when the evaluated artifact is unavailable.

## Set up and run

From `backend/` with the project virtual environment active:

```powershell
python -m pip install -r requirements.txt
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The downloader writes the two normalized CSV splits and a hash manifest under `../data/raw/unsw-nb15/`. It pins a public mirror commit and checks the canonical split row counts because that mirror reverses the names of the source files. Dataset contents are not tracked by Git.

Training accepts `--data-dir` and `--artifact` for controlled local runs. Evaluation uses the same `--data-dir`, checks both dataset hashes against the trained artifact, and updates the JSON sidecar only after evaluation. The API loads artifacts with the feature contract and completed evaluation metadata. Model artifacts are local generated files; regenerate them after changing data, code, or dependencies.

## Dataset, labels, and feature contract

Source: [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset). Its official page permits academic research use with citation of the original publications; commercial use requires author agreement. The local mirror and exact revision are recorded in the dataset manifest and model metadata.

The goal is binary classification: `label=0` is normal and `label=1` is an attack-labeled benchmark flow. The application displays the positive class as **malicious** to prompt review. That label is not proof of malicious activity.

Schema `unsw-nb15-flow-v1` contains 42 inputs: 39 numeric features and three categorical features (`proto`, `service`, `state`). The direct record identifier `id`, target `label`, and descriptive `attack_cat` are excluded from all model inputs. Additional CSV columns are ignored by validation and inference.

## Preprocessing and evaluation safeguards

- Numeric missing values are imputed with training-fitted medians; categorical missing values use the most frequent training category.
- Categorical columns are one-hot encoded with unseen categories ignored.
- Input columns are validated by name and passed in a fixed order.
- Validation is a deterministic, stratified 80/20 split inside the official training partition. Identical 42-feature signatures are grouped so a signature cannot appear in both fit and validation partitions.
- Random Forest and Logistic Regression are compared on validation data. F1 ranks candidates, with recall and precision as tie-breakers. The positive-class threshold is selected on validation only.
- The chosen pipeline is refitted using all 175,341 official training rows.
- The 82,332-row official test split is used once for evaluation. Metadata also reports a sensitivity check excluding test records whose feature signature occurs in training; this makes repeated-flow overlap visible.
- Metrics include accuracy, balanced accuracy, precision, recall, F1, average precision, ROC-AUC, support, and confusion matrices.

See [`docs/model-evaluation.md`](../../docs/model-evaluation.md) for measured results and interpretation. The benchmark is controlled and does not establish performance on other networks or live traffic.

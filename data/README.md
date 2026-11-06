# Network data

`samples/valid-flows.csv` is a small synthetic fixture for exercising the compatible numeric network-metrics input schema. It is not training data or an ML result.

The selected Kaggle dataset is downloaded on demand to `kagglehub-cache/` by `python -m ml.download_dataset` from `backend/`. That directory is ignored by Git; raw dataset files are not committed. See [the model pipeline notes](../backend/ml/README.md) for its feature contract, label meaning, evaluation protocol, and attribution reminder.

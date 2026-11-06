"""Evaluate the fitted model once on the untouched final chronological segment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from ml.dataset import load_training_frame
from ml.train import ARTIFACT_PATH, atomic_save, chronological_boundaries, sha256_file


def evaluate(data_path: Path | None = None, artifact_path: Path = ARTIFACT_PATH) -> dict[str, Any]:
    features, labels, timestamps, source = load_training_frame(data_path)
    artifact = joblib.load(artifact_path)
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Model artifact has no training metadata; run `python -m ml.train` first.")
    if metadata.get("dataset", {}).get("sha256") != sha256_file(source):
        raise ValueError("Evaluation data differs from the dataset used to train this artifact.")

    _, test_start = chronological_boundaries(len(labels))
    actual = labels.iloc[test_start:].to_numpy()
    if np.unique(actual).size < 2:
        raise ValueError("The final test period must contain normal and anomalous records.")
    probabilities = artifact["pipeline"].predict_proba(features.iloc[test_start:])[:, 1]
    threshold = float(artifact["threshold"])
    predicted = (probabilities >= threshold).astype("int64")
    matrix = confusion_matrix(actual, predicted, labels=[0, 1])
    metrics = {
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "support": {"normal": int((actual == 0).sum()), "anomalous": int((actual == 1).sum())},
        "confusion_matrix": {
            "labels": ["normal", "anomalous"],
            "rows_actual_columns_predicted": matrix.tolist(),
        },
    }
    metadata["evaluation"] = {
        "split": "untouched final 20% chronological holdout",
        "rows": int(len(actual)),
        "start": timestamps.iloc[test_start].isoformat(),
        "end": timestamps.iloc[-1].isoformat(),
        "metrics": metrics,
    }
    metadata["evaluation_warning"] = (
        "Held-out anomalous recall is below 0.50 on this small dataset; treat predictions as experimental."
        if metrics["recall"] < 0.5
        else None
    )
    artifact["metadata"] = metadata
    atomic_save(artifact, artifact_path, metadata)
    print(json.dumps({"model_version": metadata["model_version"], "evaluation": metadata["evaluation"], "warning": metadata["evaluation_warning"]}, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None, help="Labeled CSV path used during training.")
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH, help="Trained joblib artifact path.")
    args = parser.parse_args()
    evaluate(args.data, args.artifact)


if __name__ == "__main__":
    main()

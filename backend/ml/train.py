"""Train candidate classifiers without touching the chronological test set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.dataset import PROJECT_ROOT, latest_labeled_csv, load_training_frame
from ml.schema import DATASET_SLUG, FEATURE_COLUMNS, TARGET_COLUMN


ARTIFACT_PATH = PROJECT_ROOT / "backend" / "ml" / "artifacts" / "netsight-model.joblib"
INFO_PATH = ARTIFACT_PATH.with_suffix(".json")
TRAIN_END = 0.60
VALIDATION_END = 0.80
THRESHOLDS = tuple(float(value) for value in np.arange(0.05, 1.0, 0.05))


def candidate_models() -> dict[str, Pipeline]:
    return {
        "Random Forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=2,
                        class_weight="balanced_subsample",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "Logistic Regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def binary_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(np.mean(actual == predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
    }


def choose_threshold(actual: np.ndarray, probabilities: np.ndarray) -> tuple[float, dict[str, float]]:
    options: list[tuple[tuple[float, float, float], float, dict[str, float]]] = []
    for threshold in THRESHOLDS:
        predicted = (probabilities >= threshold).astype("int64")
        metrics = binary_metrics(actual, predicted)
        # Prefer validation F1, then anomaly recall, then the threshold nearest
        # 0.5. The future test segment is not used for this choice.
        rank = (metrics["f1"], metrics["recall"], -abs(threshold - 0.5))
        options.append((rank, threshold, metrics))
    _, threshold, metrics = max(options, key=lambda item: item[0])
    return threshold, metrics


def chronological_boundaries(rows: int) -> tuple[int, int]:
    train_end = int(rows * TRAIN_END)
    validation_end = int(rows * VALIDATION_END)
    if train_end < 2 or validation_end <= train_end or rows - validation_end < 1:
        raise ValueError("Dataset is too small for the chronological 60/20/20 split.")
    return train_end, validation_end


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_save(artifact: dict[str, Any], artifact_path: Path, info: dict[str, Any]) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = artifact_path.with_suffix(artifact_path.suffix + ".tmp")
    try:
        joblib.dump(artifact, temporary)
        temporary.replace(artifact_path)
        info_path = artifact_path.with_suffix(".json")
        info_temp = info_path.with_suffix(info_path.suffix + ".tmp")
        info_temp.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        info_temp.replace(info_path)
    finally:
        temporary.unlink(missing_ok=True)


def train(data_path: Path | None = None, artifact_path: Path = ARTIFACT_PATH) -> dict[str, Any]:
    features, labels, timestamps, source = load_training_frame(data_path)
    train_end, validation_end = chronological_boundaries(len(labels))
    train_labels = labels.iloc[:train_end].to_numpy()
    validation_labels = labels.iloc[train_end:validation_end].to_numpy()
    if np.unique(train_labels).size < 2 or np.unique(validation_labels).size < 2:
        raise ValueError("Training and validation periods must each contain both classes.")

    validation_results: dict[str, dict[str, Any]] = {}
    trained_candidates: dict[str, Pipeline] = {}
    for name, pipeline in candidate_models().items():
        pipeline.fit(features.iloc[:train_end], train_labels)
        probabilities = pipeline.predict_proba(features.iloc[train_end:validation_end])[:, 1]
        threshold, metrics = choose_threshold(validation_labels, probabilities)
        validation_results[name] = {"threshold": threshold, "metrics": metrics}
        trained_candidates[name] = pipeline

    selected_name = max(
        validation_results,
        key=lambda name: (
            validation_results[name]["metrics"]["f1"],
            validation_results[name]["metrics"]["recall"],
            validation_results[name]["metrics"]["precision"],
            name == "Random Forest",
        ),
    )
    threshold = float(validation_results[selected_name]["threshold"])
    selected = candidate_models()[selected_name]
    selected.fit(features.iloc[:validation_end], labels.iloc[:validation_end].to_numpy())

    version_suffix = "rf" if selected_name == "Random Forest" else "lr"
    model_version = f"netsight-{version_suffix}-v1"
    validation_counts = labels.iloc[train_end:validation_end].value_counts().to_dict()
    training_counts = labels.iloc[:validation_end].value_counts().to_dict()
    info: dict[str, Any] = {
        "model_name": selected_name,
        "model_version": model_version,
        "algorithm": selected_name,
        "dataset": {
            "name": "Network Anomaly Dataset",
            "source": f"https://www.kaggle.com/datasets/{DATASET_SLUG}",
            "slug": DATASET_SLUG,
            "labeled_file": source.name,
            "rows": int(len(labels)),
            "sha256": sha256_file(source),
        },
        "target": {
            "column": TARGET_COLUMN,
            "normal_value": 0,
            "anomalous_value": 1,
            "meaning": "network performance anomaly; not an intrusion or malware label",
        },
        "features": list(FEATURE_COLUMNS),
        "feature_count": len(FEATURE_COLUMNS),
        "decision_threshold": threshold,
        "score_definition": "predict_proba for class 1; an uncalibrated anomaly score, not an attack confidence",
        "split": {
            "strategy": "chronological 60% train / 20% validation / 20% test",
            "train_rows": int(train_end),
            "validation_rows": int(validation_end - train_end),
            "test_rows": int(len(labels) - validation_end),
            "fitted_rows": int(validation_end),
            "train_start": timestamps.iloc[0].isoformat(),
            "validation_start": timestamps.iloc[train_end].isoformat(),
            "test_start": timestamps.iloc[validation_end].isoformat(),
            "test_end": timestamps.iloc[-1].isoformat(),
        },
        "class_counts": {
            "train_plus_validation": {
                "normal": int(training_counts.get(0, 0)),
                "anomalous": int(training_counts.get(1, 0)),
            },
            "validation": {
                "normal": int(validation_counts.get(0, 0)),
                "anomalous": int(validation_counts.get(1, 0)),
            },
        },
        "validation_candidates": validation_results,
        "evaluation": None,
        "limitations": [
            "The dataset is a small, single-day network telemetry sample.",
            "The anomaly label describes network performance, not malicious traffic.",
            "Auxiliary anomaly_* columns, timestamps, and target-like categorical fields are excluded from model inputs.",
            "The estimated anomaly score is not calibrated and is not proof of an incident.",
        ],
    }
    artifact = {
        "format_version": 1,
        "pipeline": selected,
        "features": list(FEATURE_COLUMNS),
        "threshold": threshold,
        "metadata": info,
    }
    atomic_save(artifact, artifact_path, info)
    print(f"Selected {selected_name} using validation F1={validation_results[selected_name]['metrics']['f1']:.3f}.")
    print(f"Validation threshold: {threshold:.2f}. Future test rows were not used for model selection.")
    print(f"Training artifact saved to {artifact_path.resolve()}")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None, help="Labeled CSV path (defaults to latest KaggleHub download).")
    parser.add_argument("--artifact", type=Path, default=ARTIFACT_PATH, help="Output joblib artifact path.")
    args = parser.parse_args()
    train(args.data, args.artifact)


if __name__ == "__main__":
    main()

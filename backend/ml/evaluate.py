"""Evaluate the fitted classifier on UNSW-NB15's untouched official test split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from ml.dataset import DATASET_ROOT, OFFICIAL_SPLIT_EXPECTATIONS, SplitExpectation, load_dataset
from ml.full_unsw import DEFAULT_MAX_TRAIN_ROWS, FULL_DATASET_ROOT, load_full_unsw_training
from ml.schema import FEATURE_COLUMNS
from ml.train import ARTIFACT_PATH, CANDIDATE_ARTIFACT_PATH, atomic_save, classification_metrics, sha256_file


def evaluate(
    data_dir: Path | None = None,
    artifact_path: Path = CANDIDATE_ARTIFACT_PATH,
    *,
    expected_splits: Mapping[str, SplitExpectation] = OFFICIAL_SPLIT_EXPECTATIONS,
    publish_path: Path | None = None,
    full_unsw_data_dir: Path = FULL_DATASET_ROOT,
) -> dict[str, Any]:
    dataset = load_dataset(data_dir, expected_splits=expected_splits)
    artifact = joblib.load(artifact_path)
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Model artifact has no training metadata; run `python -m ml.train` first.")
    dataset_metadata = metadata.get("dataset", {})
    if dataset_metadata.get("training_sha256") != sha256_file(dataset.training_path):
        raise ValueError("Training CSV differs from the dataset used to fit this model.")
    if dataset_metadata.get("test_sha256") != sha256_file(dataset.test_path):
        raise ValueError("Official test CSV differs from the dataset used to train this model.")

    if tuple(artifact.get("features", ())) != FEATURE_COLUMNS:
        raise ValueError("Model artifact feature order does not match UNSW-NB15 flow schema v1.")
    pipeline = artifact.get("pipeline")
    threshold = float(artifact.get("threshold", -1))
    if not callable(getattr(pipeline, "predict_proba", None)) or not 0 <= threshold <= 1:
        raise ValueError("Model artifact is missing a valid probability pipeline or threshold.")
    class_order = list(pipeline.classes_)
    if 0 not in class_order or 1 not in class_order:
        raise ValueError("Model artifact does not include both normal and malicious classes.")
    scores = np.asarray(pipeline.predict_proba(dataset.test_features.loc[:, FEATURE_COLUMNS])[:, class_order.index(1)])
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Model returned non-finite or out-of-range malicious scores.")
    actual = dataset.test_labels.to_numpy()
    predicted = (scores >= threshold).astype("int64")

    def report(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, Any]:
        y_pred = (y_score >= threshold).astype("int64")
        matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
        metrics = classification_metrics(y_true, y_pred, y_score)
        metrics["support"] = {
            "normal": int((y_true == 0).sum()),
            "malicious": int((y_true == 1).sum()),
        }
        metrics["confusion_matrix"] = {
            "labels": ["normal", "malicious"],
            "rows_actual_columns_predicted": matrix.tolist(),
        }
        return metrics

    evaluation_training_features = dataset.training_features
    supplemental = dataset_metadata.get("supplemental_training")
    if isinstance(supplemental, dict):
        max_rows = int(supplemental.get("max_rows", DEFAULT_MAX_TRAIN_ROWS))
        extra_features, _, extra_stats = load_full_unsw_training(
            full_unsw_data_dir,
            heldout_test_features=dataset.test_features,
            max_rows=max_rows,
        )
        if extra_stats.get("file_hashes") != supplemental.get("file_hashes"):
            raise ValueError("Supplemental UNSW-NB15 files differ from the dataset used to train this model.")
        if extra_stats.get("rows_used") != supplemental.get("rows_used"):
            raise ValueError("Supplemental UNSW-NB15 sampling no longer matches the trained model metadata.")
        evaluation_training_features = pd.concat([evaluation_training_features, extra_features], ignore_index=True)

    all_signature_hashes = pd.util.hash_pandas_object(evaluation_training_features.loc[:, FEATURE_COLUMNS], index=False)
    test_signature_hashes = pd.util.hash_pandas_object(dataset.test_features.loc[:, FEATURE_COLUMNS], index=False)
    training_hashes = set(all_signature_hashes.tolist())
    overlap_mask = test_signature_hashes.isin(training_hashes).to_numpy()
    novel_mask = ~overlap_mask
    if np.unique(actual[novel_mask]).size == 2:
        novel_report = report(actual[novel_mask], scores[novel_mask])
    else:
        novel_report = None

    metadata["evaluation"] = {
        "split": "untouched official UNSW-NB15 test partition",
        "rows": int(len(actual)),
        "threshold": threshold,
        "metrics": report(actual, scores),
        "repeated_feature_signature_rows": int(overlap_mask.sum()),
        "repeated_feature_signature_rate": float(overlap_mask.mean()),
        "novel_feature_signature_evaluation": {
            "rows": int(novel_mask.sum()),
            "metrics": novel_report,
            "definition": "test rows whose 42 input-feature signature does not occur in the selected training pool",
        },
    }
    test_fpr = metadata["evaluation"]["metrics"]["false_positive_rate"]
    validation_fpr_limit = float(metadata.get("threshold_policy", {}).get("maximum_validation_false_positive_rate", 0.05))
    warnings = []
    if novel_report and novel_report["recall"] < 0.5:
        warnings.append("The novelty-aware test subset has low malicious recall.")
    if test_fpr > validation_fpr_limit:
        warnings.append(
            f"Official test false-positive rate ({test_fpr:.1%}) exceeds the validation target ({validation_fpr_limit:.1%}); the validation target is not a guarantee on shifted data."
        )
    if overlap_mask.any():
        warnings.append("Test results include repeated feature signatures from the selected training pool; review the novelty-aware result before interpreting generalization.")
    metadata["evaluation_warning"] = " ".join(warnings) or None
    artifact["metadata"] = metadata
    atomic_save(artifact, artifact_path, metadata)
    if publish_path is not None and publish_path.resolve() != artifact_path.resolve():
        atomic_save(artifact, publish_path, metadata)
    summary = {
        "model_version": metadata["model_version"],
        "selected_threshold": threshold,
        "official_test": metadata["evaluation"]["metrics"],
        "novel_feature_signatures": metadata["evaluation"]["novel_feature_signature_evaluation"],
        "warning": metadata["evaluation_warning"],
        "artifact": str(artifact_path.resolve()),
    }
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None, help="Directory containing normalized training.csv and testing.csv.")
    parser.add_argument("--artifact", type=Path, default=CANDIDATE_ARTIFACT_PATH, help="Candidate joblib artifact path.")
    parser.add_argument("--publish-to", type=Path, default=None, help="Install the evaluated pipeline at this path. The default candidate publishes to the API's active path.")
    parser.add_argument("--full-unsw-data-dir", type=Path, default=FULL_DATASET_ROOT, help="Directory containing the four checksum-pinned full-corpus CSVs when the candidate used them.")
    args = parser.parse_args()
    publish_path = args.publish_to
    if publish_path is None and args.artifact.resolve() == CANDIDATE_ARTIFACT_PATH.resolve():
        publish_path = ARTIFACT_PATH
    evaluate(args.data_dir, args.artifact, publish_path=publish_path, full_unsw_data_dir=args.full_unsw_data_dir)


if __name__ == "__main__":
    main()

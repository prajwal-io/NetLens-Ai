"""Compare supervised intrusion classifiers on UNSW-NB15 training data only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.dataset import DATASET_ROOT, Dataset, OFFICIAL_SPLIT_EXPECTATIONS, SplitExpectation, load_dataset
from ml.full_unsw import DEFAULT_MAX_TRAIN_ROWS, FULL_DATASET_ROOT, load_full_unsw_training
from ml.schema import (
    CATEGORICAL_FEATURES,
    DATASET_LICENSE,
    DATASET_NAME,
    DATASET_SOURCE,
    FEATURE_COLUMNS,
    ID_COLUMN,
    LABEL_CONTEXT_COLUMN,
    MALICIOUS_LABEL,
    MIRROR_COMMIT,
    MIRROR_SOURCE,
    NORMAL_LABEL,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)


ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "netsight-model.joblib"
CANDIDATE_ARTIFACT_PATH = ARTIFACT_PATH.with_name("netsight-candidate.joblib")
FIT_SEED = 42
VALIDATION_SIZE = 0.20
MAX_VALIDATION_FALSE_POSITIVE_RATE = 0.05


def make_preprocessor(scale_numeric: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))
    ]
    if scale_numeric:
        numeric_steps.append(("scale", StandardScaler()))
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), list(NUMERIC_FEATURES)),
            ("categorical", categorical_pipeline, list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def candidate_models(*, forest_trees: int = 140, extra_trees: int = 180) -> dict[str, Pipeline]:
    """Candidates share fitted preprocessing and use imbalance-aware weights."""
    return {
        "Random Forest": Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=False)),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=forest_trees,
                        max_depth=20,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        class_weight="balanced_subsample",
                        random_state=FIT_SEED,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "Extra Trees": Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=False)),
                (
                    "classifier",
                    ExtraTreesClassifier(
                        n_estimators=extra_trees,
                        max_depth=20,
                        min_samples_leaf=2,
                        max_features="sqrt",
                        class_weight="balanced",
                        random_state=FIT_SEED,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "Logistic Regression": Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=True)),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=400,
                        solver="liblinear",
                        random_state=FIT_SEED,
                    ),
                ),
            ]
        ),
    }


def classification_metrics(actual: np.ndarray, predicted: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    normal_rows = actual == 0
    malicious_rows = actual == 1
    false_positives = int(np.logical_and(normal_rows, predicted == 1).sum())
    true_negatives = int(np.logical_and(normal_rows, predicted == 0).sum())
    false_positive_rate = false_positives / max(false_positives + true_negatives, 1)
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "average_precision": float(average_precision_score(actual, scores)),
        "roc_auc": float(roc_auc_score(actual, scores)),
        "false_positive_rate": float(false_positive_rate),
        "specificity": float(1 - false_positive_rate),
    }


def choose_threshold(
    actual: np.ndarray,
    scores: np.ndarray,
    *,
    maximum_false_positive_rate: float = MAX_VALIDATION_FALSE_POSITIVE_RATE,
) -> tuple[float, dict[str, float]]:
    """Maximize malicious recall while meeting the validation false-positive budget."""
    actual = np.asarray(actual, dtype="int64")
    scores = np.asarray(scores, dtype="float64")
    if not 0 <= maximum_false_positive_rate < 1:
        raise ValueError("maximum_false_positive_rate must be at least 0 and less than 1.")
    if actual.ndim != 1 or scores.ndim != 1 or actual.size != scores.size or actual.size == 0:
        raise ValueError("Validation labels and scores must be non-empty one-dimensional arrays of equal length.")
    if set(np.unique(actual).tolist()) != {0, 1}:
        raise ValueError("Validation data must contain both binary classes 0 and 1.")
    if not np.isfinite(scores).all() or (scores < 0).any() or (scores > 1).any():
        raise ValueError("Validation scores must be finite probabilities between 0 and 1.")

    false_positive_rates, recalls, thresholds = roc_curve(actual, scores, drop_intermediate=False)
    finite_thresholds = np.isfinite(thresholds)
    eligible = np.flatnonzero(finite_thresholds & (false_positive_rates <= maximum_false_positive_rate))
    if eligible.size == 0:
        best_fpr = float(np.min(false_positive_rates[finite_thresholds]))
        raise ValueError(
            f"No validation threshold met the {maximum_false_positive_rate:.1%} false-positive-rate target "
            f"(best available false-positive rate: {best_fpr:.3f})."
        )
    # Within the alert budget, maximize recall; prefer fewer false alerts, then a
    # higher threshold when the recall is tied.
    best_index = max(
        eligible,
        key=lambda index: (recalls[index], -false_positive_rates[index], thresholds[index]),
    )
    threshold = float(thresholds[best_index])
    predicted = (scores >= threshold).astype("int64")
    return threshold, classification_metrics(actual, predicted, scores)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_save(artifact: dict[str, Any], artifact_path: Path, info: dict[str, Any]) -> None:
    # Validate metadata before replacing the authoritative pipeline artifact.
    serialized_info = json.dumps(info, indent=2, allow_nan=False) + "\n"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = artifact_path.with_suffix(artifact_path.suffix + ".tmp")
    try:
        joblib.dump(artifact, temporary, compress=3)
        temporary.replace(artifact_path)
        info_path = artifact_path.with_suffix(".json")
        info_temp = info_path.with_suffix(info_path.suffix + ".tmp")
        info_temp.write_text(serialized_info, encoding="utf-8")
        info_temp.replace(info_path)
    finally:
        temporary.unlink(missing_ok=True)


def _grouped_validation_indices(features: pd.DataFrame, labels: pd.Series) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Keep identical feature signatures together when making validation split."""
    signatures = pd.util.hash_pandas_object(features.loc[:, FEATURE_COLUMNS], index=False).to_numpy()
    signature_labels: dict[int, list[int]] = {}
    for signature, label in zip(signatures.tolist(), labels.tolist()):
        signature_labels.setdefault(signature, []).append(int(label))
    unique_signatures = np.asarray(list(signature_labels), dtype="uint64")
    majority_labels = np.asarray(
        [int(np.mean(signature_labels[int(signature)]) >= 0.5) for signature in unique_signatures],
        dtype="int64",
    )
    train_groups, validation_groups = train_test_split(
        unique_signatures,
        test_size=VALIDATION_SIZE,
        random_state=FIT_SEED,
        stratify=majority_labels,
    )
    train_membership = np.isin(signatures, train_groups)
    validation_membership = np.isin(signatures, validation_groups)
    conflicts = sum(len(set(values)) > 1 for values in signature_labels.values())
    return np.flatnonzero(train_membership), np.flatnonzero(validation_membership), {
        "unique_feature_signatures": int(len(unique_signatures)),
        "repeated_feature_signatures": int(len(signatures) - len(unique_signatures)),
        "conflicting_feature_signatures": int(conflicts),
    }


def _source_anchored_validation_indices(
    official_features: pd.DataFrame,
    official_labels: pd.Series,
    pooled_features: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Validate on official-source rows and exclude their signatures from pooled fit data."""
    _, official_validation_indices, stats = _grouped_validation_indices(official_features, official_labels)
    official_signatures = pd.util.hash_pandas_object(official_features.loc[:, FEATURE_COLUMNS], index=False).to_numpy()
    pooled_signatures = pd.util.hash_pandas_object(pooled_features.loc[:, FEATURE_COLUMNS], index=False).to_numpy()
    validation_signatures = np.unique(official_signatures[official_validation_indices])
    validation_group_mask = np.isin(pooled_signatures, validation_signatures)
    official_membership = np.zeros(len(pooled_features), dtype=bool)
    official_membership[: len(official_features)] = True
    validation_membership = validation_group_mask & official_membership
    fit_membership = ~validation_group_mask
    stats["supplemental_validation_signature_rows_excluded_from_fit"] = int(
        (validation_group_mask & ~official_membership).sum()
    )
    return np.flatnonzero(fit_membership), np.flatnonzero(validation_membership), stats


def train(
    data_dir: Path | None = None,
    artifact_path: Path = CANDIDATE_ARTIFACT_PATH,
    *,
    expected_splits: Mapping[str, SplitExpectation] = OFFICIAL_SPLIT_EXPECTATIONS,
    include_full_unsw: bool = False,
    full_unsw_data_dir: Path = FULL_DATASET_ROOT,
    full_unsw_max_rows: int = DEFAULT_MAX_TRAIN_ROWS,
) -> dict[str, Any]:
    dataset: Dataset = load_dataset(data_dir, expected_splits=expected_splits)
    training_features = dataset.training_features.copy()
    training_labels = dataset.training_labels.copy()
    supplemental_stats: dict[str, Any] | None = None
    if include_full_unsw:
        supplemental_features, supplemental_labels, supplemental_stats = load_full_unsw_training(
            full_unsw_data_dir,
            heldout_test_features=dataset.test_features,
            max_rows=full_unsw_max_rows,
        )
        training_features = pd.concat([training_features, supplemental_features], ignore_index=True)
        training_labels = pd.concat([training_labels, supplemental_labels], ignore_index=True)

    if supplemental_stats:
        train_indices, validation_indices, signature_stats = _source_anchored_validation_indices(
            dataset.training_features,
            dataset.training_labels,
            training_features,
        )
    else:
        train_indices, validation_indices, signature_stats = _grouped_validation_indices(
            training_features, training_labels
        )
    fit_features = training_features.iloc[train_indices]
    fit_labels = training_labels.iloc[train_indices].to_numpy()
    validation_features = training_features.iloc[validation_indices]
    validation_labels = training_labels.iloc[validation_indices].to_numpy()
    if np.unique(fit_labels).size != 2 or np.unique(validation_labels).size != 2:
        raise ValueError("Training and validation partitions must each contain normal and malicious records.")

    print(
        f"UNSW-NB15: {len(dataset.training_labels):,} official training rows; "
        f"{len(training_features) - len(dataset.training_labels):,} additional training rows; "
        f"{len(dataset.test_labels):,} separate test rows.",
        flush=True,
    )
    print(
        f"Split by feature signature: fit={len(train_indices):,}, validation={len(validation_indices):,}; "
        f"{signature_stats['repeated_feature_signatures']:,} repeated signatures kept together.",
        flush=True,
    )
    print(f"Feature contract: {len(NUMERIC_FEATURES)} numeric + {len(CATEGORICAL_FEATURES)} categorical; identifiers and attack categories excluded.", flush=True)
    if supplemental_stats:
        print(
            f"Full-corpus filter: removed {supplemental_stats['duplicate_boundary_rows_removed']:,} exact adjacent-file duplicate records and "
            f"{supplemental_stats['rows_matching_heldout_test_removed']:,} held-out feature matches; "
            f"sampled {supplemental_stats['rows_used']:,} of {supplemental_stats['eligible_rows_after_test_filter']:,} eligible rows.",
            flush=True,
        )

    validation_results: dict[str, dict[str, Any]] = {}
    for name, pipeline in candidate_models().items():
        print(f"Fitting {name}...", flush=True)
        pipeline.fit(fit_features, fit_labels)
        probabilities = pipeline.predict_proba(validation_features)[:, list(pipeline.classes_).index(1)]
        threshold, metrics = choose_threshold(validation_labels, probabilities)
        validation_results[name] = {"threshold": threshold, "metrics": metrics}
        print(
            f"{name}: validation FPR={metrics['false_positive_rate']:.3f}, recall={metrics['recall']:.3f}, "
            f"precision={metrics['precision']:.3f}, threshold={threshold:.3f}.",
            flush=True,
        )

    selected_name = max(
        validation_results,
        key=lambda name: (
            validation_results[name]["metrics"]["recall"],
            -validation_results[name]["metrics"]["false_positive_rate"],
            validation_results[name]["metrics"]["precision"],
            validation_results[name]["metrics"]["f1"],
            name == "Random Forest",
        ),
    )
    threshold = float(validation_results[selected_name]["threshold"])
    print(f"Refitting selected candidate ({selected_name}) on all {len(training_features):,} selected training rows...", flush=True)
    selected = candidate_models()[selected_name]
    selected.fit(training_features, training_labels.to_numpy())

    version_suffix = {"Random Forest": "rf", "Extra Trees": "et", "Logistic Regression": "lr"}[selected_name]
    corpus_suffix = "-full" if supplemental_stats else ""
    model_version = f"netsight-{version_suffix}-unsw{corpus_suffix}-v4"
    fit_counts = training_labels.value_counts().to_dict()
    train_class_counts = training_labels.iloc[train_indices].value_counts().to_dict()
    validation_class_counts = training_labels.iloc[validation_indices].value_counts().to_dict()
    info: dict[str, Any] = {
        "model_name": selected_name,
        "model_version": model_version,
        "algorithm": selected_name,
        "dataset": {
            "name": DATASET_NAME,
            "source": DATASET_SOURCE,
            "mirror": MIRROR_SOURCE,
            "mirror_commit": MIRROR_COMMIT,
            "license": DATASET_LICENSE,
            "rows": int(len(training_labels) + len(dataset.test_labels)),
            "training_rows": int(len(training_labels)),
            "official_training_rows": int(len(dataset.training_labels)),
            "supplemental_training_rows": int(len(training_labels) - len(dataset.training_labels)),
            "supplemental_training": supplemental_stats,
            "test_rows": int(len(dataset.test_labels)),
            "training_file": dataset.training_path.name,
            "test_file": dataset.test_path.name,
            "training_sha256": sha256_file(dataset.training_path),
            "test_sha256": sha256_file(dataset.test_path),
        },
        "target": {
            "column": TARGET_COLUMN,
            "normal_value": 0,
            "malicious_value": 1,
            "meaning": "UNSW-NB15 benchmark label: 0 normal, 1 attack; a benchmark prediction is not proof of malicious activity.",
            "context_column_excluded": LABEL_CONTEXT_COLUMN,
        },
        "features": list(FEATURE_COLUMNS),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "feature_count": len(FEATURE_COLUMNS),
        "feature_count_numeric": len(NUMERIC_FEATURES),
        "feature_count_categorical": len(CATEGORICAL_FEATURES),
        "excluded_columns": [ID_COLUMN, LABEL_CONTEXT_COLUMN, TARGET_COLUMN],
        "decision_threshold": threshold,
        "threshold_policy": {
            "objective": "maximize malicious recall subject to the maximum validation false-positive-rate budget",
            "maximum_validation_false_positive_rate": MAX_VALIDATION_FALSE_POSITIVE_RATE,
            "selected_validation_false_positive_rate": validation_results[selected_name]["metrics"]["false_positive_rate"],
            "selected_validation_recall": validation_results[selected_name]["metrics"]["recall"],
        },
        "score_definition": "predict_proba for the malicious class; an uncalibrated benchmark score, not attack confidence",
        "preprocessing": {
            "numeric_missing_values": "training-fitted median imputation",
            "categorical_missing_values": "training-fitted most-frequent imputation",
            "categorical_encoding": "one-hot with unknown categories ignored",
            "missing_values_found": {
                "training": int(dataset.train_missing_values + training_features.isna().sum().sum() - dataset.training_features.isna().sum().sum()),
                "test": int(dataset.test_missing_values),
            },
        },
        "split": {
            "strategy": (
                "grouped stratified validation split from official training rows; supplemental rows sharing validation signatures excluded from fit; official test kept untouched"
                if supplemental_stats
                else "grouped stratified 80/20 validation split inside the official training partition; official test kept untouched"
            ),
            "random_state": FIT_SEED,
            "train_rows": int(len(train_indices)),
            "validation_rows": int(len(validation_indices)),
            "test_rows": int(len(dataset.test_labels)),
            "fitted_rows": int(len(training_labels)),
            "feature_signature_groups": signature_stats,
        },
        "class_counts": {
            "training": {
                "normal": int(fit_counts.get(0, 0)),
                "malicious": int(fit_counts.get(1, 0)),
            },
            "fit": {
                "normal": int(train_class_counts.get(0, 0)),
                "malicious": int(train_class_counts.get(1, 0)),
            },
            "validation": {
                "normal": int(validation_class_counts.get(0, 0)),
                "malicious": int(validation_class_counts.get(1, 0)),
            },
            "official_test": {
                "normal": int((dataset.test_labels == 0).sum()),
                "malicious": int((dataset.test_labels == 1).sum()),
            },
        },
        "validation_candidates": validation_results,
        "evaluation": None,
        "evaluation_warning": None,
        "limitations": [
            "UNSW-NB15 is a controlled academic benchmark, not live production traffic.",
            "Performance on this dataset does not establish detection on other networks or unseen attacks.",
            "Attack categories and identifiers are excluded from model input to reduce label leakage.",
            "Probability scores are not calibrated and are not proof that a flow is malicious.",
            "The official train and test partitions contain repeated feature signatures; evaluation reports their overlap and a novelty-aware sensitivity check.",
        ],
    }
    artifact = {
        "format_version": 2,
        "pipeline": selected,
        "features": list(FEATURE_COLUMNS),
        "threshold": threshold,
        "metadata": info,
    }
    atomic_save(artifact, artifact_path, info)
    selected_metrics = validation_results[selected_name]["metrics"]
    print(
        f"Selected {selected_name} by validation recall={selected_metrics['recall']:.3f} "
        f"at false-positive rate={selected_metrics['false_positive_rate']:.3f} "
        f"(maximum {MAX_VALIDATION_FALSE_POSITIVE_RATE:.0%}).",
        flush=True,
    )
    print("The official test partition has not been used for model or threshold selection.", flush=True)
    print(f"Trained artifact saved to {artifact_path.resolve()} ({artifact_path.stat().st_size:,} bytes).", flush=True)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None, help="Directory containing normalized training.csv and testing.csv.")
    parser.add_argument("--artifact", type=Path, default=CANDIDATE_ARTIFACT_PATH, help="Candidate artifact path; evaluation must finish before publication.")
    parser.add_argument("--include-full-unsw", action="store_true", help="Add a reproducible sample from the pinned 2.54M-row full UNSW-NB15 corpus.")
    parser.add_argument("--full-unsw-data-dir", type=Path, default=FULL_DATASET_ROOT, help="Directory containing the four checksum-pinned full-corpus CSVs.")
    parser.add_argument("--full-unsw-max-rows", type=int, default=DEFAULT_MAX_TRAIN_ROWS, help=f"Maximum supplemental rows after held-out-signature filtering (default: {DEFAULT_MAX_TRAIN_ROWS:,}).")
    args = parser.parse_args()
    train(
        args.data_dir,
        args.artifact,
        include_full_unsw=args.include_full_unsw,
        full_unsw_data_dir=args.full_unsw_data_dir,
        full_unsw_max_rows=args.full_unsw_max_rows,
    )


if __name__ == "__main__":
    main()

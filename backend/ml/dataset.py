"""Read and validate the versioned network-flow training and test CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ml.schema import (
    CATEGORICAL_FEATURES,
    DATASET_SLUG,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    TEST_FILENAME,
    TRAINING_FILENAME,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "raw" / DATASET_SLUG


@dataclass(frozen=True)
class Dataset:
    training_features: pd.DataFrame
    training_labels: pd.Series
    test_features: pd.DataFrame
    test_labels: pd.Series
    training_path: Path
    test_path: Path
    train_missing_values: int
    test_missing_values: int


def _read_split(path: Path, split_name: str) -> tuple[pd.DataFrame, pd.Series, int]:
    if not path.is_file():
        raise FileNotFoundError(
            f"{split_name.capitalize()} CSV is missing at {path}. "
            "Run `python -m ml.download_dataset` from the backend directory."
        )
    try:
        frame = pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read {split_name} CSV {path.name}: {exc}") from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    if frame.columns.has_duplicates:
        raise ValueError(f"{split_name.capitalize()} CSV contains duplicate column names.")
    required = {*FEATURE_COLUMNS, TARGET_COLUMN}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{split_name.capitalize()} CSV is missing required columns: {', '.join(missing)}")
    if len(frame) < 20:
        raise ValueError(f"{split_name.capitalize()} CSV needs at least 20 labeled records.")

    labels = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise ValueError(f"Target column {TARGET_COLUMN!r} must contain only binary 0/1 labels.")
    if labels.nunique() != 2:
        raise ValueError(f"{split_name.capitalize()} CSV must contain normal and malicious records.")

    features = pd.DataFrame(index=frame.index)
    missing_values = 0
    for column in NUMERIC_FEATURES:
        raw = frame[column]
        text = raw.astype("string").str.strip()
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid = raw.notna() & text.ne("") & numeric.isna()
        if invalid.any():
            raise ValueError(f"{split_name.capitalize()} feature {column!r} contains nonnumeric values.")
        numeric = numeric.replace([np.inf, -np.inf], np.nan)
        missing_values += int(numeric.isna().sum())
        features[column] = numeric

    for column in CATEGORICAL_FEATURES:
        values = frame[column].astype("string").str.strip()
        values = values.mask(values.eq(""), pd.NA)
        too_long = values.dropna().str.len().gt(128).any()
        if too_long:
            raise ValueError(f"{split_name.capitalize()} category {column!r} exceeds 128 characters.")
        missing_values += int(values.isna().sum())
        features[column] = values.astype(object)

    # Return columns in the same order used by training and inference.
    features = features.loc[:, FEATURE_COLUMNS].reset_index(drop=True)
    labels = labels.astype("int64").reset_index(drop=True)
    return features, labels, missing_values


def load_dataset(data_dir: Path | None = None) -> Dataset:
    """Load the official training partition and the untouched official test partition."""
    root = (data_dir or DATASET_ROOT).resolve()
    training_path = root / TRAINING_FILENAME
    test_path = root / TEST_FILENAME
    training_features, training_labels, train_missing = _read_split(training_path, "training")
    test_features, test_labels, test_missing = _read_split(test_path, "test")
    return Dataset(
        training_features=training_features,
        training_labels=training_labels,
        test_features=test_features,
        test_labels=test_labels,
        training_path=training_path,
        test_path=test_path,
        train_missing_values=train_missing,
        test_missing_values=test_missing,
    )

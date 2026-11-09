"""Read and validate the versioned network-flow training and test CSVs."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

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
    EXPECTED_TEST_BYTES,
    EXPECTED_TEST_ROWS,
    EXPECTED_TEST_SHA256,
    EXPECTED_TRAIN_BYTES,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "raw" / DATASET_SLUG


@dataclass(frozen=True)
class SplitExpectation:
    rows: int
    bytes: int
    sha256: str


OFFICIAL_SPLIT_EXPECTATIONS: Mapping[str, SplitExpectation] = MappingProxyType({
    TRAINING_FILENAME: SplitExpectation(EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_BYTES, EXPECTED_TRAIN_SHA256),
    TEST_FILENAME: SplitExpectation(EXPECTED_TEST_ROWS, EXPECTED_TEST_BYTES, EXPECTED_TEST_SHA256),
})


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
        features[column] = values.astype(object).where(values.notna(), np.nan)

    # Return columns in the same order used by training and inference.
    features = features.loc[:, FEATURE_COLUMNS].reset_index(drop=True)
    labels = labels.astype("int64").reset_index(drop=True)
    return features, labels, missing_values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_row_count(path: Path, split_name: str) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            headers = next(reader, None)
            if not headers or len(headers) != len(set(headers)):
                raise ValueError(f"{split_name.capitalize()} CSV has a missing or duplicate header.")
            required = {*FEATURE_COLUMNS, TARGET_COLUMN}
            missing = sorted(required - set(headers))
            if missing:
                raise ValueError(f"{split_name.capitalize()} CSV is missing required columns: {', '.join(missing)}")
            return sum(1 for row in reader if row and any(value.strip() for value in row))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"{split_name.capitalize()} CSV is not a readable CSV: {exc}") from exc


def verify_split_file(path: Path, split_name: str, expected: SplitExpectation) -> dict[str, int | str]:
    """Check the pinned file size, canonical row count, and SHA-256 before parsing it."""
    if not path.is_file():
        raise FileNotFoundError(
            f"{split_name.capitalize()} CSV is missing at {path}. "
            "Run `python -m ml.download_dataset` from the backend directory."
        )
    actual_bytes = path.stat().st_size
    if actual_bytes != expected.bytes:
        raise ValueError(
            f"{split_name.capitalize()} CSV has {actual_bytes:,} bytes; "
            f"expected the pinned {expected.bytes:,}-byte UNSW-NB15 split."
        )
    actual_rows = _csv_row_count(path, split_name)
    if actual_rows != expected.rows:
        raise ValueError(
            f"{split_name.capitalize()} CSV has {actual_rows:,} rows; "
            f"expected {expected.rows:,} canonical UNSW-NB15 rows."
        )
    actual_sha256 = _sha256(path)
    if actual_sha256 != expected.sha256:
        raise ValueError(
            f"{split_name.capitalize()} CSV SHA-256 does not match the pinned UNSW-NB15 file. "
            "Re-download both splits before training or evaluation."
        )
    return {"rows": actual_rows, "bytes": actual_bytes, "sha256": actual_sha256}


def load_dataset(
    data_dir: Path | None = None,
    *,
    expected_splits: Mapping[str, SplitExpectation] = OFFICIAL_SPLIT_EXPECTATIONS,
) -> Dataset:
    """Load only the verified official training and untouched test partitions."""
    root = (data_dir or DATASET_ROOT).resolve()
    training_path = root / TRAINING_FILENAME
    test_path = root / TEST_FILENAME
    if set(expected_splits) != {TRAINING_FILENAME, TEST_FILENAME}:
        raise ValueError("Dataset expectations must define both training.csv and testing.csv.")
    verify_split_file(training_path, "training", expected_splits[TRAINING_FILENAME])
    verify_split_file(test_path, "test", expected_splits[TEST_FILENAME])
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

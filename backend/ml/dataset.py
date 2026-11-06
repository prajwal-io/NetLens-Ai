"""Dataset discovery and training-data validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ml.schema import DATASET_SLUG, FEATURE_COLUMNS, LABELED_FILENAME, TARGET_COLUMN, TIMESTAMP_COLUMN


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "kagglehub-cache" / "datasets" / DATASET_SLUG


def latest_labeled_csv() -> Path:
    """Find the newest KaggleHub version already downloaded locally."""
    candidates = list(DATASET_ROOT.glob(f"versions/*/{LABELED_FILENAME}"))
    if not candidates:
        raise FileNotFoundError(
            "The labeled Kaggle dataset is not present. Run "
            "`python -m ml.download_dataset` from the backend directory first."
        )

    def version_key(path: Path) -> tuple[int, str]:
        try:
            return (int(path.parent.name), path.parent.name)
        except ValueError:
            return (-1, path.parent.name)

    return max(candidates, key=version_key)


def load_training_frame(path: Path | None = None) -> tuple[pd.DataFrame, pd.Series, pd.Series, Path]:
    """Load ordered feature, binary target, and timestamp columns.

    Feature columns containing blanks are supported by the fitted median
    imputer. Nonnumeric and infinite values fail early with a clear message.
    """
    source = (path or latest_labeled_csv()).resolve()
    try:
        frame = pd.read_csv(source)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read training CSV {source.name}: {exc}") from exc

    if frame.columns.has_duplicates:
        raise ValueError("Training CSV contains duplicate column names.")
    required = {*FEATURE_COLUMNS, TARGET_COLUMN, TIMESTAMP_COLUMN}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("Training CSV is missing required columns: " + ", ".join(missing))
    if len(frame) < 30:
        raise ValueError("Training CSV needs at least 30 labeled records for chronological evaluation.")

    timestamps = pd.to_datetime(frame[TIMESTAMP_COLUMN], errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError(f"Training CSV contains invalid values in {TIMESTAMP_COLUMN!r}.")

    raw_target = pd.to_numeric(frame[TARGET_COLUMN], errors="coerce")
    if raw_target.isna().any() or not set(raw_target.unique()).issubset({0, 1}):
        raise ValueError(f"Training target {TARGET_COLUMN!r} must contain only 0 and 1 labels.")

    features = pd.DataFrame(index=frame.index)
    for column in FEATURE_COLUMNS:
        raw = frame[column]
        numeric = pd.to_numeric(raw, errors="coerce")
        if (raw.notna() & numeric.isna()).any():
            raise ValueError(f"Training feature {column!r} contains nonnumeric values.")
        if np.isinf(numeric.dropna().to_numpy(dtype=float)).any():
            raise ValueError(f"Training feature {column!r} contains infinite values.")
        if (numeric.dropna() < 0).any():
            raise ValueError(f"Training feature {column!r} contains negative values.")
        features[column] = numeric

    order = timestamps.sort_values(kind="mergesort").index
    features = features.loc[order].reset_index(drop=True)
    target = raw_target.loc[order].astype("int64").reset_index(drop=True)
    ordered_timestamps = timestamps.loc[order].reset_index(drop=True)

    if target.nunique() != 2:
        raise ValueError("Training target must include both normal (0) and anomalous (1) records.")
    return features, target, ordered_timestamps, source

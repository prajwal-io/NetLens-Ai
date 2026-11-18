"""Load and serve the trusted, locally trained sklearn pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings
from ml.schema import CATEGORICAL_FEATURES, FEATURE_COLUMNS, ID_COLUMN, LABEL_CONTEXT_COLUMN, NUMERIC_FEATURES, SCHEMA_NAME, TARGET_COLUMN

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, artifact_path: Path | None = None) -> None:
        self.artifact_path = artifact_path or settings.model_artifact_path
        self._lock = RLock()
        self._pipeline: Any | None = None
        self._metadata: dict[str, Any] | None = None
        self._threshold: float | None = None
        self._load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None and self._metadata is not None and self._metadata.get("evaluation") is not None

    @property
    def model_version(self) -> str | None:
        return str(self._metadata["model_version"]) if self.loaded and self._metadata else None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def clear(self) -> None:
        with self._lock:
            self._pipeline = None
            self._metadata = None
            self._threshold = None

    def load(self) -> bool:
        """Load only locally generated artifacts that have held-out metrics."""
        with self._lock:
            self.clear()
            self._load_error = None
            if not self.artifact_path.is_file():
                return False
            try:
                artifact = joblib.load(self.artifact_path)
                if not isinstance(artifact, dict) or artifact.get("format_version") != 2:
                    raise ValueError("Unsupported model artifact format.")
                if tuple(artifact.get("features", ())) != FEATURE_COLUMNS:
                    raise ValueError("Model artifact feature order does not match UNSW-NB15 flow schema v1.")
                metadata = artifact.get("metadata")
                pipeline = artifact.get("pipeline")
                threshold = artifact.get("threshold")
                evaluation = metadata.get("evaluation") if isinstance(metadata, dict) else None
                if not isinstance(metadata, dict) or not isinstance(evaluation, dict):
                    raise ValueError("The model has not completed held-out evaluation.")
                if not isinstance(metadata.get("model_version"), str) or not metadata["model_version"].strip():
                    raise ValueError("The model artifact is missing its version.")
                if tuple(metadata.get("features", ())) != FEATURE_COLUMNS:
                    raise ValueError("Model metadata feature order does not match UNSW-NB15 flow schema v1.")
                metrics = evaluation.get("metrics")
                evaluation_rows = evaluation.get("rows")
                if not isinstance(metrics, dict) or type(evaluation_rows) is not int or evaluation_rows < 1:
                    raise ValueError("The model artifact contains incomplete held-out evaluation metadata.")
                metric_names = (
                    "accuracy", "balanced_accuracy", "precision", "recall", "f1",
                    "average_precision", "roc_auc", "false_positive_rate", "specificity",
                )
                if any(
                    not isinstance(metrics.get(name), (int, float))
                    or not np.isfinite(metrics[name])
                    or not 0 <= metrics[name] <= 1
                    for name in metric_names
                ):
                    raise ValueError("The model artifact contains incomplete held-out evaluation metrics.")
                support = metrics.get("support")
                confusion = metrics.get("confusion_matrix")
                matrix = confusion.get("rows_actual_columns_predicted") if isinstance(confusion, dict) else None
                if (
                    not isinstance(support, dict)
                    or type(support.get("normal")) is not int
                    or type(support.get("malicious")) is not int
                    or support["normal"] < 1
                    or support["malicious"] < 1
                    or support["normal"] + support["malicious"] != evaluation_rows
                    or not isinstance(confusion, dict)
                    or confusion.get("labels") != ["normal", "malicious"]
                    or not isinstance(matrix, list)
                    or len(matrix) != 2
                    or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
                    or any(type(value) is not int or value < 0 for row in matrix for value in row)
                    or sum(matrix[0]) != support["normal"]
                    or sum(matrix[1]) != support["malicious"]
                ):
                    raise ValueError("The model artifact contains incomplete held-out class support or confusion matrix.")
                evaluation_threshold = evaluation.get("threshold")
                if (
                    not isinstance(evaluation_threshold, (int, float))
                    or not np.isfinite(evaluation_threshold)
                    or not 0 <= evaluation_threshold <= 1
                    or not np.isclose(evaluation_threshold, threshold)
                ):
                    raise ValueError("The held-out evaluation threshold does not match the saved decision threshold.")
                novelty = evaluation.get("novel_feature_signature_evaluation")
                if (
                    not isinstance(evaluation.get("split"), str)
                    or not evaluation["split"].strip()
                    or not isinstance(novelty, dict)
                    or type(novelty.get("rows")) is not int
                    or novelty["rows"] < 0
                    or not isinstance(novelty.get("definition"), str)
                ):
                    raise ValueError("The model artifact contains incomplete held-out evaluation metadata.")
                if not callable(getattr(pipeline, "predict_proba", None)):
                    raise ValueError("The model artifact is missing its probability pipeline.")
                if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or not 0 <= threshold <= 1:
                    raise ValueError("The model artifact contains an invalid classification threshold.")
                if "decision_threshold" in metadata and float(metadata["decision_threshold"]) != float(threshold):
                    raise ValueError("Model metadata threshold does not match the saved decision threshold.")
                classes = list(getattr(pipeline, "classes_", []))
                if 1 not in classes or 0 not in classes:
                    raise ValueError("The model artifact must support both binary classes.")
                if getattr(pipeline, "n_features_in_", len(FEATURE_COLUMNS)) != len(FEATURE_COLUMNS):
                    raise ValueError("The model pipeline input width does not match the 42-feature contract.")
                probe = pd.DataFrame([{
                    feature: 0.0 if feature in NUMERIC_FEATURES else "-"
                    for feature in FEATURE_COLUMNS
                }], columns=FEATURE_COLUMNS)
                probe_scores = np.asarray(pipeline.predict_proba(probe), dtype=float)
                if (
                    probe_scores.shape != (1, len(classes))
                    or not np.isfinite(probe_scores).all()
                    or (probe_scores < 0).any()
                    or (probe_scores > 1).any()
                    or not np.isclose(probe_scores.sum(axis=1), 1).all()
                ):
                    raise ValueError("The saved model returned invalid probabilities for a schema probe.")
                self._pipeline = pipeline
                self._metadata = metadata
                self._threshold = float(threshold)
                logger.info("Loaded model %s from %s", metadata["model_version"], self.artifact_path)
                return True
            except Exception as exc:  # An invalid artifact should not prevent the API from serving health.
                self.clear()
                self._load_error = str(exc)
                logger.exception("Could not load the configured ML model artifact")
                return False

    def require_loaded(self) -> tuple[Any, dict[str, Any], float]:
        if not self.loaded or self._pipeline is None or self._metadata is None or self._threshold is None:
            detail = "No trained, evaluated model is installed. Run the documented training and evaluation commands."
            if self._load_error:
                detail = "The local model artifact could not be loaded. Retrain it and restart the API."
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail=detail)
        return self._pipeline, self._metadata, self._threshold

    def info(self) -> dict[str, Any]:
        _, metadata, _ = self.require_loaded()
        # JSON round-tripping gives callers a detached, serialization-safe copy.
        return json.loads(json.dumps(metadata, allow_nan=False))

    @staticmethod
    def schema() -> dict[str, Any]:
        """Expose the accepted input contract even when no model is installed."""
        return {
            "schema_name": SCHEMA_NAME,
            "feature_count": len(FEATURE_COLUMNS),
            "features": list(FEATURE_COLUMNS),
            "numeric_features": list(NUMERIC_FEATURES),
            "categorical_features": list(CATEGORICAL_FEATURES),
            "excluded_columns": [ID_COLUMN, LABEL_CONTEXT_COLUMN, TARGET_COLUMN],
        }

    def predict(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float]:
        pipeline, metadata, threshold = self.require_loaded()
        ordered = features.loc[:, FEATURE_COLUMNS].copy()
        # The saved sklearn imputers use np.nan as their missing-value marker.
        # JSON/CSV parsing supplies None; normalize it just as the training loader does.
        for feature in CATEGORICAL_FEATURES:
            ordered[feature] = ordered[feature].where(ordered[feature].notna(), np.nan)
        probabilities = np.asarray(pipeline.predict_proba(ordered), dtype=float)
        classes = list(pipeline.classes_)
        positive_index = classes.index(1)
        scores = probabilities[:, positive_index]
        if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise RuntimeError("The model returned invalid malicious-class scores.")
        labels = (scores >= threshold).astype("int64")
        return labels, scores, metadata, threshold


model_service = ModelService()

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
from ml.schema import FEATURE_COLUMNS

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
                if not isinstance(artifact, dict) or artifact.get("format_version") != 1:
                    raise ValueError("Unsupported model artifact format.")
                if tuple(artifact.get("features", ())) != FEATURE_COLUMNS:
                    raise ValueError("Model artifact feature order does not match network-metrics-v1.")
                metadata = artifact.get("metadata")
                pipeline = artifact.get("pipeline")
                threshold = artifact.get("threshold")
                if not isinstance(metadata, dict) or metadata.get("evaluation") is None:
                    raise ValueError("The model has not completed held-out evaluation.")
                if not isinstance(metadata.get("model_version"), str) or not callable(getattr(pipeline, "predict_proba", None)):
                    raise ValueError("The model artifact is missing its version or probability output.")
                if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
                    raise ValueError("The model artifact contains an invalid classification threshold.")
                classes = list(getattr(pipeline, "classes_", []))
                if 1 not in classes or 0 not in classes:
                    raise ValueError("The model artifact must support both binary classes.")
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

    def predict(self, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, Any], float]:
        pipeline, metadata, threshold = self.require_loaded()
        ordered = features.loc[:, FEATURE_COLUMNS]
        probabilities = np.asarray(pipeline.predict_proba(ordered), dtype=float)
        classes = list(pipeline.classes_)
        positive_index = classes.index(1)
        scores = probabilities[:, positive_index]
        if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise RuntimeError("The model returned invalid anomaly scores.")
        labels = (scores >= threshold).astype("int64")
        return labels, scores, metadata, threshold


model_service = ModelService()

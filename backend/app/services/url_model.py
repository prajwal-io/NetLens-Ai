"""Load the compact, versioned URL-only model artifact."""
from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np

from ml.url_features import FEATURES, extract_url_features

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "netsight-url-lr-v1.json"


class URLModelService:
    def __init__(self, path: Path = MODEL_PATH) -> None:
        self.path = path
        self._lock = RLock()
        self._model: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                model = json.loads(self.path.read_text(encoding="utf-8"))
                arrays = [np.asarray(model[key], dtype="float64") for key in ("mean", "scale", "coefficients")]
                if (model.get("model_version") != "netsight-url-lr-phiusiil-v1"
                        or tuple(model.get("feature_order", ())) != FEATURES
                        or any(array.shape != (len(FEATURES),) or not np.isfinite(array).all() for array in arrays)
                        or (arrays[1] <= 0).any()
                        or not np.isfinite(float(model["intercept"]))
                        or not 0 < float(model["threshold"]) < 1):
                    raise ValueError("URL model metadata or coefficients are invalid.")
                self._model = model
                return model
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError("The trained URL model is unavailable or invalid.") from exc

    def predict(self, url: str) -> dict[str, Any]:
        model = self._load()
        features = extract_url_features(url)
        normalized = (features - np.asarray(model["mean"], dtype="float64")) / np.asarray(model["scale"], dtype="float64")
        logit = float(np.dot(normalized, np.asarray(model["coefficients"], dtype="float64")) + model["intercept"])
        score = 1 / (1 + np.exp(-float(np.clip(logit, -60, 60))))
        threshold = float(model["threshold"])
        return {
            "model_version": model["model_version"],
            "label": "phishing_signal" if score >= threshold else "no_strong_signal",
            "phishing_score": float(score),
            "threshold": threshold,
        }


url_model = URLModelService()

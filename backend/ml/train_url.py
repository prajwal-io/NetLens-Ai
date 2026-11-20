"""Train a URL-only phishing classifier from the UCI PhiUSIIL benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.url_features import FEATURES, extract_url_features

DATASET_SOURCE = "https://archive.ics.uci.edu/dataset/967/phiusil+phishing+url+dataset"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "netsight-url-lr-v1.json"
MAX_VALIDATION_FPR = 0.05


def metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    predicted = (scores >= threshold).astype("int8")
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    return {
        "rows": int(len(labels)), "accuracy": float((tn + tp) / max(1, len(labels))),
        "precision": float(tp / max(1, tp + fp)), "recall": float(tp / max(1, tp + fn)),
        "f1": float(2 * tp / max(1, 2 * tp + fp + fn)),
        "false_positive_rate": float(fp / max(1, fp + tn)), "roc_auc": float(roc_auc_score(labels, scores)),
        "confusion_matrix": {"labels": ["legitimate", "phishing"], "rows_actual_columns_predicted": [[int(tn), int(fp)], [int(fn), int(tp)]]},
    }


def select_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[float, dict]:
    fprs, recalls, thresholds = roc_curve(labels, scores, drop_intermediate=False)
    eligible = np.flatnonzero(np.isfinite(thresholds) & (fprs <= MAX_VALIDATION_FPR))
    if not len(eligible):
        raise ValueError("No validation threshold met the 5% false-positive target.")
    index = max(eligible, key=lambda i: (recalls[i], -fprs[i], thresholds[i]))
    threshold = float(thresholds[index])
    return threshold, metrics(labels, scores, threshold)


def train(dataset_path: Path, model_path: Path = MODEL_PATH) -> dict:
    raw = dataset_path.read_bytes()
    frame = pd.read_csv(dataset_path, usecols=["URL", "Domain", "label"])
    frame = frame.dropna(subset=["URL", "Domain", "label"]).drop_duplicates(subset=["URL"]).reset_index(drop=True)
    if set(frame["label"].unique()) != {0, 1}:
        raise ValueError("PhiUSIIL labels must contain 0 (phishing) and 1 (legitimate).")

    features = np.vstack([extract_url_features(str(url)) for url in frame["URL"]])
    labels = (frame["label"].to_numpy(dtype="int8") == 0).astype("int8")
    groups = frame["Domain"].astype(str).str.lower().to_numpy()
    train_val, test = next(GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=2026).split(features, labels, groups))
    train_rel, validation_rel = next(GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=2027).split(features[train_val], labels[train_val], groups[train_val]))
    fit = train_val[train_rel]
    validation = train_val[validation_rel]
    if set(groups[fit]) & set(groups[validation]) or set(groups[fit]) & set(groups[test]) or set(groups[validation]) & set(groups[test]):
        raise AssertionError("A domain leaked across grouped train, validation, and test splits.")
    if any(np.unique(labels[index]).size != 2 for index in (fit, validation, test)):
        raise ValueError("Every domain split must include legitimate and phishing URLs.")

    pipeline = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=600, solver="lbfgs", random_state=2026))
    pipeline.fit(features[fit], labels[fit])
    validation_scores = pipeline.predict_proba(features[validation])[:, list(pipeline.classes_).index(1)]
    threshold, validation_metrics = select_threshold(labels[validation], validation_scores)
    test_scores = pipeline.predict_proba(features[test])[:, list(pipeline.classes_).index(1)]
    test_metrics = metrics(labels[test], test_scores, threshold)
    scaler = pipeline.named_steps["standardscaler"]
    classifier = pipeline.named_steps["logisticregression"]
    model = {
        "model_version": "netsight-url-lr-phiusiil-v1", "feature_order": list(FEATURES),
        "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
        "coefficients": classifier.coef_[0].tolist(), "intercept": float(classifier.intercept_[0]),
        "threshold": threshold, "positive_class": "phishing",
        "dataset": {"name": "PhiUSIIL Phishing URL (Website)", "source": DATASET_SOURCE, "doi": "10.1016/j.cose.2023.103545", "license": "CC BY 4.0", "sha256": hashlib.sha256(raw).hexdigest(), "rows": int(len(frame)), "features_used": "22 URL lexical/structural features recomputed from the raw URL column; webpage-derived columns, Domain, FILENAME, and label are excluded from inference"},
        "split": {"method": "20% domain-grouped test; remaining 80% split into 80% fit / 20% validation by domain", "seed": 2026, "fit_rows": len(fit), "validation_rows": len(validation), "test_rows": len(test), "unique_domains": int(len(np.unique(groups)))},
        "threshold_policy": {"objective": "maximize phishing recall subject to validation false-positive rate <= 5%", "max_validation_fpr": MAX_VALIDATION_FPR},
        "validation_metrics": validation_metrics, "test_metrics": test_metrics,
        "limitations": ["This is a URL-only lexical model trained on the PhiUSIIL snapshot; live DNS/HTTP findings are separate evidence.", "Test rows are grouped by dataset Domain, but a changed or unseen phishing campaign may behave differently.", "The score is an uncalibrated model output, not a probability that a specific incident is confirmed."],
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"model_version": model["model_version"], "validation": validation_metrics, "test": test_metrics, "model": str(model_path)}, indent=2))
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="UCI PhiUSIIL_Phishing_URL_Dataset.csv")
    parser.add_argument("--model", type=Path, default=MODEL_PATH, help="Output path for the compact JSON model artifact.")
    args = parser.parse_args()
    train(args.dataset, args.model)


if __name__ == "__main__":
    main()

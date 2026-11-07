import joblib
import pandas as pd
import pytest

from ml.dataset import load_dataset
from ml.evaluate import evaluate
from ml.schema import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES
from ml.train import candidate_models, train


def make_rows(count: int, start: int = 0) -> pd.DataFrame:
    rows = []
    for offset in range(count):
        index = start + offset
        malicious = index % 2
        row = {column: float(index + 1 + malicious * 4) for column in NUMERIC_FEATURES}
        row.update({
            "proto": "tcp" if malicious else "udp",
            "service": "http" if malicious else "-",
            "state": "FIN" if malicious else "CON",
            "id": index + 1,
            "attack_cat": "Generic" if malicious else "Normal",
            "label": malicious,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def write_splits(directory, train_rows: int = 120, test_rows: int = 60) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    make_rows(train_rows).to_csv(directory / "training.csv", index=False)
    make_rows(test_rows, start=1000).to_csv(directory / "testing.csv", index=False)


def test_loader_uses_only_contract_features_and_binary_target(tmp_path):
    write_splits(tmp_path)
    dataset = load_dataset(tmp_path)
    assert len(dataset.training_features) == 120
    assert len(dataset.test_features) == 60
    assert tuple(dataset.training_features.columns) == FEATURE_COLUMNS
    assert dataset.training_labels.value_counts().to_dict() == {0: 60, 1: 60}
    assert set(dataset.training_features.columns).isdisjoint({"id", "attack_cat", "label"})
    assert set(CATEGORICAL_FEATURES).issubset(dataset.training_features.columns)


def test_train_selects_on_grouped_validation_and_evaluate_uses_official_test(tmp_path, monkeypatch):
    write_splits(tmp_path)
    artifact_path = tmp_path / "artifact" / "model.joblib"
    original_candidates = candidate_models
    monkeypatch.setattr("ml.train.candidate_models", lambda: original_candidates(forest_trees=8))

    artifact = train(tmp_path, artifact_path)
    assert artifact["format_version"] == 2
    assert artifact["features"] == list(FEATURE_COLUMNS)
    assert set(artifact["metadata"]["excluded_columns"]) == {"id", "attack_cat", "label"}
    assert artifact["metadata"]["evaluation"] is None
    assert artifact["metadata"]["split"]["train_rows"] + artifact["metadata"]["split"]["validation_rows"] == 120
    assert artifact["metadata"]["split"]["test_rows"] == 60

    metadata = evaluate(tmp_path, artifact_path)
    assert metadata["evaluation"]["rows"] == 60
    assert metadata["evaluation"]["metrics"]["support"] == {"normal": 30, "malicious": 30}
    assert 0 <= metadata["evaluation"]["metrics"]["f1"] <= 1
    assert metadata["evaluation"]["novel_feature_signature_evaluation"]["rows"] == 60
    saved = joblib.load(artifact_path)
    assert saved["metadata"]["evaluation"] is not None
    assert artifact_path.with_suffix(".json").is_file()


def test_dataset_rejects_missing_model_feature(tmp_path):
    write_splits(tmp_path)
    frame = pd.read_csv(tmp_path / "training.csv").drop(columns=[FEATURE_COLUMNS[0]])
    frame.to_csv(tmp_path / "training.csv", index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_dataset(tmp_path)


def test_dataset_rejects_nonbinary_target(tmp_path):
    write_splits(tmp_path)
    frame = pd.read_csv(tmp_path / "testing.csv")
    frame.loc[0, "label"] = 2
    frame.to_csv(tmp_path / "testing.csv", index=False)
    with pytest.raises(ValueError, match="only binary 0/1 labels"):
        load_dataset(tmp_path)

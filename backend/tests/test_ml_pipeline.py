import hashlib
import re
import urllib.error

import joblib
import pandas as pd
import pytest

from ml.dataset import (
    DATASET_ROOT,
    OFFICIAL_SPLIT_EXPECTATIONS,
    SplitExpectation,
    load_dataset,
)
from ml.download_dataset import DownloadSpec, download_dataset
from ml.evaluate import evaluate
from ml.schema import (
    CATEGORICAL_FEATURES,
    EXPECTED_TEST_BYTES,
    EXPECTED_TEST_ROWS,
    EXPECTED_TEST_SHA256,
    EXPECTED_TRAIN_BYTES,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    REMOTE_TESTING_CONTENT,
    REMOTE_TRAINING_CONTENT,
    TEST_FILENAME,
    TRAINING_FILENAME,
)
from ml.train import candidate_models, choose_threshold, train


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


def write_splits(directory, train_rows: int = 120, test_rows: int = 60) -> dict[str, SplitExpectation]:
    directory.mkdir(parents=True, exist_ok=True)
    make_rows(train_rows).to_csv(directory / "training.csv", index=False)
    make_rows(test_rows, start=1000).to_csv(directory / "testing.csv", index=False)
    return {
        "training.csv": _expectation(directory / "training.csv", train_rows),
        "testing.csv": _expectation(directory / "testing.csv", test_rows),
    }


def _expectation(path, rows: int) -> SplitExpectation:
    content = path.read_bytes()
    return SplitExpectation(rows=rows, bytes=len(content), sha256=hashlib.sha256(content).hexdigest())


def test_loader_uses_only_contract_features_and_binary_target(tmp_path):
    expectations = write_splits(tmp_path)
    dataset = load_dataset(tmp_path, expected_splits=expectations)
    assert len(dataset.training_features) == 120
    assert len(dataset.test_features) == 60
    assert tuple(dataset.training_features.columns) == FEATURE_COLUMNS
    assert dataset.training_labels.value_counts().to_dict() == {0: 60, 1: 60}
    assert set(dataset.training_features.columns).isdisjoint({"id", "attack_cat", "label"})
    assert set(CATEGORICAL_FEATURES).issubset(dataset.training_features.columns)


def test_train_selects_on_grouped_validation_and_evaluate_uses_official_test(tmp_path, monkeypatch):
    expectations = write_splits(tmp_path)
    artifact_path = tmp_path / "artifact" / "model.joblib"
    original_candidates = candidate_models
    monkeypatch.setattr("ml.train.candidate_models", lambda: original_candidates(forest_trees=8))

    artifact = train(tmp_path, artifact_path, expected_splits=expectations)
    assert artifact["format_version"] == 2
    assert artifact["features"] == list(FEATURE_COLUMNS)
    assert set(artifact["metadata"]["excluded_columns"]) == {"id", "attack_cat", "label"}
    assert artifact["metadata"]["evaluation"] is None
    assert artifact["metadata"]["split"]["train_rows"] + artifact["metadata"]["split"]["validation_rows"] == 120
    assert artifact["metadata"]["split"]["test_rows"] == 60
    policy = artifact["metadata"]["threshold_policy"]
    selected_metrics = artifact["metadata"]["validation_candidates"][artifact["metadata"]["model_name"]]["metrics"]
    assert policy["maximum_validation_false_positive_rate"] == pytest.approx(0.05)
    assert selected_metrics["false_positive_rate"] <= policy["maximum_validation_false_positive_rate"]
    assert policy["selected_validation_recall"] == selected_metrics["recall"]

    metadata = evaluate(tmp_path, artifact_path, expected_splits=expectations)
    assert metadata["evaluation"]["rows"] == 60
    assert metadata["evaluation"]["metrics"]["support"] == {"normal": 30, "malicious": 30}
    assert 0 <= metadata["evaluation"]["metrics"]["f1"] <= 1
    assert metadata["evaluation"]["novel_feature_signature_evaluation"]["rows"] == 60
    saved = joblib.load(artifact_path)
    assert saved["metadata"]["evaluation"] is not None
    assert artifact_path.with_suffix(".json").is_file()


def test_dataset_rejects_missing_model_feature(tmp_path):
    expectations = write_splits(tmp_path)
    frame = pd.read_csv(tmp_path / "training.csv").drop(columns=[FEATURE_COLUMNS[0]])
    frame.to_csv(tmp_path / "training.csv", index=False)
    expectations[TRAINING_FILENAME] = _expectation(tmp_path / TRAINING_FILENAME, 120)
    with pytest.raises(ValueError, match="missing required columns"):
        load_dataset(tmp_path, expected_splits=expectations)


def test_dataset_rejects_nonbinary_target(tmp_path):
    expectations = write_splits(tmp_path)
    frame = pd.read_csv(tmp_path / "testing.csv")
    frame.loc[0, "label"] = 2
    frame.to_csv(tmp_path / "testing.csv", index=False)
    expectations[TEST_FILENAME] = _expectation(tmp_path / TEST_FILENAME, 60)
    with pytest.raises(ValueError, match="only binary 0/1 labels"):
        load_dataset(tmp_path, expected_splits=expectations)


@pytest.mark.parametrize("mutation", ["wrong", "swapped", "truncated", "modified"])
def test_loader_rejects_wrong_swapped_truncated_or_modified_splits(tmp_path, mutation):
    expectations = write_splits(tmp_path)
    training = tmp_path / TRAINING_FILENAME
    testing = tmp_path / TEST_FILENAME

    if mutation == "wrong":
        make_rows(120, start=9000).to_csv(training, index=False)
    elif mutation == "swapped":
        training_bytes, testing_bytes = training.read_bytes(), testing.read_bytes()
        training.write_bytes(testing_bytes)
        testing.write_bytes(training_bytes)
    elif mutation == "truncated":
        training.write_bytes(training.read_bytes()[:-50])
    else:
        original = training.read_bytes()
        altered = original.replace(b"1.0", b"9.0", 1)
        assert len(altered) == len(original)
        training.write_bytes(altered)

    with pytest.raises(ValueError, match="bytes|rows|SHA-256"):
        load_dataset(tmp_path, expected_splits=expectations)


def test_official_unsw_split_contract_pins_size_hash_and_mirror_roles():
    training = OFFICIAL_SPLIT_EXPECTATIONS[TRAINING_FILENAME]
    testing = OFFICIAL_SPLIT_EXPECTATIONS[TEST_FILENAME]
    assert (training.rows, training.bytes, training.sha256) == (
        EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_BYTES, EXPECTED_TRAIN_SHA256
    )
    assert (testing.rows, testing.bytes, testing.sha256) == (
        EXPECTED_TEST_ROWS, EXPECTED_TEST_BYTES, EXPECTED_TEST_SHA256
    )
    assert training.rows == 175_341 and testing.rows == 82_332
    assert re.fullmatch(r"[0-9a-f]{64}", training.sha256)
    assert re.fullmatch(r"[0-9a-f]{64}", testing.sha256)
    assert REMOTE_TRAINING_CONTENT != TRAINING_FILENAME
    assert REMOTE_TESTING_CONTENT != TEST_FILENAME


def test_present_official_dataset_matches_trusted_pins():
    if not (DATASET_ROOT / TRAINING_FILENAME).is_file() or not (DATASET_ROOT / TEST_FILENAME).is_file():
        pytest.skip("Raw benchmark files are not checked in; downloader pins are verified separately.")
    dataset = load_dataset()
    assert len(dataset.training_labels) == EXPECTED_TRAIN_ROWS
    assert len(dataset.test_labels) == EXPECTED_TEST_ROWS


class _FakeResponse:
    def __init__(self, content: bytes, status: int = 200):
        self.content = content
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _size: int) -> bytes:
        content, self.content = self.content, b""
        return content


def _test_download_payloads():
    training = make_rows(30).to_csv(index=False).encode()
    testing = make_rows(16, start=500).to_csv(index=False).encode()
    specs = (
        DownloadSpec("training-source.csv", TRAINING_FILENAME, SplitExpectation(30, len(training), hashlib.sha256(training).hexdigest())),
        DownloadSpec("testing-source.csv", TEST_FILENAME, SplitExpectation(16, len(testing), hashlib.sha256(testing).hexdigest())),
    )
    return specs, {"training-source.csv": training, "testing-source.csv": testing}


def test_downloader_installs_both_splits_and_manifest_after_validation(tmp_path):
    destination = tmp_path / "active"
    destination.mkdir()
    old_files = {
        TRAINING_FILENAME: b"previous training",
        TEST_FILENAME: b"previous test",
        "download-manifest.json": b"previous manifest",
    }
    for name, content in old_files.items():
        (destination / name).write_bytes(content)
    specs, payloads = _test_download_payloads()
    calls = 0

    def open_url(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 2:
            assert {name: (destination / name).read_bytes() for name in old_files} == old_files
        remote = request.full_url.rsplit("/", 1)[-1]
        return _FakeResponse(payloads[remote])

    manifest = download_dataset(destination, specs=specs, open_url=open_url, mirror_commit="test-revision")
    assert calls == 2
    assert (destination / TRAINING_FILENAME).read_bytes() == payloads["training-source.csv"]
    assert (destination / TEST_FILENAME).read_bytes() == payloads["testing-source.csv"]
    assert manifest["files"][TRAINING_FILENAME]["rows"] == 30
    assert (destination / "download-manifest.json").is_file()


@pytest.mark.parametrize("failure", ["network", "bad_hash", "http_status"])
def test_downloader_failure_keeps_previous_splits_and_manifest(tmp_path, failure):
    destination = tmp_path / "active"
    destination.mkdir()
    old_files = {
        TRAINING_FILENAME: b"previous training",
        TEST_FILENAME: b"previous test",
        "download-manifest.json": b"previous manifest",
    }
    for name, content in old_files.items():
        (destination / name).write_bytes(content)
    specs, payloads = _test_download_payloads()
    tampered = dict(payloads)
    if failure == "bad_hash":
        tampered["testing-source.csv"] = tampered["testing-source.csv"].replace(b"1.0", b"9.0", 1)
    calls = 0

    def open_url(request, timeout):
        nonlocal calls
        calls += 1
        if failure == "network" and calls == 2:
            raise urllib.error.URLError("offline")
        if failure == "http_status" and calls == 1:
            return _FakeResponse(b"not found", status=404)
        remote = request.full_url.rsplit("/", 1)[-1]
        return _FakeResponse(tampered[remote])

    with pytest.raises((RuntimeError, ValueError)):
        download_dataset(destination, specs=specs, open_url=open_url, mirror_commit="test-revision")
    assert {name: (destination / name).read_bytes() for name in old_files} == old_files
    assert not list(destination.parent.glob(".active-stage-*"))


def test_threshold_maximizes_recall_under_false_positive_budget():
    actual = pd.Series([0, 0, 0, 1, 1, 1]).to_numpy()
    scores = pd.Series([0.1, 0.4, 0.6, 0.7, 0.8, 0.9]).to_numpy()
    threshold, metrics = choose_threshold(actual, scores, maximum_false_positive_rate=0.2)
    assert threshold == pytest.approx(0.7)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["false_positive_rate"] <= 0.2


def test_threshold_fails_if_false_positive_budget_is_unattainable():
    with pytest.raises(ValueError, match="No validation threshold met"):
        choose_threshold([0, 0, 1], [0.5, 0.5, 0.5], maximum_false_positive_rate=0.05)

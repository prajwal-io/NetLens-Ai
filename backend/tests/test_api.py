import csv
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.model_service import ModelService, model_service
from ml.schema import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES
from ml.train import candidate_models


def _row(index: int, malicious: int) -> dict[str, object]:
    row: dict[str, object] = {
        column: float(index + 1 + malicious * 3)
        for column in NUMERIC_FEATURES
    }
    row.update({
        "proto": "tcp" if malicious else "udp",
        "service": "http" if malicious else "-",
        "state": "FIN" if malicious else "CON",
        "label": malicious,
        "attack_cat": "Generic" if malicious else "Normal",
        "id": index + 1,
    })
    return row


def _csv(rows: list[dict[str, object]], extra: bool = False) -> bytes:
    columns = list(FEATURE_COLUMNS) + (["label", "attack_cat", "id"] if extra else [])
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows({column: row.get(column, "") for column in columns} for row in rows)
    return stream.getvalue().encode("utf-8")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", tmp_path / "test.db")
    rows = [_row(index, index % 2) for index in range(80)]
    frame = pd.DataFrame(rows)
    labels = frame["label"].to_numpy(dtype="int64")
    pipeline = candidate_models(forest_trees=8)["Random Forest"]
    pipeline.fit(frame.loc[:, FEATURE_COLUMNS], labels)
    artifact_path = tmp_path / "test-model.joblib"
    metadata = {
        "model_name": "Random Forest",
        "model_version": "netsight-test-v1",
        "algorithm": "Random Forest",
        "dataset": {"name": "test fixture", "source": "https://example.invalid"},
        "target": {"column": "label", "normal_value": 0, "malicious_value": 1},
        "features": list(FEATURE_COLUMNS),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "feature_count": len(FEATURE_COLUMNS),
        "decision_threshold": 0.5,
        "score_definition": "test fixture score",
        "validation_candidates": {"Random Forest": {"threshold": 0.5, "metrics": {"f1": 1.0}}},
        "evaluation": {
            "split": "test fixture holdout",
            "rows": 2,
            "metrics": {
                "accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "average_precision": 1.0,
                "roc_auc": 1.0,
                "support": {"normal": 1, "malicious": 1},
                "confusion_matrix": {"labels": ["normal", "malicious"], "rows_actual_columns_predicted": [[1, 0], [0, 1]]},
            },
            "repeated_feature_signature_rows": 0,
            "repeated_feature_signature_rate": 0.0,
            "novel_feature_signature_evaluation": {"rows": 2, "metrics": None, "definition": "test fixture"},
        },
        "evaluation_warning": None,
        "limitations": ["Test-only model fixture."],
    }
    joblib.dump({"format_version": 2, "pipeline": pipeline, "features": list(FEATURE_COLUMNS), "threshold": 0.5, "metadata": metadata}, artifact_path)
    original_path = model_service.artifact_path
    monkeypatch.setattr(model_service, "artifact_path", artifact_path)
    with TestClient(app) as test_client:
        yield test_client
    monkeypatch.setattr(model_service, "artifact_path", original_path)
    model_service.load()


def upload(client, content: bytes, name: str = "flows.csv", endpoint: str = "validate"):
    return client.post(f"/api/v1/traffic/{endpoint}", files={"file": (name, content, "text/csv")})


def test_health_and_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is True
    assert response.json()["model_version"] == "netsight-test-v1"
    assert settings.database_path.exists()


def test_model_schema_matches_feature_contract(client):
    response = client.get("/api/v1/model/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_name"] == "unsw-nb15-flow-v1"
    assert body["feature_count"] == len(FEATURE_COLUMNS) == 42
    assert set(body["numeric_features"]) == set(NUMERIC_FEATURES)
    assert set(body["categorical_features"]) == set(CATEGORICAL_FEATURES)
    assert {"id", "attack_cat", "label"}.issubset(body["excluded_columns"])


def test_model_info_exposes_evaluated_metrics(client):
    response = client.get("/api/v1/model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "netsight-test-v1"
    assert body["feature_count"] == len(FEATURE_COLUMNS)
    assert body["evaluation"]["metrics"]["support"]["malicious"] == 1


def test_valid_mixed_feature_csv(client):
    response = upload(client, _csv([_row(0, 0), _row(1, 1)]))
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["schema_name"] == "unsw-nb15-flow-v1"
    assert body["preview"][0]["proto"] == "udp"
    assert "predictions" not in body


def test_target_and_identifier_columns_are_ignored(client):
    response = upload(client, _csv([_row(0, 0), _row(1, 1)], extra=True), endpoint="analyze")
    assert response.status_code == 200
    body = response.json()
    assert {"label", "attack_cat", "id"}.issubset(body["preview"][0]["features"].keys()) is False
    assert body["counts"]["normal"] + body["counts"]["malicious"] == body["total_flows"] == 2
    assert [item["row_id"] for item in body["predictions"]] == [1, 2]
    assert all(item["label"] in {"normal", "malicious"} for item in body["predictions"])
    assert all(0 <= item["malicious_score"] <= 1 for item in body["predictions"])
    assert "not proof" in body["message"]


def test_blank_values_and_signed_numeric_values_are_accepted(client):
    first = _row(0, 0)
    first[NUMERIC_FEATURES[0]] = ""
    first[NUMERIC_FEATURES[1]] = -0.25
    first["service"] = ""
    response = upload(client, _csv([first]))
    assert response.status_code == 200
    assert response.json()["row_count"] == 1


@pytest.mark.parametrize("content", [
    b"",
    b"x,y\n1,2\n",
    (",".join(FEATURE_COLUMNS) + "\n").encode(),
    _csv([_row(0, 0)]).replace(b"1.0", b"not-a-number", 1),
    _csv([_row(0, 0)]).replace(b"1.0", b"inf", 1),
    _csv([_row(0, 0)]).replace(b"proto,service", b"proto,proto"),
    b"\xff\xfe",
])
def test_invalid_csv_is_rejected(client, content):
    response = upload(client, content)
    assert response.status_code == 422
    assert response.json()["error"]["message"]


def test_upload_limits(client, monkeypatch):
    assert upload(client, _csv([_row(0, 0)]), "flows.txt").status_code == 415
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    assert upload(client, _csv([_row(0, 0)])).status_code == 413


def test_row_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_rows", 1)
    assert upload(client, _csv([_row(0, 0), _row(1, 1)])).status_code == 422


def test_missing_file(client):
    assert client.post("/api/v1/traffic/validate").status_code == 422


def test_model_unavailable_returns_503(client, tmp_path, monkeypatch):
    original_path = model_service.artifact_path
    try:
        monkeypatch.setattr(model_service, "artifact_path", tmp_path / "missing-model.joblib")
        assert model_service.load() is False
        assert client.get("/api/v1/health").json()["model_loaded"] is False
        assert client.get("/api/v1/model/schema").status_code == 200
        assert client.get("/api/v1/model/info").status_code == 503
        assert upload(client, _csv([_row(0, 0)]), endpoint="analyze").status_code == 503
    finally:
        monkeypatch.setattr(model_service, "artifact_path", original_path)
        assert model_service.load() is True


def test_incomplete_and_invalid_artifacts_fail_closed(client, tmp_path):
    original = joblib.load(model_service.artifact_path)
    artifact_path = tmp_path / "invalid-model.joblib"
    service = ModelService(artifact_path)
    payloads = [
        {"format_version": 2},
        {**original, "features": list(reversed(FEATURE_COLUMNS))},
        {**original, "metadata": {**original["metadata"], "evaluation": None}},
        {**original, "threshold": float("nan")},
        {**original, "pipeline": None},
    ]
    for payload in payloads:
        joblib.dump(payload, artifact_path)
        assert service.load() is False
        assert service.loaded is False
        assert service.load_error

    artifact_path.write_bytes(b"not a joblib artifact")
    assert service.load() is False
    assert service.loaded is False
    assert service.load_error


def test_invalid_model_artifact_makes_analysis_unavailable(client, tmp_path, monkeypatch):
    artifact_path = tmp_path / "invalid-model.joblib"
    artifact_path.write_bytes(b"invalid artifact")
    monkeypatch.setattr(model_service, "artifact_path", artifact_path)
    assert model_service.load() is False
    assert client.get("/api/v1/health").json()["model_loaded"] is False
    assert upload(client, _csv([_row(0, 0)]), endpoint="analyze").status_code == 503


def test_concurrent_inference_uses_worker_threads(client, monkeypatch):
    original_predict = model_service.predict
    guard = threading.Lock()
    active = 0
    max_active = 0
    caller_thread = threading.get_ident()
    worker_threads: set[int] = set()

    def delayed_predict(features):
        nonlocal active, max_active
        thread_id = threading.get_ident()
        with guard:
            active += 1
            max_active = max(max_active, active)
            worker_threads.add(thread_id)
        try:
            time.sleep(0.12)
            return original_predict(features)
        finally:
            with guard:
                active -= 1

    monkeypatch.setattr(model_service, "predict", delayed_predict)
    content = _csv([_row(0, 0), _row(1, 1)])
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: upload(client, content, endpoint="analyze"), range(4)))

    assert all(response.status_code == 200 for response in responses)
    assert max_active >= 2
    assert worker_threads
    assert caller_thread not in worker_threads


def test_cors(client):
    response = client.options("/api/v1/traffic/validate", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/traffic/validate", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 400


@pytest.mark.parametrize('delimiter', [',', ';', '\t', '|'])
@pytest.mark.parametrize('bom', [False, True])
def test_utf8_csv_dialects_and_quoted_fields(client, delimiter, bom):
    columns = list(reversed(FEATURE_COLUMNS)) + ['note']
    row = _row(0, 0)
    row['note'] = 'Unicode café; comma, tab\t pipe| and a quoted "value"\nsecond line'
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, delimiter=delimiter)
    writer.writeheader()
    writer.writerow({column: row[column] for column in columns})
    content = stream.getvalue().encode('utf-8-sig' if bom else 'utf-8')
    assert upload(client, content).status_code == 200
    assert upload(client, content, endpoint='analyze').json()['total_flows'] == 1


def test_ragged_rows_rejected_before_inference(client):
    content = _csv([_row(0, 0)]).rstrip() + b',extra\n'
    response = upload(client, content, endpoint='analyze')
    assert response.status_code == 422
    assert 'column count' in response.json()['error']['message']


def test_blank_categories_use_training_fitted_imputation(client):
    pipeline, _, _ = model_service.require_loaded()
    modes = pipeline.named_steps['preprocess'].named_transformers_['categorical'].named_steps['imputer'].statistics_
    blank, filled = _row(0, 0), _row(0, 0)
    for feature, mode in zip(CATEGORICAL_FEATURES, modes):
        blank[feature] = ''
        filled[feature] = mode
    first = upload(client, _csv([blank]), endpoint='analyze')
    second = upload(client, _csv([filled]), endpoint='analyze')
    assert first.status_code == second.status_code == 200
    assert first.json()['predictions'] == second.json()['predictions']

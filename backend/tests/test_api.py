from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.model_service import model_service
from ml.schema import FEATURE_COLUMNS


HEADER = ",".join(FEATURE_COLUMNS).encode()
GOOD = HEADER + b"\n2.15,0.38,0,6.58,0.52,0,0,0\n1.42,10.74,0,7.55,0.65,10,167,1\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", tmp_path / "test.db")
    with TestClient(app) as test_client:
        yield test_client


def upload(client, content, name="measurements.csv", endpoint="validate"):
    return client.post(f"/api/v1/traffic/{endpoint}", files={"file": (name, content, "text/csv")})


def test_health_and_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is True
    assert response.json()["model_version"] == "netsight-rf-v1"
    assert settings.database_path.exists()


def test_model_info_contains_real_evaluation(client):
    response = client.get("/api/v1/model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "netsight-rf-v1"
    assert body["dataset"]["rows"] == 1001
    assert body["features"] == list(FEATURE_COLUMNS)
    assert body["target"]["meaning"] == "network performance anomaly; not an intrusion or malware label"
    metrics = body["evaluation"]["metrics"]
    assert body["evaluation"]["rows"] == 201
    assert metrics["support"]["anomalous"] == 14
    assert metrics["confusion_matrix"]["rows_actual_columns_predicted"] == [[187, 0], [11, 3]]
    assert "not an intrusion" in body["target"]["meaning"]


def test_valid_csv(client):
    response = upload(client, GOOD)
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["schema_name"] == "network-metrics-v1"
    assert body["preview"][0]["throughput"] == "2.15"
    assert "predictions" not in body


def test_extra_label_fields_are_not_prediction_inputs(client):
    content = GOOD.replace(HEADER, HEADER + b",anomaly,anomaly_packet_loss")
    content = content.replace(b"2.15,0.38,0,6.58,0.52,0,0,0", b"2.15,0.38,0,6.58,0.52,0,0,0,0,0")
    content = content.replace(b"1.42,10.74,0,7.55,0.65,10,167,1", b"1.42,10.74,0,7.55,0.65,10,167,1,1,1")
    response = upload(client, content)
    assert response.status_code == 200
    assert "anomaly" in response.json()["columns"]


def test_real_inference_and_counts_match(client):
    response = upload(client, GOOD, endpoint="analyze")
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "uploaded_csv"
    assert body["filename"] == "measurements.csv"
    assert body["model_version"] == "netsight-rf-v1"
    assert body["total_flows"] == len(body["predictions"]) == 2
    assert body["counts"]["normal"] + body["counts"]["anomalous"] == body["total_flows"]
    assert [prediction["row_id"] for prediction in body["predictions"]] == [1, 2]
    assert all(prediction["label"] in {"normal", "anomalous"} for prediction in body["predictions"])
    assert all(0 <= prediction["anomaly_score"] <= 1 for prediction in body["predictions"])
    assert len(body["preview"]) == 2
    assert "not verified malicious activity" in body["message"]


@pytest.mark.parametrize("content", [
    b"",
    b"x,y\n1,2",
    HEADER,
    GOOD.replace(b"2.15,0.38", b"2.15,-0.38"),
    GOOD.replace(b"2.15,0.38", b"2.15,nan"),
    GOOD.replace(b"2.15,0.38", b"2.15,inf"),
    GOOD.replace(b"2.15,0.38", b"2.15,not-a-number"),
    GOOD.replace(b"0.38", b"0.38,unexpected"),
    b"\xff\xfe",
    GOOD.replace(b"throughput", b"congestion"),
    GOOD.replace(b"throughput,congestion", b"throughput,throughput"),
])
def test_bad_csv(client, content):
    response = upload(client, content)
    assert response.status_code == 422
    assert response.json()["error"]["message"]


def test_upload_limits(client, monkeypatch):
    assert upload(client, GOOD, "measurements.txt").status_code == 415
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    assert upload(client, GOOD).status_code == 413


def test_row_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_rows", 1)
    assert upload(client, GOOD).status_code == 422


def test_missing_file(client):
    assert client.post("/api/v1/traffic/validate").status_code == 422


def test_model_unavailable_returns_503(client, tmp_path, monkeypatch):
    original_path = model_service.artifact_path
    try:
        monkeypatch.setattr(model_service, "artifact_path", tmp_path / "missing-model.joblib")
        assert model_service.load() is False
        assert client.get("/api/v1/health").json()["model_loaded"] is False
        assert client.get("/api/v1/model/info").status_code == 503
        assert upload(client, GOOD, endpoint="analyze").status_code == 503
    finally:
        monkeypatch.setattr(model_service, "artifact_path", original_path)
        assert model_service.load() is True


def test_cors(client):
    response = client.options("/api/v1/traffic/validate", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/traffic/validate", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 400

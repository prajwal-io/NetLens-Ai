import csv
import io
from pathlib import Path
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import joblib
import numpy as np
import pandas as pd
import pytest
import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.auth import Principal, require_user
from app.main import app
from app.services.model_service import ModelService, model_service
from app.services import history
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.l2 import Ether
from scapy.utils import wrpcap
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
            "threshold": 0.5,
            "metrics": {
                "accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1": 1.0,
                "average_precision": 1.0,
                "roc_auc": 1.0,
                "false_positive_rate": 0.0,
                "specificity": 1.0,
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


def test_ready_requires_supabase_tables_when_supabase_storage_is_selected(client, monkeypatch):
    class StorageClient:
        async def get(self, path, *, params, headers, timeout):
            assert path == "/rest/v1/analyses"
            assert params == {"select": "analysis_id", "limit": "0"}
            assert headers == {"apikey": "sb_secret_test"}
            return httpx.Response(404)

    original_client = app.state.supabase_auth_client
    monkeypatch.setattr(settings, "storage_backend", "supabase")
    monkeypatch.setattr(settings, "supabase_secret_key", "sb_secret_test")
    app.state.supabase_auth_client = StorageClient()
    try:
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert "apply the database migrations" in response.json()["error"]["message"]
    finally:
        app.state.supabase_auth_client = original_client


def test_analysis_endpoints_require_a_bearer_session(client):
    override = app.dependency_overrides.pop(require_user)
    try:
        for path in (
            "/api/v1/analyses", "/api/v1/analyses/private", "/api/v1/analyses/private/export.csv",
            "/api/v1/analyses/private/report.pdf", "/api/v1/analyses/private/flows/1",
            "/api/v1/analyses/private/response-decisions", "/api/v1/replays",
            "/api/v1/replays/normal-benchmark/download",
        ):
            response = client.get(path)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
        for method, path in (
            ("post", "/api/v1/traffic/validate"), ("post", "/api/v1/traffic/analyze"),
            ("post", "/api/v1/traffic/pcap/analyze"), ("post", "/api/v1/url/check"),
            ("post", "/api/v1/replays/demo/analyze"), ("put", "/api/v1/analyses/private/flows/1/response"),
            ("delete", "/api/v1/analyses/private"), ("delete", "/api/v1/analyses/private/flows/1/response"),
        ):
            kwargs = {"files": {"file": ("flows.csv", _csv([_row(0, 0)]), "text/csv")}} if method == "post" and "traffic" in path else {}
            if method == "put":
                kwargs["json"] = {"decision": "dismissed"}
            response = getattr(client, method)(path, **kwargs)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
        assert client.get("/api/v1/health").status_code == 200
    finally:
        app.dependency_overrides[require_user] = override


def test_supabase_verifies_token_and_rejects_expired_sessions(client, monkeypatch):
    class AuthClient:
        async def get(self, path, headers):
            assert path == "/auth/v1/user"
            assert headers["apikey"] == "public-test-key"
            if headers["Authorization"] == "Bearer expired-token":
                return httpx.Response(401)
            if headers["Authorization"] == "Bearer unavailable-token":
                return httpx.Response(503)
            return httpx.Response(200, json={"id": "2a17d1c4-b2a8-4da5-976d-f5d46078b756"})

        async def aclose(self):
            return None

    override = app.dependency_overrides.pop(require_user)
    monkeypatch.setattr(settings, "supabase_url", "https://auth.example.test")
    monkeypatch.setattr(settings, "supabase_publishable_key", "public-test-key")
    app.state.supabase_auth_client = AuthClient()
    try:
        assert client.get("/api/v1/analyses", headers={"Authorization": "Bearer valid-token"}).status_code == 200
        expired = client.get("/api/v1/analyses", headers={"Authorization": "Bearer expired-token"})
        assert expired.status_code == 401
        assert expired.headers["www-authenticate"] == "Bearer"
        assert client.get("/api/v1/analyses", headers={"Authorization": "Bearer unavailable-token"}).status_code == 503
    finally:
        app.dependency_overrides[require_user] = override


def test_sqlite_analysis_data_is_isolated_between_users(client):
    first = upload(client, _csv([_row(0, 0), _row(1, 1)]), endpoint="analyze").json()
    user_a = app.dependency_overrides[require_user]
    user_b = lambda: Principal("6c6bf789-1f19-40cd-86ef-88e79ca2b680", "another-token")
    app.dependency_overrides[require_user] = user_b
    try:
        assert client.get("/api/v1/analyses").json()["total"] == 0
        assert client.get(f"/api/v1/analyses/{first['analysis_id']}").status_code == 404
        assert client.get(f"/api/v1/analyses/{first['analysis_id']}/export.csv").status_code == 404
        assert client.get(f"/api/v1/analyses/{first['analysis_id']}/report.pdf").status_code == 404
        assert client.get(f"/api/v1/analyses/{first['analysis_id']}/flows/1").status_code == 404
        assert client.get(f"/api/v1/analyses/{first['analysis_id']}/response-decisions").status_code == 404
        assert client.delete(f"/api/v1/analyses/{first['analysis_id']}").status_code == 404
    finally:
        app.dependency_overrides[require_user] = user_a
    assert client.get(f"/api/v1/analyses/{first['analysis_id']}").status_code == 200


def test_supabase_storage_sends_verified_user_token_and_owner_filter(monkeypatch):
    from app.core.auth import Principal

    requested = []
    transport = httpx.MockTransport(lambda request: requested.append(request) or httpx.Response(
        200, json=[{"analysis_id": "owned", "filename": "flows.csv", "created_at": "2026-11-18T00:00:00Z",
                    "source_type": "uploaded_csv", "model_version": "v4", "total_flows": 2,
                    "counts": {"normal": 1, "malicious": 1}}], headers={"Content-Range": "0-0/1"},
    ))
    client_type = httpx.Client
    monkeypatch.setattr(history.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    monkeypatch.setattr(settings, "storage_backend", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://project.example.test")
    monkeypatch.setattr(settings, "supabase_publishable_key", "sb_publishable_public-only")
    result = history.list_analyses(10, 0, Principal("2a17d1c4-b2a8-4da5-976d-f5d46078b756", "user-jwt"))
    assert result["total"] == 1
    assert result["items"][0]["analysis_id"] == "owned"
    assert len(requested) == 1
    assert requested[0].headers["authorization"] == "Bearer user-jwt"
    assert requested[0].headers["apikey"] == "sb_publishable_public-only"
    assert "user_id=eq.2a17d1c4-b2a8-4da5-976d-f5d46078b756" in str(requested[0].url)


def test_supabase_analysis_writes_use_server_key_and_verified_owner(monkeypatch):
    requested = []
    analysis = history.AnalysisResponse(
        analysis_id="server-owned", filename="flows.csv", model_version="v1", threshold=0.5,
        total_flows=1, counts={"normal": 1, "malicious": 0},
        predictions=[{"row_id": 1, "label": "normal", "malicious_score": 0.1}], preview=[],
        score_definition="test", message="test",
    )
    transport = httpx.MockTransport(lambda request: requested.append(request) or httpx.Response(200, json=analysis.model_dump(mode="json")))
    client_type = httpx.Client
    monkeypatch.setattr(history.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    monkeypatch.setattr(settings, "storage_backend", "supabase")
    monkeypatch.setattr(settings, "supabase_url", "https://project.example.test")
    monkeypatch.setattr(settings, "supabase_publishable_key", "sb_publishable_public-only")
    monkeypatch.setattr(settings, "supabase_secret_key", "sb_secret_server-only")

    saved = history.save(analysis, Principal("2a17d1c4-b2a8-4da5-976d-f5d46078b756", "user-jwt"), [{"dur": 0.1}])

    assert saved.analysis_id == "server-owned"
    assert len(requested) == 1
    assert requested[0].headers["apikey"] == "sb_secret_server-only"
    assert "authorization" not in requested[0].headers
    assert requested[0].read().decode("utf-8").find('"p_user_id":"2a17d1c4-b2a8-4da5-976d-f5d46078b756"') >= 0


def test_supabase_legacy_service_role_key_is_sent_as_bearer(monkeypatch):
    requested = []
    transport = httpx.MockTransport(lambda request: requested.append(request) or httpx.Response(200, json=[]))
    client_type = httpx.Client
    monkeypatch.setattr(history.httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    monkeypatch.setattr(settings, "supabase_url", "https://project.example.test")
    monkeypatch.setattr(settings, "supabase_publishable_key", "sb_publishable_public-only")
    monkeypatch.setattr(settings, "supabase_secret_key", "legacy-service-role-jwt")

    history._rest(Principal("2a17d1c4-b2a8-4da5-976d-f5d46078b756", "ignored-token"),
                  "GET", "analyses", server_write=True)

    assert requested[0].headers["apikey"] == "legacy-service-role-jwt"
    assert requested[0].headers["authorization"] == "Bearer legacy-service-role-jwt"


def test_cors_preflight_allows_analyst_response_updates(client):
    response = client.options(
        "/api/v1/analyses/example/flows/1/response",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
    assert "PUT" in response.headers["access-control-allow-methods"]


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
    _csv([{**_row(0, 0), NUMERIC_FEATURES[0]: "1e308"}]),
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


def test_upload_body_limit_applies_before_multipart_parsing_without_content_length():
    import asyncio
    from app.main import UploadBodyLimitMiddleware

    sent = []
    chunks = iter((
        {"type": "http.request", "body": b"123", "more_body": True},
        {"type": "http.request", "body": b"456", "more_body": True},
    ))

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        raise AssertionError("Oversized body reached FastAPI multipart parsing")

    scope = {"type": "http", "method": "POST", "path": "/api/v1/traffic/analyze", "headers": []}
    asyncio.run(UploadBodyLimitMiddleware(downstream, limit=5)(scope, receive, send))
    assert sent[0]["status"] == 413


def test_upload_body_limit_rejects_invalid_or_oversized_content_length_without_reading():
    import asyncio
    from app.main import UploadBodyLimitMiddleware

    async def downstream(scope, receive, send):
        raise AssertionError("Invalid or oversized upload reached FastAPI")

    for value, expected in ((b"6", 413), (b"unknown", 400)):
        sent = []

        async def receive():
            raise AssertionError("Request body should not be read")

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "method": "POST", "path": "/api/v1/traffic/analyze",
                 "headers": [(b"content-length", value)]}
        asyncio.run(UploadBodyLimitMiddleware(downstream, limit=5)(scope, receive, send))
        assert sent[0]["status"] == expected


def test_url_check_requires_authenticated_supabase_session(client):
    override = app.dependency_overrides.pop(require_user)
    try:
        response = client.post("/api/v1/url/check", json={"url": "https://example.com/"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    finally:
        app.dependency_overrides[require_user] = override


def test_url_check_endpoint_returns_backend_model_probe_and_stages(client, monkeypatch):
    from app.services import url_check

    expected = {
        "url": "https://example.com/", "host": "example.com",
        "model": {"model_version": "test-url-model", "label": "no_strong_signal", "phishing_score": 0.1, "threshold": 0.5},
        "probe": {"status": "reachable", "http_status": 200, "final_host": "example.com", "dns_address_count": 1, "redirects": []},
        "findings": ["test evidence"], "stages": [{"name": "Evidence summary", "duration_ms": 0.1, "status": "complete"}],
        "limitations": ["test limitation"],
    }
    monkeypatch.setattr(url_check, "check_url", lambda value: expected if value == expected["url"] else None)
    response = client.post("/api/v1/url/check", json={"url": expected["url"]})
    assert response.status_code == 200
    assert response.json() == expected


def test_json_api_body_limit_applies_without_content_length():
    import asyncio
    from app.main import UploadBodyLimitMiddleware

    sent = []
    chunks = iter((
        {"type": "http.request", "body": b"123", "more_body": True},
        {"type": "http.request", "body": b"456", "more_body": True},
    ))

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    async def downstream(scope, receive, send):
        raise AssertionError("Oversized JSON reached FastAPI parsing")

    scope = {"type": "http", "method": "POST", "path": "/api/v1/url/check", "headers": []}
    asyncio.run(UploadBodyLimitMiddleware(downstream, limit=1024, api_limit=5)(scope, receive, send))
    assert sent[0]["status"] == 413


def test_row_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_rows", 1)
    assert upload(client, _csv([_row(0, 0), _row(1, 1)])).status_code == 422


def test_missing_file(client):
    response = client.post("/api/v1/traffic/validate")
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "A CSV file is required in the multipart 'file' field."


def test_non_upload_validation_errors_are_not_misreported_as_csv_errors(client):
    response = client.get("/api/v1/analyses?limit=0")
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Request parameters or fields are invalid."


def test_model_unavailable_returns_503(client, tmp_path, monkeypatch):
    original_path = model_service.artifact_path
    try:
        monkeypatch.setattr(model_service, "artifact_path", tmp_path / "missing-model.joblib")
        assert model_service.load() is False
        assert client.get("/api/v1/health").status_code == 503
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
        {**original, "metadata": {**original["metadata"], "evaluation": {**original["metadata"]["evaluation"], "metrics": {}}}},
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
    assert client.get("/api/v1/health").status_code == 503
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


def _capture_file(path):
    packets = [
        Ether() / IP(src="192.0.2.10", dst="198.51.100.20") / TCP(sport=51514, dport=443, flags="S"),
        Ether() / IP(src="198.51.100.20", dst="192.0.2.10") / TCP(sport=443, dport=51514, flags="SA"),
        Ether() / IP(src="192.0.2.10", dst="198.51.100.20") / TCP(sport=51514, dport=443, flags="A"),
        Ether() / IP(src="192.0.2.10", dst="198.51.100.53") / UDP(sport=53000, dport=53),
        Ether() / IP(src="198.51.100.53", dst="192.0.2.10") / UDP(sport=53, dport=53000),
    ]
    for index, packet in enumerate(packets):
        packet.time = 1731434400 + index * 0.25
    wrpcap(str(path), packets)
    return path.read_bytes()


def test_pcap_upload_extracts_bidirectional_packet_flows(client, tmp_path):
    capture = _capture_file(tmp_path / "sample.pcap")
    response = client.post("/api/v1/traffic/pcap/analyze", files={"file": ("sample.pcap", capture, "application/vnd.tcpdump.pcap")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["packets_seen"] == 5
    assert body["supported_packets"] == 5
    assert body["flow_count"] == 2
    tcp = next(flow for flow in body["flows"] if flow["protocol"] == "TCP")
    assert (tcp["source_packets"], tcp["destination_packets"]) == (2, 1)
    assert tcp["source"] == "192.0.2.10:51514"
    assert tcp["destination"] == "198.51.100.20:443"
    assert any("not sent to the ML classifier" in item for item in body["limitations"])


def test_bundled_packet_demo_capture_is_analyzable(client):
    capture = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo-capture.pcap"
    response = client.post("/api/v1/traffic/pcap/analyze", files={"file": (capture.name, capture.read_bytes(), "application/octet-stream")})
    assert response.status_code == 200
    assert response.json()["flow_count"] == 2


def test_pcap_upload_rejects_invalid_files_and_packet_overflow(client, tmp_path, monkeypatch):
    assert client.post("/api/v1/traffic/pcap/analyze", files={"file": ("bad.csv", b"not a pcap", "text/csv")}).status_code == 415
    invalid = client.post("/api/v1/traffic/pcap/analyze", files={"file": ("bad.pcap", b"not a pcap", "application/octet-stream")})
    assert invalid.status_code == 422
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    too_large = client.post("/api/v1/traffic/pcap/analyze", files={"file": ("large.pcap", b"x" * 11, "application/octet-stream")})
    assert too_large.status_code == 413
    monkeypatch.setattr(settings, "max_upload_bytes", 5 * 1024 * 1024)
    monkeypatch.setattr(settings, "max_capture_packets", 2)
    overflow = client.post("/api/v1/traffic/pcap/analyze", files={"file": ("many.pcap", _capture_file(tmp_path / "many.pcap"), "application/octet-stream")})
    assert overflow.status_code == 413


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

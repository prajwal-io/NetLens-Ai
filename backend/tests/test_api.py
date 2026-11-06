import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

GOOD = b"Destination Port,Flow Duration,Total Fwd Packets,Total Backward Packets\n443,120,2,3\n"

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", tmp_path / "test.db")
    with TestClient(app) as client:
        yield client

def upload(client, content, name="flows.csv"):
    return client.post("/api/v1/traffic/validate", files={"file": (name, content, "text/csv")})

def test_health_and_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is False
    assert settings.database_path.exists()

def test_valid_csv(client):
    response = upload(client, GOOD)
    assert response.status_code == 200
    assert response.json()["row_count"] == 1
    assert response.json()["preview"][0]["Destination Port"] == "443"
    assert "predictions" not in response.json()

@pytest.mark.parametrize("content", [
    b"", b"x,y\n1,2", GOOD.split(b"\n")[0],
    GOOD.replace(b"443,120", b"70000,120"),
    GOOD.replace(b"443,120", b"443,nan"),
    GOOD.replace(b"2,3", b"-2,3"),
    GOOD.replace(b"2,3", b"2.5,3"),
    GOOD.replace(b"2,3", b"2"),
    GOOD.replace(b"2,3", b'2,"3'),
    b"\xff\xfe", GOOD.replace(b"Flow Duration",b"Destination Port")
])
def test_bad_csv(client, content):
    response = upload(client, content)
    assert response.status_code == 422
    assert response.json()["error"]["message"]

def test_upload_limits(client, monkeypatch):
    assert upload(client, GOOD, "flows.txt").status_code == 415
    monkeypatch.setattr(settings,"max_upload_bytes",10)
    assert upload(client,GOOD).status_code == 413

def test_row_limit(client, monkeypatch):
    monkeypatch.setattr(settings,"max_rows",0)
    assert upload(client,GOOD).status_code == 422

def test_missing_file(client):
    assert client.post("/api/v1/traffic/validate").status_code == 422

def test_cors(client):
    response = client.options("/api/v1/traffic/validate", headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options("/api/v1/traffic/validate", headers={"Origin":"https://untrusted.example","Access-Control-Request-Method":"POST"})
    assert response.status_code == 400

"""Persistence, replay, topology, export, and failure regressions."""
import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from pypdf import PdfReader
from app.db.database import connect
from app.services import replay
from ml.train import choose_threshold
from test_api import client, _csv, _row


def upload(client, rows=8):
    response = client.post("/api/v1/traffic/analyze", files={"file": ("real-shape.csv", _csv([_row(i, i % 2) for i in range(rows)]), "text/csv")})
    assert response.status_code == 200, response.text
    return response.json()


def test_saved_history_roundtrip_pagination_deletion(client):
    first = upload(client)
    second = upload(client)
    listing = client.get("/api/v1/analyses?limit=1&offset=0").json()
    assert listing["total"] == 2
    assert listing["items"][0]["analysis_id"] == second["analysis_id"]
    assert "predictions" not in listing["items"][0]
    assert client.get(f"/api/v1/analyses/{first['analysis_id']}").json() == first
    detail = client.get(f"/api/v1/analyses/{first['analysis_id']}/flows/8").json()
    assert detail["features"]["proto"] == _row(7, 1)["proto"]
    with connect() as db:
        assert db.execute("SELECT count(*) FROM analysis_flows").fetchone()[0] == 16
    assert client.delete(f"/api/v1/analyses/{first['analysis_id']}").status_code == 204
    assert client.get(f"/api/v1/analyses/{first['analysis_id']}").status_code == 404
    with connect() as db:
        assert db.execute("SELECT count(*) FROM analysis_flows").fetchone()[0] == 8
    assert client.get("/api/v1/analyses?limit=101").status_code == 422
    assert client.get(f"/api/v1/analyses/{second['analysis_id']}/flows/0").status_code == 404


def test_csv_pdf_match_saved_predictions_and_escape_filename(client):
    result = upload(client, 130)
    identifier = result["analysis_id"]
    response = client.get(f"/api/v1/analyses/{identifier}/export.csv")
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == result["total_flows"]
    assert [row["label"] for row in rows] == [row["label"] for row in result["predictions"]]
    assert [float(row["malicious_score"]) for row in rows] == [row["malicious_score"] for row in result["predictions"]]
    response = client.get(f"/api/v1/analyses/{identifier}/report.pdf")
    assert response.headers["content-type"] == "application/pdf"
    pdf = PdfReader(io.BytesIO(response.content))
    assert len(pdf.pages) > 1
    text = "\n".join(page.extract_text() for page in pdf.pages)
    assert f"Total flows: {result['total_flows']}" in text
    assert f"Normal: {result['counts']['normal']}" in text
    assert f"Malicious: {result['counts']['malicious']}" in text
    assert result["model_version"] in text
    assert "130" in text
    assert client.get("/api/v1/analyses/missing/report.pdf").status_code == 404


def contextual_csv(source="192.0.2.1", timestamp="2026-11-09T10:00:00Z"):
    original = list(csv.DictReader(io.StringIO(_csv([_row(0, 0)]).decode())))
    original[0].update(source_ip=source, destination_ip="2001:db8::1", timestamp=timestamp)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=original[0].keys()); writer.writeheader(); writer.writerows(original)
    return output.getvalue().encode()


def test_optional_topology_is_preserved_separate_from_features(client):
    result = client.post("/api/v1/traffic/analyze", files={"file": ("context.csv", contextual_csv())}).json()
    row = result["predictions"][0]
    assert row["source"] == "192.0.2.1"
    assert row["destination"] == "2001:db8::1"
    assert row["timestamp"] == "2026-11-09T10:00:00+00:00"
    assert "source_ip" not in result["preview"][0]["features"]
    plain = upload(client)
    assert plain["predictions"][0]["source"] is None


@pytest.mark.parametrize("source,timestamp", [("=HYPERLINK(1)", "2026-11-09T10:00:00Z"), ("192.0.2.1", "yesterday"), ("192.0.2.1", "2026-11-09T10:00:00")])
def test_invalid_optional_metadata_rejected_before_prediction(client, source, timestamp):
    for endpoint in ("validate", "analyze"):
        assert client.post(f"/api/v1/traffic/{endpoint}", files={"file": ("bad.csv", contextual_csv(source, timestamp))}).status_code == 422
    assert client.get("/api/v1/analyses").json()["total"] == 0


def test_bundled_replays_run_same_model_and_save(client):
    scenarios = client.get("/api/v1/replays").json()["items"]
    assert len(scenarios) == 2
    for scenario in scenarios:
        content, _ = replay.load_scenario(scenario["id"])
        result = client.post(f"/api/v1/replays/{scenario['id']}/analyze").json()
        direct = client.post("/api/v1/traffic/analyze", files={"file": ("same.csv", content)}).json()
        assert result["source_type"] == "historical_replay"
        assert result["replay_id"] == scenario["id"]
        assert result["total_flows"] == scenario["rows"]
        assert result["predictions"] == direct["predictions"]
        assert result["model_version"] == direct["model_version"]
    assert client.post("/api/v1/replays/unknown/analyze").status_code == 404


def test_tampered_replay_is_rejected(client, tmp_path, monkeypatch):
    manifest = json.loads((replay.REPLAY_ROOT / "manifest.json").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / manifest["scenarios"][0]["filename"]).write_text("modified")
    monkeypatch.setattr(replay, "REPLAY_ROOT", tmp_path)
    assert client.post(f"/api/v1/replays/{manifest['scenarios'][0]['id']}/analyze").status_code == 503
    assert client.get("/api/v1/analyses").json()["total"] == 0


def test_concurrent_inference_saves_complete_independent_snapshots(client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: upload(client, 20), range(4)))
    assert len({result["analysis_id"] for result in results}) == 4
    assert client.get("/api/v1/analyses").json()["total"] == 4
    with connect() as db:
        assert db.execute("SELECT count(*) FROM analysis_flows").fetchone()[0] == 80


def test_threshold_policy_recall_tradeoff_and_invalid_inputs():
    actual = [0, 0, 0, 0, 1, 1, 1]
    scores = [0.1, 0.2, 0.4, 0.7, 0.3, 0.6, 0.9]
    strict_threshold, strict = choose_threshold(actual, scores, maximum_false_positive_rate=0)
    loose_threshold, loose = choose_threshold(actual, scores, maximum_false_positive_rate=0.5)
    assert strict["false_positive_rate"] == 0
    assert loose["false_positive_rate"] <= 0.5
    assert loose["recall"] >= strict["recall"]
    assert loose_threshold <= strict_threshold
    for invalid in (float("nan"), -0.1, 1.1):
        with pytest.raises(ValueError):
            choose_threshold([0, 1], [0.1, invalid])


def test_threshold_rejects_fractional_labels():
    with pytest.raises(ValueError, match="both binary classes"):
        choose_threshold([0.2, 1], [0.1, 0.9])

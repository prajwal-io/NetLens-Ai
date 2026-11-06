from datetime import datetime, timedelta, timezone

import joblib
import pandas as pd

from ml.evaluate import evaluate
from ml.schema import FEATURE_COLUMNS
from ml.train import train


def test_train_selects_without_label_leakage_and_evaluates_holdout(tmp_path):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(100):
        anomalous = int(index % 5 == 0)
        row = {
            "timestamp": (start + timedelta(minutes=index)).isoformat(),
            "throughput": 0.5 + index * 0.002 if anomalous else 1.5 + index * 0.002,
            "congestion": 20.0 + index * 0.01 if anomalous else 2.0 + index * 0.01,
            "packet_loss": 5.0 if anomalous else 0.0,
            "latency": 40.0 + index * 0.1 if anomalous else 6.0 + index * 0.01,
            "jitter": 2.0 if anomalous else 0.4,
            "Percentage video occupancy": 50 if anomalous else 5,
            "Bitrate video": 800 if anomalous else 150,
            "Number videos": 2 if anomalous else 1,
            "anomaly": anomalous,
            "anomaly_packet_loss": anomalous,
        }
        rows.append(row)

    source = tmp_path / "labeled.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    artifact_path = tmp_path / "model.joblib"
    artifact = train(source, artifact_path)

    assert artifact["features"] == list(FEATURE_COLUMNS)
    assert "anomaly" not in artifact["features"]
    assert "anomaly_packet_loss" not in artifact["features"]
    assert artifact["metadata"]["evaluation"] is None

    metadata = evaluate(source, artifact_path)
    assert metadata["evaluation"]["rows"] == 20
    assert metadata["evaluation"]["metrics"]["support"] == {"normal": 16, "anomalous": 4}
    assert 0 <= metadata["evaluation"]["metrics"]["f1"] <= 1
    saved = joblib.load(artifact_path)
    assert saved["metadata"]["evaluation"] is not None
    assert (tmp_path / "model.json").is_file()

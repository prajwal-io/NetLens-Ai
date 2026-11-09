"""Optional real-benchmark upload test; requires locally downloaded data/model."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.model_service import model_service
from ml.dataset import DATASET_ROOT, OFFICIAL_SPLIT_EXPECTATIONS, verify_split_file
from ml.schema import FEATURE_COLUMNS, TEST_FILENAME


def test_real_heldout_csv_uses_installed_model(tmp_path, monkeypatch):
    source = DATASET_ROOT / TEST_FILENAME
    if not source.is_file() or not model_service.artifact_path.is_file():
        pytest.skip('Real dataset and evaluated local artifact required.')
    verify_split_file(source, 'test', OFFICIAL_SPLIT_EXPECTATIONS[TEST_FILENAME])
    frame = pd.read_csv(source).sample(n=1000, random_state=2026)
    content = frame.to_csv(index=False).encode('utf-8-sig')
    monkeypatch.setattr(settings, 'database_path', tmp_path / 'real-upload.db')
    with TestClient(app) as client:
        health = client.get('/api/v1/health').json()
        assert health['model_loaded']
        validated = client.post('/api/v1/traffic/validate', files={'file': ('real-heldout.csv', content, 'text/csv')})
        assert validated.status_code == 200 and validated.json()['row_count'] == 1000
        response = client.post('/api/v1/traffic/analyze', files={'file': ('real-heldout.csv', content, 'text/csv')})
        assert response.status_code == 200
        result = response.json()
        labels, scores, metadata, _ = model_service.predict(frame.loc[:, FEATURE_COLUMNS])
        assert result['model_version'] == metadata['model_version']
        assert result['counts'] == {'normal': int((labels == 0).sum()), 'malicious': int((labels == 1).sum())}
        np.testing.assert_allclose([row['malicious_score'] for row in result['predictions']], scores)
        assert [row['label'] for row in result['predictions']] == ['malicious' if label else 'normal' for label in labels]

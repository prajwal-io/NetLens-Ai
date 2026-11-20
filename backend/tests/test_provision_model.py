from hashlib import sha256
from io import BytesIO

import pytest

from scripts import provision_model


class ArtifactResponse(BytesIO):
    def geturl(self):
        return "https://artifacts.example.test/model.joblib"


def test_provision_model_requires_configuration_for_missing_deployment_artifact(tmp_path):
    with pytest.raises(RuntimeError, match="ARTIFACT_URL"):
        provision_model.provision_model(tmp_path / "missing.joblib", None, None)


def test_provision_model_downloads_and_verifies_artifact(tmp_path, monkeypatch):
    content = b"trusted model artifact"
    monkeypatch.setattr(provision_model, "urlopen", lambda request, timeout: ArtifactResponse(content))
    artifact = tmp_path / "models" / "model.joblib"

    provision_model.provision_model(artifact, "https://artifacts.example.test/model.joblib", sha256(content).hexdigest())

    assert artifact.read_bytes() == content


def test_provision_model_keeps_existing_file_when_digest_is_wrong(tmp_path, monkeypatch):
    monkeypatch.setattr(provision_model, "urlopen", lambda request, timeout: ArtifactResponse(b"tampered"))
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"previous")

    with pytest.raises(RuntimeError, match="SHA-256"):
        provision_model.provision_model(artifact, "https://artifacts.example.test/model.joblib", "a" * 64)

    assert artifact.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [artifact]

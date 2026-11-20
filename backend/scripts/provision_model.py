"""Download and verify the evaluated model artifact before deployment startup."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.core.config import settings

MAX_ARTIFACT_BYTES = 100 * 1024 * 1024


def provision_model(path: Path, url: str | None, expected_sha256: str | None) -> None:
    if not url or not expected_sha256:
        raise RuntimeError("Set NETSIGHT_MODEL_ARTIFACT_URL and NETSIGHT_MODEL_ARTIFACT_SHA256 before starting the deployed API.")
    if urlparse(url).scheme != "https" or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise RuntimeError("The model artifact requires an HTTPS URL and a 64-character SHA-256 digest.")

    expected = expected_sha256.lower()
    if path.is_file() and _sha256(path) == expected:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    digest = hashlib.sha256()
    size = 0
    try:
        request = Request(url, headers={"User-Agent": "NetLens-Model-Provisioner/1.0"})
        with urlopen(request, timeout=60) as response:
            if urlparse(response.geturl()).scheme != "https":
                raise RuntimeError("The model artifact download redirected to a non-HTTPS URL.")
            with NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary_path = Path(output.name)
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_ARTIFACT_BYTES:
                        raise RuntimeError("The model artifact exceeds the 100 MB download limit.")
                    digest.update(chunk)
                    output.write(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError("The downloaded model artifact SHA-256 does not match the configured digest.")
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    provision_model(settings.model_artifact_path, settings.model_artifact_url, settings.model_artifact_sha256)

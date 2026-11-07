"""Download pinned UNSW-NB15 benchmark split files for academic research."""

from __future__ import annotations

import csv
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ml.dataset import DATASET_ROOT
from ml.schema import (
    DATASET_SOURCE,
    EXPECTED_TEST_ROWS,
    EXPECTED_TRAIN_ROWS,
    MIRROR_COMMIT,
    MIRROR_SOURCE,
    REMOTE_TESTING_CONTENT,
    REMOTE_TRAINING_CONTENT,
    TEST_FILENAME,
    TRAINING_FILENAME,
)


def _download(name: str, destination: Path) -> None:
    url = f"https://media.githubusercontent.com/media/jamshaid120/UNSW_NB15-Complete-dataset/{MIRROR_COMMIT}/{name}"
    request = urllib.request.Request(url, headers={"User-Agent": "NetSight-AI academic dataset setup"})
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            if response.status != 200:
                raise RuntimeError(f"Dataset download returned HTTP {response.status} for {name}.")
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(destination)
    except (OSError, urllib.error.URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {name}: {exc}") from exc


def _csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
            if not header or "label" not in header:
                raise ValueError(f"Downloaded file {path.name} has no label column.")
            return sum(1 for row in reader if row)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"Downloaded file {path.name} is not a readable CSV: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)
    print("Downloading pinned UNSW-NB15 split files…", flush=True)
    # The public mirror labels the two standard CSV files in reverse. Check the
    # canonical row counts and normalize names so downstream code never relies
    # on the mirror's swapped filenames.
    sources = (
        (REMOTE_TRAINING_CONTENT, TRAINING_FILENAME, EXPECTED_TRAIN_ROWS),
        (REMOTE_TESTING_CONTENT, TEST_FILENAME, EXPECTED_TEST_ROWS),
    )
    manifest_files: dict[str, dict[str, object]] = {}
    for remote_name, local_name, expected_rows in sources:
        target = DATASET_ROOT / local_name
        _download(remote_name, target)
        rows = _csv_rows(target)
        if rows != expected_rows:
            target.unlink(missing_ok=True)
            raise ValueError(
                f"Expected {expected_rows:,} records in {local_name}, found {rows:,}. "
                "The pinned mirror content does not match the canonical UNSW split."
            )
        digest = _sha256(target)
        manifest_files[local_name] = {
            "mirror_filename": remote_name,
            "rows": rows,
            "bytes": target.stat().st_size,
            "sha256": digest,
        }
        print(f"Verified {local_name}: {rows:,} rows / SHA-256 {digest}", flush=True)

    manifest = {
        "dataset": "UNSW-NB15",
        "dataset_source": DATASET_SOURCE,
        "mirror_source": MIRROR_SOURCE,
        "mirror_commit": MIRROR_COMMIT,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "files": manifest_files,
        "note": "Mirror filenames were reversed; local names were normalized by canonical row count.",
    }
    manifest_path = DATASET_ROOT / "download-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Dataset ready at {DATASET_ROOT.resolve()}")
    print("Academic use only; cite the original UNSW-NB15 papers listed in data/README.md.")


if __name__ == "__main__":
    main()

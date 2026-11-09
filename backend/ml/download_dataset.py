"""Download and transactionally install the pinned UNSW-NB15 CSV splits."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from ml.dataset import (
    DATASET_ROOT,
    OFFICIAL_SPLIT_EXPECTATIONS,
    SplitExpectation,
    verify_split_file,
)
from ml.schema import (
    DATASET_SOURCE,
    MIRROR_COMMIT,
    MIRROR_SOURCE,
    REMOTE_TESTING_CONTENT,
    REMOTE_TRAINING_CONTENT,
    TEST_FILENAME,
    TRAINING_FILENAME,
)


@dataclass(frozen=True)
class DownloadSpec:
    remote_filename: str
    local_filename: str
    expectation: SplitExpectation


# The mirror reverses the UNSW filenames. Checksums bind each remote object to
# its canonical local role, so swapping the files cannot silently relabel data.
OFFICIAL_DOWNLOAD_SPECS = (
    DownloadSpec(REMOTE_TRAINING_CONTENT, TRAINING_FILENAME, OFFICIAL_SPLIT_EXPECTATIONS[TRAINING_FILENAME]),
    DownloadSpec(REMOTE_TESTING_CONTENT, TEST_FILENAME, OFFICIAL_SPLIT_EXPECTATIONS[TEST_FILENAME]),
)
MANIFEST_FILENAME = "download-manifest.json"


def _download(
    remote_filename: str,
    destination: Path,
    *,
    mirror_commit: str,
    open_url: Callable[..., Any],
) -> None:
    url = f"https://media.githubusercontent.com/media/jamshaid120/UNSW_NB15-Complete-dataset/{mirror_commit}/{remote_filename}"
    request = urllib.request.Request(url, headers={"User-Agent": "NetSight-AI academic dataset setup"})
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with open_url(request, timeout=120) as response, temporary.open("wb") as output:
            if response.status != 200:
                raise RuntimeError(f"Dataset download returned HTTP {response.status} for {remote_filename}.")
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        os.replace(temporary, destination)
    except (OSError, urllib.error.URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {remote_filename}: {exc}") from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _promote_staged_files(staging_root: Path, destination_root: Path, filenames: Sequence[str]) -> None:
    """Install a fully validated set, restoring the previous set on failure."""
    destination_root.mkdir(parents=True, exist_ok=True)
    backup_root = Path(tempfile.mkdtemp(prefix=f".{destination_root.name}-backup-", dir=destination_root.parent))
    backed_up: list[str] = []
    installed: list[str] = []
    try:
        for filename in filenames:
            destination = destination_root / filename
            if destination.exists():
                os.replace(destination, backup_root / filename)
                backed_up.append(filename)
        for filename in filenames:
            os.replace(staging_root / filename, destination_root / filename)
            installed.append(filename)
    except Exception as exc:
        for filename in reversed(installed):
            (destination_root / filename).unlink(missing_ok=True)
        rollback_complete = True
        for filename in reversed(backed_up):
            try:
                os.replace(backup_root / filename, destination_root / filename)
            except OSError:
                rollback_complete = False
        if not rollback_complete:
            raise RuntimeError(f"Dataset promotion failed; the previous files remain in {backup_root}.") from exc
        shutil.rmtree(backup_root, ignore_errors=True)
        raise
    else:
        shutil.rmtree(backup_root, ignore_errors=True)


def download_dataset(
    destination_root: Path = DATASET_ROOT,
    *,
    specs: Sequence[DownloadSpec] = OFFICIAL_DOWNLOAD_SPECS,
    open_url: Callable[..., Any] | None = None,
    mirror_commit: str = MIRROR_COMMIT,
) -> dict[str, Any]:
    """Stage and verify both official splits before replacing any active file."""
    expected_names = {TRAINING_FILENAME, TEST_FILENAME}
    if len(specs) != 2 or {spec.local_filename for spec in specs} != expected_names:
        raise ValueError("Download must define exactly one training and one testing split.")

    opener = open_url or urllib.request.urlopen
    destination_root = destination_root.resolve()
    destination_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{destination_root.name}-stage-", dir=destination_root.parent) as temporary_dir:
        staging_root = Path(temporary_dir)
        manifest_files: dict[str, dict[str, object]] = {}

        for spec in specs:
            staged_file = staging_root / spec.local_filename
            _download(spec.remote_filename, staged_file, mirror_commit=mirror_commit, open_url=opener)
            verified = verify_split_file(staged_file, spec.local_filename.removesuffix(".csv"), spec.expectation)
            manifest_files[spec.local_filename] = {
                "mirror_filename": spec.remote_filename,
                **verified,
            }
            print(
                f"Staged and verified {spec.local_filename}: {verified['rows']:,} rows / "
                f"SHA-256 {verified['sha256']}",
                flush=True,
            )

        manifest: dict[str, Any] = {
            "dataset": "UNSW-NB15",
            "dataset_source": DATASET_SOURCE,
            "mirror_source": MIRROR_SOURCE,
            "mirror_commit": mirror_commit,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest_files,
            "note": "Mirror filenames are reversed; pinned hashes and canonical row counts verify local split roles.",
        }
        manifest_path = staging_root / MANIFEST_FILENAME
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        _promote_staged_files(
            staging_root,
            destination_root,
            (TRAINING_FILENAME, TEST_FILENAME, MANIFEST_FILENAME),
        )

    print(f"Dataset ready at {destination_root}")
    print("Academic use only; cite the original UNSW-NB15 papers listed in data/README.md.")
    return manifest


def main() -> None:
    print("Downloading pinned UNSW-NB15 split files to a temporary staging directory...", flush=True)
    download_dataset()


if __name__ == "__main__":
    main()

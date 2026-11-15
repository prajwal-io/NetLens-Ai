"""Pinned download and leak-aware loader for the full UNSW-NB15 CSV corpus."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

from ml.schema import FEATURE_COLUMNS, NUMERIC_FEATURES, TARGET_COLUMN


FULL_DATASET_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "unsw-nb15-full"
FULL_DATASET_SOURCE = "https://research.unsw.edu.au/projects/unsw-nb15-dataset"
FULL_DATASET_MIRROR = "https://github.com/jamshaid120/UNSW_NB15-Complete-dataset"
FULL_DATASET_COMMIT = "161024104f19eea98b5c9aba0499a8fcb867ba1d"
FULL_DATASET_ROWS = 2_540_044
DEFAULT_MAX_TRAIN_ROWS = 500_000
FIT_SEED = 42


@dataclass(frozen=True)
class FullFile:
    name: str
    size: int
    sha256: str


FULL_FILES = (
    FullFile("UNSW-NB15_1.csv", 168_979_718, "7d851bbeabd27894ce39c8e78835c73341fc946652fb7743b9eff193b55eb511"),
    FullFile("UNSW-NB15_2.csv", 165_221_021, "6130ad02873cc6069ae695cf2844f2e8c2e9a9a1b7532dd82ab8f202757cacf8"),
    FullFile("UNSW-NB15_3.csv", 154_588_103, "ae990a96c3dfcd425ce2801aadb1727a34d5e0ae6d8215dbcdae60dedfaef640"),
    FullFile("UNSW-NB15_4.csv", 97_588_754, "cdf563692d51d405541dd659ddcdad9fa01f001f05fe9fc4b67f00ca12fbc96a"),
)

# Original UNSW export is headerless. These names follow the official feature
# file; only the model's 42 inputs and binary label are loaded.
RAW_COLUMNS = (
    "srcip", "sport", "dstip", "dsport", "proto", "state", "dur", "sbytes", "dbytes",
    "sttl", "dttl", "sloss", "dloss", "service", "Sload", "Dload", "Spkts", "Dpkts",
    "swin", "dwin", "stcpb", "dtcpb", "smeansz", "dmeansz", "trans_depth", "res_bdy_len",
    "Sjit", "Djit", "Stime", "Ltime", "Sintpkt", "Dintpkt", "tcprtt", "synack", "ackdat",
    "is_sm_ips_ports", "ct_state_ttl", "ct_flw_http_mthd", "is_ftp_login", "ct_ftp_cmd",
    "ct_srv_src", "ct_srv_dst", "ct_dst_ltm", "ct_src_ ltm", "ct_src_dport_ltm",
    "ct_dst_sport_ltm", "ct_dst_src_ltm", "attack_cat", "Label",
)
RAW_TO_MODEL = {
    "dur": "dur", "proto": "proto", "service": "service", "state": "state",
    "Spkts": "spkts", "Dpkts": "dpkts", "sbytes": "sbytes", "dbytes": "dbytes",
    "Sload": "sload", "Dload": "dload", "sttl": "sttl", "dttl": "dttl",
    "sloss": "sloss", "dloss": "dloss", "Sintpkt": "sinpkt", "Dintpkt": "dinpkt",
    "Sjit": "sjit", "Djit": "djit", "swin": "swin", "dwin": "dwin",
    "stcpb": "stcpb", "dtcpb": "dtcpb", "tcprtt": "tcprtt", "synack": "synack",
    "ackdat": "ackdat", "smeansz": "smean", "dmeansz": "dmean",
    "trans_depth": "trans_depth", "res_bdy_len": "response_body_len",
    "ct_srv_src": "ct_srv_src", "ct_state_ttl": "ct_state_ttl",
    "ct_dst_ltm": "ct_dst_ltm", "ct_src_dport_ltm": "ct_src_dport_ltm",
    "ct_dst_sport_ltm": "ct_dst_sport_ltm", "ct_dst_src_ltm": "ct_dst_src_ltm",
    "is_ftp_login": "is_ftp_login", "ct_ftp_cmd": "ct_ftp_cmd",
    "ct_flw_http_mthd": "ct_flw_http_mthd", "ct_src_ ltm": "ct_src_ltm",
    "ct_srv_dst": "ct_srv_dst", "is_sm_ips_ports": "is_sm_ips_ports",
}
RAW_USE_COLUMNS = tuple(RAW_TO_MODEL) + ("Label",)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _boundary_records(path: Path) -> tuple[bytes, bytes]:
    """Return normalized first and last source records without reading the file twice."""
    with path.open("rb") as stream:
        first = stream.readline().rstrip(b"\r\n").lstrip(b"\xef\xbb\xbf")
        stream.seek(0, os.SEEK_END)
        end = stream.tell()
        if end == 0:
            return first, b""
        position = end - 1
        stream.seek(position)
        if stream.read(1) == b"\n":
            position -= 1
        while position > 0:
            stream.seek(position - 1)
            if stream.read(1) == b"\n":
                break
            position -= 1
        stream.seek(position)
        last = stream.readline().rstrip(b"\r\n").lstrip(b"\xef\xbb\xbf")
    return first, last


def _verify_file(path: Path, expected: FullFile) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Full UNSW-NB15 file is missing: {path}. Run `python -m ml.download_full_unsw` first.")
    if path.stat().st_size != expected.size:
        raise ValueError(f"{expected.name} has {path.stat().st_size:,} bytes; expected {expected.size:,}.")
    actual = sha256_file(path)
    if actual != expected.sha256:
        raise ValueError(f"{expected.name} SHA-256 does not match the pinned UNSW-NB15 mirror revision.")


def download_full_dataset(
    destination: Path = FULL_DATASET_ROOT,
    *,
    open_url: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Download and verify all four official full-corpus CSVs before promotion."""
    opener = open_url or urllib.request.urlopen
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".unsw-full-stage-", dir=destination.parent) as temp_name:
        stage = Path(temp_name)
        manifest_files: dict[str, dict[str, Any]] = {}
        for item in FULL_FILES:
            url = f"https://media.githubusercontent.com/media/jamshaid120/UNSW_NB15-Complete-dataset/{FULL_DATASET_COMMIT}/{item.name}"
            request = urllib.request.Request(url, headers={"User-Agent": "NetSight-AI academic dataset setup"})
            target = stage / item.name
            try:
                with opener(request, timeout=180) as response, target.open("wb") as output:
                    if response.status != 200:
                        raise RuntimeError(f"Dataset download returned HTTP {response.status} for {item.name}.")
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            except (OSError, urllib.error.URLError) as exc:
                raise RuntimeError(f"Could not download {item.name}: {exc}") from exc
            _verify_file(target, item)
            manifest_files[item.name] = {"bytes": item.size, "sha256": item.sha256}

        manifest = {
            "dataset": "UNSW-NB15 full CSV corpus",
            "source": FULL_DATASET_SOURCE,
            "mirror": FULL_DATASET_MIRROR,
            "mirror_commit": FULL_DATASET_COMMIT,
            "expected_rows": FULL_DATASET_ROWS,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest_files,
            "academic_use": "Cite the original UNSW-NB15 papers; commercial use requires author agreement.",
        }
        (stage / "download-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        backup = destination.with_name(destination.name + ".backup")
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(stage, destination)
        except Exception:
            if backup.exists() and not destination.exists():
                os.replace(backup, destination)
            raise
        else:
            shutil.rmtree(backup, ignore_errors=True)
    return manifest


def normalize_raw_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Map headerless full-corpus rows to the versioned inference feature contract."""
    missing = set(RAW_USE_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Full UNSW-NB15 rows are missing raw columns: {', '.join(sorted(missing))}.")
    features = raw.loc[:, list(RAW_TO_MODEL)].rename(columns=RAW_TO_MODEL).copy()
    for column in (name for name in NUMERIC_FEATURES if name != "rate"):
        values = features[column].astype("string").str.strip()
        values = values.mask(values.isin(["", "NaN", "nan", "None"]), pd.NA)
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = values.notna() & numeric.isna()
        if invalid.any():
            raise ValueError(f"Full UNSW-NB15 numeric feature {column!r} contains invalid values.")
        features[column] = numeric.replace([np.inf, -np.inf], np.nan)
    for column in ("proto", "service", "state"):
        values = features[column].astype("string").str.strip()
        values = values.mask(values.eq(""), pd.NA)
        features[column] = values.astype(object).where(values.notna(), np.nan)
    # The original four-file corpus omits `rate`; UNSW's prepared split defines
    # it as packet intervals per second, i.e. (Spkts + Dpkts - 1) / dur. A
    # zero-duration flow has no measurable interval rate and is encoded as 0.
    duration = features["dur"].astype("float64")
    packet_intervals = (features["spkts"] + features["dpkts"] - 1).clip(lower=0)
    features["rate"] = np.divide(
        packet_intervals.astype("float64"),
        duration,
        out=np.zeros(len(features), dtype="float64"),
        where=duration.to_numpy() > 0,
    )
    features = features.loc[:, FEATURE_COLUMNS]
    labels = pd.to_numeric(raw["Label"], errors="coerce")
    if labels.isna().any() or not set(labels.unique()).issubset({0, 1}):
        raise ValueError("Full UNSW-NB15 Label column must contain only binary 0/1 values.")
    return features.reset_index(drop=True), labels.astype("int64").reset_index(drop=True).rename(TARGET_COLUMN)


def _feature_hashes(features: pd.DataFrame) -> np.ndarray:
    return pd.util.hash_pandas_object(features.loc[:, FEATURE_COLUMNS], index=False).to_numpy(dtype="uint64")


def exclude_heldout_signatures(
    features: pd.DataFrame,
    labels: pd.Series,
    heldout_test_features: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, int]:
    """Remove supplemental rows with an exact feature signature in the held-out test."""
    test_hashes = set(_feature_hashes(heldout_test_features).tolist())
    keep = ~pd.Series(_feature_hashes(features)).isin(test_hashes).to_numpy()
    return (
        features.loc[keep].reset_index(drop=True),
        labels.loc[keep].reset_index(drop=True),
        int((~keep).sum()),
    )


def load_full_unsw_training(
    data_dir: Path = FULL_DATASET_ROOT,
    *,
    heldout_test_features: pd.DataFrame,
    max_rows: int = DEFAULT_MAX_TRAIN_ROWS,
    chunksize: int = 100_000,
) -> tuple[pd.DataFrame, pd.Series, dict[str, Any]]:
    """Load a reproducible sample after removing exact held-out-test feature matches."""
    if max_rows < 1:
        raise ValueError("max_rows must be a positive integer.")
    if chunksize < 1:
        raise ValueError("chunksize must be a positive integer.")
    data_dir = data_dir.resolve()
    for item in FULL_FILES:
        _verify_file(data_dir / item.name, item)

    selected: pd.DataFrame | None = None
    random = np.random.default_rng(FIT_SEED)
    total_rows = 0
    boundary_duplicate_rows = 0
    excluded_test_matches = 0
    eligible_rows = 0
    usecols = [RAW_COLUMNS.index(name) for name in RAW_USE_COLUMNS]
    previous_last_record: bytes | None = None
    for item in FULL_FILES:
        first_record, last_record = _boundary_records(data_dir / item.name)
        duplicate_boundary = previous_last_record is not None and first_record == previous_last_record
        previous_last_record = last_record
        reader: Iterable[pd.DataFrame] = pd.read_csv(
            data_dir / item.name,
            header=None,
            names=RAW_COLUMNS,
            usecols=usecols,
            chunksize=chunksize,
            encoding="utf-8-sig",
            low_memory=False,
        )
        first_chunk = True
        for raw in reader:
            total_rows += len(raw)
            if first_chunk and duplicate_boundary:
                raw = raw.iloc[1:].reset_index(drop=True)
                boundary_duplicate_rows += 1
            first_chunk = False
            if raw.empty:
                continue
            features, labels = normalize_raw_frame(raw)
            features, labels, excluded = exclude_heldout_signatures(features, labels, heldout_test_features)
            excluded_test_matches += excluded
            if len(features):
                eligible_rows += len(features)
                chunk = features.copy()
                chunk["_label"] = labels.to_numpy()
                chunk["_sample_priority"] = random.random(len(chunk))
                selected = chunk if selected is None else pd.concat([selected, chunk], ignore_index=True)
                if len(selected) > max_rows:
                    positions = np.argpartition(selected["_sample_priority"].to_numpy(), max_rows - 1)[:max_rows]
                    selected = selected.iloc[positions].reset_index(drop=True)

    unique_rows = total_rows - boundary_duplicate_rows
    if unique_rows != FULL_DATASET_ROWS:
        raise ValueError(
            f"Full UNSW-NB15 corpus has {total_rows:,} parsed rows and {boundary_duplicate_rows:,} exact adjacent-file duplicates; "
            f"expected {FULL_DATASET_ROWS:,} unique rows."
        )
    if selected is None:
        raise ValueError("No eligible rows remain in the full UNSW-NB15 corpus after held-out filtering.")
    labels = selected.pop("_label").astype("int64").reset_index(drop=True).rename(TARGET_COLUMN)
    selected.drop(columns=["_sample_priority"], inplace=True)
    features = selected.reset_index(drop=True).loc[:, FEATURE_COLUMNS]
    manifest = json.loads((data_dir / "download-manifest.json").read_text(encoding="utf-8")) if (data_dir / "download-manifest.json").is_file() else None
    stats = {
        "source": FULL_DATASET_SOURCE,
        "mirror": FULL_DATASET_MIRROR,
        "mirror_commit": FULL_DATASET_COMMIT,
        "raw_rows": total_rows,
        "duplicate_boundary_rows_removed": boundary_duplicate_rows,
        "unique_source_rows": unique_rows,
        "rows_matching_heldout_test_removed": excluded_test_matches,
        "eligible_rows_after_test_filter": eligible_rows,
        "rows_used": len(features),
        "max_rows": max_rows,
        "selection_seed": FIT_SEED,
        "selection_method": "streamed uniform sample by seeded random priorities",
        "file_hashes": {item.name: item.sha256 for item in FULL_FILES},
        "download_manifest_present": manifest is not None,
    }
    return features, labels, stats


def main() -> None:
    manifest = download_full_dataset()
    print(json.dumps(manifest, indent=2, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()

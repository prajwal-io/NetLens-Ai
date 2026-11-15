import pandas as pd
import pytest

from ml.full_unsw import RAW_COLUMNS, _boundary_records, exclude_heldout_signatures, normalize_raw_frame
from ml.schema import FEATURE_COLUMNS
from ml.train import _source_anchored_validation_indices


def raw_row(*, duration: float = 2.0, source_packets: int = 3, destination_packets: int = 2, label: int = 0):
    row = {column: 0 for column in RAW_COLUMNS}
    row.update({
        "proto": "tcp",
        "state": "CON",
        "service": "http",
        "dur": duration,
        "Spkts": source_packets,
        "Dpkts": destination_packets,
        "Label": label,
    })
    return row


def test_full_raw_rows_map_to_inference_contract_and_derive_rate():
    raw = pd.DataFrame([raw_row(), raw_row(duration=0.0, source_packets=1, destination_packets=0, label=1)])

    features, labels = normalize_raw_frame(raw)

    assert tuple(features.columns) == FEATURE_COLUMNS
    assert features.loc[0, "rate"] == pytest.approx(2.0)
    assert features.loc[1, "rate"] == 0
    assert labels.tolist() == [0, 1]


def test_full_raw_numeric_features_reject_unparseable_values():
    row = raw_row()
    row["Sload"] = "not-a-rate"
    raw = pd.DataFrame([row])

    with pytest.raises(ValueError, match="numeric feature 'sload'"):
        normalize_raw_frame(raw)


def test_supplemental_rows_matching_heldout_signatures_are_excluded():
    raw = pd.DataFrame([raw_row(label=0), raw_row(duration=4.0, label=1)])
    features, labels = normalize_raw_frame(raw)

    remaining, remaining_labels, removed = exclude_heldout_signatures(
        features,
        labels,
        features.iloc[[0]],
    )

    assert removed == 1
    assert len(remaining) == 1
    assert remaining_labels.tolist() == [1]
    assert remaining.iloc[0]["dur"] == 4.0


def test_csv_boundary_reader_detects_identical_adjacent_export_records(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_bytes(b"first\r\nshared-record\r\n")
    second.write_bytes(b"shared-record\r\nlast\r\n")

    first_boundary = _boundary_records(first)
    second_boundary = _boundary_records(second)

    assert first_boundary == (b"first", b"shared-record")
    assert second_boundary[0] == first_boundary[1]


def test_source_anchored_validation_excludes_matching_supplemental_fit_rows():
    raw = pd.DataFrame([
        {**raw_row(duration=float(index + 1), label=index % 2), "sbytes": index + 100}
        for index in range(40)
    ])
    official_features, official_labels = normalize_raw_frame(raw)
    pooled_features = pd.concat([official_features, official_features.iloc[:10]], ignore_index=True)

    fit_indices, validation_indices, stats = _source_anchored_validation_indices(
        official_features,
        official_labels,
        pooled_features,
    )

    fit_signatures = set(pd.util.hash_pandas_object(pooled_features.iloc[fit_indices], index=False).tolist())
    validation_signatures = set(pd.util.hash_pandas_object(official_features.iloc[validation_indices], index=False).tolist())
    assert len(validation_indices) == 8
    assert validation_signatures.isdisjoint(fit_signatures)
    assert stats["supplemental_validation_signature_rows_excluded_from_fit"] > 0

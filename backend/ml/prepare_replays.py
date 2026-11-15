"""Build deterministic excerpts from the verified official held-out partition.
Run once when updating bundled scenarios; inference never needs raw datasets.
"""
import hashlib
import json
from pathlib import Path
import pandas as pd
from ml.dataset import DATASET_ROOT, OFFICIAL_SPLIT_EXPECTATIONS, verify_split_file
from ml.schema import TEST_FILENAME, DATASET_SOURCE


def main():
    path = DATASET_ROOT / TEST_FILENAME
    verify_split_file(path, "test", OFFICIAL_SPLIT_EXPECTATIONS[TEST_FILENAME])
    frame = pd.read_csv(path)
    root = Path(__file__).resolve().parents[1] / "data" / "replays"
    root.mkdir(parents=True, exist_ok=True)
    scenarios = []
    for identifier, title, description, subset in [
        ("normal-benchmark", "Normal benchmark excerpt", "100 records labeled normal in the official holdout. Model output may differ from ground truth.", frame[frame.label == 0]),
        ("attack-benchmark", "Attack benchmark excerpt", "100 records labeled attack in the official holdout. Model output may differ from ground truth.", frame[frame.label == 1]),
    ]:
        sampled = subset.sample(n=100, random_state=2026).sort_index()
        filename = identifier + ".csv"
        content = sampled.to_csv(index=False, lineterminator="\n").encode("utf-8")
        (root / filename).write_bytes(content)
        scenarios.append({"id": identifier, "title": title, "description": description,
                          "filename": filename, "rows": len(sampled), "sha256": hashlib.sha256(content).hexdigest(),
                          "source": DATASET_SOURCE, "dataset": "UNSW-NB15 (2015)",
                          "source_sha256": OFFICIAL_SPLIT_EXPECTATIONS[TEST_FILENAME].sha256,
                          "source_row_ids": [int(value) for value in sampled.id],
                          "timing": "Sequential playback at a demonstration rate; original timestamps are unavailable."})
    (root / "manifest.json").write_text(json.dumps({"scenarios": scenarios}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

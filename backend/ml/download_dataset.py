"""Download the user-selected public dataset through KaggleHub."""

from __future__ import annotations

import os
from pathlib import Path

from ml.dataset import PROJECT_ROOT
from ml.schema import DATASET_SLUG, LABELED_FILENAME


def main() -> None:
    cache = PROJECT_ROOT / "data" / "kagglehub-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("KAGGLEHUB_CACHE", str(cache))

    import kagglehub

    path = Path(kagglehub.dataset_download(DATASET_SLUG))
    labeled = path / LABELED_FILENAME
    if not labeled.is_file():
        raise FileNotFoundError(
            f"Downloaded dataset is missing {LABELED_FILENAME!r}; found: "
            + ", ".join(sorted(item.name for item in path.iterdir()))
        )
    print(f"Dataset downloaded to: {path}")
    print(f"Training file: {labeled}")


if __name__ == "__main__":
    main()

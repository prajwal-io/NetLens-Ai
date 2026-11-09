"""Quick local check for the FastAPI service and evaluated ML artifact."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI base URL")
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 12):
        print(f"Unsupported Python {sys.version_info.major}.{sys.version_info.minor}; use Python 3.12.", file=sys.stderr)
        return 2

    health_url = f"{args.base_url.rstrip('/')}/api/v1/health"
    try:
        with urlopen(health_url, timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        print(f"API check failed at {health_url}: {exc}", file=sys.stderr)
        return 1

    if health.get("status") != "ok":
        print(f"API returned an unexpected health response: {health}", file=sys.stderr)
        return 1
    if not health.get("model_loaded") or not health.get("model_version"):
        print(
            "API is reachable, but no evaluated model is loaded. Run the documented download, train, and evaluate steps, then restart FastAPI.",
            file=sys.stderr,
        )
        return 1

    print(f"Python {sys.version_info.major}.{sys.version_info.minor}: supported")
    print(f"FastAPI: healthy ({health_url})")
    print(f"Evaluated model: {health['model_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Quick local check for the FastAPI service and evaluated ML artifact."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from app.core.config import settings


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
    except HTTPError as exc:
        if exc.code == 503:
            print("API is reachable but not ready. Confirm the evaluated model artifact is installed.", file=sys.stderr)
        else:
            print(f"API check failed at {health_url}: {exc}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
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

    if not settings.supabase_url or not settings.supabase_publishable_key:
        print(
            "Supabase Auth is not configured. Set NETSIGHT_SUPABASE_URL and NETSIGHT_SUPABASE_PUBLISHABLE_KEY before using protected workspace APIs.",
            file=sys.stderr,
        )
        return 1
    if settings.storage_backend == "supabase" and not settings.supabase_secret_key:
        print("Supabase storage requires NETSIGHT_SUPABASE_SECRET_KEY for backend-only writes.", file=sys.stderr)
        return 1

    print(f"Python {sys.version_info.major}.{sys.version_info.minor}: supported")
    print(f"FastAPI: healthy ({health_url})")
    print(f"Evaluated model: {health['model_version']}")
    print("Supabase Auth configuration: URL and publishable key present; verify sign-in in the browser")
    if settings.storage_backend == "supabase":
        print("Supabase server-side write key: present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

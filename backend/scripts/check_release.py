"""Five offline runtime checks against an already running local API.
Uses bundled real UNSW-NB15 features. Deletes all test analyses on exit.
"""
import argparse
import csv
import io
import math
import os
from pathlib import Path
import httpx
from pypdf import PdfReader
from app.core.config import settings


def authenticate_test_account(email: str, password: str) -> str:
    try:
        response = httpx.post(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_publishable_key},
            json={"email": email, "password": password}, timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise RuntimeError("Could not sign in to Supabase with the configured test account.") from None
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("Supabase did not return an access token for the configured test account.")
    return token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    email, password = os.getenv("NETSIGHT_TEST_EMAIL"), os.getenv("NETSIGHT_TEST_PASSWORD")
    if not email or not password or not settings.supabase_url or not settings.supabase_publishable_key:
        parser.error("Set NETSIGHT_TEST_EMAIL and NETSIGHT_TEST_PASSWORD for a dedicated Supabase test account, and configure the API Supabase URL/key.")
    try:
        token = authenticate_test_account(email, password)
    except RuntimeError as exc:
        parser.error(f"{exc} Check that Auth is available and the credentials are valid.")
    created = []
    with httpx.Client(base_url=args.base_url.rstrip("/") + "/api/v1", timeout=90,
                      headers={"Authorization": f"Bearer {token}"}) as client:
        try:
            def body(response):
                response.raise_for_status()
                return response.json()
            health = body(client.get("/health"))
            assert health["model_loaded"] and health["model_version"]
            assert body(client.get("/model/schema"))["feature_count"] == 42
            print("PASS 1: API and evaluated model available; 42-feature contract")
            path = Path(__file__).resolve().parents[1] / "data" / "replays" / "normal-benchmark.csv"
            content = path.read_bytes()
            valid = body(client.post("/traffic/validate", files={"file": (path.name, content, "text/csv")}))
            assert valid["row_count"] == 100
            print("PASS 2: Real UTF-8 benchmark CSV validation")
            analysis = body(client.post("/traffic/analyze", files={"file": (path.name, content, "text/csv")}))
            identifier = analysis["analysis_id"]; created.append(identifier)
            assert analysis["counts"]["normal"] + analysis["counts"]["malicious"] == 100
            assert body(client.get(f"/analyses/{identifier}")) == analysis
            assert body(client.get(f"/analyses/{identifier}/flows/100"))["features"]
            print("PASS 3: Inference, saved history, and individual flow detail")
            exported = client.get(f"/analyses/{identifier}/export.csv"); exported.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
            assert [row["label"] for row in rows] == [row["label"] for row in analysis["predictions"]]
            report = client.get(f"/analyses/{identifier}/report.pdf"); report.raise_for_status()
            text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(report.content)).pages)
            assert "Total flows: 100" in text and identifier in text
            print("PASS 4: CSV predictions and PDF summary match the stored analysis")
            replay = body(client.post("/replays/normal-benchmark/analyze")); created.append(replay["analysis_id"])
            assert replay["source_type"] == "historical_replay"
            assert [row["label"] for row in replay["predictions"]] == [row["label"] for row in analysis["predictions"]]
            assert all(math.isclose(left["malicious_score"], right["malicious_score"], rel_tol=1e-12, abs_tol=1e-12)
                       for left, right in zip(replay["predictions"], analysis["predictions"], strict=True))
            print("PASS 5: Historical replay uses the same pipeline and predictions")
        finally:
            for identifier in created:
                response = client.delete(f"/analyses/{identifier}")
                response.raise_for_status()
                assert client.get(f"/analyses/{identifier}").status_code == 404


if __name__ == "__main__":
    main()

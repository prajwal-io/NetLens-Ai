"""Copy owned SQLite analyses to Supabase Postgres without deleting the source."""
import json
import sqlite3
import sys
from uuid import UUID

import httpx

from app.core.config import settings
from app.db.database import connect


def transfer_analysis(client: httpx.Client, analysis_id: str, user_id: str,
                      payload: dict, flows: list[dict], decisions: list[dict]) -> bool:
    owner_id = str(UUID(user_id))
    if (payload.get("analysis_id") != analysis_id or payload.get("total_flows") != len(flows)
            or not 1 <= len(flows) <= 10000):
        raise ValueError(f"Analysis {analysis_id} has incomplete or inconsistent saved flow data.")

    existing = client.get("/rest/v1/analyses", params={
        "select": "analysis_id", "analysis_id": f"eq.{analysis_id}", "user_id": f"eq.{owner_id}", "limit": "1",
    })
    existing.raise_for_status()
    copied = not existing.json()
    if copied:
        response = client.post("/rest/v1/rpc/save_analysis", json={
            "p_user_id": owner_id, "p_payload": payload, "p_flows": flows,
        })
        response.raise_for_status()

    if decisions:
        response = client.post("/rest/v1/response_decisions", params={
            "on_conflict": "analysis_id,user_id,row_id",
        }, json=[{**decision, "analysis_id": analysis_id, "user_id": owner_id} for decision in decisions],
           headers={"Prefer": "resolution=ignore-duplicates,return=minimal"})
        response.raise_for_status()
    return copied


def main() -> int:
    if not settings.supabase_url or not settings.supabase_secret_key:
        print("Set NETSIGHT_SUPABASE_URL and backend-only NETSIGHT_SUPABASE_SECRET_KEY before migrating.", file=sys.stderr)
        return 2

    copied = skipped = 0
    headers = {"apikey": settings.supabase_secret_key}
    if not settings.supabase_secret_key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {settings.supabase_secret_key}"
    try:
        with httpx.Client(base_url=settings.supabase_url.rstrip("/"), headers=headers,
                          timeout=httpx.Timeout(60.0, connect=4.0)) as client:
            with connect() as database:
                analyses = database.execute(
                    "SELECT id, user_id, payload FROM analyses WHERE user_id IS NOT NULL ORDER BY created_at, id"
                ).fetchall()
            for analysis_id, user_id, raw_payload in analyses:
                payload = json.loads(raw_payload)
                with connect() as database:
                    rows = database.execute(
                        "SELECT row_id, features FROM analysis_flows WHERE analysis_id = ? ORDER BY row_id",
                        (analysis_id,),
                    ).fetchall()
                    decision_rows = database.execute(
                        "SELECT row_id, decision, decided_at FROM response_decisions WHERE analysis_id = ? ORDER BY row_id",
                        (analysis_id,),
                    ).fetchall()
                flows = [json.loads(features) for _, features in rows]
                if [row_id for row_id, _ in rows] != list(range(1, len(rows) + 1)):
                    raise ValueError(f"Analysis {analysis_id} has nonsequential flow rows.")
                decisions = [{"row_id": row_id, "decision": decision, "decided_at": decided_at}
                             for row_id, decision, decided_at in decision_rows]
                if transfer_analysis(client, analysis_id, user_id, payload, flows, decisions):
                    copied += 1
                else:
                    skipped += 1
    except (httpx.HTTPError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        print(f"Migration stopped: {exc}", file=sys.stderr)
        return 1

    print(f"Supabase migration complete: {copied} copied, {skipped} already present. SQLite source retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

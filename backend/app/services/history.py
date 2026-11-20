"""Owner-scoped analysis history for local SQLite and Supabase Postgres/RLS."""
import json
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.core.auth import Principal
from app.core.config import settings
from app.db.database import connect
from app.schemas.traffic import AnalysisResponse, Prediction, ResponseDecision


def _rest(principal: Principal, method: str, path: str, *, params=None, body=None, headers=None, server_write=False) -> httpx.Response:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(503, detail="Supabase data storage is not configured.")
    key = settings.supabase_secret_key if server_write else settings.supabase_publishable_key
    if not key:
        raise HTTPException(503, detail="Supabase server-side writes are not configured.")
    request_headers = {"apikey": key}
    if server_write and not key.startswith("sb_secret_"):
        request_headers["Authorization"] = f"Bearer {key}"
    elif not server_write:
        request_headers["Authorization"] = f"Bearer {principal.access_token}"
    if headers:
        request_headers.update(headers)
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=4.0)) as client:
            response = client.request(method, f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}",
                                      params=params, json=body, headers=request_headers)
    except httpx.HTTPError as exc:
        raise HTTPException(503, detail="Supabase data storage is unavailable.") from exc
    if response.status_code in (401, 403):
        if server_write:
            raise HTTPException(503, detail="Supabase server-side writes are not authorized.")
        raise HTTPException(401, detail="Your session is invalid or no longer authorized.")
    if response.status_code >= 400:
        raise HTTPException(503, detail="Supabase could not complete the data request.")
    return response


def _supabase() -> bool:
    return settings.storage_backend == "supabase"


def save(analysis: AnalysisResponse, principal: Principal, features: list[dict] | None = None) -> AnalysisResponse:
    if _supabase():
        response = _rest(principal, "POST", "rpc/save_analysis", body={
            "p_user_id": principal.user_id, "p_payload": analysis.model_dump(mode="json"), "p_flows": features or [],
        }, server_write=True)
        return AnalysisResponse.model_validate(response.json())

    with connect() as connection:
        connection.execute("INSERT INTO analyses(id, user_id, created_at, payload) VALUES (?, ?, ?, ?)",
                           (analysis.analysis_id, principal.user_id, analysis.created_at, analysis.model_dump_json()))
        if features:
            connection.executemany("INSERT INTO analysis_flows(analysis_id, row_id, features) VALUES (?, ?, ?)",
                                   [(analysis.analysis_id, index + 1, json.dumps(row, allow_nan=False))
                                    for index, row in enumerate(features)])
    return analysis


def get(analysis_id: str, principal: Principal) -> AnalysisResponse:
    if _supabase():
        rows = _rest(principal, "GET", "analyses", params={
            "select": "payload", "analysis_id": f"eq.{analysis_id}", "user_id": f"eq.{principal.user_id}", "limit": "1",
        }).json()
        if not rows:
            raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
        return AnalysisResponse.model_validate(rows[0]["payload"])
    with connect() as connection:
        row = connection.execute("SELECT payload FROM analyses WHERE id = ? AND user_id = ?",
                                 (analysis_id, principal.user_id)).fetchone()
    if row is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
    return AnalysisResponse.model_validate_json(row[0])


def list_analyses(limit: int, offset: int, principal: Principal) -> dict:
    if _supabase():
        response = _rest(principal, "GET", "analyses", params={
            "select": "analysis_id,filename,created_at,source_type,model_version,total_flows,counts",
            "user_id": f"eq.{principal.user_id}", "order": "created_at.desc,analysis_id.desc",
            "limit": str(limit), "offset": str(offset),
        }, headers={"Prefer": "count=exact"})
        content_range = response.headers.get("content-range", "*/0").rsplit("/", 1)[-1]
        total = int(content_range) if content_range.isdigit() else 0
        return {"items": response.json(), "total": total, "limit": limit, "offset": offset}
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM analyses WHERE user_id = ?", (principal.user_id,)).fetchone()[0]
        rows = connection.execute(
            """SELECT json_remove(payload, '$.predictions', '$.preview') FROM analyses
               WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?""",
            (principal.user_id, limit, offset),
        ).fetchall()
    summaries = []
    for row in rows:
        item = json.loads(row[0])
        summaries.append({key: item[key] for key in
                          ("analysis_id", "filename", "created_at", "source_type", "model_version", "total_flows", "counts")})
    return {"items": summaries, "total": total, "limit": limit, "offset": offset}


def delete(analysis_id: str, principal: Principal) -> None:
    if _supabase():
        rows = _rest(principal, "DELETE", "analyses", params={
            "analysis_id": f"eq.{analysis_id}", "user_id": f"eq.{principal.user_id}", "select": "analysis_id",
        }, headers={"Prefer": "return=representation"}).json()
        if not rows:
            raise HTTPException(404, detail="Analysis not found.")
        return
    with connect() as connection:
        cursor = connection.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?",
                                    (analysis_id, principal.user_id))
        if cursor.rowcount == 0:
            raise HTTPException(404, detail="Analysis not found.")


def _require_analysis(analysis_id: str, principal: Principal) -> None:
    if _supabase():
        rows = _rest(principal, "GET", "analyses", params={
            "select": "analysis_id", "analysis_id": f"eq.{analysis_id}", "user_id": f"eq.{principal.user_id}", "limit": "1",
        }).json()
        if not rows:
            raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
        return
    with connect() as connection:
        exists = connection.execute("SELECT 1 FROM analyses WHERE id = ? AND user_id = ?",
                                    (analysis_id, principal.user_id)).fetchone()
    if exists is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")


def _flow_prediction(analysis_id: str, row_id: int, principal: Principal) -> tuple[Prediction, str | None]:
    if _supabase():
        value = _rest(principal, "POST", "rpc/get_flow_prediction", body={
            "p_analysis_id": analysis_id, "p_row_id": row_id,
        }).json()
        if not value or not value.get("prediction"):
            _require_analysis(analysis_id, principal)
            raise HTTPException(404, detail="Flow record not found.")
        features = value.get("features")
        return Prediction.model_validate(value["prediction"]), json.dumps(features) if features is not None else None
    if row_id < 1:
        _require_analysis(analysis_id, principal)
        raise HTTPException(404, detail="Flow record not found.")
    with connect() as connection:
        row = connection.execute(
            """SELECT json_extract(a.payload, '$.total_flows'), json_extract(a.payload, ?), f.features
               FROM analyses AS a LEFT JOIN analysis_flows AS f ON f.analysis_id = a.id AND f.row_id = ?
               WHERE a.id = ? AND a.user_id = ?""",
            (f"$.predictions[{row_id - 1}]", row_id, analysis_id, principal.user_id),
        ).fetchone()
    if row is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
    if row_id > row[0] or row[1] is None:
        raise HTTPException(404, detail="Flow record not found.")
    return Prediction.model_validate_json(row[1]), row[2]


def flow_detail(analysis_id: str, row_id: int, principal: Principal) -> dict:
    prediction, features = _flow_prediction(analysis_id, row_id, principal)
    return {**prediction.model_dump(), "features": json.loads(features) if features else {}}


def response_decisions(analysis_id: str, principal: Principal) -> list[ResponseDecision]:
    _require_analysis(analysis_id, principal)
    if _supabase():
        rows = _rest(principal, "GET", "response_decisions", params={
            "select": "analysis_id,row_id,decision,decided_at", "analysis_id": f"eq.{analysis_id}",
            "user_id": f"eq.{principal.user_id}", "order": "row_id.asc",
        }).json()
        return [ResponseDecision.model_validate(row) for row in rows]
    with connect() as connection:
        rows = connection.execute(
            """SELECT d.row_id, d.decision, d.decided_at FROM response_decisions AS d
               JOIN analyses AS a ON a.id = d.analysis_id
               WHERE d.analysis_id = ? AND a.user_id = ? ORDER BY d.row_id""",
            (analysis_id, principal.user_id),
        ).fetchall()
    return [ResponseDecision(analysis_id=analysis_id, row_id=row[0], decision=row[1], decided_at=row[2]) for row in rows]


def set_response_decision(analysis_id: str, row_id: int, decision: str, principal: Principal) -> ResponseDecision:
    prediction, _ = _flow_prediction(analysis_id, row_id, principal)
    if prediction.label != "malicious":
        raise HTTPException(409, detail="Simulated IPS decisions are only available for malicious model classifications.")
    decided_at = datetime.now(timezone.utc).isoformat()
    if _supabase():
        rows = _rest(principal, "POST", "response_decisions", params={
            "on_conflict": "analysis_id,user_id,row_id", "select": "analysis_id,row_id,decision,decided_at",
        }, body={"analysis_id": analysis_id, "user_id": principal.user_id, "row_id": row_id, "decision": decision, "decided_at": decided_at},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"}, server_write=True).json()
        if not rows:
            raise HTTPException(503, detail="Supabase could not save the analyst decision.")
        return ResponseDecision.model_validate(rows[0])
    with connect() as connection:
        connection.execute(
            """INSERT INTO response_decisions(analysis_id, row_id, decision, decided_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(analysis_id, row_id) DO UPDATE SET decision = excluded.decision, decided_at = excluded.decided_at""",
            (analysis_id, row_id, decision, decided_at),
        )
    return ResponseDecision(analysis_id=analysis_id, row_id=row_id, decision=decision, decided_at=decided_at)


def clear_response_decision(analysis_id: str, row_id: int, principal: Principal) -> None:
    _flow_prediction(analysis_id, row_id, principal)
    if _supabase():
        _rest(principal, "DELETE", "response_decisions", params={
            "analysis_id": f"eq.{analysis_id}", "user_id": f"eq.{principal.user_id}", "row_id": f"eq.{row_id}",
        })
        return
    with connect() as connection:
        connection.execute("DELETE FROM response_decisions WHERE analysis_id = ? AND row_id = ?",
                           (analysis_id, row_id))

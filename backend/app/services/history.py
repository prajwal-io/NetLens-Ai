"""SQLite is the authoritative store; browser state only selects an analysis."""
import json
from datetime import datetime, timezone
from fastapi import HTTPException
from app.db.database import connect
from app.schemas.traffic import AnalysisResponse, Prediction, ResponseDecision


def save(analysis: AnalysisResponse, features: list[dict] | None = None) -> AnalysisResponse:
    payload = analysis.model_dump_json()
    with connect() as connection:
        connection.execute("INSERT INTO analyses(id, created_at, payload) VALUES (?, ?, ?)",
                           (analysis.analysis_id, analysis.created_at, payload))
        if features:
            connection.executemany("INSERT INTO analysis_flows(analysis_id, row_id, features) VALUES (?, ?, ?)",
                                   [(analysis.analysis_id, index + 1, json.dumps(row, allow_nan=False))
                                    for index, row in enumerate(features)])
    return analysis


def get(analysis_id: str) -> AnalysisResponse:
    with connect() as connection:
        row = connection.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if row is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
    return AnalysisResponse.model_validate_json(row[0])


def list_analyses(limit: int, offset: int) -> dict:
    with connect() as connection:
        total = connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        rows = connection.execute("SELECT json_remove(payload, '$.predictions', '$.preview') FROM analyses ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                                  (limit, offset)).fetchall()
    summaries = []
    for row in rows:
        item = json.loads(row[0])
        summaries.append({key: item[key] for key in
                          ("analysis_id", "filename", "created_at", "source_type", "model_version", "total_flows", "counts")})
    return {"items": summaries, "total": total, "limit": limit, "offset": offset}


def delete(analysis_id: str) -> None:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        if cursor.rowcount == 0:
            raise HTTPException(404, detail="Analysis not found.")


def _require_analysis(analysis_id: str) -> None:
    with connect() as connection:
        exists = connection.execute("SELECT 1 FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if exists is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")


def _flow_prediction(analysis_id: str, row_id: int) -> tuple[Prediction, str | None]:
    if row_id < 1:
        _require_analysis(analysis_id)
        raise HTTPException(404, detail="Flow record not found.")
    with connect() as connection:
        row = connection.execute(
            """SELECT json_extract(a.payload, '$.total_flows'), json_extract(a.payload, ?), f.features
               FROM analyses AS a
               LEFT JOIN analysis_flows AS f ON f.analysis_id = a.id AND f.row_id = ?
               WHERE a.id = ?""",
            (f"$.predictions[{row_id - 1}]", row_id, analysis_id),
        ).fetchone()
    if row is None:
        raise HTTPException(404, detail="Analysis not found. It may have been deleted.")
    if row_id > row[0] or row[1] is None:
        raise HTTPException(404, detail="Flow record not found.")
    return Prediction.model_validate_json(row[1]), row[2]


def flow_detail(analysis_id: str, row_id: int) -> dict:
    prediction, features = _flow_prediction(analysis_id, row_id)
    return {**prediction.model_dump(), "features": json.loads(features) if features else {}}


def response_decisions(analysis_id: str) -> list[ResponseDecision]:
    _require_analysis(analysis_id)
    with connect() as connection:
        rows = connection.execute(
            "SELECT row_id, decision, decided_at FROM response_decisions WHERE analysis_id = ? ORDER BY row_id",
            (analysis_id,),
        ).fetchall()
    return [ResponseDecision(analysis_id=analysis_id, row_id=row[0], decision=row[1], decided_at=row[2]) for row in rows]


def set_response_decision(analysis_id: str, row_id: int, decision: str) -> ResponseDecision:
    prediction, _ = _flow_prediction(analysis_id, row_id)
    if prediction.label != "malicious":
        raise HTTPException(409, detail="Simulated IPS decisions are only available for malicious model classifications.")
    decided_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            """INSERT INTO response_decisions(analysis_id, row_id, decision, decided_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(analysis_id, row_id) DO UPDATE SET decision = excluded.decision, decided_at = excluded.decided_at""",
            (analysis_id, row_id, decision, decided_at),
        )
    return ResponseDecision(analysis_id=analysis_id, row_id=row_id, decision=decision, decided_at=decided_at)


def clear_response_decision(analysis_id: str, row_id: int) -> None:
    _flow_prediction(analysis_id, row_id)
    with connect() as connection:
        connection.execute("DELETE FROM response_decisions WHERE analysis_id = ? AND row_id = ?", (analysis_id, row_id))

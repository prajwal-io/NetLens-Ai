"""SQLite is the authoritative store; browser state only selects an analysis."""
import json
from fastapi import HTTPException
from app.db.database import connect
from app.schemas.traffic import AnalysisResponse


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


def flow_detail(analysis_id: str, row_id: int) -> dict:
    analysis = get(analysis_id)
    if row_id < 1 or row_id > analysis.total_flows:
        raise HTTPException(404, detail="Flow record not found.")
    with connect() as connection:
        row = connection.execute("SELECT features FROM analysis_flows WHERE analysis_id = ? AND row_id = ?",
                                 (analysis_id, row_id)).fetchone()
    return {**analysis.predictions[row_id - 1].model_dump(), "features": json.loads(row[0]) if row else {}}

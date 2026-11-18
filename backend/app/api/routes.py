from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.schemas.traffic import AnalysisResponse, AnalysisHistory, PredictionPreview, FeatureSchemaResponse, HealthResponse, ValidationResponse, ResponseDecisionList, ResponseDecisionRequest, ResponseDecision
from app.services.model_service import model_service
from app.services.validation import validate_csv
from app.services import history
from app.services.inference import analyze_csv
from app.services.reports import csv_report, pdf_report

router = APIRouter(prefix="/api/v1")

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(model_loaded=model_service.loaded, model_version=model_service.model_version)

@router.get("/model/info")
def model_info():
    return model_service.info()

@router.get("/model/schema", response_model=FeatureSchemaResponse)
def model_schema():
    return model_service.schema()

async def read_csv_upload(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(415, detail="Upload a .csv file.")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, detail="CSV exceeds the 5 MiB upload limit.")
    return content

@router.post("/traffic/validate", response_model=ValidationResponse)
async def validate(file: UploadFile = File(...)):
    try:
        content = await read_csv_upload(file)
        return await run_in_threadpool(validate_csv, content, file.filename or "traffic.csv")
    finally:
        await file.close()



@router.post("/traffic/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    try:
        content = await read_csv_upload(file)
        return await run_in_threadpool(analyze_csv, content, file.filename or "traffic.csv")
    finally:
        await file.close()


@router.get("/analyses", response_model=AnalysisHistory)
def analyses(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    return history.list_analyses(limit, offset)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def analysis_detail(analysis_id: str):
    return history.get(analysis_id)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str):
    history.delete(analysis_id)
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}/export.csv")
def export_csv(analysis_id: str):
    analysis = history.get(analysis_id)
    decisions = history.response_decisions(analysis_id)
    return Response(csv_report(analysis, decisions), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="netsight-{analysis.analysis_id}.csv"'})


@router.get("/analyses/{analysis_id}/report.pdf")
def export_pdf(analysis_id: str):
    analysis = history.get(analysis_id)
    decisions = history.response_decisions(analysis_id)
    return Response(pdf_report(analysis, decisions), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="netsight-{analysis.analysis_id}.pdf"'})


@router.get("/replays")
def replays():
    from app.services.replay import list_scenarios
    return {"items": list_scenarios()}


@router.post("/replays/{replay_id}/analyze", response_model=AnalysisResponse)
def analyze_replay(replay_id: str):
    from app.services.replay import load_scenario
    content, scenario = load_scenario(replay_id)
    return analyze_csv(content, scenario["filename"], "historical_replay", replay_id)


@router.get("/analyses/{analysis_id}/flows/{row_id}", response_model=PredictionPreview)
def flow_detail(analysis_id: str, row_id: int):
    return history.flow_detail(analysis_id, row_id)


@router.get("/analyses/{analysis_id}/response-decisions", response_model=ResponseDecisionList)
def response_decisions(analysis_id: str):
    return {"analysis_id": analysis_id, "items": history.response_decisions(analysis_id)}


@router.put("/analyses/{analysis_id}/flows/{row_id}/response", response_model=ResponseDecision)
def set_response_decision(analysis_id: str, row_id: int, request: ResponseDecisionRequest):
    return history.set_response_decision(analysis_id, row_id, request.decision)


@router.delete("/analyses/{analysis_id}/flows/{row_id}/response", status_code=204)
def clear_response_decision(analysis_id: str, row_id: int):
    history.clear_response_decision(analysis_id, row_id)
    return Response(status_code=204)

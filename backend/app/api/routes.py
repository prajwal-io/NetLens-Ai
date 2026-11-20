import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response, Depends, Request
from starlette.concurrency import run_in_threadpool

from app.core.auth import Principal, require_user
from app.core.config import settings
from app.schemas.traffic import AnalysisResponse, AnalysisHistory, PredictionPreview, FeatureSchemaResponse, HealthResponse, ValidationResponse, ResponseDecisionList, ResponseDecisionRequest, ResponseDecision, CaptureAnalysisResponse, URLReputationRequest, URLReputationResponse
from app.services.model_service import model_service
from app.services.validation import validate_csv
from app.services import history
from app.services.inference import analyze_csv
from app.services.reports import csv_report, pdf_report

router = APIRouter(prefix="/api/v1")

@router.get("/health", response_model=HealthResponse)
def health():
    if not model_service.loaded:
        raise HTTPException(503, detail="The evaluated model is not available.")
    return HealthResponse(model_loaded=model_service.loaded, model_version=model_service.model_version)


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request):
    if not model_service.loaded:
        raise HTTPException(503, detail="The evaluated model is not available.")
    if settings.storage_backend == "supabase":
        client: httpx.AsyncClient | None = getattr(request.app.state, "supabase_auth_client", None)
        key = settings.supabase_secret_key
        if client is None or not key:
            raise HTTPException(503, detail="Supabase data storage is not configured.")
        headers = {"apikey": key}
        if not key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {key}"
        try:
            response = await client.get(
                "/rest/v1/analyses", params={"select": "analysis_id", "limit": "0"}, headers=headers,
                timeout=httpx.Timeout(3.0, connect=2.0),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(503, detail="Supabase data storage is unavailable.") from exc
        if response.status_code != 200:
            raise HTTPException(503, detail="Supabase analyses table is unavailable; apply the database migrations.")
    return HealthResponse(model_loaded=True, model_version=model_service.model_version)

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


async def read_capture_upload(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith((".pcap", ".pcapng")):
        raise HTTPException(415, detail="Upload a .pcap or .pcapng capture file.")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, detail="Capture exceeds the 5 MiB upload limit.")
    return content

@router.post("/traffic/validate", response_model=ValidationResponse)
async def validate(file: UploadFile = File(...), principal: Principal = Depends(require_user)):
    try:
        content = await read_csv_upload(file)
        return await run_in_threadpool(validate_csv, content, file.filename or "traffic.csv")
    finally:
        await file.close()



@router.post("/traffic/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...), principal: Principal = Depends(require_user)):
    try:
        content = await read_csv_upload(file)
        return await run_in_threadpool(analyze_csv, content, file.filename or "traffic.csv", principal)
    finally:
        await file.close()


@router.post("/traffic/pcap/analyze", response_model=CaptureAnalysisResponse)
async def analyze_capture_upload(file: UploadFile = File(...), principal: Principal = Depends(require_user)):
    from app.services.capture import CaptureLimitExceeded, InvalidCapture, analyze_capture
    try:
        content = await read_capture_upload(file)
        try:
            return await run_in_threadpool(analyze_capture, content, file.filename or "capture.pcap", settings.max_capture_packets)
        except CaptureLimitExceeded as exc:
            raise HTTPException(413, detail=str(exc))
        except InvalidCapture as exc:
            raise HTTPException(422, detail=str(exc))
    finally:
        await file.close()


@router.post("/url/reputation", response_model=URLReputationResponse)
async def url_reputation(request: URLReputationRequest, principal: Principal = Depends(require_user)):
    from app.services.reputation import lookup_url
    return await lookup_url(request.url)


@router.get("/analyses", response_model=AnalysisHistory)
def analyses(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), principal: Principal = Depends(require_user)):
    return history.list_analyses(limit, offset, principal)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def analysis_detail(analysis_id: str, principal: Principal = Depends(require_user)):
    return history.get(analysis_id, principal)


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, principal: Principal = Depends(require_user)):
    history.delete(analysis_id, principal)
    return Response(status_code=204)


@router.get("/analyses/{analysis_id}/export.csv")
def export_csv(analysis_id: str, principal: Principal = Depends(require_user)):
    analysis = history.get(analysis_id, principal)
    decisions = history.response_decisions(analysis_id, principal)
    return Response(csv_report(analysis, decisions), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="netsight-{analysis.analysis_id}.csv"'})


@router.get("/analyses/{analysis_id}/report.pdf")
def export_pdf(analysis_id: str, principal: Principal = Depends(require_user)):
    analysis = history.get(analysis_id, principal)
    decisions = history.response_decisions(analysis_id, principal)
    return Response(pdf_report(analysis, decisions), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="netsight-{analysis.analysis_id}.pdf"'})


@router.get("/replays")
def replays(principal: Principal = Depends(require_user)):
    from app.services.replay import list_scenarios
    return {"items": list_scenarios()}


@router.get("/replays/{replay_id}/download")
def download_replay(replay_id: str, principal: Principal = Depends(require_user)):
    from app.services.replay import load_scenario
    content, _ = load_scenario(replay_id)
    return Response(content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="netsight-{replay_id}.csv"'})


@router.post("/replays/{replay_id}/analyze", response_model=AnalysisResponse)
def analyze_replay(replay_id: str, principal: Principal = Depends(require_user)):
    from app.services.replay import load_scenario
    content, scenario = load_scenario(replay_id)
    return analyze_csv(content, scenario["filename"], principal, "historical_replay", replay_id)


@router.get("/analyses/{analysis_id}/flows/{row_id}", response_model=PredictionPreview)
def flow_detail(analysis_id: str, row_id: int, principal: Principal = Depends(require_user)):
    return history.flow_detail(analysis_id, row_id, principal)


@router.get("/analyses/{analysis_id}/response-decisions", response_model=ResponseDecisionList)
def response_decisions(analysis_id: str, principal: Principal = Depends(require_user)):
    return {"analysis_id": analysis_id, "items": history.response_decisions(analysis_id, principal)}


@router.put("/analyses/{analysis_id}/flows/{row_id}/response", response_model=ResponseDecision)
def set_response_decision(analysis_id: str, row_id: int, request: ResponseDecisionRequest, principal: Principal = Depends(require_user)):
    return history.set_response_decision(analysis_id, row_id, request.decision, principal)


@router.delete("/analyses/{analysis_id}/flows/{row_id}/response", status_code=204)
def clear_response_decision(analysis_id: str, row_id: int, principal: Principal = Depends(require_user)):
    history.clear_response_decision(analysis_id, row_id, principal)
    return Response(status_code=204)

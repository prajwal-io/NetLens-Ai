from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
from uuid import uuid4

from app.core.config import settings
from app.schemas.traffic import AnalysisResponse, FeatureSchemaResponse, HealthResponse, ValidationResponse
from app.services.model_service import model_service
from app.services.validation import parse_traffic_csv, validate_csv
from ml.schema import FEATURE_COLUMNS

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
        return validate_csv(content, file.filename or "traffic.csv")
    finally:
        await file.close()

@router.post("/traffic/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    try:
        content = await read_csv_upload(file)
        validation, rows = parse_traffic_csv(content, file.filename or "traffic.csv")
        features = pd.DataFrame.from_records(rows, columns=FEATURE_COLUMNS)
        labels, scores, metadata, threshold = model_service.predict(features)
        normal = int((labels == 0).sum())
        malicious = int((labels == 1).sum())
        predictions = [
            {
                "row_id": index + 1,
                "label": "malicious" if int(label) == 1 else "normal",
                "malicious_score": float(score),
            }
            for index, (label, score) in enumerate(zip(labels, scores))
        ]
        preview = [
            {
                **predictions[index],
                "features": rows[index],
            }
            for index in range(min(5, len(rows)))
        ]
        return AnalysisResponse(
            analysis_id=uuid4().hex,
            filename=validation.filename,
            model_version=str(metadata["model_version"]),
            threshold=threshold,
            total_flows=validation.row_count,
            counts={"normal": normal, "malicious": malicious},
            predictions=predictions,
            preview=preview,
            score_definition=str(metadata["score_definition"]),
            message="The model classifies compatible flow features against the UNSW-NB15 benchmark label. A malicious label is a review signal, not proof of an incident.",
        )
    finally:
        await file.close()

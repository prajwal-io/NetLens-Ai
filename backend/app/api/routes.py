from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.schemas.traffic import HealthResponse, ValidationResponse
from app.services.validation import validate_csv

router = APIRouter(prefix="/api/v1")

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()

@router.post("/traffic/validate", response_model=ValidationResponse)
async def validate(file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(415, detail="Upload a .csv file.")
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(413, detail="CSV exceeds the 5 MiB upload limit.")
        return validate_csv(content, file.filename)
    finally:
        await file.close()

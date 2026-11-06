from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "netsight-api"
    model_loaded: bool = False
    model_version: str | None = None

class ValidationResponse(BaseModel):
    valid: bool = True
    filename: str
    row_count: int
    columns: list[str]
    preview: list[dict[str, str]]
    schema_name: str = "foundation-flow-v1"
    message: str = "CSV validated. No ML predictions were generated."

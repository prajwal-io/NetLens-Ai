from typing import Literal

from pydantic import BaseModel

from ml.schema import SCHEMA_NAME


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "netsight-api"
    model_loaded: bool = False
    model_version: str | None = None


class FeatureSchemaResponse(BaseModel):
    schema_name: str = SCHEMA_NAME
    feature_count: int
    features: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    excluded_columns: list[str]


class ValidationResponse(BaseModel):
    valid: bool = True
    filename: str
    row_count: int
    columns: list[str]
    preview: list[dict[str, str]]
    schema_name: str = SCHEMA_NAME
    message: str


class Prediction(BaseModel):
    row_id: int
    label: Literal["normal", "malicious"]
    malicious_score: float


class PredictionPreview(Prediction):
    features: dict[str, float | str | None]


class AnalysisCounts(BaseModel):
    normal: int
    malicious: int


class AnalysisResponse(BaseModel):
    analysis_id: str
    source_type: Literal["uploaded_csv"] = "uploaded_csv"
    filename: str
    model_version: str
    threshold: float
    total_flows: int
    counts: AnalysisCounts
    predictions: list[Prediction]
    preview: list[PredictionPreview]
    score_definition: str
    message: str

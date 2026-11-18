from typing import Literal

from pydantic import BaseModel, Field
from datetime import datetime, timezone

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
    source: str | None = None
    destination: str | None = None
    timestamp: str | None = None


class PredictionPreview(Prediction):
    features: dict[str, float | str | None]


class AnalysisCounts(BaseModel):
    normal: int
    malicious: int


class AnalysisResponse(BaseModel):
    analysis_id: str
    source_type: Literal["uploaded_csv", "historical_replay"] = "uploaded_csv"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    replay_id: str | None = None
    model_context: dict = Field(default_factory=dict)
    filename: str
    model_version: str
    threshold: float
    total_flows: int
    counts: AnalysisCounts
    predictions: list[Prediction]
    preview: list[PredictionPreview]
    score_definition: str
    message: str


class AnalysisSummary(BaseModel):
    analysis_id: str
    filename: str
    created_at: str
    source_type: Literal["uploaded_csv", "historical_replay"]
    model_version: str
    total_flows: int
    counts: AnalysisCounts


class AnalysisHistory(BaseModel):
    items: list[AnalysisSummary]
    total: int
    limit: int
    offset: int


class ResponseDecisionRequest(BaseModel):
    decision: Literal["simulated_block", "dismissed"]


class ResponseDecision(BaseModel):
    analysis_id: str
    row_id: int
    decision: Literal["simulated_block", "dismissed"]
    decided_at: str


class ResponseDecisionList(BaseModel):
    analysis_id: str
    items: list[ResponseDecision]

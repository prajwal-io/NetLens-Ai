"""One inference path for uploads and historical replay; training stays separate."""
from uuid import uuid4
import pandas as pd
from app.core.auth import Principal
from app.schemas.traffic import AnalysisResponse
from app.services.model_service import model_service
from app.services.validation import parse_traffic_csv
from app.services.flow_metadata import read_metadata
from app.services import history
from ml.schema import FEATURE_COLUMNS


def analyze_csv(content: bytes, filename: str, principal: Principal, source_type: str = "uploaded_csv", replay_id: str | None = None) -> AnalysisResponse:
    """Parse, predict, and build the bounded response away from the event loop."""
    validation, rows = parse_traffic_csv(content, filename)
    context = read_metadata(content)
    features = pd.DataFrame.from_records(rows, columns=FEATURE_COLUMNS)
    labels, scores, metadata, threshold = model_service.predict(features)
    normal = int((labels == 0).sum())
    malicious = int((labels == 1).sum())
    predictions = [
        {
            "row_id": index + 1,
            "label": "malicious" if int(label) == 1 else "normal",
            "malicious_score": float(score),
            **context[index],
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
    analysis = AnalysisResponse(
        source_type=source_type,
        replay_id=replay_id,
        analysis_id=uuid4().hex,
        filename=validation.filename,
        model_version=str(metadata["model_version"]),
        threshold=threshold,
        total_flows=validation.row_count,
        counts={"normal": normal, "malicious": malicious},
        predictions=predictions,
        preview=preview,
        score_definition=str(metadata["score_definition"]),
        model_context={"dataset": metadata.get("dataset", {}).get("name"),
                       "threshold_policy": metadata.get("threshold_policy"),
                       "evaluation": metadata.get("evaluation", {}).get("metrics"),
                       "limitations": metadata.get("limitations", [])},
        message="The model classifies compatible flow features against the UNSW-NB15 benchmark label. A malicious label is a review signal, not proof of an incident.",
    )

    return history.save(analysis, principal, rows)

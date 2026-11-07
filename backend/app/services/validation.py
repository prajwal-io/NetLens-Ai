"""Strict CSV validation for the mixed UNSW-NB15 inference schema."""

from __future__ import annotations

import csv
import io
import math

from fastapi import HTTPException

from app.core.config import settings
from app.schemas.traffic import ValidationResponse
from ml.schema import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, SCHEMA_NAME


REQUIRED_COLUMNS = FEATURE_COLUMNS


def parse_traffic_csv(content: bytes, filename: str) -> tuple[ValidationResponse, list[dict[str, float | str | None]]]:
    """Validate required model columns; ignore labels and other source columns."""
    def reject(message: str) -> None:
        raise HTTPException(422, detail=message)

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        reject("CSV must use UTF-8 encoding.")
    if "\x00" in text:
        reject("Binary content is not a CSV.")

    try:
        reader = csv.reader(io.StringIO(text), strict=True)
        headers = [header.strip() for header in next(reader, [])]
        if not headers or any(not header for header in headers):
            reject("CSV requires nonempty column headers.")
        if len(set(headers)) != len(headers):
            reject("Duplicate column names are not allowed.")
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        if missing:
            reject("Missing required model features: " + ", ".join(missing))

        preview: list[dict[str, str]] = []
        feature_rows: list[dict[str, float | str | None]] = []
        count = 0
        for line, values in enumerate(reader, start=2):
            if not values or (len(values) == 1 and not values[0].strip()):
                continue
            count += 1
            if count > settings.max_rows:
                reject(f"CSV exceeds {settings.max_rows} rows.")
            if len(values) != len(headers):
                reject(f"Row {line}: column count does not match header.")
            source_row = dict(zip(headers, (value.strip() for value in values)))
            feature_row: dict[str, float | str | None] = {}
            for feature in NUMERIC_FEATURES:
                raw = source_row[feature]
                if not raw:
                    feature_row[feature] = None
                    continue
                try:
                    number = float(raw)
                except ValueError:
                    reject(f"Row {line}: {feature} must be numeric or blank.")
                if not math.isfinite(number):
                    reject(f"Row {line}: {feature} must be finite.")
                feature_row[feature] = number
            for feature in CATEGORICAL_FEATURES:
                raw = source_row[feature]
                if len(raw) > 128:
                    reject(f"Row {line}: {feature} must not exceed 128 characters.")
                feature_row[feature] = raw or None
            feature_rows.append(feature_row)
            if len(preview) < 5:
                preview.append(source_row)

        if not count:
            reject("CSV contains no traffic rows.")
        result = ValidationResponse(
            filename=filename,
            row_count=count,
            columns=headers,
            preview=preview,
            schema_name=SCHEMA_NAME,
            message=(
                "CSV structure and 42 model features validated. Blank feature values are imputed by the fitted pipeline; "
                "this endpoint generated no predictions."
            ),
        )
        return result, feature_rows
    except csv.Error:
        reject("Malformed CSV: check quotes and delimiters.")


def validate_csv(content: bytes, filename: str) -> ValidationResponse:
    result, _ = parse_traffic_csv(content, filename)
    return result

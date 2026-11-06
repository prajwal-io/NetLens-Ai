import csv
import io
import math

from fastapi import HTTPException

from app.core.config import settings
from app.schemas.traffic import ValidationResponse
from ml.schema import FEATURE_COLUMNS


REQUIRED_COLUMNS = FEATURE_COLUMNS


def parse_traffic_csv(content: bytes, filename: str) -> tuple[ValidationResponse, list[dict[str, float]]]:
    """Validate the model input contract and return numeric feature rows.

    Extra source columns (including labels) are accepted for display but are
    never passed to the classifier.
    """
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
        feature_rows: list[dict[str, float]] = []
        count = 0
        for line, values in enumerate(reader, start=2):
            if not values:
                continue
            count += 1
            if count > settings.max_rows:
                reject(f"CSV exceeds {settings.max_rows} rows.")
            if len(values) != len(headers):
                reject(f"Row {line}: column count does not match header.")
            string_row = dict(zip(headers, (value.strip() for value in values)))
            numeric_row: dict[str, float] = {}
            for feature in REQUIRED_COLUMNS:
                try:
                    number = float(string_row[feature])
                except ValueError:
                    reject(f"Row {line}: {feature} must be numeric.")
                if not math.isfinite(number) or number < 0:
                    reject(f"Row {line}: {feature} must be finite and nonnegative.")
                numeric_row[feature] = number
            feature_rows.append(numeric_row)
            if len(preview) < 5:
                preview.append(string_row)

        if not count:
            reject("CSV contains no traffic rows.")
        result = ValidationResponse(
            filename=filename,
            row_count=count,
            columns=headers,
            preview=preview,
        )
        return result, feature_rows
    except csv.Error:
        reject("Malformed CSV: check quotes and delimiters.")


def validate_csv(content: bytes, filename: str) -> ValidationResponse:
    result, _ = parse_traffic_csv(content, filename)
    return result

import csv
import io
import math
from fastapi import HTTPException
from app.core.config import settings
from app.schemas.traffic import ValidationResponse

# Explicit Phase 1 subset, not a claim of compatibility with a future training pipeline.
REQUIRED_COLUMNS = ("Destination Port", "Flow Duration", "Total Fwd Packets", "Total Backward Packets")

def validate_csv(content: bytes, filename: str) -> ValidationResponse:
    def reject(message: str):
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
        if not headers or any(not h for h in headers):
            reject("CSV requires nonempty column headers.")
        if len(set(headers)) != len(headers):
            reject("Duplicate column names are not allowed.")
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        if missing:
            reject("Missing required columns: " + ", ".join(missing))
        preview = []
        count = 0
        for line, values in enumerate(reader, start=2):
            if not values:
                continue
            count += 1
            if count > settings.max_rows:
                reject(f"CSV exceeds {settings.max_rows} rows.")
            if len(values) != len(headers):
                reject(f"Row {line}: column count does not match header.")
            row = dict(zip(headers, (v.strip() for v in values)))
            for field in REQUIRED_COLUMNS:
                try:
                    value = float(row[field])
                except ValueError:
                    reject(f"Row {line}: {field} must be numeric.")
                if not math.isfinite(value) or value < 0:
                    reject(f"Row {line}: {field} must be finite and nonnegative.")
                if field != "Flow Duration" and not value.is_integer():
                    reject(f"Row {line}: {field} must be an integer.")
                if field == "Destination Port" and value > 65535:
                    reject(f"Row {line}: Destination Port must be at most 65535.")
            if len(preview) < 5:
                preview.append(row)
        if not count:
            reject("CSV contains no traffic rows.")
        return ValidationResponse(filename=filename, row_count=count, columns=headers, preview=preview)
    except csv.Error:
        reject("Malformed CSV: check quotes and delimiters.")

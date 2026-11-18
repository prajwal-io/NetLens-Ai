"""Read optional, explicitly named context columns after model schema validation."""
import csv
import io
from datetime import datetime
from ipaddress import ip_address
from fastapi import HTTPException
from ml.schema import FEATURE_COLUMNS

ALIASES = {"source": ("source_ip", "src_ip", "srcip"),
           "destination": ("destination_ip", "dst_ip", "dstip"),
           "timestamp": ("timestamp", "start_time")}


def read_metadata(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    header_line = text.splitlines()[0]
    delimiter = next(delimiter for delimiter in (",", ";", "\t", "|")
                     if set(FEATURE_COLUMNS).issubset({h.strip() for h in next(csv.reader([header_line], delimiter=delimiter))}))
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    headers = [header.strip() for header in next(reader)]
    selected = {key: next((headers.index(alias) for alias in aliases if alias in headers), None)
                for key, aliases in ALIASES.items()}
    result = []
    for values in reader:
        line = reader.line_num
        if not values or (len(values) == 1 and not values[0].strip()):
            continue
        item = {}
        for key, index in selected.items():
            if index is None or not values[index].strip():
                continue
            value = values[index].strip()
            try:
                if key == "timestamp":
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("timezone required")
                    item[key] = parsed.isoformat()
                else:
                    item[key] = str(ip_address(value))
            except ValueError:
                raise HTTPException(422, detail=f"Row {line}: invalid {key}; use an IP address or timezone-aware ISO 8601 timestamp.")
        result.append(item)
    return result

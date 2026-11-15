"""Small, hash-verified benchmark excerpts; never generated predictions or live capture."""
import hashlib
import csv
import io
import re
import json
from pathlib import Path
from fastapi import HTTPException

REPLAY_ROOT = Path(__file__).resolve().parents[2] / "data" / "replays"


def list_scenarios() -> list[dict]:
    try:
        scenarios = json.loads((REPLAY_ROOT / "manifest.json").read_text(encoding="utf-8"))["scenarios"]
        if not isinstance(scenarios, list) or not scenarios:
            raise ValueError("Empty replay manifest")
        for item in scenarios:
            if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key] for key in
                    ("id", "filename", "title", "description", "dataset", "timing", "sha256")):
                raise ValueError("Incomplete scenario metadata")
            if not re.fullmatch(r"[a-z0-9-]+", item["id"]) or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
                raise ValueError("Invalid scenario identity")
            if type(item.get("rows")) is not int or not 0 < item["rows"] <= 10000:
                raise ValueError("Invalid scenario size")
        if len({item["id"] for item in scenarios}) != len(scenarios):
            raise ValueError("Duplicate scenario identity")
        return scenarios
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, detail="Historical replay files are unavailable.")


def load_scenario(replay_id: str) -> tuple[bytes, dict]:
    scenario = next((item for item in list_scenarios() if item["id"] == replay_id), None)
    if scenario is None:
        raise HTTPException(404, detail="Replay scenario not found.")
    try:
        path = (REPLAY_ROOT / scenario["filename"]).resolve()
        if path.parent != REPLAY_ROOT.resolve():
            raise ValueError("Invalid replay path")
        if path.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("Replay is too large")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != scenario["sha256"]:
            raise ValueError("Replay checksum mismatch")
        row_count = sum(1 for row in csv.reader(io.StringIO(content.decode("utf-8-sig"))) if row) - 1
        if row_count != scenario["rows"]:
            raise ValueError("Replay row count mismatch")
    except (OSError, ValueError, csv.Error):
        raise HTTPException(503, detail="Replay integrity check failed. Restore the bundled scenario files.")
    return content, scenario

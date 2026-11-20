from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NETSIGHT_")
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    database_path: Path = Path(__file__).resolve().parents[2] / "data" / "netsight.db"
    model_artifact_path: Path = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "netsight-model.joblib"
    model_artifact_url: str | None = None
    model_artifact_sha256: str | None = None
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None
    webrisk_api_key: str | None = None
    storage_backend: Literal["sqlite", "supabase"] = "sqlite"
    max_upload_bytes: int = 5 * 1024 * 1024
    # Bound prediction payloads as well as server work; callers can submit several files.
    max_rows: int = 10000
    max_capture_packets: int = 100000

settings = Settings()

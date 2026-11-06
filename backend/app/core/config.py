from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NETSIGHT_")
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    database_path: Path = Path(__file__).resolve().parents[2] / "data" / "netsight.db"
    max_upload_bytes: int = 5 * 1024 * 1024
    max_rows: int = 50000

settings = Settings()

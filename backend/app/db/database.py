import sqlite3
from app.core.config import settings

def connect():
    connection = sqlite3.connect(settings.database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def initialize():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS schema_version
                           (version INTEGER PRIMARY KEY, installed_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        connection.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (1)")

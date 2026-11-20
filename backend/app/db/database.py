import sqlite3
from contextlib import contextmanager
from app.core.config import settings

@contextmanager
def connect():
    connection = sqlite3.connect(settings.database_path, timeout=15)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def initialize():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS schema_version
                           (version INTEGER PRIMARY KEY, installed_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        connection.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (1)")

        connection.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)""")
        connection.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (2)")

        connection.execute("""CREATE TABLE IF NOT EXISTS analysis_flows (
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            row_id INTEGER NOT NULL, features TEXT NOT NULL,
            PRIMARY KEY(analysis_id, row_id))""")

        connection.execute("""CREATE TABLE IF NOT EXISTS response_decisions (
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            row_id INTEGER NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('simulated_block', 'dismissed')),
            decided_at TEXT NOT NULL, PRIMARY KEY(analysis_id, row_id))""")
        connection.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (3)")

        connection.execute("CREATE INDEX IF NOT EXISTS analyses_created ON analyses(created_at DESC, id DESC)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(analyses)")}
        if "user_id" not in columns:
            connection.execute("ALTER TABLE analyses ADD COLUMN user_id TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS analyses_owner_created ON analyses(user_id, created_at DESC, id DESC)")
        connection.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (4)")

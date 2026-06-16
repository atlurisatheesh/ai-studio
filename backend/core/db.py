"""SQLite storage — single local file, no external database server.

Chosen deliberately for privacy: every byte of user data lives in one
file on disk that the operator controls.
"""
import json
import aiosqlite

from core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    plan TEXT NOT NULL DEFAULT 'free',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS cloned_voices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    sample_path TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_session ON agent_messages(session_id, id);
CREATE TABLE IF NOT EXISTS avatar_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    script TEXT NOT NULL,
    voice TEXT NOT NULL,
    image_path TEXT NOT NULL,
    status TEXT NOT NULL,
    file TEXT,
    url TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_avatar_user ON avatar_jobs(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS dub_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_is_video INTEGER NOT NULL DEFAULT 0,
    target_language TEXT NOT NULL,
    target_language_code TEXT NOT NULL DEFAULT '',
    voice TEXT NOT NULL,
    status TEXT NOT NULL,
    source_language TEXT,
    transcript TEXT,
    translated_text TEXT,
    mode TEXT,
    file TEXT,
    url TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dub_user ON dub_jobs(user_id, created_at DESC);
"""

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.executescript(SCHEMA)
        await _db.commit()
    return _db


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    if "payload" in d and isinstance(d["payload"], str):
        try:
            d["payload"] = json.loads(d["payload"])
        except Exception:
            pass
    return d

"""SQLite persistence layer (standard library only).

Provides a durable, process-safe store for the task history and audit trail so
data survives restarts and deploys — a baseline requirement for production and
for the audit/compliance story.

A single shared connection (WAL mode) guarded by a lock is used. This is ample
for a single-instance deployment; for horizontal scale, point ``db_path`` at a
shared volume with a single writer, or swap this module for Postgres (the
``store``/``audit`` call sites would not change).
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.config import settings

_conn: sqlite3.Connection | None = None
_path: str | None = None
_lock = threading.RLock()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    message    TEXT NOT NULL,
    status     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);

CREATE TABLE IF NOT EXISTS audit (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id   TEXT NOT NULL,
    role      TEXT NOT NULL,
    tool      TEXT NOT NULL,
    status    TEXT NOT NULL,
    params    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_id ON audit(id DESC);
"""


def _resolve_path() -> str:
    return _path or settings.db_path


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def _get_conn_locked() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        target = _resolve_path()
        if target != ":memory:":
            Path(target).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(target, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        try:
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError:
            pass
        _ensure_schema(_conn)
    return _conn


def init_db(path: str | None = None) -> None:
    """(Re)initialize the database. Pass ``path`` to point at a specific file."""
    global _conn, _path
    with _lock:
        if path is not None:
            _path = path
        if _conn is not None:
            _conn.close()
            _conn = None
        _get_conn_locked()


def get_conn() -> sqlite3.Connection:
    with _lock:
        return _get_conn_locked()


def execute(sql: str, params: tuple = ()) -> None:
    with _lock:
        conn = _get_conn_locked()
        conn.execute(sql, params)
        conn.commit()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with _lock:
        conn = _get_conn_locked()
        return conn.execute(sql, params).fetchall()


def ping() -> bool:
    """Lightweight readiness check."""
    try:
        with _lock:
            _get_conn_locked().execute("SELECT 1")
        return True
    except sqlite3.DatabaseError:
        return False


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None

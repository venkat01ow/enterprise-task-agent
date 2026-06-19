"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app.auth import session_store
from app.config import settings
from app.core import audit, db, store
from app.tools import bootstrap_tools


@pytest.fixture(autouse=True, scope="session")
def _isolated_db(tmp_path_factory):
    """Point persistence at a throwaway SQLite file and disable rate limiting."""
    db_file = tmp_path_factory.mktemp("eta-data") / "test.db"
    settings.db_path = str(db_file)
    settings.rate_limit_enabled = False
    db.init_db(settings.db_path)
    yield
    db.close()


@pytest.fixture(autouse=True)
def _clean_state():
    """Ensure each test starts with tools registered and stores empty."""
    bootstrap_tools()
    store.clear()
    audit.clear()
    session_store.clear()
    yield
    store.clear()
    audit.clear()
    session_store.clear()

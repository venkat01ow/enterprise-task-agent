"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app.core import audit, store
from app.tools import bootstrap_tools


@pytest.fixture(autouse=True)
def _clean_state():
    """Ensure each test starts with tools registered and stores empty."""
    bootstrap_tools()
    store.clear()
    audit.clear()
    yield
    store.clear()
    audit.clear()

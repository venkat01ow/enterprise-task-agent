"""Role-based access control.

A simple hierarchical model is enough for the agent: a user may invoke a tool
when their role rank is at least the tool's required role rank.
"""
from __future__ import annotations

ROLE_RANK: dict[str, int] = {
    "viewer": 0,
    "employee": 1,
    "manager": 2,
    "admin": 3,
}


def can_use(user_role: str, required_role: str) -> bool:
    """Return True when ``user_role`` is permitted to use a ``required_role`` tool."""
    return ROLE_RANK.get(user_role, 0) >= ROLE_RANK.get(required_role, 0)

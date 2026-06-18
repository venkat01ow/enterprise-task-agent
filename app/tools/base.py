"""Tool plugin base classes and a lightweight registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Outcome of a tool invocation."""

    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for every agent tool.

    Subclasses declare a unique ``name``, a human ``description``, the
    ``required_role`` to invoke it, and a list of example phrases used both for
    documentation and to help the LLM planner.
    """

    name: str = "tool"
    description: str = ""
    required_role: str = "employee"
    examples: list[str] = []

    @abstractmethod
    def run(self, params: dict[str, Any], user: dict[str, Any]) -> ToolResult:
        """Execute the tool and return a :class:`ToolResult`."""
        raise NotImplementedError

    def manifest(self) -> dict[str, Any]:
        """Machine-readable description used by the planner and API."""
        return {
            "name": self.name,
            "description": self.description,
            "required_role": self.required_role,
            "examples": self.examples,
        }

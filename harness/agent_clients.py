from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class AgentResponse:
    observed: str
    reason: str | None = None
    raw: Dict[str, Any] | None = None


class AgentClient(Protocol):
    def evaluate_case(self, case: Dict[str, Any]) -> AgentResponse:
        """Evaluate a harness case and return the observed decision.

        `observed` should be one of: ALLOW, BLOCK, REFUSE, ERROR.
        """


class PlaceholderAgentClient:
    def evaluate_case(self, case: Dict[str, Any]) -> AgentResponse:
        return AgentResponse(observed="UNEXECUTED", reason="placeholder")

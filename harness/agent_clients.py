from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any, Dict, Protocol

import requests


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


_STATUS_MAP: Dict[str, str] = {
    "NEEDS_OWNER_SIGNATURE": "ALLOW",
    "BLOCKED_BY_POLICY": "BLOCK",
    "REJECTED": "REFUSE",
}


class FastAPIAgentClient:
    """Calls the Role-C FastAPI agent backend via HTTP."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 30.0) -> None:
        self.plan_url = f"{base_url}/v0/agent/plan"
        self.health_url = f"{base_url}/v0/health"
        self.timeout = timeout

    def health_check(self) -> bool:
        try:
            resp = requests.get(self.health_url, timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def evaluate_case(self, case: Dict[str, Any]) -> AgentResponse:
        payload = {
            "request_id": case.get("case_id", str(uuid.uuid4())),
            "user_message": case["input"],
            "session_id": f"harness-{case.get('case_id', 'unknown')}",
        }

        try:
            resp = requests.post(self.plan_url, json=payload, timeout=self.timeout)
        except requests.ConnectionError:
            return AgentResponse(observed="ERROR", reason="agent unreachable")
        except requests.Timeout:
            return AgentResponse(observed="ERROR", reason="agent timeout")

        if resp.status_code != 200:
            return AgentResponse(
                observed="ERROR",
                reason=f"HTTP {resp.status_code}",
                raw={"status_code": resp.status_code, "body": resp.text},
            )

        body = resp.json()
        status = body.get("status", "")
        observed = _STATUS_MAP.get(status, "ERROR")
        reason = None
        if body.get("error"):
            reason = body["error"].get("message", str(body["error"]))

        return AgentResponse(observed=observed, reason=reason, raw=body)

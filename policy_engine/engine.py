"""
L2 Policy Engine — deterministic evaluation orchestrator.

Accepts the agent's SwapIntent and ToolResponse (duck-typed) and returns a
plain dict with ``decision`` ("ALLOW" | "BLOCK") and ``violations`` list.

The result is **non-overridable** by LLM output: if any rule fires, the
transaction is blocked regardless of what the agent suggests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .rules import (
    Violation,
    check_token_allowlist,
    check_router_allowlist,
    check_slippage,
    check_value_cap,
)


def evaluate_policy(intent: Any, tool_response: Any) -> Dict[str, Any]:
    """Run all L2 deterministic rules and return a policy decision.

    Parameters
    ----------
    intent :
        Duck-typed SwapIntent — must expose ``sell_token``, ``buy_token``,
        ``sell_amount``.
    tool_response :
        Duck-typed ToolResponse — must expose ``market_snapshot`` (dict) and
        ``quote`` (with ``tx.to`` and ``to_token_amount``).

    Returns
    -------
    dict
        ``{"decision": "ALLOW"|"BLOCK", "violations": [...], "checked_at": ...}``
    """
    violations: List[Dict[str, Any]] = []

    try:
        sell_token: str = intent.sell_token
        buy_token: str = intent.buy_token
        sell_amount: str = str(intent.sell_amount)

        market_snapshot: Dict[str, float] = tool_response.market_snapshot

        quote = tool_response.quote
        router_address: str = quote.tx.to
        buy_amount: str = str(quote.to_token_amount)

        # ── R-01  Token allowlist ────────────────────────────────────────
        v = check_token_allowlist(sell_token, buy_token)
        if v:
            violations.append(v.to_dict())

        # ── R-02  Router allowlist ───────────────────────────────────────
        v = check_router_allowlist(router_address)
        if v:
            violations.append(v.to_dict())

        # ── R-03  Slippage ───────────────────────────────────────────────
        v = check_slippage(
            sell_token, buy_token, sell_amount, buy_amount, market_snapshot,
        )
        if v:
            violations.append(v.to_dict())

        # ── R-04  Value cap ──────────────────────────────────────────────
        v = check_value_cap(sell_token, sell_amount, market_snapshot)
        if v:
            violations.append(v.to_dict())

    except Exception as exc:
        # Fail-safe: any unexpected error blocks the transaction.
        violations.append({
            "rule_id": "R-SYS",
            "description": f"Policy evaluation error: {exc}",
            "details": {},
        })

    decision = "BLOCK" if violations else "ALLOW"
    return {
        "decision": decision,
        "violations": violations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

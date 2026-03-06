"""
L2 Policy Engine — deterministic evaluation orchestrator.

Accepts the agent's SwapIntent and ToolResponse (duck-typed) and returns a
plain dict with ``decision`` ("ALLOW" | "BLOCK") and ``violations`` list.

The result is **non-overridable** by LLM output: if any rule fires, the
transaction is blocked regardless of what the agent suggests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

from .rules import (
    Violation,
    check_token_allowlist,
    check_router_allowlist,
    check_slippage,
    check_value_cap,
    check_no_unlimited_approval,
    check_txplan_structure,
    check_network_scope,
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
        # ── R-05  No unlimited approvals ───────────────────────────────────
        tx_data = getattr(quote.tx, "data", "")
        tx_value = getattr(quote.tx, "value", "0")
        v = check_no_unlimited_approval(tx_data, tx_value)
        if v:
            violations.append(v.to_dict())

        # ── R-07  TxPlan structure validation ─────────────────────────────
        tx_dict = {
            "to": getattr(quote.tx, "to", None),
            "data": getattr(quote.tx, "data", None),
            "value": getattr(quote.tx, "value", None),
            "gas": getattr(quote, "estimated_gas", None),
        }
        v = check_txplan_structure(tx_dict)
        if v:
            violations.append(v.to_dict())

        # ── R-17  Network scope enforcement ──────────────────────────────
        chain_id = getattr(intent, "chain_id", None)
        if chain_id is not None:
            v = check_network_scope(chain_id)
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

    # ── Audit context ────────────────────────────────────────────────────
    audit: Dict[str, Any] = {
        "sell_token": getattr(intent, "sell_token", None),
        "buy_token": getattr(intent, "buy_token", None),
        "sell_amount": str(getattr(intent, "sell_amount", "")),
        "chain_id": getattr(intent, "chain_id", None),
        "router": getattr(getattr(tool_response, "quote", None),
                          "tx", SimpleNamespace()).to
                  if hasattr(getattr(tool_response, "quote", None), "tx")
                  else None,
        "rules_checked": ["R-01", "R-02", "R-03", "R-04", "R-05", "R-07", "R-17"],
    }

    return {
        "decision": decision,
        "violations": violations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "audit": audit,
    }

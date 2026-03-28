"""
L2 Policy Engine deterministic evaluation orchestrator.

Accepts the agent's SwapIntent and ToolResponse (duck-typed) and returns a
plain dict with ``decision`` ("ALLOW" | "BLOCK") and ``violations`` list.

The result is non-overridable by LLM output: if any rule fires, the
transaction is blocked regardless of what the agent suggests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

from . import config as cfg
from .rules import (
    check_network_scope,
    check_manual_deadline_override,
    check_manual_price_override,
    check_manual_slippage_override,
    check_no_unlimited_approval,
    check_quote_expiry,
    check_request_numeric_sanity,
    check_request_override_safety,
    check_requested_chain_override,
    check_request_trade_sanity,
    check_router_allowlist,
    check_slippage,
    check_token_allowlist,
    check_txplan_structure,
    check_value_cap,
    compute_slippage_bps,
)


def evaluate_policy(intent: Any, tool_response: Any) -> Dict[str, Any]:
    """Run all L2 deterministic rules and return a policy decision."""
    violations: List[Dict[str, Any]] = []
    request_signals: Dict[str, object] = {}

    try:
        sell_token: str = intent.sell_token
        buy_token: str = intent.buy_token
        sell_amount: str = str(intent.sell_amount)
        request_signals: Dict[str, object] = getattr(intent, "request_signals", {}) or {}

        market_snapshot: Dict[str, float] = tool_response.market_snapshot
        quote = tool_response.quote
        router_address: str = quote.tx.to
        buy_amount: str = str(quote.to_token_amount)
        quote_metadata: Dict[str, Any] = getattr(quote, "metadata", {}) or {}

        computed_slippage_bps = compute_slippage_bps(
            sell_token=sell_token,
            buy_token=buy_token,
            sell_amount_raw=sell_amount,
            buy_amount_raw=buy_amount,
            market_snapshot=market_snapshot,
        )

        for violation in (
            check_token_allowlist(sell_token, buy_token),
            check_request_trade_sanity(sell_token, buy_token, request_signals),
            check_request_numeric_sanity(request_signals),
            check_manual_slippage_override(request_signals),
            check_router_allowlist(router_address),
            check_slippage(sell_token, buy_token, sell_amount, buy_amount, market_snapshot),
            check_value_cap(sell_token, sell_amount, market_snapshot),
            check_no_unlimited_approval(
                getattr(quote.tx, "data", ""),
                getattr(quote.tx, "value", "0"),
            ),
            check_request_override_safety(request_signals),
            check_txplan_structure(
                {
                    "to": getattr(quote.tx, "to", None),
                    "data": getattr(quote.tx, "data", None),
                    "value": getattr(quote.tx, "value", None),
                    "gas": getattr(quote, "estimated_gas", None),
                    "max_slippage_bps": quote_metadata.get("max_slippage_bps", cfg.MAX_SLIPPAGE_BPS),
                    "quote_expires_at": quote_metadata.get("quote_expires_at"),
                }
            ),
            check_manual_deadline_override(request_signals),
            check_manual_price_override(request_signals),
            check_quote_expiry(quote_metadata.get("quote_expires_at")),
            check_requested_chain_override(request_signals),
        ):
            if violation:
                violations.append(violation.to_dict())

        chain_id = getattr(intent, "chain_id", None)
        if chain_id is not None:
            violation = check_network_scope(chain_id)
            if violation:
                violations.append(violation.to_dict())
    except Exception as exc:
        violations.append(
            {
                "rule_id": "R-SYS",
                "description": f"Policy evaluation error: {exc}",
                "details": {},
            }
        )
        computed_slippage_bps = None
        quote_metadata = {}

    decision = "BLOCK" if violations else "ALLOW"
    audit: Dict[str, Any] = {
        "sell_token": getattr(intent, "sell_token", None),
        "buy_token": getattr(intent, "buy_token", None),
        "sell_amount": str(getattr(intent, "sell_amount", "")),
        "chain_id": getattr(intent, "chain_id", None),
        "router": getattr(getattr(tool_response, "quote", None), "tx", SimpleNamespace()).to
        if hasattr(getattr(tool_response, "quote", None), "tx")
        else None,
        "computed_slippage_bps": round(computed_slippage_bps, 2) if computed_slippage_bps is not None else None,
        "max_slippage_bps": quote_metadata.get("max_slippage_bps", cfg.MAX_SLIPPAGE_BPS),
        "quote_expires_at": quote_metadata.get("quote_expires_at"),
        "request_signals": request_signals,
        "rules_checked": ["R-01", "R-02", "R-03", "R-04", "R-05", "R-07", "R-09", "R-13", "R-16", "R-17", "R-23"],
    }

    return {
        "decision": decision,
        "violations": violations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "audit": audit,
    }

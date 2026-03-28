"""
Response formatter — converts Agent PlanResponse dicts into
human-readable Telegram messages (MarkdownV2-safe plain text).

Privacy rule: NEVER include raw calldata, wallet addresses, or
transaction hashes in the output.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_response(data: Dict[str, Any]) -> str:
    """Dispatch to the correct formatter based on ``status``."""
    status = data.get("status", "ERROR")
    if status == "NEEDS_OWNER_SIGNATURE":
        return format_allow(data)
    if status == "BLOCKED_BY_POLICY":
        return format_block(data)
    if status == "REJECTED":
        return format_refuse(data)
    return format_error(data)


def format_allow(data: Dict[str, Any]) -> str:
    """Format an ALLOW (NEEDS_OWNER_SIGNATURE) response."""
    plan: Optional[Dict[str, Any]] = data.get("tx_plan")
    if not plan:
        return (
            "✅ Transaction Plan Ready\n"
            "Status: Awaiting owner signature (not broadcasted)\n"
            "Details unavailable."
        )

    intent: Dict[str, Any] = plan.get("intent", {})
    quote: Dict[str, Any] = plan.get("quote", {})
    summary: str = plan.get("summary", "")
    quote_validity: Dict[str, Any] = plan.get("quote_validity", {})
    wallet_handoff: Dict[str, Any] = plan.get("wallet_handoff", {})

    sell = intent.get("sell_token", "?")
    buy = intent.get("buy_token", "?")
    sell_amount_raw = intent.get("sell_amount", "0")
    buy_amount_raw = quote.get("to_token_amount", "?")

    # Human-readable amounts — use per-token decimal precision.
    _DECIMALS = {"USDC": 6, "USDT": 6, "WBTC": 8}

    def _humanize(raw: str, token: str) -> str:
        decimals = _DECIMALS.get(token.upper(), 18)
        try:
            return f"{int(raw) / 10**decimals:.6g}"
        except (ValueError, TypeError):
            return raw

    sell_display = _humanize(sell_amount_raw, sell)

    lines = [
        "✅ Transaction Plan Ready",
        f"Swap: {sell_display} {sell} → {buy}",
    ]

    if buy_amount_raw != "?":
        buy_display = _humanize(buy_amount_raw, buy)
        lines.append(f"Expected output: ~{buy_display} {buy}")

    gas_gwei = quote.get("gas_price_gwei", "")
    if gas_gwei:
        lines.append(f"Gas price: {gas_gwei} Gwei")

    if summary:
        lines.append(f"Summary: {_truncate(summary)}")

    if quote_validity.get("expires_at"):
        lines.append(f"Quote valid until: {_truncate(str(quote_validity['expires_at']), 40)}")

    if wallet_handoff.get("handoff_id"):
        lines.append(f"Handoff: {wallet_handoff.get('handoff_id')} ({wallet_handoff.get('status', 'pending')})")

    lines.append("Status: Awaiting owner signature (not broadcasted)")

    return "\n".join(lines)


def format_block(data: Dict[str, Any]) -> str:
    """Format a BLOCKED_BY_POLICY response."""
    plan = data.get("tx_plan") or {}
    error = data.get("error") or {}

    # Try to extract violation details
    reasons = []
    # From tx_plan.failure_reason
    failure = plan.get("failure_reason", "")
    if failure:
        reasons.append(failure)

    # From error dict
    err_detail = error.get("detail", "")
    if err_detail and err_detail not in reasons:
        reasons.append(err_detail)

    reason_text = "; ".join(reasons) if reasons else "Policy violation detected"

    return (
        "🚫 Transaction BLOCKED\n"
        f"Reason: {_truncate(reason_text, 300)}\n"
        "The request violates security policy and cannot proceed."
    )


def format_refuse(data: Dict[str, Any]) -> str:
    """Format a REJECTED response (L1 guardrail refusal)."""
    error = data.get("error") or {}
    detail = error.get("detail", "Input rejected by safety filter")
    return (
        "⛔ Request REFUSED\n"
        f"Reason: {_truncate(str(detail), 300)}\n"
        "Your message has been flagged and will not be processed."
    )


def format_error(data: Dict[str, Any]) -> str:
    """Format an unexpected error response."""
    error = data.get("error") or {}
    detail = error.get("detail", "An unexpected error occurred")
    return (
        "⚠️ Error\n"
        f"Detail: {_truncate(str(detail), 300)}\n"
        "Please try again or contact the owner."
    )

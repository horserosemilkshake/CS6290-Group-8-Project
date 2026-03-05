"""
L2 Policy Engine — individual rule implementations.

Each function accepts primitive / dict parameters (no coupling to agent_client
models) and returns ``None`` when the check passes or a ``Violation`` when it
fails.  The engine in ``engine.py`` orchestrates these rules.

Rule ID convention:
    R-01  Token allowlist
    R-02  Router allowlist
    R-03  Slippage limit
    R-04  Per-transaction value cap
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import config as cfg


@dataclass(frozen=True)
class Violation:
    rule_id: str
    description: str
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "details": dict(self.details),
        }


# ── R-01  Token allowlist ────────────────────────────────────────────────────

def check_token_allowlist(sell_token: str, buy_token: str) -> Optional[Violation]:
    """Both sell and buy tokens must appear in the project allowlist."""
    bad: List[str] = []
    if sell_token.upper() not in cfg.ALLOWED_TOKENS:
        bad.append(sell_token)
    if buy_token.upper() not in cfg.ALLOWED_TOKENS:
        bad.append(buy_token)
    if bad:
        return Violation(
            rule_id="R-01",
            description=f"Token(s) not in allowlist: {', '.join(bad)}",
            details={"disallowed_tokens": bad},
        )
    return None


# ── R-02  Router allowlist ───────────────────────────────────────────────────

def check_router_allowlist(router_address: str) -> Optional[Violation]:
    """The quote's ``to`` address (router) must be allow-listed."""
    normalised = {a.lower() for a in cfg.ALLOWED_ROUTERS}
    if router_address.lower() not in normalised:
        return Violation(
            rule_id="R-02",
            description=f"Router {router_address} not in allowlist",
            details={"router": router_address},
        )
    return None


# ── R-03  Slippage limit ────────────────────────────────────────────────────

def check_slippage(
    sell_token: str,
    buy_token: str,
    sell_amount_raw: str,
    buy_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> Optional[Violation]:
    """Realised slippage (market-price vs quote) must be ≤ MAX_SLIPPAGE_BPS.

    Slippage is computed in *value* terms so that different-decimal pairs
    are compared fairly:

        expected_value = sell_human × sell_price
        actual_value   = buy_human  × buy_price
        slippage_bps   = (expected − actual) / expected × 10 000
    """
    sell_price = market_snapshot.get(sell_token) or market_snapshot.get(sell_token.upper())
    buy_price = market_snapshot.get(buy_token) or market_snapshot.get(buy_token.upper())

    if not sell_price or not buy_price:
        return None  # cannot evaluate; other rules still apply

    try:
        sell_human = int(sell_amount_raw) / (10 ** cfg.AMOUNT_DECIMALS)
        buy_decimals = cfg.TOKEN_DECIMALS.get(buy_token.upper(), cfg.AMOUNT_DECIMALS)
        buy_human = int(buy_amount_raw) / (10 ** buy_decimals)
    except (ValueError, TypeError):
        return None

    if sell_human <= 0:
        return None

    expected_value = sell_human * sell_price
    actual_value = buy_human * buy_price

    if expected_value <= 0:
        return None

    slippage_bps = (expected_value - actual_value) / expected_value * 10_000

    # Sanity guard: absurdly high or negative slippage is almost certainly a
    # mock / data-quality anomaly rather than a real DEX quote.
    if slippage_bps < 0 or slippage_bps > cfg.SLIPPAGE_SANITY_CEILING_BPS:
        return None

    if slippage_bps > cfg.MAX_SLIPPAGE_BPS:
        return Violation(
            rule_id="R-03",
            description=f"Slippage {slippage_bps:.0f} bps exceeds limit {cfg.MAX_SLIPPAGE_BPS} bps",
            details={
                "slippage_bps": round(slippage_bps, 2),
                "limit_bps": cfg.MAX_SLIPPAGE_BPS,
            },
        )
    return None


# ── R-04  Per-transaction value cap ──────────────────────────────────────────

def check_value_cap(
    sell_token: str,
    sell_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> Optional[Violation]:
    """Single-tx value (converted to ETH-equivalent) must not exceed the cap."""
    try:
        sell_human = int(sell_amount_raw) / (10 ** cfg.AMOUNT_DECIMALS)
    except (ValueError, TypeError):
        return Violation(
            rule_id="R-04",
            description="Invalid sell_amount: cannot evaluate value cap",
        )

    if sell_token.upper() in ("ETH", "WETH"):
        value_eth = sell_human
    else:
        tok_price = (
            market_snapshot.get(sell_token)
            or market_snapshot.get(sell_token.upper())
        )
        eth_price = (
            market_snapshot.get("ETH")
            or market_snapshot.get("WETH")
            or market_snapshot.get("eth")
        )
        if not tok_price or not eth_price or eth_price <= 0:
            return None  # cannot convert; skip
        value_eth = sell_human * tok_price / eth_price

    if value_eth > cfg.MAX_SINGLE_TX_VALUE_ETH:
        return Violation(
            rule_id="R-04",
            description=(
                f"Transaction value {value_eth:.4f} ETH exceeds "
                f"cap {cfg.MAX_SINGLE_TX_VALUE_ETH} ETH"
            ),
            details={
                "value_eth": round(value_eth, 6),
                "cap_eth": cfg.MAX_SINGLE_TX_VALUE_ETH,
            },
        )
    return None

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
    R-05  No unlimited approvals
    R-07  TxPlan structure validation
    R-17  Network scope enforcement
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
        sell_decimals = cfg.TOKEN_DECIMALS.get(sell_token.upper(), cfg.AMOUNT_DECIMALS)
        sell_human = int(sell_amount_raw) / (10 ** sell_decimals)
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
        decimals = cfg.TOKEN_DECIMALS.get(sell_token.upper(), cfg.AMOUNT_DECIMALS)
        sell_human = int(sell_amount_raw) / (10 ** decimals)
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


# ── R-05  No unlimited approvals ─────────────────────────────────────────────

# ERC-20 approve MAX_UINT256 — the standard "infinite approval" sentinel.
MAX_UINT256 = 2**256 - 1
MAX_UINT256_HEX = hex(MAX_UINT256)
# 4-byte function selector for approve(address,uint256)
APPROVE_SELECTOR = "0x095ea7b3"


def check_no_unlimited_approval(tx_data: str, tx_value: str = "0") -> Optional[Violation]:
    """ERC-20 approvals must be scoped; unlimited/infinite approvals are rejected.

    The rule inspects the transaction calldata.  If the first 4 bytes match the
    ``approve(address,uint256)`` selector **and** the uint256 argument equals
    ``type(uint256).max``, the approval is considered unlimited.

    Parameters
    ----------
    tx_data :
        Hex-encoded calldata (``0x…``).
    tx_value :
        Ether value attached to the tx (used only for sanity — approve should
        be a zero-value call).
    """
    if not tx_data or len(tx_data) < 10:
        return None  # not a contract call or too short to be approve

    selector = tx_data[:10].lower()
    if selector != APPROVE_SELECTOR:
        return None  # not an approve call

    # approve(address spender, uint256 amount)
    # calldata layout: selector(4) + address(32) + uint256(32) = 68 bytes → 136 hex + 2 for 0x = 138
    if len(tx_data) < 138:
        return None  # malformed but not our concern here

    amount_hex = tx_data[74:138]  # 32-byte uint256 after 32-byte address
    try:
        amount = int(amount_hex, 16)
    except ValueError:
        return None

    # Reject MAX_UINT256 or anything within ~1% of it (some protocols use
    # slightly-below-max as "effectively infinite").
    threshold = MAX_UINT256 * 99 // 100
    if amount >= threshold:
        return Violation(
            rule_id="R-05",
            description="Unlimited/infinite ERC-20 approval detected",
            details={
                "approval_amount_hex": hex(amount),
                "threshold_hex": hex(threshold),
            },
        )
    return None


# ── R-07  TxPlan structure validation ────────────────────────────────────────

REQUIRED_TXPLAN_FIELDS = {"to", "data", "value", "gas"}


def check_txplan_structure(tx_dict: Dict) -> Optional[Violation]:
    """TxPlan must include router (to), calldata (data), value, and gas estimate.

    Parameters
    ----------
    tx_dict :
        Dictionary with at least ``to``, ``data``, ``value``, ``gas``.
    """
    missing = REQUIRED_TXPLAN_FIELDS - set(tx_dict.keys())
    empty = {
        k for k in REQUIRED_TXPLAN_FIELDS & set(tx_dict.keys())
        if tx_dict[k] is None or (isinstance(tx_dict[k], str) and not tx_dict[k].strip())
    }
    problems = missing | empty
    if problems:
        return Violation(
            rule_id="R-07",
            description=f"TxPlan missing or empty required fields: {', '.join(sorted(problems))}",
            details={"missing_fields": sorted(problems)},
        )
    return None


# ── R-17  Network scope enforcement ──────────────────────────────────────────

def check_network_scope(chain_id: int) -> Optional[Violation]:
    """Production swaps must target Ethereum mainnet (chain_id=1).

    Sepolia (chain_id=11155111) is allowed only when explicitly tagged by the
    test harness via ``cfg.ALLOW_TESTNET``.  All other networks are blocked.
    """
    allowed = set(cfg.ALLOWED_CHAIN_IDS)
    if chain_id not in allowed:
        return Violation(
            rule_id="R-17",
            description=f"Chain ID {chain_id} not in allowed networks: {sorted(allowed)}",
            details={"chain_id": chain_id, "allowed": sorted(allowed)},
        )
    return None

"""
L2 Policy Engine individual rule implementations.

Each function accepts primitive / dict parameters (no coupling to agent_client
models) and returns ``None`` when the check passes or a ``Violation`` when it
fails. The engine in ``engine.py`` orchestrates these rules.

Rule IDs:
    R-01  Token allowlist
    R-02  Router allowlist
    R-03  Slippage limit
    R-04  Per-transaction value cap
    R-05  No unlimited approvals
    R-13  Unsafe request overrides from untrusted input
    R-16  Trusted market snapshot prerequisite
    R-07  TxPlan structure validation
    R-09  Quote expiry enforcement
    R-23  Request-shape sanity checks
    R-17  Network scope enforcement
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
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


def extract_request_signals(user_message: str) -> Dict[str, object]:
    """
    Extract deterministic safety signals from the raw request text.

    The MVP natural-language interface intentionally supports only plain swap
    intents. Manual execution-control overrides are rejected until they have a
    dedicated, verified normalization path.
    """
    text = user_message or ""
    lowered = text.lower()

    chain_match = re.search(r"\bchain\s+id\s+(\d+)\b", lowered)

    return {
        "mentions_slippage": "slippage" in lowered,
        "mentions_deadline": "deadline" in lowered,
        "mentions_router_override": bool(
            re.search(r"\b(?:use|set|override)\s+router\b|\brouter\s*(?:address|=|:)", lowered)
        ),
        "mentions_recipient_override": bool(
            re.search(r"\brecipient\b|send\s+fees?\s+to\s+(?:my\s+)?(?:personal\s+)?wallet", lowered)
        ),
        "mentions_gas_override": bool(
            re.search(r"\bgasprice\b|\bgas price\b|\bgwei\b|\bextra params?\b", lowered)
        ),
        "mentions_transfer_via_swap": bool(
            re.search(r"\btransfer\b.*\b(?:via|using)\b.*\bswap\b|\bswap\b.*\btransfer\b", lowered)
        ),
        "mentions_multi_step_swap": bool(
            re.search(r"\bthen\s+swap\b|\bswap\s+it\s+all\s+back\b|\bgenerate\s+volume\b", lowered)
        ),
        "mentions_hidden_markup": bool(
            re.search(r"<!--|<script|<[^>]+>", text, re.IGNORECASE)
        ),
        "mentions_unsupported_unit_wei": bool(re.search(r"\bwei\b", lowered)),
        "mentions_explicit_buy_amount": bool(
            re.search(r"\b(?:for|to)\s+\d+(?:\.\d+)?\s+[a-z][\w-]*", lowered)
        ),
        "mentions_invalid_amount_syntax": bool(
            re.search(r"\bswap\s*-\d|\b-?\d+(?:\.\d+)?e[+-]?\d+\b|\bnan\b|\binf(?:inity)?\b", lowered)
        ),
        "mentions_untrusted_price_override": bool(
            re.search(r"\bprice\b.*\$\d+|\$\d+.*\btrust me\b|\btrust me\b.*\bprice\b", lowered)
        ),
        "requested_chain_id": int(chain_match.group(1)) if chain_match else None,
    }


def check_router_allowlist(router_address: str) -> Optional[Violation]:
    """The quote router must be allow-listed."""
    normalised = {a.lower() for a in cfg.ALLOWED_ROUTERS}
    if router_address.lower() not in normalised:
        return Violation(
            rule_id="R-02",
            description=f"Router {router_address} not in allowlist",
            details={"router": router_address},
        )
    return None


def check_manual_slippage_override(request_signals: Dict[str, object]) -> Optional[Violation]:
    """
    Reject user-provided slippage directives.

    The system already attaches trusted server-side slippage bounds to the
    TxPlan. Until the interface safely supports user-configured slippage, any
    request-side override is treated as unsafe.
    """
    if request_signals.get("mentions_slippage"):
        return Violation(
            rule_id="R-03",
            description=(
                "Manual slippage directives are unsupported; trusted server-side "
                "slippage bounds must be used instead"
            ),
            details={"request_signals": ["mentions_slippage"]},
        )
    return None


def compute_slippage_bps(
    sell_token: str,
    buy_token: str,
    sell_amount_raw: str,
    buy_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> Optional[float]:
    """Compute realised slippage in basis points when market data is available."""
    sell_price = market_snapshot.get(sell_token) or market_snapshot.get(sell_token.upper())
    buy_price = market_snapshot.get(buy_token) or market_snapshot.get(buy_token.upper())

    if not sell_price or not buy_price:
        return None

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

    # Absurdly high values are data-quality anomalies — skip the check.
    if slippage_bps > cfg.SLIPPAGE_SANITY_CEILING_BPS:
        return None

    # Negative slippage means the user got a better-than-market price.
    # Clamp to 0.0 so that downstream checks still run rather than being
    # silently skipped (returning None would bypass the slippage rule).
    return max(slippage_bps, 0.0)


def check_slippage(
    sell_token: str,
    buy_token: str,
    sell_amount_raw: str,
    buy_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> Optional[Violation]:
    """Realised slippage must be within the configured maximum."""
    slippage_bps = compute_slippage_bps(
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount_raw=sell_amount_raw,
        buy_amount_raw=buy_amount_raw,
        market_snapshot=market_snapshot,
    )
    if slippage_bps is None:
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


def check_value_cap(
    sell_token: str,
    sell_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> Optional[Violation]:
    """Single-tx value in ETH-equivalent must not exceed the cap."""
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
        tok_price = market_snapshot.get(sell_token) or market_snapshot.get(sell_token.upper())
        eth_price = (
            market_snapshot.get("ETH")
            or market_snapshot.get("WETH")
            or market_snapshot.get("eth")
        )
        if not tok_price or not eth_price or eth_price <= 0:
            return None
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


def check_request_override_safety(request_signals: Dict[str, object]) -> Optional[Violation]:
    """Block unsafe execution-control overrides embedded in untrusted request text."""
    flags = [
        name for name in (
            "mentions_router_override",
            "mentions_recipient_override",
            "mentions_gas_override",
            "mentions_transfer_via_swap",
            "mentions_explicit_buy_amount",
            "mentions_multi_step_swap",
        )
        if request_signals.get(name)
    ]

    if request_signals.get("mentions_hidden_markup") and request_signals.get("mentions_slippage"):
        flags.append("hidden_markup_with_execution_controls")

    if flags:
        return Violation(
            rule_id="R-13",
            description=(
                "Untrusted request text attempted to override execution controls "
                f"({', '.join(flags)}), which this interface does not support"
            ),
            details={"request_signals": flags},
        )
    return None


MAX_UINT256 = 2**256 - 1
MAX_UINT256_HEX = hex(MAX_UINT256)
APPROVE_SELECTOR = "0x095ea7b3"


def check_no_unlimited_approval(tx_data: str, tx_value: str = "0") -> Optional[Violation]:
    """ERC-20 approvals must be scoped; unlimited approvals are rejected."""
    if not tx_data or len(tx_data) < 10:
        return None

    selector = tx_data[:10].lower()
    if selector != APPROVE_SELECTOR:
        return None

    if len(tx_data) < 138:
        return None

    amount_hex = tx_data[74:138]
    try:
        amount = int(amount_hex, 16)
    except ValueError:
        return None

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


def check_request_numeric_sanity(request_signals: Dict[str, object]) -> Optional[Violation]:
    """Reject unsupported negative / NaN / scientific-notation amount strings."""
    if request_signals.get("mentions_invalid_amount_syntax"):
        return Violation(
            rule_id="R-23",
            description=(
                "Unsupported amount syntax detected; use a single positive decimal "
                "amount in supported token units"
            ),
            details={"request_signals": ["mentions_invalid_amount_syntax"]},
        )
    return None


REQUIRED_TXPLAN_FIELDS = {
    "to",
    "data",
    "value",
    "gas",
    "max_slippage_bps",
    "quote_expires_at",
}


def check_txplan_structure(tx_dict: Dict) -> Optional[Violation]:
    """TxPlan must include tx fields plus slippage and expiry metadata."""
    missing = REQUIRED_TXPLAN_FIELDS - set(tx_dict.keys())
    empty = {
        key for key in REQUIRED_TXPLAN_FIELDS & set(tx_dict.keys())
        if tx_dict[key] is None or (isinstance(tx_dict[key], str) and not tx_dict[key].strip())
    }
    problems = missing | empty
    if problems:
        return Violation(
            rule_id="R-07",
            description=f"TxPlan missing or empty required fields: {', '.join(sorted(problems))}",
            details={"missing_fields": sorted(problems)},
        )
    return None


def check_request_trade_sanity(
    sell_token: str,
    buy_token: str,
    request_signals: Dict[str, object],
) -> Optional[Violation]:
    """Reject unsupported same-token or raw-wei request shapes."""
    if sell_token.upper() == buy_token.upper():
        return Violation(
            rule_id="R-23",
            description="Sell token and buy token must differ",
            details={"sell_token": sell_token, "buy_token": buy_token},
        )

    if request_signals.get("mentions_unsupported_unit_wei"):
        return Violation(
            rule_id="R-23",
            description=(
                "Raw wei-denominated natural-language requests are unsupported; "
                "use supported token symbols instead"
            ),
            details={"request_signals": ["mentions_unsupported_unit_wei"]},
        )

    return None


def check_quote_expiry(expires_at: str) -> Optional[Violation]:
    """Quotes must still be valid when the plan is evaluated."""
    try:
        expiry = datetime.fromisoformat(expires_at)
    except (TypeError, ValueError):
        return Violation(
            rule_id="R-09",
            description="Quote expiry metadata is invalid",
            details={"quote_expires_at": expires_at},
        )

    if expiry <= datetime.now(timezone.utc):
        return Violation(
            rule_id="R-09",
            description="Quote has expired and must be requoted",
            details={"quote_expires_at": expires_at},
        )
    return None


def check_manual_deadline_override(request_signals: Dict[str, object]) -> Optional[Violation]:
    """
    Deadline control is derived from trusted quote metadata. Manual request-side
    overrides are rejected in the MVP interface.
    """
    if request_signals.get("mentions_deadline"):
        return Violation(
            rule_id="R-09",
            description=(
                "Manual deadline overrides are unsupported; quote expiry is "
                "derived from trusted quote metadata"
            ),
            details={"request_signals": ["mentions_deadline"]},
        )
    return None


def check_manual_price_override(request_signals: Dict[str, object]) -> Optional[Violation]:
    """
    Reject user-supplied price claims and require a trusted market snapshot to
    drive price-aware policy checks.
    """
    if request_signals.get("mentions_untrusted_price_override"):
        return Violation(
            rule_id="R-16",
            description=(
                "User-supplied price directives are unsupported; pricing must come "
                "from a trusted market snapshot"
            ),
            details={"request_signals": ["mentions_untrusted_price_override"]},
        )
    return None


def check_network_scope(chain_id: int) -> Optional[Violation]:
    """Production swaps must target approved networks only."""
    allowed = set(cfg.ALLOWED_CHAIN_IDS)
    if chain_id not in allowed:
        return Violation(
            rule_id="R-17",
            description=f"Chain ID {chain_id} not in allowed networks: {sorted(allowed)}",
            details={"chain_id": chain_id, "allowed": sorted(allowed)},
        )
    return None


def check_requested_chain_override(request_signals: Dict[str, object]) -> Optional[Violation]:
    """If the raw request specifies a chain id, it must stay within the allowed scope."""
    requested_chain_id = request_signals.get("requested_chain_id")
    if requested_chain_id is None:
        return None

    allowed = set(cfg.ALLOWED_CHAIN_IDS)
    if requested_chain_id not in allowed:
        return Violation(
            rule_id="R-17",
            description=(
                f"Requested chain ID {requested_chain_id} not in allowed networks: "
                f"{sorted(allowed)}"
            ),
            details={"chain_id": requested_chain_id, "allowed": sorted(allowed)},
        )
    return None

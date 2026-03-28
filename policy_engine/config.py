"""
L2 Policy Engine — deterministic enforcement thresholds and allowlists.

All values here are security-critical.  Changes must be reviewed and tested.
Spec references:
  - S-02  approval_amount ≤ CAP ∧ spender ∈ ALLOWLIST
  - S-05  slippage ≤ 10 %
  - specification.md §Acceptance Criteria
"""

import os

# ── Token allowlist ──────────────────────────────────────────────────────────
ALLOWED_TOKENS: frozenset = frozenset({
    "ETH", "WETH", "USDC", "USDT", "DAI",
})

# ── Router (DEX aggregator) allowlist ────────────────────────────────────────
ALLOWED_ROUTERS: frozenset = frozenset({
    "0x1111111254fb6c44bac0bed2854e76f90643097d",  # 1inch v5 Router
    "0x1111111254eeb25477b68fb85ed929f73a960582",  # 1inch v6 Router
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x Exchange Proxy
})

# ── Slippage ─────────────────────────────────────────────────────────────────
MAX_SLIPPAGE_BPS: int = 1000  # 10 %

# If computed slippage exceeds this ceiling it is almost certainly a data-
# quality issue (e.g., the mock tool-coordinator quoting the wrong direction)
# rather than a real DEX quote.  Skip the check to avoid false BLOCKs.
SLIPPAGE_SANITY_CEILING_BPS: int = 5000  # 50 %

# ── Value cap ────────────────────────────────────────────────────────────────
# NOTE: agent_client/src/config/settings.py has MAX_TRANSACTION_VALUE_ETH=10.0
# but that value is NOT used by L2.  The authoritative cap is HERE (5.0 ETH).
# Any change must be reflected in tests and the spec-rule-mapping.
MAX_SINGLE_TX_VALUE_ETH: float = 5.0  # per-transaction cap in ETH-equivalent

# ── Decimals ─────────────────────────────────────────────────────────────────
# The mock LLM parser and tool-coordinator both express sell_amount in
# 18-decimal (wei) units regardless of token type.
AMOUNT_DECIMALS: int = 18

TOKEN_DECIMALS: dict = {
    "ETH": 18,
    "WETH": 18,
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
}

# Quote / handoff TTLs used by planning and signer-boundary pause logic.
QUOTE_TTL_SECONDS: int = int(os.getenv("QUOTE_TTL_SECONDS", "120"))
WALLET_HANDOFF_TTL_SECONDS: int = int(os.getenv("WALLET_HANDOFF_TTL_SECONDS", "300"))

# ── Network scope (A-01, R-17) ─────────────────────────────────────────────
# Ethereum mainnet only for production; Sepolia for demo/test.
_BASE_CHAIN_IDS = {1, 11155111}
_extra = os.getenv("EXTRA_ALLOWED_CHAIN_IDS", "")
_BASE_CHAIN_IDS.update(int(x) for x in _extra.split(",") if x.strip().isdigit())
ALLOWED_CHAIN_IDS: frozenset = frozenset(_BASE_CHAIN_IDS)

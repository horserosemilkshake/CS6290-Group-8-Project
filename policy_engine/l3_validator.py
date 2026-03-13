"""
L3 On-Chain Validator — calls SwapGuard.validateSwap() via JSON-RPC eth_call.

Zero external dependencies: uses only stdlib (urllib, json, os).
Requires a running Anvil (or any EVM node) with SwapGuard deployed.
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple

from policy_engine import config as cfg

# ── Contract constants ─────────────────────────────────────────────────────

VALIDATE_SWAP_SELECTOR = "0x708af86b"

NATIVE_ETH_SENTINEL = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# Symbol → mainnet address mapping (also valid on mainnet fork).
# Local Anvil: these addresses have no code, but validateSwap only checks
# the allowedTokens mapping (populated by Deploy.s.sol), so it still works.
TOKEN_ADDRESS_MAP: Dict[str, str] = {
    "ETH":  NATIVE_ETH_SENTINEL,
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI":  "0x6B175474E89094C44Da98b954EedeAC495271d0F",
}


def _get_rpc_url() -> str:
    port = os.getenv("ANVIL_PORT", "8545")
    return os.getenv("L3_RPC_URL", f"http://127.0.0.1:{port}")


def _get_contract_address() -> Optional[str]:
    return os.getenv("SWAP_GUARD_ADDRESS")


def _pad32(hex_str: str) -> str:
    """Left-pad a hex string (without 0x) to 64 hex chars (32 bytes)."""
    return hex_str.lower().zfill(64)


def _encode_address(addr: str) -> str:
    return _pad32(addr.replace("0x", ""))


def _encode_uint256(value: int) -> str:
    return _pad32(hex(value)[2:])


def _build_calldata(
    sell_token: str,
    buy_token: str,
    router: str,
    eth_equivalent_wei: int,
) -> str:
    """ABI-encode a validateSwap(address,address,address,uint256) call."""
    return (
        VALIDATE_SWAP_SELECTOR
        + _encode_address(sell_token)
        + _encode_address(buy_token)
        + _encode_address(router)
        + _encode_uint256(eth_equivalent_wei)
    )


def _eth_call(rpc_url: str, to: str, data: str) -> Tuple[bool, str]:
    """Raw JSON-RPC eth_call.  Returns (success, result_or_error)."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
        "id": 1,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError) as exc:
        return False, f"RPC unreachable: {exc}"

    if "error" in result:
        err = result["error"]
        msg = err.get("message", str(err))
        # Anvil returns the revert reason inside the error message
        return False, msg
    return True, result.get("result", "0x")


def _compute_eth_equivalent(
    sell_token: str,
    sell_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> int:
    """Compute ETH-equivalent value in wei, mirroring L2 check_value_cap logic."""
    decimals = cfg.TOKEN_DECIMALS.get(sell_token.upper(), cfg.AMOUNT_DECIMALS)
    sell_human = int(sell_amount_raw) / (10 ** decimals)

    if sell_token.upper() in ("ETH", "WETH"):
        value_eth = sell_human
    else:
        tok_price = (
            market_snapshot.get(sell_token)
            or market_snapshot.get(sell_token.upper())
            or 0.0
        )
        eth_price = (
            market_snapshot.get("ETH")
            or market_snapshot.get("WETH")
            or market_snapshot.get("eth")
            or 0.0
        )
        if not tok_price or not eth_price or eth_price <= 0:
            value_eth = 0.0
        else:
            value_eth = sell_human * tok_price / eth_price

    return int(value_eth * 10**18)


def validate_l3(intent, tool_response) -> Dict:
    """
    Call SwapGuard.validateSwap() on-chain.

    Returns dict compatible with L2 evaluate_policy output:
        {"decision": "ALLOW"|"BLOCK"|"SKIP", "violations": [...]}

    SKIP means L3 is not configured (no contract address) — caller should
    treat as non-blocking.
    """
    contract = _get_contract_address()
    if not contract:
        return {"decision": "SKIP", "violations": [], "reason": "SWAP_GUARD_ADDRESS not set"}

    sell_token_sym = intent.sell_token.upper()
    buy_token_sym = intent.buy_token.upper()

    sell_addr = TOKEN_ADDRESS_MAP.get(sell_token_sym)
    buy_addr = TOKEN_ADDRESS_MAP.get(buy_token_sym)
    if not sell_addr or not buy_addr:
        return {
            "decision": "BLOCK",
            "violations": [{"rule_id": "L3-R01", "description": f"Token address unknown for L3: {sell_token_sym} or {buy_token_sym}"}],
        }

    router = getattr(tool_response.quote.tx, "to", None)
    if not router:
        return {
            "decision": "BLOCK",
            "violations": [{"rule_id": "L3-R02", "description": "No router address in quote"}],
        }

    eth_eq_wei = _compute_eth_equivalent(
        sell_token_sym,
        str(intent.sell_amount),
        tool_response.market_snapshot,
    )

    calldata = _build_calldata(sell_addr, buy_addr, router, eth_eq_wei)
    rpc_url = _get_rpc_url()

    ok, result = _eth_call(rpc_url, contract, calldata)

    if ok:
        return {"decision": "ALLOW", "violations": []}

    # Parse revert reason from Anvil error message
    reason = result
    rule_id = "L3"
    if "R-01" in result:
        rule_id = "L3-R01"
    elif "R-02" in result:
        rule_id = "L3-R02"
    elif "R-04" in result:
        rule_id = "L3-R04"

    return {
        "decision": "BLOCK",
        "violations": [{"rule_id": rule_id, "description": reason}],
    }

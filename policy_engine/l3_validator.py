"""
L3 on-chain validator: calls SwapGuard.validateSwap() via JSON-RPC eth_call.

Zero external dependencies: uses only stdlib modules.
Requires a running EVM node and a deployed SwapGuard contract when enabled.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple
import urllib.error
import urllib.request

from policy_engine import config as cfg
from policy_engine.rules import compute_slippage_bps


_KECCAK_ROUND_CONSTANTS = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
]

_KECCAK_ROTATION_OFFSETS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)

NATIVE_ETH_SENTINEL = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
VALIDATE_SWAP_SIGNATURE = "validateSwap(address,address,address,uint256,uint256)"


def _rotl64(value: int, shift: int) -> int:
    shift %= 64
    return ((value << shift) | (value >> (64 - shift))) & 0xFFFFFFFFFFFFFFFF


def _keccak_f1600(state: List[int]) -> None:
    for round_constant in _KECCAK_ROUND_CONSTANTS:
        c = [
            state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
            for x in range(5)
        ]
        d = [c[(x - 1) % 5] ^ _rotl64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]

        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl64(
                    state[x + 5 * y],
                    _KECCAK_ROTATION_OFFSETS[x][y],
                )

        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ (
                    (~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y]
                )

        state[0] ^= round_constant


def _keccak_256(data: bytes) -> bytes:
    rate_bytes = 136
    state = [0] * 25
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate_bytes != rate_bytes - 1:
        padded.append(0x00)
    padded.append(0x80)

    for offset in range(0, len(padded), rate_bytes):
        block = padded[offset : offset + rate_bytes]
        for index, byte in enumerate(block):
            state[index // 8] ^= byte << (8 * (index % 8))
        _keccak_f1600(state)

    output = bytearray()
    while len(output) < 32:
        for index in range(rate_bytes):
            output.append((state[index // 8] >> (8 * (index % 8))) & 0xFF)
            if len(output) == 32:
                break
        if len(output) < 32:
            _keccak_f1600(state)
    return bytes(output)


def _function_selector(signature: str) -> str:
    return "0x" + _keccak_256(signature.encode("ascii")).hex()[:8]


VALIDATE_SWAP_SELECTOR = _function_selector(VALIDATE_SWAP_SIGNATURE)


TOKEN_ADDRESS_MAP: Dict[str, str] = {
    "ETH": NATIVE_ETH_SENTINEL,
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
}


def _get_rpc_url() -> str:
    port = os.getenv("ANVIL_PORT", "8545")
    return os.getenv("L3_RPC_URL", f"http://127.0.0.1:{port}")


def _get_contract_address() -> Optional[str]:
    return os.getenv("SWAP_GUARD_ADDRESS")


def _pad32(hex_str: str) -> str:
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
    slippage_bps: int,
) -> str:
    """ABI-encode validateSwap(address,address,address,uint256,uint256)."""
    return (
        VALIDATE_SWAP_SELECTOR
        + _encode_address(sell_token)
        + _encode_address(buy_token)
        + _encode_address(router)
        + _encode_uint256(eth_equivalent_wei)
        + _encode_uint256(slippage_bps)
    )


def _eth_call(rpc_url: str, to: str, data: str) -> Tuple[bool, str]:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
        "id": 1,
    }
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode())
    except (urllib.error.URLError, OSError) as exc:
        return False, f"RPC unreachable: {exc}"

    if "error" in result:
        err = result["error"]
        return False, err.get("message", str(err))
    return True, result.get("result", "0x")


def _compute_eth_equivalent(
    sell_token: str,
    sell_amount_raw: str,
    market_snapshot: Dict[str, float],
) -> int:
    decimals = cfg.TOKEN_DECIMALS.get(sell_token.upper(), cfg.AMOUNT_DECIMALS)
    sell_human = int(sell_amount_raw) / (10 ** decimals)

    if sell_token.upper() in ("ETH", "WETH"):
        value_eth = sell_human
    else:
        tok_price = market_snapshot.get(sell_token) or market_snapshot.get(sell_token.upper()) or 0.0
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

    Returns:
        {"decision": "ALLOW"|"BLOCK"|"SKIP", "violations": [...]}
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
            "violations": [
                {
                    "rule_id": "L3-R01",
                    "description": f"Token address unknown for L3: {sell_token_sym} or {buy_token_sym}",
                }
            ],
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
    slippage_bps = compute_slippage_bps(
        sell_token=sell_token_sym,
        buy_token=buy_token_sym,
        sell_amount_raw=str(intent.sell_amount),
        buy_amount_raw=str(tool_response.quote.to_token_amount),
        market_snapshot=tool_response.market_snapshot,
    )
    slippage_bps_int = int(round(slippage_bps or 0.0))

    calldata = _build_calldata(sell_addr, buy_addr, router, eth_eq_wei, slippage_bps_int)
    ok, result = _eth_call(_get_rpc_url(), contract, calldata)
    if ok:
        return {"decision": "ALLOW", "violations": []}

    rule_id = "L3"
    if "R-01" in result:
        rule_id = "L3-R01"
    elif "R-02" in result:
        rule_id = "L3-R02"
    elif "R-03" in result:
        rule_id = "L3-R03"
    elif "R-04" in result:
        rule_id = "L3-R04"

    return {
        "decision": "BLOCK",
        "violations": [{"rule_id": rule_id, "description": result}],
    }

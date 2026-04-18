#!/usr/bin/env python3
"""Check parity between L2 Python policy config and deployed L3 SwapGuard."""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Tuple

from policy_engine import config as cfg
from policy_engine.l3_validator import TOKEN_ADDRESS_MAP, _function_selector

import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def _get_rpc_url() -> str:
    port = os.getenv("ANVIL_PORT", "8545")
    return os.getenv("L3_RPC_URL", f"http://127.0.0.1:{port}")


def _encode_address(address: str) -> str:
    normalized = address.lower().removeprefix("0x")
    if len(normalized) != 40:
        raise ValueError(f"Invalid address: {address}")
    return normalized.rjust(64, "0")


def _eth_call(rpc_url: str, to: str, data: str) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    }
    request = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode("utf-8"))
    if "error" in body:
        raise RuntimeError(f"eth_call failed: {body['error']}")
    return str(body.get("result") or "0x")


def _call_noarg_uint(rpc_url: str, contract: str, signature: str) -> int:
    result = _eth_call(rpc_url, contract, _function_selector(signature))
    return int(result, 16)


def _call_noarg_address(rpc_url: str, contract: str, signature: str) -> str:
    result = _eth_call(rpc_url, contract, _function_selector(signature))
    return "0x" + result[-40:]


def _call_bool_mapping(rpc_url: str, contract: str, signature: str, address: str) -> bool:
    calldata = _function_selector(signature) + _encode_address(address)
    result = _eth_call(rpc_url, contract, calldata)
    return bool(int(result, 16))


def _expected_max_value_wei() -> int:
    return int(Decimal(str(cfg.MAX_SINGLE_TX_VALUE_ETH)) * Decimal(10**18))


def build_parity_report(rpc_url: str, contract: str) -> Dict[str, Any]:
    expected_tokens = {
        symbol: TOKEN_ADDRESS_MAP[symbol]
        for symbol in sorted(cfg.ALLOWED_TOKENS)
        if symbol in TOKEN_ADDRESS_MAP
    }
    missing_token_mappings = sorted(symbol for symbol in cfg.ALLOWED_TOKENS if symbol not in TOKEN_ADDRESS_MAP)
    expected_routers = sorted(cfg.ALLOWED_ROUTERS)

    observed_tokens = {
        symbol: _call_bool_mapping(rpc_url, contract, "allowedTokens(address)", address)
        for symbol, address in expected_tokens.items()
    }
    observed_routers = {
        router: _call_bool_mapping(rpc_url, contract, "allowedRouters(address)", router)
        for router in expected_routers
    }
    observed_max_value_wei = _call_noarg_uint(rpc_url, contract, "maxValueWei()")
    observed_max_slippage_bps = _call_noarg_uint(rpc_url, contract, "maxSlippageBps()")
    observed_owner = _call_noarg_address(rpc_url, contract, "owner()")

    mismatches: List[Dict[str, Any]] = []
    for symbol, allowed in observed_tokens.items():
        if not allowed:
            mismatches.append(
                {
                    "scope": "token_allowlist",
                    "item": symbol,
                    "expected": True,
                    "observed": allowed,
                }
            )

    for router, allowed in observed_routers.items():
        if not allowed:
            mismatches.append(
                {
                    "scope": "router_allowlist",
                    "item": router,
                    "expected": True,
                    "observed": allowed,
                }
            )

    expected_max_value_wei = _expected_max_value_wei()
    if observed_max_value_wei != expected_max_value_wei:
        mismatches.append(
            {
                "scope": "max_value_wei",
                "expected": expected_max_value_wei,
                "observed": observed_max_value_wei,
            }
        )

    if observed_max_slippage_bps != cfg.MAX_SLIPPAGE_BPS:
        mismatches.append(
            {
                "scope": "max_slippage_bps",
                "expected": cfg.MAX_SLIPPAGE_BPS,
                "observed": observed_max_slippage_bps,
            }
        )

    if missing_token_mappings:
        mismatches.append(
            {
                "scope": "token_address_mapping",
                "expected": "Every L2-allowed token has an L3 token address mapping",
                "observed": missing_token_mappings,
            }
        )

    return {
        "contract": contract,
        "rpc_url": rpc_url,
        "owner": observed_owner,
        "expected": {
            "allowed_tokens": expected_tokens,
            "allowed_routers": expected_routers,
            "max_value_wei": expected_max_value_wei,
            "max_slippage_bps": cfg.MAX_SLIPPAGE_BPS,
        },
        "observed": {
            "allowed_tokens": observed_tokens,
            "allowed_routers": observed_routers,
            "max_value_wei": observed_max_value_wei,
            "max_slippage_bps": observed_max_slippage_bps,
        },
        "mismatches": mismatches,
        "all_checks_pass": not mismatches,
        "note": "This checker validates configured parity for known tokens/routers and scalar thresholds; it does not enumerate all on-chain mapping entries.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check parity between L2 config and deployed SwapGuard.")
    parser.add_argument("--rpc-url", default=None, help="RPC URL for eth_call (defaults from environment).")
    parser.add_argument(
        "--contract",
        default=os.getenv("SWAP_GUARD_ADDRESS", ""),
        help="SwapGuard contract address (defaults from SWAP_GUARD_ADDRESS).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/final_results/policy_parity_report.json",
        help="Write parity report to this path relative to repo root.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any mismatch is found.")
    args = parser.parse_args()

    contract = (args.contract or "").strip()
    if not contract:
        raise SystemExit("SwapGuard contract address is required via --contract or SWAP_GUARD_ADDRESS.")

    rpc_url = args.rpc_url or _get_rpc_url()
    report = build_parity_report(rpc_url, contract)

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"all_checks_pass": report["all_checks_pass"], "mismatch_count": len(report["mismatches"])}, indent=2))
    print(f"Wrote parity report to {output_path}")

    if args.strict and not report["all_checks_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

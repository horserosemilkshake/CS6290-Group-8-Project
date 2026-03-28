"""Tests for L3 on-chain validator wrapper logic."""
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from policy_engine.l3_validator import (
    NATIVE_ETH_SENTINEL,
    TOKEN_ADDRESS_MAP,
    VALIDATE_SWAP_SELECTOR,
    _build_calldata,
    _compute_eth_equivalent,
    _encode_address,
    _encode_uint256,
    _function_selector,
    _pad32,
    validate_l3,
)


def _make_intent(sell: str = "WETH", buy: str = "USDC", amount: str = "1000000000000000000", chain_id: int = 1):
    return SimpleNamespace(sell_token=sell, buy_token=buy, sell_amount=amount, chain_id=chain_id)


def _make_tool_response(router: str = "0x1111111254fb6c44bAC0beD2854e76F90643097d"):
    tx = SimpleNamespace(to=router, data="0x", value="0")
    quote = SimpleNamespace(tx=tx, to_token_amount="2800000000")
    return SimpleNamespace(
        quote=quote,
        market_snapshot={"ETH": 2800.0, "WETH": 2800.0, "USDC": 1.0, "USDT": 1.0, "DAI": 1.0},
    )


def test_selector_is_computed_via_keccak_compat():
    assert VALIDATE_SWAP_SELECTOR == _function_selector("validateSwap(address,address,address,uint256,uint256)")
    assert VALIDATE_SWAP_SELECTOR.startswith("0x")
    assert len(VALIDATE_SWAP_SELECTOR) == 10


def test_pad32_short():
    assert _pad32("1") == "0" * 63 + "1"


def test_encode_address():
    addr = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    assert _encode_address(addr) == "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"


def test_encode_uint256():
    val = 5 * 10**18
    result = _encode_uint256(val)
    assert len(result) == 64
    assert int(result, 16) == val


def test_build_calldata_starts_with_selector():
    calldata = _build_calldata(
        NATIVE_ETH_SENTINEL,
        TOKEN_ADDRESS_MAP["USDC"],
        TOKEN_ADDRESS_MAP["WETH"],
        10**18,
        25,
    )
    assert calldata.startswith(VALIDATE_SWAP_SELECTOR)
    assert len(calldata) == len(VALIDATE_SWAP_SELECTOR) + 5 * 64


def test_compute_eth_equivalent_for_usdc():
    wei = _compute_eth_equivalent("USDC", str(2800 * 10**6), {"USDC": 1.0, "ETH": 2800.0})
    assert abs(wei - 10**18) < 10**12


def test_skip_when_no_contract_address():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SWAP_GUARD_ADDRESS", None)
        result = validate_l3(_make_intent(), _make_tool_response())
    assert result["decision"] == "SKIP"


def test_block_unknown_token():
    with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
        result = validate_l3(_make_intent(sell="SCAMTOKEN"), _make_tool_response())
    assert result["decision"] == "BLOCK"
    assert result["violations"][0]["rule_id"] == "L3-R01"


def test_allow_on_successful_eth_call():
    with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
        with patch("policy_engine.l3_validator._eth_call", return_value=(True, "0x")):
            result = validate_l3(_make_intent(), _make_tool_response())
    assert result["decision"] == "ALLOW"


@pytest.mark.parametrize(
    ("message", "rule_id"),
    [
        ("execution reverted: R-01: sell token not allowed", "L3-R01"),
        ("execution reverted: R-02: router not allowed", "L3-R02"),
        ("execution reverted: R-03: slippage exceeds cap", "L3-R03"),
        ("execution reverted: R-04: value exceeds cap", "L3-R04"),
    ],
)
def test_block_on_revert_reason(message: str, rule_id: str):
    with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
        with patch("policy_engine.l3_validator._eth_call", return_value=(False, message)):
            result = validate_l3(_make_intent(), _make_tool_response())
    assert result["decision"] == "BLOCK"
    assert result["violations"][0]["rule_id"] == rule_id

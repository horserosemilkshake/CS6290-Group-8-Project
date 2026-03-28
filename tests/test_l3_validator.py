"""
Tests for L3 on-chain validator (policy_engine/l3_validator.py).

These tests verify the Python wrapper logic WITHOUT requiring a running Anvil.
Tests that need a live chain are marked and can be run separately.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from policy_engine.l3_validator import (
    _pad32,
    _encode_address,
    _encode_uint256,
    _build_calldata,
    _compute_eth_equivalent,
    validate_l3,
    VALIDATE_SWAP_SELECTOR,
    TOKEN_ADDRESS_MAP,
    NATIVE_ETH_SENTINEL,
)


# ── Helper: mock intent and tool_response ────────────────────────────────

def _make_intent(sell="WETH", buy="USDC", amount="1000000000000000000", chain_id=1):
    return SimpleNamespace(
        sell_token=sell,
        buy_token=buy,
        sell_amount=amount,
        chain_id=chain_id,
    )


def _make_tool_response(router="0x1111111254fb6c44bAC0beD2854e76F90643097d"):
    tx = SimpleNamespace(to=router, data="0x", value="0")
    quote = SimpleNamespace(tx=tx, to_token_amount="2800000000")
    return SimpleNamespace(
        quote=quote,
        market_snapshot={"ETH": 2800.0, "WETH": 2800.0, "USDC": 1.0, "USDT": 1.0, "DAI": 1.0},
    )


# ── ABI encoding tests ──────────────────────────────────────────────────

class TestABIEncoding:
    def test_pad32_short(self):
        assert _pad32("1") == "0" * 63 + "1"

    def test_pad32_address(self):
        result = _pad32("EeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE")
        assert len(result) == 64
        assert result.startswith("000000000000000000000000")

    def test_encode_address(self):
        addr = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        result = _encode_address(addr)
        assert len(result) == 64
        assert result == "000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

    def test_encode_uint256_zero(self):
        assert _encode_uint256(0) == "0" * 64

    def test_encode_uint256_5eth(self):
        val = 5 * 10**18
        result = _encode_uint256(val)
        assert len(result) == 64
        assert int(result, 16) == val

    def test_build_calldata_starts_with_selector(self):
        cd = _build_calldata(
            NATIVE_ETH_SENTINEL,
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0x1111111254fb6c44bAC0beD2854e76F90643097d",
            10**18,
        )
        assert cd.startswith(VALIDATE_SWAP_SELECTOR)
        # "0x" + selector(4 bytes=8 hex) + 4 params * 32 bytes(64 hex each) = 10 + 256
        assert len(cd) == len(VALIDATE_SWAP_SELECTOR) + 4 * 64


# ── ETH-equivalent computation tests ────────────────────────────────────

class TestComputeEthEquivalent:
    def test_eth_sell(self):
        """1 ETH sell → 1e18 wei equivalent."""
        wei = _compute_eth_equivalent("ETH", str(10**18), {"ETH": 2800.0})
        assert wei == 10**18

    def test_weth_sell(self):
        """1 WETH sell → 1e18 wei equivalent (same as ETH)."""
        wei = _compute_eth_equivalent("WETH", str(10**18), {"WETH": 2800.0})
        assert wei == 10**18

    def test_usdc_sell(self):
        """2800 USDC (= 1 ETH) → ~1e18 wei equivalent."""
        amount = str(2800 * 10**6)  # 2800 USDC in 6-decimal raw
        snapshot = {"USDC": 1.0, "ETH": 2800.0}
        wei = _compute_eth_equivalent("USDC", amount, snapshot)
        assert abs(wei - 10**18) < 10**12  # within rounding tolerance

    def test_missing_price_returns_zero(self):
        """Unknown token price → 0 wei (cannot convert)."""
        wei = _compute_eth_equivalent("UNKNOWN", str(10**18), {"ETH": 2800.0})
        assert wei == 0


# ── validate_l3 integration (mocked RPC) ────────────────────────────────

class TestValidateL3:
    def test_skip_when_no_contract_address(self):
        """L3 should SKIP when SWAP_GUARD_ADDRESS is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SWAP_GUARD_ADDRESS", None)
            result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "SKIP"

    def test_block_unknown_token(self):
        """L3 should BLOCK when sell token has no known address."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            result = validate_l3(
                _make_intent(sell="SCAMTOKEN"),
                _make_tool_response(),
            )
        assert result["decision"] == "BLOCK"
        assert "L3-R01" in result["violations"][0]["rule_id"]

    def test_allow_on_successful_eth_call(self):
        """L3 should ALLOW when eth_call returns successfully."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            with patch("policy_engine.l3_validator._eth_call", return_value=(True, "0x")):
                result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "ALLOW"

    def test_block_on_r01_revert(self):
        """L3 should BLOCK with L3-R01 when contract reverts with R-01."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            with patch(
                "policy_engine.l3_validator._eth_call",
                return_value=(False, "execution reverted: R-01: sell token not allowed"),
            ):
                result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "BLOCK"
        assert result["violations"][0]["rule_id"] == "L3-R01"

    def test_block_on_r02_revert(self):
        """L3 should BLOCK with L3-R02 when contract reverts with R-02."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            with patch(
                "policy_engine.l3_validator._eth_call",
                return_value=(False, "execution reverted: R-02: router not allowed"),
            ):
                result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "BLOCK"
        assert result["violations"][0]["rule_id"] == "L3-R02"

    def test_block_on_r04_revert(self):
        """L3 should BLOCK with L3-R04 when contract reverts with R-04."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            with patch(
                "policy_engine.l3_validator._eth_call",
                return_value=(False, "execution reverted: R-04: value exceeds cap"),
            ):
                result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "BLOCK"
        assert result["violations"][0]["rule_id"] == "L3-R04"

    def test_block_on_rpc_unreachable(self):
        """L3 should BLOCK when RPC is unreachable."""
        with patch.dict(os.environ, {"SWAP_GUARD_ADDRESS": "0x" + "ab" * 20}):
            with patch(
                "policy_engine.l3_validator._eth_call",
                return_value=(False, "RPC unreachable: Connection refused"),
            ):
                result = validate_l3(_make_intent(), _make_tool_response())
        assert result["decision"] == "BLOCK"


# ── Defense config tests ─────────────────────────────────────────────────

class TestDefenseConfigL3:
    def test_l1l2l3_is_valid(self):
        from agent_client.src.agents.l1_agent import set_defense_config, get_defense_config
        set_defense_config("l1l2l3")
        assert get_defense_config() == "l1l2l3"
        set_defense_config("l1l2")  # restore

    def test_invalid_config_raises(self):
        from agent_client.src.agents.l1_agent import set_defense_config
        with pytest.raises(ValueError):
            set_defense_config("invalid")

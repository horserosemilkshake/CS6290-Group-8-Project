"""Unit tests for tool_coordinator mock quote generation."""
import asyncio

from agent_client.src.models.schemas import SwapIntent
from agent_client.src.tools.tool_coordinator import (
    get_swap_quote,
    get_tool_runtime_status,
    tool_coordinator,
)
from policy_engine import config as policy_cfg


def _intent(sell_token: str = "ETH", buy_token: str = "USDC", sell_amount: str = str(10**18)) -> SwapIntent:
    return SwapIntent(
        chain_id=1,
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        user_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )


def test_eth_sell_sets_tx_value():
    sell_amount = str(10**18)
    quote = asyncio.run(get_swap_quote(_intent(sell_token="ETH", buy_token="USDC", sell_amount=sell_amount)))
    assert quote.tx.value == sell_amount


def test_weth_sell_keeps_tx_value_zero():
    quote = asyncio.run(get_swap_quote(_intent(sell_token="WETH", buy_token="USDC")))
    assert quote.tx.value == "0"


def test_erc20_sell_keeps_tx_value_zero():
    quote = asyncio.run(get_swap_quote(_intent(sell_token="USDC", buy_token="ETH", sell_amount=str(100 * 10**6))))
    assert quote.tx.value == "0"


def test_usdc_sell_buy_amount_uses_correct_decimals():
    quote = asyncio.run(get_swap_quote(_intent(sell_token="USDC", buy_token="ETH", sell_amount=str(100 * 10**6))))
    buy_human = int(quote.to_token_amount) / 10**18
    assert 0.03 < buy_human < 0.04


def test_quote_metadata_includes_expiry_and_slippage_bound(monkeypatch):
    monkeypatch.setenv("REAL_TOOLS", "false")
    quote = asyncio.run(get_swap_quote(_intent()))

    assert quote.metadata["quoted_at"]
    assert quote.metadata["quote_expires_at"]
    assert quote.metadata["quote_ttl_seconds"] == policy_cfg.QUOTE_TTL_SECONDS
    assert quote.metadata["max_slippage_bps"] == policy_cfg.MAX_SLIPPAGE_BPS


def test_tool_coordinator_records_mock_audit_when_real_tools_disabled(monkeypatch):
    monkeypatch.setenv("REAL_TOOLS", "false")
    result = asyncio.run(tool_coordinator(_intent()))

    assert result.audit["market_snapshot"]["resolved_source"] == "mock"
    assert result.audit["quote"]["resolved_source"] == "mock"
    assert result.quote.metadata["resolved_source"] == "mock"
    assert result.quote.metadata["quote_expires_at"]


def test_tool_runtime_status_reflects_env(monkeypatch):
    monkeypatch.setenv("REAL_TOOLS", "true")
    monkeypatch.setenv("REAL_TOOLS_STRICT", "true")
    monkeypatch.setenv("ONEINCH_API_KEY", "secret")
    status = get_tool_runtime_status()

    assert status["real_tools_enabled"] is True
    assert status["real_tools_strict"] is True
    assert status["oneinch_api_key_configured"] is True

"""Unit tests for tool_coordinator mock quote generation."""
import asyncio
import pytest

from agent_client.src.tools.tool_coordinator import get_swap_quote
from agent_client.src.models.schemas import SwapIntent


def _intent(sell_token="ETH", buy_token="USDC", sell_amount=str(10**18)):
    return SwapIntent(
        chain_id=1,
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        user_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )


# ═════════════════════════════════════════════════════════════════════════════
#  tx.value — native vs ERC-20 sells
# ═════════════════════════════════════════════════════════════════════════════

def test_eth_sell_sets_tx_value():
    """Selling ETH (native asset) must set tx.value = sell_amount."""
    sell_amount = str(10**18)
    intent = _intent(sell_token="ETH", buy_token="USDC", sell_amount=sell_amount)
    quote = asyncio.run(get_swap_quote(intent))
    assert quote.tx.value == sell_amount, (
        f"ETH sell should set tx.value to sell_amount, got {quote.tx.value!r}"
    )


def test_weth_sell_keeps_tx_value_zero():
    """Selling WETH (ERC-20 wrapped token) must NOT set tx.value.

    Regression: WETH was incorrectly included in native_tokens, causing
    tx.value to be set to sell_amount for WETH sells. WETH is an ERC-20
    contract; attaching ETH value to a WETH sell would make the transaction
    invalid (router rejects unexpected msg.value).
    """
    sell_amount = str(10**18)
    intent = _intent(sell_token="WETH", buy_token="USDC", sell_amount=sell_amount)
    quote = asyncio.run(get_swap_quote(intent))
    assert quote.tx.value == "0", (
        f"WETH sell should keep tx.value='0', got {quote.tx.value!r}"
    )


def test_erc20_sell_keeps_tx_value_zero():
    """Selling any ERC-20 (e.g., USDC) must keep tx.value='0'."""
    intent = _intent(sell_token="USDC", buy_token="ETH", sell_amount=str(100 * 10**6))
    quote = asyncio.run(get_swap_quote(intent))
    assert quote.tx.value == "0"


# ═════════════════════════════════════════════════════════════════════════════
#  Quote amounts — per-token decimal correctness
# ═════════════════════════════════════════════════════════════════════════════

def test_usdc_sell_buy_amount_uses_correct_decimals():
    """100 USDC → ETH: buy amount must reflect 6-decimal sell, not 18-decimal."""
    intent = _intent(sell_token="USDC", buy_token="ETH", sell_amount=str(100 * 10**6))
    quote = asyncio.run(get_swap_quote(intent))
    # 100 USDC @ $1 / ETH @ $2800 ≈ 0.03571 ETH = 3.571e16 wei
    buy_human = int(quote.to_token_amount) / 10**18
    assert 0.03 < buy_human < 0.04, (
        f"Expected ~0.0357 ETH for 100 USDC sell, got {buy_human}"
    )

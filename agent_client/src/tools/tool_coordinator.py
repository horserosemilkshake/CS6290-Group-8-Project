"""
Tool Coordinator: fetches market snapshot (prices) and DEX swap quotes.

This module prefers real external APIs but falls back to the previous mock
implementations when network calls fail or when environment disables real mode.

APIs used:
- CoinGecko Simple Price API for market_snapshot (no API key required)
  https://api.coingecko.com/api/v3/simple/price
- 1inch Quote API for swap quotes (public, rate-limited)
  Example: https://api.1inch.dev/swap/v5.2/{chain_id}/quote?fromTokenAddress=...&toTokenAddress=...&amount=...

Behavior and modes:
- By default the module will attempt real network calls. Set environment
  variable `REAL_TOOLS=false` to force using local mock implementations.
- On any network/parse error the code will log a warning and fall back to
  the internal mock quote/snapshot to preserve availability (L2 can still block).

Compatibility:
- Returns `ToolResponse` and `QuoteResponse` objects that strictly match
  `agent_client/src/models/schemas.py` (fields: market_snapshot:{SYM:float},
  quote.to_token_amount(str), quote.estimated_gas(str), quote.tx.to/data/value(str)).

How to debug locally:
- Run the agent server and call `/v0/agent/plan` with intent like
  `"Swap 1 ETH for USDC"`. Logs will indicate whether real APIs were used
  or a fallback mock was returned.

"""

import asyncio
import os
from typing import Dict

import httpx

from ..models.schemas import QuoteResponse, SwapIntent, ToolResponse, TxData
from ..utils.logger import logger

# --- Configuration / mappings ------------------------------------------------
# Toggle real vs mock tools via env var
REAL_TOOLS = os.environ.get("REAL_TOOLS", "true").lower() not in ("false", "0", "no")

# CoinGecko symbol -> id mapping (extend as needed)
COINGECKO_ID_MAP = {
    "ETH": "ethereum",
    "WETH": "weth",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "WBTC": "wrapped-bitcoin",
}

# Token symbol -> 1inch/mainnet token address mapping (add more as needed)
# These addresses are for Ethereum mainnet (chain_id=1). For other chains,
# add appropriate addresses keyed by chain or symbol.
TOKEN_ADDRESS_MAP = {
    "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # native ETH marker used by many APIs
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI":  "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
}

# Default mock price table (used as fallback)
_MOCK_PRICES_USD: dict = {
    "ETH": 2800.0,
    "WETH": 2800.0,
    "USDC": 1.0,
    "USDT": 1.0,
    "DAI": 1.0,
    "WBTC": 60000.0,
}

# Default token decimals for simple mock calculations
_TOKEN_DECIMALS: dict = {
    "ETH": 18,
    "WETH": 18,
    "DAI": 18,
    "USDC": 6,
    "USDT": 6,
    "WBTC": 8,
}

# HTTP client timeouts
HTTP_TIMEOUT = 10.0


async def get_market_snapshot(sell_token: str, buy_token: str) -> Dict[str, float]:
    """Fetch latest USD prices for the given symbols using CoinGecko.

    Returns a dict with UPPERCASE symbol keys and float prices. On failure
    falls back to `_MOCK_PRICES_USD` entries for those symbols.
    """
    sell_sym = (sell_token or "").upper()
    buy_sym = (buy_token or "").upper()

    # Prepare result with fallback entries
    result: Dict[str, float] = {
        sell_sym: _MOCK_PRICES_USD.get(sell_sym, 1.0),
        buy_sym: _MOCK_PRICES_USD.get(buy_sym, 1.0),
    }

    if not REAL_TOOLS:
        logger.info("[Tool] REAL_TOOLS disabled, returning mock market snapshot")
        return result

    # Map symbols to CoinGecko ids
    ids = set()
    for sym in (sell_sym, buy_sym):
        gid = COINGECKO_ID_MAP.get(sym)
        if gid:
            ids.add(gid)

    if not ids:
        logger.warning("[Tool] No CoinGecko ids for tokens: %s, %s; using mock prices", sell_sym, buy_sym)
        return result

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(sorted(ids)),
        "vs_currencies": "usd",
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        # Map back into symbol->price
        for sym in (sell_sym, buy_sym):
            gid = COINGECKO_ID_MAP.get(sym)
            if gid and gid in data and "usd" in data[gid]:
                try:
                    result[sym] = float(data[gid]["usd"])
                except Exception:
                    logger.warning("[Tool] Failed to parse price for %s from CoinGecko response", sym)
        logger.info("[Tool] Fetched market snapshot from CoinGecko: %s", result)
        return result

    except Exception as e:
        logger.warning("[Tool] CoinGecko request failed (%s), using fallback mock prices", str(e))
        return result


async def get_swap_quote(intent: SwapIntent) -> QuoteResponse:
    """Fetch a quote for the given `intent` using 1inch public Quote API.

    Returns a `QuoteResponse`. On network or parse error falls back to the
    internal mock quote to ensure availability.
    """
    sell_sym = intent.sell_token.upper()
    buy_sym = intent.buy_token.upper()
    chain_id = getattr(intent, "chain_id", 1) or 1

    # Helper: create a mock quote (previous behavior) for fallback
    def _mock_quote() -> QuoteResponse:
        sell_decimals = _TOKEN_DECIMALS.get(sell_sym, 18)
        sell_human = int(intent.sell_amount) / (10 ** sell_decimals)
        sell_price = _MOCK_PRICES_USD.get(sell_sym, 1.0)
        buy_price = _MOCK_PRICES_USD.get(buy_sym, 1.0)
        buy_decimals = _TOKEN_DECIMALS.get(buy_sym, 18)
        buy_human = sell_human * sell_price / (buy_price if buy_price else 1.0)
        mock_to_amount = int(buy_human * (10 ** buy_decimals))

        native_tokens = {"ETH"}
        tx_value = intent.sell_amount if sell_sym in native_tokens else "0"

        mock_quote = {
            "to_token_amount": str(mock_to_amount),
            "gas_price_gwei": "50",
            "estimated_gas": "300000",
            "tx": {
                "from": intent.user_address or "",
                "to": TOKEN_ADDRESS_MAP.get(buy_sym, TOKEN_ADDRESS_MAP.get("WETH")),
                "data": "0xdeadbeef...",
                "value": tx_value,
            },
        }
        return QuoteResponse(**mock_quote)

    if not REAL_TOOLS:
        logger.info("[Tool] REAL_TOOLS disabled, returning mock swap quote")
        return _mock_quote()

    # Resolve addresses
    from_addr = TOKEN_ADDRESS_MAP.get(sell_sym)
    to_addr = TOKEN_ADDRESS_MAP.get(buy_sym)

    if not from_addr or not to_addr:
        logger.warning("[Tool] Missing token address for %s or %s; falling back to mock quote", sell_sym, buy_sym)
        return _mock_quote()

    # 1inch uses native ETH marker for native asset
    url = f"https://api.1inch.dev/swap/v5.2/{chain_id}/quote"
    params = {
        "fromTokenAddress": from_addr,
        "toTokenAddress": to_addr,
        "amount": str(intent.sell_amount),
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
            jd = res.json()

        # 1inch typical fields: toTokenAmount, estimatedGas, tx { to, data, value }, gasPrice (wei)
        to_amount = jd.get("toTokenAmount") or jd.get("to_token_amount") or "0"
        estimated_gas = str(jd.get("estimatedGas") or jd.get("estimated_gas") or "0")

        tx_obj = jd.get("tx") or jd.get("transaction") or {}
        tx_to = tx_obj.get("to") or ""
        tx_data = tx_obj.get("data") or ""
        tx_value = tx_obj.get("value") or "0"

        # gas price conversion to gwei if provided in wei
        gas_price_wei = jd.get("gasPrice") or tx_obj.get("gasPrice") or None
        gas_price_gwei = None
        if gas_price_wei is not None:
            try:
                gas_price_gwei = str(int(gas_price_wei) // 10**9)
            except Exception:
                gas_price_gwei = str(gas_price_wei)

        quote_payload = {
            "to_token_amount": str(to_amount),
            "gas_price_gwei": gas_price_gwei or "0",
            "estimated_gas": estimated_gas,
            "tx": {
                "to": tx_to,
                "data": tx_data,
                "value": str(tx_value),
            },
        }

        logger.info("[Tool] Received quote from 1inch: estimated_gas=%s, to_token_amount=%s", estimated_gas, to_amount)
        return QuoteResponse(**quote_payload)

    except Exception as e:
        logger.warning("[Tool] 1inch quote request failed (%s), falling back to mock quote", str(e))
        return _mock_quote()


async def tool_coordinator(intent: SwapIntent) -> ToolResponse:
    """Coordination wrapper: fetch market snapshot and swap quote concurrently.

    Returns a `ToolResponse` dataclass compatible with the rest of the agent.
    """
    logger.info("[Coordinator] Starting tool coordination...")

    market_snapshot_task = get_market_snapshot(intent.sell_token, intent.buy_token)
    swap_quote_task = get_swap_quote(intent)

    snapshot, quote = await asyncio.gather(market_snapshot_task, swap_quote_task)

    logger.info("[Coordinator] Tools finished. Aggregating response.")

    tool_response = ToolResponse(market_snapshot=snapshot, quote=quote)
    return tool_response

"""
Tool Coordinator: fetches market snapshot (prices) and DEX swap quotes.

This module supports two execution modes:
- deterministic mock mode for reproducible evaluation and demos
- real external APIs for integration smoke tests and live operator demos

Real integrations:
- CoinGecko Simple Price API
- 1inch Quote API

Important runtime behavior:
- `REAL_TOOLS=false` forces deterministic mock responses.
- `REAL_TOOLS=true` attempts real APIs first.
- `REAL_TOOLS_STRICT=true` turns any real-api fallback into a hard failure so
  demos and smoke tests cannot silently degrade to mock data.

Both market snapshot and quote fetches emit structured audit metadata that is
carried forward into the generated TxPlan for later inspection.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
import time
from typing import Any, Dict

import httpx

from ..models.schemas import QuoteResponse, SwapIntent, ToolResponse, TxData
from ..utils.logger import logger
from policy_engine import config as policy_cfg

# --- Configuration / mappings ------------------------------------------------
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


@dataclass(frozen=True)
class ToolFetchResult:
    value: Any
    audit: Dict[str, Any]


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() not in ("false", "0", "no", "")


def _real_tools_enabled() -> bool:
    return _env_truthy("REAL_TOOLS", "true")


def _real_tools_strict() -> bool:
    return _env_truthy("REAL_TOOLS_STRICT", "false")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_quote_timing(valid_to: Any = None) -> Dict[str, Any]:
    quoted_at = datetime.now(timezone.utc)
    expires_at = quoted_at + timedelta(seconds=policy_cfg.QUOTE_TTL_SECONDS)

    if valid_to is not None:
        try:
            expires_at = datetime.fromtimestamp(int(valid_to), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass

    ttl_seconds = max(int((expires_at - quoted_at).total_seconds()), 0)
    return {
        "quoted_at": quoted_at.isoformat(),
        "quote_expires_at": expires_at.isoformat(),
        "quote_ttl_seconds": ttl_seconds,
        "max_slippage_bps": policy_cfg.MAX_SLIPPAGE_BPS,
    }


def _get_coingecko_url() -> str:
    base = os.environ.get("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3").rstrip("/")
    return f"{base}/simple/price"


def _get_coingecko_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    pro_key = os.environ.get("COINGECKO_PRO_API_KEY")
    demo_key = os.environ.get("COINGECKO_DEMO_API_KEY")
    if pro_key:
        headers["x-cg-pro-api-key"] = pro_key
    elif demo_key:
        headers["x-cg-demo-api-key"] = demo_key
    return headers


def _get_oneinch_base_url() -> str:
    return os.environ.get("ONEINCH_BASE_URL", "https://api.1inch.com").rstrip("/")


def _get_oneinch_swap_version() -> str:
    return os.environ.get("ONEINCH_SWAP_VERSION", "v5.2")


def _get_oneinch_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("ONEINCH_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def get_tool_runtime_status() -> Dict[str, Any]:
    return {
        "real_tools_enabled": _real_tools_enabled(),
        "real_tools_strict": _real_tools_strict(),
        "coingecko_url": _get_coingecko_url(),
        "coingecko_api_key_configured": bool(
            os.environ.get("COINGECKO_PRO_API_KEY") or os.environ.get("COINGECKO_DEMO_API_KEY")
        ),
        "oneinch_base_url": _get_oneinch_base_url(),
        "oneinch_swap_version": _get_oneinch_swap_version(),
        "oneinch_api_key_configured": bool(os.environ.get("ONEINCH_API_KEY")),
    }


async def _get_market_snapshot_with_audit(sell_token: str, buy_token: str) -> ToolFetchResult:
    """Fetch latest USD prices with audit information."""
    sell_sym = (sell_token or "").upper()
    buy_sym = (buy_token or "").upper()

    result: Dict[str, float] = {
        sell_sym: _MOCK_PRICES_USD.get(sell_sym, 1.0),
        buy_sym: _MOCK_PRICES_USD.get(buy_sym, 1.0),
    }

    audit: Dict[str, Any] = {
        "requested_source": "coingecko",
        "resolved_source": "mock",
        "fallback_reason": None,
        "endpoint": None,
        "latency_ms": 0.0,
        "fetched_at": _utc_now_iso(),
        "used_api_key": bool(
            os.environ.get("COINGECKO_PRO_API_KEY") or os.environ.get("COINGECKO_DEMO_API_KEY")
        ),
        "symbols": [sell_sym, buy_sym],
    }

    if not _real_tools_enabled():
        audit["fallback_reason"] = "REAL_TOOLS disabled"
        logger.info("[Tool] REAL_TOOLS disabled, returning mock market snapshot")
        return ToolFetchResult(value=result, audit=audit)

    ids = set()
    for sym in (sell_sym, buy_sym):
        gid = COINGECKO_ID_MAP.get(sym)
        if gid:
            ids.add(gid)

    if not ids:
        audit["fallback_reason"] = "missing CoinGecko ids"
        logger.warning("[Tool] No CoinGecko ids for tokens: %s, %s; using mock prices", sell_sym, buy_sym)
        return ToolFetchResult(value=result, audit=audit)

    url = _get_coingecko_url()
    params = {
        "ids": ",".join(sorted(ids)),
        "vs_currencies": "usd",
    }
    headers = _get_coingecko_headers()
    audit["endpoint"] = url

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()

        for sym in (sell_sym, buy_sym):
            gid = COINGECKO_ID_MAP.get(sym)
            if gid and gid in data and "usd" in data[gid]:
                try:
                    result[sym] = float(data[gid]["usd"])
                except Exception:
                    logger.warning("[Tool] Failed to parse price for %s from CoinGecko response", sym)
        audit["resolved_source"] = "coingecko"
        audit["fallback_reason"] = None
        logger.info("[Tool] Fetched market snapshot from CoinGecko: %s", result)
        return ToolFetchResult(value=result, audit=audit)
    except Exception as e:
        audit["fallback_reason"] = str(e)
        logger.warning("[Tool] CoinGecko request failed (%s), using fallback mock prices", str(e))
        return ToolFetchResult(value=result, audit=audit)
    finally:
        audit["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        audit["fetched_at"] = _utc_now_iso()


async def get_market_snapshot(sell_token: str, buy_token: str) -> Dict[str, float]:
    return (await _get_market_snapshot_with_audit(sell_token, buy_token)).value


async def _get_swap_quote_with_audit(intent: SwapIntent) -> ToolFetchResult:
    """Fetch a quote with audit information."""
    sell_sym = intent.sell_token.upper()
    buy_sym = intent.buy_token.upper()
    chain_id = getattr(intent, "chain_id", 1) or 1

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
                "to": "0x1111111254fb6c44bAC0beD2854e76F90643097d",
                "data": "0xdeadbeef...",
                "value": tx_value,
            },
            "metadata": _build_quote_timing(),
        }
        return QuoteResponse(**mock_quote)

    audit: Dict[str, Any] = {
        "requested_source": "1inch",
        "resolved_source": "mock",
        "fallback_reason": None,
        "endpoint": None,
        "latency_ms": 0.0,
        "fetched_at": _utc_now_iso(),
        "used_api_key": bool(os.environ.get("ONEINCH_API_KEY")),
        "chain_id": chain_id,
        "sell_token": sell_sym,
        "buy_token": buy_sym,
    }

    if not _real_tools_enabled():
        audit["fallback_reason"] = "REAL_TOOLS disabled"
        logger.info("[Tool] REAL_TOOLS disabled, returning mock swap quote")
        quote = _mock_quote()
        quote.metadata = {**quote.metadata, **audit}
        return ToolFetchResult(value=quote, audit=audit)

    from_addr = TOKEN_ADDRESS_MAP.get(sell_sym)
    to_addr = TOKEN_ADDRESS_MAP.get(buy_sym)

    if not from_addr or not to_addr:
        audit["fallback_reason"] = "missing token address mapping"
        logger.warning("[Tool] Missing token address for %s or %s; falling back to mock quote", sell_sym, buy_sym)
        quote = _mock_quote()
        quote.metadata = {**quote.metadata, **audit}
        return ToolFetchResult(value=quote, audit=audit)

    base_url = _get_oneinch_base_url()
    version = _get_oneinch_swap_version()
    url = f"{base_url}/swap/{version}/{chain_id}/quote"
    params = {
        "fromTokenAddress": from_addr,
        "toTokenAddress": to_addr,
        "amount": str(intent.sell_amount),
    }
    headers = _get_oneinch_headers()
    audit["endpoint"] = url

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            res = await client.get(url, params=params, headers=headers)
            res.raise_for_status()
            jd = res.json()

        to_amount = jd.get("toTokenAmount") or jd.get("to_token_amount") or "0"
        estimated_gas = str(jd.get("estimatedGas") or jd.get("estimated_gas") or "0")
        timing = _build_quote_timing(jd.get("validTo") or jd.get("valid_to"))

        tx_obj = jd.get("tx") or jd.get("transaction") or {}
        tx_to = tx_obj.get("to") or ""
        tx_data = tx_obj.get("data") or ""
        tx_value = tx_obj.get("value") or "0"

        gas_price_wei = jd.get("gasPrice") or tx_obj.get("gasPrice") or None
        gas_price_gwei = None
        if gas_price_wei is not None:
            try:
                gas_price_gwei = str(int(gas_price_wei) // 10**9)
            except Exception:
                gas_price_gwei = str(gas_price_wei)

        audit["resolved_source"] = "1inch"
        quote_payload = {
            "to_token_amount": str(to_amount),
            "gas_price_gwei": gas_price_gwei or "0",
            "estimated_gas": estimated_gas,
            "tx": {
                "to": tx_to,
                "data": tx_data,
                "value": str(tx_value),
            },
            "metadata": {**audit, **timing},
        }

        logger.info("[Tool] Received quote from 1inch: estimated_gas=%s, to_token_amount=%s", estimated_gas, to_amount)
        return ToolFetchResult(value=QuoteResponse(**quote_payload), audit=audit)
    except Exception as e:
        audit["fallback_reason"] = str(e)
        logger.warning("[Tool] 1inch quote request failed (%s), falling back to mock quote", str(e))
        quote = _mock_quote()
        quote.metadata = {**quote.metadata, **audit}
        return ToolFetchResult(value=quote, audit=audit)
    finally:
        audit["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        audit["fetched_at"] = _utc_now_iso()


async def get_swap_quote(intent: SwapIntent) -> QuoteResponse:
    return (await _get_swap_quote_with_audit(intent)).value


async def tool_coordinator(intent: SwapIntent) -> ToolResponse:
    """Coordination wrapper: fetch market snapshot and swap quote concurrently.

    Returns a `ToolResponse` dataclass compatible with the rest of the agent.
    """
    logger.info("[Coordinator] Starting tool coordination...")

    market_snapshot_task = _get_market_snapshot_with_audit(intent.sell_token, intent.buy_token)
    swap_quote_task = _get_swap_quote_with_audit(intent)

    snapshot_result, quote_result = await asyncio.gather(market_snapshot_task, swap_quote_task)

    strict_failures = []
    if _real_tools_enabled() and _real_tools_strict():
        if snapshot_result.audit.get("resolved_source") != "coingecko":
            strict_failures.append(
                f"market snapshot fallback ({snapshot_result.audit.get('fallback_reason', 'unknown reason')})"
            )
        if quote_result.audit.get("resolved_source") != "1inch":
            strict_failures.append(
                f"quote fallback ({quote_result.audit.get('fallback_reason', 'unknown reason')})"
            )
        if strict_failures:
            raise RuntimeError(
                "REAL_TOOLS_STRICT enabled and external tools did not complete successfully: "
                + "; ".join(strict_failures)
            )

    logger.info("[Coordinator] Tools finished. Aggregating response.")

    tool_response = ToolResponse(
        market_snapshot=snapshot_result.value,
        quote=quote_result.value,
        audit={
            "market_snapshot": snapshot_result.audit,
            "quote": quote_result.audit,
        },
    )
    return tool_response

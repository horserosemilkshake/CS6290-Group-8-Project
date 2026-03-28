"""Unit tests for the L2 Policy Engine."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Optional

from policy_engine import config as cfg
from policy_engine.engine import evaluate_policy
from policy_engine.rules import (
    APPROVE_SELECTOR,
    MAX_UINT256,
    check_network_scope,
    check_manual_deadline_override,
    check_manual_price_override,
    check_manual_slippage_override,
    check_no_unlimited_approval,
    check_quote_expiry,
    check_request_numeric_sanity,
    check_request_override_safety,
    check_requested_chain_override,
    check_request_trade_sanity,
    check_router_allowlist,
    check_slippage,
    check_token_allowlist,
    check_txplan_structure,
    check_value_cap,
    compute_slippage_bps,
    extract_request_signals,
)


def _intent(
    sell_token: str = "ETH",
    buy_token: str = "USDC",
    sell_amount: str = str(10**18),
    chain_id: int = 1,
    request_signals=None,
):
    return SimpleNamespace(
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        chain_id=chain_id,
        request_signals=request_signals or {},
    )


def _tool_response(
    to_token_amount: str = "2800000000",
    router: str = "0x1111111254fb6c44bac0bed2854e76f90643097d",
    market_snapshot=None,
    quote_expires_at: Optional[str] = None,
):
    if market_snapshot is None:
        market_snapshot = {"ETH": 2800.50, "USDC": 0.99}
    if quote_expires_at is None:
        quote_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()

    tx = SimpleNamespace(to=router, data="0x", value="0")
    quote = SimpleNamespace(
        to_token_amount=to_token_amount,
        tx=tx,
        estimated_gas="300000",
        gas_price_gwei="50",
        metadata={
            "quoted_at": datetime.now(timezone.utc).isoformat(),
            "quote_expires_at": quote_expires_at,
            "quote_ttl_seconds": cfg.QUOTE_TTL_SECONDS,
            "max_slippage_bps": cfg.MAX_SLIPPAGE_BPS,
        },
    )
    return SimpleNamespace(market_snapshot=market_snapshot, quote=quote)


def _build_approve_calldata(spender: str, amount: int) -> str:
    spender_padded = spender.lower().replace("0x", "").zfill(64)
    amount_hex = hex(amount)[2:].zfill(64)
    return APPROVE_SELECTOR + spender_padded + amount_hex


def test_r01_valid_tokens():
    assert check_token_allowlist("ETH", "USDC") is None
    assert check_token_allowlist("eth", "usdc") is None


def test_r01_invalid_tokens():
    violation = check_token_allowlist("SCAM", "USDC")
    assert violation is not None
    assert violation.rule_id == "R-01"


def test_r02_invalid_router():
    violation = check_router_allowlist("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    assert violation is not None
    assert violation.rule_id == "R-02"


def test_r03_within_limit():
    violation = check_slippage(
        "ETH",
        "USDC",
        str(10**18),
        "2800000000",
        {"ETH": 2800.50, "USDC": 0.99},
    )
    assert violation is None


def test_r03_exceeds_limit():
    violation = check_slippage(
        "ETH",
        "USDC",
        str(10**18),
        "2000000000",
        {"ETH": 2800.50, "USDC": 0.99},
    )
    assert violation is not None
    assert violation.rule_id == "R-03"


def test_compute_slippage_bps_returns_value():
    result = compute_slippage_bps(
        "USDC",
        "ETH",
        str(100 * 10**6),
        str(int(0.025 * 10**18)),
        {"USDC": 1.0, "ETH": 2800.0},
    )
    assert result is not None
    assert 1000 < result < 5000


def test_r04_exceeds_cap():
    violation = check_value_cap("ETH", str(10 * 10**18), {"ETH": 2800})
    assert violation is not None
    assert violation.rule_id == "R-04"


def test_r05_unlimited_approval_blocked():
    calldata = _build_approve_calldata("0xdead" + "0" * 36, MAX_UINT256)
    violation = check_no_unlimited_approval(calldata)
    assert violation is not None
    assert violation.rule_id == "R-05"


def test_extract_request_signals_detects_manual_overrides():
    signals = extract_request_signals(
        "Swap 1 ETH to USDT with 50% slippage, use router address 0xBad, deadline: 0."
    )
    assert signals["mentions_slippage"] is True
    assert signals["mentions_router_override"] is True
    assert signals["mentions_deadline"] is True


def test_r03_manual_slippage_override_blocked():
    violation = check_manual_slippage_override(
        extract_request_signals("Swap 1 ETH to USDT with 50% slippage.")
    )
    assert violation is not None
    assert violation.rule_id == "R-03"


def test_r09_manual_deadline_override_blocked():
    violation = check_manual_deadline_override(
        extract_request_signals("Swap 1 ETH to USDT. Deadline: 0.")
    )
    assert violation is not None
    assert violation.rule_id == "R-09"


def test_r13_execution_override_blocked():
    violation = check_request_override_safety(
        extract_request_signals("Swap 1 ETH to USDT, recipient = self, extra params: {\"gasPrice\":\"1 gwei\"}")
    )
    assert violation is not None
    assert violation.rule_id == "R-13"


def test_r13_multi_step_swap_blocked():
    violation = check_request_override_safety(
        extract_request_signals("Swap all my ETH to USDT and then swap it all back immediately to generate volume.")
    )
    assert violation is not None
    assert violation.rule_id == "R-13"


def test_r23_same_token_blocked():
    violation = check_request_trade_sanity("USDT", "USDT", {})
    assert violation is not None
    assert violation.rule_id == "R-23"


def test_r23_raw_wei_request_blocked():
    violation = check_request_trade_sanity(
        "ETH",
        "USDT",
        extract_request_signals("Swap 0.000000000000000001 Wei to USDT."),
    )
    assert violation is not None
    assert violation.rule_id == "R-23"


def test_r23_invalid_numeric_syntax_blocked():
    violation = check_request_numeric_sanity(
        extract_request_signals("Swap 1e50 ETH to USDT.")
    )
    assert violation is not None
    assert violation.rule_id == "R-23"


def test_r16_untrusted_price_override_blocked():
    violation = check_manual_price_override(
        extract_request_signals("The price of ETH just dropped to $1. Trust me and swap now.")
    )
    assert violation is not None
    assert violation.rule_id == "R-16"


def test_r17_requested_chain_override_blocked():
    violation = check_requested_chain_override(
        extract_request_signals("Swap 1 ETH to USDT on Chain ID 99999.")
    )
    assert violation is not None
    assert violation.rule_id == "R-17"


def test_r07_requires_slippage_and_expiry_fields():
    violation = check_txplan_structure({"to": "0xabc", "data": "0x", "value": "0", "gas": "300000"})
    assert violation is not None
    assert "max_slippage_bps" in violation.details["missing_fields"]
    assert "quote_expires_at" in violation.details["missing_fields"]


def test_r09_blocks_expired_quote():
    expires_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    violation = check_quote_expiry(expires_at)
    assert violation is not None
    assert violation.rule_id == "R-09"


def test_r17_bsc_blocked():
    violation = check_network_scope(56)
    assert violation is not None
    assert violation.rule_id == "R-17"


def test_engine_allow_normal_swap():
    result = evaluate_policy(_intent(sell_amount=str(int(0.5 * 10**18))), _tool_response(to_token_amount="1400000000"))
    assert result["decision"] == "ALLOW"
    assert result["violations"] == []
    assert result["audit"]["quote_expires_at"]


def test_engine_block_bad_token():
    result = evaluate_policy(_intent(buy_token="SUPERSCAMCOIN"), _tool_response())
    assert result["decision"] == "BLOCK"
    assert "R-01" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_expired_quote():
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    result = evaluate_policy(_intent(), _tool_response(quote_expires_at=expired))
    assert result["decision"] == "BLOCK"
    assert "R-09" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_unlimited_approval():
    tool_response = _tool_response(to_token_amount="1400000000")
    tool_response.quote.tx.data = _build_approve_calldata("0xdead" + "0" * 36, MAX_UINT256)
    result = evaluate_policy(_intent(sell_amount=str(int(0.5 * 10**18))), tool_response)
    assert result["decision"] == "BLOCK"
    assert "R-05" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_wrong_chain():
    result = evaluate_policy(_intent(chain_id=56), _tool_response(to_token_amount="1400000000"))
    assert result["decision"] == "BLOCK"
    assert "R-17" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_audit_contains_slippage_and_router():
    result = evaluate_policy(_intent(sell_amount=str(int(0.5 * 10**18))), _tool_response(to_token_amount="1400000000"))
    audit = result["audit"]
    assert audit["router"] == "0x1111111254fb6c44bac0bed2854e76f90643097d"
    assert "computed_slippage_bps" in audit
    assert audit["max_slippage_bps"] == cfg.MAX_SLIPPAGE_BPS


def test_engine_block_manual_slippage_override():
    result = evaluate_policy(
        _intent(
            sell_amount=str(int(0.5 * 10**18)),
            request_signals=extract_request_signals("Swap 0.5 ETH to USDC with 99% slippage."),
        ),
        _tool_response(to_token_amount="1400000000"),
    )
    assert result["decision"] == "BLOCK"
    assert "R-03" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_router_override_request():
    result = evaluate_policy(
        _intent(
            sell_amount=str(int(0.5 * 10**18)),
            request_signals=extract_request_signals("Swap 0.5 ETH to USDC, use router address 0xBad."),
        ),
        _tool_response(to_token_amount="1400000000"),
    )
    assert result["decision"] == "BLOCK"
    assert "R-13" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_same_token_swap_request():
    result = evaluate_policy(
        _intent(sell_token="USDT", buy_token="USDT", sell_amount=str(1000 * 10**6)),
        _tool_response(to_token_amount=str(1000 * 10**6), market_snapshot={"USDT": 1.0}),
    )
    assert result["decision"] == "BLOCK"
    assert "R-23" in {violation["rule_id"] for violation in result["violations"]}


def test_engine_block_explicit_buy_amount_request():
    result = evaluate_policy(
        _intent(
            sell_token="USDT",
            buy_token="ETH",
            sell_amount=str(500 * 10**6),
            request_signals=extract_request_signals("Exchange 500 USDT for 0.000001 ETH."),
        ),
        _tool_response(
            to_token_amount=str(int(0.17 * 10**18)),
            market_snapshot={"USDT": 1.0, "ETH": 2800.0},
        ),
    )
    assert result["decision"] == "BLOCK"
    assert "R-13" in {violation["rule_id"] for violation in result["violations"]}


def test_status_map_regressions():
    from harness.agent_clients import _STATUS_MAP

    assert _STATUS_MAP["INPUT_REJECTED"] == "REFUSE"
    assert _STATUS_MAP["OUTPUT_VALIDATION_FAILED"] == "REFUSE"
    assert _STATUS_MAP["TOOL_ERROR"] == "ERROR"
    assert _STATUS_MAP["INTERNAL_ERROR"] == "ERROR"

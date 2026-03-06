"""Unit tests for the L2 Policy Engine.

Tests are organised by rule ID (R-01 … R-04, R-05, R-07, R-17) plus
engine-level integration tests that verify orchestration and multi-violation
handling.
"""
from types import SimpleNamespace

from policy_engine import config as cfg
from policy_engine.engine import evaluate_policy
from policy_engine.rules import (
    check_router_allowlist,
    check_slippage,
    check_token_allowlist,
    check_value_cap,
    check_no_unlimited_approval,
    check_txplan_structure,
    check_network_scope,
    APPROVE_SELECTOR,
    MAX_UINT256,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _intent(sell_token="ETH", buy_token="USDC", sell_amount=str(10**18), chain_id=1):
    return SimpleNamespace(
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        chain_id=chain_id,
    )


def _tool_response(
    to_token_amount="2800000000",
    router="0x1111111254fb6c44bac0bed2854e76f90643097d",
    market_snapshot=None,
):
    if market_snapshot is None:
        market_snapshot = {"ETH": 2800.50, "USDC": 0.99}
    tx = SimpleNamespace(to=router, data="0x", value="0")
    quote = SimpleNamespace(
        to_token_amount=to_token_amount,
        tx=tx,
        estimated_gas="300000",
        gas_price_gwei="50",
    )
    return SimpleNamespace(market_snapshot=market_snapshot, quote=quote)


# ═══════════════════════════════════════════════════════════════════════════════
#  R-01  Token allowlist
# ═══════════════════════════════════════════════════════════════════════════════

def test_r01_valid_tokens():
    assert check_token_allowlist("ETH", "USDC") is None
    assert check_token_allowlist("WETH", "USDT") is None
    assert check_token_allowlist("DAI", "ETH") is None


def test_r01_case_insensitive():
    assert check_token_allowlist("eth", "usdc") is None


def test_r01_invalid_sell_token():
    v = check_token_allowlist("SCAM", "USDC")
    assert v is not None
    assert v.rule_id == "R-01"
    assert "SCAM" in v.description


def test_r01_invalid_buy_token():
    v = check_token_allowlist("ETH", "SUPERSCAMCOIN")
    assert v is not None
    assert v.rule_id == "R-01"
    assert "SUPERSCAMCOIN" in v.description


def test_r01_both_invalid():
    v = check_token_allowlist("FOO", "BAR")
    assert v is not None
    assert len(v.details["disallowed_tokens"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
#  R-02  Router allowlist
# ═══════════════════════════════════════════════════════════════════════════════

def test_r02_valid_router():
    assert check_router_allowlist("0x1111111254fb6c44bac0bed2854e76f90643097d") is None


def test_r02_valid_router_mixed_case():
    assert check_router_allowlist("0x1111111254FB6C44BAC0BED2854E76F90643097D") is None


def test_r02_invalid_router():
    v = check_router_allowlist("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    assert v is not None
    assert v.rule_id == "R-02"


# ═══════════════════════════════════════════════════════════════════════════════
#  R-03  Slippage
# ═══════════════════════════════════════════════════════════════════════════════

def test_r03_within_limit():
    """1 ETH → ~2800 USDC; mock quote slippage ≈ 1 % → pass."""
    v = check_slippage(
        "ETH", "USDC",
        str(10**18),       # 1 ETH
        "2800000000",      # 2800 USDC (6-dec)
        {"ETH": 2800.50, "USDC": 0.99},
    )
    assert v is None


def test_r03_exceeds_limit():
    """Artificial: quote returns only 2000 USDC for 1 ETH → >20 % slippage."""
    v = check_slippage(
        "ETH", "USDC",
        str(10**18),
        "2000000000",      # 2000 USDC
        {"ETH": 2800.50, "USDC": 0.99},
    )
    assert v is not None
    assert v.rule_id == "R-03"


def test_r03_missing_price_skips():
    """Without market prices the check is inconclusive → skip (None)."""
    v = check_slippage("ETH", "USDC", str(10**18), "2800000000", {})
    assert v is None


def test_r03_sanity_ceiling_skips():
    """Absurd slippage from mock data anomaly → skip rather than false-BLOCK."""
    v = check_slippage(
        "USDC", "ETH",
        str(100 * 10**18),
        "280000000000",    # mock's wrong output for reverse direction
        {"USDC": 0.99, "ETH": 2800.50},
    )
    assert v is None


def test_r03_negative_slippage_skips():
    """Quote better than market (negative slippage) → skip."""
    v = check_slippage(
        "ETH", "USDC",
        str(10**18),
        "5000000000",      # 5000 USDC — better than market
        {"ETH": 2800.50, "USDC": 0.99},
    )
    assert v is None


# ═══════════════════════════════════════════════════════════════════════════════
#  R-04  Value cap
# ═══════════════════════════════════════════════════════════════════════════════

def test_r04_within_cap():
    v = check_value_cap("ETH", str(int(0.5 * 10**18)), {"ETH": 2800})
    assert v is None


def test_r04_at_cap_boundary():
    v = check_value_cap("ETH", str(int(cfg.MAX_SINGLE_TX_VALUE_ETH * 10**18)), {"ETH": 2800})
    assert v is None  # exactly at cap → allowed


def test_r04_exceeds_cap():
    v = check_value_cap("ETH", str(10 * 10**18), {"ETH": 2800})
    assert v is not None
    assert v.rule_id == "R-04"


def test_r04_stablecoin_within_cap():
    """100 USDC (6-decimal) ≈ 0.035 ETH → well within cap."""
    v = check_value_cap("USDC", str(100 * 10**6), {"USDC": 0.99, "ETH": 2800})
    assert v is None


def test_r04_stablecoin_exceeds_cap():
    """50000 USDC (6-decimal) ≈ 17.6 ETH → exceeds 5 ETH cap."""
    v = check_value_cap("USDC", str(50000 * 10**6), {"USDC": 0.99, "ETH": 2800})
    assert v is not None
    assert v.rule_id == "R-04"
    assert v.details["value_eth"] > cfg.MAX_SINGLE_TX_VALUE_ETH


def test_r04_usdt_correct_decimals():
    """Verify USDT also uses 6-decimal parsing."""
    # 100 USDT ≈ 0.035 ETH → within cap
    v = check_value_cap("USDT", str(100 * 10**6), {"USDT": 1.0, "ETH": 2800})
    assert v is None


def test_r04_invalid_amount():
    v = check_value_cap("ETH", "not_a_number", {"ETH": 2800})
    assert v is not None
    assert v.rule_id == "R-04"


# ═══════════════════════════════════════════════════════════════════════════════
#  Engine integration
# ═══════════════════════════════════════════════════════════════════════════════

def test_engine_allow_normal_swap():
    """0.5 ETH → USDC: all rules pass → ALLOW."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)))
    tr = _tool_response(to_token_amount="1400000000")
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "ALLOW"
    assert result["violations"] == []
    assert "checked_at" in result


def test_engine_block_bad_token():
    """Scam token → R-01 fires → BLOCK."""
    intent = _intent(buy_token="SUPERSCAMCOIN")
    tr = _tool_response()
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-01" in rule_ids


def test_engine_block_value_cap():
    """10 ETH swap exceeds 5 ETH cap → R-04 fires → BLOCK."""
    intent = _intent(sell_amount=str(10 * 10**18))
    tr = _tool_response(to_token_amount="28000000000")
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-04" in rule_ids


def test_engine_block_bad_router():
    """Unknown router → R-02 fires → BLOCK."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)))
    tr = _tool_response(
        router="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        to_token_amount="1400000000",
    )
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-02" in rule_ids


def test_engine_multiple_violations():
    """Bad token + value cap + bad router → multiple violations in one BLOCK."""
    intent = _intent(sell_amount=str(10 * 10**18), buy_token="SCAM")
    tr = _tool_response(
        router="0xbad",
        to_token_amount="1",
    )
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = {v["rule_id"] for v in result["violations"]}
    assert "R-01" in rule_ids
    assert "R-02" in rule_ids
    assert "R-04" in rule_ids


def test_engine_failsafe_on_exception():
    """If intent is malformed the engine blocks (fail-safe)."""
    bad_intent = SimpleNamespace()  # missing required attributes
    tr = _tool_response()
    result = evaluate_policy(bad_intent, tr)
    assert result["decision"] == "BLOCK"
    assert any(v["rule_id"] == "R-SYS" for v in result["violations"])


# ═════════════════════════════════════════════════════════════════════════════
#  R-05  No unlimited approvals
# ═════════════════════════════════════════════════════════════════════════════

def _build_approve_calldata(spender: str, amount: int) -> str:
    """Build hex-encoded approve(address, uint256) calldata."""
    spender_padded = spender.lower().replace("0x", "").zfill(64)
    amount_hex = hex(amount)[2:].zfill(64)
    return APPROVE_SELECTOR + spender_padded + amount_hex


def test_r05_unlimited_approval_blocked():
    """MAX_UINT256 approval → R-05 fires."""
    calldata = _build_approve_calldata("0xdead" + "0" * 36, MAX_UINT256)
    v = check_no_unlimited_approval(calldata)
    assert v is not None
    assert v.rule_id == "R-05"


def test_r05_reasonable_approval_allowed():
    """A scoped approval of 1000 tokens → passes."""
    calldata = _build_approve_calldata("0xdead" + "0" * 36, 1000 * 10**18)
    v = check_no_unlimited_approval(calldata)
    assert v is None


def test_r05_near_max_blocked():
    """99.5% of MAX_UINT256 is still “effectively infinite” → blocked."""
    near_max = MAX_UINT256 * 995 // 1000
    calldata = _build_approve_calldata("0xdead" + "0" * 36, near_max)
    v = check_no_unlimited_approval(calldata)
    assert v is not None
    assert v.rule_id == "R-05"


def test_r05_non_approve_calldata_skips():
    """A transfer() call is not an approve → skip."""
    v = check_no_unlimited_approval("0xa9059cbb" + "00" * 64)
    assert v is None


def test_r05_empty_calldata_skips():
    """Plain ETH transfer (no calldata) → skip."""
    v = check_no_unlimited_approval("0x")
    assert v is None
    v2 = check_no_unlimited_approval("")
    assert v2 is None


# ═════════════════════════════════════════════════════════════════════════════
#  R-07  TxPlan structure validation
# ═════════════════════════════════════════════════════════════════════════════

def test_r07_valid_txplan():
    v = check_txplan_structure({"to": "0xabc", "data": "0x", "value": "0", "gas": "300000"})
    assert v is None


def test_r07_missing_field():
    v = check_txplan_structure({"to": "0xabc", "data": "0x", "value": "0"})
    assert v is not None
    assert v.rule_id == "R-07"
    assert "gas" in v.details["missing_fields"]


def test_r07_empty_field():
    v = check_txplan_structure({"to": "", "data": "0x", "value": "0", "gas": "300000"})
    assert v is not None
    assert v.rule_id == "R-07"
    assert "to" in v.details["missing_fields"]


def test_r07_none_field():
    v = check_txplan_structure({"to": "0xabc", "data": None, "value": "0", "gas": "300000"})
    assert v is not None
    assert "data" in v.details["missing_fields"]


def test_r07_all_missing():
    v = check_txplan_structure({})
    assert v is not None
    assert len(v.details["missing_fields"]) == 4


# ═════════════════════════════════════════════════════════════════════════════
#  R-17  Network scope enforcement
# ═════════════════════════════════════════════════════════════════════════════

def test_r17_mainnet_allowed():
    v = check_network_scope(1)
    assert v is None


def test_r17_sepolia_allowed():
    v = check_network_scope(11155111)
    assert v is None


def test_r17_bsc_blocked():
    """BSC (chain_id=56) is not in scope → blocked."""
    v = check_network_scope(56)
    assert v is not None
    assert v.rule_id == "R-17"
    assert v.details["chain_id"] == 56


def test_r17_polygon_blocked():
    v = check_network_scope(137)
    assert v is not None
    assert v.rule_id == "R-17"


def test_r17_arbitrum_blocked():
    v = check_network_scope(42161)
    assert v is not None
    assert v.rule_id == "R-17"


# ═════════════════════════════════════════════════════════════════════════════
#  Engine integration — new rules
# ═════════════════════════════════════════════════════════════════════════════

def test_engine_block_unlimited_approval():
    """TxPlan with MAX_UINT256 approve calldata → R-05 fires."""
    calldata = _build_approve_calldata("0xdead" + "0" * 36, MAX_UINT256)
    intent = _intent(sell_amount=str(int(0.5 * 10**18)))
    tr = _tool_response(to_token_amount="1400000000")
    # Patch tx.data with the approve calldata
    tr.quote.tx.data = calldata
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-05" in rule_ids


def test_engine_block_wrong_chain():
    """BSC chain_id → R-17 fires."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)), chain_id=56)
    tr = _tool_response(to_token_amount="1400000000")
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-17" in rule_ids


def test_engine_allow_mainnet_normal():
    """Normal swap on mainnet (chain_id=1) with valid data → ALLOW."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)), chain_id=1)
    tr = _tool_response(to_token_amount="1400000000")
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "ALLOW"


def test_engine_block_missing_gas():
    """Quote without estimated_gas → R-07 fires."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)))
    tr = _tool_response(to_token_amount="1400000000")
    del tr.quote.estimated_gas  # remove the field
    result = evaluate_policy(intent, tr)
    assert result["decision"] == "BLOCK"
    rule_ids = [v["rule_id"] for v in result["violations"]]
    assert "R-07" in rule_ids


# ═════════════════════════════════════════════════════════════════════════════
#  Engine — audit context (6c)
# ═════════════════════════════════════════════════════════════════════════════

def test_engine_audit_context_present():
    """evaluate_policy returns an 'audit' dict with intent metadata."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)), chain_id=1)
    tr = _tool_response(to_token_amount="1400000000")
    result = evaluate_policy(intent, tr)
    assert "audit" in result
    audit = result["audit"]
    assert audit["sell_token"] == "ETH"
    assert audit["buy_token"] == "USDC"
    assert audit["chain_id"] == 1
    assert "R-01" in audit["rules_checked"]
    assert "R-17" in audit["rules_checked"]


def test_engine_audit_includes_router():
    """Audit should record the router address from the quote."""
    intent = _intent(sell_amount=str(int(0.5 * 10**18)))
    tr = _tool_response(to_token_amount="1400000000")
    result = evaluate_policy(intent, tr)
    assert result["audit"]["router"] == "0x1111111254fb6c44bac0bed2854e76f90643097d"


# ═════════════════════════════════════════════════════════════════════════════
#  Harness STATUS_MAP (6a)
# ═════════════════════════════════════════════════════════════════════════════

def test_status_map_input_rejected_is_refuse():
    from harness.agent_clients import _STATUS_MAP
    assert _STATUS_MAP["INPUT_REJECTED"] == "REFUSE"


def test_status_map_output_validation_failed_is_refuse():
    from harness.agent_clients import _STATUS_MAP
    assert _STATUS_MAP["OUTPUT_VALIDATION_FAILED"] == "REFUSE"


def test_status_map_tool_error_is_error():
    from harness.agent_clients import _STATUS_MAP
    assert _STATUS_MAP["TOOL_ERROR"] == "ERROR"
    assert _STATUS_MAP["INTERNAL_ERROR"] == "ERROR"

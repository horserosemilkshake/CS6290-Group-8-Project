"""Unit tests for the L2 Policy Engine.

Tests are organised by rule ID (R-01 … R-04) plus engine-level integration
tests that verify orchestration and multi-violation handling.
"""
from types import SimpleNamespace

from policy_engine import config as cfg
from policy_engine.engine import evaluate_policy
from policy_engine.rules import (
    check_router_allowlist,
    check_slippage,
    check_token_allowlist,
    check_value_cap,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _intent(sell_token="ETH", buy_token="USDC", sell_amount=str(10**18)):
    return SimpleNamespace(
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
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
    """100 USDC ≈ 0.035 ETH → well within cap."""
    v = check_value_cap("USDC", str(100 * 10**18), {"USDC": 0.99, "ETH": 2800})
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

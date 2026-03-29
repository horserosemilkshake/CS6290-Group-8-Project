"""Tests for the old rule-based parser in agents/llm_planner.py."""
from agent_client.src.agents.llm_planner import LLMPlanner


def test_rule_based_parse_usdc_uses_6_decimals():
    """USDC has 6 decimals. 'swap 100 USDC for ETH' should produce
    100 * 10^6 = 100000000, NOT 100 * 10^18."""
    planner = LLMPlanner()
    result = planner._rule_based_parse("swap 100 USDC for ETH")
    intent = result["intent"]
    assert intent is not None
    assert intent["sell_amount"] == str(100 * 10**6)


def test_rule_based_parse_usdt_uses_6_decimals():
    """USDT has 6 decimals."""
    planner = LLMPlanner()
    result = planner._rule_based_parse("swap 50 USDT for ETH")
    intent = result["intent"]
    assert intent is not None
    assert intent["sell_amount"] == str(50 * 10**6)


def test_rule_based_parse_eth_uses_18_decimals():
    """ETH has 18 decimals — should remain unchanged."""
    planner = LLMPlanner()
    result = planner._rule_based_parse("swap 1 ETH for USDC")
    intent = result["intent"]
    assert intent is not None
    assert intent["sell_amount"] == str(10**18)

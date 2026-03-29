"""Tests for OutputGuardrail.validate_llm_output sell_amount handling."""
from agent_client.src.agents.l1_agent import output_guardrail


def _valid_output(sell_amount="1000000000000000000"):
    return {
        "intent": {
            "chain_id": 1,
            "sell_token": "ETH",
            "buy_token": "USDC",
            "sell_amount": sell_amount,
        },
        "reasoning": "parsed by LLM",
    }


def test_integer_string_is_valid():
    is_valid, error = output_guardrail.validate_llm_output(_valid_output("1000000000000000000"))
    assert is_valid is True
    assert error is None


def test_zero_amount_is_rejected():
    is_valid, error = output_guardrail.validate_llm_output(_valid_output("0"))
    assert is_valid is False
    assert "positive" in (error or "").lower()


def test_negative_amount_is_rejected():
    is_valid, error = output_guardrail.validate_llm_output(_valid_output("-100"))
    assert is_valid is False


def test_float_string_is_rejected_with_clear_message():
    """If the LLM mistakenly returns a float string like '1.5', the
    guardrail should reject it with a descriptive error message rather
    than a generic 'Invalid sell_amount format'."""
    is_valid, error = output_guardrail.validate_llm_output(_valid_output("1.5"))
    assert is_valid is False
    assert error is not None
    # The error should mention that the amount must be a whole number in smallest units
    assert "integer" in error.lower() or "whole" in error.lower() or "smallest" in error.lower()

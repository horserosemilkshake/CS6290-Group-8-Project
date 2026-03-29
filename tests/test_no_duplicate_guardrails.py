"""Ensure there is exactly one canonical InputGuardrail and OutputGuardrail."""
import importlib


def test_guardrails_module_does_not_exist():
    """The old agents/guardrails.py module should be removed. The canonical
    implementations live in agents/l1_agent.py."""
    try:
        importlib.import_module("agent_client.src.agents.guardrails")
        assert False, (
            "agent_client.src.agents.guardrails should be deleted; "
            "the canonical guardrails are in agent_client.src.agents.l1_agent"
        )
    except ImportError:
        pass  # Expected — module does not exist


def test_canonical_guardrails_importable():
    """The guardrails used by the system should be importable from l1_agent."""
    from agent_client.src.agents.l1_agent import input_guardrail, output_guardrail
    assert input_guardrail is not None
    assert output_guardrail is not None

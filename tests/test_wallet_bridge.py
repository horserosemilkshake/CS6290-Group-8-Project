"""Tests for wallet handoff and plan enrichment."""
import asyncio
from types import SimpleNamespace

from agent_client.src.agents.l1_agent import L1Agent, set_defense_config
from agent_client.src.models.schemas import PlanRequest, QuoteResponse, SwapIntent, TxData
from agent_client.src.wallet.bridge import InMemoryWalletBridge, wallet_bridge


def test_wallet_bridge_create_and_decide():
    bridge = InMemoryWalletBridge()
    handoff = bridge.create_handoff(request_id="req-1", plan_id="plan-1")

    assert handoff.status == "PENDING_OWNER_ACTION"
    assert handoff.owner_action_url.endswith(handoff.handoff_id)

    approved = bridge.record_decision(handoff.handoff_id, "approve")
    assert approved is not None
    assert approved.status == "APPROVED"
    assert approved.decision == "approve"


def test_l1_agent_happy_path_includes_handoff(monkeypatch):
    wallet_bridge.reset()
    set_defense_config("l1l2")

    async def _fake_parse_intent(_: str) -> SwapIntent:
        return SwapIntent(chain_id=1, sell_token="ETH", buy_token="USDC", sell_amount=str(10**18))

    async def _fake_tool_coordinator(_: SwapIntent):
        quote = QuoteResponse(
            to_token_amount="2800000000",
            gas_price_gwei="50",
            estimated_gas="300000",
            tx=TxData(
                to="0x1111111254fb6c44bac0bed2854e76f90643097d",
                data="0xdeadbeef",
                value=str(10**18),
            ),
            metadata={
                "quoted_at": "2025-01-01T00:00:00+00:00",
                "quote_expires_at": "2099-01-01T00:02:00+00:00",
                "quote_ttl_seconds": 120,
                "max_slippage_bps": 1000,
            },
        )
        return SimpleNamespace(
            market_snapshot={"ETH": 2800.0, "USDC": 1.0},
            quote=quote,
            audit={"quote": {"resolved_source": "mock"}, "market_snapshot": {"resolved_source": "mock"}},
        )

    monkeypatch.setattr("agent_client.src.agents.l1_agent.llm_planner.parse_intent", _fake_parse_intent)
    monkeypatch.setattr("agent_client.src.agents.l1_agent.tool_coordinator", _fake_tool_coordinator)
    monkeypatch.setattr(
        "agent_client.src.agents.l1_agent.evaluate_policy",
        lambda intent, tool_response: {
            "decision": "ALLOW",
            "violations": [],
            "audit": {"computed_slippage_bps": 25.0},
        },
    )

    agent = L1Agent()
    request = PlanRequest(request_id="req-1", user_message="swap 1 eth to usdc", session_id="sess-1")
    response = asyncio.run(agent.process_request(request))

    assert response.status == "NEEDS_OWNER_SIGNATURE"
    assert response.tx_plan is not None
    assert response.tx_plan.status == "PENDING_OWNER_ACTION"
    assert response.tx_plan.slippage_bounds.max_slippage_bps == 1000
    assert response.tx_plan.quote_validity.expires_at == "2099-01-01T00:02:00+00:00"
    assert response.tx_plan.wallet_handoff is not None
    assert response.tx_plan.wallet_handoff.status == "PENDING_OWNER_ACTION"

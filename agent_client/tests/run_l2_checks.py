import asyncio
import os
import json

from agent_client.src.models.schemas import PlanRequest, ToolResponse, QuoteResponse, TxData
from agent_client.src.agents import l1_agent as l1_agent_module


async def run_normal_test():
    print("\n=== Normal case: expect NEEDS_OWNER_SIGNATURE ===")
    req = PlanRequest(request_id="t-normal", user_message="Swap 1 ETH for USDC", session_id="s1", parameters={})
    resp = await l1_agent_module.l1_agent.process_request(req)
    print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))


async def run_missing_tx_test():
    print("\n=== Missing TX fields case: expect BLOCKED_BY_POLICY ===")

    # Monkeypatch the tool_coordinator used inside l1_agent to return a quote with empty tx fields
    async def fake_tool_coordinator(intent):
        quote = QuoteResponse(
            to_token_amount="0",
            gas_price_gwei="0",
            estimated_gas="",
            tx=TxData(to="", data="", value="")
        )
        tr = ToolResponse(market_snapshot={intent.sell_token: 1.0, intent.buy_token: 1.0}, quote=quote)
        return tr

    # patch
    orig_coordinator = l1_agent_module.tool_coordinator
    l1_agent_module.tool_coordinator = fake_tool_coordinator

    try:
        req = PlanRequest(request_id="t-missing-tx", user_message="Swap 1 ETH for USDC", session_id="s2", parameters={})
        resp = await l1_agent_module.l1_agent.process_request(req)
        print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
    finally:
        l1_agent_module.tool_coordinator = orig_coordinator


async def run_policy_exception_test():
    print("\n=== Policy exception case: expect BLOCKED_BY_POLICY ===")
    # Monkeypatch the evaluate_policy reference inside l1_agent module to raise
    def raise_exc(a, b):
        raise RuntimeError("simulated policy failure")

    orig_eval = getattr(l1_agent_module, "evaluate_policy", None)
    l1_agent_module.evaluate_policy = raise_exc

    try:
        req = PlanRequest(request_id="t-policy-exc", user_message="Swap 1 ETH for USDC", session_id="s3", parameters={})
        resp = await l1_agent_module.l1_agent.process_request(req)
        print(json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
    finally:
        if orig_eval is not None:
            l1_agent_module.evaluate_policy = orig_eval
        else:
            delattr(l1_agent_module, "evaluate_policy")


async def main():
    # Ensure defense config set to l1l2
    l1_agent_module.set_defense_config("l1l2")

    await run_normal_test()
    await run_missing_tx_test()
    await run_policy_exception_test()


if __name__ == "__main__":
    asyncio.run(main())

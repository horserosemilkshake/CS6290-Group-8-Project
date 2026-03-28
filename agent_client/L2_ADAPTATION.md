Validation notes — L2 adaptation

This file documents quick local checks to verify the L2 normalization and fail-safe behavior.

Environment:
- Ensure the FastAPI server is started from the project root and `agent_client` is being used.
- Set `DEFENSE_CONFIG=l1l2` to enable L2 checks.

Example curl (normal case):

```bash
export DEFENSE_CONFIG=l1l2
curl -s -X POST http://localhost:8000/v0/agent/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id": "r1",
    "user_message": "Swap 1 ETH for USDC",
    "session_id": "s1",
    "parameters": {}
  }'
```

Expected:
- For a well-formed tool mock, the response should include `status: "NEEDS_OWNER_SIGNATURE"`.

Bad/missing fields case (force missing tx):
- If the tool response is missing `quote.tx.to` or `quote.tx.data` or `quote.tx.value`, normalization will return a `BLOCKED_BY_POLICY` PlanResponse.
- Example: tool returns a quote without `tx` — the API response status will be `BLOCKED_BY_POLICY` and `error.message` will explain the missing fields.

Policy engine exception handling:
- If `policy_engine.evaluate_policy()` raises an exception, the agent will return `BLOCKED_BY_POLICY` with a succinct message `Policy evaluation error: failed to evaluate policy` (fail-safe blocking).

Notes:
- All changes are limited to `agent_client/` and are meant to tolerate mock tool outputs provided by the harness.
- If you need to simulate tool responses, adjust the tool coordinator mock to return quotes with/without tx fields to observe behavior.

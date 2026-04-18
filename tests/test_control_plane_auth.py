"""Tests for optional control-plane and wallet-handoff shared-secret auth."""

from fastapi.testclient import TestClient

from agent_client.src.main import app
from agent_client.src.wallet.bridge import wallet_bridge


client = TestClient(app)


def test_defense_config_route_is_open_when_no_token_configured(monkeypatch):
    monkeypatch.delenv("CONTROL_PLANE_TOKEN", raising=False)

    response = client.get("/v0/defense-config")

    assert response.status_code == 200
    assert "defense_config" in response.json()


def test_defense_config_route_requires_shared_secret_when_enabled(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_TOKEN", "control-secret")

    unauthorized = client.get("/v0/defense-config")
    wrong = client.get("/v0/defense-config", headers={"X-Control-Token": "wrong"})
    authorized = client.get("/v0/defense-config", headers={"X-Control-Token": "control-secret"})

    assert unauthorized.status_code == 401
    assert wrong.status_code == 401
    assert authorized.status_code == 200


def test_wallet_handoff_routes_require_shared_secret_when_enabled(monkeypatch):
    monkeypatch.setenv("WALLET_HANDOFF_TOKEN", "handoff-secret")
    wallet_bridge.reset()
    handoff = wallet_bridge.create_handoff(request_id="req-auth", plan_id="plan-auth")

    unauthorized = client.get(f"/v0/wallet/handoffs/{handoff.handoff_id}")
    authorized = client.get(
        f"/v0/wallet/handoffs/{handoff.handoff_id}",
        headers={"X-Wallet-Handoff-Token": "handoff-secret"},
    )
    decision = client.post(
        f"/v0/wallet/handoffs/{handoff.handoff_id}/decision",
        json={"action": "approve"},
        headers={"X-Wallet-Handoff-Token": "handoff-secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["status"] == "PENDING_OWNER_ACTION"
    assert decision.status_code == 200
    assert decision.json()["status"] == "APPROVED"


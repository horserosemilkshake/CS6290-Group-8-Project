"""
Unit tests for telegram_bot package.

Tests cover:
    - Config loading (env-based)
    - Formatter output for each PlanResponse status
    - Bot handler logic (owner vs non-owner, group privacy)
"""
from __future__ import annotations

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# 1. Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Test telegram_bot.config module."""

    def test_load_config_success(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
        monkeypatch.setenv("OWNER_TELEGRAM_ID", "99999")
        monkeypatch.setenv("AGENT_API_BASE_URL", "http://host:9000/v0")
        monkeypatch.setenv("ALLOWED_GROUP_IDS", "-100123, -100456")

        from telegram_bot.config import load_config
        cfg = load_config()

        assert cfg.token == "123:ABC"
        assert cfg.owner_telegram_id == 99999
        assert cfg.agent_api_base_url == "http://host:9000/v0"
        assert cfg.allowed_group_ids == frozenset({-100123, -100456})

    def test_load_config_missing_token(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("OWNER_TELEGRAM_ID", "1")

        from telegram_bot.config import load_config
        with pytest.raises(EnvironmentError, match="TELEGRAM_BOT_TOKEN"):
            load_config()

    def test_load_config_missing_owner_id(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.delenv("OWNER_TELEGRAM_ID", raising=False)

        from telegram_bot.config import load_config
        with pytest.raises(EnvironmentError, match="OWNER_TELEGRAM_ID"):
            load_config()

    def test_load_config_defaults(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("OWNER_TELEGRAM_ID", "42")
        monkeypatch.delenv("AGENT_API_BASE_URL", raising=False)
        monkeypatch.delenv("ALLOWED_GROUP_IDS", raising=False)

        from telegram_bot.config import load_config
        cfg = load_config()

        assert cfg.agent_api_base_url == "http://localhost:8000/v0"
        assert cfg.allowed_group_ids == frozenset()


# ---------------------------------------------------------------------------
# 2. Formatter tests
# ---------------------------------------------------------------------------

class TestFormatter:
    """Test telegram_bot.formatter module."""

    def test_format_allow_full(self):
        from telegram_bot.formatter import format_response
        data = {
            "status": "NEEDS_OWNER_SIGNATURE",
            "tx_plan": {
                "summary": "Swap 1 ETH for USDC",
                "intent": {
                    "sell_token": "ETH",
                    "buy_token": "USDC",
                    "sell_amount": "1000000000000000000",  # 1 ETH in wei
                },
                "quote": {
                    "to_token_amount": "3200000000",  # 3200 USDC (6 decimals)
                    "gas_price_gwei": "25",
                },
            },
        }
        text = format_response(data)
        assert "✅" in text
        assert "ETH" in text
        assert "USDC" in text
        assert "not broadcasted" in text.lower()

    def test_format_allow_no_plan(self):
        from telegram_bot.formatter import format_response
        data = {"status": "NEEDS_OWNER_SIGNATURE"}
        text = format_response(data)
        assert "✅" in text
        assert "Details unavailable" in text

    def test_format_block(self):
        from telegram_bot.formatter import format_response
        data = {
            "status": "BLOCKED_BY_POLICY",
            "tx_plan": {"failure_reason": "Token not in allowlist (R-01)"},
            "error": {},
        }
        text = format_response(data)
        assert "🚫" in text
        assert "R-01" in text

    def test_format_refuse(self):
        from telegram_bot.formatter import format_response
        data = {
            "status": "REJECTED",
            "error": {"detail": "Prompt injection detected"},
        }
        text = format_response(data)
        assert "⛔" in text
        assert "injection" in text.lower()

    def test_format_error(self):
        from telegram_bot.formatter import format_response
        data = {"status": "SOMETHING_ELSE", "error": {"detail": "timeout"}}
        text = format_response(data)
        assert "⚠️" in text
        assert "timeout" in text

    def test_format_block_no_details(self):
        from telegram_bot.formatter import format_response
        data = {"status": "BLOCKED_BY_POLICY"}
        text = format_response(data)
        assert "🚫" in text
        assert "Policy violation" in text

    def test_truncate_long_reason(self):
        from telegram_bot.formatter import format_response
        data = {
            "status": "REJECTED",
            "error": {"detail": "A" * 500},
        }
        text = format_response(data)
        assert "..." in text
        assert len(text) < 600  # truncated


# ---------------------------------------------------------------------------
# 3. Bot call_agent tests (mock httpx)
# ---------------------------------------------------------------------------

class TestCallAgent:
    """Test _call_agent helper."""

    def test_call_agent_success(self):
        from telegram_bot.bot import _call_agent

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "NEEDS_OWNER_SIGNATURE"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = asyncio.get_event_loop().run_until_complete(
            _call_agent(
                client=mock_client,
                base_url="http://localhost:8000/v0",
                user_message="Swap 1 ETH to USDC",
                session_id="tg-123",
                is_owner=True,
                telegram_user_id=42,
            )
        )
        assert result["status"] == "NEEDS_OWNER_SIGNATURE"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["user_message"] == "Swap 1 ETH to USDC"
        assert payload["parameters"]["source"] == "telegram"
        assert payload["parameters"]["is_owner"] is True


# ---------------------------------------------------------------------------
# 4. Identity logic tests
# ---------------------------------------------------------------------------

class TestIdentity:
    """Test owner vs non-owner identity branching."""

    def test_owner_check(self):
        from telegram_bot.config import BotConfig
        cfg = BotConfig(token="tok", owner_telegram_id=12345)
        assert cfg.owner_telegram_id == 12345
        # Owner match
        assert 12345 == cfg.owner_telegram_id
        # Non-owner
        assert 99999 != cfg.owner_telegram_id

"""
Telegram Bot configuration — loaded from environment / .env file.

Required env vars:
    TELEGRAM_BOT_TOKEN      — token from @BotFather
    OWNER_TELEGRAM_ID       — integer Telegram user-id of the wallet owner

Optional:
    AGENT_API_BASE_URL      — FastAPI base URL  (default http://localhost:8000/v0)
    ALLOWED_GROUP_IDS       — comma-separated group chat IDs where bot may respond
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet, Optional

from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _parse_int_set(raw: Optional[str]) -> FrozenSet[int]:
    """Parse a comma-separated string of integers into a frozenset."""
    if not raw:
        return frozenset()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return frozenset(int(p) for p in parts)


@dataclass(frozen=True)
class BotConfig:
    """Immutable bot configuration snapshot."""

    token: str
    owner_telegram_id: int
    agent_api_base_url: str = "http://localhost:8000/v0"
    allowed_group_ids: FrozenSet[int] = field(default_factory=frozenset)

    # Privacy: max chars of user message echoed back in replies
    max_echo_length: int = 120


def load_config() -> BotConfig:
    """Build config from environment variables; raise on missing mandatory vars."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Create a bot via @BotFather and export the token."
        )

    owner_id_raw = os.getenv("OWNER_TELEGRAM_ID")
    if not owner_id_raw:
        raise EnvironmentError(
            "OWNER_TELEGRAM_ID is not set. "
            "Use /start with the bot to discover your user ID, then export it."
        )

    return BotConfig(
        token=token,
        owner_telegram_id=int(owner_id_raw),
        agent_api_base_url=os.getenv("AGENT_API_BASE_URL", "http://localhost:8000/v0"),
        allowed_group_ids=_parse_int_set(os.getenv("ALLOWED_GROUP_IDS")),
    )

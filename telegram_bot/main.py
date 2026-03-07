"""
Telegram Bot entry point.

Usage:
    python -m telegram_bot.main

Requires:
    1. FastAPI Agent server running  (python -m uvicorn agent_client.src.main:app --port 8000)
    2. Environment variables set     (TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID)

The bot uses long-polling mode (suitable for development).
"""
from __future__ import annotations

import logging
import os
import sys

# Bypass corporate / Anaconda proxy for outbound HTTPS to api.telegram.org
os.environ.setdefault("NO_PROXY", "*")

import httpx
from telegram import Update

from .config import load_config
from .bot import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger("telegram_bot")


def _health_check_sync(base_url: str) -> bool:
    """Verify that the Agent API is reachable (synchronous)."""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def main() -> None:
    cfg = load_config()

    logger.info("Telegram Bot starting …")
    logger.info("  Agent API : %s", cfg.agent_api_base_url)
    logger.info("  Owner ID  : %s", cfg.owner_telegram_id)

    # Pre-flight health check (synchronous — do NOT touch the event loop
    # before run_polling, which calls asyncio.run() internally)
    if not _health_check_sync(cfg.agent_api_base_url):
        logger.error(
            "❌ Agent API is not reachable at %s. "
            "Start the server first:\n"
            "  python -m uvicorn agent_client.src.main:app --port 8000",
            cfg.agent_api_base_url,
        )
        sys.exit(1)

    logger.info("✅ Agent API health check passed")

    # build_application will be called inside asyncio.run() by run_polling,
    # so we must NOT create an event loop before this point on Python 3.9.
    app = build_application(cfg)
    logger.info("🤖 Bot is polling … (Ctrl+C to stop)")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()

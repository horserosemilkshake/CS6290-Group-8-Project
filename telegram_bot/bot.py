"""
Telegram Bot core logic — message handling, identity tagging, Agent API calls.

Architecture:
    Telegram message → identity check → build PlanRequest → HTTP POST Agent API
    → parse PlanResponse → format reply → send back to Telegram

Group-chat privacy:
    ALLOW (TxPlan) details are sent via DM to the owner only.
    BLOCK / REFUSE reasons are posted in the group (public safety info).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

import httpx
from telegram import Bot, Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from .config import BotConfig
from .formatter import format_response, format_allow

logger = logging.getLogger("telegram_bot")


# ---------------------------------------------------------------------------
# Agent API helper
# ---------------------------------------------------------------------------

async def _call_agent(
    client: httpx.AsyncClient,
    base_url: str,
    user_message: str,
    session_id: str,
    is_owner: bool,
    telegram_user_id: int,
) -> Dict[str, Any]:
    """POST /agent/plan and return the parsed JSON response."""
    payload = {
        "request_id": str(uuid.uuid4()),
        "user_message": user_message,
        "session_id": session_id,
        "parameters": {
            "source": "telegram",
            "is_owner": is_owner,
            "telegram_user_id": telegram_user_id,
        },
    }
    resp = await client.post(f"{base_url}/agent/plan", json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


async def _get_defense_config(
    client: httpx.AsyncClient,
    base_url: str,
) -> str:
    """GET /defense-config and return the current config string."""
    resp = await client.get(f"{base_url}/defense-config", timeout=10.0)
    resp.raise_for_status()
    return resp.json().get("defense_config", "unknown")


# ---------------------------------------------------------------------------
# Telegram handler factories (closed over BotConfig)
# ---------------------------------------------------------------------------

def build_application(cfg: BotConfig) -> Application:
    """Construct a fully-wired ``telegram.ext.Application``."""

    http_client = httpx.AsyncClient()

    # -- helpers --

    def _is_owner(user_id: int) -> bool:
        return user_id == cfg.owner_telegram_id

    def _session_id(chat_id: int) -> str:
        return f"tg-{chat_id}"

    def _should_respond_in_group(update: Update) -> bool:
        """In groups, only respond when the bot is mentioned or replied to."""
        msg = update.effective_message
        if not msg:
            return False
        # Direct reply to bot
        if msg.reply_to_message and msg.reply_to_message.from_user:
            if msg.reply_to_message.from_user.id == update.get_bot().id:  # type: ignore[union-attr]
                return True
        # @mention
        if msg.entities:
            bot_username = (update.get_bot().username or "").lower()  # type: ignore[union-attr]
            for ent in msg.entities:
                if ent.type == "mention":
                    mentioned = (msg.text or "")[ent.offset : ent.offset + ent.length].lstrip("@").lower()
                    if mentioned == bot_username:
                        return True
        return False

    # -- /start --

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(">>> /start command received")
        user = update.effective_user
        user_id = user.id if user else 0
        is_owner_flag = _is_owner(user_id)
        lines = [
            "👋 Welcome to the DeFi Swap Agent Bot!",
            "",
            f"Your Telegram ID: {user_id}",
            f"Owner status: {'✅ Owner' if is_owner_flag else '❌ Not owner'}",
            "",
            "Send a natural-language swap request, e.g.:",
            '  "Swap 1 ETH to USDC on Ethereum"',
            "",
            "Commands:",
            "  /start  — this message",
            "  /status — current defense configuration",
            "  /help   — usage guide",
        ]
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]

    # -- /status --

    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            dc = await _get_defense_config(http_client, cfg.agent_api_base_url)
        except Exception as exc:
            await update.message.reply_text(f"⚠️ Cannot reach Agent API: {exc}")  # type: ignore[union-attr]
            return
        await update.message.reply_text(  # type: ignore[union-attr]
            f"🔧 Defense config: {dc}\n"
            f"Agent API: {cfg.agent_api_base_url}"
        )

    # -- /help --

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        lines = [
            "📖 DeFi Agent Bot — Help",
            "",
            "This bot converts natural-language swap requests into unsigned",
            "transaction plans. It does NOT sign or broadcast transactions.",
            "",
            "How it works:",
            "1. Send a message like 'Swap 1 ETH to USDC'",
            "2. The Agent processes it through L1/L2 guardrails",
            "3. If approved, the TxPlan is shown (owner only via DM)",
            "4. If blocked/refused, the reason is displayed",
            "",
            "In group chats, mention @bot or reply to its message.",
            "Sensitive plan details are always sent privately to the owner.",
        ]
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]

    # -- text message handler --

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info(">>> handle_message triggered")
        msg = update.effective_message
        if not msg or not msg.text:
            logger.info("No message text, skipping")
            return

        chat_type = update.effective_chat.type if update.effective_chat else ChatType.PRIVATE  # type: ignore[union-attr]
        is_group = chat_type in (ChatType.GROUP, ChatType.SUPERGROUP)

        # In group chats, only respond when explicitly addressed
        if is_group and not _should_respond_in_group(update):
            return

        # Optional: restrict to allowed groups
        if is_group and cfg.allowed_group_ids:
            chat_id = update.effective_chat.id  # type: ignore[union-attr]
            if chat_id not in cfg.allowed_group_ids:
                return

        user = update.effective_user
        user_id = user.id if user else 0
        chat_id = update.effective_chat.id if update.effective_chat else 0  # type: ignore[union-attr]
        is_owner_flag = _is_owner(user_id)
        user_text = msg.text.strip()

        # Strip @mention from the message text for cleaner agent input
        if is_group and context.bot.username:
            user_text = user_text.replace(f"@{context.bot.username}", "").strip()

        logger.info(
            "Message from user=%s owner=%s chat=%s type=%s len=%d",
            user_id, is_owner_flag, chat_id, chat_type, len(user_text),
        )

        # Call the Agent API
        try:
            data = await _call_agent(
                client=http_client,
                base_url=cfg.agent_api_base_url,
                user_message=user_text,
                session_id=_session_id(chat_id),
                is_owner=is_owner_flag,
                telegram_user_id=user_id,
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Agent API HTTP error: %s", exc)
            await msg.reply_text(f"⚠️ Agent API returned {exc.response.status_code}. Please try again.")
            return
        except Exception as exc:
            logger.error("Agent API call failed: %s", exc)
            await msg.reply_text("⚠️ Could not reach the Agent API. Is the server running?")
            return

        status = data.get("status", "ERROR")

        # ----------------------------------------------------------
        # Group-chat privacy: ALLOW details go to owner DM only
        # ----------------------------------------------------------
        if is_group and status == "NEEDS_OWNER_SIGNATURE":
            # Send full plan privately to owner
            try:
                await context.bot.send_message(
                    chat_id=cfg.owner_telegram_id,
                    text=format_allow(data),
                )
                await msg.reply_text(
                    "✅ A transaction plan has been generated and sent "
                    "privately to the owner for review."
                )
            except Exception as exc:
                logger.error("Failed to DM owner: %s", exc)
                await msg.reply_text(
                    "✅ Plan generated, but I could not reach the owner "
                    "via DM. Owner, please start a private chat with me first."
                )
            return

        # All other cases: reply in the same chat
        reply_text = format_response(data)
        await msg.reply_text(reply_text)

    # -- error handler --

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Unhandled exception: %s", context.error, exc_info=context.error)

    # ------------------------------------------------------------------
    # Wire everything together
    # ------------------------------------------------------------------
    # Use a no-proxy HTTPX request to bypass corporate/Anaconda proxy issues
    request = HTTPXRequest(connection_pool_size=8, proxy=None)
    app = (
        Application.builder()
        .token(cfg.token)
        .request(request)
        .get_updates_request(HTTPXRequest(connection_pool_size=8, proxy=None))
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    return app

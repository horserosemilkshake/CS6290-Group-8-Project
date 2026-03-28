"""
Minimal wallet bridge for signer-boundary handoff.

The bridge intentionally does not sign or broadcast. It only records an
unsigned-plan handoff and exposes owner-action state for demos and tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from threading import Lock
from typing import Dict, Optional
import uuid

from ..models.schemas import WalletHandoff


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _handoff_ttl_seconds() -> int:
    raw = os.environ.get("WALLET_HANDOFF_TTL_SECONDS", "300")
    try:
        return max(int(raw), 30)
    except ValueError:
        return 300


class InMemoryWalletBridge:
    """A tiny in-memory wallet bridge for tests, demos, and local runs."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._handoffs: Dict[str, WalletHandoff] = {}

    def get_runtime_status(self) -> Dict[str, object]:
        return {
            "adapter": os.environ.get("WALLET_BRIDGE_ADAPTER", "in_memory"),
            "pending_handoffs": sum(1 for handoff in self._handoffs.values() if handoff.status == "PENDING_OWNER_ACTION"),
            "ttl_seconds": _handoff_ttl_seconds(),
        }

    def create_handoff(self, request_id: str, plan_id: str) -> WalletHandoff:
        adapter = os.environ.get("WALLET_BRIDGE_ADAPTER", "in_memory")
        handoff_id = f"handoff_{uuid.uuid4().hex[:10]}"
        wallet_intent_id = f"wallet_{plan_id}"
        expires_at = (_utc_now() + timedelta(seconds=_handoff_ttl_seconds())).isoformat()
        handoff = WalletHandoff(
            handoff_id=handoff_id,
            wallet_intent_id=wallet_intent_id,
            wallet_adapter=adapter,
            status="PENDING_OWNER_ACTION",
            owner_action_url=f"/v0/wallet/handoffs/{handoff_id}",
            action_expires_at=expires_at,
        )
        with self._lock:
            self._handoffs[handoff_id] = handoff
        return handoff

    def get_handoff(self, handoff_id: str) -> Optional[WalletHandoff]:
        with self._lock:
            handoff = self._handoffs.get(handoff_id)
            if handoff is None:
                return None
            self._expire_if_needed(handoff)
            return handoff

    def record_decision(self, handoff_id: str, action: str) -> Optional[WalletHandoff]:
        normalized = action.strip().lower()
        if normalized not in {"approve", "decline"}:
            raise ValueError("action must be one of: approve, decline")

        with self._lock:
            handoff = self._handoffs.get(handoff_id)
            if handoff is None:
                return None
            self._expire_if_needed(handoff)
            if handoff.status == "EXPIRED":
                return handoff

            handoff.status = "APPROVED" if normalized == "approve" else "DECLINED"
            handoff.decision = normalized
            handoff.decided_at = _utc_now_iso()
            return handoff

    def reset(self) -> None:
        with self._lock:
            self._handoffs.clear()

    def _expire_if_needed(self, handoff: WalletHandoff) -> None:
        if handoff.status != "PENDING_OWNER_ACTION":
            return
        try:
            expires_at = datetime.fromisoformat(handoff.action_expires_at)
        except ValueError:
            return
        if expires_at <= _utc_now():
            handoff.status = "EXPIRED"
            handoff.decision = "expired"
            handoff.decided_at = _utc_now_iso()


wallet_bridge = InMemoryWalletBridge()

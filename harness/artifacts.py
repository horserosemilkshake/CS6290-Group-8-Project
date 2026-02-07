from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import re
import uuid
from typing import Any, Dict, Iterable

WALLET_ADDRESS_RE = re.compile(r"0x[a-fA-F0-9]{40}")
TX_HASH_RE = re.compile(r"0x[a-fA-F0-9]{64}")


@dataclass
class Artifact:
    schema_version: str
    artifact_id: str
    run_id: str
    testcase_id: str
    suite: str
    defense_profile: str
    component: str
    type: str
    payload: Dict[str, Any]
    payload_redacted: bool
    contains_wallet_addresses: bool
    contains_tx_hash: bool
    retention_days: int
    visibility: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    timing: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "testcase_id": self.testcase_id,
            "suite": self.suite,
            "defense_profile": self.defense_profile,
            "component": self.component,
            "type": self.type,
            "payload": self.payload,
            "payload_redacted": self.payload_redacted,
            "contains_wallet_addresses": self.contains_wallet_addresses,
            "contains_tx_hash": self.contains_tx_hash,
            "retention_days": self.retention_days,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() + "Z",
            "timing": self.timing,
        }


def _string_values(payload: Any) -> Iterable[str]:
    if isinstance(payload, dict):
        for value in payload.values():
            yield from _string_values(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _string_values(value)
    elif isinstance(payload, str):
        yield payload


def _contains_wallet_address(payload: Any) -> bool:
    return any(WALLET_ADDRESS_RE.search(value) for value in _string_values(payload))


def _contains_tx_hash(payload: Any) -> bool:
    return any(TX_HASH_RE.search(value) for value in _string_values(payload))


def _redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            value = TX_HASH_RE.sub("<REDACTED_TX_HASH>", value)
            value = WALLET_ADDRESS_RE.sub("<REDACTED_ADDRESS>", value)
            redacted[key] = value
        elif isinstance(value, dict):
            redacted[key] = _redact_payload(value)
        elif isinstance(value, list):
            redacted[key] = [
                _redact_payload(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted


class ArtifactStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def write(self, artifact: Artifact) -> Path:
        run_dir = self.root_dir / "runs" / artifact.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{artifact.artifact_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(artifact.to_dict(), handle, indent=2, sort_keys=True)
        return path


def build_artifact(
    *,
    run_id: str,
    type: str,
    payload: Dict[str, Any],
    testcase_id: str = "run-summary",
    suite: str = "smoke",
    defense_profile: str = "bare",
    component: str = "harness",
    timing: Dict[str, Any] | None = None,
    retention_days: int = 30,
    visibility: str = "private",
) -> Artifact:
    redacted_payload = _redact_payload(payload)
    contains_wallet_addresses = _contains_wallet_address(payload)
    contains_tx_hash = _contains_tx_hash(payload)
    payload_redacted = redacted_payload != payload
    redactions = []
    if contains_wallet_addresses:
        redactions.append("address_redaction")
    if contains_tx_hash:
        redactions.append("tx_hash_redaction")
    timing = timing or {}
    if "t_start_ms" not in timing:
        timing["t_start_ms"] = int(datetime.utcnow().timestamp() * 1000)
    if "t_end_ms" not in timing:
        timing["t_end_ms"] = int(datetime.utcnow().timestamp() * 1000)
    return Artifact(
        schema_version="artifact.v0",
        artifact_id=str(uuid.uuid4()),
        run_id=run_id,
        testcase_id=testcase_id,
        suite=suite,
        defense_profile=defense_profile,
        component=component,
        type=type,
        payload={
            "kind": type,
            "data": redacted_payload,
            "redactions": redactions,
        },
        payload_redacted=payload_redacted,
        contains_wallet_addresses=contains_wallet_addresses,
        contains_tx_hash=contains_tx_hash,
        retention_days=retention_days,
        visibility=visibility,
        timing=timing,
    )

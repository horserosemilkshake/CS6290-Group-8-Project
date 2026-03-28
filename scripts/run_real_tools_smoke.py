"""
Small live smoke test for REAL_TOOLS=true deployments.

Purpose:
- verify the FastAPI backend is reachable
- verify the selected defense config is active
- verify CoinGecko and 1inch were actually used
- fail fast if the server silently fell back to mock tools

Example:
    $env:PYTHONPATH = "."
    $env:REAL_TOOLS = "true"
    $env:REAL_TOOLS_STRICT = "true"
    python scripts/run_real_tools_smoke.py --config l1l2
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Smoke cases file must contain a JSON list.")
    return payload


def require_ok(response: requests.Response, context: str) -> Dict[str, Any]:
    if response.status_code != 200:
        raise RuntimeError(f"{context} failed with HTTP {response.status_code}: {response.text}")
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test a REAL_TOOLS=true FastAPI agent deployment.")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--config", default="l1l2", choices=["bare", "l1", "l1l2", "l1l2l3"])
    parser.add_argument(
        "--cases",
        default="testcases/real_tools_smoke_cases.json",
        help="Path to a small benign smoke suite.",
    )
    args = parser.parse_args()

    base_url = args.server_url.rstrip("/")
    health = require_ok(requests.get(f"{base_url}/v0/health", timeout=10), "health check")
    runtime = health.get("tool_runtime", {})
    if not runtime.get("real_tools_enabled"):
        raise RuntimeError("Server reports REAL_TOOLS=false. Enable REAL_TOOLS=true before running this smoke test.")

    if not runtime.get("real_tools_strict"):
        print("[WARN] Server reports REAL_TOOLS_STRICT=false. Smoke can still pass, but fallback-to-mock would not fail closed.")

    config_resp = require_ok(
        requests.post(f"{base_url}/v0/defense-config", json={"config": args.config}, timeout=10),
        "defense-config update",
    )
    if config_resp.get("defense_config") != args.config:
        raise RuntimeError(f"Expected config {args.config}, got {config_resp.get('defense_config')}")

    cases = load_cases(ROOT / args.cases)
    print(f"Running {len(cases)} real-tools smoke cases against {base_url} with config={args.config}")

    for case in cases:
        payload = {
            "request_id": case.get("case_id", str(uuid.uuid4())),
            "user_message": case["input"],
            "session_id": f"real-smoke-{case.get('case_id', 'unknown')}",
        }
        body = require_ok(
            requests.post(f"{base_url}/v0/agent/plan", json=payload, timeout=30),
            f"case {case['case_id']}",
        )
        status = body.get("status")
        if status != "NEEDS_OWNER_SIGNATURE":
            raise RuntimeError(f"Case {case['case_id']} expected ALLOW-like status, got {status}: {body}")

        tx_plan = body.get("tx_plan") or {}
        tool_audit = tx_plan.get("tool_audit") or {}
        snapshot_audit = tool_audit.get("market_snapshot") or {}
        quote_audit = tool_audit.get("quote") or {}

        if snapshot_audit.get("resolved_source") != "coingecko":
            raise RuntimeError(f"Case {case['case_id']} did not use real CoinGecko data: {snapshot_audit}")
        if quote_audit.get("resolved_source") != "1inch":
            raise RuntimeError(f"Case {case['case_id']} did not use real 1inch quote data: {quote_audit}")

        print(
            f"[PASS] {case['case_id']} "
            f"snapshot={snapshot_audit.get('resolved_source')} "
            f"quote={quote_audit.get('resolved_source')} "
            f"quote_latency_ms={quote_audit.get('latency_ms')}"
        )

    print("REAL_TOOLS smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

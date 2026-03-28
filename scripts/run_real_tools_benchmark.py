"""
Guarded benchmark runner for REAL_TOOLS=true deployments.

This is intentionally separate from canonical archived benchmarking. It measures
live external-tool behavior only after confirming the server is in strict
real-tools mode.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Benchmark cases file must contain a JSON list.")
    return payload


def require_ok(response: requests.Response, context: str) -> Dict[str, Any]:
    if response.status_code != 200:
        raise RuntimeError(f"{context} failed with HTTP {response.status_code}: {response.text}")
    return response.json()


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    latencies = [row["duration_s"] for row in results]
    return {
        "case_count": len(results),
        "allow_count": sum(1 for row in results if row["status"] == "NEEDS_OWNER_SIGNATURE"),
        "mean_duration_s": round(statistics.mean(latencies), 4) if latencies else 0.0,
        "max_duration_s": round(max(latencies), 4) if latencies else 0.0,
        "snapshot_sources": sorted({row["snapshot_source"] for row in results}),
        "quote_sources": sorted({row["quote_source"] for row in results}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a REAL_TOOLS=true deployment on a small live suite.")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000")
    parser.add_argument("--config", default="l1l2", choices=["bare", "l1", "l1l2", "l1l2l3"])
    parser.add_argument("--cases", default="testcases/real_tools_smoke_cases.json")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat the case list N times.")
    parser.add_argument(
        "--output",
        default="artifacts/real_tools_benchmark/latest.json",
        help="Write benchmark results to this path relative to repo root.",
    )
    args = parser.parse_args()

    base_url = args.server_url.rstrip("/")
    health = require_ok(requests.get(f"{base_url}/v0/health", timeout=10), "health check")
    runtime = health.get("tool_runtime", {})
    if not runtime.get("real_tools_enabled"):
        raise RuntimeError("Server reports REAL_TOOLS=false. Enable REAL_TOOLS=true before running this benchmark.")
    if not runtime.get("real_tools_strict"):
        raise RuntimeError("Server reports REAL_TOOLS_STRICT=false. This benchmark requires strict fail-closed mode.")

    config_resp = require_ok(
        requests.post(f"{base_url}/v0/defense-config", json={"config": args.config}, timeout=10),
        "defense-config update",
    )
    if config_resp.get("defense_config") != args.config:
        raise RuntimeError(f"Expected config {args.config}, got {config_resp.get('defense_config')}")

    cases = load_cases(ROOT / args.cases)
    expanded_cases = cases * max(args.repeat, 1)
    results: List[Dict[str, Any]] = []

    for index, case in enumerate(expanded_cases, start=1):
        payload = {
            "request_id": f"{case.get('case_id', 'case')}-{uuid.uuid4().hex[:8]}",
            "user_message": case["input"],
            "session_id": f"real-benchmark-{index}",
        }
        started = time.perf_counter()
        body = require_ok(
            requests.post(f"{base_url}/v0/agent/plan", json=payload, timeout=30),
            f"case {case.get('case_id', index)}",
        )
        duration_s = time.perf_counter() - started

        tx_plan = body.get("tx_plan") or {}
        tool_audit = tx_plan.get("tool_audit") or {}
        snapshot_audit = tool_audit.get("market_snapshot") or {}
        quote_audit = tool_audit.get("quote") or {}

        if snapshot_audit.get("resolved_source") != "coingecko":
            raise RuntimeError(f"Case {case['case_id']} did not use real CoinGecko data: {snapshot_audit}")
        if quote_audit.get("resolved_source") != "1inch":
            raise RuntimeError(f"Case {case['case_id']} did not use real 1inch data: {quote_audit}")

        results.append(
            {
                "case_id": case.get("case_id", f"case-{index}"),
                "status": body.get("status"),
                "duration_s": round(duration_s, 4),
                "snapshot_source": snapshot_audit.get("resolved_source"),
                "quote_source": quote_audit.get("resolved_source"),
                "quote_latency_ms": quote_audit.get("latency_ms"),
                "quote_expires_at": ((tx_plan.get("quote_validity") or {}).get("expires_at")),
                "handoff_status": ((tx_plan.get("wallet_handoff") or {}).get("status")),
            }
        )

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "server_url": base_url,
            "config": args.config,
            "repeat": args.repeat,
            "strict_real_tools_required": True,
        },
        "summary": summarize(results),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote real-tools benchmark results to {output_path}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)

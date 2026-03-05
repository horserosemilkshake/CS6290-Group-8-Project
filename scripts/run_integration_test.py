"""
Integration test: run harness against the live FastAPI agent backend.

Usage:
    1. Start agent server:  python -m uvicorn agent_client.src.main:app --port 8000
    2. Run this script:     python scripts/run_integration_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from harness.agent_clients import FastAPIAgentClient
from harness.runner import SmokeHarness


def main() -> None:
    seed = 6290
    client = FastAPIAgentClient(base_url="http://127.0.0.1:8000")

    print("=== Health Check ===")
    if not client.health_check():
        print("[FAIL] Agent server unreachable at http://127.0.0.1:8000")
        print("       Start it first:  python -m uvicorn agent_client.src.main:app --port 8000")
        sys.exit(1)
    print("[OK] Agent server is running\n")

    suite_path = root / "testcases" / "milestone1_cases.json"
    artifact_root = root / "artifacts"

    print(f"=== Running suite: {suite_path.name} ===\n")
    harness = SmokeHarness(artifact_root, agent_client=client)
    report = harness.run_suite(suite_path, seed=seed)

    print(f"Run ID   : {report['run']['run_id']}")
    print(f"Seed     : {report['meta']['seed']}")
    print(f"Git      : {report['meta']['git_commit'] or 'N/A'}")
    print(f"Cases    : {report['run']['case_count']}")
    print(f"ASR      : {report['metrics']['asr']:.2%}")
    print(f"FP       : {report['metrics']['fp']:.2%}")
    print(f"TR (max) : {report['metrics']['tr']:.4f}s")
    print(f"Artifact : {report['artifact_path']}")

    print("\n=== Per-case Results ===\n")
    print(f"{'case_id':<25} {'category':<14} {'expected':<10} {'observed':<10} {'status':<10} {'reason'}")
    print("-" * 110)
    for r in report["results"]:
        reason = ""
        raw = r.get("raw") or {}
        if isinstance(raw, dict) and raw.get("error"):
            reason = raw["error"].get("message", "")[:50]
        print(f"{r['case_id']:<25} {r['category']:<14} {r['expected']:<10} {r['observed']:<10} {r['status']:<10} {reason}")


if __name__ == "__main__":
    main()

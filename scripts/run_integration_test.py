"""
Integration test: run harness against the live FastAPI agent backend.

Usage:
    1. Start agent server:  python -m uvicorn agent_client.src.main:app --port 8000
    2. Run this script:     python scripts/run_integration_test.py [suite_file]
       Default suite: milestone1_cases.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
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

    suite_name = sys.argv[1] if len(sys.argv) > 1 else "milestone1_cases.json"
    suite_path = root / "testcases" / suite_name
    artifact_root = root / "artifacts"

    print(f"=== Running suite: {suite_path.name} ===\n")
    harness = SmokeHarness(artifact_root, agent_client=client)
    report = harness.run_suite(suite_path, seed=seed)

    results = report["results"]

    print(f"Run ID   : {report['run']['run_id']}")
    print(f"Seed     : {report['meta']['seed']}")
    print(f"Git      : {report['meta']['git_commit'] or 'N/A'}")
    print(f"Cases    : {report['run']['case_count']}")
    print(f"ASR      : {report['metrics']['asr']:.2%}")
    print(f"FP       : {report['metrics']['fp']:.2%}")
    print(f"TR (max) : {report['metrics']['tr']:.4f}s")
    print(f"Artifact : {report['artifact_path']}")

    # --- Per-category summary ---
    cat_counter: Counter = Counter()
    cat_match: Counter = Counter()
    for r in results:
        cat = r["category"]
        cat_counter[cat] += 1
        if r["status"] == "MATCH":
            cat_match[cat] += 1

    print("\n=== Category Summary ===\n")
    print(f"{'category':<22} {'total':>6} {'match':>6} {'mismatch':>8} {'match%':>8}")
    print("-" * 54)
    for cat in sorted(cat_counter.keys()):
        total = cat_counter[cat]
        match = cat_match[cat]
        mis = total - match
        pct = match / total if total else 0
        print(f"{cat:<22} {total:>6} {match:>6} {mis:>8} {pct:>7.1%}")
    total_all = sum(cat_counter.values())
    match_all = sum(cat_match.values())
    mis_all = total_all - match_all
    pct_all = match_all / total_all if total_all else 0
    print(f"{'TOTAL':<22} {total_all:>6} {match_all:>6} {mis_all:>8} {pct_all:>7.1%}")

    # --- Per-case detail ---
    print("\n=== Per-case Results ===\n")
    print(f"{'case_id':<25} {'category':<22} {'expected':<10} {'observed':<10} {'status':<10}")
    print("-" * 80)
    for r in results:
        marker = " <<" if r["status"] == "MISMATCH" else ""
        print(f"{r['case_id']:<25} {r['category']:<22} {r['expected']:<10} {r['observed']:<10} {r['status']:<10}{marker}")

    # --- Mismatch detail ---
    mismatches = [r for r in results if r["status"] == "MISMATCH"]
    if mismatches:
        print(f"\n=== Mismatches ({len(mismatches)}) ===\n")
        for r in mismatches:
            print(f"  {r['case_id']}:  expected={r['expected']}  observed={r['observed']}  cat={r['category']}")

    # --- Save detailed results JSON ---
    out_path = artifact_root / "latest_100case_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nDetailed results saved to: {out_path}")


if __name__ == "__main__":
    main()

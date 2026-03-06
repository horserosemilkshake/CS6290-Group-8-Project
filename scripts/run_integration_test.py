"""
Integration test: run harness against the live FastAPI agent backend.

Usage:
    1. Start agent server:  python -m uvicorn agent_client.src.main:app --port 8000
    2. Run this script:     python scripts/run_integration_test.py [suite_file] [--config bare|l1|l1l2]
       Default suite: milestone1_cases.json    Default config: l1l2
    3. Run all three configs: python scripts/run_integration_test.py [suite_file] --all-configs
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from harness.agent_clients import FastAPIAgentClient
from harness.runner import SmokeHarness

_PROFILE_MAP = {"bare": "bare", "l1": "l1", "l1l2": "l1l2"}


def run_single(client: FastAPIAgentClient, suite_path: Path, artifact_root: Path,
               config: str, seed: int = 6290, verbose: bool = True) -> dict:
    """Run one suite under one defense config. Returns the report dict."""
    profile = _PROFILE_MAP[config]
    active = client.set_defense_config(config)
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Defense config: {active}  |  Suite: {suite_path.name}")
        print(f"{'='*60}\n")

    harness = SmokeHarness(artifact_root, agent_client=client)
    report = harness.run_suite(suite_path, seed=seed, defense_profile=profile)
    results = report["results"]

    print(f"Run ID   : {report['run']['run_id']}")
    print(f"Config   : {active}")
    print(f"Seed     : {report['meta']['seed']}")
    print(f"Git      : {report['meta']['git_commit'] or 'N/A'}")
    print(f"Cases    : {report['run']['case_count']}")
    print(f"ASR      : {report['metrics']['asr']:.2%}")
    print(f"FP       : {report['metrics']['fp']:.2%}")
    print(f"TR (max) : {report['metrics']['tr']:.4f}s")

    if verbose:
        _print_category_summary(results)
        _print_per_case(results)
        _print_mismatches(results)

    out_name = f"results_{profile}_{suite_path.stem}.json"
    out_path = artifact_root / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"Results  : {out_path}")
    return report


def run_all_configs(client: FastAPIAgentClient, suite_path: Path,
                    artifact_root: Path, seed: int = 6290) -> None:
    """Run suite under bare → l1 → l1l2 and print comparison table."""
    reports: dict[str, dict] = {}
    for cfg in ("bare", "l1", "l1l2"):
        reports[cfg] = run_single(client, suite_path, artifact_root, cfg, seed, verbose=False)

    print(f"\n{'='*60}")
    print("  THREE-CONFIG COMPARISON")
    print(f"{'='*60}\n")
    print(f"{'config':<10} {'ASR':>8} {'FP':>8} {'TR(max)':>10} {'match':>8} {'mismatch':>10}")
    print("-" * 58)
    for cfg in ("bare", "l1", "l1l2"):
        m = reports[cfg]["metrics"]
        res = reports[cfg]["results"]
        matches = sum(1 for r in res if r["status"] == "MATCH")
        mis = len(res) - matches
        print(f"{cfg:<10} {m['asr']:>7.2%} {m['fp']:>7.2%} {m['tr']:>9.4f}s {matches:>8} {mis:>10}")

    _print_per_case_comparison(reports)

    summary_path = artifact_root / f"three_config_comparison_{suite_path.stem}.json"
    summary = {cfg: {"metrics": r["metrics"], "meta": r["meta"]} for cfg, r in reports.items()}
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nComparison saved to: {summary_path}")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_category_summary(results: list) -> None:
    cat_counter: Counter = Counter()
    cat_match: Counter = Counter()
    for r in results:
        cat = r["category"]
        cat_counter[cat] += 1
        if r["status"] == "MATCH":
            cat_match[cat] += 1
    print(f"\n--- Category Summary ---\n")
    print(f"{'category':<22} {'total':>6} {'match':>6} {'mismatch':>8} {'match%':>8}")
    print("-" * 54)
    for cat in sorted(cat_counter.keys()):
        total = cat_counter[cat]
        match = cat_match[cat]
        mis = total - match
        pct = match / total if total else 0
        print(f"{cat:<22} {total:>6} {match:>6} {mis:>8} {pct:>7.1%}")


def _print_per_case(results: list) -> None:
    print(f"\n--- Per-case Results ---\n")
    print(f"{'case_id':<25} {'expected':<10} {'observed':<10} {'status':<10}")
    print("-" * 58)
    for r in results:
        marker = " <<" if r["status"] == "MISMATCH" else ""
        print(f"{r['case_id']:<25} {r['expected']:<10} {r['observed']:<10} {r['status']:<10}{marker}")


def _print_mismatches(results: list) -> None:
    mismatches = [r for r in results if r["status"] == "MISMATCH"]
    if mismatches:
        print(f"\n--- Mismatches ({len(mismatches)}) ---\n")
        for r in mismatches:
            print(f"  {r['case_id']}:  expected={r['expected']}  observed={r['observed']}")


def _print_per_case_comparison(reports: dict[str, dict]) -> None:
    """Side-by-side observed outcomes for each case across configs."""
    bare_res = {r["case_id"]: r for r in reports["bare"]["results"]}
    l1_res = {r["case_id"]: r for r in reports["l1"]["results"]}
    l1l2_res = {r["case_id"]: r for r in reports["l1l2"]["results"]}
    all_ids = [r["case_id"] for r in reports["bare"]["results"]]

    print(f"\n--- Per-case Comparison ---\n")
    print(f"{'case_id':<25} {'expected':<10} {'bare':<10} {'l1':<10} {'l1l2':<10}")
    print("-" * 68)
    for cid in all_ids:
        exp = bare_res[cid]["expected"]
        b = bare_res[cid]["observed"]
        l1 = l1_res[cid]["observed"]
        l2 = l1l2_res[cid]["observed"]
        print(f"{cid:<25} {exp:<10} {b:<10} {l1:<10} {l2:<10}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run integration tests against agent server")
    parser.add_argument("suite", nargs="?", default="milestone1_cases.json",
                        help="Test suite file name under testcases/ (default: milestone1_cases.json)")
    parser.add_argument("--config", choices=["bare", "l1", "l1l2"], default="l1l2",
                        help="Defense configuration (default: l1l2)")
    parser.add_argument("--all-configs", action="store_true",
                        help="Run all three configs (bare, l1, l1l2) and print comparison")
    parser.add_argument("--seed", type=int, default=6290)
    args = parser.parse_args()

    client = FastAPIAgentClient(base_url="http://127.0.0.1:8000")

    print("=== Health Check ===")
    if not client.health_check():
        print("[FAIL] Agent server unreachable at http://127.0.0.1:8000")
        print("       Start it first:  python -m uvicorn agent_client.src.main:app --port 8000")
        sys.exit(1)
    print("[OK] Agent server is running\n")

    suite_path = root / "testcases" / args.suite
    artifact_root = root / "artifacts"

    if args.all_configs:
        run_all_configs(client, suite_path, artifact_root, args.seed)
    else:
        run_single(client, suite_path, artifact_root, args.config, args.seed)


if __name__ == "__main__":
    main()

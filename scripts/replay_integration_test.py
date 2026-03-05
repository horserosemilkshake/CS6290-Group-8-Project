"""
Cross-machine replay checker for integration runs.

Usage:
    1. Start agent server:
       python -m uvicorn agent_client.src.main:app --port 8000
    2. Replay with auto-selected latest baseline:
       python scripts/replay_integration_test.py
    3. Replay against a specific baseline artifact:
       python scripts/replay_integration_test.py --baseline-artifact "<artifact-json-path>"

Notes:
    - By default, compares reproducibility-safe fields (seed, suite hash, case ids, metrics shape).
    - Use --strict-observed to additionally require observed decisions to match baseline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from harness.agent_clients import FastAPIAgentClient
from harness.runner import SmokeHarness


def _load_baseline(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_run_summary_artifact(path: Path) -> bool:
    try:
        data = _load_baseline(path)
    except Exception:
        return False
    return (
        isinstance(data, dict)
        and data.get("type") == "run_summary"
        and isinstance(data.get("payload"), dict)
        and isinstance(data["payload"].get("data"), dict)
        and isinstance(data["payload"]["data"].get("meta"), dict)
    )


def _find_latest_baseline_artifact(artifact_root: Path) -> Path:
    runs_root = artifact_root / "runs"
    if not runs_root.exists():
        raise FileNotFoundError("No artifacts/runs directory found.")

    candidates = [p for p in runs_root.rglob("*.json") if _is_run_summary_artifact(p)]
    if not candidates:
        raise FileNotFoundError("No run_summary artifacts found under artifacts/runs.")

    # Latest by modification time.
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _extract_core(artifact: dict) -> dict:
    data = artifact["payload"]["data"]
    meta = data["meta"]
    results = data["results"]
    return {
        "seed": meta["seed"],
        "suite_sha256": meta["suite_sha256"],
        "case_ids": [r["case_id"] for r in results],
        "observed": [r["observed"] for r in results],
        "metrics": data["metrics"],
    }


def _check(condition: bool, label: str, detail: str = "") -> bool:
    if condition:
        print(f"[OK]   {label}")
        return True
    print(f"[FAIL] {label}" + (f" -> {detail}" if detail else ""))
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay integration run and compare with baseline artifact.")
    parser.add_argument("--baseline-artifact", required=False, help="Path to baseline artifact JSON.")
    parser.add_argument(
        "--suite-path",
        default=str(root / "testcases" / "milestone1_cases.json"),
        help="Path to test suite JSON.",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Agent service base URL.")
    parser.add_argument("--strict-observed", action="store_true", help="Require observed decisions to match exactly.")
    args = parser.parse_args()

    if args.baseline_artifact:
        baseline_path = Path(args.baseline_artifact)
    else:
        baseline_path = _find_latest_baseline_artifact(root / "artifacts")
    suite_path = Path(args.suite_path)
    artifact_root = root / "artifacts"

    baseline = _load_baseline(baseline_path)
    baseline_core = _extract_core(baseline)
    seed = int(baseline_core["seed"])

    client = FastAPIAgentClient(base_url=args.base_url)
    print("=== Health Check ===")
    if not client.health_check():
        print(f"[FAIL] Agent server unreachable at {args.base_url}")
        sys.exit(1)
    print("[OK] Agent server is running\n")

    print("=== Replay Run ===")
    print(f"Baseline : {baseline_path}")
    print(f"Suite    : {suite_path}")
    print(f"Seed     : {seed}")
    print(f"Strict   : {args.strict_observed}\n")

    harness = SmokeHarness(artifact_root, agent_client=client)
    replay_report = harness.run_suite(suite_path, seed=seed)

    replay_artifact_path = Path(replay_report["artifact_path"])
    replay_artifact = _load_baseline(replay_artifact_path)
    replay_core = _extract_core(replay_artifact)

    print("=== Comparison ===")
    checks = []
    checks.append(_check(replay_core["seed"] == baseline_core["seed"], "seed matches"))
    checks.append(
        _check(
            replay_core["suite_sha256"] == baseline_core["suite_sha256"],
            "suite_sha256 matches",
            f"{replay_core['suite_sha256']} != {baseline_core['suite_sha256']}",
        )
    )
    checks.append(
        _check(
            replay_core["case_ids"] == baseline_core["case_ids"],
            "case_id order matches",
        )
    )

    for metric_name in ("asr", "fp"):
        left = float(replay_core["metrics"][metric_name])
        right = float(baseline_core["metrics"][metric_name])
        checks.append(
            _check(
                math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12),
                f"{metric_name} matches",
                f"{left} != {right}",
            )
        )

    if args.strict_observed:
        checks.append(
            _check(
                replay_core["observed"] == baseline_core["observed"],
                "observed decisions match (strict)",
            )
        )
    else:
        print("[INFO] observed decisions check skipped (use --strict-observed to enable)")

    print("\n=== Replay Artifact ===")
    print(replay_artifact_path)

    if all(checks):
        print("\n[PASS] Replay consistency checks passed.")
        return

    print("\n[FAIL] Replay consistency checks failed.")
    sys.exit(2)


if __name__ == "__main__":
    main()

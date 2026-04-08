"""
DEPRECATED (2026-03-03):
    Replaced by scripts/run_integration_test.py which uses FastAPIAgentClient
    to call the real Agent backend. This script only runs with PlaceholderAgentClient
    (all results are UNEXECUTED), and its functionality is already covered by
    tests/test_smoke_harness.py in pytest.
"""
from __future__ import annotations

from pathlib import Path

from harness.runner import SmokeHarness


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # Get the absolute path of the current script, go up two levels as the project root (assuming the script is located at scripts/run_smoke_harness.py)
    suite_path = root / "testcases" / "smoke_cases.json"
    artifact_root = root / "artifacts"

    harness = SmokeHarness(artifact_root)  # Initialize the test harness, specifying the artifact storage location
    report = harness.run_suite(suite_path)  # Run the test suite, passing the test case file path, returning the test report

    print("Smoke harness completed.")
    print(f"Run ID: {report['run']['run_id']}")
    print(f"Metrics: {report['metrics']}")


if __name__ == "__main__":
    main()
